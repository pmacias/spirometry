"""Run tables: parse the raw export pages into Parquet tables plus a DuckDB file of views.

Reads sts2_snapshot/page_*.jsonl.gz (gzipped JSONL, one raw run per line), one page per
worker process, and writes one Parquet file per page per table:

    <out>/runs/page_NNNNN.parquet         one row per record (co-op copies kept)
    <out>/run_players/page_NNNNN.parquet  one row per record x player
    <out>/card_offers/page_NNNNN.parquet  one row per card in card_choices (every source)
    <out>/shop_offers/page_NNNNN.parquet  shop offers: solo shelf + rebuilt purchases; co-op raw
    <out>/build_info.parquet              parser version, build time, counts
    <out>/runs.duckdb                     views over the Parquet files (absolute paths),
                                          plus runs_dedup, card_offers_dedup, primary_offers

Base tables keep every row and carry flags; filtering happens in the views. source_page is
the page file's number, source_line the record's 0-based line in it. Exact repeats
of a record (same run_hash, e.g. pages downloaded twice) are dropped, keeping the first by
(page, line), and counted in build_info. Column definitions: notes/run_schema.md and the
decision log in PLAN.md.

Player IDs (Steam IDs in co-op) and the uploader's player_token are replaced by a keyed hash
(HMAC-SHA256, first 16 hex characters). The key comes from the SPIROMETRY_SALT environment
variable or the git-ignored file .spirometry_salt in the working directory; `init-salt`
creates that file. Keep the key: a new key gives new hashes. Solo player id 1 stays '1'.

Usage (from the repo root):
    python -m spirometry.runs init-salt                  # once: create .spirometry_salt
    python -m spirometry.runs build [--snapshot sts2_snapshot] [--out data/runs]
                                    [--workers N] [--pages N]
"""
import argparse, concurrent.futures, csv, datetime, gzip, hashlib, hmac, json, os
import pathlib, re, secrets, shutil, sys, time

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

PARSER_VERSION = "1.0.0"
REF = pathlib.Path("reference")
SALT_ENV = "SPIROMETRY_SALT"
SALT_FILE = pathlib.Path(".spirometry_salt")
TABLES = ["runs", "run_players", "card_offers", "shop_offers"]
PAGE_RE = re.compile(r"page_(\d+)\.jsonl\.gz$")

LASTING_CANDY = "RELIC.LASTING_CANDY"
COMBAT_SOURCES = {"combat", "elite", "boss"}          # reward screens that get set_idx
# Mod markers: a quoted id with a '-' ("CARD.MULTIPLAYEREXPANDED-VULTURE",
# "CHARACTER.HERMIT-HERMIT"), BaseLib's save_dict_* keys, a mod modifier.
MOD_ID_RE = re.compile(r'"[A-Z][A-Z_]*\.[A-Za-z0-9_]*-')
MPT_SOURCE = {"monster": "combat", "elite": "elite", "boss": "boss", "ancient": "ancient",
              "shop": "shop", "rest_site": "rest_site", "treasure": "treasure"}
ROOM_SOURCE = {"monster": "combat", "elite": "elite", "boss": "boss", "event": "event",
               "shop": "shop", "rest_site": "rest_site", "treasure": "treasure"}

S = pa.string(); I16 = pa.int16(); I32 = pa.int32(); B = pa.bool_()
SCHEMAS = {
    "runs": pa.schema([
        ("run_hash", S), ("run_key", S), ("source_page", I32), ("source_line", I32),
        ("build_id", S), ("branch", S), ("schema_version", I16),
        ("start_time", pa.timestamp("s")), ("run_time_s", I32), ("seed", S),
        ("game_mode", S), ("modifiers", pa.list_(S)), ("is_custom", B), ("is_modded", B),
        ("ascension", I16), ("n_players", I16), ("win", B), ("was_abandoned", B),
        ("abandoned_at_neow", B), ("acts", pa.list_(S)), ("acts_reached", I16),
        ("floors_reached", I16), ("act1", S), ("killed_by_encounter", S),
        ("killed_by_event", S), ("uploader_tag", S), ("uploader_hash", S),
        ("platform_type", S), ("record_digest", S),
    ]),
    "run_players": pa.schema([
        ("run_hash", S), ("run_key", S), ("source_page", I32), ("source_line", I32),
        ("player_idx", I16), ("player_hash", S), ("character", S),
        ("final_deck_size", I16), ("final_relic_count", I16),
    ]),
    "card_offers": pa.schema([
        ("run_hash", S), ("run_key", S), ("source_page", I32), ("source_line", I32),
        ("player_idx", I16), ("player_hash", S), ("character", S),
        ("act", I16), ("floor", I16), ("map_point_type", S), ("room_types", S),
        ("room_model_id", S), ("source", S), ("list_pos", I16), ("list_len", I16),
        ("list_n_picked", I16), ("screen_size", I16), ("set_idx", I16),
        ("card_id", S), ("upgraded", B), ("enchantment", S), ("enchantment_amount", I16),
        ("picked", B), ("set_picked_any", B), ("in_card_list", B), ("is_mod_card", B),
    ]),
    "shop_offers": pa.schema([
        ("run_hash", S), ("run_key", S), ("source_page", I32), ("source_line", I32),
        ("player_idx", I16), ("player_hash", S), ("character", S),
        ("act", I16), ("floor", I16), ("map_point_type", S), ("origin", S),
        ("list_pos", I16), ("card_id", S), ("upgraded", B), ("enchantment", S),
        ("enchantment_amount", I16), ("colorless", B), ("bought_colorless", B),
        ("picked", B), ("usable", B), ("in_card_list", B), ("is_mod_card", B),
    ]),
}


# ------------------------------------------------------------------------------ keys

def load_key(required=True):
    """HMAC key: $SPIROMETRY_SALT, else .spirometry_salt. Returns (bytes, where it came from)."""
    val = os.environ.get(SALT_ENV)
    if val:
        return val.strip().encode(), "env"
    if SALT_FILE.exists():
        val = SALT_FILE.read_text().strip()
        if val:
            return val.encode(), "file"
    if required:
        sys.exit(f"No hashing key: set {SALT_ENV} or run `python -m spirometry.runs init-salt` "
                 f"(writes {SALT_FILE}, git-ignored). Keep the key: a new one changes every hash.")
    return None, None


def init_salt():
    if SALT_FILE.exists():
        print(f"{SALT_FILE} already exists; left unchanged")
        return
    SALT_FILE.write_text(secrets.token_hex(32) + "\n")
    SALT_FILE.chmod(0o600)
    print(f"wrote {SALT_FILE} (git-ignored); back it up, a new key changes every hash")


def keyed_hash(key, value):
    return hmac.new(key, str(value).encode(), hashlib.sha256).hexdigest()[:16]


def key_fingerprint(key):
    """Identifies the key across builds without revealing it."""
    return keyed_hash(key, "spirometry-key-fingerprint")


def player_hash(key, player_id):
    return "1" if player_id == 1 else keyed_hash(key, player_id)


def run_key(seed, start_time):
    """Dedup key shared by co-op copies: hash of (seed, start_time). Not personal data."""
    return hashlib.sha256(f"{seed}|{start_time}".encode()).hexdigest()[:16]


# ------------------------------------------------------------------------------ reference

def load_branches(path=REF / "builds.csv"):
    """build_id -> branch, None where builds.csv leaves it blank."""
    with open(path, newline="") as f:
        return {r["build_id"]: (r["branch"] or None) for r in csv.DictReader(f)}


def load_cards(path=REF / "raw" / "cards.json"):
    """card_id -> color ('colorless', 'ironclad', ...), for the current card list."""
    return {c["id"]: c.get("color") for c in json.loads(pathlib.Path(path).read_text())}


# ------------------------------------------------------------------------------ parsing

def source_of(map_point_type, room_types):
    """Where a floor's card_choices came from; see notes/run_schema.md."""
    if map_point_type == "unknown":
        if "event" in room_types and any(t in ("monster", "elite", "boss") for t in room_types):
            return "event_combat"
        return ROOM_SOURCE.get(room_types[-1], "other") if room_types else "other"
    return MPT_SOURCE.get(map_point_type, "other")


def screen_sizes(n, candy):
    """Screen size for a combat reward list of n cards: 3, or 3/4 with Lasting Candy (it
    adds a card on some fights only). Split only if exactly one size divides n."""
    sizes = [s for s in ((3, 4) if candy else (3,)) if n % s == 0]
    return sizes[0] if len(sizes) == 1 else None


def is_modded(run, line):
    return bool(MOD_ID_RE.search(line) or "save_dict_" in line
                or any(m.get("id", "").endswith("_MODIFIER") for m in run.get("modifiers", [])))


def strip_card(cid):
    return cid[5:] if cid.startswith("CARD.") else cid


def none_if_none(v):
    return None if v in (None, "NONE.NONE") else v


class Table:
    def __init__(self, name):
        self.name, self.cols = name, {f.name: [] for f in SCHEMAS[name]}

    def add(self, **row):
        for k, v in self.cols.items():
            v.append(row.get(k))

    def to_arrow(self):
        return pa.Table.from_pydict(self.cols, schema=SCHEMAS[self.name])


def parse_run(run, line, page, line_no, ctx, out):
    key, branches, cards = ctx["key"], ctx["branches"], ctx["cards"]
    players = run.get("players") or []
    solo = len(players) == 1
    rh, rk = run["run_hash"], run_key(run.get("seed"), run.get("start_time"))
    base = dict(run_hash=rh, run_key=rk, source_page=page, source_line=line_no)
    pidx = {p.get("id"): i for i, p in enumerate(players)}
    phash = {p.get("id"): player_hash(key, p.get("id")) for p in players}
    pchar = {p.get("id"): p.get("character") for p in players}
    mph = run.get("map_point_history") or []
    n_floors = sum(len(a) for a in mph)
    token = run.get("player_token")
    acts = run.get("acts") or []

    out["runs"].add(
        **base, build_id=run.get("build_id"), branch=branches.get(run.get("build_id")),
        schema_version=run.get("schema_version"), start_time=run.get("start_time"),
        run_time_s=run.get("run_time"), seed=run.get("seed"), game_mode=run.get("game_mode"),
        modifiers=[m.get("id") for m in run.get("modifiers") or []],
        is_custom=bool(run.get("modifiers")), is_modded=is_modded(run, line),
        ascension=run.get("ascension"), n_players=len(players), win=run.get("win"),
        was_abandoned=run.get("was_abandoned"),
        abandoned_at_neow=bool(run.get("was_abandoned")) and n_floors <= 1,
        acts=acts, acts_reached=len(mph), floors_reached=n_floors,
        act1=acts[0] if acts else None,
        killed_by_encounter=none_if_none(run.get("killed_by_encounter")),
        killed_by_event=none_if_none(run.get("killed_by_event")),
        uploader_tag=run.get("_sts"),
        uploader_hash=keyed_hash(key, token) if token is not None else None,
        platform_type=run.get("platform_type"),
        record_digest=hashlib.blake2b(line.encode(), digest_size=8).hexdigest())

    for i, p in enumerate(players):
        out["run_players"].add(**base, player_idx=i, player_hash=phash[p.get("id")],
                               character=p.get("character"),
                               final_deck_size=len(p.get("deck") or []),
                               final_relic_count=len(p.get("relics") or []))

    # Lasting Candy: held from its floor_added_to_deck in the final relics, or from the floor
    # it was picked/bought if it was later removed (then it's not in the final relics).
    candy_from = {p.get("id"): next((r.get("floor_added_to_deck") for r in p.get("relics") or []
                                     if r.get("id") == LASTING_CANDY), None) for p in players}
    candy_dyn = {pid: False for pid in pidx}

    floor = 0
    for act_i, act in enumerate(mph, start=1):
        for fl in act:
            floor += 1
            mpt = fl.get("map_point_type")
            rooms = fl.get("rooms") or []
            rtypes = [r.get("room_type") for r in rooms]
            loc = dict(act=act_i, floor=floor, map_point_type=mpt)
            room_types = "+".join(t or "" for t in rtypes) or None
            model_ids = "+".join(r["model_id"] for r in rooms if r.get("model_id")) or None
            src = source_of(mpt, rtypes)
            for st in fl.get("player_stats") or []:
                pid = st.get("player_id")
                who = dict(player_idx=pidx.get(pid), player_hash=phash.get(pid)
                           if pid in phash else player_hash(key, pid), character=pchar.get(pid))
                if (LASTING_CANDY in (st.get("bought_relics") or [])
                        or any(c.get("choice") == LASTING_CANDY and c.get("was_picked")
                               for c in st.get("relic_choices") or [])):
                    candy_dyn[pid] = True
                cf = candy_from.get(pid)
                candy = candy_dyn.get(pid, False) or (cf is not None and floor >= cf)
                cc = st.get("card_choices") or []
                n = len(cc)
                picks = [bool(c.get("was_picked")) for c in cc]
                size = screen_sizes(n, candy) if src in COMBAT_SOURCES and n else None
                for pos, c in enumerate(cc):
                    card = c.get("card") or {}
                    cid = strip_card(card.get("id", ""))
                    ench = card.get("enchantment") or {}
                    set_idx = pos // size if size else None
                    out["card_offers"].add(
                        **base, **who, **loc, room_types=room_types, room_model_id=model_ids,
                        source=src, list_pos=pos, list_len=n, list_n_picked=sum(picks),
                        screen_size=size, set_idx=set_idx, card_id=cid,
                        upgraded=(card.get("current_upgrade_level") or 0) >= 1,
                        enchantment=ench.get("id"), enchantment_amount=ench.get("amount"),
                        picked=picks[pos],
                        set_picked_any=any(picks[set_idx * size:(set_idx + 1) * size])
                        if size else None,
                        in_card_list=cid in cards, is_mod_card="-" in cid)
                if src == "shop":
                    shop_rows(out["shop_offers"], base, who, loc, st, cc, solo, cards)
                if LASTING_CANDY in (st.get("relics_removed") or []):
                    candy_dyn[pid] = False
                    if cf is not None and cf <= floor:
                        candy_from[pid] = None


def shop_rows(tab, base, who, loc, st, cc, solo, cards):
    """Solo: the list (unsold shelf, plus any Orrery-style screen) and one row per card gained
    on the floor that wasn't picked from the list (the purchases; bought_colorless is a subset
    of cards_gained). Co-op: the list as recorded, usable = false."""
    def card_row(card, origin, pos, picked, bought_colorless=None):
        cid = strip_card(card.get("id", ""))
        ench = card.get("enchantment") or {}
        color = cards.get(cid)
        tab.add(**base, **who, **loc, origin=origin, list_pos=pos, card_id=cid,
                upgraded=(card.get("current_upgrade_level") or 0) >= 1,
                enchantment=ench.get("id"), enchantment_amount=ench.get("amount"),
                colorless=(color == "colorless") if color else None,
                bought_colorless=bought_colorless, picked=picked, usable=solo,
                in_card_list=cid in cards, is_mod_card="-" in cid)

    for pos, c in enumerate(cc):
        card_row(c.get("card") or {}, "list", pos, bool(c.get("was_picked")))
    if not solo:
        return
    picked_ids = [(c.get("card") or {}).get("id") for c in cc if c.get("was_picked")]
    bc = list(st.get("bought_colorless") or [])
    for card in st.get("cards_gained") or []:
        cid = card.get("id")
        if cid in picked_ids:
            picked_ids.remove(cid)
            continue
        in_bc = cid in bc
        if in_bc:
            bc.remove(cid)
        card_row(card, "gained", None, True, in_bc)


# ------------------------------------------------------------------------------ pages

_CTX = {}


def _init_worker(key, branches, cards, out_dir):
    _CTX.update(key=key, branches=branches, cards=cards, out_dir=pathlib.Path(out_dir))


def parse_page(path, ctx=None):
    """Parse one page and write its four Parquet files. Returns counts and timing."""
    ctx = ctx or _CTX
    path = pathlib.Path(path)
    page = int(PAGE_RE.search(path.name).group(1))
    t0 = time.perf_counter()
    out = {t: Table(t) for t in TABLES}
    stats = dict(page=page, file=path.name, records=0, bad_lines=0, error=None)
    try:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            for line_no, line in enumerate(f):
                if not line.strip():
                    continue
                try:
                    run = json.loads(line)
                except json.JSONDecodeError:
                    stats["bad_lines"] += 1
                    continue
                parse_run(run, line, page, line_no, ctx, out)
                stats["records"] += 1
    except (OSError, EOFError) as e:          # truncated or corrupt gzip: report, keep going
        stats["error"] = f"{type(e).__name__}: {e}"
        return stats
    for t in TABLES:
        d = ctx["out_dir"] / t
        d.mkdir(parents=True, exist_ok=True)
        pq.write_table(out[t].to_arrow(), d / f"page_{page:05d}.parquet", compression="zstd")
        stats[f"rows_{t}"] = len(out[t].cols["run_hash"])
    stats["seconds"] = time.perf_counter() - t0
    return stats


def drop_repeats(out_dir):
    """Drop exact repeats of a record (same run_hash), keeping the first by (page, line).
    Rewrites only the affected pages' files. Returns (n dropped, n whose content differed)."""
    runs_glob = str(out_dir / "runs" / "*.parquet")
    con = duckdb.connect()
    rep = con.execute(f"""
        SELECT source_page, source_line, differs FROM (
            SELECT source_page, source_line,
                   record_digest <> first_value(record_digest) OVER w AS differs,
                   row_number() OVER w AS rn
            FROM read_parquet('{runs_glob}')
            WINDOW w AS (PARTITION BY run_hash ORDER BY source_page, source_line))
        WHERE rn > 1""").fetchall()
    con.close()
    by_page = {}
    for page, line_no, _ in rep:
        by_page.setdefault(page, set()).add(line_no)
    for page, lines in by_page.items():
        for t in TABLES:
            f = out_dir / t / f"page_{page:05d}.parquet"
            tab = pq.read_table(f)
            keep = [x not in lines for x in tab.column("source_line").to_pylist()]
            pq.write_table(tab.filter(pa.array(keep)), f, compression="zstd")
    return len(rep), sum(bool(d) for _, _, d in rep)


def table_stats(out_dir):
    """Counts on the final (repeat-free) tables for build_info. Combat lists are counted on
    their list_pos = 0 row; multi-pick screens only among lists split into several screens."""
    g = lambda t: f"read_parquet('{out_dir / t / '*.parquet'}')"
    con = duckdb.connect()
    lists, lists_null, offers, offers_null, multi = con.execute(f"""
        SELECT count(*), count(*) FILTER (WHERE screen_size IS NULL), sum(list_len),
               sum(list_len) FILTER (WHERE screen_size IS NULL),
               count(*) FILTER (WHERE list_len > screen_size)
        FROM {g('card_offers')} WHERE list_pos = 0 AND source IN ('combat', 'elite', 'boss')
        """).fetchone()
    multi_pick = con.execute(f"""
        SELECT count(*) FROM (
            SELECT 1 FROM {g('card_offers')} WHERE list_len > screen_size
            GROUP BY run_hash, player_idx, floor, set_idx HAVING sum(picked::INT) > 1)
        """).fetchone()[0]
    bought = con.execute(f"SELECT count(*) FROM {g('shop_offers')} WHERE origin = 'gained'"
                         ).fetchone()[0]
    counts = {t: con.execute(f"SELECT count(*) FROM {g(t)}").fetchone()[0] for t in TABLES}
    con.close()
    return {**{f"rows_{t}": n for t, n in counts.items()},
            "combat_lists": lists, "combat_lists_set_idx_null": lists_null,
            "combat_offers": offers or 0, "combat_offers_set_idx_null": offers_null or 0,
            "combat_lists_multi_screen": multi, "combat_screens_multi_pick": multi_pick,
            "shop_bought_rows": bought}


VIEWS = """
CREATE VIEW runs_dedup AS
    SELECT * EXCLUDE (rn), n_copies FROM (
        SELECT *, row_number() OVER w AS rn, count(*) OVER (PARTITION BY run_key) AS n_copies
        FROM runs WINDOW w AS (PARTITION BY run_key ORDER BY source_page, source_line))
    WHERE rn = 1;
CREATE VIEW card_offers_dedup AS
    SELECT o.* FROM card_offers o SEMI JOIN runs_dedup d USING (run_hash);
CREATE VIEW primary_offers AS
    SELECT o.*, r.build_id, r.branch, r.ascension, r.win, r.was_abandoned,
           r.abandoned_at_neow, r.start_time
    FROM card_offers o JOIN runs r USING (run_hash)
    WHERE r.n_players = 1 AND NOT r.is_custom AND NOT r.is_modded
      AND o.source IN ('combat', 'elite', 'boss') AND NOT o.is_mod_card;
"""


def write_duckdb(out_dir, info):
    db = out_dir / "runs.duckdb"
    con = duckdb.connect(str(db))
    for t in TABLES:
        glob = (out_dir / t).resolve() / "*.parquet"
        con.execute(f"CREATE VIEW {t} AS SELECT * FROM read_parquet('{glob}')")
    con.execute(VIEWS)
    con.execute("CREATE TABLE build_info (key VARCHAR, value VARCHAR)")
    con.executemany("INSERT INTO build_info VALUES (?, ?)", [[k, str(v)] for k, v in info.items()])
    con.close()
    pq.write_table(pa.table({"key": list(info), "value": [str(v) for v in info.values()]}),
                   out_dir / "build_info.parquet")


def clear_output(out_dir):
    for t in TABLES:
        shutil.rmtree(out_dir / t, ignore_errors=True)
    for f in ("runs.duckdb", "runs.duckdb.wal", "build_info.parquet"):
        (out_dir / f).unlink(missing_ok=True)


def build(snapshot="sts2_snapshot", out="data/runs", workers=None, pages=None, key=None,
          key_source=None, ref=REF, quiet=False):
    say = (lambda *a: None) if quiet else print
    t_start = time.perf_counter()
    snapshot, out_dir = pathlib.Path(snapshot), pathlib.Path(out)
    files = sorted((p for p in snapshot.glob("page_*.jsonl.gz") if PAGE_RE.search(p.name)),
                   key=lambda p: int(PAGE_RE.search(p.name).group(1)))
    if pages:
        files = files[:pages]
    if not files:
        sys.exit(f"no page_*.jsonl.gz files in {snapshot}")
    if key is None:
        key, key_source = load_key()
    workers = workers or os.cpu_count() or 1
    branches = load_branches(ref / "builds.csv")
    cards = load_cards(ref / "raw" / "cards.json")
    out_dir.mkdir(parents=True, exist_ok=True)
    clear_output(out_dir)
    say(f"parsing {len(files)} pages from {snapshot} with {workers} worker(s) -> {out_dir}")

    results = []
    if workers == 1:
        ctx = dict(key=key, branches=branches, cards=cards, out_dir=out_dir)
        results = [parse_page(f, ctx) for f in files]
    else:
        with concurrent.futures.ProcessPoolExecutor(
                workers, initializer=_init_worker,
                initargs=(key, branches, cards, str(out_dir))) as ex:
            for i, r in enumerate(ex.map(parse_page, files, chunksize=1), 1):
                results.append(r)
                if i % 50 == 0 or i == len(files):
                    say(f"  {i}/{len(files)} pages")

    failed = [r for r in results if r["error"]]
    for r in failed:
        say(f"  FAILED {r['file']}: {r['error']}")
    if len(failed) == len(results):
        sys.exit("every page failed; nothing written")
    dropped, differ = drop_repeats(out_dir)

    tot = lambda k: sum(r.get(k, 0) for r in results)
    ts = table_stats(out_dir)
    lists, lists_null = ts["combat_lists"], ts["combat_lists_set_idx_null"]
    offers, offers_null = ts["combat_offers"], ts["combat_offers_set_idx_null"]
    info = {
        "parser_version": PARSER_VERSION,
        "built_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "snapshot_dir": str(snapshot.resolve()),
        "pages_parsed": len(results) - len(failed),
        "pages_failed": ",".join(r["file"] for r in failed),
        "first_page": results[0]["page"], "last_page": results[-1]["page"],
        "records_read": tot("records"),
        "unparseable_lines": tot("bad_lines"),
        "duplicate_records_dropped": dropped,
        "duplicates_with_different_content": differ,
        **ts,
        "key_source": key_source, "key_fingerprint": key_fingerprint(key),
        "workers": workers, "python": sys.version.split()[0],
        "duckdb": duckdb.__version__, "pyarrow": pa.__version__,
        "parse_seconds_total_cpu": round(tot("seconds"), 1),
    }
    write_duckdb(out_dir, info)
    info["wall_seconds"] = round(time.perf_counter() - t_start, 1)
    say(f"records read {info['records_read']:,}; exact repeats dropped {dropped:,}"
        f" ({differ} with different content); unparseable lines {info['unparseable_lines']}")
    if lists:
        say(f"combat reward lists with set_idx NULL: {lists_null:,} of {lists:,} "
            f"({lists_null / lists:.2%}); offers {offers_null:,} of {offers:,} "
            f"({offers_null / offers:.2%})")
    say(f"pages failed: {len(failed)}; wall time {info['wall_seconds']} s -> {out_dir / 'runs.duckdb'}")
    return info, results


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m spirometry.runs",
                                 description="Build the run tables from the raw export pages.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="parse pages into Parquet + DuckDB (overwrites --out)")
    b.add_argument("--snapshot", default="sts2_snapshot")
    b.add_argument("--out", default="data/runs")
    b.add_argument("--workers", type=int, default=None, help="default: number of CPUs")
    b.add_argument("--pages", type=int, default=None, help="only the first N pages (quick test)")
    sub.add_parser("init-salt", help=f"create {SALT_FILE} with a random key if missing")
    a = ap.parse_args(argv)
    if a.cmd == "init-salt":
        init_salt()
        return
    info, results = build(a.snapshot, a.out, a.workers, a.pages)
    if info["pages_failed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
