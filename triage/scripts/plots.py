"""Figures for the Part 1 triage, for Phil to run (not run by the triage session).

1. Ruler sensitivity: z for slope2 - slope1, and slope2/slope1 with 95% interval, per ruler.
2. Dose-response on the ln ruler with the first-patch line, Leading Strike and Reflect drawn at
   their fixed sensitivity doses (open markers; not on the fitted line).
3. Power curves: detection share against planted slope2, per SE setting.

Writes PNGs to triage/figures/ (aggregate per-tweak estimates only). Not run by the triage
session. Run from the repo root:

    python triage/scripts/plots.py
"""
import pathlib
import subprocess
import sys
import tempfile

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, "triage/scripts")
from common import (RULERS, add_rulers, all_tweaks, fit, on_line, per_patch_design,  # noqa: E402
                    slopes_by_patch)

OUT = pathlib.Path("triage/figures")
OUT.mkdir(parents=True, exist_ok=True)
FIRST_C, SECOND_C, GREY = "#e8702a", "#2a6fdb", "#555555"

D = all_tweaks("h3")
L = add_rulers(on_line(D))

# 1. rulers
R = pd.DataFrame([dict(ruler=n, **slopes_by_patch(L, x, y, s)) for n, x, y, s in RULERS])
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
yy = np.arange(len(R))[::-1]
axes[0].axvspan(-2, 2, color=GREY, alpha=0.1)
axes[0].scatter(R.z_diff, yy, color=SECOND_C)
axes[0].set(xlabel="z for slope2 - slope1", title="Patch difference by ruler (weeks 0-3)")
axes[1].errorbar(R.ratio, yy, xerr=1.96 * R.se_ratio, fmt="o", color=SECOND_C, capsize=0)
axes[1].axvline(0, color=GREY, lw=0.8)
axes[1].axvline(1, color=FIRST_C, lw=0.8, ls="--")
axes[1].set(xlabel="slope2 / slope1 (95%)", xlim=(-1.5, 2.5), title="Unit-free ratio")
axes[0].set_yticks(yy, R.ruler, fontsize=8)
fig.tight_layout()
fig.savefig(OUT / "b_rulers.png", dpi=130)

# 2. dose-response with the mixed tweaks at fixed doses
b = fit(L.beta_lo, L.se_lo, per_patch_design(L.x, L.second))[0]   # the report's weighted fit
fig, ax = plt.subplots(figsize=(9, 5.5))
for sec, col, lab in [(0, FIRST_C, "first patch"), (1, SECOND_C, "second patch")]:
    g = L[L.second == sec]
    ax.errorbar(g.x, g.beta_lo, yerr=1.96 * g.se_lo, fmt="o", color=col, alpha=0.8, capsize=0, label=lab)
xs = np.linspace(-0.9, 0.55, 100)
ax.plot(xs, b[0] + b[2] * xs, color=FIRST_C, lw=1, ls="--", label="first-patch line")
ax.plot(xs, b[0] + b[1] + b[3] * xs, color=SECOND_C, lw=1, ls="--", label="second-patch line")
ls, rf = D.loc["LEADING_STRIKE@v0.103.2/patch"], D.loc["REFLECT@v0.107.1/patch"]
for xv, lab in [(0.0, "S=0"), (0.0741, "S=1"), (0.1252, "S=2"), (0.1625, "S=3"), (-0.8473, "naive")]:
    ax.errorbar(xv, ls.beta_lo, yerr=1.96 * ls.se_lo, fmt="o", mfc="white", color=GREY, capsize=0)
    if lab in ("S=3", "naive"):
        ax.annotate("Leading Strike, naive dose" if lab == "naive" else
                    "Leading Strike, S = 0, 1, 2, 3", (xv, ls.beta_lo), fontsize=7,
                    xytext=(5, 5), textcoords="offset points")
for xv, lab in [(-0.1252, "base"), (-0.0488, "upgraded"), (-0.087, "mean")]:
    ax.errorbar(xv, rf.beta_lo, yerr=1.96 * rf.se_lo, fmt="s", mfc="white", color=GREY, capsize=0)
    if lab == "base":
        ax.annotate("Reflect: base, mean, upgraded", (xv, rf.beta_lo), fontsize=7,
                    xytext=(-10, 9), textcoords="offset points")
ax.axhline(0, color=GREY, lw=0.6)
ax.axvline(0, color=GREY, lw=0.6)
ax.set(xlabel="direction x ln(new/old)", ylabel="effect on pick rate (log-odds, weeks 0-3)",
       title="Dose-response; open markers = mixed tweaks at fixed sensitivity doses (off the line)")
ax.legend(fontsize=8, frameon=False)
fig.tight_layout()
fig.savefig(OUT / "b2_mixed.png", dpi=130)

# 3. power curves (reruns d_power.py with its default settings and reads its table)
with tempfile.TemporaryDirectory() as tmp:
    csv = pathlib.Path(tmp) / "power.csv"
    subprocess.run([sys.executable, "triage/scripts/d_power.py", "--csv", str(csv)],
                   check=True, capture_output=True)
    P = pd.read_csv(csv).rename(columns={"power_slope2_ne_0": "p0", "power_diff_ne_0": "pdiff"})
fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
for name, g in P.groupby("setting"):
    axes[0].plot(g.planted, g.p0, marker="o", label=name)
    axes[1].plot(g.planted, g.pdiff, marker="o", label=name)
axes[0].set(xlabel="planted slope2", ylabel="share detected", title="slope2 differs from 0")
axes[1].set(xlabel="planted slope2", title="slope2 differs from slope1")
for ax in axes:
    ax.axhline(0.05, color=GREY, lw=0.6, ls=":")
axes[0].legend(fontsize=8, frameon=False)
fig.tight_layout()
fig.savefig(OUT / "d_power.png", dpi=130)
print("wrote", sorted(p.name for p in OUT.glob("*.png")))
