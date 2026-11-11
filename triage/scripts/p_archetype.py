"""Section P (EXPLORATORY): archetype (complement) spillover.

Found post hoc on Regent's create-card cards; this tests it on Defect, Ironclad, Necrobinder
and Silent. Changes no factor, number or result. The rules are in TRIAGE.md section P and
were written, with parts 1 and 2's tables, before parts 3-5 (the only ones that read a
placebo z) were run.

    python triage/scripts/p_archetype.py --check     # rule and statistic checks, no data
    python triage/scripts/p_archetype.py --part 1    # card -> archetype, per window (no z)
    python triage/scripts/p_archetype.py --part 2    # changes per window x archetype (no z)
    python triage/scripts/p_archetype.py --part 3    # declared test, four test characters
    python triage/scripts/p_archetype.py --part 4    # budget, all characters
    python triage/scripts/p_archetype.py --part 5    # Regent split, window text vs current
    python triage/scripts/p_archetype.py --part 6    # POST HOC: archetypes as the unit

Run from the repository root. Output: triage/out_final/p_*.csv (TRIAGE_OUT overrides).

Card text. Full text exists only in reference/raw/cards.json (stable v0.107.1's text), which
this script reads read-only; P_CARDS names another copy of it. Text in force at an earlier
build is rebuilt from it: reference/card_changes.csv's old descriptions (cut at about 80
characters by the source, flagged `truncated`), then TEXT_AT below, old wordings quoted in the
patch notes that card_changes doesn't carry. Cards with a rework whose earlier wording is in
neither are flagged `earlier text unknown` and keep the later text.

Part 1  p_archetype_rules.csv, p_archetypes.csv (one row per window, card)
Part 2  p_changes.csv (one row per window, archetype, changed member), p_archetype_windows.csv
Part 3  p_test_pairs.csv, p_test.csv
Part 4  p_budget.csv
Part 5  p_regent.csv, p_regent_split.csv
Part 6  POST HOC, added after reading part 3: p_posthoc_archetypes.csv (each archetype's mean z
        against its character-window's other pairs), p_posthoc_summary.csv
"""
import argparse
import json
import os
import pathlib
import re
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, "triage/scripts")

OUT = os.environ.get("TRIAGE_OUT", "triage/out_final")
CARDS = os.environ.get("P_CARDS") or "reference/raw/cards.json"
REF = pathlib.Path("reference")
PLACEBO = "data/analysis/placebo_h3.parquet"
COLORS = ("defect", "ironclad", "necrobinder", "regent", "silent")
TEST_COLORS = ("defect", "ironclad", "necrobinder", "silent")
POOL_RARITIES = ("Common", "Uncommon", "Rare")
STATES = ("v0.99.1", "v0.103.2", "v0.107.1")          # text states; v0.103.3 = v0.103.2
WINDOWS = {"first": ("v0.99.1", "v0.103.2"), "second": ("v0.103.2", "v0.107.1")}
WINDOW_STABLE = {"first": ("v0.103.2",), "second": ("v0.103.3", "v0.107.1")}
BLOCKS = {"first": ("v0.99.1", "v0.103.2"), "second": ("v0.103.3", "v0.107.1")}
MIN_MEMBERS = 3
SEED, N_PERM = 20261110, 10000
FACTORS = {"first": 4.10, "second": 2.67}
KEY = ["color", "before_builds", "after_builds"]
PAIR = KEY + ["fit_on", "pseudo_card"]

# ------------------------------------------------------------------------------- the rules
# name, colors it applies to (None = all five), regex on the card's text (markup removed, one
# line), and structured fields that also make a member. A card is a member of every archetype
# it matches. An archetype exists for a character in a window when at least MIN_MEMBERS of its
# reward-pool cards (Common, Uncommon, Rare) match.
SELF_HP = r"(?<!nemy )(?<!nemies )\b[Ll]ose \d+ HP|\blost HP|you lose HP|lose \d+ HP and"
RULES = [
    # the discovery's archetype, same wording for every character: makes cards, or pays off
    # making them
    ("create", None, r"\b[Aa]dds? (?:a |an |\d+ |X )?.*\b(?:into|to) (?:your|their) (?:Hand|Draw Pile|Discard Pile)"
                     r"|Transform|\bcop(?:y|ies) of|[Cc]reated?\b|Fill your Hand", {}),
    ("exhaust", None, r"Exhaust", {}),                       # in the text; the keyword alone doesn't count
    ("debuff", None, r"\bWeak\b|Vulnerable|debuff", {}),
    ("strength", None, r"[Gg]ain \d+ Strength", {}),
    ("attack_play", None, r"\bAttacks?\b", {}),
    ("skill_play", None, r"\bSkills?\b", {}),
    ("power_play", None, r"\bPowers?\b", {}),
    ("block_payoff", None, r"your Block\b|gain Block\b|Block is not removed|Block from a card|Block gain|Gain Block equal", {}),
    ("draw", None, r"[Dd]raw \d+ (?:additional )?cards?|[Dd]raw cards|[Ww]henever you draw|draw an? |cards? drawn", {}),
    ("discard", None, r"\b[Dd]iscard(?:ed)? (?!Pile)|\bSly\b", {"keywords": {"Sly"}}),
    ("hp_loss", None, SELF_HP, {}),
    ("zero_cost", None, r"0 ?\[energy:1\] (?:cards?|Attacks?|copy)|do not cost 0", {}),   # cards that cost 0, as a group
    ("ethereal", None, r"Ethereal", {"keywords": {"Ethereal"}}),
    ("dexterity", None, r"Dexterity", {}),
    ("orb", ("defect",), r"Channel|Evoke|\bOrbs?\b", {}),
    ("lightning", ("defect",), r"Lightning", {}),
    ("frost", ("defect",), r"Frost", {}),
    ("dark", ("defect",), r"\bDark\b", {}),
    ("focus", ("defect",), r"Focus", {}),
    ("status", ("defect",), r"Status", {"spawns": {"DAZED", "WOUND", "SLIMED", "BURN", "VOID"}}),
    ("poison", ("silent",), r"Poison", {}),
    ("shiv", ("silent",), r"Shivs?\b", {"spawns": {"SHIV"}}),
    ("osty", ("necrobinder",), r"Osty|Summon", {"tags": {"OstyAttack"}}),
    ("doom", ("necrobinder",), r"Doom", {}),
    ("soul", ("necrobinder",), r"\bSouls?\b", {"spawns": {"SOUL"}}),
    ("forge", ("regent",), r"Forge|Sovereign Blade", {}),
    ("star", ("regent",), r"\[star:", {"star_cost": True}),
]

# Earlier wordings that card_changes.csv doesn't carry: (card, text state) -> (text, source).
# None = the card didn't exist in that state. Numbers don't matter to the rules.
TEXT_AT = {
    ("ARSENAL", "v0.99.1"): ("Whenever you play a Colorless Card, gain 1 Strength.",
                             "patch notes v0.101.0, old text quoted"),
    ("BLADE_OF_INK", "v0.99.1"): ("This turn, whenever you play an Attack, gain 2 Strength this turn.",
                                  "patch notes v0.102.0, old text quoted"),
    ("BORROWED_TIME", "v0.99.1"): ("Apply 3 Doom to yourself. Gain [energy:1].",
                                   "patch notes v0.102.0, old text quoted"),
    ("SPOILS_OF_BATTLE", "v0.99.1"): ("Forge 10.", "patch notes v0.100.0/v0.101.0: draw added in v0.101.0"),
    ("BEGONE", "v0.99.1"): ("Deal 4 damage. Choose a card in your Hand to Transform into Minion Dive Bomb.",
                            "patch notes v0.100.0 and card_changes fields; wording rebuilt, not quoted"),
    ("CHARGE", "v0.99.1"): ("Choose 2 cards in your Draw Pile to Transform into Minion Strikes.",
                            "patch notes v0.100.0; wording rebuilt, not quoted"),
    ("CINDER", "v0.99.1"): ("Deal 17 damage. Exhaust the top card of your Draw Pile.",
                            "patch notes v0.101.0; wording rebuilt, not quoted"),
    ("NOT_YET", "v0.99.1"): (None, "added in v0.103.2"),
    ("CONFLAGRATION", "v0.103.2"): ("Deal 8 damage to ALL enemies. Deals 2 additional damage for each other "
                                    "Attack you've played this turn.", "patch notes v0.104.0, old text quoted"),
    ("DRUM_OF_BATTLE", "v0.103.2"): ("Draw 2 cards. At the start of your turn, Exhaust the top card of your "
                                     "Draw Pile.", "patch notes v0.104.0, old text quoted"),
    ("ASTRAL_PULSE", "v0.103.2"): ("Deal 14 damage to ALL enemies.", "patch notes v0.106.0"),
    ("SCARE", "v0.103.2"): (None, "added in v0.107.1"),
}
# reworks whose earlier wording is in neither source: the later text stands in, flagged
UNKNOWN_BEFORE = {("STOKE", "v0.99.1"), ("DOMINATE", "v0.99.1"), ("SPITE", "v0.99.1"),
                  ("GLOW", "v0.99.1"), ("SHATTER", "v0.103.2")}
# structured fields rolled back with card_changes (keywords, spawns)
VERB_SIGN = {"Buffed": 1, "Nerfed": -1}
NOT_BALANCE = {"bug fix", "art", "writing", "audio", "user interface & experience"}


def clean(text):
    return re.sub(r"\[/?(?:gold|blue|red|green|purple|b|i)\]", "", text or "").replace("\n", " ")


def csv(name):
    return pd.read_csv(REF / name, dtype=str, keep_default_na=False)


# ---------------------------------------------------------------------------------- part 1

def card_states():
    """One row per (text state, card) for the five characters' cards: the text in force and
    the structured fields the rules use."""
    cards = [c for c in json.loads(pathlib.Path(CARDS).read_bytes()) if c.get("color") in COLORS]
    cc = csv("card_changes.csv")
    rows = []
    for c in cards:
        cur = dict(card_id=c["id"], name=c["name"], color=c["color"], rarity=c["rarity"] or "",
                   text=clean(c["description"]), keywords=set(c["keywords"] or []),
                   spawns=set(c["spawns_cards"] or []), tags=set(c["tags"] or []),
                   star_cost=c["star_cost"] is not None, exists=True, text_source="cards.json")
        ch = cc[cc.card_id == c["id"]]
        for state, undo in (("v0.107.1", None), ("v0.103.2", "v0.107.1"), ("v0.99.1", "v0.103.2")):
            if undo:
                cur = dict(cur, keywords=set(cur["keywords"]), spawns=set(cur["spawns"]))
                for r in ch[ch.stable_build == undo].itertuples():
                    if r.field == "description":
                        cur["text"] = clean(r.old)
                        cur["text_source"] = (f"card_changes old, {undo}"
                                              + (", truncated" if r.old.endswith("...") else ""))
                    elif r.field.startswith("keywords["):
                        cur["keywords"] = (cur["keywords"] - {r.new}) | ({r.old} - {"none"})
                    elif r.field.startswith("spawns_cards["):
                        cur["spawns"] = (cur["spawns"] - {r.new}) | ({r.old} - {"none"})
                    elif r.field == "rarity":
                        cur["rarity"] = r.old
                    elif r.field == "star_cost":
                        cur["star_cost"] = r.old != "none"
                    elif r.field == "(card)" and r.old == "none":
                        cur["exists"] = False
                if (c["id"], state) in TEXT_AT:
                    text, src = TEXT_AT[(c["id"], state)]
                    if text is None:
                        cur["exists"] = False
                    else:
                        cur["text"], cur["text_source"] = text, src
                if (c["id"], state) in UNKNOWN_BEFORE:
                    cur["text_source"] = "earlier text unknown; later text used"
            rows.append(dict(cur, state=state))
    return pd.DataFrame(rows)


def matches(row):
    out = []
    for name, colors, rx, fields in RULES:
        if colors and row["color"] not in colors:
            continue
        hit = bool(re.search(rx, row["text"]))
        hit |= bool(fields.get("keywords", set()) & row["keywords"])
        hit |= bool(fields.get("spawns", set()) & row["spawns"])
        hit |= bool(fields.get("tags", set()) & row["tags"])
        hit |= bool(fields.get("star_cost")) and row["star_cost"]
        if hit:
            out.append(name)
    return out


def archetypes():
    """card -> archetypes per window. `before` and `after` are the memberships under the text
    of each side of the window; a placebo card's archetypes are their union (the same thing
    unless its wording changed, in which case it isn't a placebo card)."""
    S = card_states()
    S["arch"] = [matches(r) if r["exists"] else [] for r in S.to_dict("records")]
    by = S.set_index(["state", "card_id"])
    # a cut or missing earlier text can't show that a card was outside an archetype: such a
    # state also keeps the memberships of the next later state
    for state, later in (("v0.103.2", "v0.107.1"), ("v0.99.1", "v0.103.2")):
        for cid in by.loc[state].index:
            src = by.at[(state, cid), "text_source"]
            if by.at[(state, cid), "exists"] and ("truncated" in src or "unknown" in src):
                by.at[(state, cid), "arch"] = sorted(set(by.at[(state, cid), "arch"])
                                                     | set(by.at[(later, cid), "arch"]))
    rows = []
    for w, (sb, sa) in WINDOWS.items():
        for cid in by.loc[sa].index:
            b, a = by.loc[(sb, cid)], by.loc[(sa, cid)]
            rows.append(dict(window=w, color=a.color, card_id=cid, name=a["name"], rarity_after=a.rarity,
                             exists_before=b.exists, exists_after=a.exists,
                             arch_before=" ".join(b.arch), arch_after=" ".join(a.arch),
                             archetypes=" ".join(sorted(set(b.arch) | set(a.arch))),
                             text_before=b.text if b.exists else "", text_after=a.text if a.exists else "",
                             source_before=b.text_source, source_after=a.text_source))
    A = pd.DataFrame(rows)
    # an archetype exists for a character-window with >= MIN_MEMBERS reward-pool members
    pool = A[A.rarity_after.isin(POOL_RARITIES)]
    n = pool.assign(a=pool.archetypes.str.split()).explode("a").dropna(subset=["a"])
    n = n.groupby(["window", "color", "a"]).size()
    live = set(n[n >= MIN_MEMBERS].index)
    for col in ("arch_before", "arch_after", "archetypes"):
        A[col] = [" ".join(x for x in v.split() if (w, c, x) in live)
                  for w, c, v in zip(A.window, A.color, A[col])]
    return A, n.rename("n_pool_members").reset_index().rename(columns={"a": "archetype"})


# ---------------------------------------------------------------------------------- part 2

def card_directions():
    """One row per (window, changed card of the five colors): its events in the window, the
    patch notes' verbs, and one direction. buff / nerf: every balance note on it in the window
    says Buffed / Nerfed. unclear: verbs mixed, or Changed / Reworked, or a cost, rarity or
    mechanic change the notes don't call either. none: wording, art and bug-fix behavior only,
    or a beta change reverted before stable (net zero)."""
    ce, pn = csv("change_events.csv"), csv("patch_notes_cards.csv")
    pn = pn[(pn.role == "subject") & ~pn.section.isin(NOT_BALANCE)]
    rows = []
    for w, stables in WINDOW_STABLE.items():
        e = ce[ce.window_stable.isin(stables) & ce.color.isin(COLORS)]
        for (color, card), g in e.groupby(["color", "card_id"]):
            verbs, kinds, notes, substantive = [], [], [], False
            for r in g.itertuples():
                kinds.append(r.change_kind)
                if r.change_kind == "behavior" or "revert" in r.status or r.change_kind == "revert":
                    continue
                if r.change_kind == "text_only" and r.text_only_label == "wording":
                    continue
                n = pn[(pn.card_id == card) & (pn.version == r.event_build)]
                substantive = True
                verbs += sorted(set(n.verb) - {""})     # an event with no balance note adds no verb
                notes += list(n.raw_text)
            signs = {VERB_SIGN.get(v, 0) for v in verbs}
            direction = ("none" if not substantive else "buff" if signs == {1} else
                         "nerf" if signs == {-1} else "unclear")
            rows.append(dict(window=w, color=color, card_id=card, events=" ".join(g.event_id),
                             kinds=" | ".join(kinds), verbs=" | ".join(verbs), direction=direction,
                             field_changes=" || ".join(x for x in g.field_changes if x),
                             notes=" || ".join(dict.fromkeys(notes))))
    return pd.DataFrame(rows)


def changes_by_archetype(A, D):
    """Every changed member of every archetype, per window, with how it counts for that
    archetype: its own direction, except that a card whose text enters the archetype (or is
    added to the game) counts as a buff to it and one that leaves counts as a nerf."""
    a = A.set_index(["window", "card_id"])
    rows = []
    for d in D.itertuples():
        if (d.window, d.card_id) not in a.index:
            continue
        c = a.loc[(d.window, d.card_id)]
        before, after = set(c.arch_before.split()), set(c.arch_after.split())
        for arch in sorted(before | after):
            member = ("both" if arch in before and arch in after else
                      "entered" if arch in after else "left")
            counts = {"entered": "buff", "left": "nerf"}.get(member, d.direction)
            rows.append(dict(window=d.window, color=d.color, archetype=arch, card_id=d.card_id,
                             membership=member, card_direction=d.direction, counts_as=counts,
                             counts_as_verbs_only=d.direction, kinds=d.kinds, verbs=d.verbs,
                             field_changes=d.field_changes, notes=d.notes))
    C = pd.DataFrame(rows)
    out = []
    for (w, color, arch), g in C.groupby(["window", "color", "archetype"]):
        row = dict(window=w, color=color, archetype=arch, n_changed=len(g))
        for col, tag in (("counts_as", ""), ("counts_as_verbs_only", "_verbs_only")):
            nb, nn = int((g[col] == "buff").sum()), int((g[col] == "nerf").sum())
            nu = int((g[col] == "unclear").sum())
            row.update({f"n_buff{tag}": nb, f"n_nerf{tag}": nn, f"n_unclear{tag}": nu,
                        f"net{tag}": net_direction(nb, nn, nu)})
        row["changed_members"] = " ".join(f"{c}({x})" for c, x in zip(g.card_id, g.counts_as))
        out.append(row)
    return C, pd.DataFrame(out)


def net_direction(n_buff, n_nerf, n_unclear):
    if n_buff > n_nerf:
        return "buff"
    if n_nerf > n_buff:
        return "nerf"
    return "unclear" if n_buff + n_nerf + n_unclear else "none"


# ---------------------------------------------------------------------------------- part 3

def robust_sd(z):
    z = np.asarray(z, float)
    return 1.4826 * np.median(np.abs(z - np.median(z)))


def label_pairs(P, A, W, net="net"):
    """Adds to each placebo pair its archetypes, the ones with a net buff / nerf in its
    window, and the predicted sign d: +1 only buffed archetypes, -1 only nerfed, 0 neither,
    NaN both (conflicted, left out of both groups)."""
    arch = A.set_index(["window", "card_id"]).archetypes
    nets = W.set_index(["window", "color", "archetype"])[net].to_dict()
    P = P.copy()
    P["archetypes"] = [arch.get((w, c), "") for w, c in zip(P.patch, P.pseudo_card)]
    up, down, anyc, d = [], [], [], []
    for w, color, a in zip(P.patch, P.color, P.archetypes):
        dirs = {x: nets.get((w, color, x), "none") for x in a.split()}
        u = [x for x, v in dirs.items() if v == "buff"]
        n = [x for x, v in dirs.items() if v == "nerf"]
        up.append(" ".join(u)); down.append(" ".join(n))
        anyc.append(" ".join(x for x, v in dirs.items() if v != "none"))
        d.append(np.nan if u and n else 1.0 if u else -1.0 if n else 0.0)
    P["arch_buffed"], P["arch_nerfed"], P["arch_changed"], P["d"] = up, down, anyc, d
    return P


def shift(z, d, strata):
    """Mean over exposed pairs of d * (z - mean z of the unexposed pairs in the same
    stratum). Strata without both groups contribute nothing."""
    tot, n = 0.0, 0
    for s in np.unique(strata):
        m = strata == s
        zs, ds = z[m], d[m]
        if (ds == 0).any() and (ds != 0).any():
            tot += (ds[ds != 0] * (zs[ds != 0] - zs[ds == 0].mean())).sum()
            n += int((ds != 0).sum())
    return tot / n if n else np.nan, n


def perm_test(z, d, strata, n_perm=N_PERM, seed=SEED):
    """Labels d shuffled across pairs within each stratum (character-window)."""
    rng = np.random.default_rng(seed)
    obs, n = shift(z, d, strata)
    if not n:
        return obs, n, np.nan, np.nan
    idx = [np.flatnonzero(strata == s) for s in np.unique(strata)]
    null = np.empty(n_perm)
    for i in range(n_perm):
        dp = d.copy()
        for ix in idx:
            dp[ix] = d[rng.permutation(ix)]
        null[i] = shift(z, dp, strata)[0]
    p_one = (1 + (null >= obs).sum()) / (1 + n_perm)
    p_two = (1 + (np.abs(null) >= abs(obs)).sum()) / (1 + n_perm)
    return obs, n, p_one, p_two


def test_table(L, label):
    """Per character and pooled over the test characters."""
    rows = []
    T = L[L.d.notna()].copy()
    T["stratum"] = T.color + " " + T.patch
    scopes = [(c, T[T.color == c]) for c in TEST_COLORS]
    scopes += [(f"{c} {p}", T[(T.color == c) & (T.patch == p)]) for c in TEST_COLORS
               for p in ("first", "second")]
    scopes += [("pooled first", T[T.patch == "first"]), ("pooled second", T[T.patch == "second"]),
               ("pooled", T)]
    for name, g in scopes:
        if not len(g):
            continue
        z, d, s = g.z.to_numpy(), g.d.to_numpy(), g.stratum.to_numpy()
        obs, n, p1, p2 = perm_test(z, d, s)
        e = g[g.d != 0]
        signed = np.sign(e.d * e.z)
        up, dn, other = g[g.d == 1], g[g.d == -1], g[g.d == 0]
        rows.append(dict(
            definition=label, scope=name, n_pairs=len(g), n_buff_exposed=len(up),
            n_nerf_exposed=len(dn), n_other=len(other), n_in_test=n, shift_predicted=obs,
            p_one_sided=p1, p_two_sided=p2, mean_z_buff=up.z.mean(), mean_z_nerf=dn.z.mean(),
            mean_z_other=other.z.mean(), n_sign_as_predicted=int((signed > 0).sum()),
            n_exposed=len(e), share_z_pos_buff=(up.z > 0).mean(), share_z_pos_nerf=(dn.z > 0).mean(),
            share_z_pos_other=(other.z > 0).mean()))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------- part 4

def demean_archetype(L, col):
    """Residual of z on archetype x window terms (one indicator per character-window and
    archetype named in `col`; a card in several gets several) and a character-window
    intercept, by least squares."""
    cw = L.color + " " + L.patch
    X = pd.get_dummies(cw).astype(float)
    terms = L[col].str.split().apply(lambda v: [f"{x}" for x in v])
    for i, (c, v) in enumerate(zip(cw, terms)):
        for x in v:
            X.loc[L.index[i], f"{c}|{x}"] = 1.0
    X = X.fillna(0.0)
    X = X.loc[:, X.sum() > 0]
    beta, *_ = np.linalg.lstsq(X.to_numpy(), L.z.to_numpy(), rcond=None)
    return L.z.to_numpy() - X.to_numpy() @ beta, X.shape[1] - cw.nunique()


def budget(L, n_perm=1000):
    rng = np.random.default_rng(SEED + 1)
    rows = []
    cw = (L.color + " " + L.patch).to_numpy()
    for col, what in (("arch_changed", "any substantive change to a member"),
                      ("arch_net", "net buff or nerf only")):
        exposed = (L[col] != "").to_numpy()
        res, k = demean_archetype(L, col)
        # benchmark: the same archetype sets dealt to other cards of the same character-window
        null_drop = {p: [] for p in FACTORS}
        null_res = {p: [] for p in FACTORS}
        for _ in range(n_perm):
            Lp = L.copy()
            for s in np.unique(cw):
                ix = np.flatnonzero(cw == s)
                Lp.iloc[ix, Lp.columns.get_loc(col)] = L[col].to_numpy()[rng.permutation(ix)]
            rp, _ = demean_archetype(Lp, col)
            ep = (Lp[col] != "").to_numpy()
            for p in FACTORS:
                m = (L.patch == p).to_numpy()
                null_drop[p].append(robust_sd(L.z.to_numpy()[m & ~ep]))
                null_res[p].append(robust_sd(rp[m]))
        for p, f in FACTORS.items():
            m = (L.patch == p).to_numpy()
            z = L.z.to_numpy()
            rows.append(dict(
                exposure=what, patch=p, factor=f, n_pairs=int(m.sum()), robust_sd_all=robust_sd(z[m]),
                n_exposed=int((m & exposed).sum()), robust_sd_exposed_removed=robust_sd(z[m & ~exposed]),
                removed_shuffled_mean=np.mean(null_drop[p]),
                removed_shuffled_lo=np.percentile(null_drop[p], 2.5),
                removed_shuffled_hi=np.percentile(null_drop[p], 97.5),
                robust_sd_exposed_only=robust_sd(z[m & exposed]) if (m & exposed).any() else np.nan,
                n_terms=k, robust_sd_demeaned=robust_sd(res[m]),
                demeaned_shuffled_mean=np.mean(null_res[p]),
                demeaned_shuffled_lo=np.percentile(null_res[p], 2.5),
                demeaned_shuffled_hi=np.percentile(null_res[p], 97.5),
                sd_all=z[m].std(ddof=1), sd_demeaned=res[m].std(ddof=1)))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------- part 5

def regent(L, A):
    """Regent placebo pairs, all offers: the create archetype under each window's own text
    and under the current text (cards.json) for both windows; cards that differ."""
    cur = A[(A.window == "second")].set_index("card_id").arch_after       # v0.107.1 text
    R = L[(L.color == "regent") & (L.fit_on == "all offers")].copy()
    R["create_window_text"] = R.archetypes.str.split().apply(lambda v: "create" in v)
    R["create_current_text"] = R.pseudo_card.map(cur).fillna("").str.split().apply(lambda v: "create" in v)
    R["changed_class"] = R.create_window_text != R.create_current_text
    rows = []
    for p, g in R.groupby("patch"):
        for col in ("create_window_text", "create_current_text"):
            a, b = g[g[col]], g[~g[col]]
            rows.append(dict(patch=p, split=col, n_create=len(a), n_create_z_pos=int((a.z > 0).sum()),
                             mean_z_create=a.z.mean(), n_other=len(b), n_other_z_pos=int((b.z > 0).sum()),
                             share_other_z_pos=(b.z > 0).mean(), mean_z_other=b.z.mean(),
                             create_cards=" ".join(f"{c}({z:+.1f})" for c, z in zip(a.pseudo_card, a.z))))
    cols = ["patch", "pseudo_card", "z", "archetypes", "create_window_text", "create_current_text",
            "changed_class"]
    return R[cols], pd.DataFrame(rows)


# ---------------------------------------------------------------------------------- part 6

def posthoc_archetypes(L, W):
    """POST HOC, added after reading part 3. One row per character-window and archetype with
    at least 2 all-offers placebo pairs, whatever its net direction: members' mean z minus the
    mean z of the character-window's other pairs. Shows which archetypes carry the pooled
    shift, and whether archetypes with no net direction sit as far from their character's
    other cards as the ones with one (if they do, cards of an archetype move together anyway,
    and the pair-level permutation p is too small)."""
    nets = W.set_index(["window", "color", "archetype"])
    T = L[L.fit_on == "all offers"]
    rows = []
    for (color, patch), g in T.groupby(["color", "patch"]):
        sets = g.archetypes.str.split()
        for a in sorted({x for v in sets for x in v}):
            m = sets.apply(lambda v: a in v).to_numpy()
            if m.sum() < 2 or (~m).sum() < 2:
                continue
            net = nets.net.get((patch, color, a), "none")
            diff = g.z[m].mean() - g.z[~m].mean()
            sign = {"buff": 1, "nerf": -1}.get(net, 0)
            rows.append(dict(color=color, patch=patch, archetype=a, net=net,
                             changed_members=nets.changed_members.get((patch, color, a), ""),
                             n_pairs=int(m.sum()), mean_z=g.z[m].mean(), mean_z_rest=g.z[~m].mean(),
                             diff=diff, n_z_pos=int((g.z[m] > 0).sum()),
                             as_predicted="" if not sign else "yes" if sign * diff > 0 else "no",
                             test_character=color in TEST_COLORS))
    return pd.DataFrame(rows)


def posthoc_summary(H, n_perm=N_PERM):
    """POST HOC. Archetype-windows as the unit: sign agreement among those with a net
    direction, and the size of |diff| with and without one. Test characters only."""
    rng = np.random.default_rng(SEED + 2)
    H = H[H.test_character]
    d = H[H.net.isin(["buff", "nerf"])]
    s = np.where(d.net == "buff", 1.0, -1.0)
    obs = (s * d["diff"]).mean()
    null = np.array([(rng.choice([-1.0, 1.0], len(d)) * d["diff"].to_numpy()).mean()
                     for _ in range(n_perm)])                 # each archetype's sign flipped
    from math import comb
    k, n = int((d.as_predicted == "yes").sum()), len(d)
    p_sign = min(1.0, 2 * sum(comb(n, i) for i in range(k, n + 1)) / 2 ** n) if k >= n / 2 else \
        min(1.0, 2 * sum(comb(n, i) for i in range(0, k + 1)) / 2 ** n)
    und = H[~H.net.isin(["buff", "nerf"])]
    return pd.DataFrame([dict(
        n_directed=n, n_as_predicted=k, p_sign_two_sided=p_sign, mean_signed_diff=obs,
        p_sign_flip_two_sided=(1 + (np.abs(null) >= abs(obs)).sum()) / (1 + n_perm),
        mean_abs_diff_directed=d["diff"].abs().mean(), median_abs_diff_directed=d["diff"].abs().median(),
        n_undirected=len(und), mean_abs_diff_undirected=und["diff"].abs().mean(),
        median_abs_diff_undirected=und["diff"].abs().median())])


# ------------------------------------------------------------------------------------- main

def check():
    """Known answers for the rules and the statistic. No data read."""
    def m(text, color="ironclad", **kw):
        row = dict(color=color, text=text, keywords=set(), spawns=set(), tags=set(), star_cost=False)
        row.update(kw)
        return set(matches(row))
    assert "create" in m("Deal 6 damage. Add a copy of this card into your Discard Pile.")
    assert "create" in m("Add 3 Shivs into your Hand.", "silent") and "shiv" in m("x", "silent", spawns={"SHIV"})
    assert "create" in m("Another player adds 1 random Colorless card to their Hand.", "regent")
    assert "create" not in m("Put a card from your Discard Pile into your Hand.")
    assert "create" not in m("Put Sovereign Blade into your Hand from anywhere. Forge 8.", "regent")
    assert "hp_loss" in m("Lose 3 HP. Gain [energy:2].") and "hp_loss" in m("If you lost HP this turn, hits 2 times.")
    assert "hp_loss" not in m("Enemy loses 3 HP. Add 3 Souls into your Draw Pile.", "necrobinder")
    assert "hp_loss" in m("At the start of your turn, lose 1 HP and gain 8 Block.")
    assert "exhaust" not in m("Gain 30 Block.", keywords={"Exhaust"})
    assert "discard" in m("Gain 6 Block.", "silent", keywords={"Sly"})
    assert "discard" not in m("Put a card from your Discard Pile on top of your Draw Pile.")
    assert "strength" not in m("Deal 15 damage. Enemy loses 10 Strength this turn.")
    assert "orb" not in m("Channel 1 Frost.", "silent") and {"orb", "frost"} <= m("Channel 1 Frost.", "defect")
    assert net_direction(3, 0, 3) == "buff" and net_direction(1, 1, 0) == "unclear"
    assert net_direction(0, 0, 0) == "none" and net_direction(0, 2, 1) == "nerf"
    # statistic: a planted shift of +2 on buff-exposed and -2 on nerf-exposed comes back as 2
    rng = np.random.default_rng(0)
    d = rng.choice([0.0, 0.0, 0.0, 1.0, -1.0], 4000)
    s = rng.choice(["a", "b", "c", "d"], 4000)
    z = 3 * rng.standard_normal(4000) + pd.Series(s).map(dict(a=0, b=1, c=-1, d=5)).to_numpy()
    assert abs(shift(z + 2 * d, d, s)[0] - 2) < 0.2 and abs(shift(z, d, s)[0]) < 0.2
    ps = [perm_test(3 * rng.standard_normal(200), rng.choice([0.0, 0.0, 1.0, -1.0], 200),
                    rng.choice(["a", "b"], 200), 200, i)[3] for i in range(200)]
    assert 0.02 < np.mean(np.array(ps) < 0.05) < 0.10, np.mean(np.array(ps) < 0.05)   # size
    print("check: rules, net direction, shift and permutation size ok "
          f"(null rejection rate {np.mean(np.array(ps) < 0.05):.3f})")


def load_pairs():
    import db
    from spirometry import did
    db.use_derived_colors()
    P = did.placebo_pairs(pd.read_parquet(PLACEBO))
    if len(P) != 463 or round(robust_sd(P.z[P.patch == "first"]), 2) != FACTORS["first"]:
        raise SystemExit("placebo_h3 does not give 463 pairs and the 4.10 factor")
    for p, (b, a) in BLOCKS.items():
        g = P[P.patch == p]
        assert set(g.before_builds) == {b} and set(g.after_builds) == {a}, (p, b, a)
    return P


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--part", type=int, choices=[1, 2, 3, 4, 5, 6], action="append")
    args = ap.parse_args()
    T0 = time.time()
    pd.set_option("display.width", 250, "display.max_columns", 40, "display.max_rows", 600,
                  "display.max_colwidth", 90, "display.float_format", "{:.3f}".format)
    os.makedirs(OUT, exist_ok=True)
    parts = set(args.part or [])
    if args.check:
        check()
    if parts:
        A, N = archetypes()
        D = card_directions()
        C, W = changes_by_archetype(A, D)
    if 1 in parts:
        pd.DataFrame([dict(archetype=n, characters=" ".join(c) if c else "all", text_regex=rx,
                           also_member_by=" ".join(f"{k}:{'|'.join(sorted(v)) if isinstance(v, set) else v}"
                                                   for k, v in f.items()))
                      for n, c, rx, f in RULES]).to_csv(f"{OUT}/p_archetype_rules.csv", index=False)
        A.to_csv(f"{OUT}/p_archetypes.csv", index=False)
        print(N.pivot_table(index="archetype", columns=["window", "color"], values="n_pool_members",
                            fill_value=0).astype(int).to_string())
        print("cards with no archetype:", A[A.archetypes == ""].groupby(["window", "color"]).size().to_dict())
    if 2 in parts:
        C.to_csv(f"{OUT}/p_changes.csv", index=False)
        W.to_csv(f"{OUT}/p_archetype_windows.csv", index=False)
        print(D[["window", "color", "card_id", "kinds", "verbs", "direction"]].to_string(index=False))
        print(W.drop(columns=["changed_members"]).to_string(index=False))
    if parts & {3, 4, 5, 6}:
        P = load_pairs()
        L = label_pairs(P, A, W)
        Lv = label_pairs(P, A, W, net="net_verbs_only")
        top = pd.read_csv(f"{OUT}/o_top_pairs.csv")[["patch", "pseudo_card"]].assign(seen_in_o=True)
        L = L.merge(top, on=["patch", "pseudo_card"], how="left")
        Lv = Lv.merge(top, on=["patch", "pseudo_card"], how="left")
        L["seen_in_o"] = L.seen_in_o.eq(True)
        Lv["seen_in_o"] = Lv.seen_in_o.eq(True)
        assert len(L) == len(P) and L.seen_in_o.sum() >= len(top)   # a card's upgraded-offers pair goes too
    if 3 in parts:
        t = L[L.color.isin(TEST_COLORS) & (L.fit_on == "all offers")]
        tv = Lv[Lv.color.isin(TEST_COLORS) & (Lv.fit_on == "all offers")]
        cols = PAIR + ["patch", "z", "archetypes", "arch_buffed", "arch_nerfed", "arch_changed", "d",
                       "seen_in_o"]
        L[cols].to_csv(f"{OUT}/p_test_pairs.csv", index=False)
        TT = pd.concat([
            test_table(t, "declared: all-offers pairs, entry and exit counted"),
            test_table(tv, "sensitivity: patch-note verbs only"),
            test_table(t[~t.seen_in_o], "sensitivity: pairs shown in section O's top 25 left out"),
            test_table(L[L.color.isin(TEST_COLORS)], "sensitivity: upgraded-offers pairs included"),
        ], ignore_index=True)
        TT.to_csv(f"{OUT}/p_test.csv", index=False)
        print(TT.to_string(index=False))
    if 4 in parts:
        L4 = L.copy()
        L4["arch_net"] = (L4.arch_buffed + " " + L4.arch_nerfed).str.strip()
        B = budget(L4)
        B.to_csv(f"{OUT}/p_budget.csv", index=False)
        print(B.T.to_string())
    if 5 in parts:
        R, RS = regent(L, A)
        R.to_csv(f"{OUT}/p_regent.csv", index=False)
        RS.to_csv(f"{OUT}/p_regent_split.csv", index=False)
        print(RS.to_string(index=False))
        print(R[R.create_window_text | R.create_current_text].to_string(index=False))
    if 6 in parts:
        H = posthoc_archetypes(L, W)
        H.to_csv(f"{OUT}/p_posthoc_archetypes.csv", index=False)
        HS = posthoc_summary(H)
        HS.to_csv(f"{OUT}/p_posthoc_summary.csv", index=False)
        print(H.drop(columns=["changed_members"]).to_string(index=False))
        print(HS.T.to_string())
    print(f"done in {time.time() - T0:.0f} s")
