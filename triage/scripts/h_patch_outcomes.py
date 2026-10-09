"""Section H: what did the patches do? Pre-declared aggregate outcomes (Tier 2).

Declared before looking (Part 2 brief), with the choices fixed here:
- Population: primary runs (spirometry.runs.PRIMARY_RUN_FILTER) on stable-branch builds
  (branch = 'stable' in builds.csv), by UTC start date. Beta players are not in it.
- Weeks: whole weeks from the boundary date (00:00 UTC), -3..-1 against 0..3; every outcome
  is a per-week rate, then the mean of the weekly values on each side.
- Boundaries: v0.103.2 release (2026-04-16), v0.107.1 release (2026-06-18) (builds.csv dates),
  and two negative controls:
  (a) within-build boundary with no release. Rule (build date ranges only): the longest
      stable build with >= 3 full weeks on each side inside the build, and the week boundary
      (counted from its release) closest to the middle of its range. Ranges as current stable:
      v0.99.1 03-17..04-16 (30 d), v0.103.2 04-16..05-29 (43 d), v0.103.3 05-29..06-18 (20 d),
      v0.107.1 06-18..09-22 (96 d: no later stable in builds.csv; the data end on 09-22).
      -> v0.107.1, middle day 48, closest week boundary day 49 = 2026-08-06.
  (b) the v0.103.3 release (2026-05-29), almost no card changes.
- Outcomes: skip rate per card-reward screen (1 - set_picked_any, split screens only, one row
  per (run_key, floor, set_idx)); runs started per week; win rate among finished
  (not abandoned, not retried) runs; mean floors reached (all runs); mean ascension and the
  A0 share; character shares (5). Rarity mix of cards taken in wins vs losses: NOT computed
  (card rarities exist only in reference/raw/cards.json, which the triage may not read).
- SE for each side's mean: sd of the weekly values / sqrt(weeks) (weeks as the unit; crude),
  and the difference's z from those. 4 boundaries x 11 outcomes (5 character shares) = 44
  comparisons: about 2 at |z| > 2 by chance even if nothing happened, more with trends.

    python triage/scripts/h_patch_outcomes.py
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "triage/scripts")
import db  # noqa: E402
from spirometry.runs import PRIMARY_RUN_FILTER  # noqa: E402

pd.set_option("display.width", 240)
BOUNDS = [("v0.103.2 release", "2026-04-16"), ("v0.103.3 release (neg. control b)", "2026-05-29"),
          ("v0.107.1 release", "2026-06-18"), ("within v0.107.1 (neg. control a)", "2026-08-06")]
con = db.connect()
con.execute("SET memory_limit = '3GB'")
P = f"runs_dedup r WHERE {PRIMARY_RUN_FILTER} AND r.branch = 'stable'"

out = []
for label, day in BOUNDS:
    t0 = pd.Timestamp(day)
    lo, hi = (t0 - pd.Timedelta(weeks=3)).to_pydatetime(), (t0 + pd.Timedelta(weeks=4)).to_pydatetime()
    wk = f"floor(epoch(r.start_time - TIMESTAMP '{day}') / 604800)::INT"
    runs = con.execute(f"""
        SELECT {wk} AS week, count(*) AS runs_started,
               avg(win::INT) FILTER (WHERE NOT was_abandoned AND NOT retried) AS win_rate,
               avg(floors_reached) AS floors, avg(ascension) AS mean_asc,
               avg((ascension = 0)::INT) AS share_a0
        FROM {P} AND r.start_time >= ? AND r.start_time < ? GROUP BY 1""", [lo, hi]).df()
    ch = con.execute(f"""
        SELECT {wk} AS week, p.character, count(*) AS n
        FROM {P} AND r.start_time >= ? AND r.start_time < ? AND TRUE
        GROUP BY ALL""".replace("FROM runs_dedup r", "FROM runs_dedup r JOIN run_players p USING (run_hash)"),
                     [lo, hi]).df()
    ch["share"] = ch.n / ch.groupby("week").n.transform("sum")
    chw = ch.pivot_table(index="week", columns="character", values="share")
    chw.columns = ["share_" + c.replace("CHARACTER.", "").lower() for c in chw.columns]
    sk = con.execute(f"""
        SELECT week, 1 - avg(any_pick::INT) AS skip_rate FROM (
            SELECT {wk.replace('r.start_time', 'o.start_time')} AS week, o.run_key, o.floor, o.set_idx,
                   bool_or(o.set_picked_any) AS any_pick
            FROM primary_offers o
            WHERE o.branch = 'stable' AND o.set_idx IS NOT NULL
              AND o.start_time >= ? AND o.start_time < ?
            GROUP BY ALL) GROUP BY 1""", [lo, hi]).df()
    W = runs.set_index("week").join(sk.set_index("week")).join(chw).sort_index()
    W = W.loc[-3:3]
    print(f"\n== {label}: boundary {day}; weekly values")
    print(W.round(4).to_string())
    pre, post = W.loc[-3:-1], W.loc[0:3]
    for col in W.columns:
        m0, m1 = pre[col].mean(), post[col].mean()
        se = np.sqrt(pre[col].var() / len(pre) + post[col].var() / len(post))
        out.append(dict(boundary=label, outcome=col, pre=m0, post=m1, diff=m1 - m0,
                        rel=(m1 - m0) / m0 if m0 else np.nan, z=(m1 - m0) / se if se > 0 else np.nan))
R = pd.DataFrame(out)
print("\n== all comparisons (pre = mean of weeks -3..-1, post = mean of weeks 0..3)")
print(R.round(4).to_string(index=False))
print(f"\n|z| > 2 in {int((R.z.abs() > 2).sum())} of {len(R)} comparisons")
