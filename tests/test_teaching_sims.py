"""spirometry.teaching_sims: each toy's headline property (what the guide says it shows), not
exact values. Sizes are cut where a property holds at smaller n, so the file runs in seconds."""
import numpy as np
import pandas as pd
import pytest

from spirometry import teaching_sims as S


def test_bernoulli_variance_is_p_one_minus_p_and_mad_at_most_sd():
    t = S.bernoulli_spread()["table"]
    assert np.allclose(t.signed, 0)
    assert np.allclose(t["var"], t.p1mp)
    assert (t.mad <= t.sd + 1e-12).all() and np.isclose(t.sd[t.p == 0.2].item(), 0.4)


def test_se_is_sd_over_root_n_and_matches_the_reruns():
    r = S.sd_vs_se(n_reruns=2000)
    assert abs(r["sd_data"] - 0.4) < 0.02
    assert np.isclose(r["se_formula"], 0.4 / np.sqrt(r["n"]))
    assert abs(r["sd_reruns"] / r["se_formula"] - 1) < 0.1


def test_clt_width_set_by_n_not_by_reruns():
    a, b = S.lln_clt(n_reruns=2000, seed=0), S.lln_clt(n_reruns=500, seed=1)
    for n in (100, 1600):
        for r in (a, b):
            assert abs(r["clt"][n].std() / r["se"][n] - 1) < 0.12
    assert abs(a["running"][-1] - a["p"]) < 3 * a["se"][1] / np.sqrt(a["running"].size)


def test_plugin_collapses_and_bayes_mean_is_laplace():
    t = S.small_samples()["table"].set_index(["k", "n", "method"]).sort_index()
    for k, n in [(0, 1), (1, 1), (0, 3)]:
        assert t.loc[(k, n, "plugin"), "hi"] - t.loc[(k, n, "plugin"), "lo"] == 0
        assert t.loc[(k, n, "wilson"), "hi"] > t.loc[(k, n, "wilson"), "lo"]
        assert np.isclose(t.loc[(k, n, "bayes"), "centre"], (k + 1) / (n + 2))
    big = t.loc[(320, 1600)]
    assert big.centre.max() - big.centre.min() < 0.002        # all methods agree


def test_log_odds_push_is_about_delta_p_one_minus_p():
    r = S.log_odds_push()
    pts = r["points"].set_index("p0")
    assert pts.exact[0.5] > 5 * pts.exact[0.03]
    assert np.allclose(pts.exact, pts.approx, atol=0.002)


def test_fixed_bias_grows_in_z_with_n():
    t = S.fixed_bias(n_reruns=500)["table"]
    assert (np.diff(t.bias_over_se) > 0).all()
    assert np.allclose(t.bias_over_se, 0.01 / t.se)
    assert t.share_covers.iloc[0] > 0.5 and t.share_covers.iloc[-1] < 0.01


def test_difference_floors_at_the_smaller_side():
    r = S.se_difference()
    assert np.isclose(r["se_diff_equal"], np.sqrt(2) * r["se_before"])
    assert r["se_before"] < r["se_diff_100x"] < r["se_diff_10x"] < r["se_diff_equal"]
    assert r["se_diff_100x"] / r["se_before"] < 1.01


def test_buffs_and_nerfs_cancel_in_the_mean_not_the_slope():
    r = S.buffs_nerfs()
    assert abs(r["mean_effect"]) < 0.1 and r["slope"] > 1


def test_type_shock_leaks_through_mixed_controls():
    r = S.type_shock()
    assert np.isclose(r["did_skill_only"], r["truth"])
    share = r["n_ctrl_skill"] / (r["n_ctrl_skill"] + r["n_ctrl_attack"])
    assert np.isclose(r["did_mixed"], r["truth"] + (1 - share) * r["boss_hit"])


def test_power_rises_with_the_planted_slope():
    r = S.toy_power(n_sim=300)
    d = r["table"].detected.to_numpy()
    assert (np.diff(d) > 0).all() and d[0] < 0.12 and d[-1] > 0.8


def test_false_alarms_and_implied_factor_invert():
    r = S.false_alarms()
    assert abs(r["honest"] - 0.0455) < 1e-3
    assert np.isclose(S.implied_factor(r["share_at_3"]), 3)


def test_spillover_inflates_and_many_buffs_spill_more():
    r = S.spillover(n_screens=60_000)
    a, b = r["a"], r["b"]
    assert abs(a["did_same"]) > abs(a["truth"]) and b["did_same"] > b["truth"]   # away from 0
    assert abs(b["ctrl_change"]) > 3 * abs(a["ctrl_change"])
    assert a["did_other"] == a["truth"]


def test_four_ways_did():
    t = S.four_ways()["table"].set_index("case")
    assert t.did["parry_like"] == t.did["meta_shift"] == 15
    assert t.after_only["parry_like"] == 0 and t.before_after["meta_shift"] == 20
    assert t.did["held_still"] == -10


def test_drift_fake_patch_did_is_nonzero():
    r = S.drift(screens_per_week=10_000)
    assert r["did"] > 0.02                       # a discovered card looks treated
    assert r["skip_last"] > r["skip_first"]      # the total isn't fixed


def test_zero_one_slope_is_the_difference_of_means():
    r = S.two_columns()
    assert np.isclose(r["slope"], r["mean_diff"]) and np.isclose(r["intercept"], r["mean0"])


def test_interaction_coefficient_is_the_hand_did():
    r = S.did_regression()
    assert np.isclose(r["d"], r["did_by_hand"], atol=1e-10)
    assert np.isclose(r["a"], r["cell00"]) and np.isclose(r["a"] + r["c"], r["cell01"])
    assert abs(r["d"] - r["true_did"]) < 0.04


def test_card_fixed_effects_remove_the_composition_shift():
    r = S.composition()
    assert r["true_effect"] - r["raw"] > 0.02
    assert abs(r["fe"] - r["true_effect"]) < 0.02


def test_clustered_se_is_near_the_rerun_wobble():
    r = S.se_layers(n_reruns=80)
    se = r["se"]
    assert np.isclose(r["d"], r["did_by_hand"], atol=1e-10)
    assert abs(se["hc1"] / se["hand"] - 1) < 0.01 and abs(se["iid"] / se["hand"] - 1) < 0.05
    assert abs(se["clustered"] / r["true_wobble"] - 1) < 0.25
    assert se["clustered"] > 1.1 * se["hc1"]


def test_no_taste_means_the_layers_agree():
    rng = np.random.default_rng(0)
    _, _, se = S.fit_layers(*S.simulate_runs(rng, taste_sd=0))
    assert max(se.values()) / min(se.values()) < 1.1


def test_mix_shift_moves_the_average_not_the_bands():
    r = S.heterogeneity()
    f, s = r["first"], r["second"]
    assert f["all"] - s["all"] > 0.01
    for band in ("low", "high"):
        assert abs(f[band] - s[band]) < 0.012


def test_run_writes_summary_and_figure_data(tmp_path):
    summary, results = S.run(tmp_path, quick=True)
    assert set(summary.toy) == set(S.TOYS)
    assert not summary.duplicated(["toy", "quantity"]).any()
    assert set(summary.kind) <= {"count", "number", "signed", "pp", "ppu", "pct"}
    assert (tmp_path / "teaching_sims.csv").exists()
    assert (tmp_path / "toy_se_layers_se.csv").exists()
    back = pd.read_csv(tmp_path / "teaching_sims.csv")
    assert len(back) == len(summary)


def test_cli(tmp_path, capsys):
    S.main(["--out", str(tmp_path), "--quick", "--only", "two_columns", "four_ways"])
    assert "2 toys" in capsys.readouterr().out
