"""Synthetic stand-ins for the saved fits in data/analysis/, for the export's tests and the
dashboard's sample data (scripts/make_sample_results.py). Nothing here comes from run data.

write_inputs(analysis_dir, ref_dir) writes parquet files with the column layout notebooks
02 and 03 save (did_main, did_h3, robustness checks, event_studies,
did_second_patch_checks, anticipation_main, offer_rate) and a matching reference folder
(tweak_sizes.csv, builds.csv, beta_exposure.csv). Cards are named SAMPLE_01, SAMPLE_02, ...
so the numbers can't be mistaken for results; windows use the real stable builds.

write_numbers_inputs(analysis_dir, results_dir, ref_dir) adds what spirometry.numbers reads:
the export of those fits (meta.json with a synthetic build stamp), the placebo summary and
spirometry.sensitivity's rulers and se_inflation tables.
"""
import json
import pathlib

import numpy as np
import pandas as pd

CHARACTERS = ["ironclad", "silent", "defect", "necrobinder", "regent"]
PATCHES = {  # stable build -> (before, after, release date, weeks before, weeks after)
    "v0.103.2": ("v0.99.1", "v0.103.2", "2026-04-16", 4, 16),
    "v0.107.1": ("v0.103.3", "v0.107.1", "2026-06-18", 2, 10),
}
BUILDS = [("v0.99.1", "2026-03-17"), ("v0.103.2", "2026-04-16"), ("v0.103.3", "2026-05-29"),
          ("v0.107.1", "2026-06-18")]
SLOPE = {"v0.103.2": 1.2, "v0.107.1": 0.4}   # planted log-odds slope per patch
TAU = 0.2                                    # planted between-card scatter (log-odds)

TWEAK_COLUMNS = ["card_patch_id", "card_id", "color", "stable_build", "before_builds",
                 "after_builds", "main_field", "old", "new", "log_ratio", "upgrade_field",
                 "upgrade_old", "upgrade_new", "upgraded_log_ratio", "upgrade_only",
                 "mixed_direction", "solo_estimable", "direction", "note"]


def tweak_table(n_first=14, n_second=9, rng=None):
    rng = rng or np.random.default_rng(0)
    rows, i = [], 0
    for stable, n in [("v0.103.2", n_first), ("v0.107.1", n_second)]:
        before, after = PATCHES[stable][:2]
        for k in range(n):
            i += 1
            card = f"SAMPLE_{i:02d}"
            old = int(rng.integers(3, 15))
            new = max(1, old + int(rng.choice([-3, -2, -1, 1, 2, 3, 4])))
            r = dict(card_patch_id=f"{card}@{stable}/patch", card_id=card,
                     color=CHARACTERS[i % len(CHARACTERS)], stable_build=stable,
                     before_builds=before, after_builds=after, main_field="damage",
                     old=str(old), new=str(new), log_ratio=f"{np.log(new / old):.4f}",
                     upgrade_field="", upgrade_old="", upgrade_new="",
                     upgraded_log_ratio="", upgrade_only="no", mixed_direction="no",
                     solo_estimable="yes", direction="1", note="synthetic")
            if k == 0:                      # one upgrade-only tweak per patch
                r.update(main_field="", old="", new="", log_ratio="",
                         upgrade_field="upgrade.damage", upgrade_old="+3", upgrade_new="+5",
                         upgraded_log_ratio="0.1823", upgrade_only="yes")
            if k == 1 and stable == "v0.103.2":   # one mixed-direction tweak
                r.update(mixed_direction="yes")
            rows.append(r)
    rows.append(dict(rows[-1], card_patch_id="SAMPLE_99@v0.107.1/patch", card_id="SAMPLE_99",
                     color="colorless", solo_estimable="no",
                     note="synthetic, not solo-estimable"))
    return pd.DataFrame(rows, columns=TWEAK_COLUMNS)


def _variant(main, rng, se_mult=1.0, shift_in_se=0.3, horizon=None):
    """Another fit of the same tweaks (fixed horizon or a robustness check): beta moved by
    about shift_in_se main se's, se scaled."""
    v = main.copy()
    v["se"] = main.se * se_mult
    v["beta"] = main.beta * (0.9 if horizon else 1.0) + rng.normal(0, shift_in_se, len(v)) * main.se
    v["ci_lo"], v["ci_hi"] = v.beta - 1.96 * v.se, v.beta + 1.96 * v.se
    k = main.treated_rate_before * (1 - main.treated_rate_before)
    v["beta_lo"], v["se_lo"] = v.beta / k, v.se / k
    if horizon is not None:
        v["max_week_after"] = float(horizon)
        v["after_week_max"] = horizon
    return v


def _fit_rows(tw, rng, horizon=None):
    """did.run_all through the notebook's tidy(): one row per solo-estimable tweak."""
    rows = []
    for t in tw[tw.solo_estimable == "yes"].to_dict("records"):
        up = t["upgrade_only"] == "yes"
        x = float(t["upgraded_log_ratio"] if up else t["log_ratio"])
        p0 = float(rng.uniform(0.06, 0.45))
        lo_true = SLOPE[t["stable_build"]] * x + rng.normal(0, TAU)
        k = p0 * (1 - p0)
        n_tr = int(rng.integers(300, 900) if up else rng.integers(3000, 30000))
        se = float(np.sqrt(k / n_tr) * rng.uniform(1.4, 1.8) * (1.3 if horizon else 1))
        beta = lo_true * k + rng.normal(0, se)
        c0 = float(rng.uniform(0.2, 0.32))
        c1 = c0 + float(rng.normal(0, 0.004))
        weeks_after = PATCHES[t["stable_build"]][4]
        row = dict(t, fit_on="upgraded offers" if up else "all offers", error="",
                   placebo_error="", beta=beta, se=se, se_hc=se / 1.03, se_iid=se,
                   ci_lo=beta - 1.96 * se, ci_hi=beta + 1.96 * se,
                   max_week_after=np.nan if horizon is None else float(horizon),
                   card_act_fe="False", picked_screens_only="False",
                   after_week_max=weeks_after if horizon is None else horizon,
                   n_offers=int(n_tr * 40), n_singletons_dropped=int(rng.integers(0, 30)),
                   n_runs=int(n_tr * 12), n_treated_offers=n_tr,
                   treated_rate_before=p0, treated_rate_after=p0 + beta + (c1 - c0),
                   control_rate_before=c0, control_rate_after=c1,
                   formula="picked ~ treat_post | card_id^upg + card_id^group + block^group"
                           " + act + asc",
                   beta_lo=beta / k, se_lo=se / k,
                   placebo_beta=np.nan, placebo_se=np.nan, placebo_n_offers=np.nan,
                   placebo_treated_rate_before=np.nan)
        if up:
            n_pl = n_tr * 8
            se_pl = float(np.sqrt(k / n_pl) * 1.6)
            row.update(placebo_beta=float(rng.normal(0, se_pl)), placebo_se=se_pl,
                       placebo_n_offers=n_pl * 40, placebo_treated_rate_before=p0)
        rows.append(row)
    return pd.DataFrame(rows).set_index("card_patch_id")


def _event_studies(main, tw, rng):
    out = []
    for cpid, m in main.iterrows():
        before_weeks, after_weeks = PATCHES[m.stable_build][3:]
        cells = ([(w, "before") for w in range(-before_weeks, -1)]
                 + [(w, "before") for w in range(0, 3)]
                 + [(w, "after") for w in range(0, min(after_weeks, 9))])
        for w, blk in cells:
            n = int(m.n_treated_offers / 8) if blk == "after" or w < 0 else 60
            if blk == "before" and w == 2:
                n = 5                                   # a thin cell the export drops
            se = m.se * np.sqrt(8) * rng.uniform(0.9, 1.2)
            mean = m.beta * (1 - np.exp(-(w + 1) / 2)) if blk == "after" else 0.0
            out.append(dict(week=w, block=blk, coef=mean + rng.normal(0, se), se=se,
                            n_offers=n, formula="picked ~ treated x (week, block) | ...",
                            card_patch_id=cpid, error=""))
    return pd.DataFrame(out)


def _second_patch(main, rng):
    rows = []
    for cpid, m in main[main.stable_build == "v0.107.1"].iterrows():
        for variant, shift in [("main", 0.0), ("pooled before", 0.01),
                               ("no first-patch controls", 0.0)]:
            rows.append(dict(card_patch_id=cpid, card=m.card_id, variant=variant,
                             beta=m.beta + shift * rng.normal() if variant != "main" else m.beta,
                             se=m.se * (0.8 if variant == "pooled before" else 1.0),
                             n_treated_offers=m.n_treated_offers, n_controls=60, error=np.nan))
    return pd.DataFrame(rows)


def _anticipation(main, tw, rng):
    rows = []
    for i, (cpid, m) in enumerate(main.iterrows()):
        informative = m.stable_build == "v0.107.1" and i % 3 != 0 or i % 7 == 2
        pre = int(rng.integers(2500, 12000)) if informative else int(rng.integers(100, 1900))
        days = 30 if informative else int(rng.integers(1, 3))
        why = [] if informative else [f"{pre} treated offers pre-beta (< 2000)",
                                      f"{days} days pre-beta (< 3)"]
        se = float(m.se * 1.3)
        b = float(rng.normal(0, se * 1.5))
        clear = abs(m.beta) > 2 * m.se
        share = 0.3
        total = m.beta + share * b
        rows.append(dict(upgrade_only=m.upgrade_only, lead_days=str(int(rng.choice([14, 28, 42]))),
                         card_patch_id=cpid, card_id=m.card_id, color=m.color,
                         builds="v0.99.1" if m.stable_build == "v0.103.2" else "v0.103.2 v0.103.3",
                         status="informative" if informative else "uninformative",
                         reason="; ".join(why), beta_postbeta=b, se=se,
                         ci_lo=b - 1.96 * se, ci_hi=b + 1.96 * se,
                         n_treated_offers_pre=pre, n_treated_offers_post=pre * 2,
                         days_pre=days, days_post=30, main_postbeta_share=share,
                         beta_main=m.beta, se_main=m.se,
                         ratio_to_main=b / m.beta if clear else np.nan,
                         total_implied=total,
                         share_before_release=b / total if clear else np.nan))
    return pd.DataFrame(rows)


def _offer_rate(main, rng):
    rows = []
    for i, (cpid, m) in enumerate(main.iterrows()):
        z = float(rng.normal(0, 1.2)) + (6.0 if i == 3 else 0.0)
        rows.append(dict(card_patch_id=cpid, card=m.card_id, rarity="Common",
                         log_share_ratio=0.01 + 0.02 * z, controls_median=0.01,
                         z_spread=z, z_binom=z, flag=abs(z) > 3,
                         z_spread_rarity=z, z_binom_rarity=z, flag_rarity=abs(z) > 3,
                         rarity_note=""))
    return pd.DataFrame(rows).set_index("card_patch_id")


def write_inputs(analysis_dir, ref_dir, seed=0, n_first=14, n_second=9):
    """Write the synthetic analysis parquet files and reference CSVs. Returns the tweak
    table."""
    analysis_dir, ref_dir = pathlib.Path(analysis_dir), pathlib.Path(ref_dir)
    analysis_dir.mkdir(parents=True, exist_ok=True)
    ref_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    tw = tweak_table(n_first, n_second, rng)
    tw.to_csv(ref_dir / "tweak_sizes.csv", index=False)
    pd.DataFrame(BUILDS, columns=["build_id", "release_date"]).assign(branch="stable")[
        ["build_id", "branch", "release_date"]].to_csv(ref_dir / "builds.csv", index=False)
    ex = tw[["card_patch_id", "card_id", "color", "stable_build", "upgrade_only"]].copy()
    ex["stable_date"] = ex.stable_build.map({s: p[2] for s, p in PATCHES.items()})
    ex["lead_days"] = 28
    ex["first_beta_date"] = (pd.to_datetime(ex.stable_date) - pd.Timedelta(days=28)).dt.strftime("%Y-%m-%d")
    ex["first_beta_build"] = "beta"
    ex.to_csv(ref_dir / "beta_exposure.csv", index=False)

    main = _fit_rows(tw, rng)
    main.to_parquet(analysis_dir / "did_main.parquet")
    _variant(main, rng, 1.3, 0.8, horizon=3).to_parquet(analysis_dir / "did_h3.parquet")
    for name, se_mult, shift in [("pooled_groups", 1.0, 0.1), ("tagged", 2.0, 1.9),
                                 ("untagged", 1.1, 0.5), ("drop_shared_screens", 1.0, 0.05)]:
        _variant(main, rng, se_mult, shift).to_parquet(analysis_dir / f"did_{name}.parquet")
    _event_studies(main, tw, rng).to_parquet(analysis_dir / "event_studies.parquet")
    _second_patch(main, rng).to_parquet(analysis_dir / "did_second_patch_checks.parquet")
    _anticipation(main, tw, rng).to_parquet(analysis_dir / "anticipation_main.parquet")
    _offer_rate(main, rng).to_parquet(analysis_dir / "offer_rate.parquet")
    return tw


SAMPLE_STAMP = dict(tables_built_at_utc="2026-01-01T00:00:00+00:00", snapshot_pages="12",
                    snapshot_last_page="11", parser_version="sample")


def _placebo_summary(rng):
    """placebo_diagnostics_summary.csv's layout (did.placebo_summary, both dedupe settings)."""
    rows = []
    for dedupe, n_all in [(False, 460), (True, 250)]:
        for split, level, sd, n in [("all", "all", 3.5, n_all),
                                    ("patch", "first", 4.5, n_all * 3 // 5),
                                    ("patch", "second", 2.2, n_all * 2 // 5)]:
            z = rng.normal(0, sd, n)
            rows.append(dict(split=split, level=level, n_fits=n,
                             n_tweaks=23 if level == "all" else 14, mean_z=z.mean(), sd_z=z.std(ddof=1),
                             share_abs_z_gt2=(abs(z) > 2).mean(),
                             share_abs_z_gt3=(abs(z) > 3).mean(), median_abs_z=np.median(abs(z)),
                             robust_sd_z=1.4826 * np.median(abs(z - np.median(z))),
                             n_failed=0.0 if level == "all" else np.nan, dedupe=dedupe))
    return pd.DataFrame(rows)


def write_numbers_inputs(analysis_dir, results_dir, ref_dir, seed=0, stamp=None):
    """Everything spirometry.numbers reads, synthetic: write_inputs, the export into
    results_dir (meta.json given a build stamp, `stamp` or SAMPLE_STAMP, and sample: true),
    the placebo summary and spirometry.sensitivity's rulers and se_inflation tables in
    analysis_dir/writeup. Returns the tweak table."""
    from spirometry import export, sensitivity as S

    analysis_dir, results_dir = pathlib.Path(analysis_dir), pathlib.Path(results_dir)
    rng = np.random.default_rng(seed + 1)
    tw = write_inputs(analysis_dir, ref_dir, seed=seed)
    export.export(analysis_dir, results_dir, ref_dir, sample=True)
    m = json.loads((results_dir / "meta.json").read_text())
    m.update(stamp or SAMPLE_STAMP)
    (results_dir / "meta.json").write_text(json.dumps(m, indent=2) + "\n")

    summary = _placebo_summary(rng)
    summary.to_csv(analysis_dir / "placebo_diagnostics_summary.csv", index=False)

    def fits(name):          # the saved fits hold the tweak columns as text here
        f = pd.read_parquet(analysis_dir / f"did_{name}.parquet")
        for c in ["log_ratio", "upgraded_log_ratio", "direction"]:
            f[c] = pd.to_numeric(f[c], errors="coerce")
        return S.prepare(f)

    D, Dw = fits("h3"), fits("main")
    factors = S.placebo_factors(summary)
    out = analysis_dir / "writeup"
    out.mkdir(exist_ok=True)
    rulers = pd.concat([S.ruler_table(D, s) for s in S.SPECS], ignore_index=True)
    se = pd.concat([S.se_inflation_table(S.dose_line(d, s), factors, label=f"{s}, {lab}")
                    for s in S.SPECS
                    for d, lab in [(D, "weeks 0-3 (did_h3)"), (Dw, "all weeks (did_main)")]],
                   ignore_index=True)
    for name, df in [("rulers", rulers), ("se_inflation", se)]:
        df.insert(0, "fits", "did_h3")
        df.to_csv(out / f"{name}.csv", index=False)
    return tw
