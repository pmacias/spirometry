"""Section G1: uploader-token coverage on the primary population, and release timing (Tier 2,
aggregates only; no token or run IDs leave DuckDB, only counts).

Primary runs = runs_dedup with spirometry.runs.PRIMARY_RUN_FILTER (solo, no modifiers, not
modded, released build, not started before the build's release date, Neow start). Token
"filled" = uploader_hash IS NOT NULL (the keyed hash of player_token); "key absent" =
has_player_token IS NULL (page downloaded before the key existed). Build order comes from
builds.csv release dates, never from comparing build names as text. start_time is the
record's Unix time stored as a naive UTC timestamp (notes/run_schema.md), so days are UTC.

    python triage/scripts/g1_coverage.py
"""
import sys

import pandas as pd

sys.path.insert(0, "triage/scripts")
import db  # noqa: E402
from spirometry.runs import PRIMARY_RUN_FILTER  # noqa: E402

pd.set_option("display.width", 220)
STABLE = ["v0.99.1", "v0.103.2", "v0.103.3", "v0.107.1"]
B = pd.read_csv("reference/builds.csv", dtype=str, keep_default_na=False).set_index("build_id")
order = sorted(STABLE, key=lambda b: B.release_date[b])
print("stable builds by release date:", [(b, B.release_date[b]) for b in order])
con = db.connect()
P = f"(SELECT * FROM runs_dedup r WHERE {PRIMARY_RUN_FILTER})"

t = con.execute(f"""
    SELECT build_id, count(*) AS runs,
           count(*) FILTER (WHERE has_player_token IS NULL) AS key_absent,
           count(*) FILTER (WHERE has_player_token IS NOT NULL) AS key_present,
           count(*) FILTER (WHERE uploader_hash IS NOT NULL) AS token_filled,
           count(*) FILTER (WHERE has_player_token AND uploader_hash IS NULL) AS flag_without_hash,
           count(DISTINCT uploader_hash) AS tokens
    FROM {P} WHERE list_contains(?, build_id) GROUP BY build_id""", [STABLE]).df()
t = t.set_index("build_id").loc[order]
t["fill_all"] = t.token_filled / t.runs
t["fill_key_present"] = t.token_filled / t.key_present
t["runs_per_token"] = t.token_filled / t.tokens
print("\n== primary runs and token coverage per stable build")
print(t.round(3).to_string())

print("\n== tokens on both sides of each release (consecutive stable builds by date)")
for a, b in zip(order[:-1], order[1:]):
    n = con.execute(f"""
        WITH x AS (SELECT DISTINCT uploader_hash, build_id FROM {P}
                   WHERE uploader_hash IS NOT NULL AND build_id IN (?, ?))
        SELECT count(*) FILTER (WHERE nb = 2) AS both_sides,
               count(*) FILTER (WHERE nb = 1 AND has_a) AS only_before,
               count(*) FILTER (WHERE nb = 1 AND NOT has_a) AS only_after
        FROM (SELECT uploader_hash, count(*) AS nb, bool_or(build_id = ?) AS has_a
              FROM x GROUP BY uploader_hash)""", [a, b, a]).df().iloc[0]
    runs = con.execute(f"""
        WITH bs AS (SELECT uploader_hash FROM {P} WHERE build_id IN (?, ?)
                      AND uploader_hash IS NOT NULL GROUP BY uploader_hash
                      HAVING count(DISTINCT build_id) = 2)
        SELECT build_id, count(*) AS runs FROM {P} SEMI JOIN bs USING (uploader_hash)
        WHERE build_id IN (?, ?) GROUP BY build_id""", [a, b, a, b]).df().set_index("build_id").runs
    print(f"  {a} -> {b}: tokens on both sides {n.both_sides}, only {a} {n.only_before}, only "
          f"{b} {n.only_after}; their runs: {a} {int(runs.get(a, 0))}, {b} {int(runs.get(b, 0))}")

print("\n== same counts without the solo/primary restriction (all records in runs), for comparison")
u = con.execute("""SELECT build_id, count(*) AS records,
                          count(*) FILTER (WHERE uploader_hash IS NOT NULL) AS token_filled,
                          count(DISTINCT uploader_hash) AS tokens
                   FROM runs WHERE list_contains(?, build_id) GROUP BY build_id""", [STABLE]).df()
u = u.set_index("build_id").loc[order]
u["fill"] = u.token_filled / u.records
print(u.round(3).to_string())
for a, b in zip(order[:-1], order[1:]):
    n = con.execute("""SELECT count(*) FROM (SELECT uploader_hash FROM runs
                       WHERE uploader_hash IS NOT NULL AND build_id IN (?, ?)
                       GROUP BY uploader_hash HAVING count(DISTINCT build_id) = 2)""", [a, b]).fetchone()[0]
    print(f"  all records, tokens in both {a} and {b}: {n}")

print("\n== token coverage by source page block (key present = page downloaded after the key existed)")
pg = con.execute(f"""SELECT (source_page // 100) * 100 AS page_block, count(*) AS runs,
                            avg((has_player_token IS NOT NULL)::INT) AS key_present,
                            avg((uploader_hash IS NOT NULL)::INT) AS filled
                     FROM {P} GROUP BY 1 ORDER BY 1""").df()
print(pg.round(3).to_string(index=False))

for lo, hi, label in [("2026-04-13", "2026-04-20", "around v0.103.2 (2026-04-16)"),
                      ("2026-05-26", "2026-06-02", "around v0.103.3 (2026-05-29)"),
                      ("2026-06-16", "2026-06-23", "around v0.107.1 (builds.csv 2026-06-18, site 2026-06-19)")]:
    d = con.execute(f"""SELECT CAST(start_time AS DATE) AS day, build_id, count(*) AS n
                        FROM {P} WHERE start_time >= ? AND start_time < ?
                        GROUP BY ALL""", [lo, hi]).df()
    w = d.pivot_table(index="day", columns="build_id", values="n", fill_value=0)
    w = w[[c for c in w.columns if w[c].sum() >= 20]]
    print(f"\n== daily primary runs by build (UTC start date), {label}; builds with >= 20 runs")
    print(w.astype(int).to_string())

# first hours of v0.107.1 (UTC), and v0.103.3 / v0.107.1 runs by hour on the boundary days
h = con.execute(f"""SELECT date_trunc('hour', start_time) AS hour, build_id, count(*) AS n FROM {P}
                    WHERE start_time >= '2026-06-18' AND start_time < '2026-06-20'
                      AND build_id IN ('v0.103.3', 'v0.107.1') GROUP BY ALL""").df()
w = h.pivot_table(index="hour", columns="build_id", values="n", fill_value=0).astype(int)
print("\n== hourly, 2026-06-18 and 06-19 (UTC)")
print(w.to_string())
print("\nfirst v0.107.1 primary run start (UTC):",
      con.execute(f"SELECT min(start_time) FROM {P} WHERE build_id = 'v0.107.1'").fetchone()[0])
print("runs on v0.107.1 started 2026-06-18 (UTC) in the full runs table (incl. before_release):",
      con.execute("""SELECT count(*) FILTER (WHERE CAST(start_time AS DATE) = '2026-06-18'),
                            count(*) FILTER (WHERE CAST(start_time AS DATE) < '2026-06-18')
                     FROM runs WHERE build_id = 'v0.107.1'""").fetchone())
