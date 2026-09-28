"""spirometry.wins on synthetic runs with known structure (no network, no run data).

The synthetic runs go into an in-memory DuckDB shaped like runs.duckdb (runs_dedup,
run_players, offers_with_version), so the screen counting in SQL is tested too. A smoke test
on real pages runs only when SPIROMETRY_SMOKE_DB points to a runs.duckdb built from fetched
pages (parser 1.7.0 or later); its estimates mean nothing at that size.
"""
import json
import os

import duckdb
import numpy as np
import pandas as pd
import pytest

from spirometry import did, wins

CARDS = [f"C{i}" for i in range(10)]
X = "C0"
RELEASE = {"v1": pd.Timestamp("2026-04-16"), "v2": pd.Timestamp("2026-05-07")}


@pytest.fixture(scope="module")
def ref(tmp_path_factory):
    """builds.csv (release dates for week), card_changes.csv and raw/cards.json (colors)."""
    ref = tmp_path_factory.mktemp("wref")
    pd.DataFrame(dict(build_id=list(RELEASE), branch="stable",
                      release_date=[d.date().isoformat() for d in RELEASE.values()])).to_csv(
        ref / "builds.csv", index=False)
    pd.DataFrame(dict(card_id=["C0"], color=["ironclad"])).to_csv(ref / "card_changes.csv",
                                                                   index=False)
    (ref / "raw").mkdir()
    (ref / "raw" / "cards.json").write_text(json.dumps(
        [{"id": c, "color": "ironclad"} for c in CARDS] + [{"id": "Y", "color": "silent"}]))
    return ref


def fake_db(runs, offers):
    """runs: one row per run (run_key, build_id, ascension, tagged, start_time, win,
    floors_reached, plus optional character, was_abandoned, retried, n_players); offers: one
    row per offered card (run_key, floor, set_idx, source, card_id, picked, upgraded)."""
    r = runs.copy()
    r["run_hash"] = r.run_key
    defaults = dict(character="CHARACTER.IRONCLAD", n_players=1, is_custom=False,
                    is_modded=False, released=True, before_release=False, neow_start=True,
                    was_abandoned=False, retried=False, branch="stable")
    for k, v in defaults.items():
        r[k] = r[k].fillna(v).astype(type(v)) if k in r else v
    r["uploader_tag"] = np.where(r.pop("tagged"), "slay-the-stats/v1", None)
    o = offers.merge(r[["run_key", "run_hash", "character", "build_id"]], on="run_key")
    con = duckdb.connect()
    con.register("r_df", r)
    con.register("o_df", o)
    con.execute("CREATE TABLE runs_dedup AS SELECT * EXCLUDE (character) FROM r_df")
    con.execute("CREATE TABLE run_players AS SELECT run_hash, 0 AS player_idx, character "
                "FROM r_df")
    con.execute("CREATE TABLE offers_with_version AS SELECT * FROM o_df")
    return con


def synth(n=20000, S=12, K=3, effect=0.1, x_weight=3.0, skill_pick=1.0, skill_win=0.12,
          early_hazard=0.01, seed=0, early_hazard_skill=0.0, x_death=0.0,
          lose_if_short=False, elite_rate=0.0, elite_skill=0.0, x_offer_weight=None):
    """Runs with a hidden skill u ~ N(0, 1). Each run reaches reward screens 1..S one after
    the other: it dies before each of the first K with probability early_hazard, before
    each later one with a probability that falls with skill (sigmoid(-1 - 1.5 u)), so later
    screens are reached mostly by skilled runs. Every screen shows 3 of the 10 cards,
    uniformly at random (the RNG). The player takes a card with probability
    sigmoid(0.3 + skill_pick u), choosing among the three with weight x_weight for X (C0)
    and 1 for the others: skill raises picking. Win probability (linear, clipped):
    0.3 + skill_win u + effect x (X taken on one of the first K screens). Weeks 0-5, builds
    v1/v2, ascension 0-9 and tagged uploaders (30%) have no effect. Returns (runs, offers).

    Options (off by default; they draw from a second generator, so the default runs are
    the same with or without them):
    early_hazard_skill: the early hazard falls with skill, sigmoid(logit(early_hazard) -
      early_hazard_skill u).
    x_death: a run offered X on one of screens 1..K-1 dies before screen K with this extra
      probability.
    lose_if_short: runs that die before screen K lose.
    elite_rate, elite_skill: screens 2..K are elites with probability
      sigmoid(logit(elite_rate) + elite_skill u) (taking an early elite is a choice skilled
      players make more); source 'elite'.
    x_offer_weight: {'combat': w, 'elite': w}, X's offer weight on each screen type (the
      other cards weigh 1): a rare card that elites offer more often."""
    rng = np.random.default_rng(seed)
    rng2 = np.random.default_rng(seed + 10_000)
    u = rng.normal(size=n)
    early = early_hazard
    if early_hazard_skill:
        early = 1 / (1 + np.exp(-(np.log(early_hazard / (1 - early_hazard))
                                  - early_hazard_skill * u[:, None])))
    hazard = np.where(np.arange(S)[None, :] < K, early,
                      1 / (1 + np.exp(1 + 1.5 * u[:, None])))
    reached = np.cumprod(rng.random((n, S)) >= hazard, axis=1).astype(bool)
    elite = np.zeros((n, S), dtype=bool)
    if elite_rate:
        pe = 1 / (1 + np.exp(-(np.log(elite_rate / (1 - elite_rate)) + elite_skill * u)))
        elite[:, 1:K] = rng2.random((n, K - 1)) < pe[:, None]
    g = rng.gumbel(size=(n, S, len(CARDS)))
    if x_offer_weight is None:
        card = np.argsort(g, axis=2)[:, :, :3]
    else:
        logw = np.zeros((n, S, len(CARDS)))
        logw[:, :, 0] = np.where(elite, np.log(x_offer_weight["elite"]),
                                 np.log(x_offer_weight["combat"]))
        card = np.argsort(-(g + logw), axis=2)[:, :, :3]
    if x_death:
        offered_early = ((card == 0).any(axis=2) & reached)[:, :K - 1].any(axis=1)
        die = offered_early & (rng2.random(n) < x_death)
        reached[die, K - 1:] = False
    w = np.where(card == 0, np.log(x_weight), 0.0) + rng.gumbel(size=card.shape)
    choice = np.argmax(w, axis=2)
    take = rng.random((n, S)) < 1 / (1 + np.exp(-(0.3 + skill_pick * u[:, None])))
    picked = (np.arange(3)[None, None, :] == choice[:, :, None]) & take[:, :, None]
    picked &= reached[:, :, None]
    x_early = ((card == 0) & picked)[:, :K].any(axis=(1, 2))
    p = np.clip(0.3 + skill_win * u + effect * x_early, 0.01, 0.99)
    build = np.where(rng.random(n) < 0.5, "v1", "v2")
    week = rng.integers(0, 6, n)
    start = pd.Series(build).map(RELEASE) + pd.to_timedelta(week * 7 + 1, unit="D")
    runs = pd.DataFrame(dict(
        run_key=[f"r{i}" for i in range(n)], build_id=build, ascension=rng.integers(0, 10, n),
        tagged=rng.random(n) < 0.3, start_time=start, win=rng.random(n) < p,
        floors_reached=2 * reached.sum(axis=1) + 1))
    if lose_if_short:
        runs["win"] &= reached[:, K - 1]
    i, s, j = np.nonzero(np.broadcast_to(reached[:, :, None], card.shape))
    offers = pd.DataFrame(dict(
        run_key=runs.run_key.to_numpy()[i], floor=2 * (s + 1), set_idx=0,
        source=np.where(elite[i, s], "elite", "combat"),
        card_id=np.array(CARDS)[card[i, s, j]], picked=picked[i, s, j],
        upgraded=rng.random(len(i)) < 0.1))
    return runs, offers


@pytest.fixture(scope="module")
def planted(ref):
    return wins.load_early(fake_db(*synth(effect=0.1, seed=1)), "ironclad", ["v1", "v2"],
                           ref=ref)


@pytest.fixture(scope="module")
def null(ref):
    # IV z-scores over seeds 2-11 of this design: -1.5 to 2.5 (seed 2 is the 2.5)
    return wins.load_early(fake_db(*synth(effect=0.0, seed=7)), "ironclad", ["v1", "v2"],
                           ref=ref)


def within(res, truth, k=2):
    return abs(res["beta"] - truth) < k * res["se"]


# ------------------------------------------------------------------------------ estimators

def test_planted_effect(planted):
    a, f = wins.itt(planted, X), wins.first_stage(planted, X)
    b, c = wins.iv(planted, X), wins.naive(planted, X)
    assert within(b, 0.1) and b["beta"] > 3 * b["se"]
    # naive is biased upward: skilled runs pick more and win more
    assert c["beta"] - 0.1 > 3 * c["se"]
    assert wins.naive(planted, X, among_offered=True)["beta"] - 0.1 > 3 * c["se"]
    # itt = effect x first stage
    assert abs(a["beta"] - 0.1 * f["coef"]) < 2 * a["se"]
    assert b["beta"] == pytest.approx(a["beta"] / f["coef"], rel=0.05)
    assert f["F"] == pytest.approx((f["coef"] / f["se"]) ** 2) and not f["weak"]
    assert b["first_stage_F"] == pytest.approx(f["F"]) and not b["weak"]
    assert a["formula"] == "win ~ offered | build_group + asc + build_week"
    assert b["formula"] == "win ~ 1 | build_group + asc + build_week | picked ~ offered"
    assert a["n_runs"] == f["n_runs"] == b["n_runs"] == c["n_runs"]
    assert a["win_rate_offered"] > a["win_rate_not_offered"]


def test_no_effect(null):
    b, c = wins.iv(null, X), wins.naive(null, X)
    assert within(b, 0.0)
    assert c["beta"] > 3 * c["se"]
    assert within(wins.itt(null, X), 0.0)


def test_survival_bias_ever_offered_vs_first_k(ref):
    # No effect. Later screens are reached mostly by skilled runs, who also win more. "Ever
    # offered" (every screen, every run) makes the offer a marker of survival: the itt
    # comes out positive. The first-K design doesn't.
    runs, offers = synth(effect=0.0, seed=3)
    con = fake_db(runs, offers)
    first_k = wins.load_early(con, "ironclad", ["v1", "v2"], K=3, ref=ref)
    ever = wins.load_early(con, "ironclad", ["v1", "v2"], K=12, ref=ref)
    a = wins.itt(first_k, X)
    e = wins.itt(ever, X, include_short_runs=True)
    assert within(a, 0.0)
    assert e["beta"] > 4 * e["se"]
    share = wins.reach_share(first_k.runs)
    assert (share.share_reached_K > 0.95).all() and (share.K == 3).all()
    assert (wins.reach_share(ever.runs).share_reached_K < 0.5).all()


def test_short_runs_default_vs_keeping_them(ref):
    # No effect of X on anything. Deaths before screen 3 are more likely for less skilled
    # runs, and a run that dies before screen 3 loses. Keeping those runs with their
    # unreached screens counted as "not offered" makes "not offered" collect the early
    # deaths: a fake positive ITT. The default (runs that reached screen 3) and K = 1 don't.
    kw = dict(effect=0.0, early_hazard=0.03, early_hazard_skill=1.5, lose_if_short=True,
              seed=11)
    con = fake_db(*synth(**kw))
    d3 = wins.load_early(con, "ironclad", ["v1", "v2"], ref=ref)
    d1 = wins.load_early(con, "ironclad", ["v1", "v2"], K=1, ref=ref)
    assert (d3.runs.n_screens_reached < 3).mean() > 0.1
    assert not d3.runs.win[d3.runs.n_screens_reached < 3].any()
    assert within(wins.itt(d3, X), 0.0, 2.5)
    keep = wins.itt(d3, X, include_short_runs=True)
    assert keep["beta"] > 5 * keep["se"]
    assert within(wins.itt(d1, X), 0.0, 2.5)


def test_early_offer_that_kills_before_screen_k(ref):
    # X has no effect on runs that reach screen 3, but a run offered X on screen 1 or 2
    # dies before screen 3 (and loses) with 15% extra probability. The default compares
    # runs that reached screen 3, among which X does nothing: no fake ITT. K = 1 (every
    # run offered anything reached screen 1) recovers the total effect of an offer on
    # screen 1: about -(0.15 - 0.15 x 0.3 offered on screen 2 instead) x 0.3 win rate.
    runs, offers = synth(effect=0.0, early_hazard=0.01, x_death=0.15, lose_if_short=True,
                         seed=12)
    con = fake_db(runs, offers)
    d3 = wins.load_early(con, "ironclad", ["v1", "v2"], ref=ref)
    d1 = wins.load_early(con, "ironclad", ["v1", "v2"], K=1, ref=ref)
    early = offers[(offers.card_id == X) & (offers.floor <= 4)].run_key.unique()
    short = runs.set_index("run_key").floors_reached < 2 * 3 + 1
    assert short[early].mean() > short.drop(early).mean() + 0.1   # the offer kills
    assert within(wins.itt(d3, X), 0.0, 2.5)
    assert within(wins.iv(d3, X), 0.0, 2.5)
    total = wins.itt(d1, X)
    assert total["beta"] < -3 * total["se"]
    assert within(total, -(0.15 - 0.15 * 0.3) * 0.3, 2.5)


def test_screen_mix(ref):
    # Skilled runs take an early elite more often (and win more); elites offer X (a rare
    # card) ten times as often as normal fights; X has no effect. Without screen_mix,
    # "offered X" carries skill: a fake positive ITT and IV. With it, the offer is random
    # given the screen types: about 0. A common card (C1) is about 0 either way.
    runs, offers = synth(effect=0.0, elite_rate=0.2, elite_skill=1.0,
                         x_offer_weight={"combat": 0.3, "elite": 3.0}, seed=22)
    con = fake_db(runs, offers)
    data = wins.load_early(con, "ironclad", ["v1", "v2"], ref=ref)
    assert data.runs.screen_sources.astype(str).str.contains("elite").mean() > 0.3
    a0, a1 = wins.itt(data, X), wins.itt(data, X, screen_mix=True)
    b0, b1 = wins.iv(data, X), wins.iv(data, X, screen_mix=True)
    assert a0["beta"] > 4 * a0["se"] and b0["beta"] > 4 * b0["se"]
    assert within(a1, 0.0, 2.5) and within(b1, 0.0, 2.5)
    # the price: wider error bars for the rare card (x1.10 itt, x1.23 iv on this seed)
    assert 1.05 < a1["se"] / a0["se"] < 1.2 and 1.1 < b1["se"] / b0["se"] < 1.4
    for kw in ({}, dict(screen_mix=True)):
        assert within(wins.itt(data, "C1", **kw), 0.0, 3)
        assert within(wins.iv(data, "C1", **kw), 0.0, 3)
    c = wins.itt(data, "C1")
    assert 0.95 < wins.itt(data, "C1", screen_mix=True)["se"] / c["se"] < 1.05
    # run_all_cards takes screen_mix too
    out0 = wins.run_all_cards(con, "ironclad", ["v1", "v2"], min_offered=100, data=data,
                              ref=ref).set_index("card_id")
    out1 = wins.run_all_cards(con, "ironclad", ["v1", "v2"], min_offered=100, data=data,
                              screen_mix=True, ref=ref).set_index("card_id")
    assert out1.loc[X, "itt_beta"] == pytest.approx(a1["beta"])
    assert out0.loc[X, "itt_beta"] == pytest.approx(a0["beta"])
    assert out1.formula.str.endswith("+ screen_sources").all()


def test_one_row_per_run(ref):
    # The fits use HC1 errors without clustering: one row per run, or refuse.
    runs, offers = synth(n=500, seed=13)
    data = wins.load_early(fake_db(runs, offers), "ironclad", ["v1", "v2"], ref=ref)
    assert data.runs.run_key.is_unique and wins.run_frame(data, X).run_key.is_unique
    doubled = wins.Early(pd.concat([data.runs, data.runs.iloc[:3]]), data.offers, data.K)
    with pytest.raises(ValueError, match="more than one row"):
        wins.itt(doubled, X)
    # two different records under one run_key (runs_dedup can't produce this; identical
    # rows would merge in the GROUP BY)
    dup = pd.concat([runs, runs.iloc[:2].assign(ascension=11)])
    with pytest.raises(ValueError, match="more than one row"):
        wins.load_early(fake_db(dup, offers), "ironclad", ["v1", "v2"], ref=ref)


def test_weak_instrument(ref):
    data = wins.load_early(fake_db(*synth(x_weight=0.0003, effect=0.0, seed=4)), "ironclad",
                           ["v1", "v2"], ref=ref)
    f = wins.first_stage(data, X)
    assert f["F"] < 10 and f["weak"]
    assert wins.iv(data, X)["weak"]
    assert not wins.first_stage(data, "C1")["weak"]


def test_options(planted):
    a = wins.itt(planted, X)
    short = wins.itt(planted, X, include_short_runs=True)
    assert short["n_runs"] > a["n_runs"]
    tagged = wins.itt(planted, X, group="tagged")
    assert tagged["formula"] == "win ~ offered | build_id + asc + build_week"
    assert tagged["n_runs"] < 0.4 * a["n_runs"]
    pooled = wins.itt(planted, X, pooled_groups=True)
    assert pooled["n_runs"] == a["n_runs"] and "build_group" not in pooled["formula"]
    mix = wins.itt(planted, X, screen_mix=True)
    assert mix["formula"].endswith("+ screen_sources")
    with pytest.raises(ValueError, match="K = 3"):
        wins.itt(planted, X, K=4)
    d = wins.run_frame(planted, X)
    assert (d.n_screens_reached == 3).all() and len(d) == a["n_runs"] + a[
        "n_singletons_dropped"]


def test_run_all_cards(ref):
    con = fake_db(*synth(n=6000, effect=0.1, seed=5))
    data = wins.load_early(con, "ironclad", ["v1", "v2"], ref=ref)
    out = wins.run_all_cards(con, "ironclad", ["v1", "v2"], min_offered=100, ref=ref)
    assert set(out.card_id) == set(CARDS) and (out.error == "").all()
    assert out.n_offered_runs.is_monotonic_decreasing
    row = out.set_index("card_id").loc[X]
    assert row.iv_beta == pytest.approx(wins.iv(data, X)["beta"])
    assert row.itt_beta == pytest.approx(wins.itt(data, X)["beta"])
    assert row.naive_beta == pytest.approx(wins.naive(data, X)["beta"])
    assert row.fs_F == pytest.approx(wins.first_stage(data, X)["F"])
    assert 0.95 < row.share_reached_K <= 1
    few = wins.run_all_cards(con, "ironclad", ["v1", "v2"], min_offered=10**6, data=data,
                             ref=ref)
    assert few.empty and "iv_beta" in few.columns


# ------------------------------------------------------------------------------ SQL tables

def test_early_tables_by_hand(ref):
    t = RELEASE["v1"] + pd.Timedelta(days=9)            # week 1 of v1
    R = lambda k, **kw: dict(dict(run_key=k, build_id="v1", ascension=5, tagged=False,
                                  start_time=t, win=True, floors_reached=20), **kw)
    runs = pd.DataFrame([
        R("a", tagged=True),                  # two screens on floor 2 (Prayer Wheel)
        R("b", win=False),                    # 2 screens only
        R("c"),                               # an unsplit list among the first 3 screens
        R("d", was_abandoned=True),           # abandoned: out
        R("e", retried=True),                 # retried: out
        R("f", character="CHARACTER.SILENT"),  # another character
        R("g", build_id="v2"),                # another build
        R("h"),                               # no reward screen at all
    ])
    O = lambda k, fl, si, card, picked=False, upg=False, src="combat": dict(
        run_key=k, floor=fl, set_idx=si, source=src, card_id=card, picked=picked,
        upgraded=upg)
    offers = pd.DataFrame([
        O("a", 2, 0, "C0"), O("a", 2, 0, "C1", True), O("a", 2, 0, "C2"),
        O("a", 2, 1, "C3"), O("a", 2, 1, "C4"), O("a", 2, 1, "C5"),
        O("a", 4, 0, "C0", True, True, "elite"), O("a", 4, 0, "C6", src="elite"),
        O("a", 4, 0, "C7", src="elite"),
        O("a", 6, 0, "C8", True), O("a", 6, 0, "C9"), O("a", 6, 0, "C1"),     # screen 4
        O("b", 2, 0, "C0"), O("b", 2, 0, "C1"), O("b", 2, 0, "C2"),
        O("b", 3, 0, "C3", True), O("b", 3, 0, "C4"), O("b", 3, 0, "C5"),
        O("c", 2, 0, "C0"), O("c", 2, 0, "C1"), O("c", 2, 0, "C2"),
        O("c", 3, None, "C3"), O("c", 3, None, "C4"),
        *[O(k, 2, 0, "C0") for k in "defg"],
    ])
    con = fake_db(runs, offers)
    r = wins.early_runs(con, "ironclad", ["v1"], ref=ref).set_index("run_key")
    assert sorted(r.index) == ["a", "b", "c", "h"]
    assert r.n_screens_reached.to_dict() == {"a": 3, "b": 2, "c": 2, "h": 0}
    assert r.ambiguous_screens.to_dict() == {"a": False, "b": False, "c": True, "h": False}
    assert r.screen_sources["a"] == "combat>combat>elite" and r.screen_sources["h"] == ""
    assert (r.week == 1).all() and r.group["a"] == "tagged" and r.group["b"] == "untagged"
    assert sorted(wins.early_runs(con, None, ["v1", "v2"], ref=ref).run_key) == list("abcfgh")

    o = wins.early_offers(con, "ironclad", ["v1"], ref=ref)
    a = o[o.run_key == "a"].set_index("card_id")
    assert sorted(a.index) == [f"C{i}" for i in range(8)]          # not C8/C9 (screen 4)
    assert a.loc["C0", ["offered_screens", "picked", "first_screen", "upgraded_offer"]
                 ].tolist() == [2, True, 1, True]
    assert a.loc["C1", ["offered_screens", "picked", "first_screen"]].tolist() == [1, True, 1]
    assert a.loc["C4", "first_screen"] == 2 and a.loc["C6", "first_screen"] == 3
    assert o.offered.all() and set(o.run_key) == {"a", "b", "c"}
    assert list(o.columns) == wins.OFFER_COLS + wins.RUN_COLS[1:]

    data = wins.load_early(con, "ironclad", ["v1"], ref=ref)
    assert wins.run_frame(data, "C0").run_key.tolist() == ["a"]
    short = wins.run_frame(data, "C0", include_short_runs=True).set_index("run_key")
    assert short.offered.to_dict() == {"a": 1, "b": 1, "h": 0}
    assert short.picked.to_dict() == {"a": 1, "b": 0, "h": 0}
    share = wins.reach_share(data.runs, K=3)
    assert share[["runs", "reached_K", "ambiguous"]].values.tolist() == [[4, 1, 1]]


# ------------------------------------------------------------------------------ real pages

SMOKE_DB = os.environ.get("SPIROMETRY_SMOKE_DB")


@pytest.mark.skipif(not SMOKE_DB, reason="set SPIROMETRY_SMOKE_DB to a runs.duckdb built "
                                         "from fetched pages")
def test_smoke_real_pages():
    """End to end on real columns. Only checks that it runs; the estimates are meaningless
    at a page or two."""
    con = duckdb.connect(SMOKE_DB, read_only=True)
    builds = [b for (b,) in con.execute(
        "SELECT build_id FROM runs_dedup GROUP BY 1 ORDER BY count(*) DESC LIMIT 3").fetchall()]
    runs = wins.early_runs(con, None, builds)
    share = wins.reach_share(runs)
    assert len(share) and share.share_reached_K.between(0, 1).all()
    char = runs.character.value_counts().index[0]
    data = wins.load_early(con, char, builds)
    assert set(data.offers.first_screen) <= {1, 2, 3}
    out = wins.run_all_cards(con, char, builds, min_offered=20, data=data)
    assert len(out) and np.isfinite(out.itt_beta.dropna()).all()
    assert set(out.card_id) <= {c for c, col in did.card_colors().items()
                                if col == char.removeprefix("CHARACTER.").lower()}
