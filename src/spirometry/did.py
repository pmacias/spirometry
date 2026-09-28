"""Pick-rate difference-in-differences for numeric tweaks (Phase 5). Tables only, no plots.

Reads runs.duckdb's offers_with_version (plus runs, for uploader_hash) through a read-only
DuckDB connection, and the reference CSVs: windows.csv (level = card_patch), builds.csv,
tweak_sizes.csv (spirometry.tweaks) and the cached card list for colors. Every function
returns a pandas DataFrame or a dict.

    con = duckdb.connect("data/runs/runs.duckdb", read_only=True)
    df = load_window(con, "PARRY@v0.103.2/patch")
    offer_rate_check(df, "PARRY@v0.103.2/patch")      # step 1: did the offer share move?
    fit_did(df, "PARRY@v0.103.2/patch")               # step 2: the DiD
    fit_event_study(df, "PARRY@v0.103.2/patch")       # step 2b: gap by week
    run_all(con)                                      # every solo-estimable tweak

Model (linear probability, OLS with absorbed fixed effects, errors clustered by run_key;
heteroskedasticity-robust and iid errors of the same fit alongside, for comparison):

    picked ~ treat_post | card_id^upgraded + card_id^group + block^group + act + ascension

(card_act_fe=True: card_id^upgraded^act in place of card_id^upgraded and act.)
treat_post = offer of the treated card in the after block. The treated card and its
controls (same color, unchanged in the window) are the only cards in the fit.
"""
import json, pathlib, warnings

import numpy as np
import pandas as pd
import pyfixest as pf

REF = pathlib.Path("reference")
CLUSTER = "run_key"
SINGLETON_WARNING = r".*singleton fixed effect"
WEEK = 7 * 24 * 3600
MIN_RARITY_CONTROLS = 5         # offer_rate_check: fewer same-rarity controls -> all controls


# ------------------------------------------------------------------------------ reference

def _csv(path):
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def window(card_patch_id, ref=REF):
    """The card-patch's row in windows.csv, as a dict."""
    w = _csv(pathlib.Path(ref) / "windows.csv")
    w = w[(w.level == "card_patch") & (w.event_id == card_patch_id)]
    if w.empty:
        raise KeyError(f"{card_patch_id} is not a card_patch window in windows.csv")
    return w.iloc[0].to_dict()


def card_colors(ref=REF):
    """card_id -> color from the cached card list (the one spirometry.treatment reads),
    plus card_changes.csv's color for cards not in it."""
    ref = pathlib.Path(ref)
    colors = {c["id"]: c.get("color") or "" for c in
              json.loads((ref / "raw" / "cards.json").read_bytes())}
    for r in _csv(ref / "card_changes.csv").itertuples():
        if r.color:
            colors.setdefault(r.card_id, r.color)
    return colors


def card_rarities(ref=REF):
    """card_id -> rarity ('Common', 'Uncommon', 'Rare', ...) from the cached card list,
    plus card_changes.csv's rarity for cards not in it. This is the card's rarity now, not
    at the time of a window: 4 card-patches changed a card's rarity."""
    ref = pathlib.Path(ref)
    rar = {c["id"]: c.get("rarity") or "" for c in
           json.loads((ref / "raw" / "cards.json").read_bytes())}
    for r in _csv(ref / "card_changes.csv").itertuples():
        if getattr(r, "rarity", ""):
            rar.setdefault(r.card_id, r.rarity)
    return rar


def release_date(build_id, ref=REF):
    b = _csv(pathlib.Path(ref) / "builds.csv").set_index("build_id")
    d = b.release_date.get(build_id, "")
    if not d:
        raise ValueError(f"{build_id} has no release_date in builds.csv")
    return pd.Timestamp(d)


# ------------------------------------------------------------------------------ data

LOAD_SQL = """
SELECT o.run_key, o.card_id, o.build_id, o.picked, o.upgraded, o.act, o.ascension,
       o.uploader_tag IS NOT NULL AS tagged,
       o.run_key || '|' || o.floor || '|' || coalesce(o.set_idx::VARCHAR, 'list') AS screen_id,
       o.start_time, r.uploader_hash, o.set_picked_any{extra}
FROM offers_with_version o JOIN runs r USING (run_hash)
WHERE o.character = ? AND list_contains(?, o.build_id) AND list_contains(?, o.card_id)
"""
CATEGORICAL = ["run_key", "card_id", "build_id", "block", "group", "screen_id",
               "uploader_hash"]
COLUMNS = ["run_key", "card_id", "block", "picked", "upgraded", "act", "ascension", "group",
           "screen_id", "start_time", "week", "build_id", "uploader_hash", "set_picked_any"]
# load_window(extra_cols=True): where the offers come from
EXTRA_COLUMNS = ["source", "map_point_type", "floor", "event_fight", "list_len", "set_idx"]


def load_block_data(con, color, before_builds, after_builds, ref=REF, extra_cols=False):
    """Offers of one character's cards on the given builds. See load_window."""
    before, after = before_builds.split(), after_builds.split()
    cards = sorted(c for c, col in card_colors(ref).items() if col == color)
    extra = "".join(f", o.{c}" for c in EXTRA_COLUMNS) if extra_cols else ""
    df = con.execute(LOAD_SQL.format(extra=extra),
                     [f"CHARACTER.{color.upper()}", before + after, cards]).df()
    df["block"] = np.where(df.build_id.isin(after), "after", "before")
    df["group"] = np.where(df.pop("tagged"), "tagged", "untagged")
    t0 = release_date(after[0], ref)
    df["week"] = np.floor((df.start_time - t0).dt.total_seconds() / WEEK).astype("int16")
    df["picked"] = df.picked.astype(bool)
    df["upgraded"] = df.upgraded.astype(bool)
    df["act"] = df.act.astype("int8")
    df["ascension"] = df.ascension.astype("Int16")
    df["set_picked_any"] = df.set_picked_any.astype("boolean")
    for c in CATEGORICAL:
        df[c] = df[c].astype("category")
    if extra_cols:
        for c in ("source", "map_point_type"):
            df[c] = df[c].astype("category")
        df["floor"] = df.floor.astype("int16")
        df["event_fight"] = df.event_fight.astype(bool)
        df["list_len"] = df.list_len.astype("int16")
        df["set_idx"] = df.set_idx.astype("Int16")
    return df[COLUMNS + (EXTRA_COLUMNS if extra_cols else [])]


def load_window(con, card_patch_id, ref=REF, extra_cols=False):
    """Offers in a card-patch's window: the treated card's character (the player's
    `character` maps to the card's color, CHARACTER.IRONCLAD -> ironclad), cards of that
    color only, on the window's before_builds + after_builds (pooled blocks).

    Columns: run_key, card_id, block ('before'/'after'), picked, upgraded, act, ascension,
    group ('tagged' when the record has an _sts uploader tag), screen_id (run_key|floor|
    set_idx, or run_key|floor|list when set_idx is NULL), start_time, week (whole weeks
    from the first after-build's release date, negative before), build_id, uploader_hash,
    set_picked_any (the player took a card on the offer's screen; NA when the list couldn't
    be split into screens; fit_did's picked_screens_only uses it).

    extra_cols=True adds where each offer comes from: source (combat, elite, boss,
    event_combat), map_point_type, floor, event_fight, list_len (cards in the floor's list)
    and set_idx (the screen within it; NA when the list couldn't be split).

    Offers come from primary_offers, which keeps one record per run_key (the copy
    runs_dedup keeps, first by page and line). So a run uploaded both with and without the
    SlayTheStats tag gets the group of whichever copy was downloaded first."""
    w = window(card_patch_id, ref)
    color = card_colors(ref).get(w["card_id"], "")
    if not color:
        raise ValueError(f"{w['card_id']} has no color in the card list")
    return load_block_data(con, color, w["before_builds"], w["after_builds"], ref,
                           extra_cols=extra_cols)


def control_cards(card_patch_id, drop_behavior_flags=False, *, df=None, ref=REF):
    """Unchanged same-color cards: every card of the treated card's color seen in the
    window (in df when given, else in the cached card list), minus the treated card, minus
    control_exclusions, minus control_behavior_flags when asked."""
    w = window(card_patch_id, ref)
    if df is not None:
        seen = set(df.card_id[df.card_id.notna()].unique())
    else:
        color = card_colors(ref).get(w["card_id"])
        seen = {c for c, col in card_colors(ref).items() if col == color}
    drop = {w["card_id"], *w["control_exclusions"].split()}
    if drop_behavior_flags:
        drop |= set(w["control_behavior_flags"].split())
    return sorted(seen - drop)


# ------------------------------------------------------------------------------ step 1

def offer_rate_check(df, card_patch_id, ref=REF):
    """Offer share per card (treated + controls): offers before/after, share of all the
    character's offers in df before/after, log share ratio (after/before).

    z_spread: the log ratio against the controls' spread (median, and MAD scaled by 1.4826
    to match a normal sd). z_binom: the log ratio minus the controls' median, over its
    binomial standard error sqrt((1 - s_a)/n_a + (1 - s_b)/n_b). Shares sum to one, so a
    card whose share doubles pulls every other share down: measuring against the controls'
    median instead of zero keeps that from flagging them all. flag: both |z| > 3.
    Computed for every row; the treated card's row is the check.

    rarity: the card's rarity in the cached card list, i.e. now, not necessarily during the
    window (4 card-patches changed a card's rarity). z_spread_rarity, z_binom_rarity,
    flag_rarity: the same statistics against the median and MAD of the controls of the
    card's own rarity (controls_median_rarity, controls_mad_rarity, n_controls_rarity), so a
    change in one rarity's pool, which moves every card of that rarity, doesn't flag them.
    When a rarity has fewer than 5 controls with a log ratio (or the card has no rarity),
    the row falls back to all controls and rarity_note says so."""
    w = window(card_patch_id, ref)
    treated = w["card_id"]
    cards = [treated] + control_cards(card_patch_id, df=df, ref=ref)
    tot = df.groupby("block", observed=True).size()
    n = (df[df.card_id.isin(cards)].groupby(["card_id", "block"], observed=True).size()
         .unstack("block").reindex(index=cards, columns=["before", "after"]).fillna(0))
    out = pd.DataFrame({"card_id": cards, "treated": [c == treated for c in cards],
                        "offers_before": n.before.to_numpy().astype(int),
                        "offers_after": n.after.to_numpy().astype(int)})
    out["share_before"] = out.offers_before / tot.get("before", np.nan)
    out["share_after"] = out.offers_after / tot.get("after", np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        out["log_share_ratio"] = np.log(out.share_after / out.share_before)
        se = np.sqrt((1 - out.share_after) / out.offers_after
                     + (1 - out.share_before) / out.offers_before)
    out.loc[~np.isfinite(out.log_share_ratio), "log_share_ratio"] = np.nan
    ctrl = out.log_share_ratio[~out.treated].dropna()
    med = ctrl.median()
    mad = 1.4826 * (ctrl - med).abs().median()
    out["controls_median"], out["controls_mad"] = med, mad
    out["z_spread"] = (out.log_share_ratio - med) / mad if mad > 0 else np.nan
    out["z_binom"] = (out.log_share_ratio - med) / se
    out["flag"] = (out.z_spread.abs() > 3) & (out.z_binom.abs() > 3)

    out["rarity"] = out.card_id.map(card_rarities(ref)).fillna("")
    lr = out.log_share_ratio.where(~out.treated)
    stats = {}
    for r in out.rarity.unique():
        c = lr[out.rarity == r].dropna()
        if r and len(c) >= MIN_RARITY_CONTROLS:
            m = c.median()
            stats[r] = (m, 1.4826 * (c - m).abs().median(), len(c), "")
        else:
            stats[r] = (med, mad, len(ctrl),
                        f"{len(c)} {r or 'no-rarity'} controls (< {MIN_RARITY_CONTROLS}): "
                        "all controls used")
    st = pd.DataFrame([stats[r] for r in out.rarity], index=out.index,
                      columns=["controls_median_rarity", "controls_mad_rarity",
                               "n_controls_rarity", "rarity_note"])
    out = pd.concat([out, st], axis=1)
    dev = out.log_share_ratio - out.controls_median_rarity
    with np.errstate(divide="ignore", invalid="ignore"):
        out["z_spread_rarity"] = np.where(out.controls_mad_rarity > 0,
                                          dev / out.controls_mad_rarity, np.nan)
    out["z_binom_rarity"] = dev / se
    out["flag_rarity"] = (out.z_spread_rarity.abs() > 3) & (out.z_binom_rarity.abs() > 3)
    return out


# ------------------------------------------------------------------------------ step 2

def _subset(df, card_patch_id, *, upgraded=None, group=None, drop_shared_screens=False,
            drop_behavior_flags=False, drop_uploaders=None, max_week_after=None,
            picked_screens_only=False, ref=REF):
    """Treated card + controls, with the fit options applied. Returns (data, treated)."""
    treated = window(card_patch_id, ref)["card_id"]
    cards = [treated] + control_cards(card_patch_id, drop_behavior_flags, df=df, ref=ref)
    d = df[df.card_id.isin(cards)]
    if drop_shared_screens:                     # screens as offered, before other filters
        shared = d.screen_id[d.card_id == treated].unique()
        d = d[(d.card_id == treated) | ~d.screen_id.isin(shared)]
    if picked_screens_only:                     # unsplit lists (NA) leave too
        d = d[d.set_picked_any.fillna(False).astype(bool)]
    if upgraded is not None:
        d = d[d.upgraded == upgraded]
    if group is not None:
        d = d[d.group == group]
    if drop_uploaders:
        d = d[~d.uploader_hash.isin(drop_uploaders)]
    if max_week_after is not None:              # fixed horizon: the before block is kept
        d = d[(d.block != "after") | (d.week <= max_week_after)]
    d = d.dropna(subset=["ascension"]).copy()
    for c in d.columns:
        if isinstance(d[c].dtype, pd.CategoricalDtype):
            d[c] = d[c].cat.remove_unused_categories()
    d["is_treated"] = (d.card_id == treated).to_numpy()
    d["after"] = (d.block == "after").to_numpy()
    d["treat_post"] = (d.is_treated & d.after).astype("int8")
    d["picked"] = d.picked.astype("int8")
    d["upg"] = d.upgraded.astype("int8")
    d["asc"] = d.ascension.astype("int16")
    if d.empty or not d.is_treated.any():
        raise ValueError(f"{card_patch_id}: no offers of {treated} after the filters")
    for who, rows in (("treated", d.is_treated), ("control", ~d.is_treated)):
        for blk, flag in (("before", False), ("after", True)):
            if not (rows & (d.after == flag)).any():
                raise ValueError(f"{card_patch_id}: no {who} offers in the {blk} block "
                                 "after the filters")
    return d, treated


def _fixed_effects(d, group, pooled_groups, block_term="block", card_act_fe=False):
    two_groups = group is None and not pooled_groups and d.group.nunique() > 1
    fe = ["card_id^upg^act" if card_act_fe else "card_id^upg"]
    fe += ["card_id^group", f"{block_term}^group"] if two_groups else [block_term]
    return fe + (["asc"] if card_act_fe else ["act", "asc"])


def _feols(fml, d):
    """pyfixest feols, errors clustered by run_key. Singleton fixed-effect cells (one
    offer) are dropped, pyfixest's default; fit_did reports how many."""
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=SINGLETON_WARNING)
        return pf.feols(fml, data=d, vcov={"CRV1": CLUSTER})


def _rates(d):
    r = d.groupby(["is_treated", "after"]).picked.mean()
    get = lambda t, a: float(r.get((t, a), np.nan))
    return dict(treated_rate_before=get(True, False), treated_rate_after=get(True, True),
                control_rate_before=get(False, False), control_rate_after=get(False, True))


def fit_did(df, card_patch_id, *, upgraded=None, group=None, drop_shared_screens=False,
            drop_behavior_flags=False, drop_uploaders=None, pooled_groups=False,
            max_week_after=None, card_act_fe=False, picked_screens_only=False, ref=REF):
    """One DiD for one card-patch. Returns beta (pick probability, in probability units),
    se (clustered by run_key, the main error; ci95 uses it), se_hc (the same fit with
    heteroskedasticity-robust errors, pyfixest's "hetero": the fair comparison for the
    clustering, since a 0/1 outcome's variance p(1-p) differs between cards), se_iid (iid
    errors, one variance for every offer), ci95, n_offers (used in the fit, after pyfixest
    drops singleton fixed-effect cells; n_singletons_dropped counts them), n_runs and
    n_treated_offers (before that drop), the treated and control pick rates before/after,
    and the formula.

    upgraded=True/False: fit on upgraded (or un-upgraded) offers only; upgrade-only tweaks
      are estimated on upgraded offers and their un-upgraded offers are a placebo.
    group='tagged'/'untagged': within one uploader group (the ^group terms drop out).
    pooled_groups=True: no group terms at all (robustness: how much the adjustment matters).
    drop_shared_screens: drop control offers from screens that also held the treated card
      (competition on the screen).
    drop_behavior_flags: drop controls with a bug-fix behavior event in the window.
    drop_uploaders: uploader_hash values to drop (heavy-uploader check).
    max_week_after: fixed horizon; keep only after-block offers with week <= max_week_after
      (week as load_window defines it, 0 = the first after-build's release week), so
      patches with after periods of different length compare at the same horizon. The
      before block is unchanged. Reported back as max_week_after, with after_week_max, the
      latest after-block week in the fit data (before the singleton drop).
    card_act_fe: card_id^upg^act in place of card_id^upg (and the act term, now nested in
      it): each card gets its own act profile, for cards whose value depends on when in the
      run they're offered. A robustness check.
    picked_screens_only: keep only offers on screens where the player took a card
      (set_picked_any; offers from lists that couldn't be split into screens leave too).
      Most of the fall in pick rate through a run is whether to take a card at all, so this
      estimand is the choice among cards, free of that. Applied after drop_shared_screens
      (which sees screens as offered) and before the other filters.

    Ascension enters as one fixed effect per level. If group has one level in the data
    (e.g. no tagged runs), the group terms are dropped automatically."""
    d, treated = _subset(df, card_patch_id, upgraded=upgraded, group=group,
                         drop_shared_screens=drop_shared_screens,
                         drop_behavior_flags=drop_behavior_flags,
                         drop_uploaders=drop_uploaders, max_week_after=max_week_after,
                         picked_screens_only=picked_screens_only, ref=ref)
    fml = "picked ~ treat_post | " + " + ".join(
        _fixed_effects(d, group, pooled_groups, card_act_fe=card_act_fe))
    fit = _feols(fml, d)
    beta, se = float(fit.coef()["treat_post"]), float(fit.se()["treat_post"])
    ci = fit.confint().loc["treat_post"].to_numpy(dtype=float)
    # fit.vcov() recomputes the errors in place: read the clustered ones first
    se_hc = float(fit.vcov("hetero").se()["treat_post"])
    se_iid = float(fit.vcov("iid").se()["treat_post"])
    return dict(card_patch_id=card_patch_id, card_id=treated, beta=beta, se=se,
                ci95=(float(ci[0]), float(ci[1])), se_hc=se_hc, se_iid=se_iid,
                max_week_after=max_week_after, card_act_fe=card_act_fe,
                picked_screens_only=picked_screens_only,
                after_week_max=int(d.week[d.after].max()),
                n_offers=int(fit._N),
                n_singletons_dropped=len(d) - int(fit._N),
                n_runs=int(d.run_key.nunique()), n_treated_offers=int(d.is_treated.sum()),
                **_rates(d), formula=fml)


def fit_event_study(df, card_patch_id, weeks=(-6, 8), ref_week=-1, *, upgraded=None,
                    group=None, pooled_groups=False, ref=REF):
    """The treated card's gap to the controls by (week, block) cell. Weeks outside `weeks`
    are binned into the end weeks. Same fixed effects as fit_did, with week^block^group in
    place of block^group, plus one dummy per treated (week, block) cell; the before-block
    `ref_week` cell is the omitted reference (its row is absent). Before-build offers played
    after the release date are their own cells (block 'before', week >= 0), not dropped.
    Returns one row per cell: week, block, coef, se (clustered by run_key), n_offers."""
    d, treated = _subset(df, card_patch_id, upgraded=upgraded, group=group, ref=ref)
    lo, hi = weeks
    d["wk"] = d.week.clip(lo, hi).astype("int16")
    d["wkblock"] = (d.wk.astype(str) + "_" + d.block.astype(str)).astype("category")
    cells = (d[d.is_treated].groupby(["wk", "block"], observed=True).size()
             .rename("n_offers").reset_index())
    is_ref = (cells.wk == ref_week) & (cells.block == "before")
    if not is_ref.any():
        raise ValueError(f"{card_patch_id}: no treated offers in the reference cell "
                         f"(week {ref_week}, before)")
    cells = cells[~is_ref].reset_index(drop=True)
    names = []
    for w, b in zip(cells.wk, cells.block):
        name = f"es_{b}_{'m' if w < 0 else 'p'}{abs(w)}"
        d[name] = (d.is_treated & (d.wk == w) & (d.block == b)).astype("int8")
        names.append(name)
    fe = _fixed_effects(d, group, pooled_groups, block_term="wkblock")
    fml = "picked ~ " + " + ".join(names) + " | " + " + ".join(fe)
    fit = _feols(fml, d)
    coef, se = fit.coef(), fit.se()
    cells["coef"] = [float(coef.get(n, np.nan)) for n in names]
    cells["se"] = [float(se.get(n, np.nan)) for n in names]
    cells = cells.rename(columns={"wk": "week"})
    cells["formula"] = fml.split(" | ")[0].split(" ~ ")[0] + " ~ treated x (week, block) | " \
        + " + ".join(fe)
    return cells[["week", "block", "coef", "se", "n_offers", "formula"]]


def to_log_odds(beta, se, p_before):
    """Delta-method conversion of a probability-scale effect to log-odds:
    beta / (p (1 - p)), se / (p (1 - p)), p = the treated card's pick rate before. An
    approximation, good when beta is small next to p and 1 - p; it is not the coefficient a
    logit would give."""
    k = p_before * (1 - p_before)
    if not k > 0:
        return float("nan"), float("nan")
    return beta / k, se / k


# ------------------------------------------------------------------------------ all tweaks

PLACEBO_KEYS = ["beta", "se", "n_offers", "treated_rate_before"]


def run_all(con, *, tweaks=None, ref=REF, **fit_kwargs):
    """fit_did for every solo-estimable tweak in tweak_sizes.csv (or those listed in
    `tweaks`), joined to its tweak_sizes columns, for the dose-response plot. Loads each
    window's character data once. Upgrade-only tweaks are fit on upgraded offers; their
    un-upgraded offers are fit as a placebo (placebo_* columns). beta_lo / se_lo are the
    log-odds versions (to_log_odds with the treated card's pick rate before). A tweak whose
    fit fails (e.g. no offers in a block) gets the reason in `error` (placebo_error for the
    placebo) and blank estimates; the others still run. `fit_kwargs` go to fit_did (both
    the main and the placebo fit), e.g. max_week_after=3 for fixed-horizon estimates,
    card_act_fe=True or picked_screens_only=True."""
    ts = _csv(pathlib.Path(ref) / "tweak_sizes.csv")
    ts = ts[ts.solo_estimable == "yes"]
    if tweaks is not None:
        ts = ts[ts.card_patch_id.isin(tweaks)]
    rows = []
    for (color, before, after), g in ts.groupby(["color", "before_builds", "after_builds"],
                                                sort=False):
        df = load_block_data(con, color, before, after, ref)
        for t in g.to_dict("records"):
            up_only = t["upgrade_only"] == "yes"
            row = dict(t, fit_on="upgraded offers" if up_only else "all offers", error="",
                       placebo_error="")
            try:
                kw = dict(fit_kwargs, upgraded=True) if up_only else fit_kwargs
                res = fit_did(df, t["card_patch_id"], ref=ref, **kw)
                res.pop("card_id")
                row.update(res)
                row["beta_lo"], row["se_lo"] = to_log_odds(res["beta"], res["se"],
                                                           res["treated_rate_before"])
            except Exception as e:                  # report and keep going
                row["error"] = f"{type(e).__name__}: {e}"
            if up_only:
                try:
                    p = fit_did(df, t["card_patch_id"], ref=ref,
                                **dict(fit_kwargs, upgraded=False))
                    row.update({f"placebo_{k}": p[k] for k in PLACEBO_KEYS})
                except Exception as e:
                    row["placebo_error"] = f"{type(e).__name__}: {e}"
            rows.append(row)
        del df
    out = pd.DataFrame(rows)
    extra = ["beta_lo", "se_lo"] + [f"placebo_{k}" for k in PLACEBO_KEYS]
    return out.reindex(columns=list(out.columns) + [c for c in extra if c not in out])
