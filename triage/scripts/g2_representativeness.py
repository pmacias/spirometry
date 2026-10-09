"""Section G2: are token-filled primary runs like the others? (Tier 2, aggregates only.)

Within each stable build, compare runs with a token against runs without one. Runs whose
record has no player_token key (pages downloaded before it existed) have unknown status and
are a third group; the main comparison is token vs no token among key-present runs.
Outcomes: ascension (mean, share A0, share A10), character mix, tagged (_sts) share, win rate
(not abandoned, not retried), floors reached, runs per token (G1), and the before-block pick
rate of each of the 38 line tweaks' cards (v0.99.1 for patch 1, v0.103.3 for patch 2) on
the offers the fits use (offers_with_version, known ascension).

    python triage/scripts/g2_representativeness.py
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "triage/scripts")
import db  # noqa: E402
from common import all_tweaks, on_line  # noqa: E402
from spirometry.runs import PRIMARY_RUN_FILTER  # noqa: E402

pd.set_option("display.width", 220)
STABLE = ["v0.99.1", "v0.103.2", "v0.103.3", "v0.107.1"]
con = db.connect()
GRP = """CASE WHEN has_player_token IS NULL THEN 'key absent'
              WHEN uploader_hash IS NOT NULL THEN 'token' ELSE 'no token' END"""
P = f"(SELECT *, {GRP} AS tok FROM runs_dedup r WHERE {PRIMARY_RUN_FILTER})"

r = con.execute(f"""
    SELECT build_id, tok, count(*) AS runs, avg(ascension) AS mean_asc,
           avg((ascension = 0)::INT) AS share_a0, avg((ascension >= 10)::INT) AS share_a10,
           avg((uploader_tag IS NOT NULL)::INT) AS tagged,
           avg(win::INT) FILTER (WHERE NOT was_abandoned AND NOT retried) AS win_rate,
           avg(was_abandoned::INT) AS abandoned, avg(floors_reached) AS floors
    FROM {P} WHERE list_contains(?, build_id) GROUP BY ALL""", [STABLE]).df()
r["build_id"] = pd.Categorical(r.build_id, STABLE, ordered=True)
print("== run mix by build and token status")
print(r.sort_values(["build_id", "tok"]).round(3).to_string(index=False))

c = con.execute(f"""SELECT r.build_id, r.tok, p.character, count(*) AS n
                    FROM {P} r JOIN run_players p USING (run_hash)
                    WHERE list_contains(?, r.build_id) GROUP BY ALL""", [STABLE]).df()
c["share"] = c.n / c.groupby(["build_id", "tok"]).n.transform("sum")
w = c.pivot_table(index=["build_id", "tok"], columns="character", values="share")
w.columns = [x.replace("CHARACTER.", "").lower() for x in w.columns]
print("\n== character mix")
print(w.loc[STABLE].round(3).to_string())

L = on_line(all_tweaks("h3"))
pairs = [(r_.card_id, r_.before_builds, r_.patch) for r_ in L.itertuples()]
q = con.execute(f"""
    SELECT o.card_id, o.build_id, {GRP.replace('has_player_token', 'r.has_player_token').replace('uploader_hash', 'r.uploader_hash')} AS tok,
           count(*) AS n, avg(o.picked::INT) AS rate
    FROM offers_with_version o JOIN runs r USING (run_hash)
    WHERE o.build_id IN ('v0.99.1', 'v0.103.3') AND o.ascension IS NOT NULL
      AND list_contains(?, o.card_id) GROUP BY ALL""", [sorted(set(L.card_id))]).df()
rows = []
for card, before, patch in pairs:
    g = q[(q.card_id == card) & (q.build_id == before)].set_index("tok")
    if not {"token", "no token"} <= set(g.index):
        continue
    a, b = g.loc["token"], g.loc["no token"]
    se = np.sqrt(a.rate * (1 - a.rate) / a.n + b.rate * (1 - b.rate) / b.n)
    rows.append(dict(card_id=card, patch=patch, n_token=int(a.n), n_no_token=int(b.n),
                     rate_token=a.rate, rate_no_token=b.rate, diff_pp=100 * (a.rate - b.rate),
                     z=(a.rate - b.rate) / se))
T = pd.DataFrame(rows)
print("\n== before-block pick rate of the 38 line cards: token vs no-token runs (key present)")
print(T.round(3).to_string(index=False))
for pt, d in T.groupby("patch"):
    print(f"  {pt}: corr {np.corrcoef(d.rate_token, d.rate_no_token)[0, 1]:.3f}; median |diff| "
          f"{d.diff_pp.abs().median():.2f} pp; |z| > 2: {int((d.z.abs() > 2).sum())} of {len(d)} "
          f"(binomial z, ignores clustering by run); mean diff {d.diff_pp.mean():+.2f} pp; "
          f"median token offers {int(d.n_token.median())}")
