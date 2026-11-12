"""Section S (SENSITIVITY CHECK): an additive calibration of the DiD errors.

The headline stays the multiplicative calibration (SE x factor; clearly_nonzero_h_cal). This
script changes no factor, number or result. Rules, definitions and what each outcome means are
in TRIAGE.md section S, written before this ran.

    python triage/scripts/s_additive.py --part 1    # additive model on the 463 placebo pairs
    python triage/scripts/s_additive.py --part 2    # counts on the 43 tweaks under rules a-f
    python triage/scripts/s_additive.py --part 3    # dose-response with additive errors
    python triage/scripts/s_additive.py --privacy   # check every s_*.csv
    python triage/scripts/s_additive.py             # all of the above, in order

Run from the repository root. Reads saved tables only (no database, no DiD refit):
results/pick_rate_did.csv, data/analysis/{did_h3,placebo_h3,offer_rate}.parquet,
data/analysis/placebo_diagnostics_summary.csv, data/analysis/writeup/{calibrated_counts,
se_inflation}.csv, triage/out_final/{q_tau,r_rarity_tau,r_rarity_fits}.csv.
Writes triage/out_final/s_*.csv (TRIAGE_OUT overrides), keyed by card and patch; no run IDs.
Each part saves its tables when it finishes; the whole script takes a few minutes.

SE_add = sqrt(SE^2 + tau^2), tau = Q's placebo spread in pp (beta_i ~ N(mu, SE_i^2 + tau^2)).
"""
import argparse
import os
import re
import sys
import time

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, "triage/scripts")
import q_nudge as q  # noqa: E402  (mle, robust_sd, cluster_boot, pct)
from spirometry import did, sensitivity  # noqa: E402
from spirometry.export import CAL_Z, PLACEBO_FACTORS_H3, check_output, toward_change  # noqa: E402

OUT = os.environ.get("TRIAGE_OUT", "triage/out_final")
AN = "data/analysis"
PATCHES = ("first", "second")
N_BINS, BAND, N_BOOT, N_SIM, SEED = 6, (0.8, 1.25), 2000, 2000, 20261111
MIN_RARITY_REFIT = 20          # pairs needed in every leave-one-character-out rarity refit
EXISTING = {  # calibrated_counts.csv, weeks 0-3: clearly nonzero, with a direction, toward
    ("a", "first"): (21, 20, 17), ("a", "second"): (8, 7, 5),
    ("b", "first"): (13, 12, 12), ("b", "second"): (2, 2, 2)}
RULES = {"a": "uncalibrated (se_h)", "b": "multiplicative (se_h x factor)",
         "c": "additive, tau per patch", "d": "additive, tau per patch x rarity",
         "e": "empirical, pooled per patch (p < 0.05)",
         "f": "placebo_vs_real, per window (p < 0.05)"}


def save(name, df):
    check_output(name, df)
    df.to_csv(f"{OUT}/{name}.csv", index=False)
    print(f"  saved {OUT}/{name}.csv ({len(df)} rows)")
    return df


def stop(msg):
    raise SystemExit(f"GATE FAILED: {msg}")


# ------------------------------------------------------------------------------------ inputs

def q_tau():
    t = pd.read_csv(f"{OUT}/q_tau.csv")
    t = t[t.subset == "all pairs"]
    pp = t[t.scale == "pp"].set_index("fit").tau
    lo = t[t.scale == "log-odds"].set_index("fit").tau
    return {p: float(pp[p]) for p in PATCHES}, {p: float(lo[p]) for p in PATCHES}


def rarity_tau():
    t = pd.read_csv(f"{OUT}/r_rarity_tau.csv")
    return {(r.patch, r.rarity): float(r.tau_pp) for r in t.itertuples()}


def load_pairs():
    """The 463 pairs (placebo_pairs), beta and se in pp, R's rarity; gated against the
    factors, q_tau.csv and r_rarity_tau.csv."""
    p = did.placebo_pairs(pd.read_parquet(q.PLACEBO))
    p["b"], p["s"] = 100 * p.beta, 100 * p.se
    # converters: the Defect card NULL must stay a string, not become a missing value
    rar = pd.read_csv(f"{OUT}/r_rarity_fits.csv", converters={"pseudo_card": str})
    rar = rar.drop_duplicates("pseudo_card")
    p["rarity"] = p.pseudo_card.map(dict(zip(rar.pseudo_card, rar.rarity)))
    p = p.sort_values(["patch", "color", "fit_on", "pseudo_card"]).reset_index(drop=True)
    if len(p) != 463 or p.rarity.isna().any():
        stop(f"{len(p)} pairs, {int(p.rarity.isna().sum())} without a rarity")
    tq, _ = q_tau()
    for pt in PATCHES:
        g = p[p.patch == pt]
        rs = q.robust_sd(g.z)
        if round(rs, 2) != PLACEBO_FACTORS_H3[pt]:
            stop(f"robust sd of z, {pt}: {rs:.3f}, not {PLACEBO_FACTORS_H3[pt]}")
        tau = q.mle(g.b, g.s)[0]
        if abs(tau - tq[pt]) > 1e-3:
            stop(f"tau {pt}: {tau:.4f}, q_tau.csv has {tq[pt]:.4f}")
    for (pt, rr), want in rarity_tau().items():
        g = p[(p.patch == pt) & (p.rarity == rr)]
        tau = q.mle(g.b, g.s)[0]
        if abs(tau - want) > 1e-3:
            stop(f"tau {pt} {rr}: {tau:.4f}, r_rarity_tau.csv has {want:.4f}")
    print("gate: 463 pairs; robust sd 4.10 / 2.67; q_tau.csv and r_rarity_tau.csv reproduced")
    return p


# ------------------------------------------------------------------------------------ part 1

def loco_tau(b, s, color, group=None):
    """tau for each row from the rows of its group (None: all rows) with another color."""
    group = np.zeros(len(b), int) if group is None else np.asarray(group)
    out, rows = np.full(len(b), np.nan), []
    for gname in pd.unique(group):
        for c in pd.unique(color[group == gname]):
            fit = (group == gname) & (color != c)
            tau = q.mle(b[fit], s[fit])[0] if fit.sum() >= 2 else np.nan
            out[(group == gname) & (color == c)] = tau
            rows.append(dict(group=gname, left_out=c, n_fit=int(fit.sum()),
                             n_scored=int(((group == gname) & (color == c)).sum()), tau=tau))
    return out, rows


def bins_of(offers):
    """Six equal-count bins by rank of offers (ties in file order), 1 = fewest offers."""
    r = pd.Series(offers).rank(method="first").to_numpy()
    return np.minimum((N_BINS * (r - 1) / len(r)).astype(int), N_BINS - 1) + 1


def spearman(a, b):
    return stats.spearmanr(a, b).statistic if len(set(a)) > 1 and len(set(b)) > 1 else np.nan


def variants(p, tq, tr):
    """Every z of part 1 on the pairs of one patch (p: one patch, index reset)."""
    b, s, col = p.b.to_numpy(), p.s.to_numpy(), p.color.to_numpy()
    pt = p.patch.iat[0]
    z = {"mult": p.z.to_numpy() / PLACEBO_FACTORS_H3[pt]}
    t_loco, rows = loco_tau(b, s, col)
    for r in rows:
        r.update(patch=pt, scheme="patch", tau_all=tq[pt])
    z["add_loco"] = b / np.hypot(s, t_loco)
    z["add_all"] = b / np.hypot(s, tq[pt])
    rar = p.rarity.to_numpy()
    t_rl, rrows = loco_tau(b, s, col, rar)
    for r in rrows:
        r.update(patch=pt, scheme="patch x rarity", tau_all=tr[(pt, r["group"])])
    t_ra = np.array([tr[(pt, x)] for x in rar])
    z["add_rarity_loco"] = b / np.hypot(s, t_rl)
    z["add_rarity_all"] = b / np.hypot(s, t_ra)
    taus = dict(tau_loco=t_loco, tau_all=np.full(len(p), tq[pt]), tau_rarity_loco=t_rl,
                tau_rarity_all=t_ra)
    return z, taus, rows + rrows


def bin_stats(p, zv, patch, subset, variant):
    """Per bin and whole patch: robust sd with a card-resampling interval; Spearman of |z|
    against offers with one. Returns (bin rows, trend row)."""
    off, cards = p.n_treated_offers.to_numpy(), p.pseudo_card.to_numpy()
    bn = bins_of(off)
    rows = []
    for k in range(1, N_BINS + 1):
        m = bn == k
        bt = q.cluster_boot(cards[m], lambda i, zz=zv[m]: q.robust_sd(zz[i]), n=N_BOOT, seed=SEED)
        rs = q.robust_sd(zv[m])
        rows.append(dict(patch=patch, subset=subset, variant=variant, bin=k, n=int(m.sum()),
                         offers_min=int(off[m].min()), offers_median=float(np.median(off[m])),
                         offers_max=int(off[m].max()), median_se_pp=float(np.median(p.s[m])),
                         n_upgraded_fits=int((p.fit_on[m] == "upgraded offers").sum()),
                         robust_sd=rs, lo=q.pct(bt)[0], hi=q.pct(bt)[1],
                         in_band=bool(BAND[0] <= rs <= BAND[1]),
                         sd=float(np.std(zv[m], ddof=1)), share_abs_gt2=float((np.abs(zv[m]) > CAL_Z).mean())))
    az = np.abs(zv)
    bt = q.cluster_boot(cards, lambda i: spearman(az[i], off[i]), n=N_BOOT, seed=SEED)
    lo, hi = q.pct(bt)
    rho = spearman(az, off)
    n_out = sum(not r["in_band"] for r in rows)
    trend = dict(patch=patch, subset=subset, variant=variant, n=len(p), robust_sd=q.robust_sd(zv),
                 sd=float(np.std(zv, ddof=1)), share_abs_gt2=float((az > CAL_Z).mean()),
                 share_abs_gt3=float((az > 3).mean()), median_abs=float(np.median(az)),
                 spearman=rho, spearman_lo=lo, spearman_hi=hi,
                 trend=("none shown (interval includes 0)" if lo <= 0 <= hi else
                        "rises with offers" if lo > 0 else "falls with offers"),
                 n_bins_in_band=N_BINS - n_out, bins_out=" ".join(
                     f"{r['bin']}:{r['robust_sd']:.2f}" for r in rows if not r["in_band"]),
                 passes=bool(n_out == 0 and lo <= 0 <= hi))
    return rows, trend


def benchmark(p, tau, n=N_SIM):
    """The additive model exactly true: beta ~ N(0, se^2 + tau^2) at each pair's se; tau refit
    leaving each character out; same bins. Robust sd per bin, all-in-band, Spearman."""
    rng = np.random.default_rng(SEED)
    s, col, off = p.s.to_numpy(), p.color.to_numpy(), p.n_treated_offers.to_numpy()
    bn = bins_of(off)
    sd, rho, whole = np.empty((n, N_BINS)), np.empty(n), np.empty(n)
    for i in range(n):
        b = np.hypot(s, tau) * rng.standard_normal(len(s))
        z = b / np.hypot(s, loco_tau(b, s, col)[0])
        sd[i] = [q.robust_sd(z[bn == k]) for k in range(1, N_BINS + 1)]
        rho[i], whole[i] = spearman(np.abs(z), off), q.robust_sd(z)
    inband = (sd >= BAND[0]) & (sd <= BAND[1])
    return dict(sd=sd, rho=rho, whole=whole, all_in=float(inband.all(axis=1).mean()),
                each_in=inband.mean(axis=0), n_in=inband.sum(axis=1))


def part1(pairs):
    t0 = time.time()
    tq, _ = q_tau()
    tr = rarity_tau()
    zrows, brows, trows, lrows, bench_rows = [], [], [], [], []
    for pt in PATCHES:
        p = pairs[pairs.patch == pt].reset_index(drop=True)
        z, taus, lr = variants(p, tq, tr)
        lrows += lr
        rar_ok = all(r["n_fit"] >= MIN_RARITY_REFIT for r in lr if r["scheme"] == "patch x rarity")
        out = p[["patch", "color", "fit_on", "pseudo_card", "rarity", "n_treated_offers"]].copy()
        out["beta_pp"], out["se_pp"], out["z"] = p.b, p.s, p.z
        out["bin_offers"] = bins_of(p.n_treated_offers.to_numpy())
        for k, v in taus.items():
            out[k] = v
        for k, v in z.items():
            out[f"z_{k}"] = v
        zrows.append(out)
        for subset, m in (("all pairs", np.ones(len(p), bool)),
                          ("all-offers pairs", (p.fit_on == "all offers").to_numpy())):
            for k, v in z.items():
                b_, t_ = bin_stats(p[m].reset_index(drop=True), v[m], pt, subset, k)
                t_["rarity_loco_allowed"] = rar_ok if k == "add_rarity_loco" else np.nan
                brows += b_
                trows.append(t_)
        bm = benchmark(p, tq[pt])
        obs = [r for r in brows if r["patch"] == pt and r["subset"] == "all pairs"
               and r["variant"] == "add_loco"]
        for k in range(N_BINS):
            lo, hi = q.pct(bm["sd"][:, k])
            bench_rows.append(dict(patch=pt, bin=k + 1, observed=obs[k]["robust_sd"],
                                   sim_median=float(np.median(bm["sd"][:, k])), sim_lo=lo, sim_hi=hi,
                                   observed_inside_sim=bool(lo <= obs[k]["robust_sd"] <= hi),
                                   sim_share_in_band=float(bm["each_in"][k])))
        tr_obs = next(t for t in trows if t["patch"] == pt and t["subset"] == "all pairs"
                      and t["variant"] == "add_loco")
        lo, hi = q.pct(bm["rho"])
        wlo, whi = q.pct(bm["whole"])
        bench_rows.append(dict(patch=pt, bin="all six in band", observed=float(tr_obs["n_bins_in_band"] == N_BINS),
                               sim_median=bm["all_in"], sim_share_in_band=bm["all_in"],
                               sim_share_at_most_observed_in_band=float(
                                   (bm["n_in"] <= tr_obs["n_bins_in_band"]).mean())))
        bench_rows.append(dict(patch=pt, bin="spearman abs z vs offers", observed=tr_obs["spearman"],
                               sim_median=float(np.median(bm["rho"])), sim_lo=lo, sim_hi=hi,
                               observed_inside_sim=bool(lo <= tr_obs["spearman"] <= hi)))
        bench_rows.append(dict(patch=pt, bin="whole patch robust sd", observed=tr_obs["robust_sd"],
                               sim_median=float(np.median(bm["whole"])), sim_lo=wlo, sim_hi=whi,
                               observed_inside_sim=bool(wlo <= tr_obs["robust_sd"] <= whi)))
        print(f"  {pt}: benchmark done, {time.time() - t0:.0f} s", flush=True)
    save("s_placebo_z", pd.concat(zrows, ignore_index=True))
    save("s_loco_tau", pd.DataFrame(lrows)[["patch", "scheme", "group", "left_out", "n_fit",
                                           "n_scored", "tau", "tau_all"]])
    B = save("s_bins", pd.DataFrame(brows))
    T = save("s_trend", pd.DataFrame(trows))
    K = save("s_benchmark", pd.DataFrame(bench_rows))
    pd.set_option("display.width", 250, "display.max_columns", 40, "display.max_rows", 400)
    print("\nleave-one-character-out tau (pp):")
    print(pd.read_csv(f"{OUT}/s_loco_tau.csv").round(3).to_string(index=False))
    for subset in ("all pairs", "all-offers pairs"):
        print(f"\n== bins, {subset}: robust sd [95%] by offers bin")
        b = B[B.subset == subset]
        b = b.assign(cell=[f"{r.robust_sd:.2f} [{r.lo:.2f}, {r.hi:.2f}]{'' if r.in_band else ' *'}"
                           for r in b.itertuples()])
        print(b.pivot_table(index=["patch", "bin", "n", "offers_median", "median_se_pp", "n_upgraded_fits"],
                            columns="variant", values="cell", aggfunc="first").to_string())
        print(T[T.subset == subset].drop(columns=["subset"]).round(3).to_string(index=False))
    print("\n== benchmark (additive model exactly true, all pairs, add_loco)")
    print(K.round(3).to_string(index=False))
    print(f"part 1: {time.time() - t0:.0f} s")


# ------------------------------------------------------------------------------------ part 2

def verdicts():
    """Part 1's outcome per patch for the primary additive z (all pairs, tau without the
    pair's character); None if part 1 hasn't run."""
    path = f"{OUT}/s_trend.csv"
    if not os.path.exists(path):
        return None
    t = pd.read_csv(path)
    t = t[(t.subset == "all pairs") & (t.variant == "add_loco")]
    return {r.patch: bool(r.passes) for r in t.itertuples()}


def part2(pairs):
    tq, _ = q_tau()
    tr = rarity_tau()
    p = pd.read_csv("results/pick_rate_did.csv")
    h = pd.read_parquet(f"{AN}/did_h3.parquet")
    h = h.reset_index() if "card_patch_id" not in h.columns else h
    if (len(p) != 43 or set(p.card_patch_id) != set(h.card_patch_id)):
        stop("pick_rate_did.csv and did_h3.parquet don't hold the same 43 tweaks")
    hh = h.set_index("card_patch_id")
    if (p.beta_h - p.card_patch_id.map(hh.beta)).abs().max() > 1e-6:
        stop("beta_h differs from did_h3.parquet's beta")
    orate = pd.read_parquet(f"{AN}/offer_rate.parquet")
    p["rarity"] = p.card_patch_id.map(orate.rarity)
    p["offers_h"] = p.card_patch_id.map(hh.n_treated_offers).astype(int)
    if p.rarity.isna().any():
        stop("a tweak card has no rarity in offer_rate.parquet")
    single = (p.mixed_direction != "yes") & (p.upgrade_only != "yes")
    p["toward_h"] = toward_change(p.beta_h, p.dose_x, single)
    f = p.patch.map(PLACEBO_FACTORS_H3)
    tau = p.patch.map(tq)
    tau_r = pd.Series([tr[(a, b)] for a, b in zip(p.patch, p.rarity)], index=p.index)
    p["beta_pp"], p["se_pp"] = 100 * p.beta_h, 100 * p.se_h
    p["factor"], p["tau"], p["tau_rarity"] = f, tau, tau_r
    p["se_b"] = p.se_pp * f
    p["se_c"] = np.hypot(p.se_pp, tau)
    p["se_d"] = np.hypot(p.se_pp, tau_r)
    # a and b exactly as the export computes them (probability units)
    p["clear_a"] = p.beta_h.abs() > 2 * p.se_h
    p["clear_b"] = p.beta_h.abs() > CAL_Z * p.se_h * f
    p["clear_c"] = p.beta_pp.abs() > CAL_Z * p.se_c
    p["clear_d"] = p.beta_pp.abs() > CAL_Z * p.se_d
    for k in "bcd":
        p[f"z_{k}"] = p.beta_pp / p[f"se_{k}"]
    # gate
    if not ((p.clear_a == (p.clearly_nonzero_h == "yes")).all()
            and (p.clear_b == (p.clearly_nonzero_h_cal == "yes")).all()):
        stop("a or b flags differ from clearly_nonzero_h / clearly_nonzero_h_cal")
    cc = pd.read_csv(f"{AN}/writeup/calibrated_counts.csv")
    cc = cc[cc.horizon == "weeks 0-3"].set_index(["spread", "patch"])
    for (rule, pt), want in EXISTING.items():
        g = (p.patch == pt) & p[f"clear_{rule}"]
        got = (int(g.sum()), int((g & (p.toward_h != "")).sum()), int((g & (p.toward_h == "yes")).sum()))
        r = cc.loc[({"a": "none", "b": "robust sd"}[rule], pt)]
        filed = (int(r.n_clearly_nonzero), int(r.n_clearly_nonzero_with_direction), int(r.n_toward))
        if got != want or got != filed:
            stop(f"rule {rule}, {pt}: got {got}, expected {want}, calibrated_counts.csv {filed}")
    print("gate: a and b reproduce the existing flags for all 43 tweaks and the counts "
          "(21/20/17, 8/7/5; 13/12/12, 2/2/2)")

    # e: pooled per patch, standardized by the additive error
    p["p_e"], p["p_e_plus1"], p["n_placebo_e"] = np.nan, np.nan, 0
    for pt in PATCHES:
        g = pairs[pairs.patch == pt]
        zp = (g.b.abs() / np.hypot(g.s, tq[pt])).to_numpy()
        m = p.patch == pt
        zt = (p.beta_pp[m].abs() / p.se_c[m]).to_numpy()
        k = (zp[None, :] >= zt[:, None]).sum(axis=1)
        p.loc[m, "p_e"], p.loc[m, "p_e_plus1"] = k / len(zp), (k + 1) / (len(zp) + 1)
        p.loc[m, "n_placebo_e"] = len(zp)
    p["clear_e"] = p.p_e < 0.05
    # f: the existing per-window comparison, weeks 0-3
    pvr = did.placebo_vs_real(pd.read_parquet(f"{AN}/did_h3.parquet"),
                              pd.read_parquet(q.PLACEBO)).set_index("card_patch_id")
    p["p_f"] = p.card_patch_id.map(pvr.empirical_p)
    p["n_placebo_f"] = p.card_patch_id.map(pvr.n_placebo).astype(int)
    p["clear_f"] = p.p_f < 0.05
    if p.p_f.isna().any():
        print(f"  note: {int(p.p_f.isna().sum())} tweak(s) without an empirical p under f")

    v = verdicts()
    rows = []
    for pt in PATCHES:
        for k, name in RULES.items():
            g = (p.patch == pt) & p[f"clear_{k}"]
            status = ("existing" if k in "ab" else "existing method, weeks 0-3" if k == "f" else
                      "part 1 not run" if v is None else
                      "sensitivity" if v[pt] else "descriptive only (part 1 failed)")
            rows.append(dict(patch=pt, rule=k, rule_name=name, n_tweaks=int((p.patch == pt).sum()),
                             n_clearly_nonzero=int(g.sum()),
                             n_clearly_nonzero_with_direction=int((g & (p.toward_h != "")).sum()),
                             n_toward=int((g & (p.toward_h == "yes")).sum()), status=status))
    C = save("s_counts", pd.DataFrame(rows))
    T = p[["card_patch_id", "card_id", "character", "patch", "rarity", "fit_on", "offers_h",
           "beta_pp", "se_pp", "factor", "tau", "tau_rarity", "se_b", "se_c", "se_d", "z_b", "z_c",
           "z_d", "p_e", "p_e_plus1", "n_placebo_e", "p_f", "n_placebo_f", "mixed_direction",
           "upgrade_only", "direction", "dose_x", "toward_h"]].copy()
    for k in RULES:
        T[f"clear_{k}"] = np.where(p[f"clear_{k}"], "yes", "no")
    T["b_vs_c"] = np.select([p.clear_b & ~p.clear_c, ~p.clear_b & p.clear_c],
                            ["loses under c", "gains under c"], "same")
    T["c_wider_than_b"] = np.where(p.se_c > p.se_b, "yes", "no")
    save("s_tweaks", T)
    sw = T[T.b_vs_c != "same"]
    save("s_switches", sw)
    med = (T.groupby(["patch", "b_vs_c"]).agg(n=("offers_h", "size"), median_offers=("offers_h", "median"),
                                             median_se_pp=("se_pp", "median"),
                                             n_c_wider=("c_wider_than_b", lambda s: int((s == "yes").sum())))
           .reset_index())
    save("s_switch_summary", med)
    pd.set_option("display.width", 250, "display.max_columns", 40, "display.max_rows", 400)
    print(C.to_string(index=False))
    print("\nper tweak:")
    print(T.drop(columns=["card_patch_id", "factor", "tau", "direction", "mixed_direction",
                          "upgrade_only", "n_placebo_e", "p_e_plus1", "dose_x", "fit_on"])
          .round(3).to_string(index=False))
    print("\nswitches b vs c:")
    print(sw[["card_id", "patch", "rarity", "offers_h", "beta_pp", "se_pp", "se_b", "se_c", "z_b",
              "z_c", "toward_h", "b_vs_c"]].round(3).to_string(index=False))
    print(med.round(3).to_string(index=False))
    print(f"crossover se (c wider than b below it): " + ", ".join(
        f"{pt} {tq[pt] / np.sqrt(PLACEBO_FACTORS_H3[pt] ** 2 - 1):.3f} pp" for pt in PATCHES))


# ------------------------------------------------------------------------------------ part 3

SPECS = ("primary", "triage", "primary, Debilitate at table dose")
COLS = ["slope1", "se1", "slope2", "se2", "diff", "se_diff", "z_diff", "tau2"]
MORE = ["Q", "df"]


def dose_row(L, se_lo, spec, setting, **extra):
    A = L.assign(se_lo=np.asarray(se_lo, float))
    r = sensitivity._row(sensitivity.slopes_by_patch(A))
    sep = {}
    for pt in PATCHES:
        g = A[A.patch == pt]
        b, cov, tau2, *_ = sensitivity.fit(g.beta_lo, g.se_lo, np.column_stack([np.ones(len(g)), g.x]))
        sep[pt] = (b[1], np.sqrt(cov[1, 1]), tau2)
    return dict(spec=spec, setting=setting, **extra, **{k: r[k] for k in ["n1", "n2"] + COLS + MORE},
                median_se_lo_first=float(A.se_lo[A.patch == "first"].median()),
                median_se_lo_second=float(A.se_lo[A.patch == "second"].median()),
                sep_slope1=sep["first"][0], sep_se1=sep["first"][1], sep_tau2_1=sep["first"][2],
                sep_slope2=sep["second"][0], sep_se2=sep["second"][1], sep_tau2_2=sep["second"][2],
                sep_z_diff=(sep["second"][0] - sep["first"][0]) / np.hypot(sep["second"][1], sep["first"][1]))


def part3():
    tq, tlo = q_tau()
    tr = rarity_tau()
    D = sensitivity.prepare(pd.read_parquet(f"{AN}/did_h3.parquet"))
    existing = sensitivity.placebo_factors(pd.read_csv(f"{AN}/placebo_diagnostics_summary.csv"))
    filed = pd.read_csv(f"{AN}/writeup/se_inflation.csv")
    orate = pd.read_parquet(f"{AN}/offer_rate.parquet")
    rows = []
    for spec in SPECS:
        L = sensitivity.dose_line(D, spec)
        label = f"{spec}, weeks 0-3 (did_h3)"
        mine = sensitivity.se_inflation_table(L, {k: existing[k] for k in ("none", "robust sd by patch")},
                                              label=label)
        for r in mine.itertuples():
            want = filed[(filed.label == label) & (filed.setting == r.setting)]
            if len(want) != 1 or any(abs(getattr(r, c) - float(want[c].iloc[0])) > 1e-6 for c in COLS):
                stop(f"se_inflation.csv not reproduced: {label}, {r.setting}")
        sec = (L.patch == "second").to_numpy()
        k = (L.beta / L.beta_lo).abs().to_numpy()             # p (1 - p), as sensitivity.prepare
        se_p = L.se_lo.to_numpy() * k                         # clustered se, probability units
        pt = np.where(sec, "second", "first")
        tau_pp = np.array([tq[x] for x in pt]) / 100
        tau_lo = np.array([tlo[x] for x in pt])
        rar = L.index.map(orate.rarity)
        tau_rar = np.array([tr[(a, b)] for a, b in zip(pt, rar)]) / 100
        fa = existing["robust sd by patch"]
        f3 = (PLACEBO_FACTORS_H3["first"], PLACEBO_FACTORS_H3["second"])
        rows += [
            dose_row(L, L.se_lo, spec, "none", existing="yes"),
            dose_row(L, L.se_lo * np.where(sec, fa[1], fa[0]), spec,
                     "multiplicative, all-weeks factors (existing calibrated row)",
                     existing="yes", par_first=fa[0], par_second=fa[1]),
            dose_row(L, L.se_lo * np.where(sec, f3[1], f3[0]), spec,
                     "multiplicative, weeks 0-3 factors", existing="no", par_first=f3[0], par_second=f3[1]),
            dose_row(L, np.hypot(se_p, tau_pp) / k, spec, "additive, tau per patch (pp) [primary]",
                     existing="no", par_first=tq["first"], par_second=tq["second"]),
            dose_row(L, np.hypot(L.se_lo, tau_lo), spec, "additive, tau per patch (log-odds)",
                     existing="no", par_first=tlo["first"], par_second=tlo["second"]),
            dose_row(L, np.hypot(se_p, tau_rar) / k, spec, "additive, tau per patch x rarity (pp)",
                     existing="no"),
        ]
    print("gate: se_inflation.csv's weeks 0-3 rows (none, robust sd by patch) reproduced for "
          f"{len(SPECS)} specs")
    R = save("s_dose", pd.DataFrame(rows))
    pd.set_option("display.width", 250, "display.max_columns", 40)
    print(R[["spec", "setting", "n1", "n2"] + COLS + MORE + ["sep_tau2_1", "sep_tau2_2", "median_se_lo_first", "median_se_lo_second",
                                                      "sep_z_diff"]].round(3).to_string(index=False))


# ----------------------------------------------------------------------------------- privacy

BAD_COL = re.compile(r"uploader|player|run_key|run_hash|screen_id|hash|steam|start_time|token|seed", re.I)
HEX = re.compile(r"[0-9a-f]{12,}", re.I)


def privacy():
    files = sorted(f for f in os.listdir(OUT) if f.startswith("s_") and f.endswith(".csv"))
    n_val, bad = 0, []
    for f in files:
        cards = {c: str for c in ("pseudo_card", "card_id", "card_patch_id")}   # NULL is a card
        d = pd.read_csv(f"{OUT}/{f}", converters=cards)
        check_output(f[:-4], d)
        text = [c for c in d.columns if not pd.api.types.is_numeric_dtype(d[c])]
        bad += [f"{f}: column {c}" for c in d.columns if BAD_COL.search(c)]
        for c in text:
            vals = d[c].dropna().astype(str).unique()
            n_val += len(vals)
            bad += [f"{f}.{c}: {v[:40]}" for v in vals
                    if HEX.search(v) or "|" in v or len(v) > 80]
        print(f"  {f}: {len(d)} rows, text columns: {text}")
    print(f"privacy: {len(files)} tables, {n_val} distinct text values scanned, "
          f"{'CLEAN' if not bad else 'PROBLEMS: ' + '; '.join(bad)}")
    if bad:
        raise SystemExit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", type=int, choices=(1, 2, 3))
    ap.add_argument("--privacy", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    todo = [a.part] if a.part else ([] if a.privacy else [1, 2, 3])
    pairs = load_pairs() if set(todo) & {1, 2} else None
    if 1 in todo:
        part1(pairs)
    if 2 in todo:
        part2(pairs)
    if 3 in todo:
        part3()
    if a.privacy or not a.part:
        privacy()
    print(f"total {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
