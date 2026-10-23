"""The field guide's numbers table: every number the write-up prints, by key, from the saved
final-rerun outputs.

    python -m spirometry.numbers --analysis data/analysis --results results \
        --out writeup/numbers.json [--snapshot-log snapshot.log] [--ref reference]
        [--allow-sample]

Writes writeup/numbers.json (read by the Typst source: #n("key")) and writeup/numbers.csv
beside it (the same rows, for reading). One row per number:

    key        dotted lower-case name, e.g. dose.primary.h3.slope_first
    value      the number as computed (JSON number or string)
    text       the number as printed: decimals, ±, signs, thousands separators. Formatting
               happens here and nowhere else; negatives use the minus sign (U+2212).
    source     the file it came from
    column     the column and filter that produced it
    horizon    "weeks 0-3", "all weeks" or "" (not a fit)
    spec       which tweaks are on the dose line ("triage" = the notebooks' 38, "primary" =
               the 2026-10-09 spec; spirometry.sensitivity.SPECS), or ""
    build      the build stamp: tables built at, pages, parser version
    appendix   true for the rows the reproducibility appendix lists

Inputs (nothing else is read; the run database is never opened):

    results/meta.json                            build stamp, play-date range and build_info's
                                                 dedup counts (spirometry.export with --db)
    results/pick_rate_did.csv, dose_response.csv, flags.csv, anticipation.csv,
        robustness.csv                           the export's per-tweak and model tables
    <analysis>/writeup/                          spirometry.sensitivity: rulers, se_inflation,
                                                 calibrated_counts, dose_points, review_calls,
                                                 mixed, leave_out, character(_counts), power,
                                                 spread, placebo_by_horizon; spirometry.iv_sim:
                                                 iv_sim_single, _draws_summary, _weak, _broken,
                                                 _het, _confounding; spirometry.checks:
                                                 design_checks; spirometry.teaching_sims:
                                                 teaching_sims
    <analysis>/placebo_diagnostics_summary.csv, _vs_real.csv, _vs_real_by_patch.csv,
        _spread_by_feature.csv                   placebo calibration (final rerun)
    <analysis>/placebo_main.parquet              min_offers only (columns read: COLUMNS_READ)
    <analysis>/did_main.parquet, did_second_patch_checks.parquet,
        second_patch_checks_h3.parquet           notebook 02's saved fits (SE ratios, control
                                                 cards, the second patch's before-block checks)
    <analysis>/audit_summary.csv, audit_runs_per_build.csv
                                                 notebook 01's saved aggregates
    reference/tweak_sizes.csv, card_changes.csv
                                                 committed; exempt from the staleness check
    snapshot.log                                 the download log (scripts/snapshot_export.py):
                                                 last page and --count-only's records total.
                                                 Only three kinds of line are read (page
                                                 lines, "reached end of export", "total").
                                                 It predates the tables, so it is exempt from
                                                 the staleness check.

Guards (each stops the run and writes nothing):
- Build stamp: results/meta.json must carry tables_built_at_utc, snapshot_pages,
  parser_version, snapshot_start_date and snapshot_end_date. A sample export (meta.json
  "sample": true) is refused unless --allow-sample.
- Snapshot log: it must say "reached end of export" and have a "total" line, and its last
  page (numbered from 1) must equal meta.json's snapshot_pages.
- Calibrated counts: calibrated_counts.csv's uncalibrated rows (spread "none") must equal
  the counts from pick_rate_did.csv, so both use the same tweaks and rule.
- Staleness: an input file last modified before tables_built_at_utc was not made from these
  tables; the run names it.
- Privacy: every input table and the output pass spirometry.export.check_output
  (identifier columns, hashed-id-looking strings). Aggregates only.
- A value that is missing in its source stops the run (no blank numbers in the text).

Counting rules (as the export and SPIROMETRY.md define them):
- uncalibrated clearly nonzero (did.<h>.<patch>.uncalibrated.*) = |beta| > 2 clustered SE
  (export's clearly_nonzero / clearly_nonzero_h).
- calibrated clearly nonzero (did.<h>.<patch>.calibrated.*, the lead count by the decision
  log): |z / factor| > 2, factor = the patch's robust placebo sd at the same horizon;
  calibrated_plain_sd.* is the same with the plain placebo sd (sensitivity). Computed by
  spirometry.sensitivity.calibrated_counts; formatted here. A horizon without placebo fits
  has no keys and is listed under "missing" in numbers.json's build header.
- toward the change = export.toward_change (sign(beta) = sign(direction x ln ratio), for
  tweaks with one direction: not mixed, not upgrade-only), on beta for all weeks and on
  beta_h for weeks 0-3 (the export has no weeks 0-3 column for it).
- median |beta| in percentage points (beta x 100), all solo-estimable tweaks of the patch.
- Placebo spreads are all-weeks fits (placebo.fits / placebo.pairs); placebo.h3.* are the
  weeks 0-3 run's (placebo_by_horizon.csv), listed as missing until that run exists.

Key families added for the field guide (task A, 2026-10-16; writeup/OUTLINE.md):
- snapshot.distinct_runs (the audit's distinct (seed, start_time), the count the guide
  prints) with snapshot.distinct_runs_per_build_sum (the log's --count-only total, which
  counts a run under two build ids twice) and snapshot.runs_in_several_builds; the run stops
  if the audit's per-build sum and the log's total disagree. dedup.* from meta.json.
- audit.* (every row of notebook 01's audit_summary.csv), tweaks.* / changes.* (reference
  tables), const.honest.* (what honest errors give).
- tweak.<card>.<stable build>.*: one family per solo-estimable tweak (estimates in pp and
  log-odds at both horizons, z, calibrated z where the factor exists, rates and the hand 2x2,
  offers, SE ratios, flags, anticipation, placebo against real).
- se.*, flags.*, anticipation.*, robustness.*, second_patch.*, placebo.vs_real.*,
  placebo.spread.*, dose.triage.<h>.<model>.*, dose.example.*, dose.same_size.*, rulers.*,
  review.*, mixed.*, leave_out.*, character.*, power.*, spread.*, iv.* (simulation).
- checks.<check>.*: chapter 12's design checks (spirometry.checks); each row's spec column
  names its tables ("2,071-page tables" or "1,873-page tables"), as do checks.<check>.pages
  and checks.<check>.tables.

Added for the field guide rework (2026-10-22):
- toy.<toy>.<quantity>: every number of spirometry.teaching_sims' toy simulations, spec
  "simulation", formatted by the row's kind and decimals (toy_keys).
- did.hand_vs_model.*: how far the model's estimate is from the hand 2x2 DiD, in SEs, over
  the solo-estimable tweaks (all weeks; chapter 6).
"""
import argparse, datetime, json, math, pathlib, re, sys

import numpy as np
import pandas as pd

from spirometry.export import ExportError, check_output, toward_change

MINUS = "−"
KEY = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)*$")
HORIZONS = {"h3": "weeks 0-3", "all": "all weeks"}
HORIZON_KEY = {v: k for k, v in HORIZONS.items()}
SPREAD_KEY = {"robust sd": "calibrated", "sd": "calibrated_plain_sd"}
PATCHES = ["first", "second"]
COLUMNS = ["key", "value", "text", "source", "column", "horizon", "spec", "build",
           "appendix"]


class NumbersError(RuntimeError):
    pass


# -------------------------------------------------------------------------- formatting

def fmt_int(n):
    """2071 -> '2,071'."""
    return f"{int(n):,}".replace("-", MINUS)


def fmt_num(x, decimals=2, sign=False):
    """Fixed decimals, minus sign for negatives, '+' for positives when sign=True. A value
    that rounds to zero prints without a sign."""
    s = f"{abs(x):.{decimals}f}"
    if float(s) == 0:
        return s
    if x < 0:
        return MINUS + s
    return ("+" + s) if sign else s


def fmt_pm(x, se, decimals=2, sign=False):
    return f"{fmt_num(x, decimals, sign)} ± {fmt_num(se, decimals)}"


def fmt_pct(share, decimals=0):
    """0.715 -> '72%'."""
    return f"{fmt_num(100 * share, decimals)}%"


def fmt_time(iso):
    """'2026-10-09T21:18:20+00:00' -> '2026-10-09 21:18 UTC'."""
    t = datetime.datetime.fromisoformat(iso).astimezone(datetime.timezone.utc)
    return t.strftime("%Y-%m-%d %H:%M UTC")


# -------------------------------------------------------------------------------- rows

class Table:
    """Collects rows; refuses a bad key, a repeat or a missing value."""

    def __init__(self, build):
        self.build, self.rows = build, []

    def add(self, key, value, text, source, column, horizon="", spec="", appendix=False):
        if not KEY.match(key):
            raise NumbersError(f"bad key {key!r}: lower-case words joined by dots")
        if any(r["key"] == key for r in self.rows):
            raise NumbersError(f"key {key} defined twice")
        if value is None or (isinstance(value, float) and not math.isfinite(value)):
            raise NumbersError(f"{key}: value missing in {source} ({column})")
        if isinstance(value, (np.integer,)):
            value = int(value)
        elif isinstance(value, (np.floating,)):
            value = float(value)
        self.rows.append(dict(key=key, value=value, text=text, source=source, column=column,
                              horizon=horizon, spec=spec, build=self.build,
                              appendix=bool(appendix)))

    def estimate(self, key, est, se, decimals, source, column, sign=False, **kw):
        """Three keys: <key> (estimate), <key>_se, <key>_pm ('1.40 ± 0.19')."""
        self.add(key, est, fmt_num(est, decimals, sign), source, column, **kw)
        self.add(f"{key}_se", se, fmt_num(se, decimals), source, f"{column} (se)", **kw)
        self.add(f"{key}_pm", [float(est), float(se)], fmt_pm(est, se, decimals, sign),
                 source, f"{column} (estimate ± se)", **kw)

    def count(self, key, n, source, column, **kw):
        self.add(key, int(n), fmt_int(n), source, column, **kw)

    def frame(self):
        return pd.DataFrame(self.rows, columns=COLUMNS)


# ------------------------------------------------------------------------------ inputs

def _paths(analysis, results):
    a, r = pathlib.Path(analysis), pathlib.Path(results)
    w = a / "writeup"
    return {"meta": r / "meta.json",
            "pick_rate": r / "pick_rate_did.csv",
            "dose": r / "dose_response.csv",
            "flags": r / "flags.csv",
            "anticipation": r / "anticipation.csv",
            "robustness": r / "robustness.csv",
            "rulers": w / "rulers.csv",
            "se_inflation": w / "se_inflation.csv",
            "calibrated": w / "calibrated_counts.csv",
            "dose_points": w / "dose_points.csv",
            "review_calls": w / "review_calls.csv",
            "mixed": w / "mixed.csv",
            "leave_out": w / "leave_out.csv",
            "character": w / "character.csv",
            "character_counts": w / "character_counts.csv",
            "power": w / "power.csv",
            "spread": w / "spread.csv",
            "placebo_by_horizon": w / "placebo_by_horizon.csv",
            "design_checks": w / "design_checks.csv",
            "teaching_sims": w / "teaching_sims.csv",
            "iv_single": w / "iv_sim_single.csv",
            "iv_draws": w / "iv_sim_draws_summary.csv",
            "iv_weak": w / "iv_sim_weak.csv",
            "iv_broken": w / "iv_sim_broken.csv",
            "iv_het": w / "iv_sim_het.csv",
            "iv_confounding": w / "iv_sim_confounding.csv",
            "placebo": a / "placebo_diagnostics_summary.csv",
            "vs_real": a / "placebo_diagnostics_vs_real.csv",
            "vs_real_by_patch": a / "placebo_diagnostics_vs_real_by_patch.csv",
            "spread_by_feature": a / "placebo_diagnostics_spread_by_feature.csv",
            "audit": a / "audit_summary.csv",
            "audit_builds": a / "audit_runs_per_build.csv",
            "did_main": a / "did_main.parquet",
            "second_checks": a / "did_second_patch_checks.parquet",
            "second_checks_h3": a / "second_patch_checks_h3.parquet",
            "placebo_fits": a / "placebo_main.parquet"}


# Committed reference tables (exempt from the staleness check, like snapshot.log).
REFERENCE = {"tweak_sizes": "tweak_sizes.csv", "card_changes": "card_changes.csv"}


# Columns read from a parquet input, where the file holds more than the keys need (the
# placebo fits carry their random `seed`, a column name the privacy check refuses).
COLUMNS_READ = {"placebo_main.parquet": ["min_offers", "error"]}


def _read(p):
    if p.suffix == ".parquet":
        return pd.read_parquet(p, columns=COLUMNS_READ.get(p.name))
    return pd.read_csv(p)


def read_stamp(meta, allow_sample=False):
    """The build stamp from results/meta.json; refuses a blank stamp or a sample export."""
    if meta.get("sample") and not allow_sample:
        raise NumbersError("results/meta.json is a sample export (sample: true); "
                           "pass --allow-sample to build from it")
    need = ["tables_built_at_utc", "snapshot_pages", "parser_version",
            "snapshot_start_date", "snapshot_end_date"]
    blank = [k for k in need if not str(meta.get(k, "")).strip()]
    if blank:
        raise NumbersError(f"results/meta.json has no build stamp or play dates "
                           f"({', '.join(blank)} blank): rerun spirometry.export with --db")
    built = datetime.datetime.fromisoformat(meta["tables_built_at_utc"])
    if built.tzinfo is None:
        raise NumbersError("tables_built_at_utc has no time zone")
    return built


def check_fresh(paths, built):
    """Every input must be at least as new as the tables it was computed from."""
    old = []
    for p in paths:
        t = datetime.datetime.fromtimestamp(p.stat().st_mtime, datetime.timezone.utc)
        if t < built:
            old.append(f"{p} (modified {t.isoformat(timespec='seconds')})")
    if old:
        raise NumbersError(f"input(s) older than the run tables (built "
                           f"{built.isoformat(timespec='seconds')}): {'; '.join(old)}")


PAGE_LINE = re.compile(r"\bpage (\d+): \d+ runs\b")
TOTAL_LINE = re.compile(r"^total\s+(\d+)\s+(\d+)\s*$")


def read_snapshot_log(path):
    """(last page, records, per-build distinct) from the download log: the last "page N:
    ... runs" line (the log numbers pages from 1, so N is the page count; files are 0 ..
    N-1) and --count-only's "total" line: records (repeats included) and its "dedup" column,
    distinct (seed, start_time) counted within each build and summed over builds (so a run
    recorded under two build ids counts twice; the audit's distinct_runs counts it once).
    Refuses a log without "reached end of export"."""
    last = records = distinct = None
    end = False
    for line in pathlib.Path(path).read_text().splitlines():
        m = PAGE_LINE.search(line)
        if m:
            last = int(m.group(1))
        elif "reached end of export" in line:
            end = True
        else:
            m = TOTAL_LINE.match(line.strip())
            if m:
                records, distinct = int(m.group(1)), int(m.group(2))
    if not end:
        raise NumbersError(f"{path}: no 'reached end of export' line (snapshot unfinished)")
    if last is None or records is None:
        raise NumbersError(f"{path}: no page lines or no 'total' line")
    return last, records, distinct


def private(name, df):
    """spirometry.export's privacy check, as a NumbersError."""
    try:
        check_output(name, df)
    except ExportError as e:
        raise NumbersError(f"privacy check: {e}") from None


def load(analysis="data/analysis", results="results", allow_sample=False,
         snapshot_log="snapshot.log", ref="reference"):
    """Read and check every input. Returns (meta, built, tables, paths, log)."""
    paths = _paths(analysis, results)
    refs = {k: pathlib.Path(ref) / f for k, f in REFERENCE.items()}
    missing = [str(p) for p in [*paths.values(), *refs.values(), pathlib.Path(snapshot_log)]
               if not p.exists()]
    if missing:
        raise NumbersError(f"missing input(s): {', '.join(missing)}")
    meta = json.loads(paths["meta"].read_text())
    built = read_stamp(meta, allow_sample)
    check_fresh(paths.values(), built)
    tables = {}
    for name, p in [*paths.items(), *refs.items()]:
        if name == "meta":
            continue
        df = _read(p) if name not in REFERENCE else pd.read_csv(p, dtype=str,
                                                                  keep_default_na=False)
        private(str(p), df)
        tables[name] = df
    paths.update(refs)
    last, records, distinct = read_snapshot_log(snapshot_log)
    if str(last) != str(meta["snapshot_pages"]).strip():
        raise NumbersError(f"{snapshot_log} ends at page {last}, results/meta.json says "
                           f"{meta['snapshot_pages']} pages")
    return meta, built, tables, paths, dict(last_page=last, records=records,
                                            distinct_per_build=distinct)


# ------------------------------------------------------------------------------- keys

def _one(df, source, **where):
    """The single row of `df` matching `where`; refuses none or several."""
    m = pd.Series(True, index=df.index)
    for c, v in where.items():
        m &= df[c].astype(str) == str(v)
    if m.sum() != 1:
        raise NumbersError(f"{source}: {int(m.sum())} rows match {where}, expected 1")
    return df[m].iloc[0]


def _filter(where):
    return ", ".join(f"{c} = {v}" for c, v in where.items())


def provenance_keys(T, meta, src, log, src_log):
    T.add("build.tables_built_at", meta["tables_built_at_utc"],
          fmt_time(meta["tables_built_at_utc"]), src, "tables_built_at_utc", appendix=True)
    T.add("build.parser_version", str(meta["parser_version"]), str(meta["parser_version"]),
          src, "parser_version", appendix=True)
    T.count("snapshot.pages", int(meta["snapshot_pages"]), src, "snapshot_pages",
            appendix=True)
    T.count("snapshot.last_page", log["last_page"], src_log,
            "last 'page N: ... runs' line (pages numbered from 1; files 0 to N-1)",
            appendix=True)
    T.count("snapshot.records", log["records"], src_log,
            "'total' line, first column (records read, repeats included)", appendix=True)
    for k in ["start", "end"]:
        T.add(f"snapshot.{k}_date", meta[f"snapshot_{k}_date"], meta[f"snapshot_{k}_date"],
              src, f"snapshot_{k}_date ({meta.get('snapshot_dates_source', '')})",
              appendix=True)
    if str(meta.get("exported_at_utc", "")).strip():
        T.add("build.results_exported_at", meta["exported_at_utc"],
              fmt_time(meta["exported_at_utc"]), src, "exported_at_utc", appendix=True)


def did_keys(T, p, src):
    """Tweak counts, uncalibrated clearly nonzero (clustered SE), toward the change and
    median |beta|, per patch and horizon. Returns the counts, for the check against
    calibrated_counts.csv's uncalibrated rows."""
    counts = {}
    T.count("tweaks.solo_estimable", len(p), src, "rows")
    for pt in PATCHES:
        T.count(f"tweaks.{pt}", (p.patch == pt).sum(), src, f"rows, patch = {pt}")
    single = (p.mixed_direction != "yes") & (p.upgrade_only != "yes")
    for hz, (b, s, cn) in {"all": ("beta", "se", "clearly_nonzero"),
                           "h3": ("beta_h", "se_h", "clearly_nonzero_h")}.items():
        horizon = HORIZONS[hz]
        toward = pd.Series(toward_change(p[b], p.dose_x, single), index=p.index)
        for pt in PATCHES:
            g = p.patch == pt
            clear = g & (p[cn] == "yes")
            n = dict(n_clearly_nonzero=int(clear.sum()),
                     n_clearly_nonzero_with_direction=int((clear & (toward != "")).sum()),
                     n_toward=int((clear & (toward == "yes")).sum()))
            counts[(horizon, pt)] = n
            pre = f"did.{hz}.{pt}.uncalibrated"
            what = f"uncalibrated: {cn} = yes (|{b}| > 2 clustered {s}), patch = {pt}"
            T.count(f"{pre}.clearly_nonzero", n["n_clearly_nonzero"], src, what,
                    horizon=horizon)
            T.count(f"{pre}.clearly_nonzero_with_direction",
                    n["n_clearly_nonzero_with_direction"], src,
                    f"{what}; not mixed, not upgrade-only", horizon=horizon)
            T.count(f"{pre}.clearly_nonzero_toward", n["n_toward"], src,
                    f"{what}; export.toward_change({b}) = yes", horizon=horizon)
            med = 100 * p.loc[g, b].abs().median()
            T.add(f"did.{hz}.{pt}.median_abs_beta_pp", med, fmt_num(med, 1), src,
                  f"median |{b}| x 100, patch = {pt}", horizon=horizon)
    return counts


def calibrated_keys(T, c, src, uncalibrated):
    """Clearly nonzero on placebo-scaled z (calibrated_counts.csv), per patch, horizon and
    spread. Checks the file's uncalibrated rows against pick_rate_did.csv's counts. Returns
    the keys left out (no placebo fits at that horizon), with the reason."""
    missing = []
    for r in c.itertuples():
        hz = HORIZON_KEY.get(r.horizon)
        if hz is None:
            raise NumbersError(f"{src}: unknown horizon {r.horizon!r}")
        if r.spread == "none":
            mine = uncalibrated.get((r.horizon, r.patch))
            theirs = dict(n_clearly_nonzero=r.n_clearly_nonzero,
                          n_clearly_nonzero_with_direction=r.n_clearly_nonzero_with_direction,
                          n_toward=r.n_toward)
            if mine is None or any(int(theirs[k]) != v for k, v in mine.items()):
                raise NumbersError(f"{src}: uncalibrated counts ({r.horizon}, {r.patch}) "
                                   f"{theirs} differ from pick_rate_did.csv's {mine}")
            continue
        pre = f"did.{hz}.{r.patch}.{SPREAD_KEY[r.spread]}"
        if r.status != "ok":
            missing.append(dict(keys=f"{pre}.*", reason=str(r.status)))
            continue
        w = f"horizon = {r.horizon}, patch = {r.patch}, spread = {r.spread}"
        kw = dict(horizon=r.horizon)
        T.add(f"{pre}.factor", float(r.factor), fmt_num(r.factor, 2), src, f"factor, {w}",
              **kw)
        T.count(f"{pre}.n_placebo", r.n_placebo, src, f"n_placebo (window, pseudo card "
                f"pairs), {w}", **kw)
        T.count(f"{pre}.n_tweaks", r.n_tweaks, src, f"n_tweaks, {w}", **kw)
        T.count(f"{pre}.clearly_nonzero", r.n_clearly_nonzero, src,
                f"n_clearly_nonzero (|z / factor| > 2), {w}", **kw)
        T.count(f"{pre}.clearly_nonzero_with_direction", r.n_clearly_nonzero_with_direction,
                src, f"n_clearly_nonzero_with_direction, {w}", **kw)
        T.count(f"{pre}.clearly_nonzero_toward", r.n_toward, src, f"n_toward, {w}", **kw)
    return missing


def dose_keys(T, dose, rulers, se_inf, src_dose, src_rulers, src_se):
    """Dose-response slopes: the notebooks' 38 (triage spec) from the export, the primary
    spec from spirometry.sensitivity, and the primary spec with placebo-scaled SEs."""
    for hz, label in [("h3", "weeks 0-3"), ("all", "all weeks")]:
        for term, name in [("slope_first", "slope_first"), ("slope_second", "slope_second")]:
            w = dict(horizon=label, model="slope per patch", term=term)
            r = _one(dose, src_dose, **w)
            T.estimate(f"dose.triage.{hz}.{name}", r.coef, r.se, 2, src_dose,
                       f"coef, {_filter(w)}", horizon=label, spec="triage")
        w = dict(horizon=label, model="one slope", term="slope")
        r = _one(dose, src_dose, **w)
        T.estimate(f"dose.triage.{hz}.one_slope", r.coef, r.se, 2, src_dose,
                   f"coef, {_filter(w)}", horizon=label, spec="triage")
        T.count(f"dose.triage.{hz}.n_tweaks", r.n_tweaks, src_dose,
                f"n_tweaks, {_filter(w)}", horizon=label, spec="triage")

    for spec in ["triage", "primary"]:
        w = dict(fits="did_h3", spec=spec, ruler="ln(new/old)")
        r = _one(rulers, src_rulers, **w)
        kw = dict(horizon="weeks 0-3", spec=spec)
        if spec == "primary":
            T.estimate("dose.primary.h3.slope_first", r.slope1, r.se1, 2, src_rulers,
                       f"slope1, {_filter(w)}", **kw)
            T.estimate("dose.primary.h3.slope_second", r.slope2, r.se2, 2, src_rulers,
                       f"slope2, {_filter(w)}", **kw)
            T.count("dose.primary.h3.n_first", r.n1, src_rulers, f"n1, {_filter(w)}", **kw)
            T.count("dose.primary.h3.n_second", r.n2, src_rulers, f"n2, {_filter(w)}", **kw)
        T.add(f"dose.{spec}.h3.z_diff", float(r.z_diff), fmt_num(r.z_diff, 2), src_rulers,
              f"z_diff, {_filter(w)}", **kw)

    for setting, name in [("robust sd by patch", "placebo_robust_sd"),
                          ("sd by patch", "placebo_sd")]:
        w = dict(label="primary, weeks 0-3 (did_h3)", setting=setting)
        r = _one(se_inf, src_se, **w)
        kw = dict(horizon="weeks 0-3", spec="primary")
        T.estimate(f"dose.primary.h3.{name}.slope_first", r.slope1, r.se1, 2, src_se,
                   f"slope1, {_filter(w)}", **kw)
        T.estimate(f"dose.primary.h3.{name}.slope_second", r.slope2, r.se2, 2, src_se,
                   f"slope2, {_filter(w)}", **kw)
        T.add(f"dose.primary.h3.{name}.z_diff", float(r.z_diff), fmt_num(r.z_diff, 2),
              src_se, f"z_diff, {_filter(w)}", **kw)
        for i, pt in [(1, "first"), (2, "second")]:
            f = float(r[f"factor{i}"])
            T.add(f"dose.primary.h3.{name}.factor_{pt}", f, fmt_num(f, 2), src_se,
                  f"factor{i}, {_filter(w)}", **kw)


def placebo_keys(T, pl, src):
    """Spread of placebo z (honest errors: sd 1), every fit and one row per (window,
    pseudo card) pair."""
    kw = dict(horizon="all weeks")
    for dedupe, tag in [(False, "fits"), (True, "pairs")]:
        d = pl[pl.dedupe.astype(str).str.lower() == str(dedupe).lower()]
        for split, level in [("all", "all"), ("patch", "first"), ("patch", "second")]:
            w = dict(dedupe=dedupe, split=split, level=level)
            r = _one(d, src, split=split, level=level)
            name = "all" if level == "all" else level
            T.add(f"placebo.{tag}.{name}.sd_z", float(r.sd_z), fmt_num(r.sd_z, 2), src,
                  f"sd_z, {_filter(w)}", **kw)
            T.add(f"placebo.{tag}.{name}.robust_sd_z", float(r.robust_sd_z),
                  fmt_num(r.robust_sd_z, 2), src, f"robust_sd_z, {_filter(w)}", **kw)
            T.add(f"placebo.{tag}.{name}.share_abs_z_gt2", float(r.share_abs_z_gt2),
                  fmt_pct(r.share_abs_z_gt2), src, f"share_abs_z_gt2, {_filter(w)}", **kw)
            T.count(f"placebo.{tag}.{name}.n", r.n_fits, src, f"n_fits, {_filter(w)}", **kw)


# ----------------------------------------------------------------- field guide, task A
# Keys for every chapter of writeup/OUTLINE.md whose numbers are in saved outputs.

def slug(s):
    """'Leading Strike +1' -> 'leading_strike_1'; a key part from any label."""
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", str(s).lower())).strip("_")


def tweak_prefix(cpid):
    """'PARRY@v0.103.2/patch' -> 'tweak.parry.v0_103_2'."""
    card, rest = cpid.split("@", 1)
    return f"tweak.{slug(card)}.{slug(rest.split('/')[0])}"


def _fin(v):
    try:
        return v is not None and math.isfinite(float(v))
    except (TypeError, ValueError):
        return False


# formatting by kind: (decimals, sign, scale, percent)
KINDS = {"count": None, "estimate": (2, True, 1, False), "z": (2, True, 1, False),
         "share": (0, False, 100, True), "corr": (2, True, 1, False),
         "factor": (2, False, 1, False), "number": (3, False, 1, False)}


def add_kind(T, key, value, kind, source, column, se=None, **kw):
    """One number formatted by its kind; an estimate with an se becomes three keys."""
    if kind == "count":
        T.count(key, round(float(value)), source, column, **kw)
        return
    d, sign, scale, pct = KINDS[kind]
    if pct:
        T.add(key, float(value), fmt_pct(value, d), source, column, **kw)
    elif kind == "estimate" and _fin(se):
        T.estimate(key, float(value) * scale, float(se) * scale, d, source, column, sign=sign,
                   **kw)
    else:
        T.add(key, float(value) * scale, fmt_num(float(value) * scale, d, sign), source,
              column, **kw)


CONSTANTS = [  # (key, value, text, meaning) for errors that are honest (z ~ N(0, 1))
    ("const.honest.share_abs_z_gt2", math.erfc(2 / math.sqrt(2)), 1,
     "share of |z| > 2 under N(0, 1): 2 (1 - Phi(2))"),
    ("const.honest.share_abs_z_gt3", math.erfc(3 / math.sqrt(2)), 1,
     "share of |z| > 3 under N(0, 1)"),
    ("const.honest.median_abs_z", 0.6744897501960817, 2, "median |z| under N(0, 1)"),
    ("const.honest.sd_z", 1.0, 0, "sd of z under N(0, 1)"),
]


def constant_keys(T):
    for key, v, d, what in CONSTANTS:
        if "share" in key:
            T.add(key, v, fmt_pct(v, d), "normal distribution", what)
        else:
            T.add(key, v, fmt_num(v, d), "normal distribution", what)
    # The tables the triage ran on, for labelling numbers measured there (field guide task B)
    from spirometry.checks import TRIAGE_PAGES
    T.count("const.earlier_tables.pages", TRIAGE_PAGES, "spirometry.checks",
            "TRIAGE_PAGES: pages of the run tables of 2026-10-02 (triage/TRIAGE.md)")


def snapshot_extra_keys(T, audit, log, src_audit, src_log, meta, src_meta, missing):
    """Distinct runs (the audit's count, decision of 2026-10-16) with the download log's
    per-build sum beside it; build_info's dedup counts from meta.json."""
    a = audit.set_index("key")
    T.count("snapshot.distinct_runs", a.loc["distinct_runs", "value"], src_audit,
            "distinct_runs: distinct (seed, start_time) over all builds")
    T.count("snapshot.distinct_runs_per_build_sum", log["distinct_per_build"], src_log,
            "'total' line, second column (dedup): distinct (seed, start_time) within each "
            "build, summed over builds")
    T.count("snapshot.runs_in_several_builds", a.loc["run_keys_in_several_builds", "value"],
            src_audit, "run_keys_in_several_builds")
    if int(a.loc["distinct_runs_per_build_sum", "value"]) != int(log["distinct_per_build"]):
        raise NumbersError(f"{src_audit} distinct_runs_per_build_sum "
                           f"{int(a.loc['distinct_runs_per_build_sum', 'value'])} differs from "
                           f"{src_log}'s dedup total {log['distinct_per_build']}")
    dedup = meta.get("dedup") or {}
    from spirometry.export import DEDUP_FIELDS
    for k in DEDUP_FIELDS:
        if k in dedup:
            T.count(f"dedup.{k}", dedup[k], src_meta, f"dedup.{k} (build_info)",
                    appendix=False)
    lost = [k for k in DEDUP_FIELDS if k not in dedup]
    if lost:
        missing.append(dict(keys="dedup." + "{" + ",".join(lost) + "}",
                            reason="not in results/meta.json: rerun spirometry.export --db"))


AUDIT_UNITS = {"count": "count", "share": "share1", "days": "days", "z": "z", "corr": "corr",
               "rate": "rate"}


def audit_keys(T, audit, builds, src, src_builds):
    """Every row of notebook 01's audit_summary.csv as audit.<key>; rates also as a
    percent (<key>_pct); the thin builds as a list."""
    for r in audit.itertuples():
        col = f"{r.key}: {r.definition} [{r.population}]"
        v = float(r.value)
        if r.unit == "count":
            T.count(f"audit.{r.key}", v, src, col)
        elif r.unit == "share":
            T.add(f"audit.{r.key}", v, fmt_pct(v, 1), src, col)
        elif r.unit == "days":
            T.add(f"audit.{r.key}", v, fmt_num(v, 1), src, col)
        elif r.unit in ("z", "corr"):
            T.add(f"audit.{r.key}", v, fmt_num(v, 2), src, col)
        elif r.unit == "rate":
            T.add(f"audit.{r.key}", v, fmt_num(v, 3, sign="gap" in r.key), src, col)
            T.add(f"audit.{r.key}_pct", v, fmt_pct(v, 1), src, col + " (percent)")
        else:
            raise NumbersError(f"{src}: unknown unit {r.unit!r} for {r.key}")
    thin = builds[builds.thin.astype(str).str.lower() == "true"].build_id.tolist()
    text = (", ".join(thin[:-1]) + " and " + thin[-1]) if len(thin) > 1 else "".join(thin)
    T.add("audit.thin_builds_list", " ".join(thin), text or "none", src_builds,
          "build_id where thin (primary runs < MIN_RUNS), in version order")


def reference_keys(T, tw, cc, src_tw, src_cc):
    """Ch 0: the numeric tweaks and the card-patches by kind (committed reference tables)."""
    T.count("tweaks.numeric", len(tw), src_tw, "rows (numeric tweaks, card-patch level)")
    T.count("tweaks.not_solo_estimable", (tw.solo_estimable != "yes").sum(), src_tw,
            "solo_estimable != yes")
    s = tw[tw.solo_estimable == "yes"]
    T.count("tweaks.upgrade_only", (s.upgrade_only == "yes").sum(), src_tw,
            "solo-estimable, upgrade_only = yes")
    T.count("tweaks.mixed_direction", (s.mixed_direction == "yes").sum(), src_tw,
            "solo-estimable, mixed_direction = yes")
    T.count("tweaks.single_direction", ((s.upgrade_only != "yes")
                                        & (s.mixed_direction != "yes")).sum(), src_tw,
            "solo-estimable, neither mixed nor upgrade-only (the notebooks' dose line)")
    cp = cc.groupby(["card_id", "stable_build"]).change_kind.agg(
        lambda k: "+".join(sorted(set("+".join(k).split("+")))))
    T.count("changes.card_patches", len(cp), src_cc, "distinct (card_id, stable_build)")
    for kind in ["tweak", "rework", "mechanic", "text_only", "cost_change", "rarity_change",
                 "artifact", "added", "removed"]:
        n = cp.map(lambda k: kind in k.split("+")).sum()
        T.count(f"changes.{kind}", n, src_cc,
                f"card-patches whose change_kind includes {kind}")
    T.count("changes.tweak_only", (cp == "tweak").sum(), src_cc,
            "card-patches with change_kind exactly tweak (the numeric-tweak set)")


def tweak_keys(T, p, main, flags, ant, vs_real, sec_h3, cal, src):
    """Per tweak, tweak.<card>.<stable build>.*: estimates at both horizons (pp, log-odds,
    z, interval, calibrated z where the placebo factor exists), the before/after rates and
    the hand 2x2, offers, SE ratios, control cards, flags, anticipation and placebo-vs-real.
    A field blank in its source gets no key (e.g. the upgrade-only placebo of other
    tweaks)."""
    m = main.reset_index() if "card_patch_id" not in main.columns else main
    m = m.set_index("card_patch_id")
    fl, an, vr = (flags.set_index("card_patch_id"), ant.set_index("card_patch_id"),
                  vs_real.set_index("card_patch_id"))
    sh = sec_h3[sec_h3.variant == "pooled before"].set_index("card_patch_id")
    fac = {(r.horizon, r.patch): float(r.factor) for r in cal.itertuples()
           if r.spread == "robust sd" and r.status == "ok"}
    for r in p.itertuples():
        k = tweak_prefix(r.card_patch_id)
        T.add(f"{k}.card_id", r.card_id, r.card_id, src["pick_rate"], "card_id")
        for c in ["old", "new", "main_field", "upgrade_old", "upgrade_new", "change"]:
            v = getattr(r, c)
            if isinstance(v, str) and v or _fin(v):
                txt = str(v) if isinstance(v, str) else fmt_num(float(v), 0)
                T.add(f"{k}.{c}", txt, txt, src["pick_rate"], c)
        for c, d in [("log_ratio", 3), ("dose_x", 3)]:
            if _fin(getattr(r, c)):
                T.add(f"{k}.{c}", float(getattr(r, c)), fmt_num(getattr(r, c), d, True),
                      src["pick_rate"], c)
        for hz, b, se, lo, hi, blo, selo, horizon in [
                ("all", "beta", "se", "ci_lo", "ci_hi", "beta_lo", "se_lo", "all weeks"),
                ("h3", "beta_h", "se_h", "ci_lo_h", "ci_hi_h", "beta_lo_h", "se_lo_h",
                 "weeks 0-3")]:
            bv, sv = getattr(r, b), getattr(r, se)
            if not (_fin(bv) and _fin(sv)):
                continue
            kw = dict(horizon=horizon)
            T.estimate(f"{k}.{hz}.beta_pp", 100 * bv, 100 * sv, 1, src["pick_rate"],
                       f"{b} x 100", sign=True, **kw)
            for c, nm in [(lo, "ci_lo_pp"), (hi, "ci_hi_pp")]:
                T.add(f"{k}.{hz}.{nm}", 100 * getattr(r, c),
                      fmt_num(100 * getattr(r, c), 1, True), src["pick_rate"], f"{c} x 100",
                      **kw)
            T.add(f"{k}.{hz}.z", bv / sv, fmt_num(bv / sv, 1, True), src["pick_rate"],
                  f"{b} / {se}", **kw)
            if _fin(getattr(r, blo)):
                T.estimate(f"{k}.{hz}.beta_lo", getattr(r, blo), getattr(r, selo), 2,
                           src["pick_rate"], blo, sign=True, **kw)
            f = fac.get((horizon, r.patch))
            if f:
                T.add(f"{k}.{hz}.z_calibrated", bv / sv / f, fmt_num(bv / sv / f, 1, True),
                      src["calibrated"], f"{b} / {se} / the patch's robust placebo sd ({f:.3f})",
                      **kw)
        kw = dict(horizon="all weeks")
        for c in ["treated_rate_before", "treated_rate_after", "control_rate_before",
                  "control_rate_after"]:
            T.add(f"{k}.{c}", float(getattr(r, c)), fmt_pct(getattr(r, c), 1),
                  src["pick_rate"], c, **kw)
        tb, ta, cb, ca = (r.treated_rate_before, r.treated_rate_after, r.control_rate_before,
                          r.control_rate_after)
        for nm, v in [("treated_change_pp", 100 * (ta - tb)), ("control_change_pp", 100 * (ca - cb)),
                      ("did_raw_pp", 100 * ((ta - tb) - (ca - cb)))]:
            T.add(f"{k}.{nm}", v, fmt_num(v, 1, True), src["pick_rate"],
                  "x 100 of: treated after - before" if nm.startswith("treated") else
                  "x 100 of: control after - before" if nm.startswith("control") else
                  "x 100 of: (treated after - before) - (control after - before)", **kw)
        T.add(f"{k}.treated_relative_change", ta / tb - 1, fmt_pct(ta / tb - 1, 0),
              src["pick_rate"], "treated_rate_after / treated_rate_before - 1", **kw)
        T.count(f"{k}.n_treated_offers", r.n_treated_offers, src["pick_rate"],
                "n_treated_offers", **kw)
        T.add(f"{k}.se_over_robust", r.se / r.se_hc, fmt_num(r.se / r.se_hc, 2),
              src["pick_rate"], "se / se_hc (clustered / heteroskedasticity-robust)", **kw)
        if r.card_patch_id in m.index:
            mm = m.loc[r.card_patch_id]
            T.add(f"{k}.se_over_iid", mm.se / mm.se_iid, fmt_num(mm.se / mm.se_iid, 2),
                  src["did_main"], "se / se_iid", **kw)
            for c in ["n_control_cards", "n_singletons_dropped", "n_offers", "n_runs"]:
                T.count(f"{k}.{c}", mm[c], src["did_main"], c, **kw)
        if r.card_patch_id in fl.index:
            f_ = fl.loc[r.card_patch_id]
            if _fin(f_.offer_share_vs_controls):
                T.add(f"{k}.offer_share_vs_controls", f_.offer_share_vs_controls,
                      fmt_num(f_.offer_share_vs_controls, 3, True), src["flags"],
                      "offer_share_vs_controls (log share ratio minus the controls' median)")
            for c, nm in [("offer_rate_z_binom", "offer_rate_z"),
                          ("offer_rate_z_binom_rarity", "offer_rate_z_rarity")]:
                if _fin(f_[c]):
                    T.add(f"{k}.{nm}", f_[c], fmt_num(f_[c], 1, True), src["flags"], c)
            for c in ["offer_rate_flag", "offer_rate_flag_rarity"]:
                if isinstance(f_[c], str) and f_[c]:
                    T.add(f"{k}.{c}", f_[c], f_[c], src["flags"], c)
            for b, se, nm in [("pretrend_slope", "pretrend_slope_se", "pretrend_slope_pp"),
                              ("placebo_beta", "placebo_se", "placebo_beta_pp"),
                              ("pooled_before_beta", "pooled_before_se", "all.pooled_before_beta_pp"),
                              ("no_first_patch_controls_beta", "no_first_patch_controls_se",
                               "all.no_first_patch_controls_beta_pp")]:
                if _fin(f_[b]) and _fin(f_[se]):
                    T.estimate(f"{k}.{nm}", 100 * f_[b], 100 * f_[se], 2 if "pretrend" in b else 1,
                               src["flags"], f"{b} x 100" + (" per week" if "pretrend" in b else ""),
                               sign=True)
        if r.card_patch_id in sh.index:
            q = sh.loc[r.card_patch_id]
            if _fin(q.beta) and _fin(q.se):
                T.estimate(f"{k}.h3.pooled_before_beta_pp", 100 * q.beta, 100 * q.se, 1,
                           src["second_checks_h3"], "beta x 100, variant = pooled before",
                           sign=True, horizon="weeks 0-3")
        if r.card_patch_id in an.index:
            a_ = an.loc[r.card_patch_id]
            T.add(f"{k}.anticipation.status", a_.status, a_.status, src["anticipation"],
                  "status")
            if _fin(a_.beta_postbeta) and _fin(a_.se):
                T.estimate(f"{k}.anticipation.beta_postbeta_pp", 100 * a_.beta_postbeta,
                           100 * a_.se, 1, src["anticipation"], "beta_postbeta x 100",
                           sign=True)
            if _fin(a_.ratio_to_main):
                T.add(f"{k}.anticipation.ratio_to_main", a_.ratio_to_main,
                      fmt_num(a_.ratio_to_main, 2, True), src["anticipation"], "ratio_to_main")
            if _fin(a_.lead_days):
                T.count(f"{k}.anticipation.lead_days", a_.lead_days, src["anticipation"],
                        "lead_days")
        if r.card_patch_id in vr.index:
            v_ = vr.loc[r.card_patch_id]
            for c, nm, d in [("empirical_p", "empirical_p", 2),
                             ("calibrated_z", "all.z_calibrated_window", 1)]:
                if _fin(v_[c]):
                    T.add(f"{k}.{nm}", v_[c], fmt_num(v_[c], d, nm != "empirical_p"),
                          src["vs_real"], c, horizon="all weeks")
            T.count(f"{k}.n_placebo_window", v_.n_placebo, src["vs_real"], "n_placebo",
                    horizon="all weeks")


def _ratio_stats(T, key, r, source, column, **kw):
    r = r[np.isfinite(r)]
    for nm, v in [("median", r.median()), ("min", r.min()), ("max", r.max())]:
        T.add(f"{key}.{nm}", float(v), fmt_num(v, 2), source, f"{nm} of {column}", **kw)


def se_keys(T, p, main, src_p, src_m):
    """Ch 6: clustered against robust and iid SEs over the solo-estimable tweaks; the
    singletons pyfixest dropped."""
    _ratio_stats(T, "se.clustered_over_robust", p.se / p.se_hc, src_p, "se / se_hc",
                 horizon="all weeks")
    m = main[main.error.fillna("") == ""]
    _ratio_stats(T, "se.clustered_over_iid", m.se / m.se_iid, src_m, "se / se_iid",
                 horizon="all weeks")
    T.count("did.singletons_dropped.total", m.n_singletons_dropped.sum(), src_m,
            "sum of n_singletons_dropped", horizon="all weeks")
    T.count("did.singletons_dropped.max", m.n_singletons_dropped.max(), src_m,
            "max of n_singletons_dropped", horizon="all weeks")
    T.count("did.singletons_dropped.n_tweaks", (m.n_singletons_dropped > 0).sum(), src_m,
            "tweaks with n_singletons_dropped > 0", horizon="all weeks")
    # field guide rework: the model against the hand 2x2 (chapter 6), in units of the SE
    hand = ((p.treated_rate_after - p.treated_rate_before)
            - (p.control_rate_after - p.control_rate_before))
    gap = ((p.beta - hand).abs() / p.se).dropna()
    col = "|beta - ((treated after - before) - (control after - before))| / se"
    for nm, v in [("median_gap_se", gap.median()), ("max_gap_se", gap.max())]:
        T.add(f"did.hand_vs_model.{nm}", float(v), fmt_num(v, 2), src_p, f"{nm[:3]} of {col}",
              horizon="all weeks")
    T.count("did.hand_vs_model.n_tweaks", len(gap), src_p, f"tweaks with {col}",
            horizon="all weeks")


def false_alarm_keys(T, p, src):
    """Ch 4: false alarms expected among the tweaks at |z| > 2 if every effect were zero
    and the errors honest."""
    share = math.erfc(2 / math.sqrt(2))
    for name, g in [("all", p)] + [(pt, p[p.patch == pt]) for pt in PATCHES]:
        v = len(g) * share
        T.add(f"did.expected_false_alarms.{name}", v, fmt_num(v, 1), src,
              f"rows{'' if name == 'all' else f', patch = {name}'} x 2 (1 - Phi(2))")


def flag_keys(T, flags, src):
    """Ch 7: offer-rate flags (all controls, same rarity), by patch and overall."""
    for name, g in [("all", flags)] + [(pt, flags[flags.patch == pt]) for pt in PATCHES]:
        for c, nm in [("offer_rate_flag", "n_flagged"),
                      ("offer_rate_flag_rarity", "n_flagged_rarity")]:
            T.count(f"flags.offer_rate.{name}.{nm}", (g[c] == "yes").sum(), src,
                    f"{c} = yes" + ("" if name == "all" else f", patch = {name}"))
        T.count(f"flags.pretrend.{name}.n_beyond_2se",
                (g.pretrend_slope.abs() > 2 * g.pretrend_slope_se).sum(), src,
                "|pretrend_slope| > 2 pretrend_slope_se")


def anticipation_keys(T, ant, src):
    """Ch 7: informative tweaks, those with a clearly nonzero main effect among them, and
    the median ratio of the post-beta gap to the main effect, by patch."""
    inf = ant.status == "informative"
    clear = inf & (ant.beta_main.abs() > 2 * ant.se_main)
    for name, g in [("all", ant.index)] + [(pt, ant.index[ant.patch == pt]) for pt in PATCHES]:
        sel = ant.index.isin(g)
        w = "" if name == "all" else f", patch = {name}"
        T.count(f"anticipation.{name}.n_tweaks", sel.sum(), src, "rows" + w)
        T.count(f"anticipation.{name}.n_informative", (inf & sel).sum(), src,
                "status = informative" + w)
        T.count(f"anticipation.{name}.n_informative_clear", (clear & sel).sum(), src,
                "informative and |beta_main| > 2 se_main" + w)
        r = ant.ratio_to_main[clear & sel]
        if len(r.dropna()):
            T.add(f"anticipation.{name}.median_ratio_to_main", r.median(),
                  fmt_num(r.median(), 2, True), src,
                  "median ratio_to_main, informative and clearly nonzero" + w)
        same = clear & sel & (ant.ratio_to_main > 1)
        T.count(f"anticipation.{name}.n_same_side_larger", same.sum(), src,
                "informative, clearly nonzero, ratio_to_main > 1" + w)
    ld = ant.lead_days.dropna()
    for nm, v in [("median", ld.median()), ("min", ld.min()), ("max", ld.max())]:
        T.add(f"anticipation.lead_days.{nm}", float(v), fmt_num(v, 0), src, f"{nm} lead_days")


def robustness_keys(T, p, rob, sec, sec_h3, src_p, src_r, src_s, src_s3):
    """Ch 7: each check against the main fit at its horizon (notebook 02 section 7's
    compare / summarize: shift in the base's se, sign flips among |beta| > 2 se), the
    tagged-against-untagged agreement, and the second patch's before-block variants."""
    base = p.set_index("card_patch_id")
    for check, g in rob.groupby("check"):
        h3 = check.startswith("h3_")
        b, s = (base.beta_h, base.se_h) if h3 else (base.beta, base.se)
        g = g.set_index("card_patch_id")
        j = pd.DataFrame({"b": b, "s": s, "c": g.beta}).dropna()
        shift = (j.c - j.b) / j.s
        flip = (np.sign(j.b) != np.sign(j.c)) & (j.b.abs() > 2 * j.s)
        k, kw = f"robustness.{check}", dict(horizon="weeks 0-3" if h3 else "all weeks")
        what = f"check = {check}, against {'beta_h / se_h' if h3 else 'beta / se'}"
        T.add(f"{k}.median_shift_se", float(shift.abs().median()),
              fmt_num(shift.abs().median(), 2), src_r, f"median |shift| in se, {what}", **kw)
        T.add(f"{k}.share_beyond_2se", float((shift.abs() > 2).mean()),
              fmt_pct((shift.abs() > 2).mean()), src_r, f"share |shift| > 2 se, {what}", **kw)
        T.count(f"{k}.sign_flips", flip.sum(), src_r, f"sign flips among |beta| > 2 se, {what}",
                **kw)
        T.count(f"{k}.n", len(j), src_r, f"tweaks compared, {what}", **kw)
    for pre, horizon in [("", "all weeks"), ("h3_", "weeks 0-3")]:
        t = rob[rob.check == f"{pre}tagged"].set_index("card_patch_id")
        u = rob[rob.check == f"{pre}untagged"].set_index("card_patch_id")
        j = t.join(u, rsuffix="_u", how="inner").dropna(subset=["beta", "beta_u"])
        if len(j) < 3:
            continue
        hz = "h3" if pre else "all"
        T.add(f"robustness.tagged_untagged.{hz}.corr", float(np.corrcoef(j.beta, j.beta_u)[0, 1]),
              fmt_num(np.corrcoef(j.beta, j.beta_u)[0, 1], 2), src_r,
              f"correlation of {pre}tagged and {pre}untagged beta", horizon=horizon)
        chi2 = float((((j.beta - j.beta_u) ** 2) / (j.se ** 2 + j.se_u ** 2)).sum())
        T.add(f"robustness.tagged_untagged.{hz}.chi2", chi2, fmt_num(chi2, 0), src_r,
              "sum of (beta_t - beta_u)^2 / (se_t^2 + se_u^2) (triage A)", horizon=horizon)
        T.count(f"robustness.tagged_untagged.{hz}.n", len(j), src_r, "tweaks in both",
                horizon=horizon)
    for df, hz, horizon, src in [(sec, "all", "all weeks", src_s), (sec_h3, "h3", "weeks 0-3", src_s3)]:
        m = df[df.variant == "main"].set_index("card_patch_id")
        for v in ["pooled before", "no first-patch controls"]:
            c = df[df.variant == v].set_index("card_patch_id")
            j = m[["beta", "se"]].join(c[["beta"]], rsuffix="_v").dropna()
            sh = (j.beta_v - j.beta) / j.se
            k = f"second_patch.{hz}.{slug(v)}"
            T.add(f"{k}.median_shift_se", float(sh.abs().median()), fmt_num(sh.abs().median(), 2),
                  src, f"median |beta(variant) - beta(main)| / se(main), variant = {v}",
                  horizon=horizon)
            T.add(f"{k}.max_shift_se", float(sh.abs().max()), fmt_num(sh.abs().max(), 2),
                  src, f"max |shift| in se, variant = {v}", horizon=horizon)
            T.count(f"{k}.n", len(j), src, f"tweaks, variant = {v}", horizon=horizon)


def placebo_extra_keys(T, by_patch, spread, fits, by_h, src, missing):
    """Ch 8: placebo against real by patch (empirical p, median |beta|), the spread by the
    pseudo card's features, min_offers, and the weeks 0-3 placebo spread (when that run
    exists)."""
    for r in by_patch.itertuples():
        k = f"placebo.vs_real.{r.patch}.{r.who}"
        T.add(f"{k}.median_abs_beta_pp", 100 * r.abs_beta_q50, fmt_num(100 * r.abs_beta_q50, 1),
              src["vs_real_by_patch"], f"abs_beta_q50 x 100, patch = {r.patch}, who = {r.who}",
              horizon="all weeks")
        T.count(f"{k}.n", r.n, src["vs_real_by_patch"], "n", horizon="all weeks")
        if r.who == "real" and _fin(r.n_empirical_p):
            T.count(f"placebo.vs_real.{r.patch}.n_empirical_p", r.n_empirical_p,
                    src["vs_real_by_patch"], "n_empirical_p", horizon="all weeks")
            T.count(f"placebo.vs_real.{r.patch}.n_empirical_p_lt_05", r.n_empirical_p_lt_05,
                    src["vs_real_by_patch"], "n_empirical_p_lt_05", horizon="all weeks")
    for r in spread.itertuples():
        k = f"placebo.spread.{slug(r.feature)}.{slug(r.tercile)}"
        for c in ["sd_z", "robust_sd_z", "median_abs_z"]:
            T.add(f"{k}.{c}", float(getattr(r, c)), fmt_num(getattr(r, c), 2),
                  src["spread_by_feature"], f"{c}, feature = {r.feature}, tercile = {r.tercile}",
                  horizon="all weeks")
        T.count(f"{k}.n", r.n_fits, src["spread_by_feature"], "n_fits", horizon="all weeks")
    mo = fits.min_offers.dropna().unique()
    if len(mo) != 1:
        raise NumbersError(f"{src['placebo_fits']}: min_offers not one value ({list(mo)})")
    T.count("placebo.min_offers", mo[0], src["placebo_fits"], "min_offers (every fit)",
            horizon="all weeks")
    h3 = by_h[by_h.horizon == "weeks 0-3"]
    if not len(h3):
        missing.append(dict(keys="placebo.h3.*", reason="no weeks 0-3 placebo fits "
                            "(placebo_h3.parquet: did.placebo_run with max_week_after=3)"))
        return
    for dedupe, tag in [(False, "fits"), (True, "pairs")]:
        d = h3[h3.dedupe.astype(str).str.lower() == str(dedupe).lower()]
        for split, level in [("all", "all"), ("patch", "first"), ("patch", "second")]:
            r = _one(d, src["placebo_by_horizon"], split=split, level=level)
            w = f"horizon = weeks 0-3, dedupe = {dedupe}, split = {split}, level = {level}"
            kw = dict(horizon="weeks 0-3")
            T.add(f"placebo.h3.{tag}.{level}.sd_z", float(r.sd_z), fmt_num(r.sd_z, 2),
                  src["placebo_by_horizon"], f"sd_z, {w}", **kw)
            T.add(f"placebo.h3.{tag}.{level}.robust_sd_z", float(r.robust_sd_z),
                  fmt_num(r.robust_sd_z, 2), src["placebo_by_horizon"], f"robust_sd_z, {w}", **kw)
            T.add(f"placebo.h3.{tag}.{level}.share_abs_z_gt2", float(r.share_abs_z_gt2),
                  fmt_pct(r.share_abs_z_gt2), src["placebo_by_horizon"],
                  f"share_abs_z_gt2, {w}", **kw)
            T.count(f"placebo.h3.{tag}.{level}.n", r.n_fits, src["placebo_by_horizon"],
                    f"n_fits, {w}", **kw)


MODEL_SLUG = {"one slope": "one_slope", "slope per patch": "slope_per_patch",
              "+ patch shift": "patch_shift", "buff/nerf + patch": "buff_nerf"}


def dose_extra_keys(T, dose, points, src_dose, src_points):
    """Ch 10: every term of the notebooks' four models with tau, Q and df; the worked
    example; the same-size comparison on the primary line."""
    for (h, model), g in dose.groupby(["horizon", "model"], sort=False):
        hz, ms = HORIZON_KEY[h], MODEL_SLUG[model]
        kw = dict(horizon=h, spec="triage")
        for r in g.itertuples():
            T.estimate(f"dose.triage.{hz}.{ms}.{r.term}", r.coef, r.se, 2, src_dose,
                       f"coef, horizon = {h}, model = {model}, term = {r.term}", sign=True, **kw)
        r = g.iloc[0]
        T.add(f"dose.triage.{hz}.{ms}.tau2", float(r.tau2), fmt_num(r.tau2, 3), src_dose,
              f"tau2, model = {model}", **kw)
        T.add(f"dose.triage.{hz}.{ms}.tau", math.sqrt(r.tau2), fmt_num(math.sqrt(r.tau2), 2),
              src_dose, f"sqrt(tau2), model = {model}", **kw)
        T.add(f"dose.triage.{hz}.{ms}.q", float(r.Q), fmt_num(r.Q, 0), src_dose,
              f"Q, model = {model}", **kw)
        T.count(f"dose.triage.{hz}.{ms}.df", r.df, src_dose, f"df, model = {model}", **kw)
        T.count(f"dose.triage.{hz}.{ms}.n", r.n_tweaks, src_dose, f"n_tweaks, model = {model}",
                **kw)
    one = _one(dose, src_dose, horizon="weeks 0-3", model="one slope", term="slope").coef
    x = math.log(8 / 7)
    kw = dict(horizon="weeks 0-3", spec="triage")
    T.add("dose.example.ln_8_7", x, fmt_num(x, 3), "arithmetic", "ln(8 / 7)")
    T.add("dose.example.log_odds", one * x, fmt_num(one * x, 3, True), src_dose,
          "one-slope slope (weeks 0-3) x ln(8 / 7)", **kw)
    T.add("dose.example.pp_at_20", 100 * one * x * 0.16, fmt_num(100 * one * x * 0.16, 1, True),
          src_dose, "100 x one-slope slope x ln(8 / 7) x 0.2 x 0.8 (delta method at p = 0.2)",
          **kw)
    L = points[(points.spec == "primary") & points.on_ln_line.astype(str).str.lower().eq("true")]
    for pt in PATCHES:
        g = L[L.patch == pt]
        k, kw = f"dose.same_size.{pt}", dict(horizon="weeks 0-3", spec="primary")
        T.count(f"{k}.n", len(g), src_points, f"tweaks on the ln line, patch = {pt}", **kw)
        for nm, v, d in [("median_abs_dose", g.x_ln.abs().median(), 3),
                         ("median_abs_beta_pp", 100 * g.beta_pp.abs().median(), 1),
                         ("median_se_pp", 100 * g.se_pp.median(), 2),
                         ("median_abs_beta_lo", g.beta_lo.abs().median(), 3),
                         ("median_se_lo", g.se_lo.median(), 3)]:
            T.add(f"{k}.{nm}", float(v), fmt_num(v, d), src_points,
                  f"{nm}, primary spec, on_ln_line, patch = {pt}", **kw)


SPEC_SLUG = {"triage": "triage", "primary": "primary",
             "primary, Debilitate at table dose": "primary_debilitate_table_dose",
             "Reflect off, Debilitate off": "reflect_off_debilitate_off"}
RULER_SLUG = {"ln(new/old)": "ln", "outcome in pp, ln dose": "pp_ln",
              "absolute (new - old)": "absolute", "rank": "rank", "percent": "percent",
              "ln / kind's median |ln|": "ln_kind", "sign only": "sign",
              "(new - old) / kind's median |new - old|": "absolute_kind",
              "mean of base and upgraded ln": "base_upgraded"}


def _ruler_slug(name):
    return "hybrid" if name.startswith("hybrid") else RULER_SLUG[name]


def _slopes(T, k, r, src, column, **kw):
    T.estimate(f"{k}.slope_first", r.slope1, r.se1, 2, src, f"slope1, {column}", sign=True, **kw)
    T.estimate(f"{k}.slope_second", r.slope2, r.se2, 2, src, f"slope2, {column}", sign=True, **kw)
    T.add(f"{k}.z_diff", float(r.z_diff), fmt_num(r.z_diff, 2), src, f"z_diff, {column}", **kw)
    T.count(f"{k}.n_first", r.n1, src, f"n1, {column}", **kw)
    T.count(f"{k}.n_second", r.n2, src, f"n2, {column}", **kw)


def ruler_keys(T, t, src):
    """Ch 11: rulers per spec; review calls; mixed-tweak variants; leave-one-out; character
    terms."""
    kw = dict(horizon="weeks 0-3")
    for r in t["rulers"].itertuples():
        k = f"rulers.{SPEC_SLUG[r.spec]}.{_ruler_slug(r.ruler)}"
        _slopes(T, k, r, src["rulers"], f"spec = {r.spec}, ruler = {r.ruler}", spec=r.spec, **kw)
        T.estimate(f"{k}.ratio", r.ratio, r.se_ratio, 2, src["rulers"],
                   f"ratio slope2 / slope1, spec = {r.spec}, ruler = {r.ruler}", sign=True,
                   spec=r.spec, **kw)
    for r in t["review_calls"].itertuples():
        k = f"review.{SPEC_SLUG[r.spec]}.{slug(r.variant)}.{_ruler_slug(r.ruler)}"
        _slopes(T, k, r, src["review_calls"],
                f"spec = {r.spec}, variant = {r.variant}, ruler = {r.ruler}", spec=r.spec, **kw)
    for r in t["mixed"].itertuples():
        k = f"mixed.{_ruler_slug(r.ruler)}.{slug(r.variant)}"
        _slopes(T, k, r, src["mixed"], f"ruler = {r.ruler}, variant = {r.variant}",
                spec="triage (the notebooks' 38) + the variant's points", **kw)
    lo = t["leave_out"]
    for spec, g in lo.groupby("spec"):
        s = SPEC_SLUG[spec]
        for r in g.itertuples():
            if r.level == "tweak":
                k = f"leave_out.{s}.{tweak_prefix(r.left_out)[len('tweak.'):]}"
            elif r.level == "character":
                k = f"leave_out.{s}.{slug(r.left_out)}"
            else:
                k = f"leave_out.{s}.none"
            col = f"spec = {spec}, left_out = {r.left_out}"
            _slopes(T, k, r, src["leave_out"], col, spec=spec, **kw)
            if r.level != "none":
                T.add(f"{k}.d_slope_second_se", float(r.d_slope2_in_se),
                      fmt_num(r.d_slope2_in_se, 2, True), src["leave_out"],
                      f"d_slope2_in_se, {col}", spec=spec, **kw)
                T.add(f"{k}.d_slope_first_se", float(r.d_slope1_in_se),
                      fmt_num(r.d_slope1_in_se, 2, True), src["leave_out"],
                      f"d_slope1_in_se, {col}", spec=spec, **kw)
        tw = g[g.level == "tweak"]
        top = tw.loc[tw.d_slope2_in_se.abs().idxmax()]
        T.add(f"leave_out.{s}.most_influential_second", top.card_id, top.card_id,
              src["leave_out"], f"card_id with the largest |d_slope2_in_se|, spec = {spec}",
              spec=spec, **kw)
        T.add(f"leave_out.{s}.max_abs_d_slope_second_se", abs(float(top.d_slope2_in_se)),
              fmt_num(abs(top.d_slope2_in_se), 2), src["leave_out"],
              f"max |d_slope2_in_se| over tweaks, spec = {spec}", spec=spec, **kw)
    for r in t["character"].itertuples():
        s = SPEC_SLUG[r.spec]
        if _fin(r.slope1):
            k = f"character.{s}.{slug(r.model)}"
            T.estimate(f"{k}.slope_first", r.slope1, r.se1, 2, src["character"],
                       f"slope1, model = {r.model}", sign=True, spec=r.spec, **kw)
            T.estimate(f"{k}.slope_second", r.slope2, r.se2, 2, src["character"],
                       f"slope2, model = {r.model}", sign=True, spec=r.spec, **kw)
            T.add(f"{k}.z_diff", float(r.z_diff), fmt_num(r.z_diff, 2), src["character"],
                  f"z_diff, model = {r.model}", spec=r.spec, **kw)
        else:
            m = re.match(r"slope within (\w+), (\w+) patch", r.model)
            k = f"character.{s}.within.{m.group(1)}.{m.group(2)}"
            T.estimate(f"{k}.slope", r.slope, r.se, 2, src["character"],
                       f"slope, model = {r.model}", sign=True, spec=r.spec, **kw)
            T.count(f"{k}.n", r.n, src["character"], f"n, model = {r.model}", spec=r.spec, **kw)
    for r in t["character_counts"].itertuples():
        for pt in PATCHES:
            T.count(f"character.{SPEC_SLUG[r.spec]}.counts.{r.color}.{pt}", getattr(r, pt),
                    src["character_counts"], f"{pt}, color = {r.color}", spec=r.spec, **kw)


def power_keys(T, power, spread, src_p, src_s):
    """Ch 12: the power table and the real against placebo spread."""
    kw = dict(horizon="weeks 0-3")
    for r in power.itertuples():
        k = f"power.{SPEC_SLUG[r.spec]}.{slug(r.setting)}.planted_{slug(f'{r.planted:g}')}"
        w = f"spec = {r.spec}, setting = {r.setting}, planted = {r.planted:g}"
        T.add(f"{k}.power_slope_second", float(r.power_slope2_ne_0),
              fmt_pct(r.power_slope2_ne_0), src_p, f"power_slope2_ne_0, {w}", spec=r.spec, **kw)
        T.add(f"{k}.power_diff", float(r.power_diff_ne_0), fmt_pct(r.power_diff_ne_0), src_p,
              f"power_diff_ne_0, {w}", spec=r.spec, **kw)
        T.add(f"{k}.cover", float(r.cover_planted), fmt_pct(r.cover_planted), src_p,
              f"cover_planted, {w}", spec=r.spec, **kw)
        T.add(f"{k}.median_se_second", float(r.median_se2), fmt_num(r.median_se2, 2), src_p,
              f"median_se2, {w}", spec=r.spec, **kw)
        T.add(f"{k}.mean_slope_second", float(r.mean_slope2), fmt_num(r.mean_slope2, 2, True),
              src_p, f"mean_slope2, {w}", spec=r.spec, **kw)
    T.count("power.n_sim", power.n_sim.iloc[0], src_p, "n_sim")
    for r in spread.itertuples():
        k = f"spread.{SPEC_SLUG[r.spec]}.{r.patch}"
        for c in ["sd_real", "sd_placebo", "median_se_real", "median_se_placebo"]:
            T.add(f"{k}.{c}", float(getattr(r, c)), fmt_num(getattr(r, c), 3), src_s,
                  f"{c} (log-odds), spec = {r.spec}, patch = {r.patch}", spec=r.spec, **kw)
        for c in ["n_real", "n_placebo"]:
            T.count(f"{k}.{c}", getattr(r, c), src_s, f"{c}, spec = {r.spec}, patch = {r.patch}",
                    spec=r.spec, **kw)


def check_keys(T, checks, src, missing):
    """Ch 12: spirometry.checks' rows as checks.<check>.<item>; each check's tables (pages)
    go in the spec column and in checks.<check>.pages / .tables. A check with no rows is
    listed in the header's missing."""
    from spirometry.checks import FILES
    for check in [*FILES, "group_lines"]:
        if check not in set(checks.check):
            missing.append(dict(keys=f"checks.{check}.*",
                                reason=f"not in {src} (see spirometry.checks' output)"))
    for (check, tables), g in checks.groupby(["check", "tables"], sort=False):
        for r in g.itertuples():
            add_kind(T, f"checks.{check}.{r.item}", r.value, r.kind, src,
                     f"check = {check}, item = {r.item} (from {r.source})",
                     se=r.se if r.kind == "estimate" else None, spec=tables)
        T.count(f"checks.{check}.pages", g.pages.iloc[0], src, "pages of the tables",
                spec=tables)
        T.add(f"checks.{check}.tables", tables, tables, src, "tables", spec=tables)


def iv_keys(T, t, src):
    """Ch 2 and 13: the IV primer's simulated game (spirometry.iv_sim); "simulation"."""
    kw = dict(spec="simulation")
    s = t["iv_single"]
    for r in s.itertuples():
        T.estimate(f"iv.single.{r.quantity}", r.estimate, r.se, 3, src["iv_single"],
                   f"estimate, quantity = {r.quantity}", **kw)
    r = s.iloc[0]
    T.add("iv.single.truth", float(s.truth.dropna().iloc[0]), fmt_num(s.truth.dropna().iloc[0], 2),
          src["iv_single"], "truth", **kw)
    T.add("iv.single.f", float(r.F), fmt_num(r.F, 0), src["iv_single"], "F", **kw)
    T.count("iv.single.n_runs", r.n_runs, src["iv_single"], "n_runs", **kw)
    for c in ["share_offered", "share_picked", "win_pickers", "win_non_pickers"]:
        T.add(f"iv.single.{c}", float(getattr(r, c)), fmt_pct(getattr(r, c), 1),
              src["iv_single"], c, **kw)
    for r in t["iv_draws"].itertuples():
        k = f"iv.draws.{slug(r.estimator)}"
        T.add(f"{k}.mean", float(r.mean), fmt_num(r.mean, 3), src["iv_draws"], "mean", **kw)
        T.add(f"{k}.sd", float(r.sd_across_draws), fmt_num(r.sd_across_draws, 3),
              src["iv_draws"], "sd_across_draws", **kw)
        T.add(f"{k}.mean_se", float(r.mean_reported_se), fmt_num(r.mean_reported_se, 3),
              src["iv_draws"], "mean_reported_se", **kw)
        T.add(f"{k}.coverage", float(r.share_ci_covers_truth),
              fmt_pct(r.share_ci_covers_truth), src["iv_draws"], "share_ci_covers_truth", **kw)
    for i, r in enumerate(t["iv_weak"].itertuples()):
        k = f"iv.weak.{slug(f'intercept {r.pick_intercept:g}'.replace('-', 'minus '))}"
        T.add(f"{k}.first_stage", float(r.first_stage), fmt_num(r.first_stage, 3),
              src["iv_weak"], "first_stage", **kw)
        T.add(f"{k}.f", float(r.F), fmt_num(r.F, 0), src["iv_weak"], "F", **kw)
        T.add(f"{k}.share_f_below_10", float(r.share_F_below_10), fmt_pct(r.share_F_below_10),
              src["iv_weak"], "share_F_below_10", **kw)
        for c in ["naive_median", "naive_p10", "naive_p90", "iv_median", "iv_p10", "iv_p90"]:
            T.add(f"{k}.{c}", float(getattr(r, c)), fmt_num(getattr(r, c), 2, True),
                  src["iv_weak"], c, **kw)
    for r in t["iv_broken"].itertuples():
        k = f"iv.broken.{slug(r.case)}"
        for c in ["naive", "iv", "first_stage", "iv_bias"]:
            T.add(f"{k}.{c}", float(getattr(r, c)), fmt_num(getattr(r, c), 3, c == "iv_bias"),
                  src["iv_broken"], f"{c}, case = {r.case}", **kw)
    for r in t["iv_het"].itertuples():
        k = ("iv.het.iv_estimate" if r.quantity.startswith("IV") else
             "iv.het.true_among_pickers" if "picked" in r.quantity else "iv.het.true_all")
        T.add(k, float(r.effect), fmt_num(r.effect, 3), src["iv_het"], r.quantity, **kw)
    for r in t["iv_confounding"].itertuples():
        k = f"iv.confounding.skill_{slug(f'{r.skill_on_win:g}')}"
        for c in ["naive", "iv", "naive_bias", "iv_bias"]:
            T.add(f"{k}.{c}", float(getattr(r, c)), fmt_num(getattr(r, c), 3, "bias" in c),
                  src["iv_confounding"], f"{c}, skill_on_win = {r.skill_on_win:g}", **kw)


TOY_KINDS = {  # teaching_sims.csv kind -> (scale, sign, percent); count is separate
    "number": (1, False, False), "signed": (1, True, False), "pp": (100, True, False),
    "ppu": (100, False, False), "pct": (1, False, True)}


def toy_keys(T, t, src):
    """The toy simulations (spirometry.teaching_sims): toy.<toy>.<quantity>, "simulation"."""
    for r in t.itertuples():
        key, d = f"toy.{r.toy}.{r.quantity}", int(r.decimals)
        col = f"value, toy = {r.toy}, quantity = {r.quantity} ({r.label})"
        if r.kind == "count":
            T.count(key, round(float(r.value)), src, col, spec="simulation")
            continue
        if r.kind not in TOY_KINDS:
            raise NumbersError(f"{src}: unknown kind {r.kind!r} for {key}")
        scale, sign, pct = TOY_KINDS[r.kind]
        v = float(r.value) * scale
        T.add(key, v, fmt_pct(v, d) if pct else fmt_num(v, d, sign), src,
              col + (f" x {scale}" if scale != 1 else ""), spec="simulation")


# ------------------------------------------------------------------------------- build

def build(analysis="data/analysis", results="results", allow_sample=False,
          snapshot_log="snapshot.log", ref="reference"):
    """Every key, checked. Returns (rows DataFrame, header dict)."""
    meta, built, t, paths, log = load(analysis, results, allow_sample, snapshot_log, ref)
    stamp = (f"tables built {meta['tables_built_at_utc']}; {meta['snapshot_pages']} pages; "
             f"parser {meta['parser_version']}")
    src = {k: str(v) for k, v in paths.items()}
    T = Table(stamp)
    provenance_keys(T, meta, str(paths["meta"]), log, str(snapshot_log))
    unc = did_keys(T, t["pick_rate"], str(paths["pick_rate"]))
    missing = calibrated_keys(T, t["calibrated"], str(paths["calibrated"]), unc)
    dose_keys(T, t["dose"], t["rulers"], t["se_inflation"], str(paths["dose"]),
              str(paths["rulers"]), str(paths["se_inflation"]))
    placebo_keys(T, t["placebo"], str(paths["placebo"]))
    # field guide task A: every chapter's saved numbers
    constant_keys(T)
    snapshot_extra_keys(T, t["audit"], log, src["audit"], str(snapshot_log), meta,
                        src["meta"], missing)
    audit_keys(T, t["audit"], t["audit_builds"], src["audit"], src["audit_builds"])
    reference_keys(T, t["tweak_sizes"], t["card_changes"], src["tweak_sizes"],
                   src["card_changes"])
    tweak_keys(T, t["pick_rate"], t["did_main"], t["flags"], t["anticipation"], t["vs_real"],
               t["second_checks_h3"], t["calibrated"], src)
    false_alarm_keys(T, t["pick_rate"], src["pick_rate"])
    se_keys(T, t["pick_rate"], t["did_main"], src["pick_rate"], src["did_main"])
    flag_keys(T, t["flags"], src["flags"])
    anticipation_keys(T, t["anticipation"], src["anticipation"])
    robustness_keys(T, t["pick_rate"], t["robustness"], t["second_checks"],
                    t["second_checks_h3"], src["pick_rate"], src["robustness"],
                    src["second_checks"], src["second_checks_h3"])
    placebo_extra_keys(T, t["vs_real_by_patch"], t["spread_by_feature"], t["placebo_fits"],
                       t["placebo_by_horizon"], src, missing)
    dose_extra_keys(T, t["dose"], t["dose_points"], src["dose"], src["dose_points"])
    ruler_keys(T, t, src)
    power_keys(T, t["power"], t["spread"], src["power"], src["spread"])
    check_keys(T, t["design_checks"], src["design_checks"], missing)
    iv_keys(T, t, src)
    toy_keys(T, t["teaching_sims"], src["teaching_sims"])
    df = T.frame()
    # numeric values aren't text: 16 digits of a float would read as a hashed id
    private("numbers", df.assign(value=df.value.map(lambda v: v if isinstance(v, str)
                                                    else "")))
    header = dict(sample=bool(meta.get("sample")),
                  generated_at_utc=datetime.datetime.now(datetime.timezone.utc)
                  .isoformat(timespec="seconds"),
                  tables_built_at_utc=meta["tables_built_at_utc"],
                  snapshot_pages=str(meta["snapshot_pages"]),
                  parser_version=str(meta["parser_version"]),
                  missing=missing,
                  inputs={str(p): datetime.datetime.fromtimestamp(
                      p.stat().st_mtime, datetime.timezone.utc).isoformat(timespec="seconds")
                      for p in [*paths.values(), pathlib.Path(snapshot_log)]})
    return df, header


def write(df, header, out):
    """numbers.json ({build: header, numbers: {key: row}}) and numbers.csv beside it."""
    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = {r["key"]: {k: v for k, v in r.items() if k != "key"}
            for r in df.to_dict("records")}
    out.write_text(json.dumps(dict(build=header, numbers=rows), indent=2,
                              ensure_ascii=False) + "\n")
    df.to_csv(out.with_suffix(".csv"), index=False)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--analysis", default="data/analysis")
    p.add_argument("--results", default="results")
    p.add_argument("--out", default="writeup/numbers.json")
    p.add_argument("--snapshot-log", default="snapshot.log")
    p.add_argument("--allow-sample", action="store_true",
                   help="build from a sample export (results/meta.json sample: true)")
    p.add_argument("--ref", default="reference", help="committed reference tables")
    a = p.parse_args(argv)
    try:
        df, header = build(a.analysis, a.results, a.allow_sample, a.snapshot_log, a.ref)
    except NumbersError as e:
        sys.exit(f"numbers stopped: {e}")
    write(df, header, a.out)
    print(f"{len(df)} numbers ({int(df.appendix.sum())} for the appendix), tables built "
          f"{header['tables_built_at_utc']}, {header['snapshot_pages']} pages")
    for m in header["missing"]:
        print(f"missing: {m['keys']} ({m['reason']})")
    print(f"-> {a.out}, {pathlib.Path(a.out).with_suffix('.csv')}")


if __name__ == "__main__":
    main()
