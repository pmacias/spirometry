import csv
import pathlib

from spirometry import tweaks

REF = pathlib.Path(__file__).parent.parent / "reference"


def table():
    with open(REF / "tweak_sizes.csv", newline="") as f:
        return {r["card_patch_id"]: r for r in csv.DictReader(f)}


def test_committed_table_matches_a_fresh_build(tmp_path):
    for f in ("card_patch_fields.csv", "windows.csv", "card_changes.csv"):
        (tmp_path / f).write_bytes((REF / f).read_bytes())
    tweaks.build(tmp_path, quiet=True)
    assert (tmp_path / "tweak_sizes.csv").read_text() == (REF / "tweak_sizes.csv").read_text()


def test_tweak_sizes():
    t = table()
    assert len(t) == 50
    parry = t["PARRY@v0.103.2/patch"]
    assert (parry["main_field"], parry["old"], parry["new"], parry["log_ratio"]) == (
        "powers_applied[0].amount", "6", "10", "0.5108")
    assert (parry["upgrade_old"], parry["upgrade_new"], parry["upgraded_log_ratio"]) == (
        "+3", "+4", "0.4418")                                   # ln(14 / 9)
    assert (parry["before_builds"], parry["after_builds"], parry["color"]) == (
        "v0.99.1", "v0.103.2", "regent")
    assert t["LEADING_STRIKE@v0.103.2/patch"]["mixed_direction"] == "yes"
    assert t["REFLECT@v0.107.1/patch"]["mixed_direction"] == "yes"
    assert {k for k, r in t.items() if r["mixed_direction"] == "yes"} == {
        "LEADING_STRIKE@v0.103.2/patch", "REFLECT@v0.107.1/patch"}
    assert {k for k, r in t.items() if r["upgrade_only"] == "yes"} == {
        "SERPENT_FORM@v0.103.2/patch", "ROYALTIES@v0.107.1/patch",
        "UNTOUCHABLE@v0.107.1/patch"}
    assert t["SERPENT_FORM@v0.103.2/patch"]["main_field"] == ""
    assert "upgrade-only" in t["SERPENT_FORM@v0.103.2/patch"]["note"]
    death = t["DEATH_MARCH@v0.107.1/patch"]
    assert death["upgrade_only"] == "no" and "ExtraDamage" in death["note"]
    assert t["UNTOUCHABLE@v0.107.1/patch"]["upgraded_log_ratio"] == "0.1178"   # ln(9 / 8)
    assert {r["card_id"] for r in t.values() if r["solo_estimable"] == "no"} == {
        "BELIEVE_IN_YOU", "ETERNAL_ARMOR", "SEEKER_STRIKE", "FASTEN", "FALLING_STAR",
        "MINION_STRIKE", "MINION_SACRIFICE"}
    assert {r["direction"] for r in t.values()} == {"1"}
    assert all(r["before_builds"] and r["after_builds"] for r in t.values())
