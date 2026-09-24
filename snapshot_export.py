"""Snapshot the Spire Codex run export and count runs per build.

Saves each page as-is (gzipped JSONL) to ./sts2_snapshot/, keeps a cursor
checkpoint so it can be stopped and resumed, and backs off on rate limits.

Usage:
    python snapshot_export.py --pages 5      # quick test: first 5 pages
    python snapshot_export.py                # keep going until the export ends
    python snapshot_export.py --count-only   # just tally what's already saved
    python snapshot_export.py --count-only --per-page   # also runs per saved page
"""
import argparse, collections, gzip, json, pathlib, time
import requests

URL = "https://spire-codex.com/api/exports/runs"
OUT = pathlib.Path("sts2_snapshot")
CKPT = OUT / "cursor.txt"
PAGE_SIZE = 1000


def n_runs(gz_bytes):
    """Number of non-empty lines (runs) in a gzipped JSONL page."""
    return sum(1 for line in gzip.decompress(gz_bytes).splitlines() if line.strip())


def fetch(pages):
    OUT.mkdir(exist_ok=True)
    cursor = CKPT.read_text().strip() if CKPT.exists() else None
    n = len(list(OUT.glob("page_*.jsonl.gz")))
    done = 0
    while pages is None or done < pages:
        params = {"limit": PAGE_SIZE}
        if cursor:
            params["cursor"] = cursor
        r = requests.get(URL, params=params, timeout=120)
        if r.status_code == 429:
            wait = int(r.headers.get("Retry-After", 60))
            print(f"rate limited, sleeping {wait}s")
            time.sleep(wait)
            continue
        r.raise_for_status()
        body = r.content
        if body[:2] != b"\x1f\x8b":          # server/requests already decompressed
            body = gzip.compress(body)
        (OUT / f"page_{n:05d}.jsonl.gz").write_bytes(body)
        n += 1
        done += 1
        cursor = r.headers.get("X-Next-Cursor")
        print(f"page {n}: {n_runs(body)} runs, {len(body)/1e6:.1f} MB, "
              f"remaining budget {r.headers.get('X-RateLimit-Remaining', '?')}")
        if not cursor:
            print("reached end of export")
            CKPT.unlink(missing_ok=True)
            break
        CKPT.write_text(cursor)


def vkey(b):
    """Sort 'v0.98.2' numerically; anything unparseable goes last."""
    try:
        return (0, tuple(int(x) for x in b.lstrip("v").split(".")))
    except ValueError:
        return (1, b)


def count(per_page=False):
    builds = collections.Counter()
    beta = collections.Counter()
    unique = collections.defaultdict(set)   # build -> {(seed, start_time)}
    for p in sorted(OUT.glob("page_*.jsonl.gz")):
        k = 0
        with gzip.open(p, "rt") as f:
            for line in f:
                if not line.strip():
                    continue
                run = json.loads(line)
                b = run.get("build_id", "?")
                builds[b] += 1
                beta[b] += bool(run.get("is_beta"))
                unique[b].add((run.get("seed"), run.get("start_time")))
                k += 1
        if per_page:
            print(f"{p.name}: {k} runs")
    # "dedup" = distinct (seed, start_time); collapses co-op runs uploaded once per player
    print(f"{'build':<12}{'runs':>10}{'dedup':>10}{'beta':>10}")
    for b in sorted(builds, key=vkey):
        print(f"{b:<12}{builds[b]:>10}{len(unique[b]):>10}{beta[b]:>10}")
    total_unique = sum(len(s) for s in unique.values())
    print(f"{'total':<12}{sum(builds.values()):>10}{total_unique:>10}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=None)
    ap.add_argument("--count-only", action="store_true")
    ap.add_argument("--per-page", action="store_true")
    a = ap.parse_args()
    if not a.count_only:
        fetch(a.pages)
    count(a.per_page)
