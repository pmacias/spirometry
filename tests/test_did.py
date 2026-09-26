"""spirometry.did on synthetic offers with known structure (no network, no run data).

A smoke test on real pages runs only when SPIROMETRY_SMOKE_DB points to a runs.duckdb
built from fetched pages; its estimates mean nothing at that size.
"""
import json
import os
import pathlib

import duckdb
import numpy as np
import pandas as pd
import pytest

from spirometry import did

CPID = "C0@v2/patch"
CARDS = [f"C{i}" for i in range(8)]
EXCLUDED, FLAGGED = "C7", "C6"          # control_exclusions, control_behavior_flags
RELEASE = pd.Timestamp("2026-04-16")
WINDOW_COLS = ["level", "event_id", "card_id", "change_kind", "members", "branch",
               "before_builds", "after_builds", "clean", "reason", "control_exclusions",
               "behavior_in_window", "behavior_event_ids", "control_behavior_flags"]


@pytest.fixture(scope="module")
def ref(tmp_path_factory):
    """A minimal reference folder: windows.csv, builds.csv, tweak_sizes.csv, card_changes.csv
    and raw/cards.json for one synthetic character ('ironclad') and card-patch."""
    ref = tmp_path_factory.mktemp("ref")
    pd.DataFrame([dict(level="card_patch", event_id=CPID, card_id="C0", change_kind="tweak",
                       branch="stable", before_builds="v1", after_builds="v2", clean="yes",
                       control_exclusions=EXCLUDED, control_behavior_flags=FLAGGED)],
                 columns=WINDOW_COLS).fillna("").to_csv(ref / "windows.csv", index=False)
    pd.DataFrame(dict(build_id=["v1", "v2"], branch="stable",
                      release_date=["2026-03-01", "2026-04-16"])).to_csv(
        ref / "builds.csv", index=False)
    pd.DataFrame(dict(card_id=["C0"], color=["ironclad"])).to_csv(ref / "card_changes.csv",
                                                                   index=False)
    pd.DataFrame(dict(card_patch_id=[CPID], card_id="C0", color="ironclad",
                      stable_build="v2", before_builds="v1", after_builds="v2",
                      main_field="damage", old="6", new="8", log_ratio="0.2877",
                      upgrade_only="no", mixed_direction="no", solo_estimable="yes",
                      direction="1")).to_csv(ref / "tweak_sizes.csv", index=False)
    (ref / "raw").mkdir()
    (ref / "raw" / "cards.json").write_text(json.dumps(
        [{"id": c, "color": "ironclad"} for c in CARDS] + [{"id": "X", "color": "silent"}]))
    return ref


def synth(n_runs=1500, screens=20, effect=0.0, run_sd=0.1, run_card_sd=0.1,
          share=(0.3, 0.3), treated_gap=0.0, pretrend=0.0, offer_boost=1.0, seed=0,
          base=(0.20, 0.50), effect_slope=0.0, cards=CARDS, after_weights=None):
    """Synthetic offers in load_window's columns. Per block, n_runs runs; each run has an
    uploader group (tagged with probability share[block]), an ascension, a run effect
    ~ N(0, run_sd) shared by all its offers, a run x card effect ~ N(0, run_card_sd) shared
    by the offers of one card in the run (a deck's taste for that card), and `screens`
    3-card screens drawn without replacement (the treated card
    C0's weight times offer_boost in the after block, or every card's weight times
    after_weights). Pick probability (linear, clipped): card baseline (evenly spaced over
    `base`) + group gap (C0 gets treated_gap more in the tagged group; the others
    alternate +-0.05) + 0.03 after + act and ascension effects + 0.10 upgraded + run and
    run x card effects + (effect + effect_slope * week) on C0 after + pretrend * (week + 1)
    on C0 before release. After-block runs are spread evenly over weeks 0-9."""
    rng = np.random.default_rng(seed)
    k = len(cards)
    base = np.linspace(*base, k)
    gap = np.array([treated_gap] + [0.05 * (-1) ** i for i in range(1, k)])
    runs = pd.DataFrame({"after": np.repeat([False, True], n_runs)})
    nr = len(runs)
    runs["tagged"] = rng.random(nr) < np.where(runs.after, share[1], share[0])
    runs["asc"] = rng.integers(0, 10, nr)
    runs["u"] = rng.normal(0, run_sd, nr)
    u_card = rng.normal(0, run_card_sd, (nr, k))
    late = rng.random(nr) < 0.15              # before-build runs played after the release
    runs["week"] = np.where(runs.after, rng.integers(0, 10, nr),
                            np.where(late, rng.integers(0, 3, nr), rng.integers(-8, 0, nr)))
    # screens: top-3 of Gumbel-perturbed log weights = 3 draws without replacement
    w = np.ones((nr, k))
    w[runs.after.to_numpy(), 0] *= offer_boost
    if after_weights is not None:
        w[runs.after.to_numpy()] *= np.asarray(after_weights, dtype=float)
    keys = np.log(w)[:, None, :] + rng.gumbel(size=(nr, screens, k))
    card = np.argsort(-keys, axis=2)[:, :, :3]                  # (run, screen, 3)
    r_idx = np.broadcast_to(np.arange(nr)[:, None, None], card.shape).ravel()
    s_idx = np.broadcast_to(np.arange(screens)[None, :, None], card.shape).ravel()
    card = card.ravel()
    rr = runs.iloc[r_idx].reset_index(drop=True)
    act = 1 + s_idx * 3 // screens
    upgraded = rng.random(len(card)) < 0.2
    treated_after = (card == 0) & rr.after.to_numpy()
    pre = (card == 0) & ~rr.after.to_numpy() & (rr.week.to_numpy() < 0)
    p = (base[card] + gap[card] * rr.tagged.to_numpy() + 0.03 * rr.after.to_numpy()
         + np.array([0, 0.0, 0.04, -0.03])[act] + 0.01 * rr.asc.to_numpy()
         + 0.10 * upgraded + rr.u.to_numpy() + u_card[r_idx, card]
         + (effect + effect_slope * rr.week.to_numpy()) * treated_after
         + pretrend * (rr.week.to_numpy() + 1) * pre)
    picked = rng.random(len(card)) < np.clip(p, 0.02, 0.98)
    run_key = pd.Series([f"r{i}" for i in r_idx])
    df = pd.DataFrame({
        "run_key": run_key, "card_id": np.array(cards)[card],
        "block": np.where(rr.after, "after", "before"), "picked": picked,
        "upgraded": upgraded, "act": act.astype("int8"),
        "ascension": rr.asc.astype("Int16"),
        "group": np.where(rr.tagged, "tagged", "untagged"),
        "screen_id": run_key + "|" + pd.Series(s_idx).astype(str) + "|0",
        "start_time": RELEASE + pd.to_timedelta(rr.week * 7 + 1, unit="D"),
        "week": rr.week.astype("int16"),
        "build_id": np.where(rr.after, "v2", "v1"),
        "uploader_hash": np.where(rr.tagged, "u" + (pd.Series(r_idx) % 50).astype(str),
                                  None)})
    for c in did.CATEGORICAL:
        df[c] = df[c].astype("category")
    return df


def within(res, truth, k=2):
    return abs(res["beta"] - truth) < k * res["se"]


# ------------------------------------------------------------------------------ fit_did

def test_recovers_planted_effect_and_null(ref):
    res = did.fit_did(synth(effect=0.06, seed=1), CPID, ref=ref)
    assert within(res, 0.06) and res["beta"] > 3 * res["se"]
    assert res["formula"] == ("picked ~ treat_post | card_id^upg + card_id^group "
                              "+ block^group + act + asc")
    null = did.fit_did(synth(effect=0.0, seed=2), CPID, ref=ref)
    assert within(null, 0.0)
    assert null["treated_rate_after"] - null["treated_rate_before"] == pytest.approx(
        null["control_rate_after"] - null["control_rate_before"], abs=0.03)


def test_group_terms_remove_mix_shift_bias(ref):
    # Tagged uploaders pick C0 20 points more; their share rises from 10% to 70% after the
    # patch; true effect 0. Pooled, C0's rise from the mix looks like an effect.
    # Expected pooled bias ~ (0.7 - 0.1) x 0.20 = 0.12.
    df = synth(effect=0.0, share=(0.1, 0.7), treated_gap=0.20, seed=4)
    pooled = did.fit_did(df, CPID, pooled_groups=True, ref=ref)
    grouped = did.fit_did(df, CPID, ref=ref)
    assert pooled["beta"] > 0.08 and pooled["beta"] > 8 * pooled["se"]
    assert within(grouped, 0.0, 3)
    assert "group" not in pooled["formula"]


def test_clustered_se_vs_naive(ref):
    # Offers of one card within a run are correlated (run x card effect): clustering by run
    # widens the error bars.
    on = did.fit_did(synth(run_sd=0.0, run_card_sd=0.15, seed=4), CPID, ref=ref)
    off = did.fit_did(synth(run_sd=0.0, run_card_sd=0.0, seed=4), CPID, ref=ref)
    assert on["se"] / on["se_iid"] > 1.1
    assert 0.9 < off["se"] / off["se_iid"] < 1.1
    # A run effect shared by every card in the run cancels in the treated-vs-control
    # contrast, so on its own it doesn't widen them (the iid errors overstate it instead).
    common = did.fit_did(synth(run_sd=0.15, run_card_sd=0.0, seed=4), CPID, ref=ref)
    assert common["se"] / common["se_iid"] < 1.05


def test_robust_se_separates_unequal_variance_from_clustering(ref):
    # C0 is picked ~5% of the time, the controls ~30-60%: a 0/1 outcome's variance differs
    # a lot between cards. Without within-run correlation the iid SE is off (it assumes one
    # variance), but clustering adds nothing over heteroskedasticity-robust errors.
    kw = dict(base=(0.0, 0.6), run_sd=0.0, seed=10)
    het = did.fit_did(synth(run_card_sd=0.0, **kw), CPID, ref=ref)
    assert het["se"] / het["se_iid"] < 0.8
    assert 0.93 < het["se"] / het["se_hc"] < 1.07
    # A run x card effect correlates one card's offers within a run: clustering widens the
    # bars beyond the robust ones.
    cor = did.fit_did(synth(run_card_sd=0.15, **kw), CPID, ref=ref)
    assert cor["se"] / cor["se_hc"] > 1.1


def test_fixed_horizon(ref):
    # The effect grows by 2 points a week after release: 0.02 + 0.02 * week, weeks 0-9.
    # Capped at week 3 the fit recovers the mean over weeks 0-3 (0.05), uncapped the mean
    # over weeks 0-9 (0.11). The before block is the same in both fits. No run or run x card
    # noise, so no pick probability is clipped and the planted effect is exactly linear.
    df = synth(effect=0.02, effect_slope=0.02, run_sd=0.0, run_card_sd=0.0, seed=13)
    full = did.fit_did(df, CPID, ref=ref)
    cap = did.fit_did(df, CPID, max_week_after=3, ref=ref)
    assert within(full, 0.11, 3) and within(cap, 0.05, 3)
    assert cap["beta"] + 3 * cap["se"] < full["beta"]
    assert (full["max_week_after"], full["after_week_max"]) == (None, 9)
    assert (cap["max_week_after"], cap["after_week_max"]) == (3, 3)
    ctrl = [c for c in CARDS if c != EXCLUDED]
    kept = df.card_id.isin(ctrl) & ((df.block == "before") | (df.week <= 3))
    assert cap["n_offers"] + cap["n_singletons_dropped"] == kept.sum()
    assert cap["control_rate_before"] == full["control_rate_before"]
    assert cap["treated_rate_before"] == full["treated_rate_before"]


def test_fit_options(ref):
    df = synth(effect=0.06, seed=5)
    full = did.fit_did(df, CPID, ref=ref)
    assert full["n_offers"] + full["n_singletons_dropped"] == df.card_id.isin(
        [c for c in CARDS if c != EXCLUDED]).sum()
    assert full["n_singletons_dropped"] == 0
    # controls: C7 excluded always, C6 (behavior flag) only when asked
    assert did.control_cards(CPID, df=df, ref=ref) == ["C1", "C2", "C3", "C4", "C5", "C6"]
    assert did.control_cards(CPID, True, df=df, ref=ref) == ["C1", "C2", "C3", "C4", "C5"]
    assert did.control_cards(CPID, ref=ref) == ["C1", "C2", "C3", "C4", "C5", "C6"]
    flags = did.fit_did(df, CPID, drop_behavior_flags=True, ref=ref)
    assert flags["n_offers"] == full["n_offers"] - (df.card_id == FLAGGED).sum()
    shared = did.fit_did(df, CPID, drop_shared_screens=True, ref=ref)
    treated_screens = df.screen_id[df.card_id == "C0"].unique()
    dropped = (df.screen_id.isin(treated_screens) & ~df.card_id.isin(["C0", EXCLUDED])).sum()
    assert shared["n_offers"] == full["n_offers"] - dropped
    assert shared["n_treated_offers"] == full["n_treated_offers"]
    up = did.fit_did(df, CPID, upgraded=True, ref=ref)
    assert up["n_treated_offers"] == ((df.card_id == "C0") & df.upgraded).sum()
    tagged = did.fit_did(df, CPID, group="tagged", ref=ref)
    assert "group" not in tagged["formula"] and within(tagged, 0.06, 3)
    heavy = df.uploader_hash.value_counts().index[:5].tolist()
    no_heavy = did.fit_did(df, CPID, drop_uploaders=heavy, ref=ref)
    assert no_heavy["n_offers"] == full["n_offers"] - (
        df.uploader_hash.isin(heavy) & (df.card_id != EXCLUDED)).sum()


def test_to_log_odds():
    b, s = did.to_log_odds(0.05, 0.01, 0.2)
    assert b == pytest.approx(0.05 / 0.16) and s == pytest.approx(0.01 / 0.16)
    assert np.isnan(did.to_log_odds(0.05, 0.01, 0.0)[0])


# ------------------------------------------------------------------------------ offer rate

def test_offer_rate_check_flags_planted_share_change(ref):
    t = did.offer_rate_check(synth(offer_boost=2.0, seed=6), CPID, ref=ref)
    assert t.card_id.tolist() == ["C0", "C1", "C2", "C3", "C4", "C5", "C6"]
    assert t.loc[t.treated, "flag"].item()
    assert t.loc[t.treated, "log_share_ratio"].item() > 0.4
    assert not t.loc[~t.treated, "flag"].any()
    clean = did.offer_rate_check(synth(offer_boost=1.0, seed=6), CPID, ref=ref)
    assert not clean.flag.any()
    assert (t.offers_before + t.offers_after > 0).all()


RARITY_CARDS = [f"R{i}" for i in range(20)]
RARITY_CPID = "R0@v2/patch"


@pytest.fixture(scope="module")
def rarity_ref(tmp_path_factory, ref):
    """20 cards of one color: R0 (treated) and R1-R5 Uncommon, R6-R17 Common, R18-R19
    Rare (2 controls: too few for their own comparison)."""
    rref = tmp_path_factory.mktemp("rref")
    for f in ("builds.csv", "card_changes.csv"):
        (rref / f).write_bytes((ref / f).read_bytes())
    pd.DataFrame([dict(level="card_patch", event_id=RARITY_CPID, card_id="R0",
                       change_kind="tweak", branch="stable", before_builds="v1",
                       after_builds="v2", clean="yes")],
                 columns=WINDOW_COLS).fillna("").to_csv(rref / "windows.csv", index=False)
    rarity = ["Uncommon"] * 6 + ["Common"] * 12 + ["Rare"] * 2
    (rref / "raw").mkdir()
    (rref / "raw" / "cards.json").write_text(json.dumps(
        [{"id": c, "color": "ironclad", "rarity": r} for c, r in zip(RARITY_CARDS, rarity)]))
    return rref


def test_offer_rate_check_same_rarity(rarity_ref):
    # The Uncommon pool shrinks: every Uncommon card (R0-R5) is offered 1.5x as often after
    # the patch. Against all controls (mostly Common) they flag; against the other
    # Uncommon controls they don't.
    w = [1.5] * 6 + [1.0] * 14
    df = synth(cards=RARITY_CARDS, after_weights=w, n_runs=3000, seed=12)
    t = did.offer_rate_check(df, RARITY_CPID, ref=rarity_ref).set_index("card_id")
    unc = [f"R{i}" for i in range(6)]
    assert t.rarity[unc].eq("Uncommon").all() and t.rarity["R6"] == "Common"
    assert t.flag[unc].all() and not t.flag_rarity[unc].any()
    assert (t.n_controls_rarity[unc] == 5).all() and (t.rarity_note[unc] == "").all()
    assert not t.flag.drop(unc).any() and not t.flag_rarity.drop(unc).any()
    assert (t.n_controls_rarity[["R18", "R19"]] == 19).all()      # fell back to all controls
    assert t.rarity_note["R18"].startswith("2 Rare controls")
    assert (t.z_binom_rarity[["R18", "R19"]] == t.z_binom[["R18", "R19"]]).all()


# ------------------------------------------------------------------------------ event study

def test_event_study_shows_pretrend_and_omits_ref(ref):
    es = did.fit_event_study(synth(pretrend=0.03, effect=0.06, seed=7), CPID,
                             weeks=(-6, 8), ref=ref)
    cells = set(zip(es.week, es.block))
    assert (-1, "before") not in cells
    assert es.week.min() == -6 and es.week.max() == 8          # weeks -8, -7 binned into -6
    assert {(0, "before"), (1, "before"), (2, "before")} <= cells   # before build, after date
    early = es[(es.week == -6) & (es.block == "before")].iloc[0]
    assert early.coef < -3 * early.se                           # planted -0.15 at week -6
    after = es[es.block == "after"]
    assert (abs(after.coef - 0.06) < 3 * after.se).mean() > 0.8
    flat = did.fit_event_study(synth(pretrend=0.0, seed=7), CPID, ref=ref)
    pre = flat[(flat.block == "before") & (flat.week < 0)]
    assert (abs(pre.coef) < 3 * pre.se).all()


# ------------------------------------------------------------------------------ duckdb path

def fake_db(df):
    """An in-memory DuckDB with offers_with_version and runs shaped like runs.duckdb's."""
    o = df.astype({c: str for c in did.CATEGORICAL}).copy()
    o["run_hash"] = o.run_key
    o["character"] = "CHARACTER.IRONCLAD"
    o["uploader_tag"] = np.where(o.group == "tagged", "slay-the-stats/v1", None)
    o["floor"] = o.screen_id.str.split("|").str[1].astype(int)
    o["set_idx"] = 0
    o["ascension"] = o.ascension.astype(int)
    o["uploader_hash"] = o.uploader_hash.replace("None", None)
    runs = o.groupby("run_hash", as_index=False).uploader_hash.first()
    o = o.drop(columns=["group", "block", "screen_id", "week", "uploader_hash"])
    extra = o.iloc[:5].assign(card_id="X", character="CHARACTER.SILENT")   # other character
    con = duckdb.connect()
    con.register("o_df", pd.concat([o, extra]))
    con.register("r_df", runs)
    con.execute("CREATE TABLE offers_with_version AS SELECT * FROM o_df")
    con.execute("CREATE TABLE runs AS SELECT * FROM r_df")
    return con


def test_load_window_and_run_all(ref):
    df = synth(effect=0.06, n_runs=600, seed=8)
    con = fake_db(df)
    got = did.load_window(con, CPID, ref=ref)
    assert list(got.columns) == ["run_key", "card_id", "block", "picked", "upgraded", "act",
                                 "ascension", "group", "screen_id", "start_time", "week",
                                 "build_id", "uploader_hash"]
    assert len(got) == len(df) and set(got.card_id) == set(CARDS)
    assert (got.groupby(["block", "group"], observed=True).size()
            == df.groupby(["block", "group"], observed=True).size()).all()
    assert (got.sort_values(["run_key", "screen_id", "card_id"]).week.to_numpy()
            == df.sort_values(["run_key", "screen_id", "card_id"]).week.to_numpy()).all()
    assert isinstance(got.run_key.dtype, pd.CategoricalDtype)
    res = did.run_all(con, ref=ref)
    assert len(res) == 1 and (res.error == "").all()
    row = res.iloc[0]
    assert row.card_patch_id == CPID and row.log_ratio == "0.2877"
    assert row.beta == pytest.approx(did.fit_did(got, CPID, ref=ref)["beta"])
    assert row.beta_lo == pytest.approx(row.beta / (row.treated_rate_before
                                                    * (1 - row.treated_rate_before)))


def test_run_all_upgrade_only_placebo(ref, tmp_path):
    ts = pd.read_csv(ref / "tweak_sizes.csv", dtype=str)
    uref = tmp_path / "ref"
    uref.mkdir()
    for f in ("windows.csv", "builds.csv", "card_changes.csv"):
        (uref / f).write_bytes((ref / f).read_bytes())
    (uref / "raw").mkdir()
    (uref / "raw" / "cards.json").write_bytes((ref / "raw" / "cards.json").read_bytes())
    ts.assign(upgrade_only="yes").to_csv(uref / "tweak_sizes.csv", index=False)
    con = fake_db(synth(n_runs=600, seed=9))
    row = did.run_all(con, ref=uref).iloc[0]
    assert row.fit_on == "upgraded offers" and row.error == row.placebo_error == ""
    assert row.placebo_n_offers > row.n_offers          # most offers aren't upgraded
    assert row.se_hc > 0 and pd.isna(row.max_week_after)
    capped = did.run_all(con, ref=uref, max_week_after=3).iloc[0]
    assert capped.error == capped.placebo_error == "" and capped.max_week_after == 3
    assert capped.after_week_max == 3
    assert capped.n_offers < row.n_offers and capped.placebo_n_offers < row.placebo_n_offers


# ------------------------------------------------------------------------------ real pages

SMOKE_DB = os.environ.get("SPIROMETRY_SMOKE_DB")


@pytest.mark.skipif(not SMOKE_DB, reason="set SPIROMETRY_SMOKE_DB to a runs.duckdb built "
                                         "from fetched pages")
def test_smoke_real_pages():
    """End to end on real columns: the first stable window (v0.99.1 -> v0.103.2). Only
    checks that it runs; the estimate is meaningless at a page or two."""
    con = duckdb.connect(SMOKE_DB, read_only=True)
    cpid = "PARRY@v0.103.2/patch"
    df = did.load_window(con, cpid)
    assert set(df.block) == {"before", "after"}
    assert set(df.card_id) <= {c for c, col in did.card_colors().items() if col == "regent"}
    res = did.fit_did(df, cpid)
    assert np.isfinite(res["beta"]) and res["se"] > 0 and res["n_runs"] > 0
    assert did.offer_rate_check(df, cpid).treated.sum() == 1
    tweaks = pd.read_csv(did.REF / "tweak_sizes.csv", dtype=str)
    first = tweaks[(tweaks.before_builds == "v0.99.1") & (tweaks.solo_estimable == "yes")]
    out = did.run_all(con, tweaks=first.card_patch_id.tolist())
    assert len(out) == len(first)
