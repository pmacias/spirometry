"""Section C: the dose-response with calibrated errors, and what the saved placebo fits can say
about why placebo z has sd ~4.

1. Slope per patch with each patch's per-tweak SE multiplied by a placebo factor, on weeks 0-3
   (did_h3, the dose line's horizon) and all weeks (did_main, the horizon of the placebo fits
   and of placebo_diagnostics_dose_sensitivity.csv). Shared tau2 (the project's model) and,
   as a check, a separate tau2 per patch (two separate meta-regressions).
2. An additive alternative: each patch's excess placebo variance in log-odds (var of placebo
   beta_lo minus mean placebo se_lo^2) added to every tweak's se^2 before the meta-regression.
3. How tau2 absorbs the inflation: per-point variance budget.
4. Placebo diagnostics that discriminate between explanations of sd(z) ~4:
   window-level (shared) vs card-level spread; whether placebo |beta| scales with se
   (multiplicative, like a missing cluster) or is flat (additive, like real card drift);
   drift against base pick rate; persistence of a card's placebo z across the two patches.

Placebo factors are taken from placebo_diagnostics_summary.csv (one row per window/card pair).
Read-only; runs in a few seconds.   python triage/scripts/c_calibrated.py
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "triage/scripts")
from common import AN, all_tweaks, fit, on_line, per_patch_design, slopes_by_patch  # noqa: E402

pd.set_option("display.width", 220, "display.max_columns", 30)
S = pd.read_csv(f"{AN}/placebo_diagnostics_summary.csv")
pairs = S[S.dedupe]
f_rob = tuple(pairs.set_index(["split", "level"]).loc[[("patch", "first"), ("patch", "second")], "robust_sd_z"])
f_sd = tuple(pairs.set_index(["split", "level"]).loc[[("patch", "first"), ("patch", "second")], "sd_z"])
f_all_rob = float(pairs.set_index(["split", "level"]).loc[("all", "all"), "robust_sd_z"])
f_all_sd = float(pairs.set_index(["split", "level"]).loc[("all", "all"), "sd_z"])
FACTORS = {"none (clustered SE as is)": (1.0, 1.0),
           "robust sd by patch": f_rob, "sd by patch": f_sd,
           "robust sd, one factor": (f_all_rob, f_all_rob), "sd, one factor": (f_all_sd, f_all_sd)}
print("factors:", {k: tuple(round(v, 2) for v in f) for k, f in FACTORS.items()})

P = pd.read_parquet(f"{AN}/placebo_main.parquet")
P = P[P.error.fillna("") == ""]
P["k"] = P.treated_rate_before * (1 - P.treated_rate_before)
P["beta_lo"], P["se_lo"] = P.beta / P.k, P.se / P.k
PP = P.drop_duplicates(["color", "stable_build", "fit_on", "pseudo_card"]).copy()   # 463 pairs


def separate_tau(L, f):
    out = {}
    for pt, fac in [("first", f[0]), ("second", f[1])]:
        d = L[L.patch == pt]
        X = np.column_stack([np.ones(len(d)), d.x])
        b, cov, tau2, Q, dof = fit(d.beta_lo, d.se_lo * fac, X)
        out[pt] = (b[1], np.sqrt(cov[1, 1]), tau2)
    diff = out["second"][0] - out["first"][0]
    se = np.hypot(out["second"][1], out["first"][1])
    return out, diff, se


for fits in ["h3", "main"]:
    L = on_line(all_tweaks(fits))
    print(f"\n== 1. did_{fits}: slope per patch with inflated SEs (shared tau2) | separate tau2")
    for name, f in FACTORS.items():
        r = slopes_by_patch(L, se_factor=f)
        sep, d2, s2 = separate_tau(L, f)
        print(f"  {name:26s} slope1 {r['slope1']:.3f} ± {r['se1']:.3f}  slope2 {r['slope2']:+.3f} ± "
              f"{r['se2']:.3f}  diff {r['diff']:+.3f} ± {r['se_diff']:.3f} (z {r['z_diff']:+.2f})  "
              f"tau2 {r['tau2']:.4f} | sep: slope1 {sep['first'][0]:.3f} ± {sep['first'][1]:.3f} "
              f"(tau2 {sep['first'][2]:.4f}), slope2 {sep['second'][0]:+.3f} ± {sep['second'][1]:.3f} "
              f"(tau2 {sep['second'][2]:.4f}), z diff {d2 / s2:+.2f}")

    # 2. additive drift variance from the placebo pairs (log-odds), by patch
    add = {}
    for pt in ["first", "second"]:
        q = PP[(PP.patch == pt) & (PP.fit_on == "all offers")]
        v = q.beta_lo.var() - (q.se_lo ** 2).mean()
        add[pt] = max(v, 0.0)
    se_add = np.sqrt(L.se_lo ** 2 + np.where(L.patch == "second", add["second"], add["first"]))
    X = per_patch_design(L.x, L.second)
    b, cov, tau2, Q, dof = fit(L.beta_lo, se_add, X)
    c = np.array([0, 0, -1, 1.0])
    print(f"  additive placebo variance (log-odds^2) first {add['first']:.4f}, second "
          f"{add['second']:.4f}: slope1 {b[2]:.3f} ± {np.sqrt(cov[2, 2]):.3f}, slope2 {b[3]:+.3f} ± "
          f"{np.sqrt(cov[3, 3]):.3f}, z diff {(c @ b) / np.sqrt(c @ cov @ c):+.2f}, tau2 left {tau2:.4f}")

    # 3. variance budget
    print("  variance budget per point (medians): se_lo^2 * f^2 + tau2")
    for name in ["none (clustered SE as is)", "robust sd by patch"]:
        f = FACTORS[name]
        r = slopes_by_patch(L, se_factor=f)
        for pt, fac in [("first", f[0]), ("second", f[1])]:
            s2 = float(((L[L.patch == pt].se_lo * fac) ** 2).median())
            print(f"    {name:26s} {pt}: se^2 {s2:.4f} + tau2 {r['tau2']:.4f} = {s2 + r['tau2']:.4f}")

    # real tweaks' scatter vs placebo scatter, log-odds, by patch
    for pt in ["first", "second"]:
        q = PP[(PP.patch == pt) & (PP.fit_on == "all offers")]
        real = L[L.patch == pt]
        print(f"  {pt}: sd of real beta_lo {real.beta_lo.std():.3f} (n {len(real)}); "
              f"sd of placebo beta_lo {q.beta_lo.std():.3f} (n {len(q)}); median placebo se_lo "
              f"{q.se_lo.median():.3f}; median real se_lo {real.se_lo.median():.3f}")

# 4. diagnostics on the placebo pairs ---------------------------------------------------
print("\n== 4. Placebo diagnostics (one row per window/pseudo-card pair; all-offers fits)")
Q = PP[PP.fit_on == "all offers"].copy()
Q["window"] = Q.patch + "/" + Q.color
g = Q.groupby("window").agg(n=("z", "size"), mean_z=("z", "mean"), sd_z=("z", "std"),
                            mean_beta_pp=("beta", lambda s: 100 * s.mean()),
                            sd_beta_pp=("beta", lambda s: 100 * s.std()),
                            med_se_pp=("se", lambda s: 100 * s.median()))
print(g.round(2).to_string())
within = Q.groupby("window").z.transform(lambda s: s - s.mean())
print(f"  sd z overall {Q.z.std():.2f}; sd of window means {g.mean_z.std():.2f}; "
      f"sd within windows {within.std():.2f}")

Q["se_bin"] = pd.qcut(Q.se, 3, labels=["small se", "mid se", "large se"])
t = Q.groupby(["patch", "se_bin"], observed=True).agg(
    n=("z", "size"), med_se_pp=("se", lambda s: 100 * s.median()),
    sd_beta_pp=("beta", lambda s: 100 * s.std()),
    robust_sd_beta_pp=("beta", lambda s: 100 * 1.4826 * (s - s.median()).abs().median()),
    sd_z=("z", "std"))
print("\n  spread of placebo beta by se tercile (flat sd_beta with falling sd_z = an additive,")
print("  card-level component; sd_z flat = a multiplicative, missing-cluster component)")
print(t.round(2).to_string())
for pt in ["first", "second"]:
    q = Q[Q.patch == pt]
    A = np.column_stack([np.ones(len(q)), q.se ** 2])
    coef, *_ = np.linalg.lstsq(A, q.beta ** 2, rcond=None)
    print(f"  {pt}: beta^2 = {coef[0]:.6f} + {coef[1]:.2f} * se^2  -> additive sd "
          f"{100 * np.sqrt(max(coef[0], 0)):.2f} pp, multiplicative factor {np.sqrt(max(coef[1], 0)):.2f}")

Q["rate_bin"] = pd.qcut(Q.treated_rate_before, 3, labels=["low", "mid", "high"])
print("\n  placebo beta by the pseudo card's pick rate before (regression to the mean / meta drift?)")
print(Q.groupby(["patch", "rate_bin"], observed=True).agg(
    n=("z", "size"), mean_beta_pp=("beta", lambda s: 100 * s.mean()),
    mean_z=("z", "mean"), sd_z=("z", "std")).round(2).to_string())
print(f"  corr(beta, pick rate before): first {Q[Q.patch == 'first'][['beta', 'treated_rate_before']].corr().iloc[0, 1]:+.2f}, "
      f"second {Q[Q.patch == 'second'][['beta', 'treated_rate_before']].corr().iloc[0, 1]:+.2f}")

both = Q.pivot_table(index="pseudo_card", columns="patch", values="z")
both = both.dropna()
print(f"\n  pseudo cards in both patches: {len(both)}; corr of their z across patches "
      f"{both.corr().iloc[0, 1]:+.2f}")
print(f"  clustered / robust se, placebo fits: median {(Q.se / Q.se_hc).median():.2f}, "
      f"range {(Q.se / Q.se_hc).min():.2f}..{(Q.se / Q.se_hc).max():.2f}")
