"""Anticipation check (did.anticipation_*) and the beta exposure table (spirometry.exposure)
on synthetic offers with known structure, plus the real reference tables (no run data).

Synthetic calendar: stable v1 (old card) from 03-01, first beta of the change 03-21,
stable v2 (new card) from 04-10. Old-build runs start 03-01 to 04-09, so 20 days on each
side of the beta date; v2 runs 04-10 to 05-09. v1b is a second old-version stable build
(identical card versions, used by another window) and v0 an identical one outside every
window. A smoke test on real pages runs only when SPIROMETRY_SMOKE_DB is set.
"""
import json
import os

import duckdb
import numpy as np
import pandas as pd
import pytest

from spirometry import did, exposure

CARDS = [f"C{i}" for i in range(8)]
CPID = "C0@v2/patch"
T0, TB, TS = pd.Timestamp("2026-03-01"), pd.Timestamp("2026-03-21"), pd.Timestamp("2026-04-10")
WINDOW_COLS = ["level", "event_id", "card_id", "change_kind", "members", "branch",
               "before_builds", "after_builds", "clean", "reason", "control_exclusions",
               "behavior_in_window", "behavior_event_ids", "control_behavior_flags"]


def make_ref(ref, beta_date=TB):
    """Reference folder: one card-patch window v1 -> v2 (C0 treated, C7 excluded), a second
    window that uses v1b, card versions (v0, v1, v1b identical; v2 changes C0; C5 has a
    bug-fix behavior event on v1b only), builds, beta exposure, colors."""
    ref.mkdir(parents=True, exist_ok=True)
    win = lambda eid, card, b, a: dict(level="card_patch", event_id=eid, card_id=card,
                                       change_kind="tweak", branch="stable",
                                       before_builds=b, after_builds=a, clean="yes",
                                       control_exclusions="C7")
    pd.DataFrame([win(CPID, "C0", "v1", "v2"), win("C6@v3/patch", "C6", "v1b", "v3")],
                 columns=WINDOW_COLS).fillna("").to_csv(ref / "windows.csv", index=False)
    rel = dict(v0="2026-02-20", v1="2026-03-01", v1b="2026-03-05", v2="2026-04-10",
               v3="2026-05-20")
    pd.DataFrame(dict(build_id=list(rel), branch="stable", release_date=list(rel.values()))
                 ).to_csv(ref / "builds.csv", index=False)
    rows = []
    for c in CARDS:
        for b in rel:
            rows.append(dict(card_id=c, build_id=b, branch="stable", release_date=rel[b],
                             version="2" if (c == "C0" and b in ("v2", "v3")) else "1",
                             event_ids="", behavior_event_ids="C5@fix" if
                             (c == "C5" and b == "v1b") else "", note=""))
    pd.DataFrame(rows).to_csv(ref / "card_versions.csv", index=False)
    pd.DataFrame(dict(card_id=["C0"], color=["ironclad"])).to_csv(ref / "card_changes.csv",
                                                                   index=False)
    pd.DataFrame([dict(card_patch_id=CPID, card_id="C0", color="ironclad", stable_build="v2",
                       stable_date="2026-04-10", first_beta_build="vb",
                       first_beta_date=str(beta_date.date()), lead_days="",
                       upgrade_only="no")]).to_csv(ref / "beta_exposure.csv", index=False)
    (ref / "raw").mkdir(exist_ok=True)
    (ref / "raw" / "cards.json").write_text(json.dumps(
        [{"id": c, "color": "ironclad"} for c in CARDS] + [{"id": "X", "color": "silent"}]))
    return ref


@pytest.fixture
def ref(tmp_path):
    return make_ref(tmp_path)


def synth(gap, *, n_old=4000, n_new=3000, screens=15, stragglers=0, seed=0,
          builds_old=("v1",)):
    """Offers in offers_with_version's columns. Old-build runs start uniformly 03-01 to
    04-09 (on builds_old at random), new-build (v2) runs 04-10 to 05-09, and `stragglers`
    v1 runs after 04-10. Each run: an ascension, uploader group (30% tagged), a run effect,
    `screens` screens of 3 of the 8 cards at random. Pick probability: card baseline
    (0.2-0.5) + run effect + gap(day, on_new_build) on C0, where day = days since 03-01."""
    rng = np.random.default_rng(seed)
    days = np.concatenate([rng.uniform(0, 40, n_old), rng.uniform(40, 70, n_new),
                           rng.uniform(40, 60, stragglers)])
    new = np.r_[np.zeros(n_old, bool), np.ones(n_new, bool), np.zeros(stragglers, bool)]
    old_b = rng.choice(list(builds_old), n_old + stragglers)
    build = np.where(new, "v2", np.r_[old_b[:n_old], np.full(n_new, ""), old_b[n_old:]])
    nr = len(days)
    u = rng.normal(0, 0.08, nr)
    asc = rng.integers(0, 10, nr)
    tagged = rng.random(nr) < 0.3
    keys = rng.gumbel(size=(nr, screens, len(CARDS)))
    card = np.argsort(-keys, axis=2)[:, :, :3]
    r = np.broadcast_to(np.arange(nr)[:, None, None], card.shape).ravel()
    s = np.broadcast_to(np.arange(screens)[None, :, None], card.shape).ravel()
    card = card.ravel()
    base = np.linspace(0.2, 0.5, len(CARDS))
    p = base[card] + u[r] + 0.01 * asc[r] + (card == 0) * gap(days[r], new[r])
    picked = rng.random(len(card)) < np.clip(p, 0.02, 0.98)
    start = T0 + pd.to_timedelta(days, unit="D")
    key = np.array([f"r{i}" for i in range(nr)])
    o = pd.DataFrame(dict(
        run_key=key[r], run_hash=key[r], card_id=np.array(CARDS)[card], build_id=build[r],
        picked=picked, upgraded=rng.random(len(card)) < 0.2,
        act=(1 + s * 3 // screens).astype(int), ascension=asc[r],
        uploader_tag=np.where(tagged[r], "sts", None), floor=s + 1, set_idx=0,
        start_time=start[r], character="CHARACTER.IRONCLAD"))
    o["set_picked_any"] = o.groupby(["run_key", "floor"]).picked.transform("any")
    con = duckdb.connect()
    con.register("o_df", o)
    con.execute("CREATE TABLE offers_with_version AS SELECT * FROM o_df")
    con.execute("CREATE TABLE runs AS SELECT DISTINCT run_hash, NULL::VARCHAR AS "
                "uploader_hash FROM o_df")
    return con


D = 0.12
BETA_DAY, STABLE_DAY = (TB - T0).days, (TS - T0).days


def ramp(days, new):
    """Anticipation: C0's gap rises linearly from the beta date to the stable date."""
    return np.where(new, D, D * np.clip((days - BETA_DAY) / (STABLE_DAY - BETA_DAY), 0, 1))


def at_stable(days, new):
    return np.where(new, D, 0.0)


def within(x, truth, se, k=2):
    return abs(x - truth) < k * se


# ------------------------------------------------------------------------------ checks

def test_ramp_is_recovered(ref):
    # The move starts at the beta date and finishes at the stable date. On the old build
    # the post-beta side averages half of it: beta_postbeta ~ D/2. The main DiD's before
    # block is half post-beta, so it understates: beta_main ~ D - 0.5 x D/2 = 0.75 D, and
    # ratio_to_main ~ 2/3; total_implied = beta_main + share x beta_postbeta ~ D and
    # share_before_release ~ 1/2.
    a = did.anticipation_check(synth(ramp, seed=1), CPID, ref=ref)
    assert a["status"] == "informative" and a["reason"] == ""
    assert within(a["beta_postbeta"], D / 2, a["se"]) and a["beta_postbeta"] > 5 * a["se"]
    assert 0.45 < a["main_postbeta_share"] < 0.55
    assert within(a["beta_main"], 0.75 * D, a["se_main"])
    assert within(a["total_implied"], D, a["se_main"] + a["se"])
    assert 0.35 < a["share_before_release"] < 0.6
    # a ratio of two noisy estimates: 0.51-0.62 over seeds 1, 11, 21 (truth 2/3)
    assert 0.45 < a["ratio_to_main"] < 0.8
    assert a["days_pre"] == 20 and a["days_post"] == 20
    assert a["builds"] == "v1 v1b" or a["builds"] == "v1"
    assert a["formula"].startswith("picked ~ treat_postbeta | card_id^upg")


def test_change_only_at_stable_gives_zero(ref):
    a = did.anticipation_check(synth(at_stable, seed=2), CPID, ref=ref)
    assert a["status"] == "informative"
    assert within(a["beta_postbeta"], 0.0, a["se"])
    assert within(a["beta_main"], D, a["se_main"])
    assert abs(a["share_before_release"]) < 0.15


def test_steady_drift_shows_up_as_postbeta(ref):
    # The limitation: C0 drifts up 0.01 a week from 03-01 on, through the beta date, with
    # no jump anywhere. The pre/post split can't tell that from anticipation:
    # beta_postbeta ~ slope x week_gap (the sides' mean weeks are about 3 apart). The
    # function returns that estimate as is, plus pre_slope (the weekly slope before the
    # beta date) and week_gap, so the reader can see that slope x gap explains it.
    slope = 0.01
    drift = lambda days, new: slope * days / 7
    a = did.anticipation_check(synth(drift, seed=3), CPID, ref=ref)
    assert a["beta_postbeta"] > 2 * a["se"]
    assert 2.5 < a["week_gap"] < 3.2
    assert within(a["beta_postbeta"], slope * a["week_gap"], a["se"])
    assert within(a["pre_slope"], slope, a["pre_slope_se"])
    wk = did.anticipation_weekly(synth(drift, seed=3), CPID, ref=ref)
    fit = np.polyfit(wk.week, wk.coef, 1)
    assert within(fit[0], slope, 0.004)                   # a straight line, no jump


def test_weekly_table(ref):
    wk = did.anticipation_weekly(synth(ramp, seed=4), CPID, ref=ref)
    # the old builds run from week -3 (03-01) to week 2 (04-09): clipped there
    assert wk.week.min() == -3 and wk.week.max() == 2 and -1 not in set(wk.week)
    assert set(wk.block[wk.week < 0]) == {"before"} and set(wk.block[wk.week >= 0]) == {
        "after"}
    pre, post = wk[wk.week < 0], wk[wk.week >= 0]
    assert (pre.coef.abs() < 2.5 * pre.se).all()
    assert post.coef.is_monotonic_increasing and post.coef.iloc[-1] > 3 * post.se.iloc[-1]
    assert wk.week_start[wk.week == 0].iloc[0] == "2026-03-21"
    assert (wk.first_beta_date == "2026-03-21").all()


def test_uninformative(tmp_path):
    # the beta two days after the old build's release (like v0.100.0 after v0.99.1):
    # 2 days pre-beta, a status and a reason, the numbers still there
    ref = make_ref(tmp_path / "a", beta_date=T0 + pd.Timedelta(days=2))
    a = did.anticipation_check(synth(ramp, seed=5), CPID, ref=ref)
    assert a["status"] == "uninformative" and "2 days pre-beta (< 3)" in a["reason"]
    assert a["days_pre"] == 2 and np.isfinite(a["beta_postbeta"])
    # too few offers: the threshold is an argument
    b = did.anticipation_check(synth(ramp, seed=5), CPID, ref=make_ref(tmp_path / "b"),
                               min_offers=10**6)
    assert b["status"] == "uninformative" and "treated offers pre-beta (< 1000000)" in \
        b["reason"]
    # no old-version data before the beta date at all: no fit, and the reason
    c = did.anticipation_check(synth(ramp, seed=5), CPID,
                               ref=make_ref(tmp_path / "c", beta_date=pd.Timestamp(
                                   "2026-02-25")), beta_main=0.1, se_main=0.01)
    assert c["status"] == "uninformative" and c["n_treated_offers_pre"] == 0
    assert "no treated offers in the before block" in c["reason"]
    assert np.isnan(c["beta_postbeta"]) and np.isnan(c["share_before_release"])


def test_old_version_builds_and_behavior(tmp_path):
    ref = make_ref(tmp_path)
    # v0 has identical versions but is in no window; v1b is in another window
    assert did.old_version_builds(CPID, ref=ref) == (["v1", "v1b"], ["C5"])
    assert did.old_version_builds(CPID, widen=False, ref=ref) == (["v1"], [])
    con = synth(at_stable, seed=6, stragglers=500, builds_old=("v1", "v1b"))
    df, info = did.load_anticipation(con, CPID, ref=ref)
    assert set(df.build_id) == {"v1", "v1b"} and info["behavior_differs"] == "C5"
    assert info["n_offers_dropped_after_stable"] == 500 * 15 * 3
    assert (df.start_time < TS).all()
    a = did.anticipation_check(con, CPID, data=(df, info), ref=ref, beta_main=0.1,
                               se_main=0.01)
    assert a["behavior_dropped"] == "C5" and not a["treated_behavior_differs"]
    assert "v1 pre" in a["treated_offers_by_build"] and "v1b post" in \
        a["treated_offers_by_build"]
    kept = did.load_anticipation(con, CPID, until_stable=False, ref=ref)[1]
    assert kept["n_offers_dropped_after_stable"] == 0
    # beta_main not clearly nonzero: no ratio
    z = did.anticipation_check(con, CPID, data=(df, info), ref=ref, beta_main=0.01,
                               se_main=0.01)
    assert np.isnan(z["ratio_to_main"]) and np.isnan(z["share_before_release"])


def test_anticipation_all(ref, tmp_path):
    con = synth(ramp, seed=7)
    one = did.anticipation_check(con, CPID, ref=ref)
    out = did.anticipation_all(con, ref=ref, min_offers=500)
    assert len(out) == 1 and out.card_patch_id.iloc[0] == CPID
    row = out.iloc[0]
    assert row.beta_postbeta == pytest.approx(one["beta_postbeta"])
    assert row.beta_main == pytest.approx(one["beta_main"])
    assert row.min_offers == 500 and row.upgrade_only == "no"
    main = pd.DataFrame(dict(card_patch_id=[CPID], beta=[0.5], se=[0.01]))
    given = did.anticipation_all(con, ref=ref, main=main).iloc[0]
    assert given.beta_main == 0.5 and given.ratio_to_main == pytest.approx(
        one["beta_postbeta"] / 0.5)
    out.to_parquet(tmp_path / "a.parquet")                # cacheable
    assert len(pd.read_parquet(tmp_path / "a.parquet")) == 1


# ------------------------------------------------------------------------------ reference

def test_exposure_table_on_reference():
    rows = exposure.build_rows(*(exposure.read_csv(did.REF / f) for f in (
        "tweak_sizes.csv", "windows.csv", "change_events.csv", "change_event_fields.csv",
        "builds.csv")))
    b = pd.DataFrame(rows).set_index("card_patch_id")
    assert len(b) == 43 and (b.upgrade_only == "yes").sum() == 3
    first = b[b.stable_build == "v0.103.2"]
    assert len(first) == 26 and (first.first_beta_build == "v0.100.0").sum() == 21
    p = b.loc["PARRY@v0.103.2/patch"]
    assert p.beta_steps == "v0.100.0:2026-03-19:6>8; v0.101.0:2026-03-26:8>10"
    assert p.lead_days == 28 and p.n_beta_steps == 2 and p.revised_or_reverted.startswith(
        "yes")
    assert b.loc["REFLECT@v0.107.1/patch", "first_beta_date"] == "2026-04-23"
    assert b.loc["ROYALTIES@v0.107.1/patch", "step_field"] == "upgrade.gold"
    assert (b.revised_or_reverted != "no").sum() == 3
    # the committed file is current
    committed = pd.read_csv(did.REF / "beta_exposure.csv", dtype=str, keep_default_na=False)
    assert committed.set_index("card_patch_id").beta_steps.to_dict() == b.beta_steps.to_dict()


def test_old_version_builds_on_reference():
    # first patch: v0.99.1 only (v0.98.x carry identical versions but are in no window);
    # second: v0.103.2 and v0.103.3, identical versions on every card
    assert did.old_version_builds("PARRY@v0.103.2/patch")[0] == ["v0.99.1"]
    for cpid in ("BULWARK@v0.107.1/patch", "REFLECT@v0.107.1/patch",
                 "SIC_EM@v0.107.1/patch"):
        assert did.old_version_builds(cpid)[0] == ["v0.103.2", "v0.103.3"]
    cv = pd.read_csv(did.REF / "card_versions.csv", dtype=str, keep_default_na=False)
    v = cv.pivot(index="card_id", columns="build_id", values="version")
    assert (v["v0.103.2"] == v["v0.103.3"]).all() and (v["v0.103.2"] != "").all()


# ------------------------------------------------------------------------------ real pages

SMOKE_DB = os.environ.get("SPIROMETRY_SMOKE_DB")


@pytest.mark.skipif(not SMOKE_DB, reason="set SPIROMETRY_SMOKE_DB to a runs.duckdb built "
                                         "from fetched pages")
def test_smoke_real_pages():
    """End to end on real columns, every tweak. Only checks that it runs; at a page or
    two nearly everything is uninformative."""
    con = duckdb.connect(SMOKE_DB, read_only=True)
    out = did.anticipation_all(con)
    assert len(out) == 43 and set(out.status) <= {"informative", "uninformative", "error"}
    assert (out.status != "error").all(), out[out.status == "error"].reason.tolist()
    wk = did.anticipation_weekly(con, "BULWARK@v0.107.1/patch")
    assert len(wk) and set(wk.block) <= {"before", "after"}
