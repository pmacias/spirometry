"""Sections G3/G4 from the saved token-subset fits (seconds).

G3: slope-per-patch meta-regression (ln ruler, weeks 0-3) on the token subset against the
full data (did_h3), for all 38 and for the 35 estimable (>= 200 treated offers per block),
with and without token fixed effects, SEs clustered by run_key (primary) and by token.
G4: placebo z under the two clusterings; se_token / se_run on the real tweaks.

    python triage/scripts/g3_analysis.py
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "triage/scripts")
from common import all_tweaks, on_line, slopes_by_patch  # noqa: E402

pd.set_option("display.width", 220)
R = pd.read_csv("triage/out/g3_token_fits.csv")
H = on_line(all_tweaks("h3"))
est = (R.n_treated_before >= 200) & (R.n_treated_after >= 200)


def fmt(r):
    return (f"slope1 {r['slope1']:.3f} ± {r['se1']:.3f}, slope2 {r['slope2']:+.3f} ± {r['se2']:.3f}, "
            f"diff {r['diff']:+.3f} ± {r['se_diff']:.3f} (z {r['z_diff']:+.2f}), tau2 {r['tau2']:.4f}")


print("full data (did_h3), 38:", fmt(slopes_by_patch(H)))
for tfe in (False, True):
    for sel, lab in [(np.ones(len(R), bool), "38"), (est.to_numpy(), "35 estimable")]:
        d = R[(R.token_fe == tfe) & sel].set_index("card_patch_id")
        d["second"] = (d.patch == "second").astype(float)
        for se, sl in [("se_lo", "run-clustered"), ("se_lo_tok", "token-clustered")]:
            r = slopes_by_patch(d, "x", "beta_lo", se)
            print(f"subset, token FE {tfe}, {lab:12s}, {sl:15s} ({r['n1']}+{r['n2']}): {fmt(r)}")
        if not tfe and lab == "38":
            Hd = H.loc[d.index]
            print(f"  corr(subset, full) beta_lo: first {np.corrcoef(d.beta_lo[d.second == 0], Hd.beta_lo[d.second == 0])[0, 1]:.2f}, "
                  f"second {np.corrcoef(d.beta_lo[d.second == 1], Hd.beta_lo[d.second == 1])[0, 1]:.2f}; "
                  f"toward change: first {int((np.sign(d.beta_lo) == np.sign(d.x))[d.second == 0].sum())}/24, "
                  f"second {int((np.sign(d.beta_lo) == np.sign(d.x))[d.second == 1].sum())}/14; "
                  f"median se_lo subset/full: first {(d.se_lo / Hd.se_lo)[d.second == 0].median():.2f}, "
                  f"second {(d.se_lo / Hd.se_lo)[d.second == 1].median():.2f}")

print("\n== G4: clustering by token vs by run_key")
d = R[~R.token_fe]
print(f"real tweaks: se_token / se_run median {(d.se_tok / d.se_run).median():.2f} "
      f"(range {(d.se_tok / d.se_run).min():.2f}-{(d.se_tok / d.se_run).max():.2f}); by patch "
      + str(d.groupby("patch").apply(lambda g: round((g.se_tok / g.se_run).median(), 2)).to_dict()))
P = pd.read_csv("triage/out/g4_token_placebo.csv")
P = P[P.error.fillna("") == ""]
P["z_run"], P["z_tok"] = P.beta / P.se_run, P.beta / P.se_tok
rsd = lambda z: 1.4826 * (z - z.median()).abs().median()
for lab, g in [("all", P)] + list(P.groupby("patch")):
    print(f"placebo {lab}: n {len(g)}; sd z run {g.z_run.std():.2f} / token {g.z_tok.std():.2f}; robust sd "
          f"{rsd(g.z_run):.2f} / {rsd(g.z_tok):.2f}; |z| > 2 {(g.z_run.abs() > 2).mean():.2f} / "
          f"{(g.z_tok.abs() > 2).mean():.2f}; median se_tok/se_run {(g.se_tok / g.se_run).median():.2f}; "
          f"median pseudo offers {int(np.median(g.n_treated_before + g.n_treated_after))}")
# additive vs multiplicative on the subset placebo
for lab, g in [("all", P)]:
    A = np.column_stack([np.ones(len(g)), g.se_run ** 2])
    c, *_ = np.linalg.lstsq(A, g.beta ** 2, rcond=None)
    print(f"placebo beta^2 = {c[0]:.6f} + {c[1]:.2f} se_run^2 -> additive sd {100 * np.sqrt(max(c[0], 0)):.2f} pp, "
          f"factor {np.sqrt(max(c[1], 0)):.2f}")
