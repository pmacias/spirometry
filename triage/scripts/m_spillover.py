"""Section M (EXPLORATORY): does spillover from changed cards explain the placebo spread?

Proposed after the results were seen. Reads the final tables; changes no factor, number or
result. Same settings as the calibration: data/analysis/placebo_h3.parquet (weeks 0-3,
same-color controls, one row per (window, pseudo card), min_offers as saved). The
interpretation rule is in TRIAGE.md section M, written before this ran.

    python triage/scripts/m_spillover.py --check         # reproduce saved placebo fits first
    python triage/scripts/m_spillover.py                 # tests 1, 2, 3 (declared settings)
    python triage/scripts/m_spillover.py --part 3 --all-eligible
                                                         # secondary: every eligible card

Run from the repository root. Output: triage/out_final/m_*.csv (TRIAGE_OUT overrides), keyed by
window and card; no run IDs. Opens runs.duckdb read-only, and uses derived colors (db.py), so
reference/raw/ stays closed.

Test 1  m_windows.csv, m_window_spearman.csv: placebo spread per character-window against how
        much changed there.
Test 2  m_exposure_pairs.csv, m_exposure_corr.csv: per placebo pair, after and before block:
          screen = share of the pseudo card's offers on screens that also offered a changed card
          run    = share of its runs that took a changed card (reward screens only)
          signed = sum over numeric tweaks of dose x co-offer share
        Spillover predicts corr(z, signed) < 0 and corr(z^2, exposure) > 0.
Test 3  m_clean_placebo.csv, m_clean_summary.csv: placebo fits in the character-window with no
        numeric tweak, with cards changed in any other way left out.

Dose: direction x log_ratio, the dose line's x. `direction` is +1 on every row of
tweak_sizes.csv and the sign is in log_ratio, so direction x |log_ratio| would be unsigned.
Changed cards: window_changes (every kind of change, as the controls exclude), for screen and
run exposure; numeric tweaks only for signed exposure, since only they have a dose. The
*_subst columns (added after the first run, before anything was written up) leave out cards
whose only change is text_only_labels' "wording": those can't spill over, and they inflate
exposure (a Defect run exposure of 0.51 against the three substantive changes' much less).
"""
import argparse
import os
import resource
import sys
import time
import zlib

import numpy as np
import pandas as pd

sys.path.insert(0, "triage/scripts")
import db  # noqa: E402
from common import all_tweaks, on_line  # noqa: E402
from spirometry import did  # noqa: E402

OUT = os.environ.get("TRIAGE_OUT", "triage/out_final")    # final tables, not the 1,873-page record
PLACEBO = "data/analysis/placebo_h3.parquet"
WEEKS = 3
N_PSEUDO, SEED = 20, 0
N_BOOT, BOOT_SEED = 2000, 20261106
CLEAN_FACTOR = 4.10            # first-patch factor (export.PLACEBO_FACTORS_H3)
KEY = ["color", "before_builds", "after_builds"]
PAIR = KEY + ["fit_on", "pseudo_card"]

EXPOSURE_SQL = """
WITH o AS (
  SELECT run_key, floor, coalesce(set_idx::VARCHAR, 'list') AS s, card_id, upgraded, picked,
         list_contains($after, build_id) AS after
  FROM offers_with_version
  WHERE character = $character AND list_contains($builds, build_id)
    AND ascension IS NOT NULL
    AND (NOT list_contains($after, build_id) OR start_time < $cutoff)
),
chg AS (SELECT DISTINCT after, run_key, floor, s, card_id AS changed FROM o
        WHERE list_contains($changed, card_id)),
took AS (SELECT DISTINCT after, run_key FROM o
         WHERE picked AND list_contains($changed, card_id)),
p AS (SELECT after, run_key, floor, s, card_id FROM o
      WHERE list_contains($pseudo, card_id) AND (upgraded OR NOT $upgraded_only))
SELECT 'total' AS kind, card_id, after, NULL AS changed, count(*) AS n FROM p GROUP BY ALL
UNION ALL
SELECT 'runs', card_id, after, NULL, count(DISTINCT run_key) FROM p GROUP BY ALL
UNION ALL
SELECT 'runs_took', card_id, after, NULL, count(DISTINCT run_key)
FROM p SEMI JOIN took USING (after, run_key) GROUP BY ALL
UNION ALL
SELECT 'screen_any', card_id, after, NULL, count(*)
FROM p SEMI JOIN chg USING (after, run_key, floor, s) GROUP BY ALL
UNION ALL
SELECT 'screen_card', card_id, after, c.changed, count(*)
FROM p JOIN chg c USING (after, run_key, floor, s) GROUP BY ALL
"""


def spearman(a, b):
    a, b = pd.Series(a).reset_index(drop=True), pd.Series(b).reset_index(drop=True)
    return a.rank().corr(b.rank())


def robust_sd(z):
    z = pd.Series(z)
    return 1.4826 * (z - z.median()).abs().median()


def tweak_doses():
    """tweak_sizes.csv with the signed dose x (blank for the upgrade-only tweaks without a
    base or upgraded ln) and the line flag (the dose line's 38)."""
    t = did._csv("reference/tweak_sizes.csv")
    t["x"] = (pd.to_numeric(t.direction) * pd.to_numeric(t.log_ratio, errors="coerce"))
    line = set(on_line(all_tweaks("h3")).index)
    t["on_line"] = t.card_patch_id.isin(line)
    return t


# ---------------------------------------------------------------------------------- test 1

def substantive(changed, stable_build):
    """`changed` without the cards whose only change in this patch is a wording fix."""
    cc = did._csv("reference/card_changes.csv")
    cc = cc[cc.stable_build == stable_build]
    lab = did._csv("reference/text_only_labels.csv")
    lab = lab[(lab.stable_build == stable_build) & (lab.label == "wording")]
    other = set(cc.card_id[cc.change_kind != "text_only"])
    return set(changed) - (set(lab.card_id) - other)


def boot_sd(z, seed=BOOT_SEED):
    """Percentile 95% interval of the robust sd, resampling cards."""
    z, rng = np.asarray(z, float), np.random.default_rng(seed)
    return np.percentile([robust_sd(z[rng.integers(0, len(z), len(z))])
                          for _ in range(N_BOOT)], [2.5, 97.5])


def window_table(pairs, t):
    rows = []
    for (color, before, after), g in pairs.groupby(KEY, sort=False):
        w = t[(t.color == color) & (t.before_builds == before) & (t.after_builds == after)]
        L = w[w.on_line]
        changed, _ = did.window_changes(before, after)
        colors = did.card_colors()
        ci = boot_sd(g.z)
        rows.append(dict(
            patch=g.patch.iloc[0], color=color, window=f"{before} -> {after}",
            n_tweaks=len(w), n_line=len(L),
            n_changed_any_kind=sum(colors.get(c) == color for c in changed),
            n_changed_substantive=sum(colors.get(c) == color
                                      for c in substantive(changed, after.split()[0])),
            sum_abs_log_ratio=w.x.abs().sum(), net_signed_dose=w.x.sum(),
            sum_abs_log_ratio_line=L.x.abs().sum(), net_signed_dose_line=L.x.sum(),
            n_pairs=len(g), n_pairs_upgraded=int((g.fit_on == "upgraded offers").sum()),
            robust_sd_z=robust_sd(g.z), robust_sd_lo=ci[0], robust_sd_hi=ci[1], sd_z=g.z.std(), mean_z=g.z.mean()))
    return pd.DataFrame(rows).sort_values(["patch", "color"]).reset_index(drop=True)


def window_spearman(tab):
    rows = []
    parts = [("pooled", tab)] + [(p, g) for p, g in tab.groupby("patch")]
    for name, g in parts:
        for col in ("n_tweaks", "n_line", "n_changed_any_kind", "n_changed_substantive",
                    "sum_abs_log_ratio",
                    "sum_abs_log_ratio_line"):
            rows.append(dict(scope=name, n_windows=len(g), against=col,
                             spearman=spearman(g.robust_sd_z, g[col])))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------- test 2

def window_exposure(con, color, before, after, pseudo, changed, doses, upgraded_only=False):
    """One row per (pseudo card, block): screen and run exposure, signed exposure (doses:
    card -> x) and the counts. Cards with no offers in a block have no row for it."""
    b, a = before.split(), after.split()
    cutoff = did.release_date(a[0]) + pd.Timedelta(seconds=(WEEKS + 1) * did.WEEK)
    n = con.execute(EXPOSURE_SQL, dict(
        after=a, builds=b + a, character=did._character(color), cutoff=cutoff.to_pydatetime(),
        changed=sorted(changed), pseudo=sorted(pseudo), upgraded_only=upgraded_only)).df()
    rows = []
    for (card, is_after), g in n.groupby(["card_id", "after"]):
        get = lambda k: g.n[g.kind == k].sum()
        total, runs = get("total"), get("runs")
        by_card = g[g.kind == "screen_card"].set_index("changed").n
        rows.append(dict(
            pseudo_card=card, block="after" if is_after else "before",
            offers=total, runs=runs, screen_exposure=get("screen_any") / total,
            run_exposure=get("runs_took") / runs,
            signed_exposure=sum(x * by_card.get(c, 0) / total for c, x in doses.items())))
    return pd.DataFrame(rows)


def exposures(con, pairs, t):
    out = []
    for (color, before, after, fit_on), g in pairs.groupby(KEY + ["fit_on"], sort=False):
        t0 = time.time()
        changed, _ = did.window_changes(before, after)
        w = t[(t.color == color) & (t.before_builds == before) & (t.after_builds == after)
              & t.x.notna()]
        e = window_exposure(con, color, before, after, g.pseudo_card.unique().tolist(), changed,
                            dict(zip(w.card_id, w.x)), fit_on == "upgraded offers")
        sub = window_exposure(con, color, before, after, g.pseudo_card.unique().tolist(),
                              substantive(changed, after.split()[0]), {},
                              fit_on == "upgraded offers")
        sub = sub.rename(columns=dict(screen_exposure="screen_subst", run_exposure="run_subst"))
        e = e.merge(sub[["pseudo_card", "block", "screen_subst", "run_subst"]],
                    on=["pseudo_card", "block"])
        wide = e.pivot(index="pseudo_card", columns="block")
        wide.columns = [f"{c}_{b}" for c, b in wide.columns]
        out.append(g.merge(wide.reset_index(), on="pseudo_card", how="left"))
        print(f"  exposure {color} {before} -> {after} ({fit_on}): {len(g)} pairs, "
              f"{time.time() - t0:.0f} s", flush=True)
    return pd.concat(out, ignore_index=True)


def _demean(d, col):
    return d[col] - d.groupby(KEY + ["fit_on"])[col].transform("mean")


def _residual(y, x):
    keep = np.isfinite(y) & np.isfinite(x)
    r = np.full(len(y), np.nan)
    r[keep] = y[keep] - np.polyval(np.polyfit(x[keep], y[keep], 1), x[keep])
    return r


def _corr(a, b):
    keep = np.isfinite(a) & np.isfinite(b)
    return np.corrcoef(a[keep], b[keep])[0, 1] if keep.sum() > 2 else np.nan


def boot_corr(a, b, cards):
    """Percentile 95% interval of corr(a, b), resampling pseudo cards (each with all its
    rows, since a card appears in several windows)."""
    rng = np.random.default_rng(BOOT_SEED)
    idx = pd.Series(np.arange(len(cards))).groupby(np.asarray(cards)).apply(np.array).tolist()
    stats = []
    for _ in range(N_BOOT):
        take = np.concatenate([idx[i] for i in rng.integers(0, len(idx), len(idx))])
        stats.append(_corr(a[take], b[take]))
    return np.nanpercentile(stats, [2.5, 97.5])


def corr_table(d):
    tests = [("z", "signed_exposure", "negative"), ("z2", "screen_exposure", "positive"),
             ("z2", "run_exposure", "positive"), ("z2", "screen_subst", "positive"),
             ("z2", "run_subst", "positive")]
    d = d.assign(z2=d.z ** 2)
    parts = [("pooled", d)] + [(p, g) for p, g in d.groupby("patch")]
    rows = []
    for name, g in parts:
        g = g.reset_index(drop=True)
        lo = np.log(g.n_treated_offers.to_numpy(float))
        dlo = _demean(g.assign(lo=lo), "lo").to_numpy(float)
        for y, x, pred in tests:
            for block in ("after", "before"):
                col = f"{x}_{block}"
                a, b = g[y].to_numpy(float), g[col].to_numpy(float)
                ci = boot_corr(a, b, g.pseudo_card.to_numpy())
                dy, dx = _demean(g, y).to_numpy(float), _demean(g, col).to_numpy(float)
                ci_w = boot_corr(dy, dx, g.pseudo_card.to_numpy())
                rows.append(dict(
                    scope=name, y=y, exposure=x, block=block, predicted=pred, n_pairs=len(g),
                    n_cards=g.pseudo_card.nunique(), pearson=_corr(a, b), ci_lo=ci[0],
                    ci_hi=ci[1], spearman=spearman(a, b), within_window=_corr(dy, dx),
                    within_lo=ci_w[0], within_hi=ci_w[1],
                    partial_log_offers=_corr(_residual(a, lo), _residual(b, lo)),
                    within_partial_log_offers=_corr(_residual(dy, dlo), _residual(dx, dlo))))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------- test 3

def sample_fits(con, cpid, color, before, after, n, seed_key, min_offers, df=None, counts=None):
    """placebo_all's selection and fit for one window, with a window row chosen here:
    eligible = control_cards with at least min_offers in each block, sampled seeded by
    (SEED, crc32(seed_key)), fit on all offers at weeks 0-3."""
    df = did.load_block_data(con, color, before, after) if df is None else df
    if counts is None:
        counts = did._block_counts(con, before, after, WEEKS)
    pool = did.control_cards(cpid, False, df=df)
    offers = {c: did._card_offers(counts, c, None) for c in pool}
    eligible = [c for c in pool if min(offers[c]) >= min_offers]
    rng = np.random.default_rng([SEED, zlib.crc32(seed_key.encode())])
    k = len(eligible) if n is None else min(n, len(eligible))
    picks = sorted(rng.choice(eligible, k, replace=False))
    rows = []
    for c in picks:
        r = did.placebo_fit(df, cpid, c, max_week_after=WEEKS)
        rows.append(dict(pseudo_card=c, beta=r["beta"], se=r["se"], z=r["beta"] / r["se"],
                         n_treated_offers=r["n_treated_offers"], n_offers=r["n_offers"],
                         n_control_cards=r["n_control_cards"], pseudo_offers_before=offers[c][0],
                         pseudo_offers_after=offers[c][1]))
    return pd.DataFrame(rows), len(pool), len(eligible)


def check(con, raw):
    """Reproduce saved placebo_h3 fits with sample_fits and derived colors: same cards, same z."""
    for cpid in ("HEMOKINESIS@v0.103.2/patch", "UPROAR@v0.107.1/patch"):
        t0 = time.time()
        w = did.window(cpid)
        saved = raw[raw.card_patch_id == cpid].set_index("pseudo_card")
        color = saved.color.iloc[0]
        got, _, n_el = sample_fits(con, cpid, color, w["before_builds"], w["after_builds"],
                                   N_PSEUDO, cpid, int(saved.min_offers.iloc[0]))
        got = got.set_index("pseudo_card")
        same = set(got.index) == set(saved.index)
        dz = (got.z - saved.z).abs().max() if same else np.nan
        print(f"{cpid}: same cards {same}, eligible {n_el} (saved "
              f"{int(saved.n_eligible.iloc[0])}), max |dz| {dz:.2e}, {time.time() - t0:.0f} s",
              flush=True)
        if not same or not dz < 1e-6:
            raise SystemExit("check failed: fits differ from placebo_h3")


def clean_windows(t):
    """Character-windows with no row in tweak_sizes.csv, among the windows the tweaks use."""
    wins = t[["before_builds", "after_builds"]].drop_duplicates()
    have = set(zip(t.color, t.before_builds, t.after_builds))
    return [(c, r.before_builds, r.after_builds) for r in wins.itertuples()
            for c in did.CHARACTER_COLORS if (c, r.before_builds, r.after_builds) not in have]


def host_patch(color, before, after):
    """A card-patch row of this character-window, for its control exclusions; its own card is
    a changed card, so it is in no fit. None if the window has no card-patch row."""
    w = did._csv("reference/windows.csv")
    colors = did.card_colors()
    w = w[(w.level == "card_patch") & (w.before_builds == before) & (w.after_builds == after)]
    ids = sorted(e for e, c in zip(w.event_id, w.card_id) if colors.get(c) == color)
    return ids[0] if ids else None


def clean_placebo(con, t, min_offers, all_eligible):
    fits, rows = [], []
    for color, before, after in clean_windows(t):
        cpid = host_patch(color, before, after)
        label = f"{color} {before} -> {after}"
        print(f"clean window: {label}, host row {cpid}", flush=True)
        if cpid is None:
            rows.append(dict(window=label, note="no card-patch row: not run"))
            continue
        df = did.load_block_data(con, color, before, after)
        counts = did._block_counts(con, before, after, WEEKS)
        for name, n in (("declared: 20 cards", N_PSEUDO),
                        ("secondary: all eligible", None) if all_eligible else (None, None)):
            if name is None:
                continue
            t0 = time.time()
            f, n_pool, n_el = sample_fits(con, cpid, color, before, after, n, label, min_offers,
                                          df=df, counts=counts)
            ci = boot_sd(f.z)
            rows.append(dict(
                window=label, design=name, host_row=cpid, n_pool=n_pool, n_eligible=n_el,
                min_offers=min_offers, n_fits=len(f), robust_sd_z=robust_sd(f.z),
                robust_sd_lo=ci[0], robust_sd_hi=ci[1], sd_z=f.z.std(), mean_z=f.z.mean(),
                share_abs_z_gt2=(f.z.abs() > 2).mean(), median_se_pp=100 * f.se.median(),
                sd_beta_pp=100 * f.beta.std(), first_patch_factor=CLEAN_FACTOR,
                seconds=time.time() - t0))
            fits.append(f.assign(window=label, design=name))
            print(pd.DataFrame(rows).tail(1).T.to_string(), flush=True)
        # how clean is it: exposure of the declared cards, as test 2 measures it
        changed, _ = did.window_changes(before, after)
        cards = fits[0].pseudo_card.tolist()
        e = window_exposure(con, color, before, after, cards, changed, {})
        s = window_exposure(con, color, before, after, cards,
                            substantive(changed, after.split()[0]), {})
        e = e.drop(columns="signed_exposure").merge(
            s.rename(columns=dict(screen_exposure="screen_subst", run_exposure="run_subst"))[
                ["pseudo_card", "block", "screen_subst", "run_subst"]],
            on=["pseudo_card", "block"])
        e.to_csv(f"{OUT}/m_clean_exposure.csv", index=False)
        print(sorted(substantive(changed, after.split()[0]) & set(df.card_id.cat.categories)))
        print(e.groupby("block")[["screen_exposure", "run_exposure", "screen_subst",
                                  "run_subst"]].mean(), flush=True)
    return pd.concat(fits, ignore_index=True), pd.DataFrame(rows)


ap = argparse.ArgumentParser()
ap.add_argument("--check", action="store_true")
ap.add_argument("--part", type=int, choices=[1, 2, 3])
ap.add_argument("--all-eligible", action="store_true")
args = ap.parse_args()

T0 = time.time()
db.use_derived_colors()
con = db.connect()
RAW = pd.read_parquet(PLACEBO)
if not args.check:
    os.makedirs(OUT, exist_ok=True)
    pd.set_option("display.width", 200, "display.max_columns", 30, "display.max_rows", 200,
                  "display.float_format", "{:.3f}".format)
    TW = tweak_doses()
    PAIRS = did.placebo_pairs(RAW)
    if len(PAIRS) != 463 or PAIRS[PAIRS.patch == "first"].z.pipe(robust_sd).round(2) != CLEAN_FACTOR:
        raise SystemExit("placebo_h3 does not give 463 pairs and the 4.10 factor")

if args.check:
    check(con, RAW)
if not args.check and args.part in (None, 1):
    TAB = window_table(PAIRS, TW)
    SP = window_spearman(TAB)
    TAB.to_csv(f"{OUT}/m_windows.csv", index=False)
    SP.to_csv(f"{OUT}/m_window_spearman.csv", index=False)
    print(TAB.to_string(index=False), SP.to_string(index=False), sep="\n", flush=True)
if not args.check and args.part in (None, 2):
    D = exposures(con, PAIRS, TW)
    keep = PAIR + ["patch", "z", "beta", "se", "n_treated_offers"] + [
        c for c in D.columns if c.endswith(("_before", "_after"))
        and c.split("_")[0] in ("offers", "runs", "screen", "run", "signed")]
    D[keep].to_csv(f"{OUT}/m_exposure_pairs.csv", index=False)
    missing = int(D.screen_exposure_after.isna().sum() + D.screen_exposure_before.isna().sum())
    print("pairs without exposure in a block:", missing)
    print(D.groupby(["patch", "color"])[["screen_exposure_after", "run_exposure_after",
                                         "signed_exposure_after", "screen_subst_after",
                                         "run_subst_after", "run_exposure_before"]].mean())
    for c in ("screen_exposure", "run_exposure", "signed_exposure"):
        print(c, "corr before/after",
              round(D[f"{c}_before"].corr(D[f"{c}_after"]), 3))
    C = corr_table(D)
    C.to_csv(f"{OUT}/m_exposure_corr.csv", index=False)
    print(C.to_string(index=False), flush=True)
if not args.check and args.part in (None, 3):
    print("zero-tweak character-windows:", clean_windows(TW))
    F, S = clean_placebo(con, TW, int(RAW.min_offers.iloc[0]), args.all_eligible)
    F.to_csv(f"{OUT}/m_clean_placebo.csv", index=False)
    S.to_csv(f"{OUT}/m_clean_summary.csv", index=False)
    print(F.round(4).to_string(index=False), S.T.to_string(), sep="\n", flush=True)

rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2 ** 30
print(f"done in {time.time() - T0:.0f} s; peak RSS {rss:.1f} GB")
