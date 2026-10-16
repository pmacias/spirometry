"""Synthetic stand-ins for the saved fits in data/analysis/, for the export's tests and the
dashboard's sample data (scripts/make_sample_results.py). Nothing here comes from run data.

write_inputs(analysis_dir, ref_dir) writes parquet files with the column layout notebooks
02 and 03 save (did_main, did_h3, robustness checks, event_studies,
did_second_patch_checks, anticipation_main, offer_rate) and a matching reference folder
(tweak_sizes.csv, builds.csv, beta_exposure.csv). Cards are named SAMPLE_01, SAMPLE_02, ...
so the numbers can't be mistaken for results; windows use the real stable builds.

write_numbers_inputs(analysis_dir, results_dir, ref_dir) adds what spirometry.numbers reads:
the export of those fits against a tiny synthetic runs.duckdb (write_sample_db: build_info
and run start times), a snapshot.log, the placebo summary and spirometry.sensitivity's
rulers, se_inflation and calibrated_counts tables.
"""
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
                   n_control_cards=60 + n_tr % 40,     # no rng draw: other draws unchanged
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


SAMPLE_BUILD_INFO = dict(parser_version="sample", pages_parsed="12", last_page="11",
                         built_at_utc="2026-01-01T00:00:00+00:00",
                         records_read="11234", duplicate_records_dropped="321",
                         duplicates_with_different_content="0",
                         solo_run_keys_multi_record="7", primary_offers_dedup_removed="150",
                         solo_run_keys_retried="3", primary_run_keys_retried="2")
# (start_time UTC, primary?): the primary runs span 2026-03-18 .. 2026-07-02; the
# non-primary records (a playtest build, a run started before its build's release) lie
# outside it, so the two ranges differ.
SAMPLE_RUN_STARTS = [("2026-03-18 09:00:00", True), ("2026-05-02 23:59:59", True),
                     ("2026-07-02 18:30:00", True), ("2026-02-27 12:00:00", False),
                     ("2026-07-04 08:00:00", False)]


def write_sample_db(path, build_info=None, runs=True):
    """A tiny synthetic runs.duckdb: build_info and, with runs=True, a `runs` table with the
    columns runs.PRIMARY_RUN_FILTER and the export's play dates read."""
    import duckdb
    con = duckdb.connect(str(path))
    try:
        con.execute("CREATE TABLE build_info (key VARCHAR, value VARCHAR)")
        con.executemany("INSERT INTO build_info VALUES (?, ?)",
                        [[k, v] for k, v in (build_info or SAMPLE_BUILD_INFO).items()])
        if runs:
            con.execute("""CREATE TABLE runs (start_time TIMESTAMP, n_players INTEGER,
                           is_custom BOOLEAN, is_modded BOOLEAN, released BOOLEAN,
                           before_release BOOLEAN, neow_start BOOLEAN)""")
            con.executemany("INSERT INTO runs VALUES (?, 1, false, false, ?, ?, true)",
                            [[t, primary, False] if primary or t < "2026-03"
                             else [t, True, True] for t, primary in SAMPLE_RUN_STARTS])
    finally:
        con.close()
    return path


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


def write_numbers_inputs(analysis_dir, results_dir, ref_dir, seed=0, triage_dir=None):
    """Everything spirometry.numbers reads, synthetic: write_inputs; the export into
    results_dir with a synthetic runs.duckdb (write_sample_db, beside results_dir), so
    meta.json has a build stamp, play dates and dedup counts (and sample: true); the placebo
    fits (all weeks) and diagnostics; spirometry.sensitivity's tables (sensitivity.run) in
    analysis_dir/writeup; IV-primer-shaped tables; notebook 01's audit summary; synthetic
    triage outputs (in triage_dir, default beside results_dir, under out_final/) and
    spirometry.checks' design_checks.csv; and a snapshot.log beside results_dir. Returns the
    tweak table."""
    from spirometry import checks, did, export, sensitivity as S

    analysis_dir, results_dir = pathlib.Path(analysis_dir), pathlib.Path(results_dir)
    ref_dir = pathlib.Path(ref_dir)
    rng = np.random.default_rng(seed + 1)
    tw = write_inputs(analysis_dir, ref_dir, seed=seed)
    db = write_sample_db(results_dir.parent / "sample_runs.duckdb")
    export.export(analysis_dir, results_dir, ref_dir, db=db, sample=True)
    write_snapshot_log(results_dir.parent / "snapshot.log")
    (ref_dir / "card_changes.csv").write_text(
        "card_id,stable_build,change_kind\n" + "".join(
            f"{r.card_id},{r.stable_build},tweak\n" for r in tw.itertuples())
        + "REWORKED,v0.103.2,rework\nREWORKED,v0.103.2,rework+cost_change\n"
          "WORDING,v0.107.1,text_only\n")

    summary = _placebo_summary(rng)
    summary.to_csv(analysis_dir / "placebo_diagnostics_summary.csv", index=False)

    def fits(name):          # the saved fits hold the tweak columns as text here
        f = pd.read_parquet(analysis_dir / f"did_{name}.parquet")
        for c in ["log_ratio", "upgraded_log_ratio", "direction"]:
            f[c] = pd.to_numeric(f[c], errors="coerce")
        return S.prepare(f)

    D = fits("h3")
    placebo = placebo_fits(D, rng).assign(min_offers=51, seed=0)
    placebo["treated_rate_before"] = rng.uniform(0.05, 0.4, len(placebo))   # for the terciles
    placebo["n_runs"] = rng.integers(20000, 70000, len(placebo))
    placebo.to_parquet(analysis_dir / "placebo_main.parquet")
    main = pd.read_parquet(analysis_dir / "did_main.parquet")
    pvr = did.placebo_vs_real(main, placebo, ref=ref_dir)
    pvr.to_csv(analysis_dir / "placebo_diagnostics_vs_real.csv", index=False)
    did.placebo_vs_real_by_patch(pvr, placebo, ref=ref_dir).to_csv(
        analysis_dir / "placebo_diagnostics_vs_real_by_patch.csv", index=False)
    did.placebo_spread_by_feature(placebo, ref=ref_dir).to_csv(
        analysis_dir / "placebo_diagnostics_spread_by_feature.csv", index=False)
    second = pd.read_parquet(analysis_dir / "did_second_patch_checks.parquet")
    second.to_parquet(analysis_dir / "second_patch_checks_h3.parquet")
    S.run(analysis_dir, analysis_dir / "writeup", n_sim=20, ref=ref_dir)
    write_iv_tables(analysis_dir / "writeup")
    write_audit_summary(analysis_dir)
    triage_dir = pathlib.Path(triage_dir or results_dir.parent / "triage")
    write_triage_outputs(triage_dir / "out_final", D, rng)
    rows, _ = checks.build(triage_dir, analysis_dir, results_dir,
                           old_analysis=analysis_dir.parent / "no_old_tables")
    rows.to_csv(analysis_dir / "writeup" / "design_checks.csv", index=False)
    return tw


def write_iv_tables(out):
    """spirometry.iv_sim's tables, in its columns, with made-up values."""
    out = pathlib.Path(out)
    q = ["naive", "itt", "first_stage", "iv"]
    common = dict(F=5000.0, n_runs=50000, share_offered=0.3, share_picked=0.09,
                  win_pickers=0.43, win_non_pickers=0.30)
    pd.DataFrame([dict(quantity=k, label=k, estimate=e, se=s, truth=t, **common)
                  for k, e, s, t in [("naive", 0.13, 0.008, 0.1), ("itt", 0.027, 0.005, np.nan),
                                     ("first_stage", 0.3, 0.004, np.nan),
                                     ("iv", 0.09, 0.015, 0.1)]]).to_csv(
        out / "iv_sim_single.csv", index=False)
    rng = np.random.default_rng(1)
    pd.DataFrame(dict(draw=range(60), naive=rng.normal(0.133, 0.012, 60), naive_se=0.012,
                      itt=0.03, itt_se=0.007, first_stage=0.3, fs_se=0.006, F=2500.0,
                      iv=rng.normal(0.103, 0.025, 60), iv_se=0.024)).to_csv(
        out / "iv_sim_draws.csv", index=False)
    pd.DataFrame(dict(estimator=["naive", "iv"], mean=[0.133, 0.103],
                      sd_across_draws=[0.012, 0.025], mean_reported_se=[0.012, 0.024],
                      share_ci_covers_truth=[0.24, 0.94])).to_csv(
        out / "iv_sim_draws_summary.csv", index=False)
    pd.DataFrame(dict(pick_intercept=[-1, -6], first_stage=[0.3, 0.004], F=[650.0, 6.0],
                      share_F_below_10=[0.0, 0.92], naive_median=[0.13, 0.14],
                      naive_p10=[0.1, -0.29], naive_p90=[0.16, 0.38], iv_median=[0.09, -0.23],
                      iv_p10=[0.04, -4.9], iv_p90=[0.16, 4.4])).to_csv(
        out / "iv_sim_weak.csv", index=False)
    pd.DataFrame(dict(case=["clean", "offer depends on skill"], naive=[0.13, 0.15],
                      iv=[0.10, 0.17], first_stage=[0.3, 0.36], iv_bias=[0.003, 0.066])).to_csv(
        out / "iv_sim_broken.csv", index=False)
    pd.DataFrame(dict(quantity=["IV estimate", "true average effect, among runs that picked X",
                                "true average effect, among all runs"],
                      effect=[0.133, 0.129, 0.100])).to_csv(out / "iv_sim_het.csv", index=False)
    pd.DataFrame(dict(skill_on_win=[0.0, 0.05], naive=[0.10, 0.13], iv=[0.10, 0.10],
                      naive_bias=[0.0, 0.03], iv_bias=[0.003, 0.003])).to_csv(
        out / "iv_sim_confounding.csv", index=False)


AUDIT_ROWS = [  # key, value, unit (notebook 01's audit_summary.csv layout)
    ("pages", 12, "count"), ("records", 11000, "count"), ("repeats_dropped", 234, "count"),
    ("distinct_runs", 10980, "count"), ("distinct_runs_per_build_sum", None, "count"),
    ("run_keys_in_several_builds", 7, "count"), ("primary_runs", 8000, "count"),
    ("primary_share", 0.7286, "share"), ("lag_median_days", 16.8, "days"),
    ("lag_share_over_30d", 0.44, "share"), ("thin_builds", 1, "count"),
    ("groups_0_103_2_sd_z", 4.01, "z"), ("groups_0_103_2_spearman", 0.95, "corr"),
    ("win_rate_v0_103_2_tagged", 0.27, "rate"), ("win_rate_v0_103_2_untagged", 0.20, "rate"),
    ("win_rate_v0_103_2_gap", 0.07, "rate")]


def write_audit_summary(analysis_dir):
    """notebook 01's saved aggregates, made up: audit_summary.csv (its per-build distinct
    sum equals the sample snapshot.log's total, as on the real tables),
    audit_runs_per_build.csv and audit_upload_lag.csv."""
    a = pathlib.Path(analysis_dir)
    rows = [dict(key=k, label=k.replace("_", " "),
                 value=SAMPLE_LOG_TOTAL[1] if v is None else v, unit=u,
                 population="synthetic", definition="synthetic") for k, v, u in AUDIT_ROWS]
    pd.DataFrame(rows).to_csv(a / "audit_summary.csv", index=False)
    b = pd.DataFrame(BUILDS + [("v0.99.0", "2026-03-12"), ("v0.104.0", "2026-04-23")],
                     columns=["build_id", "release"])
    b["branch"] = np.where(b.build_id.isin(["v0.99.0", "v0.104.0"]), "beta", "stable")
    b["runs"] = [3000, 2500, 1500, 4000, 300, 900]
    b["primary"] = (b.runs * 0.73).round().astype(int)
    b["records"], b["primary_finished"] = (b.runs * 1.3).astype(int), (b.primary * 0.8).astype(int)
    b["thin"] = b.primary < 400
    b.to_csv(a / "audit_runs_per_build.csv", index=False)
    days = np.array([0, 1, 7, 30, 90, 180])
    pd.DataFrame(dict(days=days, share_all=np.exp(-days / 60), share_tagged=np.exp(-days / 150),
                      share_untagged=np.exp(-days / 20), n_all=8000, n_tagged=2000,
                      n_untagged=6000)).to_csv(a / "audit_upload_lag.csv", index=False)


def write_triage_outputs(out, D, rng):
    """The triage scripts' saved CSVs (i, j, g3/g4, l), in their columns, made up from the
    prepared fit D (did_h3): enough for spirometry.checks, no meaning."""
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    L = D[(D.mixed_direction != "yes") & (D.upgrade_only != "yes")]
    sec = L[L.patch == "second"]
    rows = []
    for horizon in ["weeks 0-3", "all weeks"]:
        for cp, t in sec.iterrows():
            se = float(rng.uniform(0.005, 0.012))
            b = float(rng.normal(0, 2 * se))
            k = t.treated_rate_before * (1 - t.treated_rate_before)
            rows.append(dict(card_patch_id=cp, card_id=t.card_id, color=t.color,
                             horizon=horizon, x=t.x, beta=b, se=se, se_hc=se, beta_lo=b / k,
                             se_lo=se / k, real_beta_lo=t.beta_lo, n_offers=100000,
                             n_treated_offers=5000, n_control_cards=70, after_week_max=3,
                             treated_rate_before=t.treated_rate_before))
    pd.DataFrame(rows).to_csv(out / "i_fake_patch.csv", index=False)
    pre = L.assign(pre_lo=rng.normal(0, 0.1, len(L)), pre_se_lo=0.08)
    pre["pre_pp"], pre["pre_se_pp"], pre["pre_n"] = 100 * pre.pre_lo * 0.16, 1.3, 3000
    pre["eff_pp"] = 100 * pre.beta
    pre["opposes"] = np.sign(pre.pre_lo) == -np.sign(pre.x)
    pre[["card_id", "patch", "x", "pre_lo", "pre_se_lo", "pre_pp", "pre_se_pp", "pre_n",
         "beta_lo", "se_lo", "eff_pp", "opposes"]].rename_axis("card_patch_id").reset_index() \
        .to_csv(out / "j_premove.csv", index=False)
    pd.DataFrame([dict(model=m, patch=p, n=n, slope_x=1.4, se_x=0.2, pre_coef=pc, pre_se=ps,
                       intercept=0.0, tau2=0.06)
                  for m, p, n, pc, ps in [("effect ~ x", "first", 13, np.nan, np.nan),
                                          ("effect ~ x + pre (declared)", "first", 13, 0.7, 0.5),
                                          ("effect ~ x + pre (comparison only)", "second", 8,
                                           -0.1, 0.3)]]).to_csv(out / "j_models.csv",
                                                                 index=False)
    pd.DataFrame([dict(week=w, n_tweaks=13, median_offers=900, slope=1.3 + 0.05 * w, se=0.22,
                       intercept=0.0, tau2=0.05, slope_vs_week_m1=1.35, se_vs_week_m1=0.22)
                  for w in range(6)]).to_csv(out / "j_weekly.csv", index=False)
    g3 = []
    for cp, t in L.iterrows():
        for tfe in (False, True):
            k = t.treated_rate_before * (1 - t.treated_rate_before)
            b = float(t.beta + rng.normal(0, t.se))
            g3.append(dict(card_patch_id=cp, card_id=t.card_id, patch=t.patch, x=t.x,
                           token_fe=tfe, error="", beta=b, se_run=2.5 * t.se,
                           se_tok=3.2 * t.se, beta_lo=b / k, se_lo=2.5 * t.se / k,
                           se_lo_tok=3.2 * t.se / k, n_treated_before=300, n_treated_after=300))
    pd.DataFrame(g3).to_csv(out / "g3_token_fits.csv", index=False)
    pd.DataFrame([dict(window="w", patch=p, pseudo_card=f"P{i}", error="",
                       beta=float(rng.normal(0, 0.03)), se_run=0.015, se_tok=0.02)
                  for i, p in enumerate(["first", "second"] * 10)]).to_csv(
        out / "g4_token_placebo.csv", index=False)
    for scope, shift in [("other", 0.004), ("all", 0.003)]:
        c = D.assign(beta=D.beta + shift * np.where(D.patch == "first", 1, 0),
                     n_control_cards=280)
        c["beta_lo"] = c.beta / (c.treated_rate_before * (1 - c.treated_rate_before))
        c.rename_axis("card_patch_id").reset_index()[
            ["card_patch_id", "beta", "se", "beta_lo", "se_lo", "n_control_cards"]].to_csv(
            out / f"did_h3_ctrl_{scope}.csv", index=False)


def placebo_fits(D, rng, n_cards=12, sd={"first": 4.5, "second": 2.2}, horizons=(None,)):
    """placebo_main.parquet's layout (did.placebo_all): for each tweak in D (a prepared fit)
    n_cards pseudo cards with z ~ N(0, sd of its patch), at each max_week_after in
    `horizons` (None = all weeks, as the saved run). Pseudo cards are shared within a
    color and patch, as real windows share them."""
    rows = []
    for h in horizons:
        for cpid, t in D.iterrows():
            for k in range(n_cards):
                se = float(rng.uniform(0.004, 0.01))
                z = float(rng.normal(0, sd[t.patch]))
                rows.append(dict(card_patch_id=cpid, pseudo_card=f"PSEUDO_{t.color}_{k:02d}",
                                 beta=z * se, se=se, z=z, n_runs=5000, treated_rate_before=0.2,
                                 error="", card_id=t.card_id, color=t.color,
                                 stable_build=t.stable_build, patch=t.patch, fit_on=t.fit_on,
                                 se_hc=se, se_iid=se, n_offers=100000,
                                 n_treated_offers=int(rng.integers(2000, 30000)),
                                 max_week_after=h))
    return pd.DataFrame(rows)


SAMPLE_LOG_TOTAL = (11234, 10987)    # records, distinct


def write_snapshot_log(path, pages=12, end=True):
    """A snapshot.log in scripts/snapshot_export.py's format: one line per page (numbered
    from 1), "reached end of export", then --count-only's table ending in "total"."""
    lines = [f"2026-01-01 00:{i:02d}:00-0700 page {i}: 1000 runs, 3.1 MB, remaining budget "
             f"{100 - i}" for i in range(1, pages + 1)]
    if end:
        lines.append("2026-01-01 00:59:00-0700 reached end of export")
    lines += ["build                         runs     dedup",
              "v0.99.1                       9000      8800",
              "v0.103.2                      2234      2187",
              f"total                      {SAMPLE_LOG_TOTAL[0]:>7d}   {SAMPLE_LOG_TOTAL[1]:>7d}",
              "records with a player_token: 1234"]
    pathlib.Path(path).write_text("\n".join(lines) + "\n")
    return path
