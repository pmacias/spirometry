"""Win effects within a build (Phase 5 steps 4-5): intent-to-treat and IV. Tables only.

Does picking card X make a run more likely to win? Runs pick cards because they are going
well (or badly), so runs that picked X aren't comparable with runs that didn't. Which cards
a reward screen offers is the game's RNG, so the offer is an experiment with non-compliance:

    itt          win rate, offered X vs. not offered X (intent-to-treat)
    first_stage  how much being offered X raises picking X
    iv           effect of picking X on winning = itt / first stage (2SLS)
    naive        win on picked X, the confounded comparison, for contrast only

"Offered X anywhere in the run" is not random: runs that survive longer see more reward
screens, so they are offered more cards and also win more. Only the first K reward screens
of the run count (combat, elite, boss and event-fight rewards in floor order, then set_idx;
default K = 3). Nearly every run reaches them, and within them the offers are the RNG's.
One row per run; a run is `offered` when X was on any of its first K screens and `picked`
when it was taken on one of them. The treatment is "took X on one of the first K screens",
not "has X at some point": later rewards, shops and events don't count, so a run not offered
X early that gets it later has picked = 0, and the effect is that of getting X early.

Runs that reach fewer than K screens are left out by default (include_short_runs=False).
Every such run is a loss (it died before screen K) and had fewer screens on which to be
offered X, so counting their unreached screens as "not offered" would make "not offered"
look worse for every card: a fake positive ITT (tests/test_wins.py). Dropping them only
biases the estimate if an early offer changes the chance of reaching screen K, and then it
is the effect among runs that reach screen K. For the total effect, deaths before screen K
included, use K = 1: every run that was offered anything reached screen 1.

    con = duckdb.connect("data/runs/runs.duckdb", read_only=True)
    data = load_early(con, "ironclad", ["v0.103.2"])     # one load per (character, builds)
    itt(data, "SETUP_STRIKE"); first_stage(data, "SETUP_STRIKE")
    iv(data, "SETUP_STRIKE"); naive(data, "SETUP_STRIKE")
    run_all_cards(con, "ironclad", ["v0.103.2"])         # every card with >= 500 offered runs
    reach_share(early_runs(con, None, ["v0.103.2"]))     # share of runs reaching screen K

Model (linear probability, OLS / 2SLS with absorbed fixed effects, heteroskedasticity-robust
errors: one row per run, runs independent):

    win ~ offered | build_id^group + ascension + week^build_id
    picked ~ offered | (same)
    win ~ 1 | (same) | picked ~ offered

Population: primary runs (runs.PRIMARY_RUN_FILTER on the record runs_dedup keeps), minus
abandoned runs (no outcome) and retried runs (runs_dedup.retried: copies that differ in win,
floors reached or abandonment).
"""
import pathlib, warnings
from typing import NamedTuple

import numpy as np
import pandas as pd
import pyfixest as pf

from spirometry import did
from spirometry.runs import PRIMARY_RUN_FILTER

REF = did.REF
K_DEFAULT = 3
MIN_OFFERED = 500
WEAK_F = 10                     # first-stage F below this: weak instrument
OFFERS_VIEW = "offers_with_version"
VCOV = "hetero"
WEEK = did.WEEK


# ------------------------------------------------------------------------------ data

def _character(character):
    """'ironclad' / 'CHARACTER.IRONCLAD' -> 'CHARACTER.IRONCLAD'; None stays None."""
    if character is None:
        return None
    c = str(character).upper()
    return c if c.startswith("CHARACTER.") else f"CHARACTER.{c}"


def _builds(builds):
    return builds.split() if isinstance(builds, str) else list(builds)


# Runs of the win population and their reward screens, numbered 1, 2, ... in floor order,
# then set_idx. A list that couldn't be split into screens (set_idx NULL) is one row here;
# a run with one among its first K screens gets ambiguous_screens (its screen count is
# unknown) and the fits leave it out.
BASE_SQL = f"""
WITH r AS (
    SELECT r.run_key, r.build_id, r.branch, p.character, r.ascension,
           r.uploader_tag IS NOT NULL AS tagged, r.start_time, r.win, r.floors_reached
    FROM runs_dedup r JOIN run_players p ON p.run_hash = r.run_hash AND p.player_idx = 0
    WHERE {PRIMARY_RUN_FILTER}
      AND NOT r.was_abandoned AND NOT r.retried
      AND ($character IS NULL OR p.character = $character)
      AND list_contains($builds, r.build_id)),
s AS (
    SELECT *, row_number() OVER (PARTITION BY run_key ORDER BY floor, set_idx NULLS LAST)
              AS screen
    FROM (SELECT DISTINCT o.run_key, o.floor, o.set_idx, o.source
          FROM {OFFERS_VIEW} o SEMI JOIN r USING (run_key)
          WHERE ($character IS NULL OR o.character = $character)
            AND list_contains($builds, o.build_id)))
"""

RUNS_SQL = BASE_SQL + """
SELECT r.*, least(count(s.screen), $K)::INTEGER AS n_screens_reached,
       coalesce(bool_or(s.set_idx IS NULL AND s.screen <= $K), false) AS ambiguous_screens,
       coalesce(string_agg(s.source, '>' ORDER BY s.screen) FILTER (WHERE s.screen <= $K), '')
           AS screen_sources
FROM r LEFT JOIN s USING (run_key)
GROUP BY ALL
"""

OFFERS_SQL = BASE_SQL + f"""
SELECT o.run_key, o.card_id, count(DISTINCT s.screen)::INTEGER AS offered_screens,
       bool_or(o.picked) AS picked, min(s.screen)::INTEGER AS first_screen,
       bool_or(o.upgraded) AS upgraded_offer
FROM {OFFERS_VIEW} o
JOIN s ON o.run_key = s.run_key AND o.floor = s.floor
      AND o.set_idx IS NOT DISTINCT FROM s.set_idx
WHERE s.screen <= $K
  AND ($character IS NULL OR o.character = $character)
  AND list_contains($builds, o.build_id)
GROUP BY ALL
"""

RUN_COLS = ["run_key", "build_id", "branch", "character", "ascension", "group", "week",
            "start_time", "win", "floors_reached", "n_screens_reached", "ambiguous_screens",
            "screen_sources"]
OFFER_COLS = ["run_key", "card_id", "offered_screens", "offered", "picked", "first_screen",
              "upgraded_offer"]


class Early(NamedTuple):
    """load_early's result: `runs` (one row per run) and `offers` (one row per run and card
    offered on its first K screens, run columns not repeated), and K."""
    runs: pd.DataFrame
    offers: pd.DataFrame
    K: int


def _release_dates(ref=REF):
    b = did._csv(pathlib.Path(ref) / "builds.csv")
    return {k: pd.Timestamp(v) for k, v in zip(b.build_id, b.release_date) if v}


def _params(character, builds, K):
    return {"character": _character(character), "builds": _builds(builds), "K": int(K)}


def _runs_frame(con, character, builds, K, ref):
    r = con.execute(RUNS_SQL, _params(character, builds, K)).df()
    r["group"] = np.where(r.pop("tagged"), "tagged", "untagged")
    rel = r.build_id.map(_release_dates(ref))
    # whole weeks from the run's own build's release date (NA where builds.csv has no date)
    r["week"] = np.floor((r.start_time - rel).dt.total_seconds() / WEEK).astype("Int16")
    r["ascension"] = r.ascension.astype("Int16")
    r["win"] = r.win.astype(bool)
    for c in ("run_key", "build_id", "branch", "character", "group", "screen_sources"):
        r[c] = r[c].astype("category")
    _check_one_row_per_run(r)
    return r[RUN_COLS]


def _check_one_row_per_run(r):
    """The fits use robust (HC1) errors without clustering, which is right only with one
    row per run: refuse anything else."""
    dup = r.run_key.duplicated()
    if dup.any():
        raise ValueError(f"{int(dup.sum())} run_keys have more than one row "
                         f"(e.g. {r.run_key[dup].iloc[0]}); the fits need one row per run")


def _offers_frame(con, character, builds, K):
    o = con.execute(OFFERS_SQL, _params(character, builds, K)).df()
    o["offered"] = True
    o["picked"] = o.picked.astype(bool)
    o["upgraded_offer"] = o.upgraded_offer.astype(bool)
    o["offered_screens"] = o.offered_screens.astype("int8")
    o["first_screen"] = o.first_screen.astype("int8")
    for c in ("run_key", "card_id"):
        o[c] = o[c].astype("category")
    return o[OFFER_COLS]


def load_early(con, character, builds, K=K_DEFAULT, ref=REF):
    """The run table and the per-(run, card) offer table for one character (None = all) and
    a list of builds (or a space-separated string), in one call. The estimators take this.
    Built in DuckDB; pandas gets one row per run and one per (run, card offered on the
    first K screens), with categorical keys."""
    return Early(early_runs(con, character, builds, K, ref),
                 _offers_frame(con, character, builds, K), int(K))


def early_runs(con, character, builds, K=K_DEFAULT, ref=REF):
    """One row per run of the win population (primary, not abandoned, not retried) for the
    character (None = all) on the builds: run_key, build_id, branch, character, ascension,
    group ('tagged' when the kept record has an _sts tag), week (whole weeks from the run's
    build's release date; NA where builds.csv has none), start_time, win, floors_reached,
    n_screens_reached (reward screens in the run, capped at K), ambiguous_screens (a list
    that couldn't be split into screens is among the first K), screen_sources (sources of
    the first K screens, e.g. 'combat>combat>elite')."""
    return _runs_frame(con, character, builds, K, ref)


def early_offers(con, character, builds, K=K_DEFAULT, ref=REF):
    """One row per (run_key, card_id) for every card offered on the run's first K reward
    screens, with the run's columns (early_runs): offered_screens (how many of the K screens
    showed it), offered (always True here), picked (taken on one of those screens),
    first_screen (1..K), upgraded_offer (any offered copy upgraded). Runs whose first K
    screens hold no offer at all (no screens) have no rows; early_runs has them."""
    data = load_early(con, character, builds, K, ref)
    return data.offers.merge(data.runs, on="run_key", how="left")


def reach_share(runs, K=None):
    """Share of runs that reach screen K, per build and character: runs, reached_K,
    share_reached_K, and ambiguous (runs whose first K screens include an unsplit list).
    `runs` is early_runs' (or load_early(...).runs) table; K defaults to the largest
    n_screens_reached in it (the K it was built with, unless no run reached it)."""
    K = int(runs.n_screens_reached.max()) if K is None else K
    g = runs.assign(reached=runs.n_screens_reached >= K).groupby(
        ["build_id", "character"], observed=True)
    out = g.agg(runs=("run_key", "size"), reached_K=("reached", "sum"),
                ambiguous=("ambiguous_screens", "sum")).reset_index()
    out["share_reached_K"] = out.reached_K / out.runs
    out["K"] = K
    return out


# ------------------------------------------------------------------------------ fits

def run_frame(data, card, *, include_short_runs=False, group=None):
    """One row per run with offered / picked for `card` on the first K screens, the rows
    the fits use: runs with ambiguous_screens and rows without ascension or week dropped;
    runs that reached fewer than K screens dropped unless include_short_runs (the default
    keeps only runs that reached all K; see the module docstring); one uploader group only
    when `group` is given. offered / picked refer to the first K screens only."""
    r = data.runs
    keep = ~r.ambiguous_screens & r.ascension.notna() & r.week.notna()
    if not include_short_runs:
        keep &= r.n_screens_reached >= data.K
    if group is not None:
        keep &= r.group == group
    d = r[keep].copy()
    _check_one_row_per_run(d)
    o = data.offers[data.offers.card_id == card]
    d["offered"] = d.run_key.isin(o.run_key).astype("int8")
    d["picked"] = d.run_key.isin(o.run_key[o.picked]).astype("int8")
    d["win"] = d.win.astype("int8")
    d["asc"] = d.ascension.astype("int16")
    d["build_group"] = (d.build_id.astype(str) + "|" + d.group.astype(str)).astype("category")
    d["build_week"] = (d.build_id.astype(str) + "|" + d.week.astype(str)).astype("category")
    for c in d.columns:
        if isinstance(d[c].dtype, pd.CategoricalDtype):
            d[c] = d[c].cat.remove_unused_categories()
    return d


def _fixed_effects(d, group, pooled_groups, screen_mix):
    """build^group (build alone within one group, pooled, or when the data have one group)
    + ascension + week^build, plus the first K screens' sources when screen_mix."""
    two = group is None and not pooled_groups and d.group.nunique() > 1
    fe = ["build_group" if two else "build_id", "asc", "build_week"]
    if screen_mix:
        fe.append("screen_sources")
    return fe


def _feols(fml, d):
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=did.SINGLETON_WARNING)
        return pf.feols(fml, data=d, vcov=VCOV)


def _prepare(data, card, K, include_short_runs, group, pooled_groups, screen_mix):
    if K is not None and K != data.K:
        raise ValueError(f"data was loaded with K = {data.K}, not {K}: reload with "
                         "load_early(..., K=...)")
    d = run_frame(data, card, include_short_runs=include_short_runs, group=group)
    if d.empty:
        raise ValueError(f"{card}: no runs after the filters")
    if not d.offered.any() or d.offered.all():
        raise ValueError(f"{card}: offered on {'every' if d.offered.all() else 'no'} run")
    return d, " + ".join(_fixed_effects(d, group, pooled_groups, screen_mix))


def _counts(d, fit):
    return dict(n_runs=int(fit._N), n_singletons_dropped=len(d) - int(fit._N),
                n_offered=int(d.offered.sum()), n_picked=int(d.picked.sum()))


def _coef(fit, name):
    return float(fit.coef()[name]), float(fit.se()[name])


def itt(data, card, *, K=None, include_short_runs=False, group=None, pooled_groups=False,
        screen_mix=False):
    """Intent-to-treat: `win ~ offered | build^group + ascension + week^build` with
    heteroskedasticity-robust errors, one row per run. Returns beta (win probability, offered
    minus not offered, net of the fixed effects), se, win_rate_offered, win_rate_not_offered
    (raw), n_runs (in the fit, after pyfixest drops singleton cells; n_singletons_dropped
    counts them), n_offered, n_picked (runs that took the card on the first K screens), K,
    formula.

    K: a check that data was loaded with that K (screens are counted in DuckDB).
    include_short_runs: also keep runs that reached fewer than K screens, their unreached
      screens counted as not offered. Every such run lost and had fewer chances to be
      offered the card, so this biases the itt upward for every card; a check only. (For
      deaths before screen K caused by an early offer, use data loaded with K = 1.)
    group: 'tagged' / 'untagged', within one uploader group (build alone in the fe).
    pooled_groups: build alone, no group terms (how much the adjustment matters).
    screen_mix: add the sources of the first K screens (e.g. 'combat>elite>combat') as a
      fixed effect: elites offer rarer cards and taking an elite early is a choice."""
    d, fe = _prepare(data, card, K, include_short_runs, group, pooled_groups, screen_mix)
    fml = f"win ~ offered | {fe}"
    fit = _feols(fml, d)
    beta, se = _coef(fit, "offered")
    rates = d.groupby("offered").win.mean()
    return dict(card_id=card, beta=beta, se=se,
                win_rate_offered=float(rates.get(1, np.nan)),
                win_rate_not_offered=float(rates.get(0, np.nan)),
                **_counts(d, fit), K=data.K, formula=fml)


def first_stage(data, card, *, K=None, include_short_runs=False, group=None,
                pooled_groups=False, screen_mix=False):
    """`picked ~ offered | (itt's fixed effects)`, robust errors. picked = took the card on
    one of the first K screens (not later rewards, shops or events), so runs not offered it
    there have picked = 0 (one-sided non-compliance). Returns coef, se, F (robust Wald
    F = (coef / se)^2, one instrument), weak (F < 10), pick_rate_offered (raw share of
    offered runs that took it), counts.
    Options as in itt."""
    d, fe = _prepare(data, card, K, include_short_runs, group, pooled_groups, screen_mix)
    fml = f"picked ~ offered | {fe}"
    fit = _feols(fml, d)
    coef, se = _coef(fit, "offered")
    F = (coef / se) ** 2 if se > 0 else np.nan
    return dict(card_id=card, coef=coef, se=se, F=F, weak=bool(not F >= WEAK_F),
                pick_rate_offered=float(d.picked[d.offered == 1].mean()),
                **_counts(d, fit), K=data.K, formula=fml)


def iv(data, card, *, K=None, include_short_runs=False, group=None, pooled_groups=False,
       screen_mix=False):
    """2SLS: `win ~ 1 | fe | picked ~ offered`, robust errors. beta = effect of taking the
    card on one of the first K screens (not later rewards, shops or events) on the win
    probability, for runs that take it when offered (compliers; with one-sided
    non-compliance, the effect on those who took it). A run not offered it early can still
    get it later; that stays in the comparison (the effect of getting it early).
    Returns beta, se, first_stage_coef, first_stage_F (as first_stage), weak, counts.
    Options as in itt."""
    d, fe = _prepare(data, card, K, include_short_runs, group, pooled_groups, screen_mix)
    fml = f"win ~ 1 | {fe} | picked ~ offered"
    fit = _feols(fml, d)
    beta, se = _coef(fit, "picked")
    fs = _feols(f"picked ~ offered | {fe}", d)
    fc, fse = _coef(fs, "offered")
    F = (fc / fse) ** 2 if fse > 0 else np.nan
    return dict(card_id=card, beta=beta, se=se, first_stage_coef=fc, first_stage_F=F,
                weak=bool(not F >= WEAK_F), **_counts(d, fit), K=data.K, formula=fml)


def naive(data, card, *, K=None, include_short_runs=False, group=None, pooled_groups=False,
          screen_mix=False, among_offered=False):
    """The confounded comparison, for contrast only: `win ~ picked | fe` on all runs (runs
    that took the card on the first K screens against every other run), robust errors. With
    among_offered=True, only runs offered it (took it vs. passed on it). Options as in itt."""
    d, fe = _prepare(data, card, K, include_short_runs, group, pooled_groups, screen_mix)
    if among_offered:
        d = d[d.offered == 1]
    fml = f"win ~ picked | {fe}"
    fit = _feols(fml, d)
    beta, se = _coef(fit, "picked")
    return dict(card_id=card, beta=beta, se=se, among_offered=among_offered,
                **_counts(d, fit), K=data.K, formula=fml)


# ------------------------------------------------------------------------------ all cards

def run_all_cards(con, character, builds, *, K=K_DEFAULT, min_offered=MIN_OFFERED,
                  include_short_runs=False, group=None, pooled_groups=False,
                  screen_mix=False, data=None, ref=REF):
    """itt, first_stage, iv and naive for every card of the character's color with at least
    `min_offered` offered runs among the runs the fits use, one row per card, sorted by
    offered runs. One data load per call (or pass `data` from load_early). A card whose fit
    fails gets the reason in `error`. share_reached_K is the share of the character's runs
    on these builds that reached screen K (not ambiguous)."""
    if character is None:
        raise ValueError("run_all_cards needs a character (its cards are the candidates)")
    data = data if data is not None else load_early(con, character, builds, K, ref)
    opts = dict(include_short_runs=include_short_runs, group=group,
                pooled_groups=pooled_groups, screen_mix=screen_mix)
    color = _character(character).removeprefix("CHARACTER.").lower()
    cards = {c for c, col in did.card_colors(ref).items() if col == color}
    base = run_frame(data, None, include_short_runs=include_short_runs, group=group)
    o = data.offers[data.offers.run_key.isin(base.run_key) & data.offers.card_id.isin(cards)]
    n_off = o.groupby("card_id", observed=True).size().sort_values(ascending=False)
    ok = data.runs[~data.runs.ambiguous_screens]
    share = float((ok.n_screens_reached >= data.K).mean()) if len(ok) else np.nan
    rows = []
    for card, n in n_off[n_off >= min_offered].items():
        row = dict(card_id=card, character=_character(character), K=data.K,
                   n_offered_runs=int(n), share_reached_K=share, error="")
        try:
            a, f = itt(data, card, **opts), first_stage(data, card, **opts)
            b, c = iv(data, card, **opts), naive(data, card, **opts)
            row.update(n_runs=a["n_runs"], n_picked=a["n_picked"],
                       win_rate_offered=a["win_rate_offered"],
                       win_rate_not_offered=a["win_rate_not_offered"],
                       itt_beta=a["beta"], itt_se=a["se"],
                       fs_coef=f["coef"], fs_se=f["se"], fs_F=f["F"], weak=f["weak"],
                       pick_rate_offered=f["pick_rate_offered"],
                       iv_beta=b["beta"], iv_se=b["se"],
                       naive_beta=c["beta"], naive_se=c["se"], formula=a["formula"])
        except Exception as e:                      # report and keep going
            row["error"] = f"{type(e).__name__}: {' '.join(str(e).split())}"
        rows.append(row)
    cols = ["card_id", "character", "K", "n_runs", "n_offered_runs", "n_picked",
            "win_rate_offered", "win_rate_not_offered", "itt_beta", "itt_se", "fs_coef",
            "fs_se", "fs_F", "weak", "pick_rate_offered", "iv_beta", "iv_se", "naive_beta",
            "naive_se", "share_reached_K", "formula", "error"]
    return pd.DataFrame(rows).reindex(columns=cols)
