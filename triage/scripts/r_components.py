"""Split the placebo excess into shocks, drift, a jump at major updates, and a fresh-update term.

EXPLORATORY, post hoc (after sections N, Q and R). Reads saved tables only, no fits.
Run from the repo root:  python triage/scripts/r_components.py

Rows (each pooled over characters, about 100 placebo pairs):
  N  gap scan cells, 1-week blocks inside a build          (y = robust excess variance, pp^2)
  Q  cut-point sweep, 3 + 3 weeks around a cut              (y = tau^2, pp^2)
  R  boundaries (beta and stable), each build's first 3 wk (y = tau^2, pp^2)

Model, no free intercept:
  y = s2 * (1/L1 + 1/L2)      weekly shocks: average down over longer blocks (L in weeks)
    + d2 * D                  drift: grows with the time D between block centres (weeks)
    + J2 * straddle           jump: the blocks sit on either side of a major update
    + F2 * fresh              fresh: the before block's centre is < 4 weeks after a major update
  Major updates: launch (v0.98.1, 2026-03-05), v0.103.2 (2026-04-16), v0.107.1 (2026-06-18).

Coefficients by least squares; 95% intervals by resampling rows (2,000 draws).
A pure random walk would put almost everything in d2; pure weekly noise in s2.

Approximations to keep in mind:
  - R's block lengths are rebuilt from release dates (cap 3 weeks); its D is the saved
    offer-weighted gap. Q's and N's are exact to the day / week.
  - Q's and R's rows for the same stable boundary use different blocks but overlap in time,
    so rows aren't fully independent; the intervals are a bit too narrow.
  - 4 terms from about 40 rows, chosen after seeing the data. A description, not a test.
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

OUT = "triage/out_final/"
MAJOR = pd.to_datetime(["2026-03-05", "2026-04-16", "2026-06-18"])
MAJOR_BUILDS = ("v0.103.2", "v0.107.1")
FRESH_WEEKS = 4
WK = pd.Timedelta(days=7)


def weeks_since_major(t):
    prior = MAJOR[MAJOR <= t]
    return (t - prior.max()) / WK if len(prior) else np.nan


# ---- N: gap scan, 1-week blocks, first block starts at week 1 (or 8) after release
n = pd.read_csv(OUT + "n_gap_summary.csv")
n = n[n.scan != "all scans"].copy()
rel = {"v0.99.1": "2026-03-17", "v0.103.2": "2026-04-16", "v0.107.1": "2026-06-18"}
n["build"] = n.scan.str.split().str[0]
n["start_wk"] = n.scan.str.extract(r"week (\d+)").astype(float)
n_rows = pd.DataFrame({
    "source": "N", "label": n.scan + ", gap " + n.gap.astype(str),
    "y": n.excess_var_robust, "y_lo": np.nan, "y_hi": np.nan,
    "L1": 1.0, "L2": 1.0, "D": n.gap.astype(float), "straddle": 0,
    "before_centre": pd.to_datetime(n.build.map(rel)) + (n.start_wk + 0.5) * WK})

# ---- Q: cut-point sweep, 3 + 3 weeks, contiguous blocks
q = pd.read_csv(OUT + "q_cut_summary.csv").dropna(subset=["tau_pp"])
cut = pd.to_datetime(q.cut)
Lb = np.minimum(21, (cut - pd.to_datetime(q.before_first_day)).dt.days) / 7
La = np.minimum(21, (pd.to_datetime(q.after_last_day) - cut).dt.days + 1) / 7
q_rows = pd.DataFrame({
    "source": "Q", "label": q.label, "y": q.tau_pp**2,
    "y_lo": q.tau_lo**2, "y_hi": q.tau_hi**2,
    "L1": Lb, "L2": La, "D": (Lb + La) / 2,
    "straddle": ((q.kind == "boundary")
                 & q.label.str.split(" -> ").str[1].isin(MAJOR_BUILDS)).astype(int),
    "before_centre": cut - Lb / 2 * WK})

# ---- R: boundaries, each build's first 3 weeks
rb = pd.read_csv(OUT + "r_posthoc_boundary.csv")
ru = (pd.read_csv(OUT + "r_units.csv")[["boundary", "branch", "old_release", "new_release"]]
      .drop_duplicates("boundary"))
rb = rb.merge(ru, on=["boundary", "branch"], how="left")
rb["old_release"] = pd.to_datetime(rb.old_release)
rb["new_release"] = pd.to_datetime(rb.new_release)
rb = rb.sort_values(["branch", "new_release"])
nxt = rb.groupby("branch").new_release.shift(-1)          # next release on the same branch
L_old = np.minimum(21, (rb.new_release - rb.old_release).dt.days) / 7
L_new = np.minimum(21, (nxt - rb.new_release).dt.days.fillna(21)) / 7
r_rows = pd.DataFrame({
    "source": "R", "label": rb.boundary, "y": rb.tau_pp**2,
    "y_lo": rb.tau_lo**2, "y_hi": rb.tau_hi**2,
    "L1": L_old, "L2": L_new, "D": rb.gap_days / 7,
    "straddle": rb.boundary.str.split(" -> ").str[1].str.split().str[0]
                  .isin(MAJOR_BUILDS).astype(int),
    "before_centre": rb.old_release + L_old / 2 * WK})

rows = pd.concat([n_rows, q_rows, r_rows], ignore_index=True)
rows["wk_since_major"] = rows.before_centre.map(weeks_since_major)
rows["fresh"] = (rows.wk_since_major < FRESH_WEEKS).astype(int)
rows["shock_x"] = 1 / rows.L1 + 1 / rows.L2

TERMS = ["shock_x", "D", "straddle", "fresh"]
NAMES = {"shock_x": "s2  shocks, per (1/L1 + 1/L2)", "D": "d2  drift, per week apart",
         "straddle": "J2  jump across a major update", "fresh": "F2  fresh (< 4 wk after one)"}
X, y = rows[TERMS].to_numpy(float), rows.y.to_numpy(float)
coef = np.linalg.lstsq(X, y, rcond=None)[0]

rng = np.random.default_rng(0)
boot = np.array([np.linalg.lstsq(X[i], y[i], rcond=None)[0]
                 for i in (rng.integers(0, len(y), len(y)) for _ in range(2000))])
lo, hi = np.percentile(boot, [2.5, 97.5], axis=0)

print(f"{len(rows)} rows: " + ", ".join(f"{k} {v}" for k, v in rows.source.value_counts().items()))
print(f"{'term':38s} {'pp^2':>7s}   95% interval")
for t, c, a, b in zip(TERMS, coef, lo, hi):
    print(f"{NAMES[t]:38s} {c:7.2f}   [{a:.2f}, {b:.2f}]")
rows["pred"] = X @ coef
rows["resid"] = rows.y - rows.pred
r2 = 1 - (rows.resid**2).sum() / ((y - y.mean())**2).sum()
print(f"R^2 (no intercept, about the mean) = {r2:.2f}")
print("\nRows with the largest residuals:")
print(rows.reindex(rows.resid.abs().sort_values(ascending=False).index)
      [["source", "label", "y", "pred", "D", "straddle", "fresh", "wk_since_major"]]
      .head(8).round(2).to_string(index=False))

# ---- plots
marker = {"N": "s", "Q": "o", "R": "^"}
def colour(r):
    return "C3" if r.straddle else ("C1" if r.fresh else "C0")

fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(16, 5))
for _, r in rows.iterrows():
    c = colour(r)
    if np.isfinite(r.y_lo):
        a1.plot([r.D, r.D], [r.y_lo, r.y_hi], color=c, alpha=0.3, lw=1)
    a1.scatter(r.D, r.y, marker=marker[r.source], color=c, s=40)
    a2.scatter(r.wk_since_major, r.resid, marker=marker[r.source], color=c, s=40)
    a3.scatter(r.pred, r.y, marker=marker[r.source], color=c, s=40)
D = np.linspace(0, rows.D.max(), 50)
for L, ls in [(1, ":"), (3, "--")]:
    a1.plot(D, coef[0] * 2 / L + coef[1] * D, "k" + ls, lw=1,
            label=f"shocks + drift, {L}-wk blocks, quiet")
a1.set_xlabel("weeks between block centres"); a1.set_ylabel("excess variance / tau^2  (pp^2)")
a1.set_title("A. Excess against separation")
a2.axhline(0, color="k", lw=0.8)
a2.axvline(FRESH_WEEKS, color="grey", ls=":", lw=1)
a2.set_xlabel("weeks since the last major update (before block's centre)")
a2.set_ylabel("residual (pp^2)"); a2.set_title("B. What the model misses")
m = max(rows.y.max(), rows.pred.max()) * 1.05
a3.plot([0, m], [0, m], "k", lw=0.8)
a3.set_xlabel("model (pp^2)"); a3.set_ylabel("observed (pp^2)"); a3.set_title("C. Observed against model")
for s, mk in marker.items():
    a3.scatter([], [], marker=mk, color="grey", label={"N": "N gap scan", "Q": "Q cuts",
                                                        "R": "R boundaries"}[s])
for c, lab in [("C3", "across a major update"), ("C1", "fresh, < 4 wk after one"),
               ("C0", "quiet")]:
    a3.scatter([], [], marker="o", color=c, label=lab)
a1.legend(fontsize=7); a3.legend(fontsize=7)
fig.suptitle("Placebo excess: shocks, drift, jump, fresh (EXPLORATORY, post hoc)")
fig.tight_layout()
FIG = "triage/figures/r_components.png"
fig.savefig(FIG, dpi=150)
print(f"\nsaved {FIG}")
plt.show()
