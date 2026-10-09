"""Shared Tier 2 helpers: a read-only connection to runs.duckdb and card colors without
reference/raw/.

spirometry.did.card_colors() reads reference/raw/cards.json, which the triage may not open.
derived_colors() rebuilds the card -> color map from the run tables instead: a card's color
is the character whose primary reward screens hold at least 90% of its offers (character
cards are offered to their own character; colorless cards are spread over all five and get
no color, as under card_colors' use in did.py, where colorless cards are never loaded).
card_changes.csv's color overrides it where that table has the card (see _derived). use_derived_colors() points
did.card_colors at it (a monkeypatch in this process only; src/ is not edited). It is
checked by reproducing saved did_h3 fits to the last digit (i_fake_patch.py --check).

Nothing here prints or writes run-level IDs.
"""
import functools

import duckdb
import pandas as pd

from spirometry import did

DB = "data/runs/runs.duckdb"
CHARS = {f"CHARACTER.{c.upper()}": c for c in did.CHARACTER_COLORS}


def connect():
    return duckdb.connect(DB, read_only=True)


@functools.lru_cache(maxsize=1)
def _derived(share=0.9):
    con = connect()
    n = con.execute("""SELECT card_id, character, count(*) AS n FROM primary_offers
                       GROUP BY ALL""").df()
    con.close()
    n["color"] = n.character.map(CHARS)
    n = n.dropna(subset=["color"])
    tot = n.groupby("card_id").n.transform("sum")
    # at least 1,000 offers: ~170 mod cards without a "-" in their id reach primary_offers
    # with at most ~100 offers each; every character card has thousands
    top = n[(n.n / tot >= share) & (tot >= 1000)]
    colors = dict(zip(top.card_id, top.color))
    # card_changes.csv's color comes from the cached card list (or is blank for a card not
    # in it, which did.card_colors then leaves without a color): it wins where present, so
    # e.g. Entrench and Exterminate ("event" now) are not loaded, as in did.py.
    cc = pd.read_csv("reference/card_changes.csv", dtype=str, keep_default_na=False)
    for r in cc.drop_duplicates("card_id").itertuples():
        if r.color in did.CHARACTER_COLORS:
            colors[r.card_id] = r.color
        else:
            colors.pop(r.card_id, None)
    return colors


def derived_colors(ref=None):
    return dict(_derived())


def use_derived_colors():
    did.card_colors = derived_colors
    return derived_colors()


def check_against_reference():
    """Agreement with card_changes.csv / tweak_sizes.csv colors (where they have one)."""
    col = derived_colors()
    out = {}
    for f in ["reference/card_changes.csv", "reference/tweak_sizes.csv"]:
        t = pd.read_csv(f, dtype=str, keep_default_na=False)
        t = t[t.color != ""].drop_duplicates("card_id")
        got = t.card_id.map(col)
        out[f] = dict(n=len(t), agree=int((got == t.color).sum()),
                      no_color=int(got.isna().sum()),
                      disagree=int((got.notna() & (got != t.color)).sum()),
                      ref_colors=sorted(t.color.unique()))
    return out
