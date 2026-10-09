"""Section K3 (EXPLORATORY: proposed by Phil after seeing patch 2 flat) and the K3 addendum.

Hypotheses and predictions, declared before looking:
 (1) floor: cards most deliberate players never pick respond little to a modest buff, so on
     the ln ruler the response per unit dose is smaller for cards that start low;
 (2) if patch 2's buffs started lower than patch 1's, that composition could flatten patch 2;
 (3) (addendum) ceiling, the mirror image for nerfs: cards most players always take respond
     little to a modest nerf; if patch 2's nerfs started higher, that could flatten patch 2.
 Regression to the mean predicts the opposite sign for (1): low starters show bigger
 measured responses.

Data: did_h3's treated_rate_before and control_rate_before (no new fits). "All controls'
rates" (choice fixed here): one before-block pick rate per (window, control card) for every
control card of the 38 line tweaks' windows (a card that is a control for any tweak of the
window), pooled over both patches; this needs one aggregate query (Tier 2): picks / offers
per (character, card, build) in offers_with_version with known ascension, as the fits load
them. Floor = below the pooled 25th percentile, ceiling = above the 75th. Per-patch
percentiles are printed as a secondary check.

(b) declared model: beta_lo ~ 1 + second + x(1-s) + x*s + gap_c + x*gap_c, gap = logit(treated
rate before) - logit(control rate before), centred at its mean over the 38.

Selection caveat (stated with every result): the developers chose which cards to change and
by how much, probably looking at pick rates, so starting point and dose are not independent.

    python triage/scripts/k3_threshold.py
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "triage/scripts")
import db  # noqa: E402
from common import C_DIFF, all_tweaks, fit, on_line, per_patch_design  # noqa: E402
from spirometry import did  # noqa: E402

pd.set_option("display.width", 220)
logit = lambda p: np.log(p / (1 - p))
L = on_line(all_tweaks("h3"))
L["gap"] = logit(L.treated_rate_before) - logit(L.control_rate_before)
L["buff"] = np.where(L.x > 0, "buff", "nerf")

db.use_derived_colors()
con = db.connect()
n = con.execute("""SELECT character, card_id, build_id, count(*) AS n, avg(picked::INT) AS rate
                   FROM offers_with_version WHERE build_id IN ('v0.99.1', 'v0.103.3')
                   AND ascension IS NOT NULL GROUP BY ALL""").df()
n["color"] = n.character.map(db.CHARS)
rates = []
for (color, before, patch), g in L.groupby(["color", "before_builds", "patch"]):
    ctrl = set()
    for cp in g.index:
        ctrl |= set(did.control_cards(cp))
    m = n[(n.color == color) & (n.build_id == before) & n.card_id.isin(ctrl)]
    rates.append(m.assign(patch=patch))
C = pd.concat(rates)
q25, q75 = C.rate.quantile([0.25, 0.75])
print(f"control cards' before-block pick rates: {len(C)} (window, card) rates; pooled 25th "
      f"pct {q25:.3f}, median {C.rate.median():.3f}, 75th {q75:.3f}")
for pt, g in C.groupby("patch"):
    print(f"  {pt}: n {len(g)}, 25th {g.rate.quantile(.25):.3f}, median {g.rate.median():.3f}, "
          f"75th {g.rate.quantile(.75):.3f}")
L["floor"] = L.treated_rate_before < q25
L["ceiling"] = L.treated_rate_before > q75

print("\n== K3(a) starting points of the 38 line tweaks")
t = L.groupby(["patch", "buff"]).agg(
    n=("x", "size"), median_rate=("treated_rate_before", "median"),
    median_ctrl_rate=("control_rate_before", "median"), median_gap=("gap", "median"),
    below_q25=("floor", "sum"), above_q75=("ceiling", "sum"))
print(t.round(3).to_string())
print(L.groupby("patch").agg(n=("x", "size"), median_rate=("treated_rate_before", "median"),
                             median_gap=("gap", "median"), below_q25=("floor", "sum"),
                             above_q75=("ceiling", "sum")).round(3).to_string())
print("\nper tweak:")
print(L.sort_values(["patch", "treated_rate_before"])[
    ["card_id", "patch", "x", "treated_rate_before", "control_rate_before", "gap", "beta_lo",
     "floor", "ceiling"]].round(3).to_string(index=False))

print("\n== K3(b) beta_lo ~ 1 + second + x(1-s) + x s + gap_c + x gap_c")
g = L.gap - L.gap.mean()
X = np.column_stack([per_patch_design(L.x, L.second), g, L.x * g])
b, cov, tau2, Q, dof = fit(L.beta_lo, L.se_lo, X)
s = np.sqrt(np.diag(cov))
c = np.r_[C_DIFF, 0, 0]
names = ["intercept", "second shift", "slope1", "slope2", "gap_c", "x*gap_c"]
for nm, bi, si in zip(names, b, s):
    print(f"  {nm:12s} {bi:+.3f} ± {si:.3f} (z {bi / si:+.2f})")
print(f"  z diff (slope2 - slope1) {(c @ b) / np.sqrt(c @ cov @ c):+.2f} (without the gap terms -3.80); tau2 {tau2:.4f}")
# sensitivity: within patch 1 only, and floor indicator
for pt in ["first"]:
    d = L[L.patch == pt]
    gg = d.gap - d.gap.mean()
    Xp = np.column_stack([np.ones(len(d)), d.x, gg, d.x * gg])
    bp, cp_, *_ = fit(d.beta_lo, d.se_lo, Xp)
    print(f"  patch 1 alone: slope {bp[1]:.3f} ± {np.sqrt(cp_[1, 1]):.3f}, x*gap {bp[3]:+.3f} ± {np.sqrt(cp_[3, 3]):.3f}")
# outcome in pp (the log-odds conversion divides by p(1-p), which is small for low starters)
Xpp = X
bpp, cpp, *_ = fit(L.beta_pp, L.se_pp, Xpp)
print(f"  same model, outcome in pp: x*gap {bpp[5]:+.4f} ± {np.sqrt(cpp[5, 5]):.4f}; z diff "
      f"{(c @ bpp) / np.sqrt(c @ cpp @ c):+.2f}")

print("\n== K3(c) points near the floor (< pooled 25th pct) and ceiling (> 75th) per patch")
for pt, d in L.groupby("patch"):
    print(f"  {pt}: floor {int(d.floor.sum())} ({', '.join(d[d.floor].card_id.str.lower())}); "
          f"ceiling {int(d.ceiling.sum())} ({', '.join(d[d.ceiling].card_id.str.lower())})")
print("  patch 2 nerfs (described, not fitted):")
for r in L[(L.patch == "second") & (L.x < 0)].itertuples():
    print(f"    {r.card_id}: x {r.x:+.3f}, rate before {r.treated_rate_before:.3f} (controls "
          f"{r.control_rate_before:.3f}), gap {r.gap:+.2f}, effect {r.beta_lo:+.3f} ± {r.se_lo:.3f} log-odds")
