"""spirometry.strength on synthetic runs with known structure (no network, no run data).

Two blocks of runs (build v1 = before, v2 = after) go into an in-memory DuckDB shaped like
runs.duckdb (tests/test_wins.fake_db), so the whole path from SQL to the change runs. As in
tests/test_wins.py, a hidden skill raises both picking and winning. A smoke test on real
pages runs only when SPIROMETRY_SMOKE_DB points to a runs.duckdb built from fetched pages.
"""
import json
import os
import time

import duckdb
import numpy as np
import pandas as pd
import pytest

from spirometry import did, strength, wins
from test_wins import fake_db

CARDS = [f"C{i}" for i in range(10)]
X, CHANGED = "C0", "C9"                 # C9 changed in the same patch: not a control
CPID = "C0@v2/patch"
RELEASE = {"v1": pd.Timestamp("2026-04-16"), "v2": pd.Timestamp("2026-05-07")}
N = 30_000                              # runs per block


@pytest.fixture(scope="module")
def ref(tmp_path_factory):
    return make_ref(tmp_path_factory.mktemp("sref"))


def make_ref(ref):
    """builds.csv, card_changes.csv, raw/cards.json (colors), windows.csv (one card-patch
    window, C9 excluded from the controls) and tweak_sizes.csv (C0: a numeric tweak; C5: an
    upgrade-only one; C4: not solo-estimable)."""
    dates = [d.date().isoformat() for d in RELEASE.values()]
    pd.DataFrame(dict(build_id=list(RELEASE), branch="stable", release_date=dates)).to_csv(
        ref / "builds.csv", index=False)
    pd.DataFrame(dict(card_id=[X], color=["ironclad"])).to_csv(ref / "card_changes.csv",
                                                               index=False)
    (ref / "raw").mkdir()
    (ref / "raw" / "cards.json").write_text(json.dumps(
        [{"id": c, "color": "ironclad"} for c in CARDS] + [{"id": "Y", "color": "silent"}]))
    win = lambda c, excl: dict(level="card_patch", event_id=f"{c}@v2/patch", card_id=c,
                               change_kind="tweak", branch="stable", before_builds="v1",
                               after_builds="v2", clean="yes", control_exclusions=excl,
                               control_behavior_flags="")
    pd.DataFrame([win(X, CHANGED), win("C5", f"{X} {CHANGED}"), win("C4", "")]).to_csv(
        ref / "windows.csv", index=False)
    tw = lambda c, up, solo: dict(card_patch_id=f"{c}@v2/patch", card_id=c,
                                  color="ironclad", stable_build="v2", before_builds="v1",
                                  after_builds="v2", main_field="damage", old="6",
                                  new="8", log_ratio="0.2877",
                                  upgrade_only=up, solo_estimable=solo, direction="1")
    pd.DataFrame([tw(X, "no", "yes"), tw("C5", "yes", "yes"), tw("C4", "no", "no")]).to_csv(
        ref / "tweak_sizes.csv", index=False)
    return ref


def sigmoid(x):
    return 1 / (1 + np.exp(-x))


def block(n, build, *, effects=None, weights=None, base=0.3, skill_win=0.12,
          offer_skill=0.0, asc_skill=1.0, seed=0, prefix=None):
    """n runs on `build`, each reaching 3 reward screens. Hidden skill u ~ N(0, 1).
    Each screen shows 3 of the 10 cards at random; with offer_skill, X's offer weight is
    exp(offer_skill u) (skilled runs are offered X more: independence broken). The player
    takes a card with probability sigmoid(0.3 + u), choosing among the three by `weights`
    (card -> weight, default 1). Win probability (linear, clipped): base + skill_win u + the
    effect of every card taken on the three screens (`effects`, card -> effect, default 0).
    Ascension rises with skill (asc_skill), so a skill-dependent offer shows up in it.
    Weeks 0-5 and tagged uploaders (30%) have no effect. Returns (runs, offers)."""
    effects, weights = effects or {}, weights or {}
    rng = np.random.default_rng(seed)
    u = rng.normal(size=n)
    S = 3
    logw = np.zeros((n, S, len(CARDS)))
    logw[:, :, 0] = offer_skill * u[:, None]
    card = np.argsort(-(rng.gumbel(size=(n, S, len(CARDS))) + logw), axis=2)[:, :, :3]
    w = np.log(np.array([weights.get(c, 1.0) for c in CARDS]))[card]
    choice = np.argmax(w + rng.gumbel(size=card.shape), axis=2)
    take = rng.random((n, S)) < sigmoid(0.3 + u[:, None])
    picked = (np.arange(3)[None, None, :] == choice[:, :, None]) & take[:, :, None]
    took = np.zeros((n, len(CARDS)), dtype=bool)
    i, s, j = np.nonzero(picked)
    took[i, card[i, s, j]] = True
    eff = np.array([effects.get(c, 0.0) for c in CARDS])
    p = np.clip(base + skill_win * u + took @ eff, 0.01, 0.99)
    week = rng.integers(0, 6, n)
    prefix = prefix or build
    runs = pd.DataFrame(dict(
        run_key=[f"{prefix}_{k}" for k in range(n)], build_id=build,
        ascension=np.clip(np.round(4.5 + 2 * asc_skill * u + rng.normal(0, 1.5, n)), 0, 9
                          ).astype(int),
        tagged=rng.random(n) < 0.3,
        start_time=RELEASE[build] + pd.to_timedelta(week * 7 + 1, unit="D"),
        win=rng.random(n) < p, floors_reached=20))
    i, s, j = np.nonzero(np.ones(card.shape, dtype=bool))
    offers = pd.DataFrame(dict(
        run_key=runs.run_key.to_numpy()[i], floor=2 * (s + 1), set_idx=0, source="combat",
        card_id=np.array(CARDS)[card[i, s, j]], picked=picked[i, s, j], upgraded=False))
    return runs, offers


def window_db(before, after, seed=0):
    """A DB with a before block on v1 and an after block on v2 (kwargs for block())."""
    b = block(N, "v1", seed=seed, **before)
    a = block(N, "v2", seed=seed + 1, **after)
    return fake_db(pd.concat([b[0], a[0]], ignore_index=True),
                   pd.concat([b[1], a[1]], ignore_index=True))


def run(con, ref, **kw):
    return strength.strength_change(con, CPID, ref=ref, **kw)


def treated(res):
    return res.summary.iloc[0]


def controls(res):
    return res.changes[~res.changes.treated]


# ------------------------------------------------------------------------------ scenarios

@pytest.fixture(scope="module")
def planted(ref):
    # X's effect doubles, +0.05 -> +0.10; X is picked more than the others (weight 3)
    con = window_db(dict(effects={X: 0.05}, weights={X: 3}),
                    dict(effects={X: 0.10}, weights={X: 3}), seed=1)
    return con, run(con, ref)


def test_planted_change(planted):
    _, res = planted
    t = treated(res)
    assert abs(t.iv_change - 0.05) < 2 * t.iv_change_se
    assert abs(t.iv_net - 0.05) < 2 * t.iv_change_se
    assert abs(t.iv_before - 0.05) < 2 * t.iv_change_se
    # the controls didn't change
    c = controls(res)
    assert len(c) == 8 and CHANGED not in set(c.card_id)
    assert abs(t.iv_controls_median) < 0.02
    assert (c.iv_z_raw.abs() < 3).all()
    assert t.n_controls == 8 and t.iv_n_controls_used == 8
    assert t.n_controls_skipped_weak == 0 and t.n_controls_skipped_few == 0
    # the pick rate didn't move: the ITT moves with the effect
    assert abs(t.fs_change) < 2 * t.fs_change_se and t.itt_change > 0
    # se of a difference of independent blocks
    b = res.blocks.set_index(["card_id", "block"])
    assert t.iv_change_se == pytest.approx(np.hypot(b.loc[(X, "before"), "iv_se"],
                                                    b.loc[(X, "after"), "iv_se"]))
    assert t.iv_change == pytest.approx(b.loc[(X, "after"), "iv_beta"]
                                        - b.loc[(X, "before"), "iv_beta"])
    assert t.n_runs_before > 0.95 * N and t.n_runs_after > 0.95 * N
    # matched controls: k_match = 20 > 8 controls, so all of them in each block
    assert t.iv_n_matched_before == t.iv_n_matched_after == 8
    assert abs(t.iv_net_m - 0.05) < 2 * t.iv_change_se
    for k, v in dict(K=3, screen_mix=False, group="", pooled_groups=False,
                     include_short_runs=False, min_offered=500, k_match=20).items():
        assert t[k] == v and (res.blocks[k] == v).all() and (res.changes[k] == v).all()


def test_block_fits_match_wins(planted, ref):
    # block_estimates reuses one run frame; its numbers are wins.itt / first_stage / iv's
    con, res = planted
    data = wins.load_early(con, "ironclad", ["v2"], ref=ref)
    row = res.blocks.set_index(["card_id", "block"]).loc[(X, "after")]
    assert row.itt_beta == pytest.approx(wins.itt(data, X)["beta"], rel=1e-9)
    assert row.itt_se == pytest.approx(wins.itt(data, X)["se"], rel=1e-9)
    assert row.fs_F == pytest.approx(wins.first_stage(data, X)["F"], rel=1e-9)
    assert row.iv_beta == pytest.approx(wins.iv(data, X)["beta"], rel=1e-9)
    assert row.iv_se == pytest.approx(wins.iv(data, X)["se"], rel=1e-9)
    assert row.n_runs == wins.iv(data, X)["n_runs"]


def test_stacked_fit_equals_difference(planted, ref):
    # One stacked fit with every fixed effect interacted with the block gives the same
    # change as two separate fits, and (runs disjoint) the same se up to HC1's dof factor.
    import pyfixest as pf
    con, res = planted
    d = []
    for blk, b in (("before", "v1"), ("after", "v2")):
        f = wins.run_frame(wins.load_early(con, "ironclad", [b], ref=ref), X)
        d.append(f.assign(after=int(blk == "after")))
    d = pd.concat(d, ignore_index=True)
    for c in ("build_group", "build_week"):
        d[c] = d[c].astype(str)
    d["asc_block"] = d.asc.astype(str) + "|" + d.after.astype(str)
    d["off_after"] = d.offered * d.after
    fit = pf.feols("win ~ offered + off_after | build_group + asc_block + build_week",
                   data=d, vcov="hetero")
    t = treated(res)
    assert float(fit.coef()["off_after"]) == pytest.approx(t.itt_change, rel=1e-6)
    assert float(fit.se()["off_after"]) == pytest.approx(t.itt_change_se, rel=0.01)


def test_null(ref):
    # X's effect is +0.10 in both blocks. Over seeds 20-38 the raw z ran -2.1 to 1.8 and
    # the controls' raw z had sd 1.06 (80 draws): the se of the difference is about right.
    con = window_db(dict(effects={X: 0.1}, weights={X: 3}),
                    dict(effects={X: 0.1}, weights={X: 3}), seed=30)
    t = treated(run(con, ref))
    assert abs(t.iv_change) < 2 * t.iv_change_se
    assert abs(t.iv_z_se) < 2 and abs(t.iv_z_spread) < 3 and abs(t.iv_z_total) < 2
    assert abs(t.itt_z_se) < 2
    assert abs(t.iv_z_se_m) < 2 and abs(t.iv_z_total_m) < 2


def test_level_drift_cancels_within_blocks(ref):
    # Win rates fall 10 points for every run in the after block. Each block's estimate is
    # a within-block contrast (offered vs. not), so a level drift doesn't reach it, raw or
    # net.
    con = window_db(dict(effects={X: 0.1}, weights={X: 3}, base=0.35),
                    dict(effects={X: 0.1}, weights={X: 3}, base=0.25), seed=5)
    res = run(con, ref)
    t = treated(res)
    b = res.blocks[res.blocks.card_id == X].set_index("block")
    assert b.win_rate_not_offered["before"] - b.win_rate_not_offered["after"] > 0.08
    assert abs(t.iv_change) < 2 * t.iv_change_se and abs(t.iv_z_se) < 2


def test_shared_drift_cancels_net_of_controls(ref):
    # A drift that moves every card's estimate alike: C9, changed in the same patch (so not
    # a control), is taken whenever it is shown and is worth +0.5 before and 0 after. Being
    # offered any other card takes a slot C9 could have had, so every card's effect
    # (relative to what the run would otherwise have taken) rises after the patch. X has
    # no change of its own and is picked like the controls (weight 1). Over seeds 20-38:
    # raw z 1.6 to 4.9 (mean 3.2), net z_se -1.4 to 2.2 (mean 0.3).
    con = window_db(dict(effects={X: 0.1, CHANGED: 0.5}, weights={CHANGED: 20}),
                    dict(effects={X: 0.1, CHANGED: 0.0}, weights={CHANGED: 20}), seed=20)
    res = run(con, ref)
    t = treated(res)
    assert t.iv_change > 2 * t.iv_change_se                 # the raw change moves ...
    assert t.iv_controls_median > 0.08                      # ... and so do the controls
    assert abs(t.iv_net) < 2 * t.iv_change_se and abs(t.iv_z_se) < 2   # net: about 0
    assert abs(t.iv_z_spread) < 3
    assert t.itt_z_raw > 2 and abs(t.itt_z_se) < 2


def test_pick_rate_change_alone_is_not_a_strength_change(ref):
    # Players pick X three times as eagerly after the patch (weight 3 -> 9), its effect
    # unchanged. The first stage rises, the ITT (= first stage x effect) rises with it, and
    # the IV (the strength) doesn't move. Over seeds 20-38 the raw iv z ran -1.9 to 1.8.
    con = window_db(dict(effects={X: 0.1}, weights={X: 3}),
                    dict(effects={X: 0.1}, weights={X: 9}), seed=9)
    t = treated(run(con, ref))
    assert t.fs_z_se > 5
    assert abs(t.iv_change) < 2 * t.iv_change_se and abs(t.iv_z_se) < 2
    assert t.itt_net > 0 and t.itt_z_se > 2
    assert abs(t.iv_z_se_m) < 2


def test_matched_controls_cancel_per_offer_drift(ref):
    # Parry-like: X is picked much less than most controls before the patch and three
    # times as eagerly after (weight 0.3 -> 0.9, effect +0.10 throughout). The same
    # per-offer drift as in the shared-drift test (C9 worth +0.5 before, 0 after) moves
    # every card by the same amount on the ITT scale, i.e. by drift / first stage on the
    # IV scale: X, with a low first stage before, moves much more than the median
    # control, so the all-controls net shows a fake strength change. Three controls are
    # picked about as rarely as X (weights 0.3-0.4); matching on the first stage in each
    # block (k_match = 3) compares X with them before and with weight ~1 controls after.
    # Over seeds 40-48: all-controls net +0.13 to +0.26 (z_se 1.6-2.8), matched net_m
    # -0.09 to +0.14 (z_se_m -0.9 to 1.4).
    w = dict(C1=0.3, C2=0.3, C3=0.4, C4=1, C5=1.5, C6=2, C7=3, C8=3, C9=20)
    con = window_db(dict(effects={X: 0.1, CHANGED: 0.5}, weights=dict(w, C0=0.3)),
                    dict(effects={X: 0.1, CHANGED: 0.0}, weights=dict(w, C0=0.9)), seed=40)
    res = run(con, ref, k_match=3, balance=False)
    t = treated(res)
    ch = res.changes.set_index("card_id")
    assert ch.fs_before[X] < 0.1 and ch.fs_after[X] > 0.15    # the taker group grew
    assert t.iv_n_matched_before == t.iv_n_matched_after == 3 and t.k_match == 3
    assert abs(t.iv_fs_matched_before - ch.fs_before[X]) < 0.02
    assert abs(t.iv_fs_matched_after - ch.fs_after[X]) < 0.03
    # all controls: a fake change well above zero; matched: about zero
    assert t.iv_net > 0.15 and t.iv_z_se > 2
    assert abs(t.iv_z_se_m) < 1 and abs(t.iv_z_total_m) < 1
    assert abs(t.iv_net_m) < 0.5 * t.iv_net


def test_weak_first_stage(ref):
    # X (and control C8) are almost never taken after the patch: the IV change is blank
    # with a reason, not a huge number; the ITT and first-stage changes stay; the weak
    # control is counted and left out of the median.
    con = window_db(dict(effects={X: 0.1}, weights={X: 3}),
                    dict(effects={X: 0.1}, weights={X: 0.0003, "C8": 0.0003}), seed=11)
    res = run(con, ref)
    t = treated(res)
    assert t.weak_after and not t.weak_before and t.fs_F_after < 10
    assert np.isnan(t.iv_change) and np.isnan(t.iv_z_se)
    assert t.iv_reason.startswith("weak first stage after (F = ")
    assert np.isfinite(t.itt_change) and np.isfinite(t.fs_change) and t.itt_reason == ""
    assert t.n_controls_skipped_weak == 1 and t.iv_n_controls_used == 7
    assert t.itt_n_controls_used == 8
    c8 = res.changes.set_index("card_id").loc["C8"]
    assert np.isnan(c8.iv_change) and "weak first stage after" in c8.iv_reason
    b = res.blocks.set_index(["card_id", "block"])
    assert b.loc[(X, "after"), "weak"] and np.isfinite(b.loc[(X, "after"), "iv_beta"])


def test_min_offered_and_disjoint_blocks(planted, ref):
    con, _ = planted
    res = run(con, ref, min_offered=10**6, balance=False)
    t = treated(res)
    assert np.isnan(t.iv_change) and "fewer than 1000000 offered runs" in t.iv_reason
    assert np.isnan(t.itt_change) and t.n_controls_skipped_few == 8
    # a run in both blocks breaks sqrt(se_b^2 + se_a^2): refused
    b = wins.load_early(con, "ironclad", ["v1"], ref=ref)
    with pytest.raises(ValueError, match="in both blocks"):
        run(con, ref, data=(b, b))


def test_options_end_to_end(ref):
    # K = 1 and screen_mix (the planned robustness rows), group and pooled_groups run
    # through and are echoed
    con = window_db(dict(effects={X: 0.05}, weights={X: 3}),
                    dict(effects={X: 0.10}, weights={X: 3}), seed=13)
    k1 = treated(run(con, ref, K=1, balance=False))
    assert k1.K == 1 and np.isfinite(k1.iv_change) and k1.n_offered_after < 0.4 * N
    mix = treated(run(con, ref, screen_mix=True, balance=False))
    assert mix.screen_mix and np.isfinite(mix.iv_change)
    tg = treated(run(con, ref, group="tagged", min_offered=100, balance=False))
    assert tg.group == "tagged" and tg.n_runs_after < 0.4 * N
    pooled = treated(run(con, ref, pooled_groups=True, balance=False))
    assert pooled.pooled_groups and np.isfinite(pooled.iv_change)
    with pytest.raises(ValueError, match="K = 3"):
        run(con, ref, K=1, data=(wins.load_early(con, "ironclad", ["v1"], ref=ref),
                                 wins.load_early(con, "ironclad", ["v2"], ref=ref)))


def test_strength_all_and_cache(planted, ref, tmp_path):
    con, res = planted
    t0 = time.perf_counter()
    out = strength.strength_all(con, ref=ref)
    elapsed = time.perf_counter() - t0
    s = out.summary.set_index("card_patch_id")
    assert list(s.index) == [CPID, "C5@v2/patch"]           # C4 isn't solo-estimable
    assert s.loc["C5@v2/patch", "skipped"].startswith("upgrade-only")
    assert s.loc[CPID, "skipped"] == ""
    assert s.loc[CPID, "iv_change"] == pytest.approx(treated(res).iv_change)
    assert s.loc[CPID, "log_ratio"] == "0.2877"             # tweak_sizes columns carried
    assert set(out.changes.card_patch_id) == {CPID}
    strength.save(out, tmp_path, "main")
    back = strength.load(tmp_path, "main")
    assert back.summary.set_index("card_patch_id").loc[CPID, "iv_change"] == pytest.approx(
        s.loc[CPID, "iv_change"])
    assert len(back.blocks) == len(out.blocks) == 2 * 9
    # 9 cards x 2 blocks x 3 fits on 30,000 runs a block (runtime estimate for the PR)
    print(f"\nstrength_all: {elapsed:.1f} s for 54 fits + 2 balance checks")


# ------------------------------------------------------------------------------ balance

def test_balance_random_offers(planted, ref):
    con, _ = planted
    data = wins.load_early(con, "ironclad", ["v1"], ref=ref)
    b = strength.balance_check(data, X)
    assert b["p_joint"] > 0.01 and b["max_abs_std_diff"] < 0.05
    assert set(b["table"].covariate) == {"ascension", "week", "group", "build_id",
                                         "screen_sources"}
    assert np.isnan(b["p_build"])                           # one build in the block
    al = strength.balance_all(data, "ironclad", min_offered=100, ref=ref)
    assert al["n_cards"] == 10 and al["n_fail"] <= 2 and al["p_binom"] > 0.01
    s = treated(planted[1])
    assert s.balance_p_joint_before > 0.01 and s.balance_p_joint_after > 0.01
    # few runs (the fetched pages hold dozens per character and build): levels with a run
    # or two would fit exactly and make the robust test reject; they are pooled instead
    small = wins.load_early(fake_db(*block(300, "v1", seed=17)), "ironclad", ["v1"],
                            ref=ref)
    al = strength.balance_all(small, "ironclad", min_offered=20, ref=ref)
    assert al["n_cards"] == 10 and al["n_fail"] <= 2


def test_balance_offer_depends_on_skill(ref):
    # iv_primer section 7's "offer depends on skill": skilled runs are offered X more.
    # Skill is hidden, but skilled players play higher ascensions, so offered runs sit at
    # higher ascension and the check fails; IV inherits the bias.
    runs, offers = block(N, "v1", effects={X: 0.0}, weights={X: 3}, offer_skill=0.5,
                         seed=15)
    data = wins.load_early(fake_db(runs, offers), "ironclad", ["v1"], ref=ref)
    b = strength.balance_check(data, X)
    asc = b["table"].set_index("covariate").loc["ascension"]
    assert b["p_joint"] < 1e-6 and asc.std_diff > 0.1
    assert wins.iv(data, X)["beta"] > 3 * wins.iv(data, X)["se"]   # the bias it warns of
    al = strength.balance_all(data, "ironclad", min_offered=100, ref=ref)
    assert al["cards"].set_index("card_id").loc[X, "fail"] and al["p_binom"] < 0.05


# ------------------------------------------------------------------------------ real pages

SMOKE_DB = os.environ.get("SPIROMETRY_SMOKE_DB")


@pytest.mark.skipif(not SMOKE_DB, reason="set SPIROMETRY_SMOKE_DB to a runs.duckdb built "
                                         "from fetched pages")
def test_smoke_real_pages():
    """End to end on real columns: the first stable window (v0.99.1 -> v0.103.2), with a
    minimum of 5 offered runs (the pages hold a few dozen runs per character and build).
    Only checks that it runs; the estimates mean nothing at this size."""
    con = duckdb.connect(SMOKE_DB, read_only=True)
    tweaks = pd.read_csv(did.REF / "tweak_sizes.csv", dtype=str)
    first = tweaks[(tweaks.before_builds == "v0.99.1") & (tweaks.solo_estimable == "yes")]
    out = strength.strength_all(con, tweaks=first.card_patch_id.tolist(), min_offered=5)
    s = out.summary
    assert len(s) == len(first)
    ran = s[s.skipped == ""]
    assert len(ran) and (ran.n_runs_before > 0).all() and (ran.n_runs_after > 0).all()
    up = set(first.card_patch_id[first.upgrade_only == "yes"])
    assert s.skipped[s.card_patch_id.isin(up)].str.startswith("upgrade-only").all()
    assert (s.skipped[~s.card_patch_id.isin(up)] == "").all()
    assert set(out.blocks.block) == {"before", "after"}
