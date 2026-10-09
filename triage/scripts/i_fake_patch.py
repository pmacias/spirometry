"""Section I: a fake patch inside the old card versions (before-block drift test).

Specification (TRIAGE.md section E, run-level fit 1; choices fixed here before running):
- Before block = v0.103.2, after block = v0.103.3. No card changed between them
  (did.window_changes finds 0 changed cards); Stardust and Summon Forth (regent; bug-fix
  behavior differs between the two builds, as notebook 03 drops them) are removed from the
  data. Bad Luck (also flagged) has no character color and is never loaded.
- Treated cards: the 14 second-patch line tweaks (not mixed, not upgrade-only), each fit with
  fit_did on its real card_patch_id, so treated card, controls (windows.csv's control set
  for the real v0.103.3 -> v0.107.1 window: cards changed in v0.107.1 are excluded) and
  model are the main analysis's. Only the data's builds change. Week = whole weeks from
  v0.103.3's release (builds.csv), max_week_after=3 (weeks 0-3, the primary horizon), every
  other option at did_h3's defaults (control_scope "color", all offers, group terms).
- Dose = the tweak's eventual v0.107.1 dose x (did_h3), y = fake beta in log-odds
  (to_log_odds with the treated card's v0.103.2 pick rate). Meta-regression: intercept +
  slope on the 14 points (spirometry.meta, as the main per-patch fit).
- Report: fake slope ± se, z; |z| > 2 count at honest SEs and with z / 2.09 (the second
  patch's placebo robust sd), against what the second patch's placebo spread predicts.
- Secondary horizon (reported beside, never instead): all v0.103.3 weeks.

--check reproduces two saved did_h3 fits (v0.103.3 -> v0.107.1) with the derived card
colors (triage/scripts/db.py) and prints timing and peak memory; --tweaks limits the run.

    python triage/scripts/i_fake_patch.py --check
    python triage/scripts/i_fake_patch.py [--tweaks A B ...]
Writes triage/out/i_fake_patch.csv (card_patch_id-level estimates, no run IDs).
"""
import argparse
import os
import resource
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, "triage/scripts")
import db  # noqa: E402
from common import all_tweaks, fit, on_line  # noqa: E402
from spirometry import did  # noqa: E402

PLACEBO_F2 = 2.09
DROP = ["STARDUST", "SUMMON_FORTH"]


def peak_mb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2 ** 20   # bytes on macOS


ap = argparse.ArgumentParser()
ap.add_argument("--check", action="store_true")
ap.add_argument("--tweaks", nargs="*")
args = ap.parse_args()

db.use_derived_colors()
con = db.connect()
H3 = all_tweaks("h3")
L2 = on_line(H3)
L2 = L2[L2.second == 1]

if args.check:
    for cp in ["UPROAR@v0.107.1/patch", "BULWARK@v0.107.1/patch", "POUNCE@v0.107.1/patch",
               "JUGGERNAUT@v0.107.1/patch", "SIC_EM@v0.107.1/patch"]:   # one per color
        color = H3.loc[cp, "color"]
        t = time.time()
        df = did.load_block_data(con, color, "v0.103.3", "v0.107.1")
        tl = time.time() - t
        r = did.fit_did(df, cp, max_week_after=3)
        print(f"{cp}: load {tl:.1f} s ({len(df):,} rows), fit {time.time() - t - tl:.1f} s; "
              f"beta {r['beta']:.10f} vs saved {H3.loc[cp, 'beta']:.10f}; se {r['se']:.10f} vs "
              f"{H3.loc[cp, 'se']:.10f}; n_offers {r['n_offers']} vs {int(H3.loc[cp, 'n_offers'])}; "
              f"peak RSS {peak_mb():.0f} MB")
        del df
    sys.exit()

todo = L2 if not args.tweaks else L2[L2.index.isin(args.tweaks)]
rows = []
t0 = time.time()
for color, g in todo.groupby("color"):
    t = time.time()
    df = did.load_block_data(con, color, "v0.103.2", "v0.103.3")
    df = df[~df.card_id.isin(DROP)]
    tl = time.time() - t
    for cp in g.index:
        for horizon, mwa in [("weeks 0-3", 3), ("all weeks", None)]:
            ts = time.time()
            r = did.fit_did(df, cp, max_week_after=mwa)
            b_lo, s_lo = did.to_log_odds(r["beta"], r["se"], r["treated_rate_before"])
            rows.append(dict(card_patch_id=cp, card_id=g.loc[cp, "card_id"], color=color,
                             horizon=horizon, x=g.loc[cp, "x"], beta=r["beta"], se=r["se"],
                             se_hc=r["se_hc"], beta_lo=b_lo, se_lo=s_lo,
                             real_beta_lo=g.loc[cp, "beta_lo"], n_offers=r["n_offers"],
                             n_treated_offers=r["n_treated_offers"],
                             n_control_cards=r["n_control_cards"],
                             after_week_max=r["after_week_max"],
                             treated_rate_before=r["treated_rate_before"],
                             fit_s=time.time() - ts))
    print(f"{color}: load {tl:.1f} s, {len(g)} tweaks, peak RSS {peak_mb():.0f} MB", flush=True)
    del df
R = pd.DataFrame(rows)
os.makedirs("triage/out", exist_ok=True)
if not args.tweaks:
    R.drop(columns="fit_s").to_csv("triage/out/i_fake_patch.csv", index=False)
print(f"total {time.time() - t0:.0f} s; mean fit {R.fit_s.mean():.1f} s")

pd.set_option("display.width", 220)
for horizon, d in R.groupby("horizon", sort=False):
    d = d.sort_values("x")
    d["z"] = d.beta / d.se
    print(f"\n== {horizon}")
    print(d[["card_id", "x", "beta", "se", "z", "beta_lo", "se_lo", "real_beta_lo",
             "n_treated_offers", "after_week_max"]].assign(beta=100 * d.beta, se=100 * d.se)
          .round(3).to_string(index=False))
    if len(d) < 3:
        continue
    X = np.column_stack([np.ones(len(d)), d.x])
    b, cov, tau2, Q, dof = fit(d.beta_lo, d.se_lo, X)
    s = np.sqrt(np.diag(cov))
    print(f"fake slope {b[1]:+.3f} ± {s[1]:.3f} (z {b[1] / s[1]:+.2f}); intercept {b[0]:+.3f} ± "
          f"{s[0]:.3f}; tau2 {tau2:.4f}, Q {Q:.1f} on {dof}")
    for f, lab in [(1.0, "honest"), (PLACEBO_F2, "z / 2.09")]:
        bf, covf, t2f, *_ = fit(d.beta_lo, d.se_lo * f, X)
        print(f"  {lab}: |z| > 2 in {int((d.z.abs() / f > 2).sum())} of {len(d)} "
              f"(|z| > 3: {int((d.z.abs() / f > 3).sum())}); slope with se x {f}: "
              f"{bf[1]:+.3f} ± {np.sqrt(covf[1, 1]):.3f}")
    toward = int((np.sign(d.beta) == np.sign(d.x)).sum())
    print(f"  fake effects toward the eventual change: {toward} of {len(d)}; corr(fake, real "
          f"weeks 0-3 effect) {np.corrcoef(d.beta_lo, d.real_beta_lo)[0, 1]:+.2f}")
