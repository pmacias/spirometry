"""spirometry.sensitivity on synthetic saved fits: planted slopes per patch, the specs'
line membership, the rulers, the review-call variant, SE inflation, the power simulation,
and the written tables. Reproduction of the triage's numbers on the real fits is checked
locally (the fits are git-ignored), not here."""
import numpy as np
import pandas as pd
import pytest

from spirometry import sensitivity as S

SPECIAL = {  # card_patch_id: (card, color, patch, main field, old, new, mixed, upgrade-only)
    S.LEADING_STRIKE: ("LEADING_STRIKE", "silent", 1, "damage", 7, 3, "yes", "no"),
    S.REFLECT: ("REFLECT", "regent", 2, "block", 17, 15, "yes", "no"),
    S.DEBILITATE_2: ("DEBILITATE", "necrobinder", 2, "powers_applied[0].amount", 3, 2, "no", "no"),
    S.GRAND_FINALE: ("GRAND_FINALE", "silent", 1, "damage", 50, 60, "no", "no"),
    S.CRESCENT_SPEAR: ("CRESCENT_SPEAR", "regent", 2, "damage", 6, 8, "no", "no"),
    "SERPENT_FORM@v0.103.2/patch": ("SERPENT_FORM", "silent", 1, "", "", "", "no", "yes"),
}
COLORS = ["defect", "ironclad", "necrobinder", "regent", "silent"]
FIELDS = ["damage", "block", "powers_applied[0].amount", "vars.Forge"]


def synthetic_fits(n1=30, n2=20, slope1=1.4, slope2=0.0, tau=0.05, seed=0):
    """A did_h3-like table: y = slope_p * ln(new/old) + noise, se ~ 0.05 log-odds."""
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n1 + n2):
        patch = 1 if i < n1 else 2
        old = int(rng.integers(3, 15))
        new = old + int(rng.choice([-2, -1, 1, 2, 3]))
        rows.append((f"CARD_{i:02d}@v0.10{3 if patch == 1 else 7}.{2 if patch == 1 else 1}/patch",
                     f"CARD_{i:02d}", COLORS[i % 5], patch, FIELDS[i % 4], old, max(new, 1),
                     "no", "no"))
    for cpid, (card, color, patch, field, old, new, mixed, upg) in SPECIAL.items():
        rows.append((cpid, card, color, patch, field, old, new, mixed, upg))
    d = pd.DataFrame(rows, columns=["card_patch_id", "card_id", "color", "patch", "main_field",
                                    "old", "new", "mixed_direction", "upgrade_only"])
    o, n = pd.to_numeric(d.old), pd.to_numeric(d.new)
    d["log_ratio"] = np.log(n / o)
    d["upgraded_log_ratio"] = np.where(np.arange(len(d)) % 7 == 0, d.log_ratio * 0.8, np.nan)
    d["direction"] = 1
    d["before_builds"] = np.where(d.patch == 2, S.SECOND_BEFORE, "v0.99.1")
    d["error"] = ""
    d["se_lo"] = rng.uniform(0.03, 0.08, len(d))
    slope = np.where(d.patch == 2, slope2, slope1)
    d["beta_lo"] = slope * d.log_ratio.fillna(0) + rng.normal(0, tau, len(d)) \
        + rng.normal(0, d.se_lo)
    d["beta"] = d.beta_lo * 0.2                       # as if p(1 - p) = 0.2
    d["old"], d["new"] = d.old.astype(str), d.new.astype(str)
    return d.drop(columns="patch").set_index("card_patch_id")


@pytest.fixture
def D():
    return S.prepare(synthetic_fits())


def test_slopes_by_patch_recovers_planted_slopes():
    d = S.prepare(synthetic_fits(n1=200, n2=200, slope1=1.4, slope2=0.3, seed=1))
    r = S.slopes_by_patch(S.notebook_line(d))
    assert abs(r["slope1"] - 1.4) < 3 * r["se1"]
    assert abs(r["slope2"] - 0.3) < 3 * r["se2"]
    assert abs(r["diff"] + 1.1) < 3 * r["se_diff"]
    assert r["z_diff"] < -3


def test_notebook_line_excludes_mixed_and_upgrade_only(D):
    L = S.notebook_line(D)
    assert S.LEADING_STRIKE not in L.index and S.REFLECT not in L.index
    assert "SERPENT_FORM@v0.103.2/patch" not in L.index
    assert S.DEBILITATE_2 in L.index


def test_primary_spec_membership_and_doses(D):
    L = S.dose_line(D, "primary")
    assert S.REFLECT in L.index and np.isclose(L.loc[S.REFLECT, "x"], np.log(15 / 17))
    assert S.DEBILITATE_2 not in L.index and S.LEADING_STRIKE not in L.index
    Sg = S.sign_line(D, "primary")
    assert Sg.loc[S.LEADING_STRIKE, "x_sign"] == 1 and Sg.loc[S.DEBILITATE_2, "x_sign"] == -1
    assert set(Sg.x_sign.unique()) <= {-1.0, 1.0}
    # with Debilitate at its table dose: on the line, Leading Strike still sign-only
    L2 = S.dose_line(D, "primary, Debilitate at table dose")
    assert np.isclose(L2.loc[S.DEBILITATE_2, "x"], np.log(2 / 3))
    assert len(L2) == len(L) + 1
    # the triage spec is the notebooks' line; its sign ruler adds nothing
    assert S.dose_line(D, "triage").index.equals(S.notebook_line(D).index)
    assert S.sign_line(D, "triage").index.equals(S.notebook_line(D).index)


def test_rulers(D):
    L = S.add_rulers(S.dose_line(D, "triage"))
    assert L.x_rank.between(-0.5, 0.5).all()
    for col in ["x_kind", "x_abs_kind", "x_hybrid"]:
        med = L[col].abs().groupby(L.kind).median()
        np.testing.assert_allclose(med, 1.0)
    dmg = L.kind == "damage"
    np.testing.assert_allclose(L.x_hybrid[dmg], L.x_abs[dmg] / L.x_abs[dmg].abs().median())
    no_up = L.upgraded_log_ratio.isna()
    np.testing.assert_allclose(L.x_baseupg[no_up], L.x[no_up])
    T = S.ruler_table(D, "primary")
    assert len(T) == len(S.RULERS)
    assert T.set_index("ruler").post_hoc.sum() == 1
    assert T.set_index("ruler").loc["hybrid: abs for damage/block, ln for power/other, / kind's "
                                    "median", "post_hoc"]
    sign = T.set_index("ruler").loc["sign only"]
    assert sign.n1 + sign.n2 == len(S.sign_line(D, "primary"))


def test_review_calls(D):
    L = S.dose_line(D, "triage")
    V = S.review_calls(L)
    assert S.GRAND_FINALE not in V.index and S.DEBILITATE_2 not in V.index
    assert np.isclose(V.loc[S.CRESCENT_SPEAR, "x"], np.log(10 / 8))
    assert V.loc[S.CRESCENT_SPEAR, "x_abs"] == 2.0
    assert len(V) == len(L) - 2
    T = S.review_call_table(D, "triage")
    assert {"as specified", "review calls"} <= set(T.variant)


def test_mixed_table_doses(D):
    M = S.mixed_table(D)
    ln = M[M.ruler == "ln(new/old)"].set_index("variant")
    assert ln.loc["both off", "n1"] + ln.loc["both off", "n2"] == len(S.notebook_line(D))
    assert ln.loc["Leading Strike damage-equivalent S=0", "n1"] == ln.loc["both off", "n1"] + 1
    assert np.isclose(S.LS_DOSES["damage-equivalent S=0"], 0.0)
    assert len(ln) == 1 + 5 + 3 + 15


def test_se_inflation(D):
    L = S.dose_line(D, "triage")
    T = S.se_inflation_table(L, {"none": (1.0, 1.0), "x3": (3.0, 3.0)}).set_index("setting")
    plain = S.slopes_by_patch(L)
    assert np.isclose(T.loc["none", "slope1"], plain["slope1"])
    assert T.loc["x3", "tau2"] <= T.loc["none", "tau2"]
    assert T.loc["x3", "se1"] > 0


def test_leave_out_and_character(D):
    T = S.leave_out_table(D, "primary")
    L = S.dose_line(D, "primary")
    assert (T.level == "tweak").sum() == len(L)
    assert (T.level == "character").sum() == L.color.nunique()
    none = T[T.level == "none"].iloc[0]
    assert none.d_slope1_in_se == 0
    C, counts = S.character_table(D, "primary")
    assert {"character intercepts", "character x patch intercepts"} <= set(C.model)
    assert counts.to_numpy().sum() == len(L)


def test_power_simulation_detects_a_planted_slope_and_is_reproducible():
    L = S.dose_line(S.prepare(synthetic_fits(n1=30, n2=20, slope2=0.0, seed=4)), "triage")
    P = S.power_simulation(L, (2.0, 2.0), n_sim=60, planted=(0.0, 1.4))
    P2 = S.power_simulation(L, (2.0, 2.0), n_sim=60, planted=(0.0, 1.4))
    pd.testing.assert_frame_equal(P, P2)
    h = P[P.setting == "honest"].set_index("planted")
    assert h.loc[1.4, "power_slope2_ne_0"] > 0.8
    assert h.loc[0.0, "power_slope2_ne_0"] < 0.2
    assert h.loc[0.0, "power_diff_ne_0"] > 0.8
    assert set(P.setting) == {"honest", "placebo-inflated", "honest, patch-2 tau2"}


def placebo_inputs():
    summary = pd.DataFrame({
        "split": ["all", "patch", "patch"], "level": ["all", "first", "second"],
        "sd_z": [3.7, 4.7, 2.5], "robust_sd_z": [3.0, 4.3, 2.1], "dedupe": [True] * 3})
    rng = np.random.default_rng(5)
    n = 60
    placebo = pd.DataFrame({
        "color": np.repeat(COLORS, n // 5), "stable_build": "v0.103.2",
        "fit_on": "all offers", "pseudo_card": [f"P{i}" for i in range(n)],
        "patch": np.where(np.arange(n) % 2, "second", "first"),
        "treated_rate_before": rng.uniform(0.1, 0.4, n), "beta": rng.normal(0, 0.02, n),
        "se": rng.uniform(0.003, 0.008, n), "error": ""})
    return summary, placebo


def test_placebo_factors():
    summary, _ = placebo_inputs()
    f = S.placebo_factors(summary)
    assert f["robust sd by patch"] == (4.3, 2.1)
    assert f["sd, one factor"] == (3.7, 3.7)
    assert f["none"] == (1.0, 1.0)


def test_run_writes_tables(tmp_path):
    an = tmp_path / "analysis"
    an.mkdir()
    fits = synthetic_fits().reset_index()
    fits.to_parquet(an / "did_h3.parquet")
    fits.to_parquet(an / "did_main.parquet")
    summary, placebo = placebo_inputs()
    summary.to_csv(an / "placebo_diagnostics_summary.csv", index=False)
    placebo.to_parquet(an / "placebo_main.parquet")
    out = tmp_path / "writeup"
    t = S.run(an, out, n_sim=20)
    for name in ["rulers", "dose_points", "review_calls", "mixed", "leave_out", "character",
                 "character_counts", "se_inflation", "spread", "power"]:
        assert (out / f"{name}.csv").exists(), name
        assert (t[name].fits == "did_h3").all()
    assert set(t["rulers"].spec) == set(S.SPECS)
    assert "additive placebo variance" in set(t["se_inflation"].setting)
    assert "seed" not in t["power"].columns
