import pathlib

import pytest

from spirometry import patch_history as ph

REPO = pathlib.Path(__file__).resolve().parents[1]


def ch(field, old, new):
    return {"field": field, "old": old, "new": new}


@pytest.mark.parametrize("changes, kind", [
    ([ch("damage", "7", "10"), ch("vars.Damage", "7", "10"), ch("description", "a", "b")], "tweak"),
    ([ch("upgrade.block", "+3", "+4")], "tweak"),
    ([ch("vars.Repeat", "none", "4"), ch("damage", "8", "2")], "rework"),
    ([ch("type", "Power", "Skill"), ch("cost", "0", "1")], "rework+cost_change"),
    ([ch("cost", "2", "1"), ch("block", "8", "9")], "tweak+cost_change"),
    ([ch("cost", "2", "1")], "cost_change"),
    ([ch("rarity", "Common", "Uncommon"), ch("rarity_key", "Common", "Uncommon")], "rarity_change"),
    ([ch("description_raw", "x", "y"), ch("upgrade_description", "a", "b")], "text_only"),
    ([ch("compendium_order", "1", "2")], None),
])
def test_classify(changes, kind):
    assert ph.classify(changes) == kind


def test_vkey_orders_numerically_and_suffix_first():
    vs = ["v0.103.2", "V0.98.0-beta", "v0.98.0", "v0.100.0", "v0.99.1"]
    assert sorted(vs, key=ph.vkey) == ["V0.98.0-beta", "v0.98.0", "v0.99.1", "v0.100.0", "v0.103.2"]


def test_history_label():
    assert ph.history_label("powers_applied[0].amount") == "powers applied[0].amount"
    assert ph.history_label("vars.DebilitatePower") == "vars.debilitatepower"


def test_build_changes_matches_beta_by_field(monkeypatch):
    monkeypatch.setattr(ph, "GAME_CHANGELOGS", {"9.0.0": ("v0.105.0", "stable v0.105.0")})
    changelogs = {"9.0.0": {"title": "stable v0.105.0", "date": "2026-05-10", "categories": [
        {"id": "cards", "changed": [
            {"id": "A", "changes": [ch("block", "13", "12"), ch("compendium_order", "1", "2")]},
            {"id": "B", "changes": [ch("vars.Energy", "none", "2")]}]},
        {"id": "relics", "changed": [{"id": "FAKE_ANCHOR", "changes": [ch("x", "1", "2")]}]}]}}
    histories = {
        "A": [{"version": "V0.104.0", "type": "Beta Patch", "date": "2026-05-01",
               "changes": ["Block: 13 → 12"]},
              {"version": "V0.98.0-beta", "type": "Beta Patch", "date": "2026-03-05",
               "changes": ["Block: 12 → 13"]}],
        "B": [{"version": "V0.103.0", "type": "Beta Patch", "date": "2026-04-09",
               "changes": ["Vars: 3 fields → 4 fields"]},
              {"version": "V0.106.0", "type": "Beta Patch", "date": "2026-05-21",
               "changes": ["Vars: 4 fields → 5 fields"]}],   # after the stable build
    }
    rows, text_rows, excl, unmatched, non_card = ph.build_changes(changelogs, histories, {"A", "B"})
    by_card = {r["card_id"]: r for r in rows}
    assert set(by_card) == {"A", "B"}                       # relics skipped, compendium excluded
    assert by_card["A"]["beta_build"] == "v0.104.0"         # '-beta' flip entry ignored
    assert by_card["A"]["change_kind"] == "tweak"
    assert by_card["B"]["beta_build"] == "v0.103.0"         # whole-'vars' label match
    assert by_card["B"]["change_kind"] == "rework"
    assert non_card == {"relics": 1}
    assert {e["field"] for e in excl} == {"compendium_order"}
    assert [u["version"] for u in unmatched] == ["v0.98.0-beta"]


@pytest.fixture(scope="module")
def cached(tmp_path_factory):
    if not (REPO / "reference/raw/changelogs.json").exists():
        pytest.skip("no cached raw responses")
    monkey = pytest.MonkeyPatch()
    monkey.setattr(ph, "RAW", REPO / "reference/raw")
    cards, changelogs, histories = ph.load_cache()
    monkey.undo()
    ids = {c["id"] for c in cards}
    for cl in changelogs.values():
        ids |= ph.changelog_card_ids(cl)
    return ph.build_changes(changelogs, histories, ids)


@pytest.mark.parametrize("card, stable, beta, kind", [
    ("DEBILITATE", "v0.103.2", "v0.100.0", "tweak"),
    ("DEBILITATE", "v0.107.1", "v0.106.0", "tweak"),
    ("CONFLAGRATION", "v0.107.1", "v0.104.0", "rework"),
    ("DRUM_OF_BATTLE", "v0.107.1", "v0.104.0", "rework+cost_change"),
    ("BULWARK", "v0.107.1", "v0.105.0", "tweak"),
])
def test_known_cards(cached, card, stable, beta, kind):
    rows = [r for r in cached[0] if r["card_id"] == card and r["stable_build"] == stable]
    assert rows
    assert {r["beta_build"] for r in rows} == {beta}
    assert {r["change_kind"] for r in rows} == {kind}
