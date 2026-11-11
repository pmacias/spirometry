"""Placebo |z| against the pseudo card's offers: nudge or broken SE?

EXPLORATORY. Run from the repo root:  python triage/scripts/q_z_vs_offers.py

Two predictions for how placebo z behaves as a card's offers n grow:
  nudge (real movement the SE ignores): beta spread fixed in pp, SE ~ 1/sqrt(n),
      so z width ~ sqrt(1 + tau^2/SE^2): about 1 for thin cards, rising like sqrt(n).
  broken SE (fixed undercount factor k): z width = k at every n.

Left panel: z width by offer bin (robust sd), with both predictions.
Right panel: beta spread in pp by offer bin. Nudge: flattens at tau for large n.
Broken SE: keeps falling like 1/sqrt(n).
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import minimize_scalar

from spirometry import did

PATH = "data/analysis/placebo_h3.parquet"
N_BINS = 6

df = pd.read_parquet(PATH)
if len(df) > 463:                      # raw fits: one row per (window, pseudo card)
    df = did.placebo_pairs(did._placebo_ok(df))
df = df.assign(beta_pp=100 * df.beta, se_pp=100 * df.se)
print(df.groupby("patch").size())


def robust_sd(x):
    x = np.asarray(x)
    return 1.4826 * np.median(np.abs(x - np.median(x)))


def fit_tau(beta, se):
    """MLE of tau in beta ~ N(0, se^2 + tau^2)."""
    def nll(t):
        v = se**2 + t**2
        return 0.5 * np.sum(np.log(v) + beta**2 / v)
    return minimize_scalar(nll, bounds=(0, 50), method="bounded").x


fig, (ax_z, ax_b) = plt.subplots(1, 2, figsize=(12, 5))
for (patch, d), color in zip(df.groupby("patch"), ["C0", "C1"]):
    tau = fit_tau(d.beta_pp.to_numpy(), d.se_pp.to_numpy())
    k = robust_sd(d.z)
    print(f"{patch}: tau = {tau:.2f} pp, robust sd z = {k:.2f}, "
          f"median SE = {d.se_pp.median():.2f} pp")

    d = d.assign(bin=pd.qcut(np.log10(d.n_treated_offers), N_BINS, labels=False))
    b = d.groupby("bin").agg(n=("n_treated_offers", "median"),
                             se=("se_pp", "median"),
                             z_w=("z", robust_sd),
                             b_w=("beta_pp", robust_sd))

    # left: z width
    ax_z.scatter(d.n_treated_offers, d.z.abs(), s=6, alpha=0.25, color=color)
    ax_z.plot(b.n, b.z_w, "o-", color=color, label=f"{patch}: robust sd of z")
    ax_z.plot(b.n, np.sqrt(1 + tau**2 / b.se**2), "--", color=color,
              label=f"{patch}: nudge prediction (tau={tau:.1f} pp)")
    ax_z.axhline(k, ls=":", color=color, label=f"{patch}: broken-SE prediction ({k:.2f})")

    # right: beta spread in pp
    ax_b.scatter(d.n_treated_offers, d.beta_pp.abs(), s=6, alpha=0.25, color=color)
    ax_b.plot(b.n, b.b_w, "o-", color=color, label=f"{patch}: robust sd of beta")
    ax_b.plot(b.n, np.sqrt(tau**2 + b.se**2), "--", color=color, label=f"{patch}: nudge")
    ax_b.plot(b.n, k * b.se, ":", color=color, label=f"{patch}: broken SE")

ax_z.axhline(1, color="k", lw=0.8, label="honest errors")
for ax, ylab in [(ax_z, "|z|  (points)  /  width of z (lines)"),
                 (ax_b, "|beta| pp  (points)  /  width of beta (lines)")]:
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("pseudo card's offers in the fit")
    ax.set_ylabel(ylab)
    ax.legend(fontsize=7)
fig.suptitle("Placebo pairs, weeks 0-3: does z width grow with offers? (EXPLORATORY)")
fig.tight_layout()
plt.show()
