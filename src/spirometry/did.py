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
    placebo = placebo_all(con)                        # SE calibration on unchanged cards
    placebo_summary(placebo, dedupe=True)             # z spread, one row per (window, card)
    placebo_vs_real(run_all(con), placebo)            # each tweak against its window's placebos

Model (linear probability, OLS with absorbed fixed effects, errors clustered by run_key;
heteroskedasticity-robust and iid errors of the same fit alongside, for comparison):

    picked ~ treat_post | card_id^upgraded + card_id^group + block^group + act + ascension

(card_act_fe=True: card_id^upgraded^act in place of card_id^upgraded and act.)
treat_post = offer of the treated card in the after block. The treated card and its
controls are the only cards in the fit. Controls are unchanged cards seen in the window;
control_scope picks which ones: "color" (default: the treated card's color, from its
character's runs), "all" (every character's cards, each from its own character's runs) or
"other" (the other characters' cards only). See control_cards.
"""
import json, pathlib, warnings, zlib

import numpy as np
import pandas as pd
import pyfixest as pf

REF = pathlib.Path("reference")
CLUSTER = "run_key"
SINGLETON_WARNING = r".*singleton fixed effect"
WEEK = 7 * 24 * 3600
MIN_RARITY_CONTROLS = 5         # offer_rate_check: fewer same-rarity controls -> all controls
CONTROL_SCOPES = ("color", "all", "other")
# the five characters (runs.VANILLA_CHARACTERS): a character card's color is its character
CHARACTER_COLORS = ("defect", "ironclad", "necrobinder", "regent", "silent")


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


def _check_scope(control_scope):
    if control_scope not in CONTROL_SCOPES:
        raise ValueError(f"control_scope must be one of {CONTROL_SCOPES}, "
                         f"not {control_scope!r}")


def scope_colors(color, control_scope="color"):
    """The card colors a control scope draws controls from, for a treated card of `color`:
    "color" {color}; "all" the five character colors; "other" the four besides `color`.
    Colorless (and token, status, curse, event) cards are in no scope: see control_cards."""
    _check_scope(control_scope)
    if control_scope == "color":
        return {color}
    others = set(CHARACTER_COLORS) - {color}
    return others | {color} if control_scope == "all" else others


def _unknown_behavior(note):
    """Behavior event ids a card_versions.csv note says a build may carry."""
    for part in note.split("; "):
        if part.startswith("may carry behavior "):
            return set(part[len("may carry behavior "):].split())
    return set()


def window_changes(before_builds, after_builds, ref=REF):
    """Cards of every color that changed between two blocks, from card_versions.csv, by the
    rule spirometry.treatment uses for windows.csv's control_exclusions and
    control_behavior_flags (which cover the treated card's color only). Returns
    (changed, behavior_flagged), two sets of card_id:

    changed: the card's carried card events (event_ids) differ between the before and the
      after builds (each block's union), or its version is unknown (blank) on a build of
      the window, or it has no row for one of them.
    behavior_flagged: a bug-fix behavior event (behavior_event_ids, from
      behavior_changes.csv through change_events.csv) appears after the window's first
      build, or a build after the first may carry one (the note's "may carry behavior").

    For the treated card's color these give windows.csv's two columns (checked on the
    real reference tables in tests/test_did.py)."""
    before, after = before_builds.split(), after_builds.split()
    builds = before + after
    cv = _csv(pathlib.Path(ref) / "card_versions.csv")
    cv = cv[cv.build_id.isin(builds)]
    changed, flagged = set(), set()
    for card, g in cv.groupby("card_id", sort=False):
        rows = {r.build_id: r for r in g.itertuples()}
        if any(b not in rows or rows[b].version == "" for b in builds):
            changed.add(card)
        else:
            ev = lambda blk: set().union(*(set(rows[b].event_ids.split()) for b in blk))
            if ev(before) != ev(after):
                changed.add(card)
        if not before or not all(b in rows for b in builds):
            continue
        start = set(rows[builds[0]].behavior_event_ids.split())
        for b in builds[1:]:
            if (set(rows[b].behavior_event_ids.split()) - start
                    or _unknown_behavior(rows[b].note)):
                flagged.add(card)
                break
    return changed, flagged


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
# control_scope "all" / "other": (character, card) pairs, each card from its own character
LOAD_SQL_PAIRS = """
SELECT o.run_key, o.card_id, o.build_id, o.picked, o.upgraded, o.act, o.ascension,
       o.uploader_tag IS NOT NULL AS tagged,
       o.run_key || '|' || o.floor || '|' || coalesce(o.set_idx::VARCHAR, 'list') AS screen_id,
       o.start_time, r.uploader_hash, o.set_picked_any{extra}
FROM offers_with_version o JOIN runs r USING (run_hash)
JOIN (SELECT unnest(?::VARCHAR[]) AS k_character, unnest(?::VARCHAR[]) AS k_card) k
  ON o.character = k.k_character AND o.card_id = k.k_card
WHERE list_contains(?, o.build_id)
"""
CATEGORICAL = ["run_key", "card_id", "build_id", "block", "group", "screen_id",
               "uploader_hash"]
COLUMNS = ["run_key", "card_id", "block", "picked", "upgraded", "act", "ascension", "group",
           "screen_id", "start_time", "week", "build_id", "uploader_hash", "set_picked_any"]
# load_window(extra_cols=True): where the offers come from
EXTRA_COLUMNS = ["source", "map_point_type", "floor", "event_fight", "list_len", "set_idx"]


def _character(color):
    return f"CHARACTER.{color.upper()}"


def _load_offers(con, color, builds, ref=REF, extra_cols=False, pairs=None):
    """Offers of one character's cards on the given builds, without block and week.
    pairs: (color, card_id) pairs to load instead, each card from its color's character."""
    extra = "".join(f", o.{c}" for c in EXTRA_COLUMNS) if extra_cols else ""
    if pairs is None:
        cards = sorted(c for c, col in card_colors(ref).items() if col == color)
        df = con.execute(LOAD_SQL.format(extra=extra),
                         [_character(color), list(builds), cards]).df()
    else:
        pairs = sorted(pairs)
        df = con.execute(LOAD_SQL_PAIRS.format(extra=extra),
                         [[_character(col) for col, _ in pairs], [c for _, c in pairs],
                          list(builds)]).df()
    df["group"] = np.where(df.pop("tagged"), "tagged", "untagged")
    return df


def _scope_pairs(color, before_builds, after_builds, control_scope, ref=REF):
    """(color, card_id) pairs a wide scope's data need: the other scope colors' cards
    unchanged between the blocks (window_changes), plus, for the treated color, every card
    ("all": as control_scope="color" loads) or only the changed ones ("other": the
    possible treated cards; its unchanged cards are never controls there)."""
    changed, _ = window_changes(before_builds, after_builds, ref)
    pool = scope_colors(color, control_scope)
    out = []
    for c, col in card_colors(ref).items():
        if col == color:
            if control_scope == "all" or c in changed:
                out.append((col, c))
        elif col in pool and c not in changed:
            out.append((col, c))
    return out


def load_block_data(con, color, before_builds, after_builds, ref=REF, extra_cols=False,
                    control_scope="color"):
    """Offers of one character's cards on the given builds. See load_window.

    control_scope="color" (default): the character's own cards, as always. "all" / "other":
    also the other characters' cards that are unchanged between the blocks
    (window_changes), each from its own character's runs; cards changed in another color
    are never loaded, since they can't be controls. "other" loads only the changed cards of
    `color` (the possible treated cards), not its unchanged ones. The filtering happens in
    the DuckDB query, so only rows a fit can use reach pandas."""
    _check_scope(control_scope)
    before, after = before_builds.split(), after_builds.split()
    pairs = (None if control_scope == "color" else
             _scope_pairs(color, before_builds, after_builds, control_scope, ref))
    df = _load_offers(con, color, before + after, ref, extra_cols, pairs)
    df["block"] = np.where(df.build_id.isin(after), "after", "before")
    t0 = release_date(after[0], ref)
    df["week"] = np.floor((df.start_time - t0).dt.total_seconds() / WEEK).astype("int16")
    return _finish(df, extra_cols)


def _finish(df, extra_cols=False):
    """Types and column order shared by the loaders."""
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


def load_window(con, card_patch_id, ref=REF, extra_cols=False, control_scope="color"):
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
    SlayTheStats tag gets the group of whichever copy was downloaded first.

    control_scope "all" / "other" adds the other characters' unchanged cards (see
    load_block_data); the columns are the same."""
    w = window(card_patch_id, ref)
    color = card_colors(ref).get(w["card_id"], "")
    if not color:
        raise ValueError(f"{w['card_id']} has no color in the card list")
    return load_block_data(con, color, w["before_builds"], w["after_builds"], ref,
                           extra_cols=extra_cols, control_scope=control_scope)


def control_cards(card_patch_id, drop_behavior_flags=False, *, df=None, ref=REF,
                  control_scope="color"):
    """Unchanged cards in the control scope: every card of the scope's colors seen in the
    window (in df when given, else in the cached card list), minus the treated card, minus
    cards changed between the blocks, minus bug-fix-flagged cards when asked.

    control_scope:
      "color" (default): the treated card's color, minus windows.csv's control_exclusions
        (and control_behavior_flags). The original definition, unchanged.
      "all": the five character colors (CHARACTER_COLORS), the treated color included.
      "other": the four character colors other than the treated card's.
    For "all" and "other", the changed and flagged cards of every color come from
    window_changes (card_versions.csv, by the rule windows.csv uses for its same-color
    columns), joined with windows.csv's columns.

    Colorless cards (and token, status, curse, event, quest cards) are controls under no
    scope. Under "color" they never were (the treated character's cards only), and keeping
    them out of the others too means the scopes differ only in which characters' cards they
    add: "all" is "color" plus "other". They are offered to every character, so under
    "other" they would bring the treated character's own runs (and its players and screens)
    back into a group meant to have none; and they barely appear in the reward offers the
    fit uses (shop, events and ancients are their sources). Cards a character is offered
    from another color's pool are likewise not loaded: each card's offers come from its own
    character's runs.

    With df, cards outside the scope's colors are ignored (a no-op on the data
    load_window loads for the same scope; it lets "color" fit on wider data)."""
    w = window(card_patch_id, ref)
    colors = card_colors(ref)
    pool = scope_colors(colors.get(w["card_id"], ""), control_scope)
    if df is not None:
        seen = {c for c in df.card_id[df.card_id.notna()].unique()
                if colors.get(c, "") in pool}
    else:
        seen = {c for c, col in colors.items() if col in pool}
    drop = {w["card_id"], *w["control_exclusions"].split()}
    flags = set(w["control_behavior_flags"].split())
    if control_scope != "color":
        changed, flagged = window_changes(w["before_builds"], w["after_builds"], ref)
        drop |= changed
        flags |= flagged
    if drop_behavior_flags:
        drop |= flags
    return sorted(seen - drop)


# ------------------------------------------------------------------------------ step 1

def offer_rate_check(df, card_patch_id, ref=REF):
    """Offer share per card (treated + controls): offers before/after, share of all the
    character's offers in df before/after, log share ratio (after/before).

    z_spread: the log ratio against the controls' spread (median, and MAD scaled by 1.4826
    to match a normal sd). z_binom: the log ratio minus the controls' median, over its
    binomial standard error sqrt((1 - s_a)/n_a + (1 - s_b)/n_b). Shares are of the offers
    of the treated card's color (all of df's offers on load_window's default data; data
    loaded with a wider control_scope give the same table). Shares sum to one, so a
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
    colors = card_colors(ref)
    own = (df.card_id.astype(object).map(colors) == colors.get(treated)).to_numpy()
    tot = df[own].groupby("block", observed=True).size()
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
            picked_screens_only=False, control_scope="color", pseudo=None, ref=REF):
    """Treated card + controls, with the fit options applied. Returns (data, treated).
    pseudo: an unchanged card of the window's color (a control under control_scope="color")
    fit as the treated card instead (placebo_fit); it leaves the controls, and the real
    treated card is not in the data at all (control_cards never returns it)."""
    treated = window(card_patch_id, ref)["card_id"]
    controls = control_cards(card_patch_id, drop_behavior_flags, df=df, ref=ref,
                             control_scope=control_scope)
    if pseudo is not None:
        if pseudo not in control_cards(card_patch_id, drop_behavior_flags, df=df, ref=ref):
            raise ValueError(f"{card_patch_id}: {pseudo} is not an unchanged card of the "
                             "window's color with offers (control_cards, control_scope="
                             "'color')")
        treated, controls = pseudo, [c for c in controls if c != pseudo]
    cards = [treated] + controls
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
            max_week_after=None, card_act_fe=False, picked_screens_only=False,
            control_scope="color", ref=REF):
    """One DiD for one card-patch. Returns beta (pick probability, in probability units),
    se (clustered by run_key, the main error; ci95 uses it), se_hc (the same fit with
    heteroskedasticity-robust errors, pyfixest's "hetero": the fair comparison for the
    clustering, since a 0/1 outcome's variance p(1-p) differs between cards), se_iid (iid
    errors, one variance for every offer), ci95, n_offers (used in the fit, after pyfixest
    drops singleton fixed-effect cells; n_singletons_dropped counts them), n_runs and
    n_treated_offers (before that drop), the treated and control pick rates before/after,
    and the formula; control_scope and n_control_cards (controls with an offer in the fit
    data, before the singleton drop).

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
    control_scope: which unchanged cards are the controls: "color" (default, the treated
      card's color), "all" (every character's cards) or "other" (the other characters'
      cards only); see control_cards. df must hold them (load_window / load_block_data
      with the same control_scope). The model is the same under every scope: the same fixed
      effects (no color or character terms), covariates and clustering, so a difference
      between scopes comes from the choice of controls alone. Under "all" and "other",
      block^group is shared by every character, so a shock to the treated card's
      character alone is not absorbed. drop_shared_screens can only drop same-color
      controls (other characters' offers are on other runs' screens: a no-op under
      "other"); drop_behavior_flags drops flagged controls of every color.

    Ascension enters as one fixed effect per level. If group has one level in the data
    (e.g. no tagged runs), the group terms are dropped automatically."""
    return _fit_did(df, card_patch_id, upgraded=upgraded, group=group,
                    drop_shared_screens=drop_shared_screens,
                    drop_behavior_flags=drop_behavior_flags, drop_uploaders=drop_uploaders,
                    pooled_groups=pooled_groups, max_week_after=max_week_after,
                    card_act_fe=card_act_fe, picked_screens_only=picked_screens_only,
                    control_scope=control_scope, ref=ref)


def _fit_did(df, card_patch_id, *, upgraded=None, group=None, drop_shared_screens=False,
             drop_behavior_flags=False, drop_uploaders=None, pooled_groups=False,
             max_week_after=None, card_act_fe=False, picked_screens_only=False,
             control_scope="color", pseudo=None, ref=REF):
    """fit_did's fit; pseudo as in _subset (placebo_fit)."""
    d, treated = _subset(df, card_patch_id, upgraded=upgraded, group=group,
                         drop_shared_screens=drop_shared_screens,
                         drop_behavior_flags=drop_behavior_flags,
                         drop_uploaders=drop_uploaders, max_week_after=max_week_after,
                         picked_screens_only=picked_screens_only,
                         control_scope=control_scope, pseudo=pseudo, ref=ref)
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
                picked_screens_only=picked_screens_only, control_scope=control_scope,
                after_week_max=int(d.week[d.after].max()),
                n_offers=int(fit._N),
                n_singletons_dropped=len(d) - int(fit._N),
                n_runs=int(d.run_key.nunique()), n_treated_offers=int(d.is_treated.sum()),
                n_control_cards=int(d.card_id[~d.is_treated].nunique()),
                **_rates(d), formula=fml)


def fit_event_study(df, card_patch_id, weeks=(-6, 8), ref_week=-1, *, upgraded=None,
                    group=None, pooled_groups=False, control_scope="color", ref=REF):
    """The treated card's gap to the controls by (week, block) cell. Weeks outside `weeks`
    are binned into the end weeks. Same fixed effects as fit_did, with week^block^group in
    place of block^group, plus one dummy per treated (week, block) cell; the before-block
    `ref_week` cell is the omitted reference (its row is absent). Before-build offers played
    after the release date are their own cells (block 'before', week >= 0), not dropped.
    Returns one row per cell: week, block, coef, se (clustered by run_key), n_offers.
    control_scope: as in fit_did."""
    d, treated = _subset(df, card_patch_id, upgraded=upgraded, group=group,
                         control_scope=control_scope, ref=ref)
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


def run_all(con, *, tweaks=None, control_scope="color", ref=REF, **fit_kwargs):
    """fit_did for every solo-estimable tweak in tweak_sizes.csv (or those listed in
    `tweaks`), joined to its tweak_sizes columns, for the dose-response plot. Loads each
    window's character data once. Upgrade-only tweaks are fit on upgraded offers; their
    un-upgraded offers are fit as a placebo (placebo_* columns). beta_lo / se_lo are the
    log-odds versions (to_log_odds with the treated card's pick rate before). A tweak whose
    fit fails (e.g. no offers in a block) gets the reason in `error` (placebo_error for the
    placebo) and blank estimates; the others still run. `fit_kwargs` go to fit_did (both
    the main and the placebo fit), e.g. max_week_after=3 for fixed-horizon estimates,
    card_act_fe=True or picked_screens_only=True.

    control_scope ("color", "all", "other"; see control_cards) picks the controls for both
    fits and the data each window loads (load_block_data). Every row says which
    (control_scope) and how many control cards had offers in the fit (n_control_cards), so
    saved fits describe themselves."""
    _check_scope(control_scope)
    ts = _csv(pathlib.Path(ref) / "tweak_sizes.csv")
    ts = ts[ts.solo_estimable == "yes"]
    if tweaks is not None:
        ts = ts[ts.card_patch_id.isin(tweaks)]
    rows = []
    for (color, before, after), g in ts.groupby(["color", "before_builds", "after_builds"],
                                                sort=False):
        df = load_block_data(con, color, before, after, ref, control_scope=control_scope)
        for t in g.to_dict("records"):
            up_only = t["upgrade_only"] == "yes"
            row = dict(t, fit_on="upgraded offers" if up_only else "all offers", error="",
                       placebo_error="")
            try:
                kw = dict(fit_kwargs, upgraded=True) if up_only else fit_kwargs
                res = fit_did(df, t["card_patch_id"], ref=ref, control_scope=control_scope,
                              **kw)
                res.pop("card_id")
                row.update(res)
                row["beta_lo"], row["se_lo"] = to_log_odds(res["beta"], res["se"],
                                                           res["treated_rate_before"])
            except Exception as e:                  # report and keep going
                row["error"] = f"{type(e).__name__}: {e}"
            if up_only:
                try:
                    p = fit_did(df, t["card_patch_id"], ref=ref, control_scope=control_scope,
                                **dict(fit_kwargs, upgraded=False))
                    row.update({f"placebo_{k}": p[k] for k in PLACEBO_KEYS})
                except Exception as e:
                    row["placebo_error"] = f"{type(e).__name__}: {e}"
            row.setdefault("control_scope", control_scope)     # also on failed fits
            rows.append(row)
        del df
    out = pd.DataFrame(rows)
    extra = (["control_scope", "n_control_cards", "beta_lo", "se_lo"]
             + [f"placebo_{k}" for k in PLACEBO_KEYS])
    return out.reindex(columns=list(out.columns) + [c for c in extra if c not in out])


def control_pool_sizes(con, *, tweaks=None, scopes=CONTROL_SCOPES, drop_behavior_flags=False,
                       ref=REF):
    """Control cards and control offers per solo-estimable tweak (tweak_sizes.csv, or those
    in `tweaks`) and control scope, as loaded: offers on the window's builds, each card
    from its own character's runs, before fit_did's filters (missing ascension, singleton
    cells, upgraded-only for upgrade-only tweaks). One aggregate DuckDB query per window;
    no offer-level data. A control card is one control_cards returns (with
    drop_behavior_flags) and that has an offer in the window.

    Columns: card_patch_id, card_id, color, before_builds, after_builds, control_scope,
    n_control_cards, n_control_offers (before + after), n_control_offers_before,
    n_control_offers_after, n_control_offers_own_color (offers of controls of the treated
    card's color), own_color_share (that over n_control_offers), n_treated_offers."""
    for s in scopes:
        _check_scope(s)
    ts = _csv(pathlib.Path(ref) / "tweak_sizes.csv")
    ts = ts[ts.solo_estimable == "yes"]
    if tweaks is not None:
        ts = ts[ts.card_patch_id.isin(tweaks)]
    colors = card_colors(ref)
    chars = {_character(c): c for c in CHARACTER_COLORS}
    rows = []
    for (before, after), g in ts.groupby(["before_builds", "after_builds"], sort=False):
        b_list, a_list = before.split(), after.split()
        n = con.execute("""
            SELECT o.character, o.card_id, o.build_id, count(*) AS n
            FROM offers_with_version o JOIN runs r USING (run_hash)
            WHERE list_contains(?, o.build_id) GROUP BY ALL""", [b_list + a_list]).df()
        n = n[(n.character.map(chars) == n.card_id.map(colors)).to_numpy()].copy()
        n["block"] = np.where(n.build_id.isin(a_list), "after", "before")
        by = (n.groupby(["card_id", "block"]).n.sum().unstack("block")
              .reindex(columns=["before", "after"]).fillna(0).astype(int))
        seen = pd.DataFrame({"card_id": by.index[(by.before + by.after) > 0]})
        for t in g.to_dict("records"):
            cpid, treated = t["card_patch_id"], t["card_id"]
            n_treated = int(by.loc[treated].sum()) if treated in by.index else 0
            for s in scopes:
                ctrl = control_cards(cpid, drop_behavior_flags, df=seen, ref=ref,
                                     control_scope=s)
                c = by.reindex(ctrl).fillna(0)
                own = c[[colors.get(x) == t["color"] for x in c.index]]
                tot, n_own = int(c.to_numpy().sum()), int(own.to_numpy().sum())
                rows.append(dict(
                    card_patch_id=cpid, card_id=treated, color=t["color"],
                    before_builds=before, after_builds=after, control_scope=s,
                    n_control_cards=len(ctrl), n_control_offers=tot,
                    n_control_offers_before=int(c.before.sum()),
                    n_control_offers_after=int(c.after.sum()),
                    n_control_offers_own_color=n_own,
                    own_color_share=n_own / tot if tot else np.nan,
                    n_treated_offers=n_treated))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------ placebo

PATCH_NAMES = ["first", "second", "third", "fourth", "fifth"]   # as spirometry.export
PLACEBO_COLUMNS = [
    "card_patch_id", "pseudo_card", "beta", "se", "z", "n_runs", "treated_rate_before",
    "error", "card_id", "color", "stable_build", "patch", "fit_on", "se_hc", "se_iid",
    "n_offers", "n_treated_offers", "n_control_cards", "pseudo_offers_before",
    "pseudo_offers_after", "n_eligible", "min_offers", "max_cards_per_window", "seed",
    "control_scope", "max_week_after", "card_act_fe", "picked_screens_only"]
PLACEBO_FIT_KEYS = ["beta", "se", "se_hc", "se_iid", "n_runs", "n_offers", "n_treated_offers",
                    "n_control_cards", "treated_rate_before", "control_scope",
                    "max_week_after", "card_act_fe", "picked_screens_only"]
COUNT_SQL = """
SELECT o.character, o.card_id, o.upgraded, list_contains(?, o.build_id) AS after,
       count(*) AS n
FROM offers_with_version o JOIN runs r USING (run_hash)
WHERE list_contains(?, o.build_id) AND o.ascension IS NOT NULL
  AND (NOT list_contains(?, o.build_id) OR o.start_time < ?)
GROUP BY ALL
"""


def placebo_fit(df, card_patch_id, pseudo_card, **fit_kwargs):
    """fit_did with `pseudo_card` as the treated card: an unchanged card of the window's
    color that passes the control rules (control_cards with control_scope="color" and the
    fit's drop_behavior_flags; it must have offers in df). Its true effect is zero, so
    beta / se over many such fits shows whether the errors are honest. The window's real
    treated card is not in the fit (it is never a control), and pseudo_card leaves the
    controls. Same model, clustering and options as fit_did (fit_kwargs: upgraded,
    max_week_after, control_scope, ref, ...). Returns fit_did's dict, with card_id the
    window's real treated card, plus pseudo_card; the treated_* columns are pseudo_card's."""
    res = _fit_did(df, card_patch_id, pseudo=pseudo_card, **fit_kwargs)
    res["card_id"] = window(card_patch_id, fit_kwargs.get("ref", REF))["card_id"]
    res["pseudo_card"] = pseudo_card
    return res


def _block_counts(con, before_builds, after_builds, max_week_after=None, ref=REF):
    """Offers per (card_id, upgraded) and block on a window's builds, each card from its own
    character's runs, with known ascension; after-block offers past max_week_after (weeks
    from the first after-build's release, as load_block_data) left out. One aggregate
    DuckDB query. Columns card_id, upgraded, before, after."""
    before, after = before_builds.split(), after_builds.split()
    cutoff = (pd.Timestamp("2200-01-01") if max_week_after is None else
              release_date(after[0], ref) + pd.Timedelta(seconds=(max_week_after + 1) * WEEK))
    n = con.execute(COUNT_SQL, [after, before + after, after, cutoff.to_pydatetime()]).df()
    chars = {_character(c): c for c in CHARACTER_COLORS}
    n = n[(n.character.map(chars) == n.card_id.map(card_colors(ref))).to_numpy()]
    n["block"] = np.where(n.after, "after", "before")
    return (n.groupby(["card_id", "upgraded", "block"]).n.sum().unstack("block")
            .reindex(columns=["before", "after"]).fillna(0).astype(int).reset_index())


def _card_offers(counts, card, upgraded):
    """(before, after) offers of `card` in _block_counts' table; upgraded as fit_did's."""
    c = counts[counts.card_id == card]
    if upgraded is not None:
        c = c[c.upgraded == upgraded]
    return int(c.before.sum()), int(c.after.sum())


def _patch_labels(ts, ref=REF):
    """stable_build -> "first", "second", ... by release date (builds.csv), as
    spirometry.export labels patches; blank for a build without a release date."""
    b = _csv(pathlib.Path(ref) / "builds.csv").set_index("build_id")
    dates = {x: b.release_date.get(x, "") for x in ts.stable_build.unique()}
    order = sorted((x for x in dates if dates[x]), key=dates.get)
    return {x: PATCH_NAMES[i] if i < len(PATCH_NAMES) else str(i + 1)
            for i, x in enumerate(order)}


def placebo_all(con, *, tweaks=None, max_cards_per_window=20, seed=0, min_offers=None,
                ref=REF, **fit_kwargs):
    """placebo_fit on sampled unchanged cards, for every solo-estimable tweak in
    tweak_sizes.csv (or those in `tweaks`): one row per fit. Loads each window's data once.

    Eligible pseudo cards: the tweak's control cards of its own color (control_cards,
    control_scope="color", with fit_kwargs' drop_behavior_flags) with at least `min_offers`
    offers in each block. Up to max_cards_per_window of them are sampled per tweak, without
    replacement, seeded by (seed, card_patch_id), so a tweak gets the same cards whichever
    other tweaks run. Tweaks sharing a window can draw the same pseudo card; those fits
    differ only in which real treated card is left out of the data.

    min_offers: the minimum the real tweaks meet. None (default) sets it to the smallest
    min(before, after) treated-card offer count among all solo-estimable tweaks (not just
    those in `tweaks`), so a pseudo card is never offered less than the least-offered real
    tweak. Offers are counted as loaded (the window's builds, the card's own character,
    known ascension), on the offers the fit uses (upgraded only for upgrade-only tweaks or
    when fit_kwargs set it; after-block weeks <= max_week_after), before fit_did's other
    filters (group, screens, uploaders) and the singleton drop. Every row carries it.

    Upgrade-only tweaks are fit on upgraded offers (as run_all's main fit). fit_kwargs go to
    placebo_fit (fit_did's options, e.g. max_week_after=3, control_scope="all").

    Columns: card_patch_id, pseudo_card, beta, se, z (beta / se), n_runs,
    treated_rate_before (the pseudo card's), error, then card_id (the real treated card),
    color, stable_build, patch (as spirometry.export), fit_on, se_hc, se_iid, n_offers,
    n_treated_offers (pseudo card offers in the fit), n_control_cards,
    pseudo_offers_before / _after (the counts above), n_eligible, min_offers,
    max_cards_per_window, seed and the fit options. A failed fit keeps its row with the
    reason in `error`; a tweak with no eligible card gets one row with a blank pseudo_card."""
    control_scope = fit_kwargs.get("control_scope", "color")
    _check_scope(control_scope)
    flags = fit_kwargs.get("drop_behavior_flags", False)
    ts_all = _csv(pathlib.Path(ref) / "tweak_sizes.csv")
    ts_all = ts_all[ts_all.solo_estimable == "yes"]
    ts = ts_all if tweaks is None else ts_all[ts_all.card_patch_id.isin(tweaks)]
    need = ts_all if min_offers is None else ts
    counts = {k: _block_counts(con, *k, fit_kwargs.get("max_week_after"), ref)
              for k in dict.fromkeys(zip(need.before_builds, need.after_builds))}
    up = lambda t: True if t["upgrade_only"] == "yes" else fit_kwargs.get("upgraded")
    offers = lambda t, card: _card_offers(counts[(t["before_builds"], t["after_builds"])],
                                          card, up(t))
    if min_offers is None:
        min_offers = min(min(offers(t, t["card_id"])) for t in ts_all.to_dict("records"))
    patch = _patch_labels(ts_all, ref)
    opts = dict(control_scope=control_scope,
                max_week_after=fit_kwargs.get("max_week_after"),
                card_act_fe=fit_kwargs.get("card_act_fe", False),
                picked_screens_only=fit_kwargs.get("picked_screens_only", False))
    rows = []
    for (color, before, after), g in ts.groupby(["color", "before_builds", "after_builds"],
                                                sort=False):
        df = load_block_data(con, color, before, after, ref, control_scope=control_scope)
        for t in g.to_dict("records"):
            cpid = t["card_patch_id"]
            base = dict(card_patch_id=cpid, card_id=t["card_id"], color=color,
                        stable_build=t["stable_build"],
                        patch=patch.get(t["stable_build"], ""),
                        fit_on="upgraded offers" if up(t) else (
                            "all offers" if up(t) is None else "un-upgraded offers"),
                        min_offers=min_offers, max_cards_per_window=max_cards_per_window,
                        seed=seed, pseudo_card="", error="", **opts)
            try:
                eligible = [c for c in control_cards(cpid, flags, df=df, ref=ref)
                            if min(offers(t, c)) >= min_offers]
            except Exception as e:                  # report and keep going
                rows.append(dict(base, error=f"{type(e).__name__}: {e}"))
                continue
            base["n_eligible"] = len(eligible)
            if not eligible:
                rows.append(dict(base, error=f"no eligible pseudo card (>= {min_offers} "
                                             "offers in each block)"))
                continue
            rng = np.random.default_rng([seed, zlib.crc32(cpid.encode())])
            picks = sorted(rng.choice(eligible, min(max_cards_per_window, len(eligible)),
                                      replace=False))
            for c in picks:
                nb, na = offers(t, c)
                row = dict(base, pseudo_card=c, pseudo_offers_before=nb,
                           pseudo_offers_after=na)
                try:
                    kw = dict(fit_kwargs, upgraded=True) if t["upgrade_only"] == "yes" \
                        else fit_kwargs
                    res = placebo_fit(df, cpid, c, ref=ref, **kw)
                    row.update({k: res[k] for k in PLACEBO_FIT_KEYS})
                    row["z"] = res["beta"] / res["se"] if res["se"] > 0 else np.nan
                except Exception as e:
                    row["error"] = f"{type(e).__name__}: {e}"
                rows.append(row)
        del df
    return pd.DataFrame(rows).reindex(columns=PLACEBO_COLUMNS)


def placebo_file(max_week_after=None):
    """The saved placebo fits' file name for a horizon: all weeks (the 2026-10-02 run) is
    placebo_main.parquet, weeks 0-k is placebo_h<k>.parquet (as did_main / did_h3)."""
    return ("placebo_main.parquet" if max_week_after is None
            else f"placebo_h{int(max_week_after)}.parquet")


def placebo_run(con, analysis, max_week_after=None, **kwargs):
    """placebo_all with the 2026-10-02 settings (same-color controls, 20 pseudo cards per
    tweak, seed 0; kwargs override them) at one horizon, saved in `analysis` under
    placebo_file(max_week_after), beside the other horizon's file, so
    spirometry.sensitivity's calibrated counts read both. Returns the rows."""
    kw = dict(max_cards_per_window=20, seed=0, **kwargs)
    if max_week_after is not None:
        kw["max_week_after"] = max_week_after
    out = placebo_all(con, **kw)
    path = pathlib.Path(analysis) / placebo_file(max_week_after)
    path.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(path)
    return out


MIN_PLACEBO_CARDS = 5     # placebo_vs_real: fewer placebo pairs in a window -> blank
PAIR_KEY = ["color", "before_builds", "after_builds", "fit_on", "pseudo_card"]
PAIR_MEAN = ["beta", "se", "z", "se_hc", "se_iid", "n_runs", "n_offers", "n_treated_offers",
             "treated_rate_before"]
Z_QUANTILES = (0.05, 0.25, 0.5, 0.75, 0.95)


def _placebo_ok(df):
    """placebo_all rows without an error and with a finite z."""
    z = pd.to_numeric(df.z, errors="coerce")
    return df[(df.error.fillna("") == "") & np.isfinite(z)].assign(z=z)


def placebo_pairs(df, ref=REF):
    """placebo_all's successful fits, one row per (window, pseudo card): window = the
    tweak's color, before_builds and after_builds (tweak_sizes.csv) and fit_on (upgrade-only
    tweaks are fit on upgraded offers, a different fit). Tweaks sharing a window draw from
    the same cards, and their fits of one pseudo card differ only in which real treated card
    is left out of the data, so they are near duplicates. beta, se, z, se_hc, se_iid,
    n_runs, n_offers, n_treated_offers and treated_rate_before are the mean over the tweaks
    sharing the pair (z is the mean of their z, not mean beta / mean se); the other columns
    are the first tweak's (card_patch_id, card_id, patch, ...). n_tweaks_sharing and
    card_patch_ids (space-separated) say which tweaks were averaged; window is
    "<before_builds> -> <after_builds>"."""
    ts = _csv(pathlib.Path(ref) / "tweak_sizes.csv").set_index("card_patch_id")
    d = _placebo_ok(df).copy()
    for c in ("before_builds", "after_builds"):
        d[c] = d.card_patch_id.map(ts[c])
    g = d.groupby(PAIR_KEY, sort=False)
    out = g.first()
    out[PAIR_MEAN] = g[PAIR_MEAN].mean()
    out["n_tweaks_sharing"] = g.size()
    out["card_patch_ids"] = g.card_patch_id.agg(" ".join)
    out = out.reset_index()
    out["window"] = out.before_builds + " -> " + out.after_builds
    return out


def _z_stats(z):
    """mean / sd of z, shares beyond 2 and 3, and robust versions: median |z| (honest
    errors: 0.674), robust sd (1.4826 x MAD of z) and quantiles."""
    out = dict(mean_z=z.mean(), sd_z=z.std(), share_abs_z_gt2=(z.abs() > 2).mean(),
               share_abs_z_gt3=(z.abs() > 3).mean(), median_abs_z=z.abs().median(),
               robust_sd_z=1.4826 * (z - z.median()).abs().median())
    for q in Z_QUANTILES:
        out[f"z_q{round(q * 100):02d}"] = z.quantile(q)
    return out


def _patch_order(patches):
    rank = {p: i for i, p in enumerate(PATCH_NAMES)}
    return sorted(set(patches), key=lambda p: (rank.get(p, len(rank)), p))


def placebo_summary(df, dedupe=False, ref=REF):
    """Calibration of placebo_all's z: n_fits, n_tweaks, mean_z, sd_z, share_abs_z_gt2 and
    share_abs_z_gt3 (for honest errors about 0, 1, 0.046 and 0.003), overall, by patch and
    by the pseudo card's offers in the fit (n_treated_offers): "small" below the median
    over the fits, "large" at or above it (the cutoff is in the label). Only fits without
    an error and with a finite z count; n_failed (overall row) counts the others.

    Robust columns (less moved by a few extreme fits): median_abs_z (honest errors:
    0.674), robust_sd_z = 1.4826 x the median absolute deviation of z (honest: 1), and
    z's 5/25/50/75/95% quantiles z_q05 ... z_q95.

    dedupe=True: one row per (window, pseudo card) pair (placebo_pairs: z averaged over
    the tweaks sharing the pair), so near-duplicate fits count once; n_fits then counts
    pairs and n_tweaks the tweaks behind them."""
    ok = placebo_pairs(df, ref) if dedupe else _placebo_ok(df)
    tweaks = lambda g: (len(set(" ".join(g.card_patch_ids).split())) if dedupe
                        else g.card_patch_id.nunique())
    parts = [("all", "all", ok)]
    parts += [("patch", p, ok[ok.patch == p]) for p in _patch_order(ok.patch)]
    if len(ok):
        cut = ok.n_treated_offers.median()
        small = ok.n_treated_offers < cut
        parts += [("offers", f"small (< {cut:g})", ok[small]),
                  ("offers", f"large (>= {cut:g})", ok[~small])]
    out = pd.DataFrame([dict(split=s, level=lvl, n_fits=len(g), n_tweaks=tweaks(g),
                             **_z_stats(g.z)) for s, lvl, g in parts])
    out["n_failed"] = np.where(out.split == "all", len(df) - len(_placebo_ok(df)), np.nan)
    out["dedupe"] = dedupe
    return out


def _real(real_df, ref=REF):
    """A saved run_all result (card_patch_id as a column or the index) with patch and
    the tweak_sizes window columns; z_real = beta / se."""
    r = real_df.reset_index() if "card_patch_id" not in real_df.columns else real_df.copy()
    ts = _csv(pathlib.Path(ref) / "tweak_sizes.csv").set_index("card_patch_id")
    for c in ("color", "before_builds", "after_builds", "upgrade_only", "mixed_direction",
              "direction", "log_ratio", "stable_build"):
        r[c] = r.card_patch_id.map(ts[c])
    r["patch"] = r.stable_build.map(_patch_labels(ts[ts.solo_estimable == "yes"], ref))
    if "fit_on" not in r:
        r["fit_on"] = np.where(r.upgrade_only == "yes", "upgraded offers", "all offers")
    r["beta"], r["se"] = pd.to_numeric(r.beta), pd.to_numeric(r.se)
    r["z_real"] = r.beta / r.se
    return r


def placebo_vs_real(real_df, placebo_df, ref=REF):
    """Each real tweak against the placebos of its own window. real_df: a run_all result
    (e.g. data/analysis/did_main.parquet), fit with the options placebo_df was. The
    placebos are placebo_pairs rows with the tweak's color, builds and fit_on: the same
    players, weeks and fit as the real estimate, other cards. One row per real tweak:
    card_patch_id, card_id, patch, fit_on, beta_real, se_real, z_real, n_placebo (pairs in
    the window), placebo_beta_mean, placebo_beta_sd, empirical_p (share of the window's
    placebo |beta| >= the real |beta|) and calibrated_z ((beta_real - placebo_beta_mean) /
    placebo_beta_sd); the last two blank when n_placebo < MIN_PLACEBO_CARDS (5). Betas
    are in probability units, as fit_did returns them."""
    r = _real(real_df, ref)
    pairs = placebo_pairs(placebo_df, ref).groupby(
        ["color", "before_builds", "after_builds", "fit_on"]).beta
    rows = []
    for t in r.itertuples():
        key = (t.color, t.before_builds, t.after_builds, t.fit_on)
        pl = pairs.get_group(key) if key in pairs.groups else pd.Series(dtype=float)
        enough = len(pl) >= MIN_PLACEBO_CARDS
        mean, sd = pl.mean(), pl.std()
        rows.append(dict(
            card_patch_id=t.card_patch_id, card_id=t.card_id, patch=t.patch,
            fit_on=t.fit_on, beta_real=t.beta, se_real=t.se, z_real=t.z_real,
            n_placebo=len(pl), placebo_beta_mean=mean, placebo_beta_sd=sd,
            empirical_p=(pl.abs() >= abs(t.beta)).mean() if enough else np.nan,
            calibrated_z=(t.beta - mean) / sd if enough and sd > 0 else np.nan))
    return pd.DataFrame(rows)


def placebo_vs_real_by_patch(pvr, placebo_df, ref=REF):
    """Per patch, |beta| quantiles (5/25/50/75/95%) of the real tweaks (placebo_vs_real
    rows) and of the placebo pairs side by side (one row each, `who` = "real" /
    "placebo"); on the real rows, n_empirical_p (tweaks with one) and n_empirical_p_lt_05
    (those with empirical_p < 0.05)."""
    pairs = placebo_pairs(placebo_df, ref)
    rows = []
    for p in _patch_order(list(pvr.patch) + list(pairs.patch)):
        for who, b in (("real", pvr.beta_real[pvr.patch == p]),
                       ("placebo", pairs.beta[pairs.patch == p])):
            row = dict(patch=p, who=who, n=len(b))
            for q in Z_QUANTILES:
                row[f"abs_beta_q{round(q * 100):02d}"] = b.abs().quantile(q)
            if who == "real":
                e = pvr.empirical_p[pvr.patch == p].dropna()
                row.update(n_empirical_p=len(e), n_empirical_p_lt_05=int((e < 0.05).sum()))
            rows.append(row)
    return pd.DataFrame(rows)


def sign_agreement(real_df, ref=REF):
    """Per patch (and "all"): how many real tweaks moved toward the change, by
    spirometry.export's toward_change rule: sign(beta) = sign(direction x log_ratio),
    defined for tweaks with one direction that are not upgrade-only. Counts only:
    n_tweaks, n_with_direction, n_toward, and the same among |z_real| > 2
    (n_z_gt2_with_direction, n_z_gt2_toward)."""
    r = _real(real_df, ref)
    dose = pd.to_numeric(r.direction) * pd.to_numeric(r.log_ratio)
    has = ((r.mixed_direction != "yes") & (r.upgrade_only != "yes") & dose.notna()
           & r.beta.notna())
    toward = has & (np.sign(r.beta) == np.sign(dose))
    big = r.z_real.abs() > 2
    rows = []
    for p in ["all"] + _patch_order(r.patch):
        m = r.patch.notna() if p == "all" else (r.patch == p)
        rows.append(dict(patch=p, n_tweaks=int(m.sum()), n_with_direction=int((m & has).sum()),
                         n_toward=int((m & toward).sum()),
                         n_z_gt2_with_direction=int((m & has & big).sum()),
                         n_z_gt2_toward=int((m & toward & big).sum())))
    return pd.DataFrame(rows)


def placebo_spread_by_feature(placebo_df, dedupe=True, min_cell=30, ref=REF):
    """sd_z, median_abs_z and robust_sd_z by tercile of the pseudo card's
    treated_rate_before and of n_runs (pd.qcut; lo / hi are the tercile's range), on
    placebo_pairs (dedupe=True, default) or every fit. n_fits per cell; small_cell when
    under min_cell (30)."""
    d = placebo_pairs(placebo_df, ref) if dedupe else _placebo_ok(placebo_df)
    rows = []
    for feat in ("treated_rate_before", "n_runs"):
        t = pd.qcut(d[feat], 3, labels=["low", "mid", "high"])
        for lvl in ["low", "mid", "high"]:
            g = d[t == lvl]
            st = _z_stats(g.z)
            rows.append(dict(feature=feat, tercile=lvl, lo=g[feat].min(), hi=g[feat].max(),
                             n_fits=len(g), sd_z=st["sd_z"], median_abs_z=st["median_abs_z"],
                             robust_sd_z=st["robust_sd_z"], small_cell=len(g) < min_cell))
    return pd.DataFrame(rows).assign(dedupe=dedupe)


def dose_response_sensitivity(real_df, factors, ref=REF):
    """The dose-response "slope per patch" model (spirometry.meta, all weeks, log-odds, on
    the tweaks spirometry.export's dose_response uses: one direction, not upgrade-only,
    with a size) refit with each tweak's se_lo multiplied by its patch's factor. factors:
    {label: (first-patch factor, second-patch factor)}; (1, 1) gives the existing fit.
    One row per (label, patch): factor, slope, se, z, tau2, n_tweaks (all patches)."""
    from spirometry import meta
    r = _real(real_df, ref)
    if "beta_lo" not in r or "se_lo" not in r:
        r["beta_lo"], r["se_lo"] = zip(*(to_log_odds(b, s, p) for b, s, p in zip(
            r.beta, r.se, pd.to_numeric(r.treated_rate_before))))
    r["dose_x"] = pd.to_numeric(r.direction) * pd.to_numeric(r.log_ratio)
    y, se = pd.to_numeric(r.beta_lo), pd.to_numeric(r.se_lo)
    line = r[(r.mixed_direction != "yes") & (r.upgrade_only != "yes") & r.dose_x.notna()
             & y.notna() & (se > 0)]
    second = (line.patch != "first").astype(float)
    rows = []
    for label, (f1, f2) in factors.items():
        fits = meta.dose_response_fits(y[line.index], se[line.index], line.dose_x, second,
                                       se_inflation=(f1, f2))
        fits = fits[fits.model == "slope per patch"].set_index("term")
        for p, term, f in (("first", "slope_first", f1), ("second", "slope_second", f2)):
            rows.append(dict(factors=label, patch=p, se_factor=f, slope=fits.coef[term],
                             se=fits.se[term], z=fits.z[term], tau2=fits.tau2[term],
                             n_tweaks=int(fits.n_tweaks[term])))
    return pd.DataFrame(rows)


# -------------------------------------------------------------------------- anticipation

MIN_ANTICIPATION_OFFERS = 2000   # treated offers needed on each side of the beta date
MIN_ANTICIPATION_DAYS = 3        # days with treated offers needed on each side


def exposure(card_patch_id, ref=REF):
    """The card-patch's row in beta_exposure.csv (spirometry.exposure), as a dict."""
    e = _csv(pathlib.Path(ref) / "beta_exposure.csv")
    e = e[e.card_patch_id == card_patch_id]
    if e.empty:
        raise KeyError(f"{card_patch_id} is not in beta_exposure.csv")
    return e.iloc[0].to_dict()


def old_version_builds(card_patch_id, *, widen=True, ref=REF):
    """Stable builds on which every card of the treated card's color has the same card
    version (card_versions.csv) as on the window's before builds: the builds where stable
    players still have the old card and the controls are unchanged too. widen=False: the
    window's before builds only. widen=True (default): also any other stable build with
    identical versions that is a before or after build of some card_patch window (the
    builds the project uses; the launch builds v0.98.x, identical to v0.99.1 but outside
    every window per the audit, stay out). Returns (builds in release order, cards of that
    color whose behavior_event_ids differ between those builds: bug fixes that no card
    version shows)."""
    w = window(card_patch_id, ref)
    color = card_colors(ref).get(w["card_id"], "")
    before = w["before_builds"].split()
    cv = _csv(pathlib.Path(ref) / "card_versions.csv")
    cards = {c for c, col in card_colors(ref).items() if col == color}
    cv = cv[cv.card_id.isin(cards)]
    ver = cv.pivot(index="card_id", columns="build_id", values="version")
    b = _csv(pathlib.Path(ref) / "builds.csv").set_index("build_id")
    ref_ver = ver[before[0]]
    for x in before[1:]:
        if not (ver[x] == ref_ver).all():
            raise ValueError(f"{card_patch_id}: before builds carry different versions")
    builds = list(before)
    if widen:
        wins_ = _csv(pathlib.Path(ref) / "windows.csv")
        used = set(" ".join(wins_[wins_.level == "card_patch"].before_builds + " "
                            + wins_[wins_.level == "card_patch"].after_builds).split())
        for x in ver.columns:
            if (x not in builds and x in used and b.branch.get(x) == "stable"
                    and (ver[x] == ref_ver).all() and (ref_ver != "").all()):
                builds.append(x)
    builds.sort(key=lambda x: b.release_date.get(x, ""))
    return builds, behavior_differs(card_patch_id, builds, ref)


def behavior_differs(card_patch_id, builds, ref=REF):
    """Cards of the treated card's color whose behavior_event_ids (bug fixes no card
    version shows) differ between `builds`."""
    color = card_colors(ref).get(window(card_patch_id, ref)["card_id"], "")
    cv = _csv(pathlib.Path(ref) / "card_versions.csv")
    cards = {c for c, col in card_colors(ref).items() if col == color}
    bh = cv[cv.card_id.isin(cards) & cv.build_id.isin(builds)].pivot(
        index="card_id", columns="build_id", values="behavior_event_ids")
    return sorted(bh.index[bh.nunique(axis=1) > 1])


def load_anticipation(con, card_patch_id, *, widen=True, builds=None, until_stable=True,
                      ref=REF):
    """Offers of the treated card's character on the old-version stable builds
    (old_version_builds, or `builds`), split at the card's first-beta date
    (beta_exposure.csv): block = 'before' for runs whose UTC start date is before it,
    'after' on or after it (as runs.before_release compares dates); week = whole weeks
    from that date (negative before). until_stable=True drops runs started on or after the
    first after-build's release (the new stable is out; those runs are stragglers on an
    old build). Returns (df, info): df with load_window's columns, info with the builds,
    dates, dropped counts, behavior-differing cards and main_postbeta_share (the share of
    the treated card's offers in the main design's before block, all dates, from runs
    started on or after the beta date: how much of the before block is post-beta)."""
    w = window(card_patch_id, ref)
    color = card_colors(ref).get(w["card_id"], "")
    builds = list(builds) if builds is not None else old_version_builds(
        card_patch_id, widen=widen, ref=ref)[0]
    return _split(_load_offers(con, color, builds, ref), card_patch_id, builds,
                  until_stable, widen, ref)


def _side_counts(d, treated):
    """Treated offers, runs and days (distinct UTC start dates with a treated offer) on
    each side, and treated offers per build and side."""
    t = d[d.card_id == treated]
    out = {}
    for side, blk in (("pre", "before"), ("post", "after")):
        s = t[t.block == blk]
        out[f"n_treated_offers_{side}"] = len(s)
        out[f"n_runs_{side}"] = int(d.run_key[d.block == blk].nunique())
        out[f"n_offers_{side}"] = int((d.block == blk).sum())
        out[f"days_{side}"] = int(s.start_time.dt.normalize().nunique())
        out[f"first_day_{side}"] = str(s.start_time.min().date()) if len(s) else ""
        out[f"last_day_{side}"] = str(s.start_time.max().date()) if len(s) else ""
    by = t.groupby(["build_id", "block"], observed=True).size()
    out["treated_offers_by_build"] = "; ".join(
        f"{b} {'pre' if k == 'before' else 'post'} {n}" for (b, k), n in by.items())
    return out


def _pre_slope(d, fe):
    """Weekly slope of the treated card's gap before the beta date: picked ~ treated x
    week on pre-beta offers, same fixed effects. NaN without two pre-beta weeks."""
    p = d[~d.after].copy()
    if p[p.is_treated].week.nunique() < 2:
        return np.nan, np.nan
    p["treated_week"] = p.is_treated * p.week.astype(float)
    fit = _feols("picked ~ treated_week | " + " + ".join(fe), p)
    return float(fit.coef()["treated_week"]), float(fit.se()["treated_week"])


def anticipation_check(con, card_patch_id, *, data=None, min_offers=MIN_ANTICIPATION_OFFERS,
                       min_days=MIN_ANTICIPATION_DAYS, beta_main=None, se_main=None,
                       widen=True, builds=None, until_stable=True, drop_behavior_diff=True,
                       upgraded=None, group=None, pooled_groups=False, ref=REF):
    """Did stable players start picking the card differently when its change appeared on
    a beta, while they still had the old card? On the old-version stable builds
    (load_anticipation), the fit_did model with the split at the first-beta date in place
    of the stable release: picked ~ treat_postbeta | (fit_did's fixed effects), errors
    clustered by run_key, controls as control_cards. treat_postbeta = treated card, run
    started on or after the first-beta date.

    Returns a dict: beta_postbeta, se, ci_lo, ci_hi, treated offers / all offers / runs /
    days (distinct dates with a treated offer) and first/last day on each side,
    treated_offers_by_build, status ('informative', 'uninformative' or 'error') and reason.
    Uninformative: fewer than `min_offers` treated offers or `min_days` days on a side (the
    fit still runs when both sides have data, so the numbers are there to look at). With no
    data on a side there is no fit.

    Main design: beta_main / se_main (fit_did on the window; refit unless given),
    ratio_to_main = beta_postbeta / beta_main (blank unless |beta_main| > 2 se_main), and
    total_implied = beta_main + main_postbeta_share x beta_postbeta: if the move before
    the stable release is real, the main DiD's before block already carries that share of
    it, and the total move is this sum (approximate: it assumes the before block's
    post-beta offers look like this check's post side). share_before_release =
    beta_postbeta / total_implied, blank under the same rule.

    Drift: a trend in the treated card that runs through the beta date also shows up as
    beta_postbeta (about slope x week_gap). pre_slope / pre_slope_se (the weekly slope of
    the gap before the beta date, when there are two pre-beta weeks) and week_gap (mean
    week of the treated post-beta offers minus pre-beta) let the reader compare; nothing
    is corrected. anticipation_weekly shows it by week.

    widen / builds / until_stable: see old_version_builds and load_anticipation.
    drop_behavior_diff: drop cards whose bug-fix behavior events differ between the
    builds (e.g. Bad Luck, Stardust, Summon Forth between v0.103.2 and v0.103.3) from the
    fit (a treated card among them is kept and flagged). upgraded / group /
    pooled_groups: as in fit_did."""
    df, info = data if data is not None else load_anticipation(
        con, card_patch_id, widen=widen, builds=builds, until_stable=until_stable, ref=ref)
    treated = info["card_id"]
    out = dict(info, status="", reason="", beta_postbeta=np.nan, se=np.nan, ci_lo=np.nan,
               ci_hi=np.nan, min_offers=min_offers, min_days=min_days,
               drop_behavior_diff=drop_behavior_diff, upgraded=upgraded,
               group=group or "", pooled_groups=pooled_groups)
    differ = [c for c in info["behavior_differs"].split() if c != treated]
    if drop_behavior_diff and differ:
        df = df[~df.card_id.isin(differ)]
    out["behavior_dropped"] = " ".join(differ) if drop_behavior_diff else ""
    out["treated_behavior_differs"] = treated in info["behavior_differs"].split()
    sub = df if upgraded is None else df[df.upgraded == upgraded]
    if group is not None:
        sub = sub[sub.group == group]
    out.update(_side_counts(sub, treated))
    why = []
    for side in ("pre", "post"):
        if out[f"n_treated_offers_{side}"] < min_offers:
            why.append(f"{out[f'n_treated_offers_{side}']} treated offers {side}-beta "
                       f"(< {min_offers})")
        if out[f"days_{side}"] < min_days:
            why.append(f"{out[f'days_{side}']} days {side}-beta (< {min_days})")
    out["status"] = "uninformative" if why else "informative"
    out["reason"] = "; ".join(why)
    try:
        d, _ = _subset(df, card_patch_id, upgraded=upgraded, group=group, ref=ref)
        fe = _fixed_effects(d, group, pooled_groups)
        fit = _feols("picked ~ treat_post | " + " + ".join(fe), d)
        ci = fit.confint().loc["treat_post"].to_numpy(dtype=float)
        out.update(beta_postbeta=float(fit.coef()["treat_post"]),
                   se=float(fit.se()["treat_post"]), ci_lo=float(ci[0]), ci_hi=float(ci[1]),
                   n_fit_offers=int(fit._N), **_rates(d),
                   formula="picked ~ treat_postbeta | " + " + ".join(fe))
        wk = d[d.is_treated]
        out["week_gap"] = float(wk.week[wk.after].mean() - wk.week[~wk.after].mean())
        out["pre_slope"], out["pre_slope_se"] = _pre_slope(d, [f for f in fe
                                                               if "block" not in f])
    except Exception as e:                          # e.g. no data on one side
        out["status"] = "uninformative" if "no " in str(e) else "error"
        out["reason"] = "; ".join(filter(None, [out["reason"], f"{type(e).__name__}: {e}"]))
    if beta_main is None and con is not None:
        try:
            m = fit_did(load_window(con, card_patch_id, ref), card_patch_id,
                        upgraded=upgraded, group=group, pooled_groups=pooled_groups,
                        ref=ref)
            beta_main, se_main = m["beta"], m["se"]
        except Exception as e:
            out["main_error"] = f"{type(e).__name__}: {e}"
    out["beta_main"] = np.nan if beta_main is None else float(beta_main)
    out["se_main"] = np.nan if se_main is None else float(se_main)
    clear = abs(out["beta_main"]) > 2 * out["se_main"]
    b, s = out["beta_postbeta"], info["main_postbeta_share"]
    out["ratio_to_main"] = b / out["beta_main"] if clear else np.nan
    out["total_implied"] = out["beta_main"] + s * b if np.isfinite(b) else np.nan
    out["share_before_release"] = b / out["total_implied"] if clear else np.nan
    return out


def anticipation_weekly(con, card_patch_id, *, data=None, weeks=(-6, 8), widen=True,
                        builds=None, until_stable=True, drop_behavior_diff=True,
                        upgraded=None, group=None, pooled_groups=False, ref=REF):
    """The treated card's gap to the controls by week from its first-beta date (week 0 =
    the beta date's week), fit_event_study's model on load_anticipation's data: week -1
    is the reference, weeks beyond `weeks` are binned into the end weeks, and the range is
    clipped to the weeks the old-version builds have data for. Returns one row per week:
    week, block ('before' / 'after' the beta date), coef, se, n_offers (treated), plus
    week_start (date) and first_beta_date, for a plot with a line at the beta date."""
    df, info = data if data is not None else load_anticipation(
        con, card_patch_id, widen=widen, builds=builds, until_stable=until_stable, ref=ref)
    differ = [c for c in info["behavior_differs"].split() if c != info["card_id"]]
    if drop_behavior_diff and differ:
        df = df[~df.card_id.isin(differ)]
    lo = max(weeks[0], int(df.week.min()))
    hi = min(weeks[1], int(df.week.max()))
    es = fit_event_study(df, card_patch_id, weeks=(lo, hi), ref_week=-1, upgraded=upgraded,
                         group=group, pooled_groups=pooled_groups, ref=ref)
    tb = pd.Timestamp(info["first_beta_date"])
    es["week_start"] = [str((tb + pd.Timedelta(weeks=int(w))).date()) for w in es.week]
    es["first_beta_date"] = info["first_beta_date"]
    es["card_patch_id"] = card_patch_id
    return es


def anticipation_all(con, *, tweaks=None, main=None, ref=REF, **kwargs):
    """anticipation_check for every row of beta_exposure.csv (the 43 solo-estimable numeric
    tweaks; or those listed in `tweaks`), one data load per (character, old-version builds);
    the split is redone per tweak. Upgrade-only tweaks are fit on upgraded offers (as
    run_all) and flagged. `main`: a run_all result to take beta_main / se_main from
    (matched on card_patch_id; the same options should have been used); without it each
    tweak's main DiD is refit. kwargs go to anticipation_check (min_offers, min_days, widen,
    until_stable, drop_behavior_diff, group, pooled_groups) and are echoed as columns.
    Returns one flat row per tweak (parquet-ready)."""
    ex = _csv(pathlib.Path(ref) / "beta_exposure.csv")
    if tweaks is not None:
        ex = ex[ex.card_patch_id.isin(tweaks)]
    mains = {} if main is None else main.set_index("card_patch_id")[["beta", "se"]].to_dict(
        "index")
    widen = kwargs.get("widen", True)
    until = kwargs.get("until_stable", True)
    cache, rows = {}, []
    for e in ex.to_dict("records"):
        cpid = e["card_patch_id"]
        up = e["upgrade_only"] == "yes"
        row = dict(upgrade_only=e["upgrade_only"], lead_days=e["lead_days"])
        try:
            builds, _ = old_version_builds(cpid, widen=widen, ref=ref)
            key = (e["color"], tuple(builds))
            if key not in cache:
                cache.clear()                       # one character's data at a time
                cache[key] = _load_offers(con, e["color"], builds, ref)
            data = _split(cache[key], cpid, builds, until, widen, ref)
            m = mains.get(cpid)
            kw = dict(kwargs, upgraded=True if up else kwargs.get("upgraded"))
            if m is not None:
                kw.update(beta_main=m["beta"], se_main=m["se"])
            row.update(anticipation_check(con if m is None else None, cpid, data=data,
                                          ref=ref, **kw))
        except Exception as ex_:                    # report and keep going
            row.update(card_patch_id=cpid, card_id=e["card_id"], status="error",
                       reason=f"{type(ex_).__name__}: {ex_}")
        rows.append(row)
    out = pd.DataFrame(rows)
    for c in out.columns:
        if out[c].dtype == object:
            out[c] = out[c].map(lambda v: "" if v is None or (isinstance(v, float)
                                                               and np.isnan(v)) else v)
            if not out[c].map(lambda v: isinstance(v, (bool, np.bool_))).all():
                out[c] = out[c].astype(str)
    return out


def _split(raw, card_patch_id, builds, until_stable, widen, ref):
    """load_anticipation's split of loaded offers at the first-beta date (also used on
    anticipation_all's cached offers)."""
    w = window(card_patch_id, ref)
    e = exposure(card_patch_id, ref)
    if not e["first_beta_date"]:
        raise ValueError(f"{card_patch_id}: no first-beta date in beta_exposure.csv")
    tb = pd.Timestamp(e["first_beta_date"])
    stable = release_date(w["after_builds"].split()[0], ref)
    df = raw.copy()
    post = df.start_time.dt.normalize() >= tb
    df["block"] = np.where(post, "after", "before")
    df["week"] = np.floor((df.start_time - tb).dt.total_seconds() / WEEK).astype("int16")
    tr = (df.card_id == w["card_id"]) & df.build_id.isin(w["before_builds"].split())
    share = float(post[tr].mean()) if tr.any() else np.nan
    n0 = len(df)
    if until_stable:
        df = df[df.start_time.dt.normalize() < stable]
    info = dict(card_patch_id=card_patch_id, card_id=w["card_id"],
                color=card_colors(ref).get(w["card_id"], ""), builds=" ".join(builds),
                first_beta_build=e["first_beta_build"],
                first_beta_date=e["first_beta_date"], stable_date=str(stable.date()),
                until_stable=until_stable, widen=widen,
                n_offers_dropped_after_stable=n0 - len(df),
                behavior_differs=" ".join(behavior_differs(card_patch_id, builds, ref)),
                main_postbeta_share=share)
    return _finish(df.copy()), info
