"""Section L, part 2: compare the three control scopes (from saved CSVs; seconds).

"color" = data/analysis/did_h3.parquet; "other" / "all" = triage/out/did_h3_ctrl_<scope>.csv
(l_control_scope.py). Rulers change only x and scopes change only y, so the ruler x scope
table needs no further fitting.

    python triage/scripts/l_compare.py

Reads TRIAGE_OUT's CSVs (default triage/out) and TRIAGE_AN's did_h3 (common.py).
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "triage/scripts")
from common import OUT, RULERS, add_rulers, all_tweaks, on_line, slopes_by_patch  # noqa: E402

pd.set_option("display.width", 220)
H3 = all_tweaks("h3")
S = {"color": H3}
for sc in ["other", "all"]:
    c = pd.read_csv(f"{OUT}/did_h3_ctrl_{sc}.csv").set_index("card_patch_id")
    d = H3.copy()
    for col in ["beta", "se", "beta_lo", "se_lo", "treated_rate_before", "control_rate_before",
                "n_control_cards", "n_offers"]:
        d[col] = c[col].reindex(d.index)
    d["beta_pp"], d["se_pp"] = d.beta, d.se
    S[sc] = d

W = pd.DataFrame({f"beta_{sc}": 100 * S[sc].beta for sc in S})
W["se_color"] = 100 * H3.se
for sc in ["other", "all"]:
    W[f"se_{sc}"] = 100 * S[sc].se
    W[f"ctrl_{sc}"] = S[sc].n_control_cards
W["patch"], W["card_id"], W["x"] = H3.patch, H3.card_id, H3.x
print("== per tweak, weeks 0-3, pp (43 solo-estimable)")
print(W.sort_values(["patch", "x"]).round(2).to_string())
for sc in ["other", "all"]:
    d = W[f"beta_{sc}"] - W.beta_color
    flip = np.sign(W[f"beta_{sc}"]) != np.sign(W.beta_color)
    big = d.abs() > W.se_color
    flip_sig = flip & ((W.beta_color.abs() > 2 * W.se_color) | (W[f"beta_{sc}"].abs() > 2 * W[f"se_{sc}"]))
    print(f"\n{sc} vs color: sign changes {int(flip.sum())} (of which clearly nonzero in either fit: "
          f"{int(flip_sig.sum())}); moved > 1 color SE {int(big.sum())} of {len(W)}; median |shift| "
          f"{d.abs().median():.2f} pp = {(d.abs() / W.se_color).median():.2f} SE; mean shift {d.mean():+.2f} pp; "
          f"regression of shift on color beta: {np.polyfit(W.beta_color, d, 1)[0]:+.3f}")
    for pt in ["first", "second"]:
        m = W.patch == pt
        print(f"  {pt}: median |shift| {(d[m].abs() / W.se_color[m]).median():.2f} SE; moved > 1 SE "
              f"{int(big[m].sum())} of {int(m.sum())}; mean shift {d[m].mean():+.2f} pp")
    print("  sign changes:", ", ".join(f"{r.card_id} ({r.beta_color:+.2f} -> {r[f'beta_{sc}']:+.2f})"
                                     for _, r in W[flip].iterrows()))

rows = []
for name, x, y, s in RULERS:
    row = dict(ruler=name[:45])
    for sc in S:
        r = slopes_by_patch(add_rulers(on_line(S[sc])), x, y, s)
        row[f"slope1_{sc}"], row[f"slope2_{sc}"], row[f"zdiff_{sc}"] = r["slope1"], r["slope2"], r["z_diff"]
    rows.append(row)
print("\n== dose-response (38 line tweaks) by ruler and control scope, weeks 0-3")
print(pd.DataFrame(rows).round(3).to_string(index=False))
for sc in S:
    r = slopes_by_patch(on_line(S[sc]))
    print(f"  ln, {sc}: slope1 {r['slope1']:.3f} ± {r['se1']:.3f}, slope2 {r['slope2']:+.3f} ± {r['se2']:.3f}, "
          f"z diff {r['z_diff']:+.2f}, tau2 {r['tau2']:.4f}, shift {r['shift']:+.3f} ± {r['se_shift']:.3f}")
