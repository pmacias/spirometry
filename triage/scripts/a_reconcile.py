"""Section A: recompute the numbers SPIROMETRY.md / PLAN.md quote, from the saved fits.

Read-only: data/analysis/*.parquet, reference/tweak_sizes.csv. Prints aggregates only (card
names, counts, estimates); no run-level or uploader data. Runs in a second or two.

    python triage/scripts/a_reconcile.py
"""
import numpy as np
import pandas as pd

from spirometry.meta import dose_response_fits

AN = "data/analysis"
SECOND_BEFORE = "v0.103.3"


def load(name):
    d = pd.read_parquet(f"{AN}/did_{name}.parquet")
    return d.set_index("card_patch_id") if "card_patch_id" in d.columns else d


def patch(d):
    return np.where(d.before_builds == SECOND_BEFORE, "second", "first")


def line(d):
    """Notebook 02 section 8's selection."""
    m = d[d.error == ""].copy()
    m["x"] = m.direction * m.log_ratio
    m = m[(m.mixed_direction != "yes") & (m.upgrade_only != "yes") & m.x.notna()
          & m.beta_lo.notna() & (m.se_lo > 0)]
    m["second"] = (m.before_builds == SECOND_BEFORE).astype(float)
    return m


def toward(d):
    """Export's toward_change rule as notebook 05 applies it: sign(beta) == sign(x), only for
    tweaks with a single direction (not mixed, not upgrade-only)."""
    x = d.direction * d.log_ratio
    ok = (d.mixed_direction != "yes") & (d.upgrade_only != "yes") & x.notna()
    return ok, np.sign(d.beta) == np.sign(x)


main, h3 = load("main"), load("h3")
print("== Fits on file:", len(main), "main,", len(h3), "h3; errors:",
      int((main.error != "").sum()), int((h3.error != "").sum()))

for name, d in [("main (all weeks)", main), ("h3 (weeks 0-3)", h3)]:
    print(f"\n== {name}")
    p = patch(d)
    nz = d.beta.abs() > 2 * d.se
    ok, tw = toward(d)
    for pt in ["first", "second"]:
        s = p == pt
        print(f"  {pt}: n={int(s.sum())}, clearly nonzero {int((nz & s).sum())}, "
              f"toward among nonzero with direction {int((nz & s & ok & tw).sum())} of "
              f"{int((nz & s & ok).sum())}; toward overall {int((s & ok & tw).sum())} of "
              f"{int((s & ok).sum())}; median |beta| {100 * d.beta[s].abs().median():.2f} pp")
    L = line(d)
    print(f"  on the line: {len(L)} ({int((L.second == 0).sum())} + {int(L.second.sum())}); "
          f"left off: {sorted(set(d.index) - set(L.index))}")
    f = dose_response_fits(L.beta_lo, L.se_lo, L.x, L.second)
    for model in ["one slope", "slope per patch", "+ patch shift", "buff/nerf + patch"]:
        r = f[f.model == model]
        print(f"  {model:18s} " + "; ".join(f"{t} {c:+.3f} ± {s:.3f}" for t, c, s in
                                             zip(r.term, r.coef, r.se))
              + f"  (tau2 {r.tau2.iloc[0]:.4f}, Q {r.Q.iloc[0]:.0f} on {int(r.df.iloc[0])})")
    g = L.groupby("second").agg(n=("x", "size"), med_abs_x=("x", lambda s: s.abs().median()),
                                med_abs_beta_pp=("beta", lambda s: 100 * s.abs().median()),
                                med_se_lo=("se_lo", "median"))
    print(g.round(3).to_string())

print("\n== Named cards (main, pp)")
for cid in ["PARRY@v0.103.2/patch", "CORROSIVE_WAVE@v0.103.2/patch", "LEADING_STRIKE@v0.103.2/patch",
            "UNTOUCHABLE@v0.103.2/patch", "PINPOINT@v0.103.2/patch", "FIGHT_ME@v0.103.2/patch",
            "DANSE_MACABRE@v0.103.2/patch", "DEBILITATE@v0.107.1/patch", "ROYALTIES@v0.107.1/patch",
            "SERPENT_FORM@v0.103.2/patch", "UNTOUCHABLE@v0.107.1/patch"]:
    r = main.loc[cid]
    hh = h3.loc[cid]
    print(f"  {cid:32s} main {100 * r.beta:+6.2f} ± {100 * r.se:.2f}   h3 {100 * hh.beta:+6.2f} ± "
          f"{100 * hh.se:.2f}   placebo {100 * r.placebo_beta:+.2f} ± {100 * r.placebo_se:.2f}"
          if pd.notna(r.placebo_beta) else
          f"  {cid:32s} main {100 * r.beta:+6.2f} ± {100 * r.se:.2f}   h3 {100 * hh.beta:+6.2f} ± "
          f"{100 * hh.se:.2f}")

print("\n== Robustness checks vs main (shift in main SEs)")
for name in ["pooled_groups", "tagged", "untagged", "drop_shared_screens",
             "drop_behavior_flags", "drop_top_uploaders"]:
    c = load(name)
    j = main[["beta", "se"]].join(c[["beta", "se"]], rsuffix="_c").dropna()
    sh = (j.beta_c - j.beta) / j.se
    flips = ((np.sign(j.beta) != np.sign(j.beta_c)) & (j.beta.abs() > 2 * j.se)).sum()
    print(f"  {name:20s} median |shift| {sh.abs().median():.2f}, max {sh.abs().max():.2f}, "
          f"beyond 2 SE {100 * (sh.abs() > 2).mean():.0f}%, sign flips {int(flips)}")
t, u = load("tagged"), load("untagged")
j = t[["beta", "se"]].join(u[["beta", "se"]], rsuffix="_u").dropna()
chi2 = (((j.beta - j.beta_u) ** 2) / (j.se ** 2 + j.se_u ** 2)).sum()
print(f"  tagged vs untagged: corr {np.corrcoef(j.beta, j.beta_u)[0, 1]:.2f}, "
      f"chi2 of differences {chi2:.0f} on {len(j)}")

print("\n== Clustered SE ratios (main)")
for lab, den in [("robust", main.se_hc), ("iid", main.se_iid)]:
    r = main.se / den
    print(f"  clustered / {lab}: median {r.median():.2f}, range {r.min():.2f}-{r.max():.2f}")
