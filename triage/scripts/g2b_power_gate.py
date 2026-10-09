"""Section G2b: power gate for a token-subset replication (Tier 2 counts, then d_power.py).

Treated offers per line tweak and block in the full primary data and in the token subset
(runs with uploader_hash), as the weeks 0-3 fits use them: the treated card's offers in its
own character's runs, known ascension; before block = the window's before build (all of it),
after block = the after build's runs started before release + 4 weeks (weeks 0-3).

Rule fixed before counting: a tweak is "estimable" on the subset when it has at least 200
treated offers in each block (counts at 50 and 500 printed for reference).
SE ratio per tweak (approximation, stated): the DiD's SE is dominated by the treated card's
binomial noise, so SE is proportional to sqrt(1/n_before + 1/n_after) at a similar pick rate;
ratio = that for the subset over that for the full data. Per patch, the median ratio over
its line tweaks goes to d_power.py --se-scale(-first) with --simulate-first --tau2 0.0517.
Gate (Part 2 brief): skip G3/G4 if power to detect slope 1.44 in patch 1 is below 50% or
fewer than 30 of the 38 are estimable.

    python triage/scripts/g2b_power_gate.py
"""
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "triage/scripts")
import db  # noqa: E402
from common import all_tweaks, on_line  # noqa: E402
from spirometry import did  # noqa: E402

pd.set_option("display.width", 220)
MIN_OFFERS = 200
L = on_line(all_tweaks("h3"))
con = db.connect()
rows = []
for r in L.itertuples():
    cut = (did.release_date(r.after_builds.split()[0]) + pd.Timedelta(weeks=4)).to_pydatetime()
    n = con.execute("""
        SELECT o.build_id = ? AS after, r.uploader_hash IS NOT NULL AS token, count(*) AS n
        FROM offers_with_version o JOIN runs r USING (run_hash)
        WHERE o.character = ? AND o.card_id = ? AND o.ascension IS NOT NULL
          AND (o.build_id = ? OR (o.build_id = ? AND o.start_time < ?))
        GROUP BY ALL""", [r.after_builds, f"CHARACTER.{r.color.upper()}", r.card_id,
                          r.before_builds, r.after_builds, cut]).df()
    get = lambda a, t: int(n[(n.after == a) & (n.token == t)].n.sum())
    fb, fa = get(False, False) + get(False, True), get(True, False) + get(True, True)
    sb, sa = get(False, True), get(True, True)
    ratio = np.sqrt((1 / sb + 1 / sa) / (1 / fb + 1 / fa)) if sb and sa else np.inf
    rows.append(dict(card_id=r.card_id, patch=r.patch, full_before=fb, full_after=fa,
                     token_before=sb, token_after=sa, se_ratio=ratio))
T = pd.DataFrame(rows)
print(T.sort_values(["patch", "token_before"]).round(2).to_string(index=False))
for m in [50, MIN_OFFERS, 500]:
    ok = (T.token_before >= m) & (T.token_after >= m)
    print(f"estimable at >= {m} treated offers per block: {int(ok.sum())} of {len(T)} "
          f"(first {int(ok[T.patch == 'first'].sum())}, second {int(ok[T.patch == 'second'].sum())})")
ratio = T.groupby("patch").se_ratio.median()
print("median SE ratio (subset / full):", ratio.round(2).to_dict())
cmd = [sys.executable, "triage/scripts/d_power.py", "--simulate-first", "--tau2", "0.0517",
       "--se-scale", f"{ratio['second']:.2f}", "--se-scale-first", f"{ratio['first']:.2f}"]
print("\n$", " ".join(cmd[1:]))
print(subprocess.run(cmd, capture_output=True, text=True).stdout)
