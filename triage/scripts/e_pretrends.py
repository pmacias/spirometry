"""Section E, part 2: do the treated cards' pre-release trends line up with their doses?

From event_studies.parquet (notebook 02 section 5; per tweak, week x block cells relative to the
before build's week -1). Pre-trend slope = weighted slope of the before-build cells with week < 0
(notebook 02's pretrend_summary, reimplemented). A dose-correlated pre-trend would bias the
DiD slope (e.g. buffs chosen for cards already falling). Read-only; runs in a second.

    python triage/scripts/e_pretrends.py
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "triage/scripts")
from common import AN, all_tweaks, on_line, fit  # noqa: E402

ES = pd.read_parquet(f"{AN}/event_studies.parquet")
ES = ES[ES.error.fillna("") == ""]
L = on_line(all_tweaks("h3"))


def pre_slope(es):
    pre = es[(es.block == "before") & (es.week < 0)].dropna(subset=["coef", "se"])
    if len(pre) < 2:
        return np.nan, np.nan, len(pre)
    w = 1 / pre.se ** 2
    xm = np.average(pre.week, weights=w)
    sxx = (w * (pre.week - xm) ** 2).sum()
    return (w * (pre.week - xm) * pre.coef).sum() / sxx, 1 / np.sqrt(sxx), len(pre)


rows = []
for cpid, g in ES.groupby("card_patch_id"):
    if cpid in L.index:
        s, se, n = pre_slope(g)
        rows.append(dict(card_patch_id=cpid, slope_pp_wk=100 * s, se_pp_wk=100 * se, n_pre=n))
T = pd.DataFrame(rows).set_index("card_patch_id").join(L[["card_id", "patch", "x", "beta"]])
T["beta_pp"] = 100 * T.beta
T["sign_x"] = np.sign(T.x)
print(T.drop(columns="beta").sort_values(["patch", "x"]).round(2).to_string())
for pt in ["first", "second"]:
    d = T[T.patch == pt].dropna(subset=["slope_pp_wk"])
    X = np.column_stack([np.ones(len(d)), d.x])
    b, cov, tau2, Q, dof = fit(d.slope_pp_wk, d.se_pp_wk, X)
    print(f"{pt}: n {len(d)} (pre weeks per tweak: {sorted(d.n_pre.unique())}); pre-slope on dose "
          f"{b[1]:+.2f} ± {np.sqrt(cov[1, 1]):.2f} pp/week per unit ln (z {b[1] / np.sqrt(cov[1, 1]):+.2f}); "
          f"mean pre-slope buffs {d[d.x > 0].slope_pp_wk.mean():+.2f}, nerfs {d[d.x < 0].slope_pp_wk.mean():+.2f}; "
          f"corr(pre-slope, x) {np.corrcoef(d.slope_pp_wk, d.x)[0, 1]:+.2f}")
