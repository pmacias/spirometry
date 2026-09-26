"""Snapshot the Spire Codex run export and count runs per build.

Saves each page as-is (gzipped JSONL) to ./sts2_snapshot/ (or --out), keeps a cursor
checkpoint so it can be stopped and resumed, and backs off on rate limits.
Paths are relative to the working directory: run it from the repo root.

Rate limits: the export has an hourly budget and a daily cap; on a 429 the script
waits until the time the server gives (Retry-After). The wait is measured against the
wall clock, so it resumes on time even if the Mac slept in between (time.sleep alone
stops counting while macOS is asleep).

Only one download per output folder can run at a time (lock file with the process id).

Usage:
    python scripts/snapshot_export.py --pages 5      # quick test: first 5 pages
    python scripts/snapshot_export.py                # keep going until the export ends
    python scripts/snapshot_export.py --out sts2_snapshot_v2   # into another folder
    python scripts/snapshot_export.py --count-only   # just tally what's already saved
    python scripts/snapshot_export.py --count-only --per-page   # also runs per saved page
"""
import argparse, collections, datetime, gzip, json, os, pathlib, sys, time
import requests

URL = "https://spire-codex.com/api/exports/runs"
PAGE_SIZE = 1000
POLL = 60                      # seconds between wall-clock checks while waiting


def now():
    return datetime.datetime.now().astimezone()


def log(msg):
    print(f"{now():%Y-%m-%d %H:%M:%S%z} {msg}", flush=True)


def n_runs(gz_bytes):
    """Number of non-empty lines (runs) in a gzipped JSONL page."""
    return sum(1 for line in gzip.decompress(gz_bytes).splitlines() if line.strip())


def wait_until(deadline):
    """Sleep in short steps until the wall clock passes `deadline` (a timestamp).

    Checking time.time() each step means a Mac that slept through part of the wait
    resumes as soon as it wakes after the deadline, instead of finishing a countdown
    that paused during sleep."""
    while True:
        left = deadline - time.time()
        if left <= 0:
            return
        time.sleep(min(POLL, left))


def pid_alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:          # exists, owned by someone else
        return True
    return True


def take_lock(out):
    """Refuse to run if another live process holds this folder's lock."""
    lock = out / ".lock"
    if lock.exists():
        try:
            pid = int(lock.read_text().split()[0])
        except (ValueError, IndexError):
            pid = None
        if pid and pid != os.getpid() and pid_alive(pid):
            sys.exit(f"another download (pid {pid}) is already writing to {out}/; "
                     f"stop it first (pkill -f snapshot_export)")
    lock.write_text(f"{os.getpid()} {now().isoformat()}\n")
    return lock


def fetch(out, pages):
    out.mkdir(exist_ok=True)
    lock = take_lock(out)
    ckpt = out / "cursor.txt"
    try:
        cursor = ckpt.read_text().strip() if ckpt.exists() else None
        n = len(list(out.glob("page_*.jsonl.gz")))
        if n == 0 and not cursor:
            (out / "started_at.txt").write_text(now().isoformat() + "\n")
        log(f"starting at page {n} in {out}/" + (" (resuming from cursor)" if cursor else ""))
        done = 0
        while pages is None or done < pages:
            params = {"limit": PAGE_SIZE}
            if cursor:
                params["cursor"] = cursor
            r = requests.get(URL, params=params, timeout=120)
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", 60))
                until = time.time() + wait
                log(f"rate limited: waiting {wait}s, until "
                    f"{datetime.datetime.fromtimestamp(until).astimezone():%Y-%m-%d %H:%M %Z}")
                wait_until(until)
                continue
            r.raise_for_status()
            body = r.content
            if body[:2] != b"\x1f\x8b":          # server/requests already decompressed
                body = gzip.compress(body)
            (out / f"page_{n:05d}.jsonl.gz").write_bytes(body)
            n += 1
            done += 1
            cursor = r.headers.get("X-Next-Cursor")
            log(f"page {n}: {n_runs(body)} runs, {len(body)/1e6:.1f} MB, "
                f"remaining budget {r.headers.get('X-RateLimit-Remaining', '?')}")
            if not cursor:
                log("reached end of export")
                ckpt.unlink(missing_ok=True)
                (out / "finished_at.txt").write_text(now().isoformat() + "\n")
                break
            ckpt.write_text(cursor)
    finally:
        lock.unlink(missing_ok=True)


def vkey(b):
    """Sort 'v0.98.2' numerically; anything unparseable goes last."""
    try:
        return (0, tuple(int(x) for x in b.lstrip("v").split(".")))
    except ValueError:
        return (1, b)


def count(out, per_page=False):
    """Records and distinct (seed, start_time) per build. Branch comes from
    reference/builds.csv at analysis time; the export has no is_beta field."""
    builds = collections.Counter()
    unique = collections.defaultdict(set)   # build -> {(seed, start_time)}
    tokens = 0
    for p in sorted(out.glob("page_*.jsonl.gz")):
        k = 0
        with gzip.open(p, "rt") as f:
            for line in f:
                if not line.strip():
                    continue
                run = json.loads(line)
                b = run.get("build_id", "?")
                builds[b] += 1
                unique[b].add((run.get("seed"), run.get("start_time")))
                tokens += bool(run.get("player_token"))
                k += 1
        if per_page:
            print(f"{p.name}: {k} runs")
    # "dedup" = distinct (seed, start_time); collapses co-op runs uploaded once per player
    print(f"{'build':<24}{'runs':>10}{'dedup':>10}")
    for b in sorted(builds, key=vkey):
        print(f"{b:<24}{builds[b]:>10}{len(unique[b]):>10}")
    total_unique = sum(len(s) for s in unique.values())
    print(f"{'total':<24}{sum(builds.values()):>10}{total_unique:>10}")
    print(f"records with a player_token: {tokens}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=None)
    ap.add_argument("--out", type=pathlib.Path, default=pathlib.Path("sts2_snapshot"))
    ap.add_argument("--count-only", action="store_true")
    ap.add_argument("--per-page", action="store_true")
    a = ap.parse_args()
    if not a.count_only:
        fetch(a.out, a.pages)
    count(a.out, a.per_page)
