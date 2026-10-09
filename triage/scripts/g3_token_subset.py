"""Sections G3 and G4: the dose-response on the token subset, and clustering by token.

did.fit_did has no option to restrict to a subset of runs, but load_block_data's frame
carries uploader_hash, so the subset is a row filter on that frame (runs with a token; their
controls' offers are from the same runs). The fit is fit_did's model and filters, reused
through did._subset and did._fixed_effects (read-only use of src/, nothing edited):

    picked ~ treat_post | card_id^upg + card_id^group + block^group + act + asc
    (weeks 0-3: max_week_after=3; same-color controls; group terms as fit_did decides)

For each fit, two clusterings of the same estimate: by run_key (the project's) and by
uploader_hash (token). Optional variant: + uploader_hash fixed effects (each player
compared with themselves). y in log-odds with the subset's own treated pick rate before.

G4 placebo: up to N_PSEUDO (5) unchanged cards per window (color x patch), drawn with
seed 20261008 from the window's eligible pseudo cards (did.control_cards for the window's
first line tweak, >= 200 offers per block on the subset), fit as fake treated cards with
the real treated card left out (did._subset(pseudo=...)), weeks 0-3, both clusterings.

    python triage/scripts/g3_token_subset.py --tweaks A B C       (test: timing only)
    python triage/scripts/g3_token_subset.py --all                (38 tweaks + placebo)
Writes triage/out/g3_token_fits.csv and triage/out/g4_token_placebo.csv (card-level
estimates and counts; no token or run IDs).
"""
import argparse
import os
import resource
import sys
import time
import warnings

import numpy as np
import pandas as pd
import pyfixest as pf

sys.path.insert(0, "triage/scripts")
import db  # noqa: E402
from common import all_tweaks, on_line  # noqa: E402
from spirometry import did  # noqa: E402

N_PSEUDO, SEED, MIN_PSEUDO = 5, 20261008, 200
ap = argparse.ArgumentParser()
ap.add_argument("--tweaks", nargs="*")
ap.add_argument("--all", action="store_true")
ap.add_argument("--no-placebo", action="store_true")
args = ap.parse_args()

db.use_derived_colors()
con = db.connect()
L = on_line(all_tweaks("h3"))
todo = L if args.all else L[L.index.isin(args.tweaks or [])]


def fit_one(d0, cpid, token_fe=False, pseudo=None):
    d, treated = did._subset(d0, cpid, max_week_after=3, pseudo=pseudo)
    fe = did._fixed_effects(d, None, False) + (["uploader_hash"] if token_fe else [])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        f = pf.feols("picked ~ treat_post | " + " + ".join(fe), data=d,
                     vcov={"CRV1": "run_key"})
        beta, se_run = float(f.coef()["treat_post"]), float(f.se()["treat_post"])
        se_tok = float(f.vcov({"CRV1": "uploader_hash"}).se()["treat_post"])
    rates = did._rates(d)
    k = rates["treated_rate_before"] * (1 - rates["treated_rate_before"])
    return dict(beta=beta, se_run=se_run, se_tok=se_tok, beta_lo=beta / k, se_lo=se_run / k,
                se_lo_tok=se_tok / k, n_offers=int(f._N), n_runs=int(d.run_key.nunique()),
                n_tokens=int(d.uploader_hash.nunique()),
                n_treated_before=int((d.is_treated & ~d.after).sum()),
                n_treated_after=int((d.is_treated & d.after).sum()), **rates)


rows, prow = [], []
t0 = time.time()
rng = np.random.default_rng(SEED)
for (color, before, after), g in todo.groupby(["color", "before_builds", "after_builds"]):
    t = time.time()
    df = did.load_block_data(con, color, before, after)
    df = df[df.uploader_hash.notna()]
    tl = time.time() - t
    for cp in g.index:
        for tfe in (False, True):
            ts = time.time()
            try:
                r = fit_one(df, cp, token_fe=tfe)
                err = ""
            except Exception as e:
                r, err = {}, f"{type(e).__name__}: {e}"
            rows.append(dict(card_patch_id=cp, card_id=g.loc[cp, "card_id"], patch=g.loc[cp, "patch"],
                             x=g.loc[cp, "x"], token_fe=tfe, error=err, fit_s=time.time() - ts, **r))
    if args.all and not args.no_placebo:
        cp0 = g.index[0]
        cnt = df[~df.week.gt(3) | (df.block == "before")].groupby(["card_id", "block"],
                                                                   observed=True).size().unstack()
        elig = [c for c in did.control_cards(cp0, df=df)
                if c in cnt.index and cnt.loc[c].min() >= MIN_PSEUDO]
        picks = sorted(rng.choice(elig, min(N_PSEUDO, len(elig)), replace=False))
        for c in picks:
            try:
                r = fit_one(df, cp0, pseudo=c)
                err = ""
            except Exception as e:
                r, err = {}, f"{type(e).__name__}: {e}"
            prow.append(dict(window=f"{color} {before}->{after}", patch=g.loc[cp0, "patch"],
                             pseudo_card=c, error=err, **r))
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2 ** 30
    print(f"{color} {before}->{after}: load+filter {tl:.1f} s ({len(df):,} subset rows), "
          f"{len(g)} tweaks; elapsed {time.time() - t0:.0f} s; peak RSS {rss:.1f} GB", flush=True)
    del df
R = pd.DataFrame(rows)
print(f"total {time.time() - t0:.0f} s; mean fit {R.fit_s.mean():.1f} s; errors "
      f"{int((R.error != '').sum())}")
pd.set_option("display.width", 220)
print(R.drop(columns=["fit_s"]).round(4).to_string(index=False))
if args.all:
    os.makedirs("triage/out", exist_ok=True)
    R.drop(columns="fit_s").to_csv("triage/out/g3_token_fits.csv", index=False)
    if prow:
        pd.DataFrame(prow).to_csv("triage/out/g4_token_placebo.csv", index=False)
