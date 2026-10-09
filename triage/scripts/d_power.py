"""Section D: could a patch-1-sized slope be seen in patch 2 at all? Power by simulation.

Design (fixed before running):
- Data: the 38 tweaks on the dose line from did_<fits>.parquet (default h3, weeks 0-3).
- For each SE setting, fit the project's "slope per patch" model (spirometry.meta.
  meta_regression) to the real data with that setting's SEs, giving the intercept a, the
  second-patch shift c and tau2.
- Each simulation keeps the 24 first-patch points as observed and replaces the 14 second-patch
  points with y = (a + c) + b * x + e, e ~ N(0, (se * f2 * SE_SCALE)^2 + tau2), x and se the
  observed ones, b the planted slope. Then refit the same model (tau2 re-estimated) on all 38.
- Planted slopes: 0, 0.3, 0.7, 1.0, 1.44. N_SIM = 1000 per planted slope per setting.
  SEED = 20261007 (one generator, settings run in the order listed).
- "Detected": two-sided test at alpha = 0.05, i.e. the 95% interval (estimate +- 1.96 se)
  excludes the value: slope2 = 0, and slope2 - slope1 = 0 (difference se from the coefficient
  covariance).
- SE settings: "honest" = clustered SEs as fitted (factors 1, 1); "placebo-inflated" = each
  patch's SEs times its placebo robust sd of z, one row per window/card pair (4.33 first,
  2.09 second; placebo_diagnostics_summary.csv). An extra setting, "honest, patch-2 tau2",
  generates patch-2 noise with the tau2 of a patch-2-only fit (its own scatter) and still
  fits the shared-tau2 model.
- SE_SCALE (command line, default 1) multiplies the second-patch per-tweak SEs in both the
  generation and the fit, for Part 2 to reuse on a smaller subset (e.g. the token runs, whose
  SEs are larger). --se-scale-first does the same for the first patch's observed SEs (fit
  only, unless --simulate-first). --tau2 overrides the generating tau2. For a subset, pass
  --tau2 at the full-data value (0.052 on h3): with scaled SEs on the observed points the
  refit tau2 shrinks to absorb the same scatter, so total noise would barely grow.
- --simulate-first also replaces the first-patch points with a + slope1 * x + noise (slope1,
  a from the real fit at that setting; same noise model), so the slope difference test carries
  the first patch's sampling noise too. Off by default (the first patch is then the observed one).

Read-only; about 10 s for the default run.
    python triage/scripts/d_power.py [--fits h3] [--se-scale 1.0] [--se-scale-first 1.0] [--tau2 X]
                                     [--simulate-first] [--csv PATH]
"""
import argparse
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, "triage/scripts")
from common import AN, all_tweaks, fit, on_line, per_patch_design  # noqa: E402

N_SIM = 1000
SEED = 20261007
PLANTED = [0.0, 0.3, 0.7, 1.0, 1.44]
Z_CRIT = 1.959963984540054          # two-sided alpha = 0.05
C_DIFF = np.array([0.0, 0.0, -1.0, 1.0])

ap = argparse.ArgumentParser()
ap.add_argument("--fits", default="h3")
ap.add_argument("--se-scale", type=float, default=1.0)
ap.add_argument("--se-scale-first", type=float, default=1.0)
ap.add_argument("--tau2", type=float, default=None)
ap.add_argument("--simulate-first", action="store_true")
ap.add_argument("--csv", default=None, help="also write the result table to this path")
args = ap.parse_args()

S = pd.read_csv(f"{AN}/placebo_diagnostics_summary.csv")
S = S[S.dedupe].set_index(["split", "level"])
F_ROB = (float(S.loc[("patch", "first"), "robust_sd_z"]), float(S.loc[("patch", "second"), "robust_sd_z"]))
SETTINGS = [("honest", (1.0, 1.0), "shared"),
            ("placebo-inflated", F_ROB, "shared"),
            ("honest, patch-2 tau2", (1.0, 1.0), "patch2")]

L = on_line(all_tweaks(args.fits))
sec = L.second.to_numpy()
x = L.x.to_numpy()
y_obs = L.beta_lo.to_numpy()
se_obs = L.se_lo.to_numpy()
X = per_patch_design(x, sec)
i2 = sec == 1
print(f"fits did_{args.fits}: {int((~i2).sum())} + {int(i2.sum())} tweaks; N_SIM {N_SIM}, seed {SEED}, "
      f"se_scale second {args.se_scale}, first {args.se_scale_first}, tau2 override {args.tau2}, "
      f"simulate first patch {args.simulate_first}")

rng = np.random.default_rng(SEED)
rows = []
t0 = time.time()
for name, (f1, f2), tau_src in SETTINGS:
    se_fit = se_obs * np.where(i2, f2 * args.se_scale, f1 * args.se_scale_first)
    b_real, cov_real, tau2_real, *_ = fit(y_obs, se_fit, X)
    if args.tau2 is not None:
        tau2_gen = args.tau2
    elif tau_src == "patch2":
        X2 = np.column_stack([np.ones(i2.sum()), x[i2]])
        tau2_gen = fit(y_obs[i2], se_fit[i2], X2)[2]
    else:
        tau2_gen = tau2_real
    a2 = b_real[0] + b_real[1]
    sd_gen = np.sqrt(se_fit[i2] ** 2 + tau2_gen)
    sd_gen1 = np.sqrt(se_fit[~i2] ** 2 + tau2_gen)
    for b in PLANTED:
        est = np.empty((N_SIM, 5))
        for k in range(N_SIM):
            y = y_obs.copy()
            y[i2] = a2 + b * x[i2] + rng.normal(0.0, sd_gen)
            if args.simulate_first:
                y[~i2] = b_real[0] + b_real[2] * x[~i2] + rng.normal(0.0, sd_gen1)
            bb, cov, tau2, *_ = fit(y, se_fit, X)
            est[k] = (bb[3], np.sqrt(cov[3, 3]), C_DIFF @ bb, np.sqrt(C_DIFF @ cov @ C_DIFF), tau2)
        s2, s2se, d, dse, t2 = est.T
        rows.append(dict(setting=name, planted=b, tau2_gen=tau2_gen, slope1_obs=b_real[2],
                         mean_slope2=s2.mean(), sd_slope2=s2.std(), q025=np.quantile(s2, 0.025),
                         q975=np.quantile(s2, 0.975), median_se2=np.median(s2se),
                         power_slope2_ne_0=np.mean(np.abs(s2 / s2se) > Z_CRIT),
                         power_diff_ne_0=np.mean(np.abs(d / dse) > Z_CRIT),
                         cover_planted=np.mean(np.abs(s2 - b) <= Z_CRIT * s2se),
                         median_tau2_fit=np.median(t2)))
R = pd.DataFrame(rows)
pd.set_option("display.width", 220, "display.max_columns", 20)
print(R.round(3).to_string(index=False))
if args.csv:
    R.to_csv(args.csv, index=False)
print(f"elapsed {time.time() - t0:.1f} s")
