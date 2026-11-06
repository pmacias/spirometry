"""Results export: Phil's saved fits -> small aggregate tables for the dashboard.

    python -m spirometry.export --analysis data/analysis --out results
        [--ref reference] [--db data/runs/runs.duckdb] [--horizon h3] [--skip-errors]
        [--snapshot-end YYYY-MM-DD] [--min-cell-offers 10]

--db (read-only) fills meta.json's build stamp from build_info and the snapshot's play
dates from the run tables: snapshot_start_date / snapshot_end_date = the first and last UTC
start date over the primary population (play_dates_all_records: the same over every
record). Aggregates only. --snapshot-end overrides the end date. It also copies build_info's
deduplication counts into meta.json's "dedup" (DEDUP_FIELDS: records read, exact repeats
dropped and how many of them differed, solo run keys with several records, primary offers
removed by run_key deduplication, retried solo and primary run keys).

Reads what notebooks/02_pick_rate_did.ipynb and 03_anticipation.ipynb save in
data/analysis/ (git-ignored):

    did_main.parquet                main fit, did.run_all through the notebook's tidy()
                                    (index card_patch_id, ci95 split into ci_lo / ci_hi)
    did_<horizon>.parquet           fixed-horizon fit (--horizon, default h3: weeks 0-3)
    did_<check>.parquet             robustness checks (pooled_groups, tagged, untagged,
                                    drop_shared_screens, drop_behavior_flags,
                                    drop_top_uploaders): whatever is there
    event_studies.parquet           did.fit_event_study per tweak (+ card_patch_id, error)
    did_second_patch_checks.parquet second patch's before-block variants
    anticipation_main.parquet       did.anticipation_all (optional)
    offer_rate.parquet              the notebook's section 3 table `orc` (optional; the
                                    notebook doesn't save it yet: one line,
                                    orc.to_parquet(OUT / "offer_rate.parquet"))

plus reference/tweak_sizes.csv, beta_exposure.csv and builds.csv. Writes to --out:

    pick_rate_did.csv   one row per tweak (card_patch_id)
    flags.csv           one row per tweak: offer-rate flags, pre-trend slope, placebo,
                        second-patch before-block variants
    weekly.csv          event study: one row per (tweak, week, block) cell
    dose_response.csv   the four meta-regression models (spirometry.meta), both horizons
    robustness.csv      one row per (tweak, check): beta, se
    anticipation.csv    one row per tweak (only when anticipation_main.parquet exists)
    meta.json           provenance: build_info and the play-date range (only with --db),
                        inputs, blanks and why

Derived columns (everything else is copied from the fits or tweak_sizes.csv):

- patch: "first", "second", ... by the release date (builds.csv) of the tweak's
  stable_build. window: "<before_builds> -> <after_builds>".
- beta_lo, se_lo (all weeks) and beta_lo_h, se_lo_h (fixed horizon): delta method, as in
  the notebook's section 8 (did.to_log_odds): beta / (p (1 - p)), se / (p (1 - p)), p =
  the treated card's pick rate before, from the same fit.
- clearly_nonzero (clearly_nonzero_h): |beta| > 2 se, "yes" / "no". Clustered errors, not
  calibrated.
- clearly_nonzero_cal (clearly_nonzero_h_cal): the same with the se multiplied by the
  patch's placebo factor at that horizon (PLACEBO_FACTORS_ALL, PLACEBO_FACTORS_H3), which
  gives the calibrated counts: |beta| > CAL_Z x se x factor. Blank for a patch with no
  factor.
- toward_change: "yes" when sign(beta) = sign(direction x log_ratio), "no" otherwise,
  blank for mixed-direction and upgrade-only tweaks (no single direction to compare) and
  when beta or log_ratio is missing. Computed for every tweak, not only clearly nonzero
  ones.
- change: "buff" / "nerf" by the sign of direction x log_ratio, or for upgrade-only
  tweaks of direction x (upgrade_new - upgrade_old), as the notebook's forest plot colors
  them; mixed-direction tweaks by their main field; blank when the size is missing.
- dose_x: direction x log_ratio; dose_x_upgraded: direction x upgraded_log_ratio (where
  the dashboard draws upgrade-only tweaks).
- pretrend_slope, pretrend_slope_se: the notebook's section 5 pretrend_summary: weighted
  (1/se^2) least-squares slope of the before-block event-study coefficients at weeks < 0
  on week, probability per week; blank with fewer than 2 such weeks.

Safety: every output is checked before writing. A column named uploader_hash, run_key,
run_hash, seed or player_*, or a string cell that looks like a hashed id (16 or 64 hex
characters), stops the export; so does a repeated key (every table has one row per tweak,
per (tweak, week, block) or per (tweak, check)). Event-study cells with fewer than
--min-cell-offers treated offers are dropped (the notebook's plots hide cells under 100).

Errors: a fit table row with a non-empty `error` stops the export, naming the rows, unless
--skip-errors; skipped rows are left out and listed in meta.json. A failed upgrade-only
placebo (placebo_error) leaves the placebo blank and is listed in meta.json.
"""
import argparse, datetime, json, pathlib, re, sys

import numpy as np
import pandas as pd

from spirometry import meta

REF = pathlib.Path("reference")
PATCH_NAMES = ["first", "second", "third", "fourth", "fifth"]
FORBIDDEN_COLUMN = re.compile(r"^(uploader_hash|run_key|run_hash|seed|player_.*)$")
HASH_VALUE = re.compile(r"(?<![0-9a-f])(?:[0-9a-f]{16}|[0-9a-f]{64})(?![0-9a-f])")
FIT_CHECK_SKIP = {"main", "second_patch_checks"}     # did_*.parquet that aren't checks
# Robust placebo sd by patch: SPIROMETRY.md, "Weeks 0–3 placebos" and the calibrated counts
# in "Phase 5 results". Multiplies a clustered SE as it divides a z. Here because the export
# can't import site_figures (that needs pyfixest); site_figures imports them from here.
# index.html's CAL (website repo) must match the weeks 0-3 ones; scripts/site_publish.sh
# checks that it does.
PLACEBO_FACTORS_H3 = {"first": 4.10, "second": 2.67}
PLACEBO_FACTORS_ALL = {"first": 4.52, "second": 2.07}
CAL_Z = 2                       # calibrated |z| cutoff: the calibrated counts' rule


class ExportError(RuntimeError):
    pass


# ---------------------------------------------------------------------------- reading

def _csv(path):
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _num(s):
    return pd.to_numeric(s, errors="coerce")


def _text(s):
    """Missing-safe string column ('' for None/NaN)."""
    return s.map(lambda v: "" if v is None or (isinstance(v, float) and np.isnan(v))
                 else str(v))


def read_fit(path):
    """A saved fit table with card_patch_id as a column (tidy() saves it as the index)."""
    df = pd.read_parquet(path)
    if df.index.name == "card_patch_id":
        df = df.reset_index()
    return df


def drop_errors(df, name, skip_errors, skipped, col="error"):
    """Rows with a non-empty `col` stop the export unless skip_errors; skipped rows are
    removed and recorded in `skipped`."""
    if col not in df:
        return df
    bad = _text(df[col]) != ""
    if not bad.any():
        return df
    ids = sorted(set(df.loc[bad, "card_patch_id"]))
    if not skip_errors:
        raise ExportError(f"{name}: {len(ids)} tweak(s) with an error row: "
                          f"{', '.join(ids)}. Fix the fit or pass --skip-errors.")
    skipped.append(dict(table=name, card_patch_ids=ids))
    return df[~bad].copy()


def tweaks(ref=REF):
    """tweak_sizes.csv with patch and window labels."""
    ref = pathlib.Path(ref)
    tw = _csv(ref / "tweak_sizes.csv")
    builds = _csv(ref / "builds.csv").set_index("build_id")
    dates = {b: builds.release_date.get(b, "") for b in tw.stable_build.unique()}
    missing = sorted(b for b, d in dates.items() if not d)
    if missing:
        raise ExportError(f"builds.csv has no release date for stable build(s) {missing}")
    order = sorted(dates, key=lambda b: dates[b])
    if len(order) > len(PATCH_NAMES):
        raise ExportError(f"{len(order)} stable builds; PATCH_NAMES has {len(PATCH_NAMES)}")
    tw["patch"] = tw.stable_build.map(dict(zip(order, PATCH_NAMES)))
    tw["window"] = tw.before_builds + " -> " + tw.after_builds
    for c in ["log_ratio", "upgraded_log_ratio", "direction"]:
        tw[c] = _num(tw[c])
    return tw.set_index("card_patch_id")


# ---------------------------------------------------------------------------- derived

def to_log_odds(beta, se, p_before):
    """did.to_log_odds, vectorized: beta / (p (1 - p)), se / (p (1 - p)); blank when
    p (1 - p) is not positive."""
    k = p_before * (1 - p_before)
    k = k.where(k > 0)
    return beta / k, se / k


def _yes_no(cond, valid=None):
    out = np.where(cond, "yes", "no").astype(object)
    if valid is not None:
        out[~np.asarray(valid, bool)] = ""
    return out


def clearly_nonzero_calibrated(beta, se, patch, factors):
    """'yes' / 'no' by the calibrated rule, |beta| > CAL_Z x se x the patch's factor; blank
    where beta is missing or the patch has no factor."""
    factor = patch.map(factors)
    return _yes_no(beta.abs() > CAL_Z * se * factor, beta.notna() & factor.notna())


def toward_change(beta, dose_x, single):
    """"yes" when sign(beta) = sign(dose_x), "no" otherwise; blank where the tweak has no
    single direction (`single` false: mixed-direction or upgrade-only) or beta or dose_x is
    missing. dose_x = direction x log_ratio."""
    return _yes_no(np.sign(beta) == np.sign(dose_x),
                   single & dose_x.notna() & beta.notna())


def _upgrade_delta(tw):
    strip = lambda s: _num(s.str.replace("+", "", regex=False))
    return strip(tw.upgrade_new) - strip(tw.upgrade_old)


def pretrend(es):
    """The notebook's pretrend_summary (section 5), without the chi2 screen: weighted
    slope of the before-block coefficients at week < 0 on week. Returns (n_pre, slope,
    slope_se)."""
    pre = es[(es.block == "before") & (es.week < 0)].dropna(subset=["coef", "se"])
    if len(pre) < 2:
        return len(pre), np.nan, np.nan
    w = 1 / pre.se ** 2
    xm = np.average(pre.week, weights=w)
    sxx = (w * (pre.week - xm) ** 2).sum()
    slope = (w * (pre.week - xm) * pre.coef).sum() / sxx
    return len(pre), float(slope), float(1 / np.sqrt(sxx))


# ------------------------------------------------------------------------------ tables

PICK_RATE_COLUMNS = [
    "card_patch_id", "card_id", "character", "patch", "window", "stable_build", "fit_on",
    "beta", "se", "se_hc", "ci_lo", "ci_hi", "after_week_max", "n_treated_offers",
    "treated_rate_before", "treated_rate_after", "control_rate_before", "control_rate_after",
    "beta_h", "se_h", "ci_lo_h", "ci_hi_h", "after_week_max_h",
    "main_field", "old", "new", "log_ratio", "upgrade_field", "upgrade_old", "upgrade_new",
    "upgraded_log_ratio", "direction", "upgrade_only", "mixed_direction", "solo_estimable",
    "beta_lo", "se_lo", "beta_lo_h", "se_lo_h", "clearly_nonzero", "clearly_nonzero_h",
    "clearly_nonzero_cal", "clearly_nonzero_h_cal",
    "toward_change", "change", "dose_x", "dose_x_upgraded"]


def pick_rate_did(main, h, tw):
    """One row per tweak in the main fit; the fixed-horizon columns by card_patch_id."""
    m = main.set_index("card_patch_id")
    num = ["beta", "se", "se_hc", "ci_lo", "ci_hi", "after_week_max", "n_treated_offers",
           "treated_rate_before", "treated_rate_after", "control_rate_before",
           "control_rate_after"]
    out = m[["card_id", "fit_on"]].copy()
    for c in num:
        out[c] = _num(m[c])
    hh = h.set_index("card_patch_id")
    for c in ["beta", "se", "ci_lo", "ci_hi", "after_week_max", "treated_rate_before"]:
        out[f"{c}_h"] = _num(hh[c]).reindex(out.index)
    unknown = sorted(set(out.index) - set(tw.index))
    if unknown:
        raise ExportError(f"fits have tweaks not in tweak_sizes.csv: {unknown}")
    t = tw.loc[out.index]
    for c in ["patch", "window", "stable_build", "main_field", "old", "new", "log_ratio",
              "upgrade_field", "upgrade_old", "upgrade_new", "upgraded_log_ratio",
              "direction", "upgrade_only", "mixed_direction", "solo_estimable"]:
        out[c] = t[c]
    out["character"] = t["color"]
    out["beta_lo"], out["se_lo"] = to_log_odds(out.beta, out.se, out.treated_rate_before)
    out["beta_lo_h"], out["se_lo_h"] = to_log_odds(out.beta_h, out.se_h,
                                                   out.treated_rate_before_h)
    out["clearly_nonzero"] = _yes_no(out.beta.abs() > 2 * out.se, out.beta.notna())
    out["clearly_nonzero_h"] = _yes_no(out.beta_h.abs() > 2 * out.se_h, out.beta_h.notna())
    out["clearly_nonzero_cal"] = clearly_nonzero_calibrated(out.beta, out.se, out.patch,
                                                            PLACEBO_FACTORS_ALL)
    out["clearly_nonzero_h_cal"] = clearly_nonzero_calibrated(out.beta_h, out.se_h, out.patch,
                                                              PLACEBO_FACTORS_H3)
    out["dose_x"] = out.direction * out.log_ratio
    out["dose_x_upgraded"] = out.direction * out.upgraded_log_ratio
    single = (out.mixed_direction != "yes") & (out.upgrade_only != "yes")
    out["toward_change"] = toward_change(out.beta, out.dose_x, single)
    dose = np.where(out.upgrade_only == "yes", out.direction * _upgrade_delta(t), out.dose_x)
    out["change"] = np.where(pd.isna(dose), "", np.where(dose > 0, "buff", "nerf"))
    return out.reset_index()[PICK_RATE_COLUMNS]


FLAG_COLUMNS = [
    "card_patch_id", "card_id", "patch",
    "offer_rate_flag", "offer_rate_flag_rarity", "offer_share_vs_controls",
    "offer_rate_z_binom", "offer_rate_z_binom_rarity",
    "pretrend_n_weeks", "pretrend_slope", "pretrend_slope_se",
    "placebo_beta", "placebo_se", "placebo_n_offers",
    "pooled_before_beta", "pooled_before_se",
    "no_first_patch_controls_beta", "no_first_patch_controls_se"]


def flags(prd, es, main, offer_rate=None, second=None):
    out = prd[["card_patch_id", "card_id", "patch"]].set_index("card_patch_id")
    out = out.reindex(columns=FLAG_COLUMNS[1:])
    if offer_rate is not None:
        o = offer_rate.set_index("card_patch_id").reindex(out.index)
        present = o.flag.notna()
        out["offer_rate_flag"] = _yes_no(o.flag.fillna(False).astype(bool), present)
        out["offer_rate_flag_rarity"] = _yes_no(o.flag_rarity.fillna(False).astype(bool),
                                                o.flag_rarity.notna())
        out["offer_share_vs_controls"] = _num(o.log_share_ratio) - _num(o.controls_median)
        out["offer_rate_z_binom"] = _num(o.z_binom)
        out["offer_rate_z_binom_rarity"] = _num(o.z_binom_rarity)
    for cpid, g in es.groupby("card_patch_id"):
        if cpid in out.index:
            out.loc[cpid, ["pretrend_n_weeks", "pretrend_slope", "pretrend_slope_se"]] = \
                pretrend(g)
    m = main.set_index("card_patch_id")
    for c in ["beta", "se", "n_offers"]:
        if f"placebo_{c}" in m:
            out[f"placebo_{c}"] = _num(m[f"placebo_{c}"]).reindex(out.index)
    if second is not None:
        for variant, prefix in [("pooled before", "pooled_before"),
                                ("no first-patch controls", "no_first_patch_controls")]:
            s = second[second.variant == variant].set_index("card_patch_id")
            out[f"{prefix}_beta"] = _num(s.beta).reindex(out.index)
            out[f"{prefix}_se"] = _num(s.se).reindex(out.index)
    return out.reset_index()[FLAG_COLUMNS]


def weekly(es, prd, min_cell_offers):
    w = es[es.card_patch_id.isin(prd.card_patch_id)].copy()
    for c in ["week", "coef", "se", "n_offers"]:
        w[c] = _num(w[c])
    w = w[w.n_offers >= min_cell_offers]
    w["card_id"] = w.card_patch_id.map(prd.set_index("card_patch_id").card_id)
    w["week"] = w.week.astype(int)
    w["n_offers"] = w.n_offers.astype(int)
    return (w[["card_patch_id", "card_id", "week", "block", "coef", "se", "n_offers"]]
            .sort_values(["card_patch_id", "block", "week"]).reset_index(drop=True))


def dose_response(prd, horizon_label):
    """The notebook's section 8 on the tweaks with one direction and a size: both
    horizons, four models each."""
    base = prd[(prd.mixed_direction != "yes") & (prd.upgrade_only != "yes")
               & prd.dose_x.notna()]
    out = []
    for label, b, s in [(horizon_label, "beta_lo_h", "se_lo_h"),
                        ("all weeks", "beta_lo", "se_lo")]:
        line = base[base[b].notna() & (base[s] > 0)]
        if len(line) < 5:
            continue
        fits = meta.dose_response_fits(line[b], line[s], line.dose_x,
                                       (line.patch != "first").astype(float))
        out.append(fits.assign(horizon=label))
    if not out:
        return pd.DataFrame(columns=["horizon", "model", "term", "term_label", "coef", "se",
                                     "z", "tau2", "Q", "df", "n_tweaks"])
    return pd.concat(out, ignore_index=True)[
        ["horizon", "model", "term", "term_label", "coef", "se", "z", "tau2", "Q", "df",
         "n_tweaks"]]


def robustness(checks, prd):
    rows = []
    for name, df in checks.items():
        d = df[df.card_patch_id.isin(prd.card_patch_id)]
        rows.append(pd.DataFrame(dict(card_patch_id=d.card_patch_id, check=name,
                                      beta=_num(d.beta), se=_num(d.se),
                                      n_treated_offers=_num(d.n_treated_offers))))
    if not rows:
        return pd.DataFrame(columns=["card_patch_id", "check", "beta", "se",
                                     "n_treated_offers"])
    return pd.concat(rows, ignore_index=True).sort_values(["card_patch_id", "check"])


ANTICIPATION_COLUMNS = ["card_patch_id", "card_id", "patch", "window", "status", "reason",
                        "beta_main", "se_main", "beta_postbeta", "se", "ratio_to_main",
                        "share_before_release", "lead_days", "first_beta_build",
                        "first_beta_date", "stable_date"]


def anticipation(ant, tw, exposure):
    """anticipation_main.parquet's columns, plus patch / window (tweak_sizes.csv) and the
    first-beta build, its date and the stable date (beta_exposure.csv)."""
    a = ant.copy()
    a["patch"] = a.card_patch_id.map(tw.patch)
    a["window"] = a.card_patch_id.map(tw.window)
    ex = exposure.set_index("card_patch_id")
    for c in ["first_beta_build", "first_beta_date", "stable_date"]:
        a[c] = a.card_patch_id.map(ex[c]).fillna("") if c in ex else ""
    for c in ["beta_main", "se_main", "beta_postbeta", "se", "ratio_to_main",
              "share_before_release", "lead_days"]:
        a[c] = _num(a[c]) if c in a else np.nan
    for c in ["status", "reason", "card_id"]:
        a[c] = _text(a[c])
    return a[ANTICIPATION_COLUMNS].sort_values("card_patch_id").reset_index(drop=True)


# ------------------------------------------------------------------------------ checks

KEYS = {"pick_rate_did": ["card_patch_id"], "flags": ["card_patch_id"],
        "weekly": ["card_patch_id", "week", "block"], "robustness": ["card_patch_id", "check"],
        "anticipation": ["card_patch_id"], "dose_response": ["horizon", "model", "term"]}


def check_output(name, df):
    """Stop before writing anything run-level or identifying."""
    bad = [c for c in df.columns if FORBIDDEN_COLUMN.match(str(c))]
    if bad:
        raise ExportError(f"{name}: identifier column(s) {bad} must not be exported")
    for c in df.columns:
        if df[c].dtype == object or pd.api.types.is_string_dtype(df[c]):
            hit = df[c].astype(str).str.contains(HASH_VALUE)
            if hit.any():
                raise ExportError(f"{name}.{c}: {int(hit.sum())} value(s) look like a "
                                  f"hashed id")
    key = KEYS.get(name)
    if key and df.duplicated(key).any():
        raise ExportError(f"{name}: repeated {key}: not one row per aggregate")


# ------------------------------------------------------------------------------ meta

def build_info(db):
    """build_info from runs.duckdb, read-only."""
    import duckdb
    con = duckdb.connect(str(db), read_only=True)
    try:
        return dict(con.execute("SELECT key, value FROM build_info").fetchall())
    finally:
        con.close()


PLAY_DATES_POPULATION = "primary runs (runs.PRIMARY_RUN_FILTER on runs)"

# build_info's deduplication counts (spirometry.runs), copied into meta.json's "dedup" with
# --db: meta.json key -> build_info key.
DEDUP_FIELDS = {
    "records_read": "records_read",
    "exact_repeats_dropped": "duplicate_records_dropped",
    "exact_repeats_with_different_content": "duplicates_with_different_content",
    "solo_run_keys_multi_record": "solo_run_keys_multi_record",
    "primary_offers_dedup_removed": "primary_offers_dedup_removed",
    "solo_run_keys_retried": "solo_run_keys_retried",
    "primary_run_keys_retried": "primary_run_keys_retried",
}


def dedup_info(info):
    """build_info's deduplication counts under DEDUP_FIELDS' names, as integers; a field
    build_info lacks is left out (its reason goes in blank_reasons)."""
    out = {}
    for name, key in DEDUP_FIELDS.items():
        v = str(info.get(key, "")).strip()
        if v:
            out[name] = int(float(v))
    return out


def _date(v):
    """A start_time (TIMESTAMP, or epoch seconds) -> 'YYYY-MM-DD' (UTC); '' when missing."""
    if v is None:
        return ""
    if isinstance(v, (int, float)):
        v = datetime.datetime.fromtimestamp(v, datetime.timezone.utc)
    return v.date().isoformat()


def play_dates(db):
    """First and last play date (UTC date of start_time) in the run tables, read-only, two
    aggregates per population: the primary population (PRIMARY_RUN_FILTER: released builds,
    started on or after the build's release, solo, unmodded, Neow start) and every record.
    Copies of a run share start_time, so runs and runs_dedup give the same dates. {} when
    the database has no runs table."""
    import duckdb
    from spirometry.runs import PRIMARY_RUN_FILTER
    con = duckdb.connect(str(db), read_only=True)
    try:
        names = {r[0] for r in con.execute(
            "SELECT table_name FROM information_schema.tables").fetchall()}
        if "runs" not in names:
            return {}
        a = con.execute("SELECT min(start_time), max(start_time) FROM runs").fetchone()
        p = con.execute("SELECT min(r.start_time), max(r.start_time) FROM runs r "
                        f"WHERE {PRIMARY_RUN_FILTER}").fetchone()
    finally:
        con.close()
    return dict(start=_date(p[0]), end=_date(p[1]), all_start=_date(a[0]),
                all_end=_date(a[1]))


def meta_info(db, snapshot_end, inputs, skipped, notes, horizon_label):
    blank = {}
    info = build_info(db) if db else {}
    dates = play_dates(db) if db else {}
    why = ("no --db given" if not db else "not in build_info")
    why_dates = ("no --db given" if not db else
                 "no runs table, or no primary run with a start_time")
    m = dict(sample=False,
             exported_at_utc=datetime.datetime.now(datetime.timezone.utc)
             .isoformat(timespec="seconds"),
             parser_version=info.get("parser_version", ""),
             snapshot_pages=info.get("pages_parsed", ""),
             snapshot_last_page=info.get("last_page", ""),
             tables_built_at_utc=info.get("built_at_utc", ""),
             snapshot_start_date=dates.get("start", ""),
             snapshot_end_date=snapshot_end or dates.get("end", ""),
             snapshot_dates_source=("run tables, " + PLAY_DATES_POPULATION
                                    if dates.get("start") else ""),
             snapshot_end_date_source=("--snapshot-end" if snapshot_end else
                                       "run tables" if dates.get("end") else ""),
             play_dates_all_records=dict(start=dates.get("all_start", ""),
                                         end=dates.get("all_end", "")),
             dedup=dedup_info(info),
             horizon=horizon_label)
    for k in ["parser_version", "snapshot_pages", "snapshot_last_page",
              "tables_built_at_utc"]:
        if not m[k]:
            blank[k] = why
    for k in DEDUP_FIELDS:
        if k not in m["dedup"]:
            blank[f"dedup.{k}"] = why
    for k in ["snapshot_start_date", "snapshot_end_date"]:
        if not m[k]:
            blank[k] = why_dates
    m.update(blank_reasons=blank, inputs=inputs, skipped=skipped, notes=notes)
    return m


# ------------------------------------------------------------------------------ export

def export(analysis="data/analysis", out="results", ref=REF, db=None, horizon="h3",
           skip_errors=False, snapshot_end=None, min_cell_offers=10, sample=False):
    """Read the saved fits, build every table, check them, write them. Returns the tables
    (dict of DataFrames, plus 'meta')."""
    analysis, out, ref = pathlib.Path(analysis), pathlib.Path(out), pathlib.Path(ref)
    need = [analysis / "did_main.parquet", analysis / f"did_{horizon}.parquet",
            analysis / "event_studies.parquet"]
    missing = [str(p) for p in need if not p.exists()]
    if missing:
        raise ExportError(f"missing input(s): {missing}")
    skipped, notes = [], []
    inputs = {}

    def load(path):
        inputs[path.name] = datetime.datetime.fromtimestamp(
            path.stat().st_mtime, datetime.timezone.utc).isoformat(timespec="seconds")
        return read_fit(path)

    tw = tweaks(ref)
    for f in ["tweak_sizes.csv", "builds.csv", "beta_exposure.csv"]:
        inputs[f"reference/{f}"] = "committed"
    main = drop_errors(load(need[0]), need[0].name, skip_errors, skipped)
    h = drop_errors(load(need[1]), need[1].name, skip_errors, skipped)
    es = drop_errors(load(need[2]), need[2].name, skip_errors, skipped)
    if "placebo_error" in main:
        pe = _text(main.placebo_error) != ""
        if pe.any():
            notes.append("placebo blank (placebo_error): "
                         + ", ".join(sorted(main.card_patch_id[pe])))
    labels = _num(h.get("max_week_after", pd.Series(dtype=float))).dropna().unique()
    horizon_label = (f"weeks 0-{int(labels[0])}" if len(labels) == 1 else horizon)

    prd = pick_rate_did(main, h, tw)
    lost = sorted(set(main.card_patch_id) - set(h.card_patch_id))
    if lost:
        notes.append(f"no fixed-horizon row (beta_h blank): {', '.join(lost)}")

    orc_path = analysis / "offer_rate.parquet"
    offer_rate = load(orc_path) if orc_path.exists() else None
    if offer_rate is None:
        notes.append("offer-rate flag columns blank: offer_rate.parquet not found "
                     "(notebook 02 section 3 doesn't save its table yet)")
    sp_path = analysis / "did_second_patch_checks.parquet"
    second = None
    if sp_path.exists():
        second = drop_errors(load(sp_path), sp_path.name, skip_errors, skipped)
    else:
        notes.append("second-patch before-block columns blank: "
                     "did_second_patch_checks.parquet not found")

    checks = {}
    for p in sorted(analysis.glob("did_*.parquet")):
        name = p.stem[len("did_"):]
        if name in FIT_CHECK_SKIP or name == horizon:
            continue
        checks[name] = drop_errors(load(p), p.name, skip_errors, skipped)

    tables = {
        "pick_rate_did": prd,
        "flags": flags(prd, es, main, offer_rate, second),
        "weekly": weekly(es, prd, min_cell_offers),
        "dose_response": dose_response(prd, horizon_label),
        "robustness": robustness(checks, prd),
    }
    ant_path = analysis / "anticipation_main.parquet"
    if ant_path.exists():
        ant = load(ant_path)
        err = ant.status.astype(str) == "error"
        if err.any():
            ids = sorted(ant.card_patch_id[err])
            if not skip_errors:
                raise ExportError(f"{ant_path.name}: {len(ids)} tweak(s) with status "
                                  f"'error': {', '.join(ids)}. Fix or pass --skip-errors.")
            skipped.append(dict(table=ant_path.name, card_patch_ids=ids))
            ant = ant[~err]
        tables["anticipation"] = anticipation(ant, tw, _csv(ref / "beta_exposure.csv"))
    else:
        notes.append("anticipation.csv not written: anticipation_main.parquet not found")

    for name, df in tables.items():
        check_output(name, df)
    m = meta_info(db, snapshot_end, inputs, skipped, notes, horizon_label)
    m["sample"] = bool(sample)
    m["min_cell_offers"] = min_cell_offers

    out.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(out / f"{name}.csv", index=False, float_format="%.6g")
    stale = out / "anticipation.csv"
    if "anticipation" not in tables and stale.exists():
        stale.unlink()                       # don't leave an older run's table behind
    (out / "meta.json").write_text(json.dumps(m, indent=2) + "\n")
    tables["meta"] = m
    return tables


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--analysis", default="data/analysis")
    p.add_argument("--out", default="results")
    p.add_argument("--ref", default=str(REF))
    p.add_argument("--db", default=None, help="runs.duckdb (read-only) for meta.json")
    p.add_argument("--horizon", default="h3", help="fixed-horizon fit: did_<horizon>.parquet")
    p.add_argument("--skip-errors", action="store_true",
                   help="leave out fit rows with an error instead of stopping")
    p.add_argument("--snapshot-end", default=None,
                   help="override meta.json's snapshot end date (default: from --db)")
    p.add_argument("--min-cell-offers", type=int, default=10,
                   help="drop event-study cells with fewer treated offers")
    a = p.parse_args(argv)
    try:
        t = export(a.analysis, a.out, a.ref, a.db, a.horizon, a.skip_errors, a.snapshot_end,
                   a.min_cell_offers)
    except ExportError as e:
        sys.exit(f"export stopped: {e}")
    for name, df in t.items():
        if name != "meta":
            print(f"{name + '.csv':20s} {len(df):5d} rows")
    for n in t["meta"]["notes"]:
        print("note:", n)
    for s in t["meta"]["skipped"]:
        print(f"skipped ({s['table']}): {', '.join(s['card_patch_ids'])}")
    print(f"-> {a.out}/")


if __name__ == "__main__":
    main()
