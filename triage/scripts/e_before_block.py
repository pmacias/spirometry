"""Section E: is the second patch's dose-response different under the before-block variants?

did_second_patch_checks.parquet (notebook 02 section 7) has, for the 17 second-patch tweaks,
three fits: "main" (v0.103.3 before), "pooled before" (v0.103.2 + v0.103.3) and "no
first-patch controls" (v0.103.3, every card changed in the first patch dropped from the
controls). They are ALL-WEEKS fits (no max_week_after), so they are compared with did_main.

The dose line needs log-odds. The saved checks have only beta and se (pp scale), so each is
converted with the factor p(1-p) of the matching did_main row (k = beta / beta_lo), i.e. the
main design's before-block pick rate. For "pooled before" that p is not the pooled block's,
so the conversion is approximate; the pp-scale fit (no conversion) is shown too.

Read-only; runs in a second.   python triage/scripts/e_before_block.py
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "triage/scripts")
from common import AN, all_tweaks, on_line, slopes_by_patch  # noqa: E402

SP = pd.read_parquet(f"{AN}/did_second_patch_checks.parquet")
print("variants:", SP.variant.value_counts().to_dict(), "errors:",
      int(SP.get("error", pd.Series(dtype=str)).fillna("").ne("").sum()))
M = all_tweaks("main")
L = on_line(M)

chk = SP[SP.variant == "main"].set_index("card_patch_id")
j = chk.join(M[["beta", "se"]], rsuffix="_main")
print(f"sanity: 'main' variant vs did_main, max |beta diff| {np.abs(j.beta - j.beta_main).max():.2e}, "
      f"max |se diff| {np.abs(j.se - j.se_main).max():.2e}")

wide = SP.pivot_table(index="card_patch_id", columns="variant", values=["beta", "se"])
print("\nper tweak (pp):")
show = pd.DataFrame({v: 100 * wide["beta"][v] for v in wide["beta"].columns})
show["x"] = M.x.reindex(show.index)
show["on_line"] = show.index.isin(L.index)
print(show.round(2).sort_values("x").to_string())

rows = []
for v in ["main", "pooled before", "no first-patch controls"]:
    s = SP[SP.variant == v].set_index("card_patch_id")
    Lv = L.copy()
    idx = Lv.index[Lv.second == 1]
    k = (M.beta / M.beta_lo).abs()
    Lv.loc[idx, "beta"] = s.beta.reindex(idx)
    Lv.loc[idx, "beta_lo"] = (s.beta / k).reindex(idx)
    Lv.loc[idx, "se_lo"] = (s.se / k).reindex(idx)
    Lv["beta_pp"], Lv["se_pp"] = Lv.beta, np.where(Lv.second == 1, s.se.reindex(Lv.index), Lv.se)
    for scale, y, se in [("log-odds", "beta_lo", "se_lo"), ("pp", "beta_pp", "se_pp")]:
        r = slopes_by_patch(Lv, "x", y, se)
        rows.append(dict(variant=v, scale=scale, slope1=r["slope1"], se1=r["se1"],
                         slope2=r["slope2"], se2=r["se2"], shift=r["shift"], se_shift=r["se_shift"],
                         z_diff=r["z_diff"], tau2=r["tau2"]))
    d2 = Lv[Lv.second == 1]
    print(f"\n{v}: second-patch line tweaks toward their change: "
          f"{int((np.sign(d2.beta) == np.sign(d2.x)).sum())} of {len(d2)}; median |beta| "
          f"{100 * d2.beta.abs().median():.2f} pp; mean beta_lo buffs {d2[d2.x > 0].beta_lo.mean():+.3f}, "
          f"nerfs {d2[d2.x < 0].beta_lo.mean():+.3f}")
pd.set_option("display.width", 200)
print()
print(pd.DataFrame(rows).round(3).to_string(index=False))
