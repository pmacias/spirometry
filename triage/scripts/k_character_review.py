"""Section K1 and K2 (Tier 1, saved weeks 0-3 fits, did_h3).

K1  Character: line tweaks per character per patch; (a) leave one character out (both
    patches) -> slope1, slope2, z diff; (b) character intercepts added to the slope-per-patch
    model; (c) per-character slopes where a character has >= 4 points in a patch
    (descriptive). Ruler: ln.
K2  Phil's card-review calls as ONE sensitivity variant (never primary): Grand Finale off,
    Debilitate v0.107.1 off, Crescent Spear at its effective damage 8 -> 10 (x = ln(10/8) =
    0.223, absolute +2, percent +25%; its upgraded-card ln is left as the table's). Every
    Part 1 ruler (rank and per-kind medians recomputed on the variant's 36 tweaks), next to
    the primary 38. Plus a HYBRID ruler, proposed after notebook 04's results were known:
    damage and block tweaks on absolute change, power amounts and "other" on ln, each part
    divided by its kind's median |dose| (computed on the tweaks in the fit).

Read-only; runs in a second.    python triage/scripts/k_character_review.py
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "triage/scripts")
from common import (C_DIFF, RULERS, add_rulers, all_tweaks, fit, on_line,  # noqa: E402
                    per_patch_design, slopes_by_patch)

pd.set_option("display.width", 220)
L0 = on_line(all_tweaks("h3"))
L = add_rulers(L0)

# ---------------------------------------------------------------- K1
print("== K1: line tweaks per character and patch")
print(pd.crosstab(L.color, L.patch, margins=True).to_string())

base = slopes_by_patch(L)
print(f"\nall: slope1 {base['slope1']:.3f} ± {base['se1']:.3f}, slope2 {base['slope2']:+.3f} ± "
      f"{base['se2']:.3f}, z diff {base['z_diff']:+.2f}")
print("\n(a) leave one character out")
for c in sorted(L.color.unique()):
    r = slopes_by_patch(L[L.color != c])
    print(f"  without {c:12s} ({r['n1']}+{r['n2']}): slope1 {r['slope1']:.3f} ± {r['se1']:.3f}, "
          f"slope2 {r['slope2']:+.3f} ± {r['se2']:.3f}, z diff {r['z_diff']:+.2f}")

print("\n(b) character intercepts (4 dummies, Defect = reference) in the slope-per-patch model")
D = pd.get_dummies(L.color, drop_first=True).astype(float)
X = np.column_stack([per_patch_design(L.x, L.second), D.to_numpy()])
b, cov, tau2, Q, dof = fit(L.beta_lo, L.se_lo, X)
c = np.r_[C_DIFF, np.zeros(D.shape[1])]
print(f"  slope1 {b[2]:.3f} ± {np.sqrt(cov[2, 2]):.3f}, slope2 {b[3]:+.3f} ± {np.sqrt(cov[3, 3]):.3f}, "
      f"z diff {(c @ b) / np.sqrt(c @ cov @ c):+.2f}, tau2 {tau2:.4f} (without: {base['tau2']:.4f})")
for name, bi, si in zip(D.columns, b[4:], np.sqrt(np.diag(cov))[4:]):
    print(f"    intercept {name} - defect: {bi:+.3f} ± {si:.3f}")
# character x patch intercepts
DI = pd.get_dummies(L.color + "_" + L.patch, drop_first=True).astype(float)
X2 = np.column_stack([L.x * (1 - L.second), L.x * L.second, np.ones(len(L)), DI.to_numpy()])
b2, cov2, t2b, *_ = fit(L.beta_lo, L.se_lo, X2)
c2 = np.r_[-1, 1, np.zeros(X2.shape[1] - 2)]
print(f"  character x patch intercepts instead: slope1 {b2[0]:.3f} ± {np.sqrt(cov2[0, 0]):.3f}, slope2 "
      f"{b2[1]:+.3f} ± {np.sqrt(cov2[1, 1]):.3f}, z diff {(c2 @ b2) / np.sqrt(c2 @ cov2 @ c2):+.2f}, tau2 {t2b:.4f}")

print("\n(c) per-character slopes, >= 4 points in a patch (DESCRIPTIVE)")
for (col, pt), g in L.groupby(["color", "patch"]):
    if len(g) < 4:
        continue
    Xg = np.column_stack([np.ones(len(g)), g.x])
    bg, cg, tg, *_ = fit(g.beta_lo, g.se_lo, Xg)
    print(f"  {col:12s} {pt:6s} n {len(g)}: slope {bg[1]:+.3f} ± {np.sqrt(cg[1, 1]):.3f}, tau2 {tg:.4f}; "
          f"cards: {', '.join(g.sort_values('x').card_id.str.lower())}")

# ---------------------------------------------------------------- K2
def hybrid(L):
    """abs change for damage/block, ln for power amount/other, each / its kind's median |dose|."""
    L = L.copy()
    raw = np.where(L.kind.isin(["damage", "block"]), L.x_abs, L.x)
    L["_raw"] = raw
    L["x_hybrid"] = L._raw / L.groupby("kind")._raw.transform(lambda s: s.abs().median())
    return L


def variant(L0):
    V = L0.drop(["GRAND_FINALE@v0.103.2/patch", "DEBILITATE@v0.107.1/patch"]).copy()
    cs = "CRESCENT_SPEAR@v0.107.1/patch"
    V.loc[cs, ["old_n", "new_n"]] = [8.0, 10.0]
    V.loc[cs, "x"] = V.loc[cs, "direction"] * np.log(10 / 8)
    V.loc[cs, "x_abs"] = V.loc[cs, "direction"] * 2.0
    return V


RUL = RULERS + [("HYBRID (post hoc): abs/kind for dmg+block, ln/kind for power+other",
                 "x_hybrid", "beta_lo", "se_lo")]
P = hybrid(add_rulers(L0))
V = hybrid(add_rulers(variant(L0)))
print("\n== K2: Phil's review calls (GF off, Debilitate v0.107.1 off, Crescent Spear x = 0.223)")
print(f"Crescent Spear: primary x {L.loc['CRESCENT_SPEAR@v0.107.1/patch', 'x']:.3f}, variant "
      f"{V.loc['CRESCENT_SPEAR@v0.107.1/patch', 'x']:.3f}; n primary {len(P)}, variant {len(V)}")
rows = []
for name, x, y, s in RUL:
    rp, rv = slopes_by_patch(P, x, y, s), slopes_by_patch(V, x, y, s)
    rows.append(dict(ruler=name[:62], slope1_P=rp["slope1"], slope2_P=rp["slope2"], zdiff_P=rp["z_diff"],
                     slope1_V=rv["slope1"], se1_V=rv["se1"], slope2_V=rv["slope2"], se2_V=rv["se2"],
                     zdiff_V=rv["z_diff"], ratio_V=rv["ratio"], se_ratio_V=rv["se_ratio"]))
print(pd.DataFrame(rows).round(3).to_string(index=False))
print("\nhybrid ruler: kind medians of |raw dose| (primary):",
      P.groupby("kind")._raw.apply(lambda s: round(float(s.abs().median()), 3)).to_dict())
# each review call alone, ln ruler
print("\neach call alone (ln ruler):")
for lab, drop, cs in [("GF off", ["GRAND_FINALE@v0.103.2/patch"], False),
                      ("Debilitate v0.107.1 off", ["DEBILITATE@v0.107.1/patch"], False),
                      ("Crescent Spear 0.223", [], True)]:
    W = L0.drop(drop).copy()
    if cs:
        W.loc["CRESCENT_SPEAR@v0.107.1/patch", "x"] = np.log(10 / 8)
    r = slopes_by_patch(W)
    print(f"  {lab:24s}: slope1 {r['slope1']:.3f}, slope2 {r['slope2']:+.3f}, z diff {r['z_diff']:+.2f}")
