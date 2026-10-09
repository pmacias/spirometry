"""Section B: the ruler puzzle.

1. Composition of the two patches on the line (kind, sizes).
2. Every ruler (notebook 04's seven plus two new ones), weeks 0-3 fits: slope1, slope2,
   difference, z, ratio slope2/slope1, tau2. Ruler choices are a sensitivity range, not a pick.
3. A kind-slope model: one slope per kind of number (pooled over patches) plus ONE common
   patch-2 slope difference, under the ln and absolute rulers.
4. Which first-patch tweaks carry slope1 under each ruler: leave-one-out shift in slope1 and
   z_diff; dropping the named big power/other tweaks.

Read-only (saved fits + tweak_sizes). Runs in about a second.

    python triage/scripts/b_rulers.py [h3|main]
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "triage/scripts")
from common import RULERS, add_rulers, all_tweaks, fit, on_line, slopes_by_patch  # noqa: E402

pd.set_option("display.width", 220, "display.max_columns", 30, "display.max_rows", 200)
FITS = sys.argv[1] if len(sys.argv) > 1 else "h3"

D = all_tweaks(FITS)
L = add_rulers(on_line(D))
print(f"fits: did_{FITS}.parquet; {len(L)} on the line")

# 1. composition ------------------------------------------------------------------------
print("\n== 1. Composition by kind and patch")
comp = L.groupby(["kind", "patch"]).agg(
    n=("x", "size"), med_abs_ln=("x", lambda s: s.abs().median()),
    med_abs_delta=("x_abs", lambda s: s.abs().median()), med_old=("old_n", "median"),
    med_abs_beta_lo=("beta_lo", lambda s: s.abs().median())).unstack("patch")
print(comp.round(3).to_string())
tot = L.groupby("patch").agg(n=("x", "size"), med_abs_ln=("x", lambda s: s.abs().median()),
                             med_abs_delta=("x_abs", lambda s: s.abs().median()),
                             med_old=("old_n", "median"), share_nerf=("x", lambda s: (s < 0).mean()))
print(tot.round(3).to_string())
print("Tweaks with changed upgrade delta on the line:",
      L.groupby("patch").upgraded_log_ratio.apply(lambda s: int(s.notna().sum())).to_dict())

# 2. rulers -----------------------------------------------------------------------------
print("\n== 2. Every ruler (slope per patch; slopes are in each ruler's own units)")
rows = []
for name, x, y, s in RULERS:
    rows.append(dict(ruler=name, **slopes_by_patch(L, x, y, s)))
R = pd.DataFrame(rows).set_index("ruler")
R["z1"], R["z2"] = R.slope1 / R.se1, R.slope2 / R.se2
show = ["slope1", "se1", "z1", "slope2", "se2", "z2", "diff", "se_diff", "z_diff", "ratio",
        "se_ratio", "tau2"]
print(R[show].round(3).to_string())
print(f"\nrange over rulers: z1 {R.z1.min():.2f}..{R.z1.max():.2f}; z2 {R.z2.min():.2f}.."
      f"{R.z2.max():.2f}; z_diff {R.z_diff.min():.2f}..{R.z_diff.max():.2f}; "
      f"ratio slope2/slope1 {R.ratio.min():.2f}..{R.ratio.max():.2f}")
print("ratio 95% interval per ruler (delta method):")
for n, r in R.iterrows():
    print(f"  {n:45s} {r.ratio:+.2f}  [{r.ratio - 1.96 * r.se_ratio:+.2f}, "
          f"{r.ratio + 1.96 * r.se_ratio:+.2f}]")

# 3. kind slopes + one common patch-2 difference ------------------------------------------
print("\n== 3. Slope per kind (pooled) + one common second-patch slope difference d")
kinds = ["damage", "block", "power amount", "other"]
for xcol in ["x", "x_abs", "x_kind"]:
    sec = L.second.to_numpy()
    X = np.column_stack([np.ones(len(L)), sec]
                        + [(L[xcol] * (L.kind == k)).to_numpy() for k in kinds]
                        + [(L[xcol] * sec).to_numpy()])
    b, cov, tau2, Q, dof = fit(L.beta_lo, L.se_lo, X)
    se = np.sqrt(np.diag(cov))
    lab = ["a", "shift"] + [f"slope {k}" for k in kinds] + ["d (patch-2 slope diff)"]
    print(f"  dose {xcol}: tau2 {tau2:.4f}; " + "; ".join(
        f"{n} {bi:+.3f} ± {si:.3f}" for n, bi, si in zip(lab, b, se))
        + f"; z(d) {b[-1] / se[-1]:+.2f}")
    # same, but the patch difference as a ratio: y = a + shift + (1 + g*second) * sum_k b_k x_k
    # is nonlinear; report d relative to the dose-weighted pooled slope instead
    pooled = slopes_by_patch(L, xcol)
    print(f"      (for scale: slope1 under this ruler {pooled['slope1']:+.3f})")

# 4. influence on slope1 -----------------------------------------------------------------
print("\n== 4. Leave-one-out influence on slope1 (first-patch tweaks), by ruler")
base = {n: slopes_by_patch(L, x, y, s) for n, x, y, s in RULERS}
infl = []
for cpid in L.index[L.second == 0]:
    Ld = L.drop(index=cpid)
    Ld = add_rulers(Ld.drop(columns=[c for c in Ld.columns if c.startswith("x_") and c != "x_abs"]))
    for n, x, y, s in RULERS[:1] + RULERS[2:3] + RULERS[5:6] + RULERS[7:8]:
        r = slopes_by_patch(Ld, x, y, s)
        infl.append(dict(tweak=L.loc[cpid, "card_id"], kind=L.loc[cpid, "kind"], ruler=n,
                         x=L.loc[cpid, x], y=L.loc[cpid, "beta_lo"],
                         d_slope1_in_se=(r["slope1"] - base[n]["slope1"]) / base[n]["se1"],
                         z_diff=r["z_diff"]))
I = pd.DataFrame(infl)
for n in I.ruler.unique():
    t = I[I.ruler == n].reindex(I[I.ruler == n].d_slope1_in_se.abs().sort_values(
        ascending=False).index).head(6)
    print(f"\n  {n}: base slope1 {base[n]['slope1']:.3f} ± {base[n]['se1']:.3f}, "
          f"z_diff {base[n]['z_diff']:.2f}; LOO z_diff range "
          f"{I[I.ruler == n].z_diff.min():.2f}..{I[I.ruler == n].z_diff.max():.2f}")
    print(t[["tweak", "kind", "x", "y", "d_slope1_in_se", "z_diff"]].round(3).to_string(index=False))

print("\n== 4b. Drop the named big first-patch tweaks, refit (dose rulers recomputed)")
NAMED = ["PARRY@v0.103.2/patch", "FIGHT_ME@v0.103.2/patch", "ANTICIPATE@v0.103.2/patch",
         "CORROSIVE_WAVE@v0.103.2/patch", "DEBILITATE@v0.103.2/patch"]
POW_OTHER_1 = list(L.index[(L.second == 0) & L.kind.isin(["power amount", "other"])])
POW_OTHER_ALL = list(L.index[L.kind.isin(["power amount", "other"])])
for label, drop in [("named five", NAMED), ("all first-patch power/other", POW_OTHER_1),
                    ("all power/other, both patches", POW_OTHER_ALL)]:
    Ld = on_line(D).drop(index=[c for c in drop if c in L.index])
    Ld = add_rulers(Ld)
    print(f"  drop {label} ({len(drop)}): n {int((Ld.second == 0).sum())} + {int(Ld.second.sum())}")
    for n, x, y, s in RULERS:
        r = slopes_by_patch(Ld, x, y, s)
        print(f"     {n:45s} slope1 {r['slope1']:+.3f} ± {r['se1']:.3f}  slope2 {r['slope2']:+.3f} ± "
              f"{r['se2']:.3f}  z_diff {r['z_diff']:+.2f}  ratio {r['ratio']:+.2f}")
print("\nkinds of the named five:", L.loc[NAMED, ["kind", "x", "x_abs", "beta_lo"]].round(3).to_dict("index"))
