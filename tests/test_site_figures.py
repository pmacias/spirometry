"""spirometry.site_figures on synthetic saved fits and test_did's synthetic offers."""
import numpy as np
import pandas as pd
import pytest

from spirometry import did, site_figures as sf
from test_did import CPID, ref, synth  # noqa: F401  (ref is a fixture)


def tweak(cpid, before, *, log_ratio, beta, se, mixed="no", n=1000, upgrade_only="no"):
    return dict(card_patch_id=cpid, card_id=cpid.split("@")[0], before_builds=before,
                after_builds="vB" if before == sf.FIRST_BEFORE else "vD", error="",
                solo_estimable="yes", mixed_direction=mixed, upgrade_only=upgrade_only,
                upgrade_old="", upgrade_new="", direction=1.0, log_ratio=log_ratio,
                beta=beta, se=se, ci_lo=beta - 1.96 * se, ci_hi=beta + 1.96 * se,
                n_treated_offers=n, n_control_cards=50, treated_rate_before=0.2,
                treated_rate_after=0.2 + beta, control_rate_before=0.25,
                control_rate_after=0.25)


def es_rows(cpid, pre_coefs, se=0.01):
    weeks = [-5, -4, -3, -2][-len(pre_coefs):]
    return [dict(week=w, block="before", coef=c, se=se, n_offers=500, card_patch_id=cpid,
                 error="") for w, c in zip(weeks, pre_coefs)] + \
           [dict(week=0, block="after", coef=0.1, se=se, n_offers=500, card_patch_id=cpid,
                 error="")]


@pytest.fixture
def saved():
    F = sf.FIRST_BEFORE
    h3 = pd.DataFrame([
        tweak("BIG@1", F, log_ratio=-0.4, beta=-0.10, se=0.01),       # pre-trend fails
        tweak("MID@1", F, log_ratio=-0.4, beta=-0.06, se=0.01),       # passes everything
        tweak("FLIP@1", F, log_ratio=-0.4, beta=-0.08, se=0.01),      # a check flips it
        tweak("BUFF@1", F, log_ratio=0.4, beta=0.20, se=0.01),        # not a nerf
        tweak("MIX@1", F, log_ratio=-0.4, beta=-0.20, se=0.01, mixed="yes"),
        tweak("N1@2", "vC", log_ratio=0.2, beta=0.001, se=0.01, n=900),
        tweak("N2@2", "vC", log_ratio=0.2, beta=0.002, se=0.01, n=5000),  # anticipation gap
        tweak("N3@2", "vC", log_ratio=0.2, beta=0.003, se=0.01, n=3000),  # clear at all weeks
        tweak("N4@2", "vC", log_ratio=0.2, beta=0.05, se=0.01, n=9000),   # clear at weeks 0-3
    ]).set_index("card_patch_id")
    main = h3.copy()
    main.loc["N3@2", "beta"] = 0.05
    orc = pd.DataFrame({"flag": False, "flag_rarity": False, "z_spread": 0.0, "z_binom": 0.0},
                       index=h3.index)
    es = pd.DataFrame(sum([es_rows(c, [0.05, -0.05, 0.05, -0.05] if c == "BIG@1"
                                   else [0.0, 0.001, 0.0, 0.001]) for c in h3.index], []))
    chk = h3.copy()
    chk.loc["FLIP@1", "beta"] = 0.01
    sp = pd.DataFrame([dict(card_patch_id=c, variant=v, beta=0.0, se=0.01)
                       for c in h3.index[h3.before_builds == "vC"]
                       for v in ["main", "pooled before"]])
    an = pd.DataFrame([dict(card_patch_id="N2@2", status="informative", beta_postbeta=0.05,
                            se=0.01),
                       dict(card_patch_id="N1@2", status="uninformative", beta_postbeta=0.5,
                            se=0.01)])
    return dict(main=main, h3=h3, orc=orc, es=es, sp_h3=sp, anticipation=an,
                checks_h3={"tagged": chk})


def test_pick_nerf(saved):
    pick, steps = sf.pick_nerf(saved)
    assert pick == "MID@1"
    assert steps.n.tolist() == [5, 3, 3, 2, 2, 1]


def test_pick_null(saved):
    pick, steps = sf.pick_null(saved)
    assert pick == "N1@2"                     # N2 has an informative anticipation gap
    assert steps.n.tolist() == [4, 4, 3, 2, 2, 1, 1, 1]
    saved["anticipation"] = saved["anticipation"].iloc[1:]
    assert sf.pick_null(saved)[0] == "N2@2"
    es = saved["es"]                          # a pre-trend drops N2 again
    es.loc[(es.card_patch_id == "N2@2") & (es.block == "before"), "coef"] = [.05, -.05, .05, -.05]
    assert sf.pick_null(saved)[0] == "N1@2"
    es.loc[es.card_patch_id == "N2@2", "coef"] = 0.0
    saved["checks_h3"]["tagged"].loc["N2@2", "beta"] = 0.05     # a check moves N2 by 4.8 se
    assert sf.pick_null(saved)[0] == "N1@2"


def test_patch_summary_and_kind(saved):
    s = sf.patch_summary(saved)
    assert s["first"]["n"] == 5 and s["second"]["n"] == 4
    assert s["second"]["n_clear"] == 0      # N4@2's z of 5 is 1.87 calibrated
    assert sf.kind_of(saved["h3"].loc["MIX@1"]) == "rework"
    assert sf.kind_of(saved["h3"].loc["BUFF@1"]) == "buff"
    assert sf.kind_of(saved["h3"].loc["MID@1"]) == "nerf"


def test_weekly_cells_match_event_study(ref):
    df = synth(n_runs=600, screens=10, effect=0.1, seed=3)
    es = did.fit_event_study(df, CPID, ref=ref).assign(card_patch_id=CPID)
    cells = sf.weekly_cells(df, CPID, es, ref=ref)
    d, _ = did._subset(df, CPID, ref=ref)
    tr = d[d.is_treated]
    assert cells.offers.sum() == len(tr) and cells.picks.sum() == tr.picked.sum()
    r = cells[cells.is_ref].iloc[0]
    assert r.coef == 0 and np.isnan(r.se)
    wk = d.week.clip(*sf.WEEKS)
    c0 = d[(~d.is_treated) & (wk == 0) & (d.block == "after")].picked.mean()
    got = cells[(cells.week == 0) & (cells.block == "after")].control_pick_rate.item()
    assert got == pytest.approx(c0)
    with pytest.raises(ValueError, match="differ"):
        sf.weekly_cells(df, CPID, es.assign(n_offers=es.n_offers + 1), ref=ref)


def test_card_entry_shape(ref, saved):
    df = synth(n_runs=600, screens=10, effect=0.1, seed=3)
    es = did.fit_event_study(df, CPID, ref=ref).assign(card_patch_id=CPID)
    cells = sf.weekly_cells(df, CPID, es, ref=ref)
    saved = dict(saved, h3=pd.concat([saved["h3"], pd.DataFrame(
        [tweak(CPID, "v1", log_ratio=0.29, beta=0.1, se=0.01)]).set_index("card_patch_id")]))
    tw = pd.read_csv(ref / "tweak_sizes.csv", dtype=str, keep_default_na=False) \
        .set_index("card_patch_id")
    b = pd.read_csv(ref / "builds.csv", dtype=str, keep_default_na=False).set_index("build_id")
    e = sf.card_entry(saved, CPID, cells, change_text="Damage 6 → 8", tweaks=tw, builds=b,
                      name="C0", kind="buff", note="n")
    assert e["patch"] == "second" and e["release_date"] == "2026-04-16"
    assert e["headline"]["beta_pts"] == 10.0 and e["note"] == "n"
    assert all(w["offers"] >= sf.MIN_OFFERS for w in e["weeks"])
    assert {"week", "block", "coef_pts", "se_pts", "offers", "picks", "pick_rate",
            "control_pick_rate"} == set(e["weeks"][0])


def _plot(patch):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cells = sf.es_cells(pd.DataFrame(es_rows("X@1", [0.0, 0.0])), "X@1")
    entry = {"patch": patch, "builds": "vA → vB", "headline": {
        "beta_pts": 10.0, "ci_lo_pts": 9.0, "ci_hi_pts": 11.0,
        "treated_rate_before": 0.2, "treated_rate_after": 0.3}}
    with plt.rc_context(sf.SITE_STYLE):
        return sf.plot_event_study_site(cells, entry, title="t", change_label="c")


@pytest.mark.parametrize("patch", ["first", "second"])
def test_site_plot_band_is_placebo_calibrated(patch):
    import matplotlib.pyplot as plt
    fig = _plot(patch)
    ax = fig.axes[0]
    ys = ax.collections[0].get_paths()[0].vertices[:, 1]
    f = sf.PLACEBO_FACTORS_H3[patch]
    assert (ys.min(), ys.max()) == pytest.approx((10 - f, 10 + f))
    labels = [t.get_text() for t in ax.get_legend().get_texts()]
    assert labels[0] == "95% interval, placebo-calibrated"
    assert any(t.get_text() == "weekly bars: sampling error only" for t in ax.texts)
    plt.close(fig)


def test_patch_summary_counts_are_calibrated(saved):
    f = sf.PLACEBO_FACTORS_H3["second"]
    h3 = saved["h3"].copy()
    keep = ["N1@2", "N2@2"]
    h3 = h3.loc[keep].assign(se=0.01)
    h3.loc["N1@2", "beta"] = 0.01 * 2 * f * 0.9        # past 2 se, not past the calibrated 2
    h3.loc["N2@2", "beta"] = 0.01 * 2 * f * 1.1
    s = sf.patch_summary(dict(saved, h3=h3, main=h3))
    assert s["second"]["n_clear"] == 1 and s["second"]["n"] == 2


def test_card_entry_keeps_the_raw_ci(saved):
    tw = pd.DataFrame([dict(card_patch_id="MID@1", color="silent", before_builds=sf.FIRST_BEFORE,
                            after_builds="vB", direction=1.0, log_ratio=-0.4,
                            upgraded_log_ratio=np.nan, mixed_direction="no", upgrade_only="no")]) \
        .set_index("card_patch_id")
    b = pd.DataFrame({"release_date": ["2026-04-16"]}, index=["vB"])
    e = sf.card_entry(saved, "MID@1", None, change_text="", tweaks=tw, builds=b, name="M", kind="nerf")
    h = saved["h3"].loc["MID@1"]
    assert (e["headline"]["ci_lo_pts"], e["headline"]["ci_hi_pts"]) == pytest.approx(
        (100 * h.ci_lo, 100 * h.ci_hi))
    assert "sentence" not in e


def _forest(saved):
    h3 = saved["h3"]
    tw = h3.assign(upgrade_only="no")
    names = {c: c.title() for c in h3.card_id}
    return tw, names


def test_forest_table_uses_the_calibrated_cutoff(saved):
    tw, names = _forest(saved)
    f = sf.PLACEBO_FACTORS_H3["first"]
    h3 = saved["h3"].assign(se=0.01)
    h3.loc["MID@1", "beta"] = 0.01 * f * 1.98           # past 1.96, not past 2
    h3.loc["BIG@1", "beta"] = 0.01 * f * 2.02
    t = sf.forest_table(dict(saved, h3=h3), tw.assign(se=0.01), names,
                        kinds={"MIX@1": "nerf"})
    assert not t.loc["MID@1", "clear"] and t.loc["BIG@1", "clear"]
    assert list(t.beta_pts) == sorted(t.beta_pts, reverse=True)


def test_forest_table_drops_upgrade_only_and_needs_a_kind_for_reworks(saved):
    tw, names = _forest(saved)
    tw.loc["FLIP@1", "upgrade_only"] = "yes"
    t = sf.forest_table(saved, tw, names, kinds={"MIX@1": "buff"})
    assert "FLIP@1" not in t.index and t.loc["MIX@1", "kind"] == "buff"
    with pytest.raises(ValueError, match="MIX@1"):
        sf.forest_table(saved, tw, names)


def test_forest_plot_text_size_and_colors(saved):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    tw, names = _forest(saved)
    t = sf.forest_table(saved, tw, names, kinds={"MIX@1": "nerf"})
    with plt.rc_context(sf.SITE_STYLE):
        fig = sf.plot_forest_site(t, title="t", subtitle="s", xlabel="x")
    fig.canvas.draw()
    ax = fig.axes[0]
    sizes = [x.get_fontsize() for x in [*fig.texts, *ax.get_yticklabels(), *ax.get_xticklabels(),
                                         *ax.get_legend().get_texts()]]
    assert min(sizes) >= 13
    plt.close(fig)


def test_factors_are_the_exports():
    from spirometry import export
    assert sf.PLACEBO_FACTORS_H3 is export.PLACEBO_FACTORS_H3 and sf.CAL_Z is export.CAL_Z

