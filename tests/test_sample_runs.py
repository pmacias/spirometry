import json
import pathlib
import re

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "sample_runs.jsonl"


def load():
    return [json.loads(line) for line in FIXTURE.read_text().splitlines() if line.strip()]


def test_fixture_covers_the_documented_cases():
    runs = load()
    assert len(runs) == 6
    assert any(r["win"] for r in runs)
    assert any(not r["win"] and not r["was_abandoned"] for r in runs)
    assert any(r["was_abandoned"] for r in runs)
    assert any(len(r["players"]) > 1 for r in runs)
    assert any(r["build_id"] == "v0.100.0" for r in runs)          # beta per builds.csv
    assert any(r["schema_version"] == 10 for r in runs)            # recent page
    assert not any("is_beta" in r for r in runs)


def test_fixture_has_no_steam_ids():
    assert not re.search(r"\d{15,}", FIXTURE.read_text())
    for r in load():
        ids = [p["id"] for p in r["players"]]
        if len(ids) > 1:
            assert ids == list(range(1001, 1001 + len(ids)))
        for act in r["map_point_history"]:
            for floor in act:
                assert [s["player_id"] for s in floor["player_stats"]] == ids
