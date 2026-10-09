"""The IV primer's simulated game (`notebooks/iv_primer.ipynb`) as functions and tables.

The notebook stays the place to read and play with it; this module reruns the same game with
the same seeds and writes its tables, so the field guide's IV figures and numbers come from a
file, not from a notebook's printed output. The functions are copied from the notebook
unchanged (estimators, `simulate`, `replicate`, `summarize`); `tests/test_iv_sim.py` checks
them against the notebook's saved outputs.

A run is offered card X at random (the instrument); a hidden skill raises both picking X and
winning (the confounder); picking X raises the win probability by tau (0.10).

    python -m spirometry.iv_sim --out data/analysis/writeup
"""
import argparse
import pathlib

import numpy as np
import pandas as pd
from scipy.special import expit, logit

TAU = 0.10


def slope(x, y):
    """Slope of y on x (with intercept) and its HC1 standard error."""
    x = np.asarray(x, float); y = np.asarray(y, float); n = len(x)
    xc = x - x.mean(); sxx = (xc**2).sum()
    b = (xc * y).sum() / sxx
    e = y - y.mean() - b * xc
    se = np.sqrt(n / (n - 2) * (xc**2 * e**2).sum()) / sxx
    return b, se


def wald_iv(z, d, y):
    """IV estimate ITT / first stage, with a robust standard error from the IV residual."""
    z = np.asarray(z, float); d = np.asarray(d, float); y = np.asarray(y, float); n = len(z)
    zc = z - z.mean(); den = (zc * d).sum()
    b = (zc * y).sum() / den
    e = y - (y.mean() - b * d.mean()) - b * d
    se = np.sqrt(n / (n - 2) * (zc**2 * e**2).sum()) / abs(den)
    return b, se


def estimates(df):
    """All four quantities for one simulated dataset, plus the first-stage F."""
    naive, naive_se = slope(df.picked, df.won)
    itt, itt_se = slope(df.offered, df.won)
    fs, fs_se = slope(df.offered, df.picked)
    iv, iv_se = wald_iv(df.offered, df.picked, df.won)
    return dict(naive=naive, naive_se=naive_se, itt=itt, itt_se=itt_se,
                first_stage=fs, fs_se=fs_se, F=(fs / fs_se) ** 2, iv=iv, iv_se=iv_se)


def simulate(n=50_000, tau=0.10, het=0.0, skill_on_pick=1.0, skill_on_win=0.05,
             pick_intercept=-1.0, offer_rate=0.30, offer_skill=0.0, direct=0.0, seed=1):
    """One dataset of n runs (parameters as in the notebook: het = effect varies with skill,
    offer_skill > 0 breaks independence, direct > 0 breaks exclusion)."""
    rng = np.random.default_rng(seed)
    skill = rng.standard_normal(n)
    offered = rng.random(n) < expit(logit(offer_rate) + offer_skill * skill)
    picked = offered & (rng.random(n) < expit(pick_intercept + skill_on_pick * skill))
    effect_i = tau + het * skill
    p_win = np.clip(0.30 + effect_i * picked + direct * offered + skill_on_win * skill, 0, 1)
    won = rng.random(n) < p_win
    return pd.DataFrame({"skill": skill, "offered": offered.astype(int),
                         "picked": picked.astype(int), "won": won.astype(int),
                         "effect_i": effect_i})


def replicate(n_reps, seed0=1000, **kw):
    return pd.DataFrame([estimates(simulate(seed=seed0 + i, **kw)) for i in range(n_reps)])


def summarize(r, truth=TAU):
    out = {}
    for name in ["naive", "iv"]:
        covered = (r[name] - truth).abs() < 1.96 * r[name + "_se"]
        out[name] = dict(mean=r[name].mean(), sd_across_draws=r[name].std(),
                         mean_reported_se=r[name + "_se"].mean(),
                         share_ci_covers_truth=covered.mean())
    return pd.DataFrame(out).T


def run(out=None):
    """The notebook's sections 2-8 as tables (same seeds). Returns {name: DataFrame}; with
    `out`, writes iv_sim_<name>.csv there."""
    t = {}
    df = simulate(seed=2)
    e = estimates(df)
    t["single"] = pd.DataFrame({
        "quantity": ["naive", "itt", "first_stage", "iv"],
        "label": ["naive (won ~ picked)", "ITT (won ~ offered)",
                  "first stage (picked ~ offered)", "IV = ITT / first stage"],
        "estimate": [e["naive"], e["itt"], e["first_stage"], e["iv"]],
        "se": [e["naive_se"], e["itt_se"], e["fs_se"], e["iv_se"]],
        "truth": [TAU, np.nan, np.nan, TAU]})
    t["single"]["F"] = e["F"]
    t["single"]["n_runs"] = len(df)
    t["single"]["share_offered"] = df.offered.mean()
    t["single"]["share_picked"] = df.picked.mean()
    t["single"]["win_pickers"] = df.won[df.picked == 1].mean()
    t["single"]["win_non_pickers"] = df.won[df.picked == 0].mean()

    rep = replicate(300, n=20_000)
    t["draws"] = rep.rename_axis("draw").reset_index()
    t["draws_summary"] = summarize(rep).rename_axis("estimator").reset_index()

    rows = []
    for a in [-1, -2, -3, -4, -5, -6]:
        r = replicate(300, n=5_000, pick_intercept=a)
        rows.append(dict(
            pick_intercept=a, first_stage=r.first_stage.median(), F=r.F.median(),
            share_F_below_10=(r.F < 10).mean(),
            naive_median=r.naive.median(), naive_p10=r.naive.quantile(.1),
            naive_p90=r.naive.quantile(.9), iv_median=r.iv.median(),
            iv_p10=r.iv.quantile(.1), iv_p90=r.iv.quantile(.9)))
    t["weak"] = pd.DataFrame(rows)

    rows = []
    for s in [0, 0.02, 0.05, 0.08, 0.12]:
        r = replicate(200, n=20_000, skill_on_win=s)
        rows.append(dict(skill_on_win=s, naive=r.naive.mean(), iv=r.iv.mean()))
    conf = pd.DataFrame(rows)
    conf["naive_bias"], conf["iv_bias"] = conf.naive - TAU, conf.iv - TAU
    t["confounding"] = conf

    cases = {"clean": {}, "offer depends on skill": dict(offer_skill=0.5),
             "offer acts on winning directly": dict(direct=0.03)}
    rows = []
    for name, kw in cases.items():
        r = replicate(200, n=20_000, **kw)
        rows.append(dict(case=name, naive=r.naive.mean(), iv=r.iv.mean(),
                         first_stage=r.first_stage.mean()))
    broken = pd.DataFrame(rows)
    broken["iv_bias"] = broken.iv - TAU
    t["broken"] = broken

    d_het = simulate(n=200_000, het=0.05, seed=3)
    t["het"] = pd.DataFrame({
        "quantity": ["IV estimate", "true average effect, among runs that picked X",
                     "true average effect, among all runs"],
        "effect": [estimates(d_het)["iv"], d_het.effect_i[d_het.picked == 1].mean(),
                   d_het.effect_i.mean()]})
    if out:
        o = pathlib.Path(out)
        o.mkdir(parents=True, exist_ok=True)
        for name, d in t.items():
            d.to_csv(o / f"iv_sim_{name}.csv", index=False)
    return t


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--out", default="data/analysis/writeup")
    a = p.parse_args(argv)
    t = run(a.out)
    for name, d in t.items():
        print(f"iv_sim_{name + '.csv':22s} {len(d):4d} rows")
    print(t["single"][["label", "estimate", "se"]].round(4).to_string(index=False))
    print(f"-> {a.out}/")


if __name__ == "__main__":
    main()
