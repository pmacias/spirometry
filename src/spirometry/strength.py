"""Strength change across a patch (Phase 5 step 5): after the patch, is picking a card
worth more or less for winning than before, compared with unchanged cards? Tables only.

spirometry.wins estimates, within one set of builds, the effect of taking card X on one of
a run's first K reward screens on winning (IV, with the RNG's offer as the instrument).
Here the same fits run twice, once on the window's before builds and once on its after
builds, for the treated card and for every control card (same color, unchanged in the
window: did.control_cards, control_exclusions applied); the change is after - before:

    con = duckdb.connect("data/runs/runs.duckdb", read_only=True)
    res = strength_change(con, "PARRY@v0.103.2/patch")  # Strength(blocks, changes, summary)
    res = strength_all(con)                             # every solo-estimable numeric tweak
    save(res, "data/analysis", "main"); load("data/analysis", "main")
    balance_check(wins.load_early(con, "regent", ["v0.103.2"]), "PARRY")

Three estimates per card and block (wins.itt / first_stage / iv, same fixed effects and
errors), and their change:
    iv   effect of taking the card on winning (the strength estimate; noisy: it divides the
         itt by the first stage)
    itt  effect of being offered it (less noisy; = first stage x iv, so it also moves when
         only the pick rate moves: not a pure strength measure)
    fs   the first stage: how much being offered it raises taking it (a pick rate)

"Net of unchanged cards": the treated card's change minus the median change of the
controls, with the controls' spread (median and MAD scaled by 1.4826, as
did.offer_rate_check). z-scores for every row: z_spread (net over the controls' MAD), z_se
(net over the card's own se, the median's se added), z_total (also adding tau^2 = the
controls' MAD^2 minus their median se^2, the spread between cards beyond noise). The
controls' rows give the null distribution to read the treated card's z against.

The before and after blocks are different runs (different builds), so their estimates are
independent and se(after - before) = sqrt(se_before^2 + se_after^2); strength_change checks
that no run_key is in both blocks. Differencing two separate fits equals one stacked fit
with every fixed effect interacted with the block (tests/test_strength.py checks this on
the ITT).
"""
import pathlib
import time
from typing import NamedTuple

import numpy as np
import pandas as pd
from scipy import stats

from spirometry import did, wins

REF = did.REF
MAD_SCALE = 1.4826
MEDIAN_SE = 1.2533              # se of a median ~ 1.2533 sd / sqrt(n) (normal data)
ESTIMATES = ("iv", "itt", "fs")
MATCHED = ("iv", "itt")         # fs matched on fs would be ~0 by construction
K_MATCH = 20                    # controls matched on first stage, per block
BALANCE_ALPHA = 0.05
MIN_LEVEL_RUNS = 20             # balance_check: levels with fewer runs are pooled
UPGRADE_ONLY_REASON = ("upgrade-only tweak: not estimated (the treatment 'took the card "
                       "early' doesn't separate the upgraded card; out for now)")


class Strength(NamedTuple):
    """strength_change / strength_all result: `blocks` one row per (card, block), `changes`
    one row per card (after - before, net of controls), `summary` one row per card-patch
    (the treated card's row with the controls' statistics and counts)."""
    blocks: pd.DataFrame
    changes: pd.DataFrame
    summary: pd.DataFrame


# ------------------------------------------------------------------------------ block fits

BLOCK_COLS = ["card_id", "n_runs", "n_singletons_dropped", "n_offered", "n_picked",
              "win_rate_offered", "win_rate_not_offered", "pick_rate_offered",
              "itt_beta", "itt_se", "fs_coef", "fs_se", "fs_F", "weak", "iv_beta", "iv_se",
              "reason"]


def block_estimates(data, cards, *, min_offered=wins.MIN_OFFERED, include_short_runs=False,
                    group=None, pooled_groups=False, screen_mix=False):
    """wins.itt, first_stage and iv for each card on one block's data (a wins.load_early
    result), one row per card. The run frame is built once and only offered / picked change
    per card (same rows, formulas and errors as the wins functions). A card with fewer than
    `min_offered` offered runs in the fit's runs, or whose fit fails, gets blank estimates
    and a `reason`. `weak` (first-stage F < 10) is reported, not acted on here."""
    base = wins.run_frame(data, None, include_short_runs=include_short_runs, group=group)
    fe = " + ".join(wins._fixed_effects(base, group, pooled_groups, screen_mix)) \
        if len(base) else ""
    o = data.offers[data.offers.run_key.isin(base.run_key)]
    by_card = {c: g for c, g in o.groupby("card_id", observed=True)}
    rows = []
    for card in cards:
        g = by_card.get(card, o.iloc[:0])
        d = base.copy(deep=False)
        d["offered"] = d.run_key.isin(g.run_key).astype("int8")
        d["picked"] = d.run_key.isin(g.run_key[g.picked]).astype("int8")
        n_off = int(d.offered.sum())
        row = dict(card_id=card, n_runs=len(d), n_offered=n_off,
                   n_picked=int(d.picked.sum()), reason="")
        if n_off < min_offered:
            row["reason"] = f"fewer than {min_offered} offered runs ({n_off})"
        elif n_off == len(d):
            row["reason"] = "offered on every run"
        else:
            try:
                row.update(_fit_card(d, fe))
            except Exception as e:                  # report and keep going
                row["reason"] = f"{type(e).__name__}: {' '.join(str(e).split())}"
        rows.append(row)
    return pd.DataFrame(rows).reindex(columns=BLOCK_COLS)


def _fit_card(d, fe):
    a = wins._feols(f"win ~ offered | {fe}", d)
    f = wins._feols(f"picked ~ offered | {fe}", d)
    b = wins._feols(f"win ~ 1 | {fe} | picked ~ offered", d)
    itt_b, itt_se = wins._coef(a, "offered")
    fc, fse = wins._coef(f, "offered")
    iv_b, iv_se = wins._coef(b, "picked")
    F = (fc / fse) ** 2 if fse > 0 else np.nan
    rates = d.groupby("offered").win.mean()
    return dict(n_runs=int(a._N), n_singletons_dropped=len(d) - int(a._N),
                win_rate_offered=float(rates.get(1, np.nan)),
                win_rate_not_offered=float(rates.get(0, np.nan)),
                pick_rate_offered=float(d.picked[d.offered == 1].mean()),
                itt_beta=itt_b, itt_se=itt_se, fs_coef=fc, fs_se=fse, fs_F=F,
                weak=bool(not F >= wins.WEAK_F), iv_beta=iv_b, iv_se=iv_se)


# ------------------------------------------------------------------------------ changes

def _differences(before, after, treated):
    """One row per card: each estimate before, after, change and its se, and why a change
    is blank (iv: a block missing or weak; itt, fs: a block missing)."""
    b, a = before.set_index("card_id"), after.set_index("card_id")
    out = pd.DataFrame({"card_id": b.index, "treated": b.index == treated})
    out = out.set_index("card_id")
    for side, t in (("before", b), ("after", a)):
        out[f"n_runs_{side}"] = t.n_runs
        out[f"n_offered_{side}"] = t.n_offered
        out[f"n_picked_{side}"] = t.n_picked
        out[f"fs_F_{side}"] = t.fs_F
        out[f"weak_{side}"] = t.weak
    missing = pd.Series("", index=out.index)
    for side, t in (("before", b), ("after", a)):
        missing = missing.str.cat(np.where(t.reason != "", f"{side}: " + t.reason, ""),
                                  sep="; ").str.strip("; ")
    weak = pd.Series("", index=out.index)
    for side, t in (("before", b), ("after", a)):
        w = (t.reason == "") & t.weak.fillna(False).astype(bool)
        weak = weak.str.cat(np.where(w, f"weak first stage {side} (F = "
                                     + t.fs_F.round(1).astype(str) + ")", ""), sep="; "
                            ).str.strip("; ")
    for est, col in (("iv", "iv_beta"), ("itt", "itt_beta"), ("fs", "fs_coef")):
        se_col = col.replace("_beta", "_se").replace("_coef", "_se")
        out[f"{est}_before"], out[f"{est}_after"] = b[col], a[col]
        out[f"{est}_se_before"], out[f"{est}_se_after"] = b[se_col], a[se_col]
        reason = missing if est != "iv" else missing.str.cat(weak, sep="; ").str.strip("; ")
        ok = reason == ""
        out[f"{est}_change"] = (a[col] - b[col]).where(ok)
        out[f"{est}_change_se"] = np.hypot(a[se_col], b[se_col]).where(ok)
        out[f"{est}_reason"] = reason
    return out.reset_index()


def _net_of_controls(ch):
    """Adds, per estimate, the controls' median and scaled MAD of the change, the median's
    se (1.2533 MAD / sqrt(n)), tau (spread between cards beyond their own noise), and for
    every row net, z_raw, z_spread, z_se (net over sqrt(se^2 + median se^2)), z_total.
    The median and MAD use the controls with a change (the row itself included when it is a
    control, as in did.offer_rate_check)."""
    stats_ = {}
    for est in ESTIMATES:
        c = ch[~ch.treated & ch[f"{est}_change"].notna()]
        x, se = c[f"{est}_change"], c[f"{est}_change_se"]
        med = float(x.median()) if len(x) else np.nan
        mad = float(MAD_SCALE * (x - med).abs().median()) if len(x) else np.nan
        tau = float(np.sqrt(max(mad ** 2 - (se ** 2).median(), 0))) if len(x) else np.nan
        med_se = MEDIAN_SE * mad / np.sqrt(len(x)) if len(x) else np.nan
        net = ch[f"{est}_change"] - med
        se_net = np.sqrt(ch[f"{est}_change_se"] ** 2 + med_se ** 2)
        ch[f"{est}_net"] = net
        ch[f"{est}_z_raw"] = ch[f"{est}_change"] / ch[f"{est}_change_se"]
        ch[f"{est}_z_spread"] = net / mad if mad > 0 else np.nan
        ch[f"{est}_z_se"] = net / se_net
        ch[f"{est}_z_total"] = net / np.sqrt(se_net ** 2 + tau ** 2)
        z = ch.loc[c.index, f"{est}_z_se"]
        stats_[est] = dict(controls_median=med, controls_median_se=med_se,
                           controls_mad=mad, controls_tau=tau, n_controls_used=len(x),
                           controls_share_abs_z_se_gt2=float((z.abs() > 2).mean())
                           if len(z) else np.nan)
    return ch, stats_


def _matched(ch, before, after, k):
    """Net of the k controls whose first stage, in each block, is closest to the card's.

    A drift that acts per offer on every card (d on the itt scale) is d / first stage on
    the iv scale, so it cancels against controls taken about as often as the card. The
    treated card's first stage moves with the patch, so the controls are matched
    separately in each block, and the comparison is made on the block's levels:

        net_m = (est_after - median of matched controls' est_after)
                - (est_before - median of matched controls' est_before)

    {est}_matched_change is the difference of the two medians. Because the two blocks'
    matched sets can hold different cards, differences in the controls' own levels
    (card strength) enter net_m; they are counted in its uncertainty:
    z_se_m = net_m / sqrt(se^2 + median se_before^2 + median se_after^2), each median's se
    1.2533 MAD / sqrt(n) of the matched controls' levels in that block (so it includes
    the spread between those cards); z_spread_m = net_m / sqrt(MAD_before^2 +
    MAD_after^2); z_total_m adds tau_m^2 (that spread minus the matched controls' median
    se^2 in each block). Eligible controls in a block: a fit there (no reason) and, for
    iv, no weak first stage. Every row gets the columns (a control is matched against the
    other controls, never itself); rows without both blocks stay blank."""
    tb, ta = before.set_index("card_id"), after.set_index("card_id")
    ctrl = ch.card_id[~ch.treated].tolist()
    for est in MATCHED:
        col, se_col = f"{est}_beta", f"{est}_se"
        ok = {}
        for side, t in (("before", tb), ("after", ta)):
            good = (t.reason == "") & t[col].notna()
            if est == "iv":
                good &= ~t.weak.fillna(True).astype(bool)
            ok[side] = good
        rows = []
        for card in ch.card_id:
            r, parts = {}, {}
            for side, t in (("before", tb), ("after", ta)):
                pool = [c for c in ctrl if c != card and ok[side].get(c, False)]
                if not ok[side].get(card, False) or not pool:
                    parts = None
                    break
                dist = (t.fs_coef[pool] - t.fs_coef[card]).abs().sort_values(kind="stable")
                m = list(dist.index[:k])
                lv = t.loc[m, col]
                med = float(lv.median())
                mad = float(MAD_SCALE * (lv - med).abs().median())
                parts[side] = dict(level=float(t.loc[card, col]) - med, med=med, mad=mad,
                                   med_se=MEDIAN_SE * mad / np.sqrt(len(m)),
                                   noise2=float((t.loc[m, se_col] ** 2).median()),
                                   n=len(m), fs=float(t.fs_coef[m].median()))
            if parts:
                b, a = parts["before"], parts["after"]
                net = a["level"] - b["level"]
                se = float(np.hypot(tb.loc[card, se_col], ta.loc[card, se_col]))
                se_net = np.sqrt(se ** 2 + b["med_se"] ** 2 + a["med_se"] ** 2)
                spread = np.hypot(b["mad"], a["mad"])
                tau = np.sqrt(max(spread ** 2 - b["noise2"] - a["noise2"], 0))
                r = dict(net_m=net, matched_change=a["med"] - b["med"],
                         z_spread_m=net / spread if spread > 0 else np.nan,
                         z_se_m=net / se_net,
                         z_total_m=net / np.sqrt(se_net ** 2 + tau ** 2),
                         n_matched_before=b["n"], n_matched_after=a["n"],
                         fs_matched_before=b["fs"], fs_matched_after=a["fs"])
            rows.append(r)
        m = pd.DataFrame(rows, index=ch.index).reindex(columns=MATCHED_COLS)
        for c in MATCHED_COLS:
            ch[f"{est}_{c}"] = m[c]
    return ch


MATCHED_COLS = ["net_m", "matched_change", "z_spread_m", "z_se_m", "z_total_m",
                "n_matched_before", "n_matched_after", "fs_matched_before",
                "fs_matched_after"]


def _summary(ch, stats_, bal, meta):
    """The treated card's row with the controls' statistics and counts."""
    t = ch[ch.treated]
    row = dict(meta)
    t = t.iloc[0]
    for c in ("n_runs", "n_offered", "n_picked", "fs_F", "weak"):
        for side in ("before", "after"):
            row[f"{c}_{side}"] = t[f"{c}_{side}"]
    ctrl = ch[~ch.treated]
    row["n_controls"] = len(ctrl)
    few = ctrl.iv_reason.str.contains("fewer than")
    row["n_controls_skipped_few"] = int(few.sum())
    row["n_controls_skipped_weak"] = int((ctrl.iv_reason.str.contains("weak first stage")
                                          & ~few).sum())
    row["n_controls_error"] = int((ctrl.iv_reason != "").sum()
                                  - row["n_controls_skipped_few"]
                                  - row["n_controls_skipped_weak"])
    for est in ESTIMATES:
        for c in ("before", "after", "change", "change_se", "net", "z_raw", "z_spread",
                  "z_se", "z_total", "reason"):
            row[f"{est}_{c}"] = t[f"{est}_{c}"]
        for k, v in stats_[est].items():
            row[f"{est}_{k}"] = v
        if est in MATCHED:
            for c in MATCHED_COLS:
                row[f"{est}_{c}"] = t[f"{est}_{c}"]
    row.update(bal)
    return row


# ------------------------------------------------------------------------------ one tweak

def _options(K, min_offered, include_short_runs, group, pooled_groups, screen_mix,
             k_match):
    return dict(K=int(K), min_offered=int(min_offered), k_match=int(k_match),
                include_short_runs=bool(include_short_runs), group=group or "",
                pooled_groups=bool(pooled_groups), screen_mix=bool(screen_mix))


def _check_disjoint(before, after):
    """The se of a difference assumes independent blocks: no run in both."""
    both = set(before.runs.run_key) & set(after.runs.run_key)
    if both:
        raise ValueError(f"{len(both)} run_keys are in both blocks (e.g. "
                         f"{sorted(both)[0]}); the before and after builds must not "
                         "overlap")


def _color(card_patch_id, ref):
    w = did.window(card_patch_id, ref)
    color = did.card_colors(ref).get(w["card_id"], "")
    if not color:
        raise ValueError(f"{w['card_id']} has no color in the card list")
    return w, color


def _cards(card_patch_id, color, before, after, ref):
    """Treated card + controls: color cards offered in either block, minus the treated card
    and control_exclusions (did.control_cards)."""
    w = did.window(card_patch_id, ref)
    colored = {c for c, col in did.card_colors(ref).items() if col == color}
    seen = colored & (set(before.offers.card_id.astype(str))
                      | set(after.offers.card_id.astype(str)))
    controls = did.control_cards(card_patch_id, df=pd.DataFrame({"card_id": sorted(seen)}),
                                 ref=ref)
    return [w["card_id"]] + controls


def strength_change(con, card_patch_id, *, K=wins.K_DEFAULT, min_offered=wins.MIN_OFFERED,
                    include_short_runs=False, group=None, pooled_groups=False,
                    screen_mix=False, k_match=K_MATCH, balance=True, data=None, ref=REF,
                    _cache=None):
    """Did the patch change how much taking the card on one of the first K reward screens
    helps a run win, net of the character's unchanged cards?

    Loads the treated card's character with wins.load_early once for the window's
    before_builds and once for its after_builds (windows.csv, level = card_patch), or takes
    `data` = (before, after) load_early results. Fits itt, first stage and iv for the
    treated card and every control in each block (block_estimates) and returns
    Strength(blocks, changes, summary):

    blocks   one row per (card, block): estimates, se, first-stage F, weak, n_runs,
             n_offered, n_picked, raw rates, reason (why blank).
    changes  one row per card: {iv,itt,fs}_{before,after,change,change_se,reason}, with
             change_se = sqrt(se_before^2 + se_after^2) (the blocks are different runs,
             checked); then net of controls: {est}_net = change - controls' median change,
             z_raw (change / se, against zero), z_spread (net / controls' scaled MAD),
             z_se (net / sqrt(se^2 + se of the median^2): the card's own noise plus the
             median's, 1.2533 MAD / sqrt(n controls)), z_total (net / sqrt(that^2 + tau^2),
             tau = the controls' spread beyond their own noise). Matched version
             (iv and itt, suffix _m): net of the k_match (20) controls whose first stage
             is closest to the card's, matched in each block separately (_matched):
             net_m, matched_change, z_spread_m, z_se_m, z_total_m, n_matched_before/after
             (controls actually used), fs_matched_before/after (their median first stage).
    summary  one row: the treated card's changes and z's, the controls' median, MAD, tau,
             how many controls have a change and how many were skipped (few offered runs,
             weak first stage, error), controls_share_abs_z_se_gt2 (about 0.05 if the se's
             are right and the controls didn't change), runs per block, and the options.

    A block where the first stage is weak (F < 10) blanks the iv change with a reason
    (weak cards are counted, not dropped silently); itt and fs changes are kept (they don't
    divide by the first stage). A card with fewer than `min_offered` offered runs in a
    block (as in wins.run_all_cards) gets blank changes and the reason.

    The itt change is first stage x effect: it also moves when only the pick rate moves, so
    read it next to fs_change. The iv estimate is the effect for runs that take the card
    when it is offered; after a big buff more runs take it, and the added takers may
    differ from the earlier ones, so an iv change can be a change in who takes the card
    and not only in what the card does. fs_change shows how much the taker group moved.
    A drift that acts per offer on every card alike (e.g. a changed card that shares the
    screens) is common on the itt scale and spread by 1 / first stage on the iv scale, so
    the iv's net of all controls removes it only for cards picked about as often as the
    median control; the matched (_m) columns remove it for cards picked much more or less
    (at the price of the matched controls' own level differences, see _matched).

    balance=True adds balance_check's p-values for the treated card in each block.
    Options (K, include_short_runs, group, pooled_groups, screen_mix) as in wins.itt; they
    and k_match are echoed as columns in every table."""
    w, color = _color(card_patch_id, ref)
    if data is None:
        data = (wins.load_early(con, color, w["before_builds"], K, ref),
                wins.load_early(con, color, w["after_builds"], K, ref))
    before, after = data
    if before.K != K or after.K != K:
        raise ValueError(f"data was loaded with K = {before.K}/{after.K}, not {K}")
    _check_disjoint(before, after)
    cards = _cards(card_patch_id, color, before, after, ref)
    opts = _options(K, min_offered, include_short_runs, group, pooled_groups, screen_mix,
                    k_match)
    fit_kw = dict(min_offered=min_offered, include_short_runs=include_short_runs,
                  group=group, pooled_groups=pooled_groups, screen_mix=screen_mix)
    blocks = {}
    for side, d, builds in (("before", before, w["before_builds"]),
                            ("after", after, w["after_builds"])):
        blocks[side] = _cached_blocks(d, cards, fit_kw, (color, builds),
                                      _cache if _cache is not None else {})
    ch = _differences(blocks["before"], blocks["after"], w["card_id"])
    ch, st = _net_of_controls(ch)
    ch = _matched(ch, blocks["before"], blocks["after"], k_match)
    bal = {}
    if balance:
        for side, d in (("before", before), ("after", after)):
            try:
                b = balance_check(d, w["card_id"], include_short_runs=include_short_runs,
                                  group=group)
                for k in ("p_joint", "p_screens", "max_abs_std_diff"):
                    bal[f"balance_{k}_{side}"] = b[k]
            except Exception as e:
                bal[f"balance_error_{side}"] = f"{type(e).__name__}: {e}"
    meta = dict(card_patch_id=card_patch_id, card_id=w["card_id"], color=color,
                before_builds=w["before_builds"], after_builds=w["after_builds"],
                skipped="")
    summary = pd.DataFrame([dict(_summary(ch, st, bal, meta), **opts)])
    bl = pd.concat([blocks["before"].assign(block="before", builds=w["before_builds"]),
                    blocks["after"].assign(block="after", builds=w["after_builds"])],
                   ignore_index=True)
    bl.insert(0, "treated", bl.card_id == w["card_id"])
    tag = dict(card_patch_id=card_patch_id)
    return Strength(bl.assign(**tag, **opts), ch.assign(**tag, **opts), summary)


def _cached_blocks(data, cards, fit_kw, key, cache):
    """block_estimates for `cards`, reusing rows already fit on the same block data with
    the same options (strength_all shares them between the tweaks of a window)."""
    k = (key, tuple(sorted(fit_kw.items())))
    have = cache.get(k)
    todo = [c for c in cards if have is None or c not in set(have.card_id)]
    if todo:
        new = block_estimates(data, todo, **fit_kw)
        have = new if have is None else pd.concat([have, new], ignore_index=True)
        cache[k] = have
    return have.set_index("card_id").loc[cards].reset_index()


# ------------------------------------------------------------------------------ all tweaks

def strength_all(con, *, tweaks=None, K=wins.K_DEFAULT, min_offered=wins.MIN_OFFERED,
                 include_short_runs=False, group=None, pooled_groups=False,
                 screen_mix=False, k_match=K_MATCH, balance=True, verbose=True, ref=REF):
    """strength_change for every solo-estimable numeric tweak in tweak_sizes.csv (or those
    listed in `tweaks`), one data load per (character, before builds, after builds) and one
    fit per (card, block) shared by the tweaks of that window. Upgrade-only tweaks are not
    estimated: they get a summary row with `skipped` saying so. Returns Strength(blocks,
    changes, summary), every row tagged with card_patch_id and the options; summary also
    carries the tweak_sizes columns. A tweak that fails gets `skipped` = the error.
    save() / load() write and read the three tables as parquet. verbose prints each
    window's elapsed time and number of fits (to check the runtime estimate)."""
    ts = did._csv(pathlib.Path(ref) / "tweak_sizes.csv")
    ts = ts[ts.solo_estimable == "yes"]
    if tweaks is not None:
        ts = ts[ts.card_patch_id.isin(tweaks)]
    opts = _options(K, min_offered, include_short_runs, group, pooled_groups, screen_mix,
                    k_match)
    kw = dict(K=K, min_offered=min_offered, include_short_runs=include_short_runs,
              group=group, pooled_groups=pooled_groups, screen_mix=screen_mix,
              k_match=k_match, balance=balance, ref=ref)
    size_cols = [c for c in ts.columns if c not in ("card_patch_id", "card_id", "color",
                                                   "before_builds", "after_builds")]
    blocks, changes, summary = [], [], []
    for (color, before, after), g in ts.groupby(["color", "before_builds", "after_builds"],
                                                sort=False):
        t0 = time.perf_counter()
        todo = g[g.upgrade_only != "yes"]
        data = None
        if len(todo):
            data = (wins.load_early(con, color, before, K, ref),
                    wins.load_early(con, color, after, K, ref))
        cache = {}
        for t in g.to_dict("records"):
            sizes = {c: t[c] for c in size_cols}
            if t["upgrade_only"] == "yes":
                summary.append(dict(card_patch_id=t["card_patch_id"], card_id=t["card_id"],
                                    color=color, before_builds=before, after_builds=after,
                                    skipped=UPGRADE_ONLY_REASON, **opts, **sizes))
                continue
            try:
                r = strength_change(con, t["card_patch_id"], data=data, _cache=cache, **kw)
            except Exception as e:                  # report and keep going
                err = f"{type(e).__name__}: {' '.join(str(e).split())}"
                summary.append(dict(card_patch_id=t["card_patch_id"], card_id=t["card_id"],
                                    color=color, before_builds=before, after_builds=after,
                                    skipped=err, **opts, **sizes))
                continue
            blocks.append(r.blocks)
            changes.append(r.changes)
            summary.append(dict(r.summary.iloc[0].to_dict(), **sizes))
        if verbose:
            fitted = sum(int((v.reason == "").sum()) for v in cache.values())
            print(f"strength_all: {color} {before} -> {after}: {len(todo)} tweaks, "
                  f"{3 * fitted} fits, {time.perf_counter() - t0:.1f} s", flush=True)
        del data, cache
    cat = lambda xs: pd.concat(xs, ignore_index=True) if xs else pd.DataFrame()
    return Strength(cat(blocks), cat(changes), pd.DataFrame(summary))


# ------------------------------------------------------------------------------ caching

def _tidy(df):
    """Parquet-safe: object columns as text (blank for missing), bools as bools."""
    df = df.copy()
    for c in df.columns:
        if df[c].dtype == object:
            vals = df[c].dropna()
            if len(vals) and vals.map(lambda v: isinstance(v, (bool, np.bool_))).all():
                df[c] = df[c].astype("boolean")
            elif len(vals) and vals.map(lambda v: isinstance(v, (int, float, np.number))
                                        and not isinstance(v, bool)).all():
                df[c] = pd.to_numeric(df[c])
            else:
                df[c] = df[c].fillna("").astype(str)
    return df


def save(res, directory, name):
    """Writes strength_<name>_{blocks,changes,summary}.parquet in `directory`."""
    d = pathlib.Path(directory)
    d.mkdir(parents=True, exist_ok=True)
    for part, df in res._asdict().items():
        _tidy(df).to_parquet(d / f"strength_{name}_{part}.parquet", index=False)


def load(directory, name):
    """Reads what save() wrote, as a Strength."""
    d = pathlib.Path(directory)
    return Strength(*(pd.read_parquet(d / f"strength_{name}_{p}.parquet")
                      for p in Strength._fields))


# ------------------------------------------------------------------------------ balance

def _std_diff(x1, x0):
    v = (np.var(x1, ddof=1) + np.var(x0, ddof=1)) / 2 if len(x1) > 1 and len(x0) > 1 \
        else np.nan
    return float((np.mean(x1) - np.mean(x0)) / np.sqrt(v)) if v > 0 else np.nan


def _chi2_p(level, offered):
    t = pd.crosstab(level, offered)
    t = t.loc[t.sum(axis=1) > 0]
    if t.shape[0] < 2 or t.shape[1] < 2:
        return np.nan
    return float(stats.chi2_contingency(t.to_numpy(), correction=False).pvalue)


def _dummies(s, within=None, min_runs=MIN_LEVEL_RUNS):
    """Indicator columns of `s` for the joint test: one reference level dropped (per
    `within` group if given, so the columns are free of `within`'s own dummies), and levels
    with fewer than `min_runs` runs folded into the reference. A level with a run or two
    fits them exactly (zero residual), which makes the robust variance too small and the
    test reject for no reason."""
    s = s.astype(str)
    key = s if within is None else within.astype(str) + "|" + s
    grp = pd.Series("", index=s.index) if within is None else within.astype(str)
    n = key.map(key.value_counts())
    big = key.where(n >= min_runs)
    ref = big.groupby(grp).transform("min")
    return pd.get_dummies(big.where(big != ref), dtype=float)


def _wald_hc1(y, X, test):
    """OLS of y on X (with an intercept column included), HC1 covariance; Wald chi^2 that
    the `test` columns are all zero. Returns chi2, df, p."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    n, k = X.shape
    XtX_inv = np.linalg.pinv(X.T @ X)
    b = XtX_inv @ X.T @ y
    e = y - X @ b
    meat = (X * e[:, None] ** 2).T @ X
    V = XtX_inv @ meat @ XtX_inv * n / max(n - np.linalg.matrix_rank(X), 1)
    bt, Vt = b[test], V[np.ix_(test, test)]
    df = int(np.linalg.matrix_rank(Vt))
    if df == 0:
        return np.nan, 0, np.nan
    chi2 = float(bt @ np.linalg.pinv(Vt) @ bt)
    return chi2, df, float(stats.chi2.sf(chi2, df))


def balance_check(data, card, *, include_short_runs=False, group=None):
    """Is being offered `card` on the first K screens unrelated to what was fixed before the
    offer? On the runs the fits use (wins.run_frame), offered vs. not-offered runs compared
    on ascension, week, uploader group, build and screen_sources (the first K screens'
    types). Returns a dict:

    table            one row per covariate (and level, for group / build / screen_sources):
                     mean (or share) among offered and not-offered runs, std_diff
                     (difference over the pooled sd; |std_diff| > 0.1 is the usual flag),
                     p_chi2 (chi^2 test of independence of offered and the covariate's
                     levels, one value per covariate).
    p_joint          HC1 Wald test, in a regression of offered on build dummies plus
                     ascension, week-within-build and group-within-build dummies, that the
                     last three are all zero (chi2_joint, df_joint; levels with fewer than
                     20 runs are folded into the reference level). Conditional on build
                     because the fits have build fixed effects: a card's offer rate may
                     differ between builds of a pooled block without harming the design.
    p_build          chi^2 across builds (informative only when the block pools builds).
    p_screens        chi^2 across screen_sources levels (levels with fewer than 20 runs
                     pooled). A rare card fails this when elites offer it more: that is what
                     screen_mix is for, not a failure of the RNG.
    max_abs_std_diff largest |std_diff| over ascension, week, group and build rows;
                     max_abs_std_diff_screens over screen_sources rows.
    """
    d = wins.run_frame(data, card, include_short_runs=include_short_runs, group=group)
    off = d.offered.to_numpy() == 1
    if off.all() or not off.any():
        raise ValueError(f"{card}: offered on {'every' if off.all() else 'no'} run")
    screens = d.screen_sources.astype(str)
    counts = screens.value_counts()
    screens = screens.where(screens.map(counts) >= MIN_LEVEL_RUNS, "other")
    rows = []
    for cov in ("ascension", "week"):
        x = d[cov].astype(float).to_numpy()
        rows.append(dict(covariate=cov, level="(mean)", offered=float(x[off].mean()),
                         not_offered=float(x[~off].mean()),
                         std_diff=_std_diff(x[off], x[~off]),
                         p_chi2=_chi2_p(d[cov].astype(int), off)))
    for cov, s in (("group", d.group.astype(str)), ("build_id", d.build_id.astype(str)),
                   ("screen_sources", screens)):
        p = _chi2_p(s, off)
        for lv in sorted(s.unique()):
            x = (s == lv).to_numpy().astype(float)
            rows.append(dict(covariate=cov, level=lv, offered=float(x[off].mean()),
                             not_offered=float(x[~off].mean()),
                             std_diff=_std_diff(x[off], x[~off]), p_chi2=p))
    table = pd.DataFrame(rows)
    parts = [pd.Series(1.0, index=d.index, name="const").to_frame(),
             _dummies(d.build_id),
             _dummies(d.ascension.astype(int)).add_prefix("asc="),
             _dummies(d.week.astype(int), within=d.build_id).add_prefix("week="),
             _dummies(d.group, within=d.build_id).add_prefix("group=")]
    X = pd.concat(parts, axis=1)
    n_fixed = 1 + parts[1].shape[1]
    chi2, df, p = _wald_hc1(off.astype(float), X.to_numpy(), np.arange(n_fixed, X.shape[1]))
    main = table[table.covariate != "screen_sources"]
    scr = table[table.covariate == "screen_sources"]
    return dict(card_id=card, n_runs=len(d), n_offered=int(off.sum()),
                chi2_joint=chi2, df_joint=df, p_joint=p,
                p_build=float(table.loc[table.covariate == "build_id", "p_chi2"].iloc[0]),
                p_screens=float(scr.p_chi2.iloc[0]) if len(scr) else np.nan,
                max_abs_std_diff=float(main.std_diff.abs().max()),
                max_abs_std_diff_screens=float(scr.std_diff.abs().max()) if len(scr)
                else np.nan,
                table=table)


def balance_all(data, character=None, *, cards=None, min_offered=wins.MIN_OFFERED,
                alpha=BALANCE_ALPHA, include_short_runs=False, group=None, ref=REF):
    """balance_check for every card of the character's color (or `cards`) with at least
    `min_offered` offered runs, and how many fail against what chance gives. Returns a dict:
    cards (one row per card: n_offered, p_joint, p_screens, max_abs_std_diff, fail = p_joint
    < alpha, fail_screens = p_screens < alpha, error), n_cards, n_fail, share_fail,
    n_fail_screens, share_fail_screens, alpha, and p_binom / p_binom_screens (one-sided
    binomial test of that many failures at rate alpha). The cards' tests are not independent
    (they share runs, and a card offered more leaves fewer slots for the others), so the
    binomial p is a guide, not an exact test."""
    if cards is None:
        character = character or str(data.runs.character.iloc[0])
        color = wins._character(character).removeprefix("CHARACTER.").lower()
        cards = sorted(c for c, col in did.card_colors(ref).items() if col == color)
    base = wins.run_frame(data, None, include_short_runs=include_short_runs, group=group)
    o = data.offers[data.offers.run_key.isin(base.run_key)]
    n_off = o.groupby("card_id", observed=True).size()
    rows = []
    for card in cards:
        n = int(n_off.get(card, 0))
        if n < min_offered:
            continue
        row = dict(card_id=card, n_offered=n, error="")
        try:
            b = balance_check(data, card, include_short_runs=include_short_runs,
                              group=group)
            row.update({k: b[k] for k in ("p_joint", "p_screens", "max_abs_std_diff",
                                          "max_abs_std_diff_screens")})
        except Exception as e:
            row["error"] = f"{type(e).__name__}: {e}"
        rows.append(row)
    t = pd.DataFrame(rows).reindex(columns=["card_id", "n_offered", "p_joint", "p_screens",
                                            "max_abs_std_diff", "max_abs_std_diff_screens",
                                            "error"])
    t["fail"] = t.p_joint < alpha
    t["fail_screens"] = t.p_screens < alpha
    ok = t[t.error == ""]
    n, k, ks = len(ok), int(ok.fail.sum()), int(ok.fail_screens.sum())
    binom = lambda x: float(stats.binomtest(x, n, alpha, alternative="greater").pvalue) \
        if n else np.nan
    return dict(cards=t, n_cards=n, n_fail=k, share_fail=k / n if n else np.nan,
                n_fail_screens=ks, share_fail_screens=ks / n if n else np.nan, alpha=alpha,
                p_binom=binom(k), p_binom_screens=binom(ks))
