"""Section L: the 43 solo-estimable tweaks under control_scope "other" and "all" (Tier 2).

Every setting as did_h3 (run_all defaults, max_week_after=3: weeks 0-3, the primary
horizon); only control_scope changes. Uses did.run_all with the derived card colors
(triage/scripts/db.py; reproduces did_h3 exactly under "color").

    python triage/scripts/l_control_scope.py --scope other --tweaks UPROAR@v0.107.1/patch
        (test: prints runtime and peak memory; writes nothing)
    python triage/scripts/l_control_scope.py --scope other      (all 43 -> triage/out/)
    python triage/scripts/l_control_scope.py --scope all

Output: triage/out/did_h3_ctrl_<scope>.csv, one row per tweak (card_patch_id-level
estimates and counts; no run IDs). One scope per process, so peak memory is per scope.
"""
import argparse
import os
import resource
import sys
import time

import pandas as pd

sys.path.insert(0, "triage/scripts")
import db  # noqa: E402
from spirometry import did  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--scope", required=True, choices=["color", "all", "other"])
ap.add_argument("--tweaks", nargs="*")
args = ap.parse_args()

db.use_derived_colors()
con = db.connect()
LOAD_S = []
_load = did.load_block_data


def timed_load(*a, **k):                      # time the data loads separately from the fits
    t0 = time.time()
    df = _load(*a, **k)
    LOAD_S.append((time.time() - t0, len(df)))
    return df


did.load_block_data = timed_load
t = time.time()
R = did.run_all(con, tweaks=args.tweaks, control_scope=args.scope, max_week_after=3)
el = time.time() - t
rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2 ** 30
print(f"scope {args.scope}: {len(R)} tweaks in {el:.0f} s; peak RSS {rss:.1f} GB; errors "
      f"{int((R.error != '').sum())}; loads: "
      + ", ".join(f"{s:.0f} s / {n / 1e6:.1f}M rows" for s, n in LOAD_S))
cols = ["card_patch_id", "beta", "se", "beta_lo", "se_lo", "n_offers", "n_control_cards",
        "n_treated_offers", "treated_rate_before", "control_rate_before", "error"]
print(R[cols].to_string(index=False))
if not args.tweaks:
    os.makedirs("triage/out", exist_ok=True)
    keep = [c for c in R.columns if c not in ("formula", "ci95")]
    R[keep].to_csv(f"triage/out/did_h3_ctrl_{args.scope}.csv", index=False)
