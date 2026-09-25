import csv
import pathlib

import pytest

from spirometry import patch_notes as pn

REPO = pathlib.Path(__file__).resolve().parents[1]
WIKI = REPO / "reference" / "raw" / "wiki"


@pytest.fixture(scope="module")
def names():
    return pn.load_names(REPO / "reference")


def page(version, label):
    return (WIKI / f"Slay_the_Spire_2__{version}_-_{label}.wikitext").read_text()


def rows_for(rows, card_id):
    return [r for r in rows if r["card_id"] == card_id]


def test_header_and_branch():
    assert pn.page_header(page("V0.100.0", "Beta_Patch")) == ("v0.100.0", "Beta Patch", "2026-03-19")
    assert pn.branch_of("Beta Hotfix") == "beta"
    assert pn.branch_of("Major Update") == "stable"
    assert pn.branch_of("Patch") == "stable"


def test_numeric_changes():
    assert pn.numeric_changes("Damage increased from 7(9) -> 10(12)") == [("damage", "7", "9", "10", "12")]
    assert pn.numeric_changes("Cost increased from 6 -> 9(7)") == [("cost", "6", "", "9", "7")]
    assert pn.numeric_changes("Forge increased from 5(8) → 6(9)") == [("forge", "5", "8", "6", "9")]
    # ranges and quoted card text are not changes
    assert pn.numeric_changes("HP at A8 increased from 24-28(25-29) → 24-28(26-30)") == []
    assert pn.numeric_changes('"Discard 2 cards." -> "Draw 1 card."') == []


def test_v0100_balance_rows(names):
    rows = pn.parse_page(page("V0.100.0", "Beta_Patch"), names)
    deb = rows_for(rows, "DEBILITATE")
    assert len(deb) == 1
    d = deb[0]
    assert (d["section"], d["verb"], d["branch"], d["date"]) == ("balance", "Buffed", "beta", "2026-03-19")
    assert (d["before_base"], d["before_upg"], d["after_base"], d["after_upg"]) == ("7", "9", "10", "12")
    # two numeric changes -> two rows
    assert [r["quantity"] for r in rows_for(rows, "CAPTURE_SPIRIT")] == ["hp loss", "souls generated"]
    # writing section, two cards in one line, both subjects
    w = [r for r in rows if r["section"] == "writing"]
    assert {r["card_id"] for r in w} >= {"BOMBARDMENT", "HOWL_FROM_BEYOND"}
    # apostrophes inside bold names
    assert rows_for(rows, "BANSHEES_CRY") and rows_for(rows, "NEOWS_FURY")
    # a card that exists only in this beta
    prep = rows_for(rows, "PREPARE")
    assert prep and prep[0]["in_card_list"] == "no"


def test_v0104_bug_fixes_and_wiki_only(names):
    rows = pn.parse_page(page("V0.104.0", "Beta_Patch"), names)
    bomb = [r for r in rows_for(rows, "BOMBARDMENT") if r["section"] == "bug fix"]
    assert bomb and bomb[0]["role"] == "subject"
    pacts = rows_for(rows, "PACTS_END")
    assert pacts[0]["wiki_only"] == "yes"
    # "Changed Tyranny card: now triggers before Bombardment card": Bombardment is context
    tyr = [r for r in rows if "Tyranny" in r["raw_text"] and r["section"] == "balance"]
    assert {(r["card_id"], r["role"]) for r in tyr} == {("TYRANNY", "subject"), ("BOMBARDMENT", "context")}
    # relics and enemies are not cards
    assert not rows_for(rows, "REGALITE")


def test_v0111_templates(names):
    rows = pn.parse_page(page("V0.111.0", "Beta_Patch"), names)
    rend = rows_for(rows, "REND")
    assert [(r["quantity"], r["before_base"], r["after_base"]) for r in rend] == [
        ("energy cost", "2", "1"), ("base damage", "15", "10")]
    assert {r["card_id"] for r in rows if "Salvo" in r["raw_text"]} == {"SALVO", "SPLASH"}
    assert not rows_for(rows, "AXEBOT")                 # {{M2|...}} is a monster


def test_reconcile_builds_fills_and_flags():
    builds = [
        {"build_id": "v0.99.1", "branch": "", "release_date": "", "source": "run data", "notes": ""},
        {"build_id": "v0.105.0", "branch": "beta", "release_date": "2026-05-07",
         "source": "update-history", "notes": ""},
    ]
    pages = [("v0.99.1", "Beta Hotfix", "t1", "{{PatchNav\n|Version = V0.99.1\n|Type = Beta Hotfix\n|ReleaseDate = 2026-03-14\n}}"),
             ("v0.99.1", "Patch", "t2", "{{PatchNav\n|Version = V0.99.1\n|Type = Patch\n|ReleaseDate = 2026-03-17\n}}"),
             ("v0.105.0", "Beta Patch", "t3", "{{PatchNav\n|Version = V0.105.0\n|Type = Beta Patch\n|ReleaseDate = 2026-05-08\n}}"),
             ("v0.110.1", "Beta Hotfix", "t4", "{{PatchNav\n|Version = V0.110.1\n|Type = Beta Hotfix\n|ReleaseDate = 2026-07-31\n}}")]
    out = {r["build_id"]: r for r in pn.reconcile_builds(builds, pages)}
    assert (out["v0.99.1"]["branch"], out["v0.99.1"]["release_date"]) == ("stable", "2026-03-17")
    assert out["v0.105.0"]["release_date"] == "2026-05-07"
    assert "conflict: wiki date 2026-05-08" in out["v0.105.0"]["notes"]
    assert out["v0.110.1"]["source"] == "wiki patch notes"
    again = {r["build_id"]: r for r in pn.reconcile_builds(list(out.values()), pages)}
    assert again == out


def test_committed_csv_has_expected_columns():
    with open(REPO / "reference" / "patch_notes_cards.csv") as f:
        assert next(csv.reader(f)) == pn.PNC_FIELDS


# ------------------------------------------------------------------ cross-check

from spirometry import notes_crosscheck as nc


def note(card, version, section="balance", verb="Buffed", q="", b0="", u0="", b1="", u1="",
         text="", role="subject"):
    return {"card_id": card, "version": version, "section": section, "verb": verb,
            "quantity": q, "before_base": b0, "before_upg": u0, "after_base": b1,
            "after_upg": u1, "raw_text": text, "role": role, "wiki_only": "",
            "in_card_list": "yes", "branch": "beta", "date": ""}


def change(card, field, old, new, stable="v0.103.2", beta="v0.100.0", kind="tweak"):
    return {"card_id": card, "field": field, "old": old, "new": new, "stable_build": stable,
            "beta_build": beta, "change_kind": kind}


def test_window_of():
    assert nc.window_of("v0.100.0") == "v0.103.2"
    assert nc.window_of("v0.103.2") == "v0.103.2"
    assert nc.window_of("v0.104.0") == "v0.107.1"
    assert nc.window_of("v0.103.3") == ""
    assert nc.window_of("v0.99.1") == "" and nc.window_of("v0.108.0") == ""


def test_crosscheck_chains_betas_and_matches_net_change():
    notes = [note("PARRY", "v0.100.0", q="Block", b0="6", u0="9", b1="8", u1="11"),
             note("PARRY", "v0.101.0", q="Block gain", b0="8", u0="11", b1="10", u1="14")]
    changes = [change("PARRY", "vars.ParryPower", "6", "10"),
               change("PARRY", "upgrade.parrypower", "+3", "+4", beta="v0.101.0")]
    [row] = nc.crosscheck(notes, changes, [])
    assert row["agreement"] == "agree: numbers match"
    assert row["version"] == "v0.100.0"


def test_crosscheck_flags_direction_and_missing():
    notes = [note("X", "v0.100.0", q="Damage", b0="7", b1="10"),
             note("Y", "v0.104.0", verb="Nerfed", text="Nerfed Y card: now Exhausts")]
    changes = [change("X", "damage", "10", "7")]
    rows = {r["card_id"]: r for r in nc.crosscheck(notes, changes, [])}
    assert rows["X"]["agreement"] == "disagree: direction"
    assert rows["Y"]["agreement"] == "notes only: missing from card_changes"


def test_crosscheck_reverted_and_table_only_and_labels():
    notes = [note("C", "v0.100.0", verb="Nerfed", q="HP loss", b0="3", u0="4", b1="2", u1="3"),
             note("C", "v0.101.0", verb="Reverted (Buffed)"),
             note("W", "v0.100.0", section="writing", verb="")]
    changes = [change("T", "damage", "1", "2"), change("W", "description_raw", "a", "b",
                                                         kind="text_only")]
    labels = [{"card_id": "W", "stable_build": "v0.103.2", "label": "mechanic"}]
    rows = {r["card_id"]: r for r in nc.crosscheck(notes, changes, labels)}
    assert rows["C"]["agreement"] == "notes only: reverted within beta"
    assert rows["T"]["agreement"] == "table only"
    assert "label mechanic but notes list it under writing" in rows["W"]["agreement"]
