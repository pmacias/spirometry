"""Section J: regression to the mean in patch 1? (Tier 1: saved outputs only.)

Inputs: event_studies.parquet (notebook 02 section 5: the treated card's gap to its controls
per (week, block) cell, pp, all weeks, before-block week -1 = 0 as the reference, weeks
binned at -6 and 8), did_h3 (weeks 0-3 effects, log-odds) through common.all_tweaks.

Declared before looking (Part 2 brief):
J1  pre-movement = gap at week -1 minus gap at week -4 (= -coef(week -4, before)), against
    the controls, converted to log-odds with the did_h3 p(1-p) of the treated card's
    before-block pick rate; next to the weeks 0-3 effect; share whose pre-movement opposes
    the patch-note direction (sign(pre) = -sign(x)).
J2  one meta-regression on patch 1's 24 line tweaks: beta_lo(weeks 0-3) ~ 1 + x + pre
    (spirometry.meta random effects). Reversion: pre coefficient < 0; continuation: >= 0.
    Also reported: slope on x without pre (same 24 points).
J3  per post-release week w inside v0.103.2 (weeks 0..5 are complete before v0.103.3's
    release on 2026-05-29; week 6 holds one day), the dose-response slope of
    y_w = coef(w, after) - (weighted mean of the before cells, week -5..-1, ref = 0), in
    log-odds, on the 24 tweaks (intercept + slope, same meta-regression). Also relative to
    week -1 alone. Cell SEs only (covariance with the reference cells ignored).
J4  as J1 for patch 2's 14 tweaks: movement from week -3 to week -1 (= -coef(week -3)).

Read-only; runs in a second.    python triage/scripts/j_reversion.py

Writes (added for the final-table rerun; TRIAGE_OUT sets the folder, TRIAGE_AN the fits):
j_premove.csv (J1 and J4: one row per line tweak, patch column), j_models.csv (J2's models
and J4's comparison model) and j_weekly.csv (J3). Card-level estimates only.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "triage/scripts")
from common import AN, OUT, all_tweaks, fit, on_line  # noqa: E402

pd.set_option("display.width", 220)
ES = pd.read_parquet(f"{AN}/event_studies.parquet")
ES = ES[ES.error.fillna("") == ""]
L = on_line(all_tweaks("h3"))
L["k"] = L.treated_rate_before * (1 - L.treated_rate_before)


def cell(cpid, week, block="before"):
    c = ES[(ES.card_patch_id == cpid) & (ES.week == week) & (ES.block == block)]
    return (float(c.coef.iloc[0]), float(c.se.iloc[0]), int(c.n_offers.iloc[0])) if len(c) \
        else (np.nan, np.nan, 0)


def premove(patch, start_week):
    d = L[L.patch == patch].copy()
    pre = [cell(c, start_week) for c in d.index]
    d["pre_pp"] = [-100 * p[0] for p in pre]
    d["pre_se_pp"] = [100 * p[1] for p in pre]
    d["pre_n"] = [p[2] for p in pre]
    d["pre_lo"] = -np.array([p[0] for p in pre]) / d.k
    d["pre_se_lo"] = np.array([p[1] for p in pre]) / d.k
    d["eff_pp"] = 100 * d.beta
    d["opposes"] = np.sign(d.pre_lo) == -np.sign(d.x)
    return d


def report_pre(d, label):
    print(f"\n== {label}")
    cols = ["card_id", "x", "pre_pp", "pre_se_pp", "pre_lo", "pre_se_lo", "eff_pp", "beta_lo",
            "pre_n", "opposes"]
    print(d.sort_values("x")[cols].round(3).to_string(index=False))
    big = d.pre_lo.abs() > 2 * d.pre_se_lo
    print(f"pre-movement opposes the patch-note direction: {int(d.opposes.sum())} of {len(d)}; "
          f"among |pre| > 2 SE: {int((d.opposes & big).sum())} of {int(big.sum())}")
    print(f"median |pre| {d.pre_lo.abs().median():.3f} log-odds ({d.pre_pp.abs().median():.2f} pp); "
          f"median |weeks 0-3 effect| {d.beta_lo.abs().median():.3f} ({d.eff_pp.abs().median():.2f} pp); "
          f"median pre SE {d.pre_se_lo.median():.3f}; corr(pre, effect) "
          f"{np.corrcoef(d.pre_lo, d.beta_lo)[0, 1]:+.2f}, corr(pre, x) {np.corrcoef(d.pre_lo, d.x)[0, 1]:+.2f}")
    for s, nm in [(1, "buffs"), (-1, "nerfs")]:
        g = d[np.sign(d.x) == s]
        print(f"  {nm}: n {len(g)}, mean pre {g.pre_lo.mean():+.3f} log-odds, mean effect {g.beta_lo.mean():+.3f}")


# J1
D1 = premove("first", -4)
report_pre(D1, "J1: patch 1, movement week -4 -> -1 (log-odds), next to the weeks 0-3 effect")

MODELS = []


def model(name, patch, b, c, n, tau2=None, pre=True):
    s = np.sqrt(np.diag(c))
    MODELS.append(dict(model=name, patch=patch, n=n, slope_x=b[1], se_x=s[1],
                       pre_coef=b[2] if pre else np.nan, pre_se=s[2] if pre else np.nan,
                       intercept=b[0], tau2=np.nan if tau2 is None else tau2))


# J2
print("\n== J2: patch 1, beta_lo ~ 1 + x + pre (random-effects meta-regression)")
X0 = np.column_stack([np.ones(len(D1)), D1.x])
b0, c0, t0, Q0, df0 = fit(D1.beta_lo, D1.se_lo, X0)
X = np.column_stack([np.ones(len(D1)), D1.x, D1.pre_lo])
b, c, t2, Q, dof = fit(D1.beta_lo, D1.se_lo, X)
s, s0 = np.sqrt(np.diag(c)), np.sqrt(np.diag(c0))
model("effect ~ x", "first", b0, c0, len(D1), t0, pre=False)
model("effect ~ x + pre (declared)", "first", b, c, len(D1), t2)
print(f"without pre: slope on x {b0[1]:.3f} ± {s0[1]:.3f}; tau2 {t0:.4f}")
print(f"with pre:    slope on x {b[1]:.3f} ± {s[1]:.3f}; pre coefficient {b[2]:+.3f} ± {s[2]:.3f} "
      f"(z {b[2] / s[2]:+.2f}); intercept {b[0]:+.3f} ± {s[0]:.3f}; tau2 {t2:.4f}")
# sensitivity: pre as a slope over weeks -5..-1 (e_pretrends' definition) x 3 weeks
D1s = D1.copy()
for cp in D1s.index:
    pre = ES[(ES.card_patch_id == cp) & (ES.block == "before") & (ES.week < 0)]
    w = 1 / pre.se ** 2
    wk = np.r_[pre.week, -1]
    cf = np.r_[pre.coef, 0.0]
    ww = np.r_[w, w.max()]
    xm = np.average(wk, weights=ww)
    D1s.loc[cp, "pre_slope_lo"] = 3 * (ww * (wk - xm) * cf).sum() / (ww * (wk - xm) ** 2).sum() / D1s.loc[cp, "k"]
Xs = np.column_stack([np.ones(len(D1s)), D1s.x, D1s.pre_slope_lo])
bs, cs, ts_, *_ = fit(D1s.beta_lo, D1s.se_lo, Xs)
model("effect ~ x + 3 x pre-slope (weeks -5..-1)", "first", bs, cs, len(D1s), ts_)
print(f"sensitivity, pre = 3 x weighted slope over weeks -5..-1 (ref cell at 0): slope on x "
      f"{bs[1]:.3f} ± {np.sqrt(cs[1, 1]):.3f}; pre coefficient {bs[2]:+.3f} ± {np.sqrt(cs[2, 2]):.3f}")
# leave out the largest |pre|
o = D1.pre_lo.abs().idxmax()
m = D1.index != o
bl, cl, *_ = fit(D1.beta_lo[m], D1.se_lo[m], X[m])
model(f"declared, without {D1.loc[o, 'card_id']} (largest |pre|)", "first", bl, cl, int(m.sum()))
print(f"without the largest |pre| ({D1.loc[o, 'card_id']}): slope on x {bl[1]:.3f} ± {np.sqrt(cl[1, 1]):.3f}; "
      f"pre {bl[2]:+.3f} ± {np.sqrt(cl[2, 2]):.3f}")

# J3
print("\n== J3: patch 1 dose-response by post-release week (event_studies, all-weeks fits)")
rows = []
for w in range(0, 9):
    ys, ys1, ses, ns, xs = [], [], [], [], []
    for cp in D1.index:
        pre = ES[(ES.card_patch_id == cp) & (ES.block == "before") & (ES.week < 0)]
        wts = np.r_[pre.n_offers, cell(cp, -1)[2] or D1.loc[cp, "pre_n"]]
        base = np.average(np.r_[pre.coef, 0.0], weights=wts)
        cf, se, n = cell(cp, w, "after")
        if np.isnan(cf) or n < 200:
            continue
        k = D1.loc[cp, "k"]
        ys.append((cf - base) / k); ys1.append(cf / k); ses.append(se / k); ns.append(n)
        xs.append(D1.loc[cp, "x"])
    if len(ys) < 10:
        rows.append(dict(week=w, n_tweaks=len(ys)))
        continue
    Xw = np.column_stack([np.ones(len(xs)), xs])
    bw, cw, tw, *_ = fit(ys, ses, Xw)
    bw1, cw1, *_ = fit(ys1, ses, Xw)
    rows.append(dict(week=w, n_tweaks=len(ys), median_offers=int(np.median(ns)),
                     slope=bw[1], se=np.sqrt(cw[1, 1]), intercept=bw[0], tau2=tw,
                     slope_vs_week_m1=bw1[1], se_vs_week_m1=np.sqrt(cw1[1, 1])))
J3 = pd.DataFrame(rows)
print(J3.round(3).to_string(index=False))
ok = J3.dropna(subset=["slope"])
ok = ok[ok.week <= 5]
wts = 1 / ok.se ** 2
xm = np.average(ok.week, weights=wts)
tr = (wts * (ok.week - xm) * ok.slope).sum() / (wts * (ok.week - xm) ** 2).sum()
print(f"weeks 0-5: weighted trend of the weekly slope {tr:+.3f} per week (weekly slopes are "
      f"correlated through shared cards; no SE given)")

# J4
D2 = premove("second", -3)
report_pre(D2, "J4: patch 2, movement week -3 -> -1 (log-odds), next to the weeks 0-3 effect")
X2 = np.column_stack([np.ones(len(D2)), D2.x, D2.pre_lo])
b2, c2, t22, *_ = fit(D2.beta_lo, D2.se_lo, X2)
model("effect ~ x + pre (comparison only)", "second", b2, c2, len(D2), t22)
print(f"for comparison only (14 points): beta_lo ~ 1 + x + pre: slope on x {b2[1]:+.3f} ± "
      f"{np.sqrt(c2[1, 1]):.3f}; pre {b2[2]:+.3f} ± {np.sqrt(c2[2, 2]):.3f}")

os.makedirs(OUT, exist_ok=True)
cols = ["card_id", "patch", "x", "pre_lo", "pre_se_lo", "pre_pp", "pre_se_pp", "pre_n", "beta_lo",
        "se_lo", "eff_pp", "opposes"]
pd.concat([D1[cols], D2[cols]]).rename_axis("card_patch_id").reset_index().to_csv(
    f"{OUT}/j_premove.csv", index=False)
pd.DataFrame(MODELS).to_csv(f"{OUT}/j_models.csv", index=False)
J3.to_csv(f"{OUT}/j_weekly.csv", index=False)
print(f"-> {OUT}/j_premove.csv, j_models.csv, j_weekly.csv")
