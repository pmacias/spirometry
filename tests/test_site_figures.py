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
    assert s["second"]["n_clear"] == 1
    assert sf.kind_of(saved["h3"].loc["MIX@1"]) == "rework"
    assert sf.kind_of(saved["h3"].loc["BUFF@1"]) == "buff"
    assert sf.kind_of(saved["h3"].loc["MID@1"]) == "nerf"


def test_sentence():
    assert sf.sentence(14.13, 12.68, 15.57, "Regent") == \
        "Pick rate up 14.1 pts vs. unchanged Regent cards (95% CI 12.7–15.6)."
    assert sf.sentence(-8.1, -9.1, -7.2, "Silent").startswith("Pick rate down 8.1 pts")
    assert "(95% CI 7.2–9.1)" in sf.sentence(-8.1, -9.1, -7.2, "Silent")
    assert sf.sentence(-2.0, -4.2, 0.2, "Ironclad").startswith("No clear change")


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
