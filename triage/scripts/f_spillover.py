"""Section F: direction of the drop_shared_screens shift, as a check on the sign of same-screen
spillover. If substitution on shared screens pushes the controls opposite to the treated card,
dropping the shared control offers should move estimates TOWARD zero (|beta| smaller).

Read-only (did_main, did_drop_shared_screens). Runs in a second.
    python triage/scripts/f_spillover.py
"""
import numpy as np
import pandas as pd

AN = "data/analysis"


def load(n):
    d = pd.read_parquet(f"{AN}/did_{n}.parquet")
    return d.set_index("card_patch_id") if "card_patch_id" in d.columns else d


m, s = load("main"), load("drop_shared_screens")
j = m[["card_id", "before_builds", "beta", "se", "n_offers", "control_rate_before",
       "control_rate_after"]].join(
    s[["beta", "se", "n_offers", "control_rate_before", "control_rate_after"]], rsuffix="_d")
j["patch"] = np.where(j.before_builds == "v0.103.3", "second", "first")
j["toward_zero_pp"] = 100 * (j.beta - j.beta_d) * np.sign(j.beta)   # >0: dropping shrinks |beta|
j["shift_se"] = (j.beta_d - j.beta) / j.se
j["offers_dropped_share"] = 1 - j.n_offers_d / j.n_offers
j["ctrl_change_main_pp"] = 100 * (j.control_rate_after - j.control_rate_before)
j["ctrl_change_drop_pp"] = 100 * (j.control_rate_after_d - j.control_rate_before_d)
nz = j.beta.abs() > 2 * j.se
for lab, g in [("all", j), ("clearly nonzero", j[nz])] + [(p, j[j.patch == p]) for p in ["first", "second"]]:
    print(f"{lab:16s} n {len(g):2d}: |beta| shrinks when shared screens dropped in "
          f"{int((g.toward_zero_pp > 0).sum())}; mean shrink {g.toward_zero_pp.mean():+.3f} pp "
          f"(median {g.toward_zero_pp.median():+.3f}); median |shift| {g.shift_se.abs().median():.2f} SE; "
          f"offers dropped median {100 * g.offers_dropped_share.median():.1f}%")
X = np.column_stack([np.ones(len(j)), 100 * j.beta])
b, *_ = np.linalg.lstsq(X, 100 * (j.beta_d - j.beta), rcond=None)
print(f"(beta_drop - beta_main) on beta_main, pp: intercept {b[0]:+.3f}, slope {b[1]:+.4f} "
      "(negative slope = dropping shrinks large effects)")
print(j.sort_values("toward_zero_pp")[["card_id", "patch", "beta", "beta_d", "toward_zero_pp",
                                         "offers_dropped_share"]].assign(
    beta=lambda d: 100 * d.beta, beta_d=lambda d: 100 * d.beta_d).round(3).to_string())
