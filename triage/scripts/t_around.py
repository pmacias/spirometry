"""Section T (EXPLORATORY): did things that changed AROUND unchanged cards at the two major
updates (v0.103.2, v0.107.1) produce the "jump" in the placebo spread?

Proposed by Phil after reading the patch notes, with sections P to S seen. Reads the final
tables; changes no factor, number or result. Rules, definitions and what each outcome means
are in TRIAGE.md section T, written before this ran.

    python triage/scripts/t_around.py --check             # known-answer checks and the gate
    python triage/scripts/t_around.py --part 1            # recording per build (artifact check)
    python triage/scripts/t_around.py --part 2a --time    # 10 fits, runtime estimate, saves nothing
    python triage/scripts/t_around.py --part 2a           # refit on regular rewards only
    python triage/scripts/t_around.py --part 2b           # co-offer strength (competition)
    python triage/scripts/t_around.py --part 2c [--time]  # screen fixed effects
    python triage/scripts/t_around.py --part 3 [--time]   # POST HOC: enablers, beta fits, budget
    python triage/scripts/t_around.py --part 2a --analyze # tables from the saved fits only
    python triage/scripts/t_around.py --privacy           # check every t_*.csv

Fits are appended to triage/out_final/t_*_fits.csv as each window finishes, and a rerun skips
what is there: a pause or restart redoes nothing. Delete a fits file to redo it.

Run from the repository root. Output: triage/out_final/t_*.csv (TRIAGE_OUT overrides), keyed by
build, window and card. No run, screen, player or uploader ID is printed or written.
runs.duckdb is opened read-only. Colors and rarities are derived as in q_nudge.py, whose
loader, fit and likelihood this script reuses; card archetypes are read from the saved
p_archetypes.csv, so reference/raw/ is not opened.
"""
import argparse
import glob
import os
import resource
import sys
import time

import numpy as np
import pandas as pd
from scipy import optimize, stats

sys.path.insert(0, "triage/scripts")
import db  # noqa: E402
import q_nudge as q  # noqa: E402
import r_dose as r  # noqa: E402
import p_archetype as p  # noqa: E402
from spirometry import did  # noqa: E402
from spirometry.export import check_output  # noqa: E402

OUT = q.OUT
N_BOOT = q.N_BOOT
pct, robust_sd, mle, cluster_boot = q.pct, q.robust_sd, q.mle, q.cluster_boot
Store, tau_ci = r.Store, r.tau_ci
Q_TAU = {"first": (3.35, 2.95, 3.72), "second": (2.44, 2.15, 2.71)}
MAJOR = ["v0.99.1 -> v0.103.2", "v0.103.3 -> v0.107.1"]
QUIET = ["v0.98.3 -> v0.99.1", "v0.103.2 -> v0.103.3"]
PRESENT = 20                     # offers for a card id to count as present in a build
FAR = pd.Timestamp("2100-01-01")
POPULATION = ("r.n_players = 1 AND NOT r.is_custom AND NOT r.is_modded AND r.released "
              "AND NOT r.before_release AND r.neow_start")


def save(t, name):
    check_output(name, t)
    t.to_csv(f"{OUT}/{name}.csv", index=False)


def show(name, t):
    print(name, t.to_string(index=False), sep="\n", flush=True)


# ------------------------------------------------------------------------------------ part 1

def groups():
    """Labels to aggregate over: every build with a branch (whole build), and for each stable
    boundary the two blocks a fit would use (older build whole, newer build weeks 0-3)."""
    b = did._csv("reference/builds.csv")
    b = b[(b.branch != "") & (b.release_date != "")].copy()
    b["date"] = pd.to_datetime(b.release_date)
    b = b.sort_values(["date", "build_id"], kind="stable")
    rows = [dict(label=x.build_id, kind="build", branch=x.branch, build_id=x.build_id,
                 release=x.date, t_lo=pd.Timestamp("1900-01-01"), t_hi=FAR) for x in b.itertuples()]
    for old, new in zip(q.STABLE, q.STABLE[1:]):
        bd = f"{old} -> {new}"
        rows.append(dict(label=f"{bd} | before", kind="block", branch="stable", build_id=old,
                         release=q.release(old), t_lo=pd.Timestamp("1900-01-01"), t_hi=FAR))
        rows.append(dict(label=f"{bd} | after", kind="block", branch="stable", build_id=new,
                         release=q.release(new), t_lo=pd.Timestamp("1900-01-01"),
                         t_hi=q.release(new) + pd.Timedelta(seconds=4 * did.WEEK)))
    return pd.DataFrame(rows)


JOIN_O = ("FROM primary_offers o JOIN grp g ON o.build_id = g.build_id "
          "AND o.start_time >= g.t_lo AND o.start_time < g.t_hi")
SCREEN_SQL = f"""
WITH s AS (
  SELECT g.label, o.run_key, o.floor, o.source, o.set_idx, any_value(o.list_len) AS list_len,
         count(*) AS n_cards, sum(o.picked::INT) AS n_picked
  {JOIN_O} GROUP BY ALL),
l AS (
  SELECT label, run_key, floor, source, count(*) AS n_screens, bool_or(set_idx IS NULL) AS unsplit,
         any_value(list_len) AS list_len, sum(n_cards) AS n_cards, sum(n_picked) AS n_picked
  FROM s GROUP BY ALL),
a AS (
  SELECT label, source, count(*) AS screens,
         count(*) FILTER (n_picked >= 1) AS screens_pick,
         count(*) FILTER (n_picked > 1) AS screens_multi_pick,
         count(*) FILTER (n_cards = 3) AS screens_3, count(*) FILTER (n_cards = 4) AS screens_4,
         sum(n_cards) AS cards_in_screens
  FROM s WHERE set_idx IS NOT NULL GROUP BY ALL),
b AS (
  SELECT label, source, count(*) AS lists, count(*) FILTER (unsplit) AS lists_unsplit,
         count(*) FILTER (NOT unsplit AND n_screens > 1) AS lists_multi_screen,
         count(*) FILTER (list_len = 3 AND NOT unsplit) AS lists_one_screen_of_3,
         count(*) FILTER (n_picked = 0) AS lists_no_pick,
         sum(n_cards) AS offers, sum(n_picked) AS picks, count(DISTINCT run_key) AS runs
  FROM l GROUP BY ALL)
SELECT * FROM b LEFT JOIN a USING (label, source)
"""
ACT_SQL = f"""
SELECT g.label, o.act, count(*) AS offers, count(DISTINCT o.run_key) AS runs
{JOIN_O} GROUP BY ALL
"""
RUNS_SQL = f"SELECT g.label, count(DISTINCT o.run_key) AS runs {JOIN_O} GROUP BY ALL"
SOURCE_SQL = f"""
SELECT g.label,
       CASE WHEN o.source = 'ancient' AND o.room_model_id = 'EVENT.NEOW' THEN 'neow'
            WHEN o.source = 'ancient' THEN 'ancient_other' ELSE o.source END AS src,
       count(*) AS offers, sum(o.picked::INT) AS picks,
       count(DISTINCT hash(o.run_key, o.floor)) AS lists, count(DISTINCT o.run_key) AS runs
FROM card_offers o JOIN runs_dedup r USING (run_hash)
JOIN grp g ON r.build_id = g.build_id AND r.start_time >= g.t_lo AND r.start_time < g.t_hi
WHERE {POPULATION} AND NOT o.is_mod_card GROUP BY ALL
"""
CARD_SQL = """
SELECT build_id, character, card_id, count(*) AS n, sum(picked::INT) AS picks
FROM primary_offers GROUP BY ALL
"""


def null_shares(con, view, join, where, skip):
    """Share of rows where each column of `view` is null (or an empty list), per label."""
    cols = con.execute(f"DESCRIBE {view}").df()
    parts = []
    for c, t in zip(cols.column_name, cols.column_type):
        if c in skip:
            continue
        test = f"(x.{c} IS NULL OR len(x.{c}) = 0)" if t.endswith("[]") else f"x.{c} IS NULL"
        parts.append(f'avg(({test})::INT) AS "{c}"')
    d = con.execute(f"SELECT g.label, count(*) AS n_rows, {', '.join(parts)} FROM {view} x {join} "
                    f"{where} GROUP BY ALL").df()
    return d.melt(["label", "n_rows"], var_name="column", value_name="null_share").assign(table=view)


def part1(con):
    G = groups()
    con.register("grp", G[["label", "build_id", "t_lo", "t_hi"]])
    t0 = time.time()
    S = con.execute(SCREEN_SQL).df()
    A = con.execute(ACT_SQL).df()
    R = con.execute(RUNS_SQL).df().set_index("label").runs
    print(f"  reward screens, acts: {time.time() - t0:.0f} s", flush=True)
    t0 = time.time()
    SRC = con.execute(SOURCE_SQL).df()
    print(f"  sources: {time.time() - t0:.0f} s", flush=True)
    t0 = time.time()
    jr = "JOIN grp g ON x.build_id = g.build_id AND x.start_time >= g.t_lo AND x.start_time < g.t_hi"
    ids = {"run_hash", "run_key", "source_page", "source_line", "player_hash", "seed",
           "record_digest", "uploader_hash", "start_time", "build_id"}
    N = pd.concat([
        null_shares(con, "runs_dedup", jr, "WHERE " + POPULATION.replace("r.", "x."), ids),
        null_shares(con, "primary_offers", jr, "", ids)], ignore_index=True)
    SV = con.execute(f"""SELECT g.label, x.schema_version, count(*) AS runs FROM runs_dedup x {jr}
                         WHERE {POPULATION.replace('r.', 'x.')} GROUP BY ALL""").df()
    C = con.execute(CARD_SQL).df()
    print(f"  null shares, schema, card ids: {time.time() - t0:.0f} s", flush=True)

    # ---- one row per label
    tot = S.groupby("label").sum(numeric_only=True)
    M = pd.DataFrame(index=G.label)
    M["runs"] = R
    sv = SV.pivot_table(index="label", columns="schema_version", values="runs", fill_value=0)
    M["schema_versions"] = [" ".join(f"{int(v)}:{n / row.sum():.4f}" for v, n in row.items() if n)
                            if lab in sv.index else "" for lab, row in sv.reindex(M.index).fillna(0).iterrows()]
    M["schema_version_main"] = sv.idxmax(axis=1).reindex(M.index)
    M["share_screens_with_pick"] = tot.screens_pick / tot.screens
    for src in ("combat", "elite", "boss", "event_combat"):
        s = S[S.source == src].set_index("label")
        M[f"share_screens_with_pick_{src}"] = s.screens_pick / s.screens
        M[f"share_of_reward_offers_{src}"] = s.offers / tot.offers
    M["share_screens_multi_pick"] = tot.screens_multi_pick / tot.screens
    M["cards_per_screen"] = tot.cards_in_screens / tot.screens
    M["share_screens_3_cards"] = tot.screens_3 / tot.screens
    M["share_screens_4_cards"] = tot.screens_4 / tot.screens
    M["share_lists_unsplit"] = tot.lists_unsplit / tot.lists
    M["share_lists_multi_screen"] = tot.lists_multi_screen / tot.lists
    M["share_lists_one_screen_of_3"] = tot.lists_one_screen_of_3 / tot.lists
    M["share_lists_no_pick"] = tot.lists_no_pick / tot.lists
    M["picks_per_offer"] = tot.picks / tot.offers
    M["reward_offers_per_run"] = tot.offers / M.runs
    M["reward_lists_per_run"] = tot.lists / M.runs
    for act in (1, 2, 3):
        a = A[A.act == act].set_index("label")
        M[f"offers_per_run_act{act}"] = a.offers / a.runs       # runs with an offer in the act
        M[f"share_runs_with_offer_act{act}"] = a.runs / M.runs
    src_tot = SRC.groupby("label").offers.sum()
    src_runs = SRC.groupby("label").runs.max()
    for s_, g in SRC.groupby("src"):
        g = g.set_index("label")
        M[f"source_share_{s_}"] = (g.offers / src_tot).reindex(M.index).fillna(0)
        M[f"source_offers_per_run_{s_}"] = (g.offers / src_runs).reindex(M.index).fillna(0)
        M[f"source_pick_share_{s_}"] = (g.picks / g.offers).reindex(M.index)
    M = G.set_index("label")[["kind", "branch", "build_id", "release"]].join(M).reset_index()
    M["release"] = M.release.dt.date.astype(str)

    # ---- steps at stable boundaries, on the fits' blocks
    blk = M[M.kind == "block"].set_index("label")
    num = [c for c in blk.columns if c not in ("kind", "branch", "build_id", "release",
                                               "schema_versions")]
    steps = []
    for old, new in zip(q.STABLE, q.STABLE[1:]):
        bd = f"{old} -> {new}"
        for m in num:
            b_, a_ = blk.loc[f"{bd} | before", m], blk.loc[f"{bd} | after", m]
            steps.append(dict(metric=m, boundary=bd, before=b_, after=a_, delta=a_ - b_))
    ST = pd.DataFrame(steps)
    quiet = ST[ST.boundary.isin(QUIET)].groupby("metric").delta.agg(lambda x: x.abs().max())
    ST["largest_quiet_delta"] = ST.metric.map(quiet)
    ST["flag"] = ST.boundary.isin(MAJOR) & (ST.delta.abs() > ST.largest_quiet_delta) & (ST.delta != 0)

    # ---- null shares: columns that move at all
    N["kind"] = N.label.map(G.set_index("label").kind)
    rng = N.groupby(["table", "column"]).null_share.agg(lambda x: x.max() - x.min())
    moving = rng[rng > 1e-4].reset_index()[["table", "column"]]
    NV = N.merge(moving, on=["table", "column"])
    n_const = int((rng <= 1e-4).sum())

    # ---- card ids
    order = G[G.kind == "build"].reset_index(drop=True)
    C = C[C.build_id.isin(order.build_id)].copy()
    C["color"] = C.character.map(db.CHARS)
    C = C.dropna(subset=["color"])
    C["share_of_character"] = C.n / C.groupby(["build_id", "character"]).n.transform("sum")
    C["present"] = C.n >= PRESENT
    loaded = did.card_colors()
    cc = did._csv("reference/card_changes.csv").drop_duplicates("card_id").set_index("card_id")
    ev = []
    for branch, ob in order.groupby("branch"):
        blds = list(ob.build_id)
        pres = {b_: C[(C.build_id == b_) & C.present] for b_ in blds}
        for prev, cur in zip(blds, blds[1:]):
            a_, b_ = pres[prev], pres[cur]
            # compare within the characters both builds have enough data for
            ka, kb = set(zip(a_.color, a_.card_id)), set(zip(b_.color, b_.card_id))
            for kind, keys, src, ref_b in (("new", kb - ka, b_, cur), ("vanished", ka - kb, a_, prev)):
                for col, card in sorted(keys):
                    row = src[(src.color == col) & (src.card_id == card)].iloc[0]
                    other = C[(C.build_id == (prev if kind == "new" else cur)) & (C.color == col)
                              & (C.card_id == card)]
                    ev.append(dict(branch=branch, build_before=prev, build=cur, kind=kind,
                                   character=col, card_id=card, offers_where_present=int(row.n),
                                   share_of_character=row.share_of_character,
                                   offers_on_other_side=int(other.n.sum()),
                                   color_on_file=cc.color.get(card, ""),
                                   loaded_by_fits=loaded.get(card) == col,
                                   own_color_card=row.share_of_character > 0 and
                                   C[C.card_id == card].groupby("color").n.sum().idxmax() == col))
    EV = pd.DataFrame(ev)
    # candidate renames: a vanished id next to a new id, same character, same build
    pr = []
    if len(EV):
        own = EV[EV.own_color_card]
        for (branch, b_, col), g in own.groupby(["branch", "build", "character"]):
            for v in g[g.kind == "vanished"].itertuples():
                for n_ in g[g.kind == "new"].itertuples():
                    pr.append(dict(branch=branch, build=b_, character=col, vanished_id=v.card_id,
                                   new_id=n_.card_id, vanished_share=v.share_of_character,
                                   new_share=n_.share_of_character,
                                   vanished_loaded_by_fits=v.loaded_by_fits,
                                   new_loaded_by_fits=n_.loaded_by_fits))
    PR = pd.DataFrame(pr)

    # ---- offer tier per stable build (rarity as the offers show it)
    T = C[C.build_id.isin(q.STABLE)].copy()
    main = T.groupby(["card_id", "color"]).n.sum().reset_index().sort_values("n").drop_duplicates(
        "card_id", keep="last").set_index("card_id").color
    T = T[(T.color == T.card_id.map(main)).to_numpy()]
    T = T[T.card_id.isin(loaded) | T.card_id.isin(cc.index)]       # the game's cards on file
    T = T[T.card_id.map(lambda c: loaded.get(c, main.get(c)) == main.get(c))]
    T["ratio"] = T.n / T.groupby(["build_id", "color"]).n.transform("max")
    T["tier"] = np.select([T.ratio >= 0.6, T.ratio >= 0.25], ["Common", "Uncommon"], "Rare")
    T = T[T.n >= 200]
    W = T.pivot_table(index=["color", "card_id"], columns="build_id", values="tier", aggfunc="first")
    Wr = T.pivot_table(index=["color", "card_id"], columns="build_id", values="ratio")
    W = W.reindex(columns=[b_ for b_ in q.STABLE if b_ in W.columns])
    today = pd.Series(q.RARITY)
    rows = []
    for (col, card), row in W.iterrows():
        tiers = row.dropna()
        win = {w: (row.get(a_), row.get(b_)) for w, (a_, b_) in q.REAL.items()}
        rows.append(dict(
            character=col, card_id=card, rarity_today=today.get(card, ""),
            rarity_on_file=cc.rarity.get(card, ""),
            **{f"tier_{b_}": row.get(b_) for b_ in W.columns},
            **{f"ratio_{b_}": Wr.loc[(col, card)].get(b_) for b_ in W.columns},
            tier_changes=tiers.nunique() > 1,
            first_window_differs=win["first"][0] != win["first"][1]
            and not pd.isna(win["first"][0]) and not pd.isna(win["first"][1]),
            second_window_differs=win["second"][0] != win["second"][1]
            and not pd.isna(win["second"][0]) and not pd.isna(win["second"][1]),
            differs_from_today_first=any(t_ != today.get(card) for t_ in win["first"] if not pd.isna(t_)),
            differs_from_today_second=any(t_ != today.get(card) for t_ in win["second"] if not pd.isna(t_)),
            rarity_change_on_file=" ".join(sorted(
                e.event_id for e in CE_RARITY.itertuples() if e.card_id == card))))
    TI = pd.DataFrame(rows)
    return M, ST, NV, n_const, EV, PR, TI


def under_offered(TI, pairs):
    """POST HOC, added after reading the tier table: cards offered well below their rarity's
    typical rate (under 0.9 x the rarity's median offer ratio on v0.99.1), their ratio to
    that median on each stable build, and their placebo spread against the other cards'."""
    on_file = set(CE_RARITY.card_id)
    t = TI[~TI.card_id.isin(on_file) & TI.rarity_today.isin(["Common", "Uncommon", "Rare"])].copy()
    builds = [c[6:] for c in t.columns if c.startswith("ratio_")]
    for b_ in builds:
        t[f"rel_{b_}"] = t[f"ratio_{b_}"] / t.groupby("rarity_today")[f"ratio_{b_}"].transform("median")
    t["under_offered"] = t["rel_v0.99.1"] < 0.9
    cards = t[t.under_offered][["character", "card_id", "rarity_today"] + [f"rel_{b_}" for b_ in builds]]
    rows = [dict(group="under-offered cards", stat="mean ratio to the rarity's median",
                 n=int(t.under_offered.sum()), **{b_: t[f"rel_{b_}"][t.under_offered].mean() for b_ in builds}),
            dict(group="other cards", stat="mean ratio to the rarity's median",
                 n=int((~t.under_offered).sum()), **{b_: t[f"rel_{b_}"][~t.under_offered].mean() for b_ in builds})]
    low = set(cards.card_id)
    for (patch, flag), g in pairs.assign(low=pairs.pseudo_card.isin(low)).groupby(["patch", "low"]):
        rows.append(dict(group="under-offered cards" if flag else "other cards",
                         stat=f"placebo pairs, {patch} patch", n=len(g), robust_sd_z=robust_sd(g.z),
                         mean_z=g.z.mean(), tau_pp=mle(100 * g.beta, 100 * g.se)[0]))
    return cards, pd.DataFrame(rows)


def _ce_rarity():
    ce = did._csv("reference/change_events.csv")
    return ce[ce.change_kind.str.contains("rarity_change|added|removed")]


CE_RARITY = _ce_rarity()


def placed_from_offers(con):
    """Character and offer tier, before the change, of the cards the change tables hold
    without a color (Grapple, Follow Through, Rip and Tear)."""
    n = con.execute("""SELECT build_id, character, card_id, count(*) AS n FROM primary_offers
                       WHERE build_id IN ('v0.99.1', 'v0.103.2', 'v0.103.3', 'v0.107.1')
                       GROUP BY ALL""").df()
    n["color"] = n.character.map(db.CHARS)
    n = n.dropna(subset=["color"])
    n["ratio"] = n.n / n.groupby(["build_id", "color"]).n.transform("max")
    n["share"] = n.n / n.groupby(["build_id", "card_id"]).n.transform("sum")
    out = n[n.card_id.isin(["GRAPPLE", "FOLLOW_THROUGH", "RIP_AND_TEAR", "SCARE", "NOT_YET",
                            "ACROBATICS", "COLOSSUS", "PREDATOR"])].copy()
    out["tier"] = np.select([out.ratio >= 0.6, out.ratio >= 0.25], ["Common", "Uncommon"], "Rare")
    return out.sort_values(["card_id", "build_id", "n"])[
        ["card_id", "build_id", "color", "n", "share", "ratio", "tier"]]


# -------------------------------------------------------------------------- part 2: shared

def windows(pairs):
    return pairs.groupby(["color", "before_builds", "after_builds"], sort=False)


def load_h3(con, color, before, after, extra=False):
    df = did.load_block_data(con, color, before, after, extra_cols=extra)
    return df[(df.block != "after") | (df.week <= 3)]


def tau_table(f, variants, label):
    """tau per patch for each fit variant next to the saved fits of the same pairs."""
    rows = []
    for scope, d in (("all pairs fit", f), (">= 51 offers of the pseudo card in each block",
                                           f[(f.pseudo_offers_before >= 51) & (f.pseudo_offers_after >= 51)])):
        for v in variants:
            for patch, g in d[d.variant == v].groupby("patch"):
                g = g.reset_index(drop=True)
                b1, s1 = 100 * g.beta.to_numpy(), 100 * g.se.to_numpy()
                b0, s0 = 100 * g.beta_saved.to_numpy(), 100 * g.se_saved.to_numpy()
                t1, t0 = mle(b1, s1)[0], mle(b0, s0)[0]
                bt = cluster_boot(g.pseudo_card.to_numpy(), lambda i: (
                    mle(b1[i], s1[i])[0], mle(b0[i], s0[i])[0]))
                ratio = bt[:, 0] / np.where(bt[:, 1] > 0, bt[:, 1], np.nan)
                qt, qlo, qhi = Q_TAU[patch]
                lo, hi = pct(bt[:, 0])
                rows.append(dict(
                    part=label, scope=scope, variant=v, patch=patch, n_pairs=len(g),
                    n_cards=g.pseudo_card.nunique(), tau=t1, tau_lo=lo, tau_hi=hi, tau_saved=t0,
                    tau_saved_lo=pct(bt[:, 1])[0], tau_saved_hi=pct(bt[:, 1])[1],
                    ratio_to_saved=t1 / t0, ratio_lo=pct(ratio)[0], ratio_hi=pct(ratio)[1],
                    q_tau=qt, ratio_to_q=t1 / qt, intervals_overlap_q=bool(hi >= qlo and lo <= qhi),
                    robust_sd_z=robust_sd(g.z), robust_sd_z_saved=robust_sd(g.z_saved),
                    median_se_pp=float(np.median(s1)), median_se_saved_pp=float(np.median(s0)),
                    corr_beta=np.corrcoef(g.beta, g.beta_saved)[0, 1],
                    share_rows_kept=g.n_rows.sum() / g.n_rows_all.sum(),
                    singleton_share=g.n_dropped.sum() / g.n_rows.sum()))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------ part 2a

A_COLS = ["window", "patch", "color", "fit_on", "pseudo_card", "card_patch_id", "variant", "beta",
          "se", "z", "n_rows", "n_rows_all", "n_offers", "n_dropped", "pseudo_offers_before",
          "pseudo_offers_after", "beta_saved", "se_saved", "z_saved", "error"]
A_INFO = ["window", "patch", "color", "block", "offers", "share_event_fight", "share_not_one_screen_of_3",
          "share_4_card_screen", "share_multi_screen", "share_unsplit"]
FILTERS = {
    "a1 no event fights": lambda d: d[~d.event_fight],
    "a2 one screen of 3": lambda d: d[~d.event_fight & (d.list_len == 3) & d.set_idx.notna()],
}


def fit_plain(df, key, pseudo, extra_fe=None, **kw):
    """q.fit's model (placebo_fit's), optionally with the block/act/ascension terms replaced
    by a screen fixed effect; also the rows used and the singleton drop."""
    d, _ = did._subset(df, key, pseudo=pseudo, **kw)
    fe = did._fixed_effects(d, None, False)
    if extra_fe:
        fe = [t for t in fe if t.startswith("card_id")] + list(extra_fe)
    f = did._feols("picked ~ treat_post | " + " + ".join(fe), d)
    t = d[d.is_treated]
    return dict(beta=float(f.coef()["treat_post"]), se=float(f.se()["treat_post"]),
                n_rows=len(d), n_offers=int(f._N), n_dropped=len(d) - int(f._N),
                pseudo_offers_before=int((~t.after).sum()), pseudo_offers_after=int(t.after.sum()))


def run_fits(con, pairs, store, variants, cols, time_only=False, extra=False, info=None, subset=None):
    """variants: name -> (filter or None, extra fixed effects). One chunk per window."""
    todo = pairs if subset is None else pairs[subset]
    for (color, before, after), g in windows(todo):
        w = f"{color} {before} -> {after}"
        if w in store.done and not time_only:
            continue
        t0 = time.time()
        df = load_h3(con, color, before, after, extra=extra)
        t_load = time.time() - t0
        if info is not None and not time_only and w not in info.done:
            info.add(w, [dict(
                window=w, patch=g.patch.iloc[0], color=color, block=blk, offers=len(d),
                share_event_fight=d.event_fight.mean(),
                share_not_one_screen_of_3=1 - ((d.list_len == 3) & d.set_idx.notna() & ~d.event_fight).mean(),
                share_4_card_screen=((d.list_len % 4 == 0) & (d.list_len % 3 != 0)).mean(),
                share_multi_screen=(d.set_idx.notna() & (d.list_len >= 6)).mean(),
                share_unsplit=d.set_idx.isna().mean())
                for blk, d in df.groupby("block", observed=True)])
        rows = []
        dfs = {v: (df if flt is None else flt(df)) for v, (flt, _) in variants.items()}
        for x in (g.head(10) if time_only else g).itertuples():
            up = True if x.fit_on == "upgraded offers" else None
            for v, (_, fe) in variants.items():
                row = dict(window=w, patch=x.patch, color=color, fit_on=x.fit_on,
                           pseudo_card=x.pseudo_card, card_patch_id=x.card_patch_id, variant=v,
                           beta_saved=x.beta, se_saved=x.se, z_saved=x.z, error="")
                try:
                    row.update(fit_plain(dfs[v], x.card_patch_id, x.pseudo_card, fe, upgraded=up))
                    row["z"] = row["beta"] / row["se"]
                    row["n_rows_all"] = x.n_offers          # the saved fit's offers
                except Exception as e:
                    row["error"] = f"{type(e).__name__}: {e}"[:200]
                rows.append(row)
        if time_only:
            t = (time.time() - t0 - t_load) / max(len(rows), 1)
            n = len(todo) * len(variants)
            print(f"timing ({w}, {len(df):,} offers): load {t_load:.0f} s, {t:.2f} s per fit; "
                  f"{n} fits and 9 loads: about {(n * t + 9 * t_load) / 60:.0f} min", flush=True)
            return
        store.add(w, rows)
        print(f"  {w}: {len(rows)} fits, {time.time() - t0:.0f} s", flush=True)


def gate(con, pairs):
    """With no filter, the extra-column loader and fit_plain return the saved z."""
    worst = 0.0
    picks = [pairs[(pairs.patch == "first") & (pairs.color == "silent")].iloc[0],
             pairs[(pairs.patch == "second") & (pairs.color == "ironclad")].iloc[0],
             pairs[pairs.fit_on == "upgraded offers"].iloc[0]]
    for x in picks:
        df = load_h3(con, x.color, x.before_builds, x.after_builds, extra=True)
        up = True if x.fit_on == "upgraded offers" else None
        ids = x.card_patch_ids.split()
        z = np.mean([(lambda f: f["beta"] / f["se"])(fit_plain(df, k, x.pseudo_card, upgraded=up))
                     for k in ids])
        worst = max(worst, abs(z - x.z))
        print(f"  {x.color} {x.patch} {x.pseudo_card} ({x.fit_on}, {len(ids)} tweaks): saved z "
              f"{x.z:+.5f}, refit {z:+.5f}", flush=True)
    if worst > 1e-4:
        raise SystemExit(f"gate failed: |dz| {worst:.1e} > 1e-4")
    print(f"gate passed: largest |dz| {worst:.1e}")


# ------------------------------------------------------------------------------------ part 2b

COMP_SQL = """
SELECT o.run_key || '|' || o.floor || '|' || coalesce(o.set_idx::VARCHAR, 'list') AS screen_id,
       o.card_id, o.build_id, o.picked, o.upgraded, o.start_time
FROM primary_offers o
WHERE o.character = ? AND list_contains(?, o.build_id) AND o.ascension IS NOT NULL
"""
FIRST_WINDOW_RARITY = {"PREDATOR": "Uncommon"}      # today Common; rarity changed at v0.107.1
POOL_CHANGED = {("first", "ironclad", "Rare"), ("first", "ironclad", "Uncommon"),
                ("first", "silent", "Common"), ("first", "silent", "Uncommon"),
                ("second", "silent", "Common"), ("second", "silent", "Uncommon")}


def window_rarity(patch, card):
    if patch == "first" and card in FIRST_WINDOW_RARITY:
        return FIRST_WINDOW_RARITY[card]
    return q.RARITY.get(card, "none")


def part2b(con, pairs):
    rows = []
    for (color, before, after), g in windows(pairs):
        t0 = time.time()
        bb, ab = before.split(), after.split()
        d = con.execute(COMP_SQL, [did._character(color), bb + ab]).df()
        d["after"] = d.build_id.isin(ab)
        wk = np.floor((d.start_time - did.release_date(ab[0])).dt.total_seconds() / did.WEEK)
        d = d[~d.after | (wk <= 3)].drop(columns=["start_time", "build_id"])
        d["screen"] = pd.factorize(d.screen_id)[0]
        d = d.drop(columns="screen_id")
        n = d.groupby(["card_id", "after"]).picked.agg(["size", "mean"]).unstack("after")
        nb, rb = n[("size", False)].fillna(0), n[("mean", False)]
        na, ra = n[("size", True)].fillna(0), n[("mean", True)]
        strength = rb.where(nb >= q.MIN_OFFERS)
        flagged = strength.isna() & (na >= q.MIN_OFFERS)
        strength = strength.fillna(ra.where(flagged))
        d["s"] = d.card_id.map(strength).to_numpy()
        d["s_nf"] = d.card_id.map(strength.where(~flagged)).to_numpy()
        for col in ("s", "s_nf"):
            ok = d[col].notna()
            d[f"{col}_sum"] = d[col].fillna(0).groupby(d.screen).transform("sum")
            d[f"{col}_n"] = ok.groupby(d.screen).transform("sum")
        d["size"] = d.groupby("screen").card_id.transform("size")
        for x in g.itertuples():
            m = d.card_id == x.pseudo_card
            if x.fit_on == "upgraded offers":
                m &= d.upgraded
            t = d[m]
            row = dict(color=color, before_builds=before, after_builds=after, patch=x.patch,
                       fit_on=x.fit_on, pseudo_card=x.pseudo_card, beta_pp=100 * x.beta,
                       se_pp=100 * x.se, z=x.z, rarity_window=window_rarity(x.patch, x.pseudo_card),
                       own_rate_before=float(rb.get(x.pseudo_card, np.nan)))
            for blk, tt in (("before", t[~t.after]), ("after", t[t.after])):
                row[f"n_screens_{blk}"] = len(tt)
                row[f"mean_other_cards_{blk}"] = (tt["size"] - 1).mean()
                for col, name in (("s", "comp"), ("s_nf", "comp_noflag")):
                    own = tt[col].fillna(0)
                    num = (tt[f"{col}_sum"] - own).sum()
                    den = (tt[f"{col}_n"] - tt[col].notna()).sum()
                    row[f"{name}_{blk}"] = 100 * num / den if den else np.nan
                row[f"share_other_rows_flagged_{blk}"] = 1 - (
                    (tt["s_nf_n"] - tt["s_nf"].notna()).sum() / max((tt["s_n"] - tt["s"].notna()).sum(), 1))
            rows.append(row)
        print(f"  {color} {before} -> {after}: {len(d):,} offers, {int(flagged.sum())} cards take "
              f"their after-block rate, {time.time() - t0:.0f} s", flush=True)
    C = pd.DataFrame(rows)
    C["delta_comp"] = C.comp_after - C.comp_before
    C["delta_comp_noflag"] = C.comp_noflag_after - C.comp_noflag_before
    C["pool_changed"] = [(p_, c_, r_) in POOL_CHANGED for p_, c_, r_ in
                         zip(C.patch, C.color, C.rarity_window)]
    return C


def spearman_cards(d, x, y, n=N_BOOT):
    d = d.dropna(subset=[x, y]).reset_index(drop=True)
    if len(d) < 8:
        return dict(n_pairs=len(d))
    a, b = d[x].to_numpy(), d[y].to_numpy()
    bt = cluster_boot(d.pseudo_card.to_numpy(), lambda i: stats.spearmanr(a[i], b[i]).statistic, n=n)
    slope, icpt, rr, _, _ = stats.linregress(b, a)
    return dict(n_pairs=len(d), n_cards=d.pseudo_card.nunique(),
                spearman=stats.spearmanr(a, b).statistic, lo=pct(bt)[0], hi=pct(bt)[1],
                slope_pp_per_pp=slope, r2=rr ** 2, sd_x=a.std(ddof=1), sd_delta=b.std(ddof=1))


def part2b_tests(C):
    C = C.copy()
    cw = C.color + " " + C.patch
    grp = cw + " " + C.rarity_window
    for col in ("beta_pp", "delta_comp", "delta_comp_noflag"):
        C[f"{col}_cw"] = C[col] - C.groupby(cw)[col].transform("mean")
        C[f"{col}_grp"] = C[col] - C.groupby(grp)[col].transform("mean")
    rows = []

    def add(test, scope, d, x, y, rule=False):
        for patch, g in d.groupby("patch"):
            res = spearman_cards(g, x, y)
            if rule and "spearman" in res:
                res["outcome"] = ("stronger competitors lower the pick rate (interval below 0)"
                                  if res["hi"] < 0 else "not shown")
            rows.append(dict(test=test, scope=scope, patch=patch, **res))

    add("declared [rule]", "all pairs", C, "beta_pp", "delta_comp", rule=True)
    add("deviations from the character-window mean", "all pairs", C, "beta_pp_cw", "delta_comp_cw")
    add("declared, flagged competitors left out", "all pairs", C, "beta_pp", "delta_comp_noflag")
    ao = C[C.fit_on == "all offers"]
    add("declared", "all-offers pairs", ao, "beta_pp", "delta_comp")
    add("deviations from the character-window mean", "all-offers pairs", ao, "beta_pp_cw", "delta_comp_cw")
    for flag, name in ((True, "character x rarity groups whose pool changed"),
                       (False, "groups whose pool did not change")):
        d = C[C.pool_changed == flag]
        add("deviations from the group mean", name, d, "beta_pp_grp", "delta_comp_grp")
        add("declared (raw values)", name, d, "beta_pp", "delta_comp")
    # size: how much the competition measure moves, against how much it differs between cards
    size = []
    for (patch, flag), g in C.groupby(["patch", "pool_changed"]):
        size.append(dict(patch=patch, pool_changed=flag, n_pairs=len(g),
                         mean_comp_before=g.comp_before.mean(), sd_comp_before=g.comp_before.std(),
                         mean_delta_comp=g.delta_comp.mean(), sd_delta_comp=g.delta_comp.std(),
                         sd_delta_comp_within_cw=g.delta_comp_cw.std(),
                         corr_comp_before_after=np.corrcoef(g.comp_before, g.comp_after)[0, 1],
                         sd_beta_pp=g.beta_pp.std(), robust_sd_z=robust_sd(g.z)))
    by = C.groupby(["patch", "color", "rarity_window", "pool_changed"]).agg(
        n_pairs=("z", "size"), mean_delta_comp=("delta_comp", "mean"),
        sd_delta_comp=("delta_comp", "std"), mean_beta_pp=("beta_pp", "mean"),
        robust_sd_z=("z", robust_sd)).reset_index()
    return pd.DataFrame(rows), pd.DataFrame(size), by


# ------------------------------------------------------------------------------------ part 2c

def sim_screens(n_runs=6000, own=0.0, rival=0.0, seed=0):
    """Simulated reward screens for --check. Cards 0..11 are fit cards (0 the pseudo card),
    card 99 a rival outside the fit that shares more screens with card 0 than with the rest.
    Logit choice with a skip option. own: card 0's utility shift after; rival: card 99's."""
    rng = np.random.default_rng(seed)
    rows = []
    for run in range(n_runs):
        after = run % 2
        for scr in range(6):
            if rng.random() < 0.5:
                cards = [0, 99, int(rng.integers(1, 12))]
            else:
                cards = list(rng.choice(np.arange(1, 12), 3, replace=False))
                if rng.random() < 0.1:
                    cards[0] = 99
            u = np.array([(own * after if c == 0 else rival * after if c == 99 else 0.0)
                          + 0.03 * (c % 5) for c in cards] + [0.4])
            pr = np.exp(u) / np.exp(u).sum()
            k = rng.choice(4, p=pr)
            for j, c in enumerate(cards):
                rows.append((run, f"{run}|{scr}", c, after, int(j == k)))
    d = pd.DataFrame(rows, columns=["run_key", "screen_id", "card", "after", "picked"])
    d = d[d.card != 99].copy()
    d["treat_post"] = ((d.card == 0) & (d.after == 1)).astype(int)
    return d


def check():
    import pyfixest as pf
    q.check_mle()
    out = {}
    for name, kw in (("own shift", dict(own=0.6)), ("rival shift", dict(rival=1.2))):
        d = sim_screens(**kw)
        std = pf.feols("picked ~ treat_post | card + after", d, vcov={"CRV1": "run_key"})
        fe = pf.feols("picked ~ treat_post | card + screen_id", d, vcov={"CRV1": "run_key"})
        b0, b1 = float(std.coef()["treat_post"]), float(fe.coef()["treat_post"])
        out[name] = b1 / b0
        print(f"  simulated screens, {name}: standard beta {100 * b0:+.2f} pp, screen FE "
              f"{100 * b1:+.2f} pp, ratio {b1 / b0:.2f}")
    assert out["own shift"] > 1 and out["rival shift"] < 0.5, out
    # mle_x: an intercept-only design returns q.mle; a planted group mean is absorbed
    rng = np.random.default_rng(3)
    s = rng.uniform(0.5, 1.5, 600)
    grp = rng.integers(0, 3, 600)
    b = np.array([4.0, 0.0, -4.0])[grp] + rng.standard_normal(600) * np.sqrt(s * s + 2.0 ** 2)
    assert abs(mle_x(b, s, np.ones((600, 1))) - mle(b, s)[0]) < 1e-3
    X = np.column_stack([grp == k for k in range(3)]).astype(float)
    assert abs(mle_x(b, s, X) - 2.0) < 0.25 and mle(b, s)[0] > 3
    print("mle_x: ok")


# ------------------------------------------------------------------------------------ part 3

POSTHOC = [  # Phil's mapping, made after P's archetype z were seen
    dict(update="v0.103.2", patch="first", change="Regalite and Arsenal now reward any created card",
         color="regent", archetype="create", direction="up",
         enabler_build="v0.101.0 (Arsenal rework; Regalite's build is not in the reference tables)",
         why="Phil's mapping; Arsenal's new text is a create payoff"),
    dict(update="v0.103.2", patch="first", change="Acrobatics Common -> Uncommon",
         color="silent", archetype="discard", direction="down", enabler_build="v0.103.0",
         why="Phil's mapping; a draw-and-discard card is offered less often"),
    dict(update="v0.103.2", patch="first", change="Not Yet added (Rare, heals)",
         color="ironclad", archetype="hp_loss", direction="up", enabler_build="v0.103.0",
         why="Phil's mapping; a heal pays for HP loss. Not a text-rule match: Not Yet's own "
             "text is not in hp_loss"),
]
BEFORE_Z = [  # written in TRIAGE.md section T's rules before part 3 loaded any z
    dict(update="v0.103.2", patch="first", change="Acrobatics Common -> Uncommon", color="silent",
         archetype="draw", direction="down", enabler_build="v0.103.0",
         why="a draw-and-discard card is offered less often", z_seen_in_p="yes"),
    dict(update="v0.103.2", patch="first", change="Colossus Rare -> Uncommon", color="ironclad",
         archetype="debuff", direction="up", enabler_build="v0.103.0",
         why="a Vulnerable payoff is offered more often", z_seen_in_p="yes"),
    dict(update="v0.103.2", patch="first", change="Follow Through reworked, Uncommon -> Common",
         color="silent", archetype="debuff", direction="down", enabler_build="v0.103.0",
         why="its old text applied Weak; the new text does not", z_seen_in_p="yes"),
    dict(update="v0.103.2", patch="first", change="Follow Through reworked, Uncommon -> Common",
         color="silent", archetype="skill_play", direction="down", enabler_build="v0.103.0",
         why="its old text paid off playing a Skill; the new text does not", z_seen_in_p="yes"),
    dict(update="v0.103.2", patch="first", change="Not Yet added (Rare, 'Heal ... Exhaust')",
         color="ironclad", archetype="exhaust", direction="up", enabler_build="v0.103.0",
         why="one more card that exhausts itself", z_seen_in_p="no"),
    dict(update="v0.107.1", patch="second", change="Scare Common -> Uncommon", color="silent",
         archetype="debuff", direction="down", enabler_build="v0.106.0",
         why="a Weak card is offered less often", z_seen_in_p="yes"),
    dict(update="v0.107.1", patch="second", change="Predator Uncommon -> Common", color="silent",
         archetype="draw", direction="up", enabler_build="v0.106.0",
         why="a draw card is offered more often", z_seen_in_p="no"),
]
NOT_SCORED = [
    ("v0.103.2", "Rip and Tear -> Event", "no text or color on file"),
    ("v0.103.2", "Grapple deprecated", "no text or color on file"),
    ("v0.103.2", "Hefty Tablet (Neow: choose one of three Rare cards)",
     "touches Rares, a rarity and not an archetype; reported as a rarity row"),
    ("v0.103.2", "Ascension 6: Gloom -> Inflation", "no archetype under P's text rules"),
    ("v0.103.2", "Shop relic prices and pool", "no archetype under P's text rules"),
    ("v0.103.2", "Colorless pool and rarity shifts",
     "Regent create (P: most of its cards make Colorless cards): already a post hoc row"),
    ("v0.107.1", "Kaleidoscope (Neow: 2 card rewards from other characters)",
     "other characters' cards; no archetype under P's text rules"),
    ("v0.107.1", "PRNG replaced (xoshiro256**)", "no archetype; see part 1 and the open list"),
    ("v0.107.1", "Enemy, boss and ascension HP changes", "no archetype under P's text rules"),
]


def enabler_list():
    rows = [dict(e, label="post hoc", z_seen_in_p="yes") for e in POSTHOC]
    rows += [dict(e, label="written before reading z") for e in BEFORE_Z]
    rows += [dict(update=u, change=c, why=w, label="written before reading z: not scored",
                  patch="first" if u == "v0.103.2" else "second") for u, c, w in NOT_SCORED]
    return pd.DataFrame(rows)[["label", "update", "patch", "change", "color", "archetype",
                               "direction", "enabler_build", "why", "z_seen_in_p"]]


def mle_x(b, s, X, return_fit=False):
    """b_i ~ Normal(X_i c, s_i^2 + tau^2): tau by maximum likelihood, c profiled out by
    generalized least squares at each tau (q.mle with a design matrix)."""
    b, s, X = np.asarray(b, float), np.asarray(s, float), np.asarray(X, float)
    X = X[:, np.abs(X).sum(axis=0) > 0]

    def prof(tau):
        w = 1 / (s * s + tau * tau)
        sw = np.sqrt(w)
        c, *_ = np.linalg.lstsq(X * sw[:, None], b * sw, rcond=None)
        res = b - X @ c
        return 0.5 * (np.sum(w * res * res) - np.sum(np.log(w))), res

    hi = 3 * b.std() + 1e-9
    o = optimize.minimize_scalar(lambda t: prof(t)[0], bounds=(0, hi), method="bounded",
                                 options=dict(xatol=1e-6 * max(hi, 1)))
    tau = float(o.x) if o.fun < prof(0.0)[0] else 0.0
    return (tau, prof(tau)[1]) if return_fit else tau


def design(L, col):
    """P's design: a character-window intercept and one indicator per character-window and
    archetype named in `col` (demean_archetype's X)."""
    cw = (L.color + " " + L.patch).to_numpy()
    names = sorted(set(cw))
    terms = sorted({f"{c}|{a}" for c, v in zip(cw, L[col].str.split()) for a in v})
    ix = {n: j for j, n in enumerate(names + terms)}
    X = np.zeros((len(L), len(ix)))
    for i, (c, v) in enumerate(zip(cw, L[col].str.split())):
        X[i, ix[c]] = 1.0
        for a in v:
            X[i, ix[f"{c}|{a}"]] = 1.0
    return X, len(terms)


def budget(L, cols, n_perm=1000, n_boot=500):
    rng = np.random.default_rng(p.SEED + 2)
    L = L.reset_index(drop=True)
    cw = (L.color + " " + L.patch).to_numpy()
    b, s, z = 100 * L.beta.to_numpy(), 100 * L.se.to_numpy(), L.z.to_numpy()
    rows = []
    for col, what in cols:
        X, k = design(L, col)
        res_z = z - X @ np.linalg.lstsq(X, z, rcond=None)[0]
        nz = {pt: [] for pt in p.FACTORS}
        ntau = {pt: [] for pt in p.FACTORS}
        for it in range(n_perm):
            Lp = L.copy()
            for g in np.unique(cw):
                ix = np.flatnonzero(cw == g)
                Lp.loc[ix, col] = L[col].to_numpy()[rng.permutation(ix)]
            Xp, _ = design(Lp, col)
            rz = z - Xp @ np.linalg.lstsq(Xp, z, rcond=None)[0]
            for pt in p.FACTORS:
                m = (L.patch == pt).to_numpy()
                nz[pt].append(robust_sd(rz[m]))
                if it < 200:
                    ntau[pt].append(mle_x(b[m], s[m], Xp[m]))
        for pt, f in p.FACTORS.items():
            m = (L.patch == pt).to_numpy()
            Xm = X[m]
            tau = mle_x(b[m], s[m], Xm)
            tau0 = mle_x(b[m], s[m], pd.get_dummies(pd.Series(cw[m])).to_numpy(float))
            bm, sm = b[m], s[m]
            bt = cluster_boot(L.pseudo_card[m].to_numpy(), lambda i: mle_x(bm[i], sm[i], Xm[i]), n=n_boot)
            kk = int((np.abs(Xm).sum(axis=0) > 0).sum() - len(set(cw[m])))
            rows.append(dict(
                terms=what, patch=pt, factor=f, n_pairs=int(m.sum()), n_terms_all=k, n_terms_patch=kk,
                n_pairs_in_a_term=int((L[col][m] != "").sum()),
                robust_sd_all=robust_sd(z[m]), robust_sd_absorbed=robust_sd(res_z[m]),
                shuffled_mean=np.mean(nz[pt]), shuffled_lo=np.percentile(nz[pt], 2.5),
                shuffled_hi=np.percentile(nz[pt], 97.5),
                tau_character_window_only=tau0, tau_absorbed=tau, tau_lo=pct(bt)[0], tau_hi=pct(bt)[1],
                tau_shuffled_mean=np.mean(ntau[pt]), tau_shuffled_lo=np.percentile(ntau[pt], 2.5),
                tau_shuffled_hi=np.percentile(ntau[pt], 97.5),
                share_of_excess_var_z=(np.mean(nz[pt]) ** 2 - robust_sd(res_z[m]) ** 2)
                / (robust_sd(z[m]) ** 2 - 1),
                share_of_tau2=(np.mean(ntau[pt]) ** 2 - tau ** 2) / tau0 ** 2))
    return pd.DataFrame(rows)


def contrast(g, member, zcol="z", bcol="beta", n_perm=10000, seed=0):
    """Members against the rest: mean z, mean beta (pp), difference, a label-shuffle p."""
    m = np.asarray(member, bool)
    if m.sum() < 1 or (~m).sum() < 1:
        return dict(n_members=int(m.sum()), n_rest=int((~m).sum()))
    z, b = g[zcol].to_numpy(float), 100 * g[bcol].to_numpy(float)
    d = z[m].mean() - z[~m].mean()
    rng = np.random.default_rng(seed)
    null = np.array([(lambda mm: z[mm].mean() - z[~mm].mean())(rng.permutation(m))
                     for _ in range(n_perm)]) if m.sum() >= 2 else np.array([np.nan])
    return dict(n_members=int(m.sum()), n_rest=int((~m).sum()), mean_z_members=z[m].mean(),
                mean_z_rest=z[~m].mean(), diff_z=d, n_members_z_pos=int((z[m] > 0).sum()),
                mean_beta_pp_members=b[m].mean(), mean_beta_pp_rest=b[~m].mean(),
                diff_beta_pp=b[m].mean() - b[~m].mean(),
                p_shuffle_two_sided=float((np.abs(null) >= abs(d)).mean()) if m.sum() >= 2 else np.nan)


def has_arch(arch_series, a):
    return arch_series.fillna("").str.split().apply(lambda v: a in v).to_numpy()


# v0.99.0-beta is left out: card_versions.csv has no version for any card on it (unknown, not
# guessed), so window_changes would mark every card as changed. It holds 52 to 94 runs a character.
BETA_BUILDS = ["v0.99.0", "v0.100.0", "v0.101.0", "v0.102.0", "v0.103.0", "v0.103.1"]
B_COLS = ["color", "enabler_build", "before_builds", "after_builds", "pseudo_card", "beta", "se", "z",
          "n_offers", "n_runs", "pseudo_offers_before", "pseudo_offers_after", "rate_before",
          "rate_after", "n_control_cards", "n_eligible", "runs_before", "runs_after", "error"]


def changed_any(builds):
    out = set()
    for a_, b_ in zip(builds, builds[1:]):
        ch, _ = did.window_changes(a_, b_)
        out |= ch
    return out


def beta_fits(con, time_only=False):
    """First-window enablers on the beta branch: beta builds before the enabler's build
    pooled against the enabler's build through v0.103.1, cards unchanged across all of them."""
    store = Store("t_beta_fits", B_COLS)
    for color, eb in (("regent", "v0.101.0"), ("silent", "v0.103.0"), ("ironclad", "v0.103.0")):
        chunk = f"{color}|{eb}"
        if chunk in store.done and not time_only:
            continue
        t0 = time.time()
        i = BETA_BUILDS.index(eb)
        bb, ab = BETA_BUILDS[:i], BETA_BUILDS[i:]
        raw = did._load_offers(con, color, bb + ab)
        raw["block"] = np.where(raw.build_id.isin(ab), "after", "before")
        raw["week"] = np.floor((raw.start_time - q.release(eb)).dt.total_seconds()
                               / did.WEEK).astype("int16")
        df = did._finish(raw)
        key = q.fake_host(color, f"T:{chunk}", changed_any(BETA_BUILDS))
        el = q.eligible(df, key, q.card_order(color))
        runs = df.groupby("block", observed=True).run_key.nunique()
        base = dict(color=color, enabler_build=eb, before_builds=" ".join(bb),
                    after_builds=" ".join(ab), n_eligible=len(el),
                    runs_before=int(runs.get("before", 0)), runs_after=int(runs.get("after", 0)))
        rows = []
        for c in (el[:10] if time_only else el):
            row = dict(base, pseudo_card=c, error="")
            try:
                row.update(q.fit(df, key, c))
                row["z"] = row["beta"] / row["se"]
            except Exception as e:
                row["error"] = f"{type(e).__name__}: {e}"[:200]
            rows.append(row)
        if time_only:
            t = (time.time() - t0) / max(len(rows), 1)
            print(f"part 3 beta fits timing ({chunk}, {len(df):,} offers, {len(el)} eligible): "
                  f"{t:.2f} s per fit with the load; three characters: about "
                  f"{3 * len(el) * t / 60:.0f} min", flush=True)
            return
        store.add(chunk, rows or [dict(base, error="no eligible card")])
        print(f"  beta {chunk}: {len(rows)} fits, runs {base['runs_before']} / {base['runs_after']}, "
              f"{time.time() - t0:.0f} s", flush=True)


def part3(con, pairs):
    A = pd.read_csv(f"{OUT}/p_archetypes.csv", dtype=str, keep_default_na=False)
    W = pd.read_csv(f"{OUT}/p_archetype_windows.csv", dtype=str, keep_default_na=False)
    L = p.label_pairs(pairs, A, W).reset_index(drop=True)
    E = enabler_list()
    scored = E[E.archetype.notna() & (E.archetype != "")]

    # archetype z at the stable release: all-offers pairs, as P's post hoc table
    ao = L[L.fit_on == "all offers"]
    zrows = []
    for e in scored.itertuples():
        g = ao[(ao.patch == e.patch) & (ao.color == e.color)].reset_index(drop=True)
        c = contrast(g, has_arch(g.archetypes, e.archetype))
        sign = {"up": 1, "down": -1}[e.direction]
        zrows.append(dict(label=e.label, update=e.update, change=e.change, color=e.color,
                          archetype=e.archetype, implied_direction=e.direction,
                          z_seen_in_p=e.z_seen_in_p, **c,
                          as_implied=(np.sign(c["diff_z"]) == sign) if "diff_z" in c else np.nan))
    Z = pd.DataFrame(zrows)
    # Hefty Tablet: a rarity row (Rares against the rest), first window, by character
    rar = []
    for (patch, color), g in ao.groupby(["patch", "color"]):
        g = g.reset_index(drop=True)
        rr = np.array([window_rarity(patch, c) for c in g.pseudo_card])
        rar.append(dict(patch=patch, color=color, group="Rare against the rest",
                        **contrast(g, rr == "Rare")))
    RAR = pd.DataFrame(rar)

    # beta builds: the three post hoc rows from the fresh fits; the second window's rows from R
    brows = []
    if os.path.exists(f"{OUT}/t_beta_fits.csv"):
        bf = Store("t_beta_fits", B_COLS).read()
        bf = bf[bf.error.fillna("").eq("") & np.isfinite(bf.z)]
        arch1 = A[A.window == "first"].set_index("card_id").archetypes
        for e in scored[scored.patch == "first"].itertuples():
            g = bf[bf.color == e.color].reset_index(drop=True)
            if g.empty:
                continue
            mem = has_arch(g.pseudo_card.map(arch1), e.archetype)
            st = Z[(Z.label == e.label) & (Z.color == e.color) & (Z.archetype == e.archetype)
                   & (Z["update"] == e.update)].iloc[0]
            brows.append(dict(
                label=e.label, color=e.color, archetype=e.archetype, change=e.change,
                source="fresh fits, beta builds pooled", before_builds=g.before_builds.iloc[0],
                after_builds=g.after_builds.iloc[0], runs_before=int(g.runs_before.iloc[0]),
                runs_after=int(g.runs_after.iloc[0]), median_se_pp=100 * g.se.median(),
                robust_sd_z=robust_sd(g.z), **contrast(g, mem),
                stable_diff_z=st.diff_z, stable_diff_beta_pp=st.diff_beta_pp,
                stable_n_members=st.n_members))
    rf = pd.read_csv(f"{OUT}/r_dose_fits.csv")
    rf = rf[rf.error.fillna("").eq("") & np.isfinite(rf.z)]
    arch2 = A[A.window == "second"].set_index("card_id").archetypes
    for e in scored[scored.patch == "second"].itertuples():
        for bd in sorted(b_ for b_ in rf.boundary.unique() if "-> v0.106.0" in b_):
            g = rf[(rf.boundary == bd) & (rf.color == e.color)].reset_index(drop=True)
            if g.empty:
                continue
            st = Z[(Z.label == e.label) & (Z.color == e.color) & (Z.archetype == e.archetype)
                   & (Z["update"] == e.update)].iloc[0]
            brows.append(dict(label=e.label, color=e.color, archetype=e.archetype, change=e.change,
                              source=f"R's saved beta fits, {bd}", median_se_pp=100 * g.se.median(),
                              robust_sd_z=robust_sd(g.z),
                              **contrast(g, has_arch(g.pseudo_card.map(arch2), e.archetype)),
                              stable_diff_z=st.diff_z, stable_diff_beta_pp=st.diff_beta_pp,
                              stable_n_members=st.n_members))
    BT = pd.DataFrame(brows)

    # budget
    def named(rows_):
        keys = {(e.patch, e.color, e.archetype) for e in rows_.itertuples()}
        return [" ".join(a for a in arch.split() if (pt, col, a) in keys)
                for pt, col, arch in zip(L.patch, L.color, L.archetypes)]

    L["t_posthoc"] = named(scored[scored.label == "post hoc"])
    L["t_named"] = named(scored)
    L["t_all"] = L.arch_changed
    B = budget(L, [("t_posthoc", "the three post hoc archetype-windows"),
                   ("t_named", "post hoc plus the list written before reading z"),
                   ("t_all", "P's figure: every archetype with a substantive change to a member")])
    return E, Z, RAR, BT, B, L


# ------------------------------------------------------------------------------------- main

def privacy():
    import re
    bad_col = re.compile(r"uploader|player|run_key|run_hash|screen_id|hash|steam|start_time|token|seed")
    n_text = 0
    for f in sorted(glob.glob(f"{OUT}/t_*.csv")):
        check_output(os.path.basename(f)[:-4], pd.read_csv(f, converters={"pseudo_card": str, "card_id": str}))
        d = pd.read_csv(f, dtype=str, keep_default_na=False)      # the scan below reads text as written
        cols = [c for c in d.columns if bad_col.search(c)]
        vals = set()
        for c in d.columns:
            v = d[c][~d[c].str.fullmatch(r"-?[\d.eE+-]*|True|False|nan|")]
            vals |= set(v.unique())
        long_hex = [v for v in vals if re.search(r"[0-9a-f]{12,}", v)]
        piped = [v for v in vals if re.fullmatch(r"[^ ]+\|\d+\|[^ ]+", v)]
        n_text += len(vals)
        print(f"  {os.path.basename(f)}: {len(d)} rows, {len(d.columns)} columns; identifier-like "
              f"columns {cols}; hex-like values {len(long_hex)}; key-like values {len(piped)}; "
              f"longest text value {max((len(v) for v in vals), default=0)}")
        if cols or long_hex or piped:
            raise SystemExit(f"privacy check failed on {f}: {cols} {long_hex[:3]} {piped[:3]}")
    print(f"privacy check: clean ({n_text} distinct text values scanned)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", choices=("1", "2a", "2b", "2c", "3"), action="append", default=[])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--time", action="store_true")
    ap.add_argument("--analyze", action="store_true")
    ap.add_argument("--privacy", action="store_true")
    ap.add_argument("--sample", type=int, default=0,
                    help="part 2c: a fixed random N pairs per patch (the declared fallback: 100)")
    args = ap.parse_args()

    T0 = time.time()
    pd.set_option("display.width", 250, "display.max_columns", 80, "display.max_rows", 500,
                  "display.max_colwidth", 80, "display.float_format", "{:.4f}".format)
    os.makedirs(OUT, exist_ok=True)
    if args.privacy:
        privacy()
        sys.exit()
    db.use_derived_colors()
    con = db.connect()
    try:
        con.execute(f"SET temp_directory = '{os.environ.get('TMPDIR', '/tmp/claude')}/t_around_duckdb'")
    except Exception as e:                      # spill space only; the queries run without it
        print(f"temp_directory not set: {e}")
    q.patch_did(con)
    PAIRS = did.placebo_pairs(pd.read_parquet(q.PLACEBO))
    f1, f2 = (round(robust_sd(PAIRS.z[PAIRS.patch == x]), 2) for x in ("first", "second"))
    t1, t2 = (round(mle(100 * g.beta, 100 * g.se)[0], 2) for _, g in PAIRS.groupby("patch"))
    if len(PAIRS) != 463 or (f1, f2) != (4.10, 2.67) or (t1, t2) != (3.35, 2.44):
        raise SystemExit(f"startup gate failed: {len(PAIRS)} pairs, {f1} / {f2}, tau {t1} / {t2}")
    print(f"startup gate: 463 pairs, robust sd {f1} / {f2}, tau {t1} / {t2} pp", flush=True)

    if args.check:
        check()
        gate(con, PAIRS)

    if "1" in args.part:
        M, ST, NV, n_const, EV, PR, TI = part1(con)
        PL = placed_from_offers(con)
        save(M[M.kind == "build"].drop(columns="kind"), "t_builds")
        save(M[M.kind == "block"].drop(columns="kind"), "t_blocks")
        save(ST, "t_steps"), save(NV, "t_null_shares"), save(EV, "t_card_ids")
        save(PR, "t_id_pairs"), save(TI, "t_rarity_tiers"), save(PL, "t_placed_from_offers")
        show("t_builds", M[M.kind == "build"].drop(columns="kind").T.reset_index())
        show("t_steps (flagged at a major update)", ST[ST.flag])
        piv = ST.pivot_table(index="metric", columns="boundary", values="delta", sort=False)
        print("t_steps: delta per boundary\n", piv.to_string(), flush=True)
        print(f"null shares: {n_const} columns constant across builds and blocks; moving ones:")
        print(NV[NV.kind == "build"].pivot_table(index=["table", "column"], columns="label",
                                                 values="null_share", sort=False).T.to_string())
        show("t_card_ids", EV)
        show("t_id_pairs", PR)
        show("t_rarity_tiers: tier changes or differs from today's",
             TI[TI.tier_changes | TI.differs_from_today_first | TI.differs_from_today_second])
        show("t_placed_from_offers", PL)
        UO, UOS = under_offered(TI, PAIRS)
        save(UO, "t_under_offered"), save(UOS, "t_under_offered_summary")
        show("t_under_offered (post hoc)", UO)
        show("t_under_offered_summary (post hoc)", UOS)

    if "2a" in args.part:
        fits, info = Store("t_source_fits", A_COLS), Store("t_source_windows", A_INFO)
        if not args.analyze:
            run_fits(con, PAIRS, fits, {v: (flt, None) for v, flt in FILTERS.items()}, A_COLS,
                     time_only=args.time, extra=True, info=info)
        if not args.time:
            F = fits.read()
            ok = F[F.error.fillna("").eq("") & np.isfinite(F.z) & (F.se > 0)]
            print(f"  fits: {len(F)}, failed: {len(F) - len(ok)}")
            TA = tau_table(ok, list(FILTERS), "2a")
            TA["outcome"] = np.where((TA.ratio_to_q <= 0.75) & ~TA.intervals_overlap_q,
                                     "offer-source composition is part of the jump", "not part of it")
            save(TA, "t_source_tau")
            show("t_source_windows", info.read())
            print(TA.T.to_string(), flush=True)

    if "2b" in args.part:
        C = part2b(con, PAIRS)
        TS, SZ, BY = part2b_tests(C)
        save(C, "t_comp_pairs"), save(TS, "t_comp_tests"), save(SZ, "t_comp_size")
        save(BY, "t_comp_groups")
        show("t_comp_tests", TS)
        show("t_comp_size", SZ)
        show("t_comp_groups", BY)

    if "2c" in args.part:
        fits = Store("t_screen_fits", A_COLS)
        sub = None
        if args.sample:
            rng = np.random.default_rng(q.SEED)
            pick = np.concatenate([rng.choice(np.flatnonzero(PAIRS.patch == x), args.sample, replace=False)
                                   for x in ("first", "second")])
            sub = np.isin(np.arange(len(PAIRS)), pick)
        if not args.analyze:
            run_fits(con, PAIRS, fits, {"screen FE": (None, ("screen_id",))}, A_COLS,
                     time_only=args.time, subset=sub)
        if not args.time:
            F = fits.read()
            ok = F[F.error.fillna("").eq("") & np.isfinite(F.z) & (F.se > 0)]
            print(f"  fits: {len(F)}, failed: {len(F) - len(ok)}")
            TC = tau_table(ok, ["screen FE"], "2c")
            TC["outcome"] = np.where(TC.ratio_to_saved <= 0.75,
                                     "competition on the screen carries a real share",
                                     "the miss is the card's own, not its screen's")
            save(TC, "t_screen_tau")
            print(TC.T.to_string(), flush=True)

    if "3" in args.part:
        save(enabler_list(), "t_enabler_list")          # saved before any z is loaded below
        if not args.analyze:
            beta_fits(con, time_only=args.time)
        if not args.time:
            E, Z, RAR, BT, B, L = part3(con, PAIRS)
            save(Z, "t_enabler_z"), save(RAR, "t_rarity_rows"), save(BT, "t_enabler_beta")
            save(B, "t_budget")
            show("t_enabler_z", Z)
            show("t_rarity_rows", RAR)
            show("t_enabler_beta", BT)
            print(B.T.to_string(), flush=True)

    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2 ** 30
    print(f"done in {time.time() - T0:.0f} s; peak RSS {rss:.1f} GB")
