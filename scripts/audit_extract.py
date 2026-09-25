"""Compact audit tables from the raw run snapshot, for notebooks/01_data_audit.ipynb.

Interim tooling for the Phase 2 data audit. The real run tables come from the Phase 3
parser (src/spirometry/runs.py, CC); column names here follow the `runs` proposal in
notes/run_schema.md where they overlap, so the notebook ports over later.

Reads sts2_snapshot/page_*.jsonl.gz and writes to data/audit/:

  runs.parquet         one row per record (no player IDs stored at all)
  offer_counts.parquet card_choices entries aggregated by
                       (build, character, card, source, act, upgraded, enchanted,
                        picked, solo, clean, abandoned, before_release, tagged) -> n
  list_counts.parquet  card_choices lists aggregated by
                       (build, source, act, list_len, n_picked, solo, clean,
                        before_release, tagged) -> n
  pages.parquet        one row per page file: records, repeats dropped, mtime, bytes

"clean" = no modifiers and no mod markers. "before_release" = the run's start date (UTC)
is before its build's release_date in reference/builds.csv (False where there's no date).
"tagged" = the record has the uploader tag `_sts`. Records repeated across pages (same run_hash)
are kept once, first page wins. Co-op copies (same run_key) are NOT merged here: filter
on solo for offer work, or dedup runs on run_key.

Usage (from the repo root):
    python scripts/audit_extract.py                 # all pages
    python scripts/audit_extract.py --pages 20      # first 20 pages, quick test
    python scripts/audit_extract.py --workers 6
"""
import argparse, collections, gzip, multiprocessing as mp, pathlib, re, time

try:
    import orjson
    loads = orjson.loads
except ImportError:                      # stdlib fallback, ~2x slower
    import json
    loads = json.loads

import pandas as pd

SNAP = pathlib.Path("sts2_snapshot")
OUT = pathlib.Path("data/audit")

VANILLA_CHARACTERS = {"IRONCLAD", "SILENT", "REGENT", "NECROBINDER", "DEFECT"}
# Mod modifiers seen so far all end in _MODIFIER (UNCAPPED_SPIRE_MODIFIER,
# HEXTECH_MAYHEM_MODIFIER, LIMITLESS_MODIFIER); game ones don't (SEALED_DECK, MIDAS, ...).
# Either way a run with any modifier is not "clean".
PAGE_RE = re.compile(r"page_(\d+)\.jsonl\.gz$")
BUILDS_CSV = pathlib.Path("reference/builds.csv")


def load_release_dates():
    """build_id -> 'YYYY-MM-DD' from builds.csv (blank dates left out)."""
    import csv
    if not BUILDS_CSV.exists():
        raise SystemExit(f"{BUILDS_CSV} not found: run from the repo root")
    with open(BUILDS_CSV, newline="") as f:
        return {r["build_id"]: r["release_date"] for r in csv.DictReader(f) if r["release_date"]}


RELEASE = load_release_dates()       # module level, so worker processes get it too


def strip(x, prefix):
    if x == "NONE.NONE":
        return None
    return x[len(prefix):] if isinstance(x, str) and x.startswith(prefix) else x


def source_of(floor):
    """Where a floor's card_choices came from (notes/run_schema.md: there is no source field)."""
    mpt = floor.get("map_point_type")
    rooms = {r.get("room_type") for r in floor.get("rooms", [])}
    if mpt in ("monster", "elite", "boss"):
        return {"monster": "combat"}.get(mpt, mpt)
    if mpt == "unknown":                 # a ? node
        if rooms & {"monster", "elite", "boss"}:
            return "event_combat"
        if "shop" in rooms:
            return "shop"
        return "event"
    return mpt or "none"                 # ancient (Neow etc.), shop, rest_site, treasure


def parse_run(line, page, lineno, offers, lists):
    r = loads(line)
    players = r.get("players", [])
    n_players = len(players)
    solo = n_players == 1
    chars = [strip(p.get("character"), "CHARACTER.") for p in players]
    char_by_id = {p.get("id"): c for p, c in zip(players, chars)}
    mods = [strip(m.get("id"), "MODIFIER.") for m in r.get("modifiers") or []]
    mph = r.get("map_point_history") or []
    acts = r.get("acts") or []

    # Mod markers (notes/run_schema.md), plus a non-vanilla character or modifier.
    mod_card = False
    for p in players:
        for c in p.get("deck", []):
            if "-" in c.get("id", ""):
                mod_card = True
                break
    marker = {
        "mod_save_dict": "save_dict_" in line if isinstance(line, str) else b"save_dict_" in line,
        "mod_acts": any("ACTSFROMTHEPAST" in a for a in acts),
        "mod_character": any(c not in VANILLA_CHARACTERS for c in chars),
        "mod_modifier": any(m.endswith("_MODIFIER") or "-" in m for m in mods),
    }

    first = mph[0][0] if mph and mph[0] else {}
    first_ids = [x.get("model_id") for x in first.get("rooms", [])]
    floors = sum(len(a) for a in mph)
    abandoned = bool(r.get("was_abandoned"))
    p0 = players[0] if players else {}
    build = r.get("build_id")
    st = r.get("start_time")
    rel = RELEASE.get(build)
    before_release = bool(rel and isinstance(st, (int, float))
                          and time.strftime("%Y-%m-%d", time.gmtime(st)) < rel)
    tagged = "_sts" in r

    # Offers: aggregate per page; also count per-run totals.
    n_lists = n_offers = n_picks = 0
    clean_so_far = not mods and not any(marker.values())
    floor_no = 0
    last_stats = {}
    turns = 0
    for a, act in enumerate(mph, start=1):
        for fl in act:
            floor_no += 1
            turns += sum(x.get("turns_taken") or 0 for x in fl.get("rooms", []))
            src = None
            for ps in fl.get("player_stats", []):
                if ps.get("player_id") == p0.get("id"):
                    last_stats = ps
                cc = ps.get("card_choices")
                if not cc:
                    continue
                src = src or source_of(fl)
                ch = char_by_id.get(ps.get("player_id"), "?")
                n_picked = 0
                for o in cc:
                    card = o.get("card", {})
                    cid = strip(card.get("id"), "CARD.")
                    if "-" in (cid or ""):
                        mod_card = True
                    picked = bool(o.get("was_picked"))
                    n_picked += picked
                    offers[(build, ch, cid, src, a,
                            (card.get("current_upgrade_level") or 0) >= 1,
                            "enchantment" in card, picked, solo, clean_so_far,
                            abandoned, before_release, tagged)] += 1
                lists[(build, src, a, len(cc), n_picked, solo, clean_so_far,
                       before_release, tagged)] += 1
                n_lists += 1
                n_offers += len(cc)
                n_picks += n_picked
    # A mod card found only in the offers after aggregation started: the offers above were
    # counted as clean. Rare; the runs table has the correct flag, and the notebook
    # reports how many runs this affects.
    marker["mod_card"] = mod_card

    return {
        "run_hash": r.get("run_hash"),
        "run_key": f"{r.get('seed')}|{r.get('start_time')}",
        "source_page": page,
        "line_no": lineno,
        "build_id": build,
        "schema_version": r.get("schema_version"),
        "start_time": r.get("start_time"),
        "run_time_s": r.get("run_time"),
        "game_mode": r.get("game_mode"),
        "modifiers": ",".join(mods),
        "n_modifiers": len(mods),
        **marker,
        "ascension": r.get("ascension"),
        "n_players": n_players,
        "character": chars[0] if chars else None,
        "characters": ",".join(sorted(chars)),
        "win": bool(r.get("win")),
        "was_abandoned": abandoned,
        "acts_reached": len(mph),
        "floors_reached": floors,
        "act1": strip(acts[0], "ACT.") if acts else None,
        "first_floor": first.get("map_point_type"),
        "first_floor_neow": "EVENT.NEOW" in first_ids,
        "killed_by_encounter": strip(r.get("killed_by_encounter"), "ENCOUNTER."),
        "killed_by_event": strip(r.get("killed_by_event"), "EVENT."),
        "uploader_tag": r.get("_sts"),
        "before_release": before_release,
        "has_spirecodex_damage": "_spirecodex_damage" in r,
        "deck_size": len(p0.get("deck", [])),
        "n_relics": len(p0.get("relics", [])),
        "final_gold": last_stats.get("current_gold"),
        "final_hp": last_stats.get("current_hp"),
        "final_max_hp": last_stats.get("max_hp"),
        "total_turns": turns,
        "n_card_lists": n_lists,
        "n_offers": n_offers,
        "n_picks": n_picks,
    }


def parse_page(args):
    path, exclude = args
    page = int(PAGE_RE.search(path.name).group(1))
    offers, lists, rows = collections.Counter(), collections.Counter(), []
    bad = 0
    try:
        with gzip.open(path, "rb") as f:
            for i, line in enumerate(f):
                if not line.strip():
                    continue
                try:
                    if exclude:
                        # cheap pre-check before the full parse
                        h = loads(line).get("run_hash")
                        if h in exclude:
                            continue
                    rows.append(parse_run(line, page, i, offers, lists))
                except ValueError:
                    bad += 1
    except (EOFError, OSError):
        bad = -1                          # truncated file (still being written?)
    st = path.stat()
    info = {"page": page, "records": len(rows), "bad_lines": bad,
            "bytes": st.st_size, "mtime": pd.Timestamp(st.st_mtime, unit="s")}
    return page, rows, offers, lists, info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, help="only the first N pages")
    ap.add_argument("--workers", type=int, default=max(1, mp.cpu_count() - 1))
    ap.add_argument("--snapshot", type=pathlib.Path, default=SNAP)
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    a = ap.parse_args()

    paths = sorted(a.snapshot.glob("page_*.jsonl.gz"),
                   key=lambda p: int(PAGE_RE.search(p.name).group(1)))
    if a.pages:
        paths = paths[:a.pages]
    print(f"{len(paths)} pages, {a.workers} workers")
    t0 = time.time()

    seen, runs, infos = set(), [], []
    offers, lists = collections.Counter(), collections.Counter()
    redo = []

    def merge(page, rows, o, l, info, repeats):
        runs.extend(rows)
        offers.update(o)
        lists.update(l)
        info["repeats_dropped"] = repeats
        infos.append(info)

    with mp.Pool(a.workers) as pool:
        for k, (page, rows, o, l, info) in enumerate(
                pool.imap(parse_page, [(p, None) for p in paths], chunksize=2), 1):
            hashes = [r["run_hash"] for r in rows]
            rep = seen.intersection(hashes)
            if rep:                               # redo this page without the repeats
                redo.append((page, rep))
            else:
                seen.update(hashes)
                merge(page, rows, o, l, info, 0)
            if k % 50 == 0:
                print(f"  {k}/{len(paths)} pages, {len(runs):,} runs, "
                      f"{time.time() - t0:.0f}s")
    by_page = {int(PAGE_RE.search(p.name).group(1)): p for p in paths}
    for page, rep in redo:                        # rare; in page order after the pool
        _, rows, o, l, info = parse_page((by_page[page], seen))
        seen.update(r["run_hash"] for r in rows)
        merge(page, rows, o, l, info, len(rep))

    a.out.mkdir(parents=True, exist_ok=True)
    runs = pd.DataFrame(runs).sort_values(["source_page", "line_no"])
    runs["start_time"] = pd.to_datetime(runs["start_time"], unit="s", utc=True)
    runs.to_parquet(a.out / "runs.parquet", index=False)

    ocols = ["build_id", "character", "card_id", "source", "act", "upgraded",
             "enchanted", "picked", "solo", "clean", "abandoned", "before_release", "tagged"]
    pd.DataFrame([(*k, n) for k, n in offers.items()], columns=ocols + ["n"]) \
        .to_parquet(a.out / "offer_counts.parquet", index=False)
    lcols = ["build_id", "source", "act", "list_len", "n_picked", "solo", "clean",
             "before_release", "tagged"]
    pd.DataFrame([(*k, n) for k, n in lists.items()], columns=lcols + ["n"]) \
        .to_parquet(a.out / "list_counts.parquet", index=False)
    pd.DataFrame(infos).sort_values("page").to_parquet(a.out / "pages.parquet", index=False)

    n_rep = sum(len(r) for _, r in redo)
    print(f"done in {time.time() - t0:.0f}s: {len(runs):,} runs from {len(paths)} pages, "
          f"{n_rep} cross-page repeats dropped, {sum(offers.values()):,} offers "
          f"-> {a.out}/")


if __name__ == "__main__":
    main()
