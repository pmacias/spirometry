import gzip
import hashlib
import hmac
import json
import pathlib

import duckdb
import pytest

from spirometry import runs

HERE = pathlib.Path(__file__).parent
FIXTURE = HERE / "fixtures" / "sample_runs.jsonl"
REF = HERE.parent / "reference"
KEY = b"spirometry-test-key"

WIN, SIX, ABANDONED, COOP, PREPARE, SCHEMA10 = (
    "2823a3180dad3c9c", "344778d82365e4af", "420e7f550122ee41",
    "1ee25d46da842936", "545666d976bab316", "ab7f7e8f6118dc26")


def lines():
    return [l for l in FIXTURE.read_text().splitlines() if l.strip()]


def write_page(snap, n, recs):
    snap.mkdir(parents=True, exist_ok=True)
    with gzip.open(snap / f"page_{n:05d}.jsonl.gz", "wt") as f:
        f.write("\n".join(recs) + "\n")


def build(tmp_path, page_recs, workers=1, **kw):
    snap, out = tmp_path / "snap", tmp_path / "out"
    for n, recs in enumerate(page_recs):
        write_page(snap, n, recs)
    info, _ = runs.build(snap, out, workers=workers, key=KEY, key_source="test", ref=REF,
                         quiet=True, **kw)
    return info, duckdb.connect(str(out / "runs.duckdb"), read_only=True)


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    info, con = build(tmp_path_factory.mktemp("fx"), [lines()])
    yield info, con
    con.close()


def rows(con, sql):
    return con.execute(sql).fetchall()


# ------------------------------------------------------------------------------ fixture runs

def test_offer_counts_per_run_and_source(db):
    _, con = db
    got = rows(con, """SELECT run_hash, source, count(*), sum(picked::INT),
                              count(*) FILTER (WHERE set_idx IS NULL)
                       FROM card_offers GROUP BY ALL ORDER BY ALL""")
    assert got == [
        (COOP, "combat", 18, 6, 0),
        (WIN, "boss", 6, 1, 0), (WIN, "combat", 57, 11, 0), (WIN, "elite", 12, 1, 0),
        (WIN, "event", 3, 0, 3), (WIN, "shop", 24, 0, 24),
        (SIX, "ancient", 2, 0, 2), (SIX, "combat", 24, 4, 0), (SIX, "shop", 6, 0, 6),
        (ABANDONED, "combat", 9, 3, 0),
        (PREPARE, "combat", 12, 4, 0),
        (SCHEMA10, "combat", 9, 3, 0),
    ]
    # every card_choices entry becomes one row
    raw = sum(len(s.get("card_choices", [])) for l in lines()
              for a in json.loads(l)["map_point_history"] for f in a for s in f["player_stats"])
    assert rows(con, "SELECT count(*) FROM card_offers")[0][0] == raw == 182


def test_run_flags(db):
    _, con = db
    got = {r[0]: r[1:] for r in rows(con, """
        SELECT run_hash, build_id, branch, schema_version, n_players, win, was_abandoned,
               abandoned_at_neow, is_custom, is_modded, killed_by_encounter IS NOT NULL
        FROM runs""")}
    assert got == {
        WIN: ("v0.98.3", "stable", 8, 1, True, False, False, False, False, False),
        SIX: ("v0.100.0", "beta", 8, 1, False, False, False, False, False, True),
        ABANDONED: ("v0.98.3", "stable", 8, 1, False, True, False, False, False, True),
        COOP: ("v0.99.1", "stable", 8, 2, False, False, False, False, False, True),
        PREPARE: ("v0.100.0", "beta", 8, 1, False, True, False, False, False, True),
        SCHEMA10: ("v0.111.0", "beta", 10, 1, False, False, False, False, False, True),
    }
    assert rows(con, f"SELECT uploader_tag FROM runs WHERE run_hash = '{SCHEMA10}'")[0][0]


def test_six_card_floors_split_into_screens(db):
    _, con = db
    got = rows(con, f"""
        SELECT floor, set_idx, screen_size, sum(picked::INT), bool_and(set_picked_any),
               bool_or(set_picked_any)
        FROM card_offers WHERE run_hash = '{SIX}' AND list_len = 6 AND source = 'combat' GROUP BY ALL ORDER BY ALL""")
    assert got == [
        (2, 0, 3, 1, True, True), (2, 1, 3, 1, True, True),
        (3, 0, 3, 1, True, True), (3, 1, 3, 0, False, False),
        (4, 0, 3, 1, True, True), (4, 1, 3, 0, False, False),
        (8, 0, 3, 0, False, False), (8, 1, 3, 0, False, False),
    ]


def test_abandoned_run_offers_stay_in_primary(db):
    _, con = db
    got = rows(con, f"""SELECT count(*), sum(picked::INT), bool_and(was_abandoned)
                        FROM primary_offers WHERE run_hash = '{ABANDONED}'""")
    assert got == [(9, 3, True)]


def test_primary_offers(db):
    _, con = db
    got = rows(con, "SELECT run_hash, count(*), sum(picked::INT) FROM primary_offers "
                    "GROUP BY 1 ORDER BY 1")
    # solo only (no COOP); combat/elite/boss only (WIN loses its event and shop rows)
    assert got == [(WIN, 75, 13), (SIX, 24, 4), (ABANDONED, 9, 3), (PREPARE, 12, 4),
                   (SCHEMA10, 9, 3)]


def test_beta_only_card_kept_and_flagged(db):
    _, con = db
    got = rows(con, "SELECT run_hash, card_id, source, picked, is_mod_card FROM card_offers "
                    "WHERE NOT in_card_list")
    assert got == [(PREPARE, "PREPARE", "combat", False, False)]
    assert rows(con, "SELECT count(*) FROM primary_offers WHERE card_id = 'PREPARE'") == [(1,)]


def test_coop_players_hashed_with_key(db):
    _, con = db
    expect = [hmac.new(KEY, str(i).encode(), hashlib.sha256).hexdigest()[:16]
              for i in (1001, 1002)]
    got = rows(con, f"SELECT player_idx, player_hash FROM run_players "
                    f"WHERE run_hash = '{COOP}' ORDER BY 1")
    assert got == [(0, expect[0]), (1, expect[1])]
    got = rows(con, f"SELECT player_idx, player_hash, count(*), sum(picked::INT) "
                    f"FROM card_offers WHERE run_hash = '{COOP}' GROUP BY ALL ORDER BY 1")
    assert got == [(0, expect[0], 9, 3), (1, expect[1], 9, 3)]
    assert rows(con, "SELECT DISTINCT player_hash FROM run_players "
                     f"WHERE run_hash <> '{COOP}'") == [("1",)]
    assert "1001" not in str(rows(con, "SELECT * FROM card_offers"))


def test_solo_shops_rebuilt(db):
    _, con = db
    got = rows(con, """SELECT run_hash, origin, usable, count(*), sum(picked::INT),
                              sum(bought_colorless::INT)
                       FROM shop_offers GROUP BY ALL ORDER BY ALL""")
    assert got == [(WIN, "gained", True, 4, 4, 1), (WIN, "list", True, 24, 0, None),
                   (SIX, "gained", True, 1, 1, 0), (SIX, "list", True, 6, 0, None)]


def test_build_info(db):
    info, con = db
    meta = dict(rows(con, "SELECT key, value FROM build_info"))
    assert meta["parser_version"] == runs.PARSER_VERSION
    assert meta["records_read"] == "6" and meta["duplicate_records_dropped"] == "0"
    assert meta["combat_lists_set_idx_null"] == "0"
    assert meta["event_fight_lists_by_len"] == ""
    assert (meta["runs_not_released"], meta["runs_before_release"],
            meta["runs_not_neow_start"], meta["runs_modded"], meta["runs_uploader_tag"],
            meta["runs_player_token_absent"], meta["runs_mod_entity"]) == (
        "0", "0", "0", "0", "1", "6", "0")
    assert meta["key_fingerprint"] == runs.key_fingerprint(KEY)
    assert rows(con, "SELECT DISTINCT source_page FROM runs") == [(0,)]


# ------------------------------------------------------------------------------ dedup, pages

def test_exact_repeats_dropped_across_pages(tmp_path):
    recs = lines()
    info, con = build(tmp_path, [recs, [recs[1], recs[0]]])
    assert info["records_read"] == 8
    assert info["duplicate_records_dropped"] == 2
    assert info["duplicates_with_different_content"] == 0
    assert rows(con, "SELECT count(*), count(DISTINCT run_hash), max(source_page) FROM runs") \
        == [(6, 6, 0)]
    assert rows(con, "SELECT count(*) FROM card_offers") == [(182,)]


def test_coop_copies_kept_and_deduped_in_view(tmp_path):
    recs = lines()
    copy = json.loads(recs[3])
    copy["run_hash"] = "ffffffffffffffff"
    info, con = build(tmp_path, [recs, [json.dumps(copy)]])
    assert info["duplicate_records_dropped"] == 0
    assert rows(con, "SELECT count(*) FROM runs") == [(7,)]
    assert rows(con, "SELECT count(*), max(n_copies) FROM runs_dedup") == [(6, 2)]
    assert rows(con, "SELECT count(*) FROM card_offers_dedup") == [(182,)]
    assert rows(con, "SELECT run_hash FROM runs_dedup WHERE n_copies = 2") == [(COOP,)]


def test_workers_pages_and_rebuild_overwrite(tmp_path):
    recs = lines()
    info, con = build(tmp_path, [recs[:3], recs[3:]], workers=2)
    assert rows(con, "SELECT source_page, count(*) FROM runs GROUP BY 1 ORDER BY 1") \
        == [(0, 3), (1, 3)]
    con.close()
    info, con = build(tmp_path, [recs[:3], recs[3:]], pages=1)
    assert info["pages_parsed"] == 1
    assert rows(con, "SELECT count(*) FROM runs") == [(3,)]
    assert not (tmp_path / "out" / "runs" / "page_00001.parquet").exists()


def test_branch_blank_or_unknown_is_null(tmp_path):
    r = json.loads(lines()[0])
    a, b = dict(r, run_hash="a" * 16, build_id="v0.98.0"), dict(r, run_hash="b" * 16,
                                                              build_id="v9.9.9")
    _, con = build(tmp_path, [[json.dumps(a), json.dumps(b)]])
    assert rows(con, "SELECT build_id, branch FROM runs ORDER BY 1") \
        == [("v0.98.0", None), ("v9.9.9", None)]


def test_modded_and_custom_runs_leave_primary(tmp_path):
    r = json.loads(lines()[5])
    mod = dict(r, run_hash="a" * 16)
    mod["players"] = [dict(mod["players"][0], character="CHARACTER.HERMIT-HERMIT")]
    custom = dict(r, run_hash="b" * 16, modifiers=[{"id": "MODIFIER.SEALED_DECK"}])
    _, con = build(tmp_path, [[json.dumps(mod), json.dumps(custom), lines()[5]]])
    assert rows(con, "SELECT run_hash, is_modded, is_custom FROM runs ORDER BY 1") == [
        ("a" * 16, True, False), (SCHEMA10, False, False), ("b" * 16, False, True)]
    assert rows(con, "SELECT DISTINCT run_hash FROM primary_offers") == [(SCHEMA10,)]


def variant(i, run_hash, **fields):
    """A fixture run under a new run_hash, with top-level fields replaced."""
    return dict(json.loads(lines()[i]), run_hash=run_hash, **fields)


def test_non_release_builds_leave_primary(tmp_path):
    recs = [variant(5, h * 16, build_id=b) for h, b in
            [("a", "v0.97.0"), ("b", "v0.107.1-rc.1"), ("c", "NON-RELEASE-VERSION"),
             ("d", "v0.98.0")]]           # v0.98.0 is in builds.csv, with no branch or date
    _, con = build(tmp_path, [[json.dumps(r) for r in recs] + [lines()[5]]])
    assert rows(con, "SELECT run_hash, released, branch FROM runs ORDER BY 1") == [
        ("a" * 16, False, None), (SCHEMA10, True, "beta"), ("b" * 16, False, None),
        ("c" * 16, False, None), ("d" * 16, True, None)]
    assert rows(con, "SELECT DISTINCT run_hash FROM primary_offers ORDER BY 1") \
        == [(SCHEMA10,), ("d" * 16,)]


def test_before_release(tmp_path):
    # v0.107.1 released 2026-06-18; v0.98.0 has no date in builds.csv
    day = 1781740800                                   # 2026-06-18T00:00:00Z
    recs = [variant(5, "a" * 16, build_id="v0.107.1", start_time=day - 1),   # 06-17 23:59:59
            variant(5, "b" * 16, build_id="v0.107.1", start_time=day),
            variant(5, "c" * 16, build_id="v0.98.0", start_time=0),
            variant(5, "d" * 16, build_id="v0.97.0", start_time=0)]
    _, con = build(tmp_path, [[json.dumps(r) for r in recs]])
    assert rows(con, "SELECT run_hash, before_release FROM runs ORDER BY 1") == [
        ("a" * 16, True), ("b" * 16, False), ("c" * 16, False), ("d" * 16, False)]
    assert rows(con, "SELECT DISTINCT run_hash FROM primary_offers ORDER BY 1") \
        == [("b" * 16,), ("c" * 16,)]
    assert runs.started_before_release(None, runs.datetime.date(2026, 6, 18)) is False


def test_mod_character_without_dash(tmp_path):
    r = variant(5, "a" * 16)
    r["players"] = [dict(r["players"][0], character="CHARACTER.WATCHER")]
    _, con = build(tmp_path, [[json.dumps(r), lines()[5]]])
    assert rows(con, "SELECT run_hash, is_modded FROM runs ORDER BY 1") == [
        ("a" * 16, True), (SCHEMA10, False)]
    assert rows(con, "SELECT DISTINCT run_hash FROM primary_offers") == [(SCHEMA10,)]


def test_neow_start(tmp_path):
    r = variant(5, "a" * 16)
    del r["map_point_history"][0][0]                  # first floor is now a fight
    _, con = build(tmp_path, [[json.dumps(r), lines()[5]]])
    assert rows(con, "SELECT run_hash, neow_start FROM runs ORDER BY 1") == [
        ("a" * 16, False), (SCHEMA10, True)]
    assert rows(con, "SELECT DISTINCT run_hash FROM primary_offers") == [(SCHEMA10,)]
    assert runs.neow_start([]) is False and runs.neow_start([[]]) is False


def test_event_fight_floor_in_primary_with_flag(tmp_path):
    r = variant(5, "a" * 16)
    fl = next(f for a in r["map_point_history"] for f in a
              if f["map_point_type"] == "monster" and f["player_stats"][0].get("card_choices"))
    fl["map_point_type"] = "unknown"
    fl["rooms"] = [{"room_type": "event", "model_id": "EVENT.THE_LANTERN_KEY",
                    "turns_taken": 0}] + fl["rooms"]
    n = len(fl["player_stats"][0]["card_choices"])
    _, con = build(tmp_path, [[json.dumps(r)]])
    got = rows(con, """SELECT source, event_fight, room_types, count(*), min(set_idx),
                              max(screen_size)
                       FROM primary_offers GROUP BY ALL ORDER BY ALL""")
    assert got == [("combat", False, "monster", 9 - n, 0, 3),
                   ("event_combat", True, "event+monster", n, 0, 3)]
    meta = dict(rows(con, "SELECT key, value FROM build_info"))
    assert meta["event_fight_lists_by_len"] == f"{n}:1"


def test_uploader_fields(tmp_path):
    recs = [variant(0, "a" * 16),                                  # page without the field
            variant(0, "b" * 16, player_token=None),
            variant(0, "c" * 16, player_token="0123456789abcdef", _sts="slay-the-stats/v1.2.2")]
    _, con = build(tmp_path, [[json.dumps(r) for r in recs]])
    got = rows(con, "SELECT run_hash, uploader_tag, has_player_token, uploader_hash "
                    "FROM runs ORDER BY 1")
    assert got == [("a" * 16, None, None, None), ("b" * 16, None, False, None),
                   ("c" * 16, "slay-the-stats/v1.2.2", True,
                    hmac.new(KEY, b"0123456789abcdef", hashlib.sha256).hexdigest()[:16])]
    meta = dict(rows(con, "SELECT key, value FROM build_info"))
    assert (meta["runs_uploader_tag"], meta["runs_player_token_absent"],
            meta["runs_player_token_present"]) == ("1", "1", "1")


def test_mod_enchantment_huge_amount(tmp_path):
    # Edited sample run: a non-game enchantment with an amount past SMALLINT on an offer,
    # as seen on page_00905 (RUNE_OF_CORRUPTION 110111), and one on a deck card only.
    offer = variant(5, "a" * 16)
    cc = next(st["card_choices"] for a in offer["map_point_history"] for f in a
              for st in f["player_stats"] if st.get("card_choices"))
    cc[0]["card"]["enchantment"] = {"id": "ENCHANTMENT.RUNE_OF_CORRUPTION", "amount": 110111}
    deck = variant(5, "b" * 16)
    deck["players"][0]["deck"][0]["enchantment"] = {"id": "ENCHANTMENT.RUNE_OF_CORRUPTION",
                                                    "amount": 123013}
    info, con = build(tmp_path, [[json.dumps(offer), json.dumps(deck), lines()[5]]])
    assert info["pages_failed"] == ""
    assert rows(con, "SELECT run_hash, is_modded FROM runs ORDER BY 1") == [
        ("a" * 16, True), (SCHEMA10, False), ("b" * 16, True)]
    assert rows(con, "SELECT run_hash, card_id, enchantment, enchantment_amount FROM card_offers "
                     "WHERE is_mod_enchantment") == [
        ("a" * 16, cc[0]["card"]["id"][5:], "ENCHANTMENT.RUNE_OF_CORRUPTION", 110111)]
    assert rows(con, "SELECT DISTINCT run_hash FROM primary_offers") == [(SCHEMA10,)]
    # game enchantments are not mod markers
    assert rows(con, "SELECT count(*) FROM card_offers WHERE enchantment IS NOT NULL "
                     "AND is_mod_enchantment") == [(1,)]


def test_game_entities_cover_stable_beta_and_removed():
    ids = runs.load_game_entities(REF / "raw")
    # stable list, beta-only (v0.108.0+), and removed before the beta lists (changelog 1.1.0)
    for e in ("EVENT.NEOW", "ENCOUNTER.AEONGLASS_BOSS", "MONSTER.AEONGLASS",
              "ENCOUNTER.BATTLEWORN_DUMMY_EVENT_V2_ENCOUNTER", "ENCOUNTER.DOORMAKER_BOSS",
              "MONSTER.DOORMAKER", "ENCOUNTER.TOADPOLES_NORMAL", "MONSTER.DOOR"):
        assert e in ids, e
    assert "EVENT.NINE_TAILED_FOX_EVENT" not in ids
    assert "ENCOUNTER.SHANGHAI_JIAOTONG_ENCOUNTER" not in ids


def test_mod_event_and_encounter(tmp_path):
    # Edited sample run shaped like the full-build case: a solo event-then-fight floor whose
    # event and encounter aren't in the game data, and no other mod marker.
    mod = variant(5, "a" * 16)
    fl = next(f for a in mod["map_point_history"] for f in a
              if f["map_point_type"] == "monster" and f["player_stats"][0].get("card_choices"))
    fl["map_point_type"] = "unknown"
    fl["rooms"] = [{"room_type": "event", "model_id": "EVENT.NINE_TAILED_FOX_EVENT",
                    "turns_taken": 0},
                   dict(fl["rooms"][0], model_id="ENCOUNTER.SHANGHAI_JIAOTONG_ENCOUNTER")]
    # removed and beta-only game content is not a mod marker
    old = variant(5, "b" * 16)
    fl = next(f for a in old["map_point_history"] for f in a if f["map_point_type"] == "monster")
    fl["rooms"][0].update(model_id="ENCOUNTER.DOORMAKER_BOSS", monster_ids=["MONSTER.DOOR"])
    old["killed_by_encounter"] = "ENCOUNTER.BATTLEWORN_DUMMY_EVENT_V2_ENCOUNTER"
    info, con = build(tmp_path, [[json.dumps(mod), json.dumps(old), lines()[5]]])
    assert rows(con, "SELECT run_hash, is_modded, mod_markers, mod_entities FROM runs "
                     "ORDER BY 1") == [
        ("a" * 16, True, ["mod_entity"],
         ["ENCOUNTER.SHANGHAI_JIAOTONG_ENCOUNTER", "EVENT.NINE_TAILED_FOX_EVENT"]),
        (SCHEMA10, False, [], []), ("b" * 16, False, [], [])]
    assert rows(con, "SELECT DISTINCT run_hash FROM primary_offers ORDER BY 1") == [
        (SCHEMA10,), ("b" * 16,)]
    assert (info["runs_mod_entity"], info["runs_mod_entity_only"]) == (1, 1)


def test_mod_markers_listed_in_order():
    run = {"modifiers": [{"id": "MODIFIER.HEXTECH_MAYHEM_MODIFIER"}],
           "players": [{"character": "CHARACTER.WATCHER"}]}
    line = json.dumps(dict(run, x="CARD.MOD-X", save_dict_y=1, e="ENCHANTMENT.RUNE_OF_CORRUPTION",
                           r="EVENT.NINE_TAILED_FOX_EVENT"))
    ents = runs.load_game_entities(REF / "raw")
    enchs = runs.load_enchantments(REF / "raw" / "enchantments.json")
    assert runs.mod_markers(run, line, enchs, ents) == [
        "dash_id", "save_dict", "mod_enchantment", "mod_modifier", "mod_character", "mod_entity"]
    assert "mod_entity" not in runs.mod_markers(run, line, enchs)       # check off without lists


def test_failing_pages_skipped_and_reported(tmp_path, monkeypatch):
    recs = lines()
    too_big = variant(0, "a" * 16, run_time=2 ** 70)          # fails at the Parquet write
    broken = variant(0, "b" * 16, players=5)                  # fails while parsing
    snap, out = tmp_path / "snap", tmp_path / "out"
    write_page(snap, 0, recs[:3])
    write_page(snap, 1, [recs[3], json.dumps(too_big)])
    write_page(snap, 2, [json.dumps(broken)])
    write_page(snap, 3, recs[4:])
    monkeypatch.chdir(REF.parent)
    monkeypatch.setenv(runs.SALT_ENV, "test")
    with pytest.raises(SystemExit) as e:
        runs.main(["build", "--snapshot", str(snap), "--out", str(out), "--workers", "2"])
    assert e.value.code == 1
    con = duckdb.connect(str(out / "runs.duckdb"), read_only=True)
    meta = dict(rows(con, "SELECT key, value FROM build_info"))
    assert meta["pages_parsed"] == "2" and meta["records_read"] == "5"
    assert meta["pages_failed"] == "page_00001.jsonl.gz,page_00002.jsonl.gz"
    d1, d2 = meta["pages_failed_detail"].split(" | ")
    assert "run_hash " + "a" * 16 in d1 and "runs.run_time_s" in d1
    assert d2.startswith("page_00002.jsonl.gz; TypeError") and "b" * 16 in d2
    assert rows(con, "SELECT source_page, count(*) FROM runs GROUP BY 1 ORDER BY 1") \
        == [(0, 3), (3, 2)]
    assert not (out / "runs" / "page_00001.parquet").exists()


def test_truncated_page_reported(tmp_path):
    snap = tmp_path / "snap"
    write_page(snap, 0, lines())
    data = gzip.compress("\n".join(lines()).encode())
    (snap / "page_00001.jsonl.gz").write_bytes(data[: len(data) // 2])
    info, _ = runs.build(snap, tmp_path / "out", workers=1, key=KEY, key_source="test",
                         ref=REF, quiet=True)
    assert info["pages_parsed"] == 1 and info["pages_failed"] == "page_00001.jsonl.gz"


# ------------------------------------------------------------------------------ helpers

@pytest.mark.parametrize("n,candy,size", [
    (3, False, 3), (6, False, 3), (9, False, 3), (4, False, None), (7, False, None),
    (3, True, 3), (4, True, 4), (6, True, 3), (8, True, 4), (12, True, None), (5, True, None)])
def test_screen_sizes(n, candy, size):
    assert runs.screen_sizes(n, candy) == size


@pytest.mark.parametrize("mpt,rooms,src", [
    ("monster", ["monster"], "combat"), ("elite", ["elite"], "elite"),
    ("boss", ["boss"], "boss"), ("unknown", ["monster"], "combat"),
    ("unknown", ["elite"], "elite"), ("unknown", ["event", "monster"], "event_combat"),
    ("unknown", ["event"], "event"), ("unknown", ["shop"], "shop"),
    ("ancient", ["event"], "ancient"), ("rest_site", ["rest_site"], "rest_site")])
def test_source_of(mpt, rooms, src):
    assert runs.source_of(mpt, rooms) == src


def test_key_from_env_or_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(runs.SALT_ENV, raising=False)
    with pytest.raises(SystemExit):
        runs.load_key()
    runs.init_salt()
    key, src = runs.load_key()
    assert src == "file" and len(key) == 64
    monkeypatch.setenv(runs.SALT_ENV, "from-env")
    assert runs.load_key() == (b"from-env", "env")
    assert runs.player_hash(b"k", 1) == "1"
    assert runs.player_hash(b"k", 76561198000000000) != runs.player_hash(b"j", 76561198000000000)


def test_offers_with_version(db):
    _, con = db
    n_primary = rows(con, "SELECT count(*) FROM primary_offers")[0][0]
    got = rows(con, """SELECT count(*), count(card_version),
                              count(*) FILTER (WHERE build_id = 'v0.98.0')
                       FROM offers_with_version""")[0]
    assert got[0] == n_primary > 0                  # the join adds no rows and drops none
    # every offer gets a version except on v0.98.0 (branch unknown: blank by design)
    missing = rows(con, """SELECT DISTINCT build_id FROM offers_with_version
                           WHERE card_version IS NULL""")
    assert {b for (b,) in missing} <= {"v0.98.0"}
    assert got[1] == got[0] - got[2]
