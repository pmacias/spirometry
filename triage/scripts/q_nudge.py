"""Section Q (EXPLORATORY): is the placebo excess a per-card nudge at each release?

Proposed after sections O and P were seen. Reads the final tables; changes no factor, number
or result. Rules, definitions and what each outcome means are in TRIAGE.md section Q, written
before this ran.

    python triage/scripts/q_nudge.py --check          # likelihood known-answer; the gate: the
                                                      # date-split loader returns saved z
    python triage/scripts/q_nudge.py --part 1         # one tau, two patches?
    python triage/scripts/q_nudge.py --part 2         # offer rate on the 43 windows
    python triage/scripts/q_nudge.py --part 3 --time  # 10 fits, runtime estimate, nothing saved
    python triage/scripts/q_nudge.py --part 3         # cut-point sweep, anchors, summaries
    python triage/scripts/q_nudge.py --part 3 --summary   # summaries from the saved fits only
    python triage/scripts/q_nudge.py --part 4         # POST HOC, added after reading parts 1-3

--interior-step 14 thins the interior cuts (the declared fallback if the sweep is over 2 h).

Run from the repository root. Output: triage/out_final/q_*.csv (TRIAGE_OUT overrides), keyed by
cut, window and card; no run IDs. runs.duckdb is opened read-only. Colors are derived (db.py).
Rarity (offer_rate_check reads it from reference/raw/cards.json) comes from card_changes.csv and
offer_rate.parquet where they have the card, else from offer tiers as in n_drift.py; with
TRIAGE_COLORS=reference the file's colors and rarities are used.
"""
import argparse
import os
import resource
import sys
import time
import zlib

import numpy as np
import pandas as pd
from scipy import optimize, sparse, stats

sys.path.insert(0, "triage/scripts")
import db  # noqa: E402
from spirometry import did  # noqa: E402

OUT = os.environ.get("TRIAGE_OUT", "triage/out_final")
PLACEBO = "data/analysis/placebo_h3.parquet"
MIN_OFFERS = 51                 # placebo_h3's min_offers
FACTORS = {"first": 4.10, "second": 2.67}
N_BOOT, N_SIM, BOOT_SEED, SEED, N_PSEUDO, N_RUN_BOOT = 2000, 5000, 20261111, 0, 20, 200
STABLE = ["v0.98.1", "v0.98.2", "v0.98.3", "v0.99.1", "v0.103.2", "v0.103.3", "v0.107.1"]
RARITY_BUILDS = ["v0.99.1", "v0.103.2", "v0.107.1"]            # as n_drift.derive_rarity
SNAPSHOT_END = pd.Timestamp("2026-10-04")       # first day without a full day of play
BLOCK = pd.Timedelta(days=21)
REAL = {"first": ("v0.99.1", "v0.103.2"), "second": ("v0.103.3", "v0.107.1")}
BANDS = ((1.2, "honest"), (1.5, "mixed"))


def robust_sd(z):
    z = np.asarray(z, float)
    z = z[np.isfinite(z)]
    return 1.4826 * np.median(np.abs(z - np.median(z))) if len(z) else np.nan


def z_stats(z):
    z = pd.Series(z, dtype=float).dropna()
    return dict(n=len(z), robust_sd_z=robust_sd(z), sd_z=z.std(),
                share_abs_z_gt2=(z.abs() > 2).mean(), mean_z=z.mean())


def cluster_boot(cluster, fn, n=N_BOOT, seed=BOOT_SEED):
    """fn(row index array) over n resamples of whole clusters. Returns an array of results."""
    codes = pd.factorize(pd.Series(cluster).to_numpy())[0]
    order = np.argsort(codes, kind="stable")
    bounds = np.searchsorted(codes[order], np.arange(codes.max() + 2))
    groups = [order[bounds[i]:bounds[i + 1]] for i in range(codes.max() + 1)]
    rng = np.random.default_rng(seed)
    return np.array([fn(np.concatenate([groups[i] for i in rng.integers(0, len(groups),
                                                                         len(groups))]))
                     for _ in range(n)])


def pct(x, axis=0):
    return np.nanpercentile(np.asarray(x, float), [2.5, 97.5], axis=axis)


# ------------------------------------------------------------------- likelihood (parts 1, 3)

def mle(b, s, g=None):
    """b_i ~ Normal(mu_g, s_i^2 + tau^2): tau and mu per group by maximum likelihood (mu is
    profiled out: the precision-weighted mean at each tau)."""
    b, s = np.asarray(b, float), np.asarray(s, float)
    g = np.zeros(len(b), int) if g is None else np.asarray(g)
    ng = int(g.max()) + 1

    def prof(tau):
        w = 1 / (s * s + tau * tau)
        mu = np.bincount(g, w * b, ng) / np.bincount(g, w, ng)
        r = b - mu[g]
        return 0.5 * (np.sum(w * r * r) - np.sum(np.log(w))), mu

    hi = 3 * b.std() + 1e-9
    res = optimize.minimize_scalar(lambda t: prof(t)[0], bounds=(0, hi), method="bounded",
                                   options=dict(xatol=1e-7 * max(hi, 1)))
    tau = float(res.x) if res.fun < prof(0.0)[0] else 0.0
    return tau, prof(tau)[1]


def sim_robust(se, tau, mu=0.0, n=N_SIM, seed=BOOT_SEED, taus=None):
    """Robust sd of z = beta / se over n draws of beta ~ Normal(mu, se^2 + tau^2); taus: one
    tau per draw instead (the bootstrap's)."""
    rng = np.random.default_rng(seed)
    se = np.asarray(se, float)
    out = np.empty(n)
    for i in range(n):
        t = tau if taus is None else taus[rng.integers(len(taus))]
        out[i] = robust_sd((mu + np.sqrt(se * se + t * t) * rng.standard_normal(len(se))) / se)
    return out


# ------------------------------------------------------------------------------------ part 1

def part1(pairs):
    d = pairs.copy()
    k = d.treated_rate_before * (1 - d.treated_rate_before)
    d["beta_pp"], d["se_pp"] = 100 * d.beta, 100 * d.se
    d["beta_lo"], d["se_lo"] = d.beta / k, d.se / k
    d["p"] = (d.patch == "second").astype(int)
    tau_rows, pred_rows = [], []
    for subset, dd in (("all pairs", d), ("all-offers pairs", d[d.fit_on == "all offers"])):
        dd = dd.reset_index(drop=True)
        for scale, unit in (("pp", "pp"), ("lo", "log-odds")):
            b, s, p = dd[f"beta_{scale}"].to_numpy(), dd[f"se_{scale}"].to_numpy(), dd.p.to_numpy()
            est, boots = {}, {}
            for name, m in (("first", p == 0), ("second", p == 1)):
                tau, mu = mle(b[m], s[m])
                bb, ss = b[m], s[m]
                bt = cluster_boot(dd.pseudo_card[m], lambda i: mle(bb[i], ss[i])[0])
                est[name], boots[name] = (tau, mu), bt
            tau, mu = mle(b, s, p)
            joint = cluster_boot(dd.pseudo_card, lambda i: (
                mle(b[i], s[i], p[i])[0], mle(b[i][p[i] == 0], s[i][p[i] == 0])[0],
                mle(b[i][p[i] == 1], s[i][p[i] == 1])[0]))
            est["pooled"], boots["pooled"] = (tau, mu), joint[:, 0]
            diff = joint[:, 1] - joint[:, 2]
            for name in ("first", "second", "pooled"):
                m = np.ones(len(dd), bool) if name == "pooled" else (dd.patch == name).to_numpy()
                t, mu_ = est[name]
                lo, hi = pct(boots[name])
                tau_rows.append(dict(
                    subset=subset, scale=unit, fit=name, n_pairs=int(m.sum()),
                    n_cards=dd.pseudo_card[m].nunique(), mu_first=mu_[0],
                    mu_second=mu_[-1] if name != "first" else np.nan, tau=t, tau_lo=lo,
                    tau_hi=hi, sigma_b=t / np.sqrt(2), median_se=float(np.median(s[m])),
                    mean_se2=float((s[m] ** 2).mean())))
                if name == "first":
                    tau_rows[-1]["mu_second"] = np.nan
                if name == "second":
                    tau_rows[-1]["mu_first"], tau_rows[-1]["mu_second"] = np.nan, mu_[0]
            lo, hi = pct(diff)
            tau_rows.append(dict(subset=subset, scale=unit, fit="first - second",
                                 n_pairs=len(dd), n_cards=dd.pseudo_card.nunique(),
                                 tau=est["first"][0] - est["second"][0], tau_lo=lo, tau_hi=hi))
            for i, name in enumerate(("first", "second")):
                m = p == i
                sim = sim_robust(s[m], tau, mu[i])
                simb = sim_robust(s[m], tau, mu[i], taus=boots["pooled"])
                own = sim_robust(s[m], est[name][0], est[name][1][0])
                obs = robust_sd(dd.z[m])
                lo, hi = pct(sim)
                pred_rows.append(dict(
                    subset=subset, scale=unit, patch=name, n_pairs=int(m.sum()),
                    observed_robust_sd=obs, pooled_tau=tau, predicted_median=np.median(sim),
                    predicted_lo=lo, predicted_hi=hi, inside=bool(lo <= obs <= hi),
                    predicted_lo_tau_boot=pct(simb)[0], predicted_hi_tau_boot=pct(simb)[1],
                    own_tau=est[name][0], own_tau_predicted_median=np.median(own),
                    own_tau_lo=pct(own)[0], own_tau_hi=pct(own)[1]))
    keep = ["patch", "color", "before_builds", "after_builds", "fit_on", "pseudo_card", "z",
            "beta_pp", "se_pp", "beta_lo", "se_lo", "treated_rate_before", "n_tweaks_sharing"]
    return pd.DataFrame(tau_rows), pd.DataFrame(pred_rows), d[keep]


# ----------------------------------------------------------------------- rarity, fake windows

FAKE_ROWS, FAKE_COLORS, RARITY = {}, {}, {}


def derive_rarity(con):
    """card -> rarity: card_changes.csv and offer_rate.parquet where they have the card, else
    the offer tier (n_drift.derive_rarity: offers relative to the character's most offered
    card on three builds; Rare about 0.17, Uncommon 0.36, Common 1.0)."""
    n = con.execute("""SELECT character, card_id, count(*) AS n FROM offers_with_version
                       WHERE list_contains(?, build_id) AND ascension IS NOT NULL
                       GROUP BY ALL""", [RARITY_BUILDS]).df()
    n["color"] = n.character.map(db.CHARS)
    n = n[(n.card_id.map(did.card_colors()) == n.color).to_numpy()]
    r = n.n / n.groupby("color").n.transform("max")
    out = dict(zip(n.card_id, np.select([r >= 0.6, r >= 0.25], ["Common", "Uncommon"], "Rare")))
    a = pd.read_parquet("data/analysis/offer_rate.parquet")[["card", "rarity"]]
    b = did._csv("reference/card_changes.csv")[["card_id", "rarity"]]
    b = b[b.rarity != ""].rename(columns=dict(card_id="card"))
    known = pd.concat([a, b]).drop_duplicates("card")
    agree = sum(out.get(c) == r_ for c, r_ in zip(known.card, known.rarity) if c in out)
    both = sum(c in out for c in known.card)
    out.update(dict(zip(known.card, known.rarity)))
    return out, agree, both


def patch_did(con):
    """Fake window rows for did's model code (as n_drift.py), and rarities without
    reference/raw/."""
    window, colors = did.window, did.card_colors
    did.window = lambda cpid, ref=did.REF: (FAKE_ROWS[cpid] if cpid in FAKE_ROWS
                                            else window(cpid, ref))
    did.card_colors = lambda ref=did.REF: {**colors(ref), **FAKE_COLORS}
    if os.environ.get("TRIAGE_COLORS") != "reference":
        rar, agree, both = derive_rarity(con)
        RARITY.update(rar)
        did.card_rarities = lambda ref=did.REF: dict(RARITY)
        print(f"rarity: {len(rar)} cards; offer tier agrees with the rarity on file for "
              f"{agree} of {both}", flush=True)


def fake_host(color, key, drop):
    card = f"__FAKE_{color}"
    FAKE_ROWS[key] = dict(card_id=card, control_exclusions=" ".join(sorted(drop)),
                          control_behavior_flags="", before_builds="", after_builds="")
    FAKE_COLORS[card] = color
    return key


# ------------------------------------------------------------------------------------ part 2

def boot_offer_se(df, orc, n=N_RUN_BOOT, seed=BOOT_SEED):
    """Run-clustered bootstrap SE of each control row's deviation (log share ratio minus the
    median of its rarity's controls, with offer_rate_check's fallback to all controls). Runs
    are resampled with replacement within each block; every draw recomputes all of it."""
    c = orc[~orc.treated].reset_index(drop=True)
    cards = pd.Index(c.card_id)
    counts = {}
    rng = np.random.default_rng(seed)
    for blk in ("before", "after"):
        d = df[df.block == blk]
        runs = pd.factorize(d.run_key.astype(object))[0]
        nr = runs.max() + 1
        col = cards.get_indexer(d.card_id.astype(object))
        ok = col >= 0
        m = sparse.csr_matrix((np.ones(ok.sum()), (runs[ok], col[ok])), shape=(nr, len(cards)))
        tot = np.bincount(runs, minlength=nr).astype(float)
        w = rng.multinomial(nr, np.full(nr, 1 / nr), size=n).astype(float)        # n x runs
        counts[blk] = ((m.T @ w.T).T, w @ tot)
    with np.errstate(divide="ignore", invalid="ignore"):
        lr = (np.log(counts["after"][0] / counts["after"][1][:, None])
              - np.log(counts["before"][0] / counts["before"][1][:, None]))
    lr[~np.isfinite(lr)] = np.nan
    dev = np.full_like(lr, np.nan)
    own = (c.rarity_note == "").to_numpy()
    for r in c.rarity[own].unique():
        m = own & (c.rarity == r).to_numpy()
        dev[:, m] = lr[:, m] - np.nanmedian(lr[:, m], axis=1, keepdims=True)
    if (~own).any():
        dev[:, ~own] = lr[:, ~own] - np.nanmedian(lr, axis=1, keepdims=True)
    return pd.Series(np.nanstd(dev, axis=0, ddof=1), index=cards)


def offer_rows(df, key, boot=True):
    """offer_rate_check's control rows for one window or cut, with the bootstrap z."""
    orc = did.offer_rate_check(df, key)
    c = orc[~orc.treated].copy()
    if boot:
        se = boot_offer_se(df, orc)
        dev = c.log_share_ratio - c.controls_median_rarity
        c["se_boot"] = c.card_id.map(se).to_numpy()
        c["z_boot_rarity"] = dev / c.se_boot
    keep = ["card_id", "rarity", "offers_before", "offers_after", "log_share_ratio",
            "controls_median_rarity", "n_controls_rarity", "rarity_note", "z_binom",
            "z_binom_rarity"] + (["se_boot", "z_boot_rarity"] if boot else [])
    return c[keep]


def pool_changed(color, stable_build):
    cc = did._csv("reference/card_changes.csv")
    cc = cc[(cc.color == color) & (cc.stable_build == stable_build)]
    hit = cc[cc.change_kind.str.contains("added|removed|rarity_change")]
    return " ".join(sorted(hit.card_id.unique()))


def part2(con):
    ts = did._csv("reference/tweak_sizes.csv")
    ts = ts[ts.solo_estimable == "yes"]
    patch = did._patch_labels(ts)
    rows, t_boot = [], 0.0
    for (color, before, after), g in ts.groupby(["color", "before_builds", "after_builds"],
                                                sort=False):
        t0 = time.time()
        df = did.load_block_data(con, color, before, after)
        df = df[(df.block != "after") | (df.week <= 3)]
        for i, t in enumerate(g.to_dict("records")):
            t1 = time.time()
            r = offer_rows(df, t["card_patch_id"], boot=i == 0)   # control sets are the same
            t_boot += (time.time() - t1) if i == 0 else 0.0       # within a window (checked
            rows.append(r.assign(card_patch_id=t["card_patch_id"], color=color,   # below)
                                 before_builds=before, after_builds=after,
                                 patch=patch[t["stable_build"]],
                                 pool_changes=pool_changed(color, t["stable_build"])))
        print(f"  {color} {before} -> {after}: {len(g)} tweaks, {time.time() - t0:.0f} s",
              flush=True)
    r = pd.concat(rows, ignore_index=True)
    key = ["color", "before_builds", "after_builds", "card_id"]
    num = ["offers_before", "offers_after", "log_share_ratio", "z_binom", "z_binom_rarity",
           "se_boot", "z_boot_rarity"]
    g = r.groupby(key, sort=False)
    spread = g.z_binom_rarity.agg(lambda x: x.max() - x.min()).max()
    out = g.first()
    out[num] = g[num].mean()
    out["n_tweaks_sharing"] = g.size()
    out = out.reset_index().drop(columns="card_patch_id")
    n_all = len(out)
    out = out[np.isfinite(out.z_binom_rarity)].reset_index(drop=True)
    out["window"] = out.color + " " + out.before_builds + " -> " + out.after_builds
    out["pool_changed"] = out.pool_changes != ""
    pick = np.random.default_rng(SEED).choice(len(out), 100, replace=False)
    out["fixed_100"] = np.isin(np.arange(len(out)), pick)
    print(f"  {n_all} (window, card) rows, {n_all - len(out)} without a finite z dropped; "
          f"largest spread of z over tweaks sharing a row {spread:.2g}; bootstrap "
          f"{t_boot:.0f} s", flush=True)
    return out


def offer_summary(o):
    rows = []
    views = [("all", "all", o)] + [("patch", p, g) for p, g in o.groupby("patch")]
    views += [("patch x rarity", f"{p} {r}", g) for (p, r), g in o.groupby(["patch", "rarity"])]
    views += [("window", w, g) for w, g in o.groupby("window", sort=False)]
    views += [("patch x pool changed", f"{p} {'changed' if c else 'unchanged'}", g)
              for (p, c), g in o.groupby(["patch", "pool_changed"])]
    views += [("fixed 100 rows", "all", o[o.fixed_100])]
    for split, level, g in views:
        row = dict(split=split, level=level)
        for stat in ("z_binom_rarity", "z_binom", "z_boot_rarity"):
            st = z_stats(g[stat])
            row.update({f"{stat}.{k}": v for k, v in st.items()})
        row["median_se_boot_over_binom"] = float(np.nanmedian(
            g.se_boot / ((g.log_share_ratio - g.controls_median_rarity) / g.z_binom_rarity)))
        rows.append(row)
    return pd.DataFrame(rows)


def band(x):
    return "honest (<= 1.2)" if x <= 1.2 else "inflated (>= 1.5)" if x >= 1.5 else "mixed"


# ------------------------------------------------------------------------------------ part 3

def release(build):
    return did.release_date(build)


def cut_list(step=7):
    """Boundaries between consecutive stable builds, and interior cuts of each stable build
    while it was the current stable."""
    rows = []
    for old, new in zip(STABLE, STABLE[1:]):
        changed, flagged = did.window_changes(old, new)
        rows.append(dict(cut_id=f"{old} -> {new}", kind="boundary", older=old, newer=new,
                         cut=release(new), weeks_since_release=0.0,
                         older_build_age_days=(release(new) - release(old)).days,
                         n_changed_all_colors=len(changed)))
    for i, b in enumerate(STABLE):
        end = release(STABLE[i + 1]) if i + 1 < len(STABLE) else SNAPSHOT_END
        cut = release(b) + BLOCK
        while cut <= end - BLOCK:
            rows.append(dict(cut_id=f"{b} @ {cut.date()}", kind="interior", older=b, newer=b,
                             cut=cut, weeks_since_release=(cut - release(b)).days / 7,
                             older_build_age_days=(cut - release(b)).days,
                             n_changed_all_colors=0))
            cut += pd.Timedelta(days=step)
    return pd.DataFrame(rows)


def make_df(raw, older, newer, cut, main=False):
    """The date-split loader. raw: build -> did._load_offers frame. 3 + 3 design: before =
    `older`'s offers started in the 21 days before `cut`, after = `newer`'s in the 21 days
    from it (older == newer: one build split by start_time). main=True: the main design's
    build split (all of `older`; `newer` through week 3), for the gate."""
    b, a = raw[older], raw[newer]
    if main:
        wk = np.floor((a.start_time - cut).dt.total_seconds() / did.WEEK)
        a = a[wk <= 3]
    else:
        b = b[(b.start_time >= cut - BLOCK) & (b.start_time < cut)]
        a = a[(a.start_time >= cut) & (a.start_time < cut + BLOCK)]
    df = pd.concat([b.assign(block="before"), a.assign(block="after")], ignore_index=True)
    df["week"] = np.floor((df.start_time - cut).dt.total_seconds() / did.WEEK).astype("int16")
    return did._finish(df)


def fit(df, key, pseudo, **kw):
    """placebo_fit's model: did._subset's data, did._fixed_effects, did._feols."""
    d, _ = did._subset(df, key, pseudo=pseudo, **kw)
    f = did._feols("picked ~ treat_post | " + " + ".join(did._fixed_effects(d, None, False)), d)
    t = d[d.is_treated]
    r = did._rates(d)
    return dict(beta=float(f.coef()["treat_post"]), se=float(f.se()["treat_post"]),
                n_offers=int(f._N), n_runs=int(d.run_key.nunique()),
                pseudo_offers_before=int((~t.after).sum()), pseudo_offers_after=int(t.after.sum()),
                rate_before=r["treated_rate_before"], rate_after=r["treated_rate_after"],
                n_control_cards=int(d.card_id[~d.is_treated].nunique()))


def card_order(color):
    cards = sorted(c for c, col in did.card_colors().items()
                   if col == color and not c.startswith("__FAKE_"))
    rng = np.random.default_rng([SEED, zlib.crc32(color.encode())])
    return list(rng.permutation(cards))


def eligible(df, key, order, upgraded=None):
    d = df[df.ascension.notna()]
    if upgraded is not None:
        d = d[d.upgraded == upgraded]
    n = d.groupby(["card_id", "block"], observed=True).size().unstack("block")
    n = n.reindex(columns=["before", "after"]).fillna(0)
    ok = set(n.index[(n >= MIN_OFFERS).all(axis=1)]) & set(did.control_cards(key, df=df))
    return [c for c in order if c in ok]


def run_cut(raw, color, cut, order, entering, n_fits=N_PSEUDO):
    df = make_df(raw, cut.older, cut.newer, cut.cut)
    changed = did.window_changes(cut.older, cut.newer)[0] if cut.kind == "boundary" else set()
    key = fake_host(color, f"Q:{color}:{cut.cut_id}", changed)
    base = dict(cut_id=cut.cut_id, kind=cut.kind, color=color)
    if df.empty or df.block.nunique() < 2:
        return [dict(base, error="no offers in a block")], None, {}
    el = eligible(df, key, order)
    fits = []
    for c in el[:n_fits]:
        row = dict(base, pseudo_card=c, n_eligible=len(el), error="",
                   changed_entering_build=c in entering)
        try:
            row.update(fit(df, key, c))
            row["z"] = row["beta"] / row["se"]
        except Exception as e:
            row["error"] = f"{type(e).__name__}: {e}"
        fits.append(row)
    off = offer_rows(df, key).assign(**base)
    nxt = STABLE.index(cut.newer) + 1
    late = (df.start_time[df.block == "after"] >= release(STABLE[nxt])).mean() \
        if cut.kind == "boundary" and nxt < len(STABLE) else 0.0
    info = dict(base, n_offers_before=int((df.block == "before").sum()),
                n_offers_after=int((df.block == "after").sum()),
                n_runs=int(df.run_key.nunique()), n_changed_own_color=len(
                    [c for c in changed if did.card_colors().get(c) == color]),
                n_control_cards=len(did.control_cards(key, df=df)), n_eligible=len(el),
                share_after_on_superseded_build=float(late),
                before_first_day=str(df.start_time[df.block == "before"].min().date()),
                after_last_day=str(df.start_time[df.block == "after"].max().date()))
    return fits, off, info


def gate(con, raw_placebo):
    """The date-split loader and the fake window, given a real boundary's build split, return
    the saved placebo z."""
    ok = raw_placebo[(raw_placebo.error.fillna("") == "") & raw_placebo.z.notna()]
    picks = [ok[(ok.patch == "first") & (ok.color == "silent")].iloc[0],
             ok[(ok.patch == "second") & (ok.color == "ironclad")].iloc[0],
             ok[(ok.fit_on == "upgraded offers")].iloc[0]]
    worst = 0.0
    for r in picks:
        w = did.window(r.card_patch_id)
        old, new = w["before_builds"], w["after_builds"]
        raw = {b: did._load_offers(con, r.color, [b]) for b in (old, new)}
        df = make_df(raw, old, new, release(new), main=True)
        key = fake_host(r.color, f"GATE:{r.card_patch_id}", did.window_changes(old, new)[0])
        up = True if r.fit_on == "upgraded offers" else None
        for name, k in (("real window row", r.card_patch_id), ("fake window", key)):
            f = fit(df, k, r.pseudo_card, upgraded=up)
            dz = abs(f["beta"] / f["se"] - r.z)
            worst = max(worst, dz)
            print(f"  {r.card_patch_id} {r.pseudo_card} ({r.fit_on}), {name}: saved z "
                  f"{r.z:+.5f}, date-split path {f['beta'] / f['se']:+.5f}, |dz| {dz:.1e}",
                  flush=True)
    if worst > 1e-4:
        raise SystemExit(f"gate failed: |dz| {worst:.1e} > 1e-4")
    print(f"gate passed: largest |dz| {worst:.1e}")


def check_mle():
    rng = np.random.default_rng(1)
    s = rng.uniform(0.5, 1.5, 4000)
    g = (np.arange(4000) % 2)
    b = np.where(g == 0, 1.0, -2.0) + rng.standard_normal(4000) * np.sqrt(s * s + 2.0 ** 2)
    tau, mu = mle(b, s, g)
    assert abs(tau - 2.0) < 0.1 and abs(mu[0] - 1) < 0.15 and abs(mu[1] + 2) < 0.15, (tau, mu)
    assert mle(rng.standard_normal(4000) * s * 0.8, s)[0] == 0.0
    sim = sim_robust(np.ones(2000), np.sqrt(3.0), n=200)
    assert abs(np.median(sim) - 2.0) < 0.05, np.median(sim)
    print("mle and sim_robust: ok")


def time_fits(con, cuts):
    color = "silent"
    c = cuts[(cuts.kind == "interior") & (cuts.older == "v0.107.1")].iloc[0]
    t0 = time.time()
    raw = {"v0.107.1": did._load_offers(con, color, ["v0.107.1"])}
    t_load = time.time() - t0
    t0 = time.time()
    df = make_df(raw, c.older, c.newer, c.cut)
    key = fake_host(color, f"TIME:{color}", set())
    el = eligible(df, key, card_order(color))
    t_prep = time.time() - t0
    t0 = time.time()
    for card in el[:10]:
        fit(df, key, card)
    t_fit = (time.time() - t0) / 10
    t0 = time.time()
    offer_rows(df, key)
    t_off = time.time() - t0
    n_cuts = len(cuts)
    n_fits = n_cuts * 5 * N_PSEUDO + 463
    est = n_fits * t_fit + 5 * 7 * t_load / 2 + n_cuts * 5 * (t_prep + t_off)
    print(f"timing ({color}, {c.cut_id}, {len(df):,} offers): load v0.107.1 {t_load:.0f} s; "
          f"blocks and eligibility {t_prep:.1f} s; {t_fit:.2f} s per fit; offer-rate rows with "
          f"bootstrap {t_off:.1f} s")
    print(f"estimate: {n_cuts} cuts x 5 characters x up to {N_PSEUDO} fits + 463 anchor fits = "
          f"up to {n_fits} fits: about {est / 60:.0f} min")


def sweep(con, cuts, pairs):
    fits, offers, infos, anchors = [], [], [], []
    entering = {b: did.window_changes(STABLE[i - 1], b)[0] if i else set()
                for i, b in enumerate(STABLE)}
    for color in did.CHARACTER_COLORS:
        t0 = time.time()
        raw = {b: did._load_offers(con, color, [b]) for b in STABLE}
        order = card_order(color)
        print(f"{color}: loaded {sum(len(v) for v in raw.values()):,} offers, "
              f"{time.time() - t0:.0f} s", flush=True)
        for c in cuts.itertuples():
            t1 = time.time()
            f, o, info = run_cut(raw, color, c, order, entering[c.older])
            fits += f
            if o is not None:
                offers.append(o)
                infos.append(info)
            print(f"  {c.cut_id}: {len(f)} fits, {time.time() - t1:.0f} s", flush=True)
        for patch, (old, new) in REAL.items():           # anchors: the saved pairs, 3 + 3
            g = pairs[(pairs.patch == patch) & (pairs.color == color)]
            if g.empty:
                continue
            t1 = time.time()
            df = make_df(raw, old, new, release(new))
            for r in g.itertuples():
                up = True if r.fit_on == "upgraded offers" else None
                row = dict(patch=patch, color=color, fit_on=r.fit_on, pseudo_card=r.pseudo_card,
                           card_patch_id=r.card_patch_id, z_saved=r.z, beta_saved=r.beta,
                           se_saved=r.se, error="")
                try:
                    row.update(fit(df, r.card_patch_id, r.pseudo_card, upgraded=up))
                    row["z"] = row["beta"] / row["se"]
                except Exception as e:
                    row["error"] = f"{type(e).__name__}: {e}"
                anchors.append(row)
            print(f"  anchor {patch}: {len(g)} fits, {time.time() - t1:.0f} s", flush=True)
        del raw
    return (pd.DataFrame(fits), pd.concat(offers, ignore_index=True), pd.DataFrame(infos),
            pd.DataFrame(anchors))


def spread_row(g, label, cluster=True, **extra):
    """Robust sd of z with a card-resampling interval, plus the pp-scale quantities."""
    g = g.reset_index(drop=True)
    z, b, s = g.z.to_numpy(), 100 * g.beta.to_numpy(), 100 * g.se.to_numpy()
    cut = pd.factorize(g.cut_id)[0] if "cut_id" in g else np.zeros(len(g), int)
    boots = cluster_boot(g.pseudo_card if cluster else np.arange(len(g)),
                         lambda i: robust_sd(z[i]))
    tau, _ = mle(b, s, cut)
    tb = cluster_boot(g.pseudo_card, lambda i: mle(b[i], s[i], pd.factorize(cut[i])[0])[0],
                      n=500)
    dev = b - pd.Series(b).groupby(cut).transform("mean").to_numpy()
    n_g = cut.max() + 1
    return dict(label=label, **extra, **z_stats(z), robust_sd_lo=pct(boots)[0],
                robust_sd_hi=pct(boots)[1], n_cards=g.pseudo_card.nunique(),
                median_se_pp=np.median(s), sd_beta_pp=np.sqrt((dev ** 2).sum() / (len(g) - n_g)),
                excess_var_pp2=(dev ** 2).sum() / (len(g) - n_g) - (s ** 2).mean(),
                excess_var_robust_pp2=robust_sd(dev) ** 2 - np.median(s) ** 2,
                tau_pp=tau, tau_lo=pct(tb)[0], tau_hi=pct(tb)[1])


def summaries(cuts, fits, offers, infos, anchors, pairs):
    f = fits[(fits.error.fillna("") == "") & np.isfinite(fits.z)].copy()
    f = f.merge(cuts[["cut_id", "older", "newer", "cut", "weeks_since_release",
                      "older_build_age_days"]], on="cut_id")
    f["changed_entering_build"] = f.changed_entering_build.astype(bool)
    info = infos.groupby("cut_id", sort=False).agg(
        n_offers_before=("n_offers_before", "sum"), n_offers_after=("n_offers_after", "sum"),
        n_changed_own_color=("n_changed_own_color", "sum"),
        share_after_on_superseded_build=("share_after_on_superseded_build", "mean"),
        before_first_day=("before_first_day", "min"), after_last_day=("after_last_day", "max"))
    # per cut
    per = []
    for c in cuts.itertuples():
        g = f[f.cut_id == c.cut_id]
        o = offers[offers.cut_id == c.cut_id]
        if len(g) < 5:
            per.append(dict(label=c.cut_id, kind=c.kind, cut=str(c.cut.date()), n=len(g)))
            continue
        row = spread_row(g, c.cut_id, kind=c.kind, cut=str(c.cut.date()),
                         weeks_since_release=c.weeks_since_release,
                         older_build_age_days=c.older_build_age_days)
        row.update(info.loc[c.cut_id].to_dict() if c.cut_id in info.index else {})
        for stat in ("z_binom_rarity", "z_boot_rarity"):
            st = z_stats(o[stat])
            row.update({f"offer.{stat}.{k}": st[k] for k in ("n", "robust_sd_z", "sd_z",
                                                              "share_abs_z_gt2")})
        per.append(row)
    per = pd.DataFrame(per)

    # pooled
    inter, bound = f[f.kind == "interior"], f[f.kind == "boundary"]
    late3 = bound[bound.newer.isin(["v0.103.2", "v0.103.3", "v0.107.1"])]
    zero = per[(per.kind == "boundary") & (per.n_changed_own_color == 0)].label
    v107 = inter[inter.older == "v0.107.1"]
    views = [
        ("interior cuts, pooled [rule]", inter),
        ("interior, cards changed entering the build left out", inter[~inter.changed_entering_build]),
        ("interior, v0.107.1 only", v107),
        ("interior, v0.107.1 weeks 3 and 9 (no shared data)",
         v107[v107.weeks_since_release.isin([3.0, 9.0])]),
        ("interior, v0.107.1 weeks 3-7", v107[v107.weeks_since_release <= 7]),
        ("interior, v0.107.1 weeks 8-12", v107[v107.weeks_since_release >= 8]),
        ("real boundaries, pooled [rule]", bound),
        ("boundaries, the three later ones", late3),
        ("boundaries, v0.98.x (short before blocks)", bound[~bound.cut_id.isin(late3.cut_id)]),
        ("boundaries with zero card changes", bound[bound.cut_id.isin(zero)]),
        ("boundaries with card changes", bound[~bound.cut_id.isin(zero)]),
        ("boundary v0.103.2 -> v0.103.3 (zero changes, full blocks)",
         bound[bound.cut_id == "v0.103.2 -> v0.103.3"]),
    ]
    pooled = pd.DataFrame([spread_row(g, name) for name, g in views if len(g) >= 5])
    for name, o in (("interior cuts, pooled [rule]", offers[offers.kind == "interior"]),
                    ("real boundaries, pooled [rule]", offers[offers.kind == "boundary"])):
        for stat in ("z_binom_rarity", "z_boot_rarity"):
            st = z_stats(o[stat])
            for k in ("n", "robust_sd_z", "sd_z", "share_abs_z_gt2"):
                pooled.loc[pooled.label == name, f"offer.{stat}.{k}"] = st[k]

    # benchmark: interior z if the interior cuts carried the boundaries' tau
    bench = []
    s_in = 100 * inter.se.to_numpy()
    for name in ("real boundaries, pooled [rule]", "boundaries, the three later ones",
                 "boundary v0.103.2 -> v0.103.3 (zero changes, full blocks)"):
        r = pooled[pooled.label == name]
        if r.empty:
            continue
        for which, tau in (("point", r.tau_pp.iloc[0]), ("lower end", r.tau_lo.iloc[0])):
            sim = sim_robust(s_in, tau)
            bench.append(dict(tau_from=name, tau=which, tau_pp=tau,
                              interior_observed_robust_sd=robust_sd(inter.z),
                              predicted_median=np.median(sim), predicted_lo=pct(sim)[0],
                              predicted_hi=pct(sim)[1],
                              interior_median_se_pp=np.median(s_in)))
    bench = pd.DataFrame(bench)

    # settling
    cid = pd.factorize(inter.cut_id)[0]
    wk = inter.groupby(cid).weeks_since_release.first().to_numpy()
    z, b, s = inter.z.to_numpy(), 100 * inter.beta.to_numpy(), 100 * inter.se.to_numpy()

    def rho(i, what, ks):
        v = [robust_sd(z[i][cid[i] == k]) if what == "z" else
             mle(b[i][cid[i] == k], s[i][cid[i] == k])[0] if (cid[i] == k).sum() > 1 else np.nan
             for k in ks]
        ok = np.isfinite(v)
        return stats.spearmanr(wk[ks][ok], np.asarray(v)[ok]).statistic

    settle = []
    for what, n in (("z", N_BOOT), ("tau", 500)):
        for scope, m in (("all interior cuts", np.ones(len(inter), bool)),
                         ("v0.107.1 only", (inter.older == "v0.107.1").to_numpy())):
            idx = np.flatnonzero(m)
            ks = np.unique(cid[idx])
            bt = cluster_boot(inter.pseudo_card.to_numpy()[idx],
                              lambda i: rho(idx[i], what, ks), n=n)
            lo, hi = pct(bt)
            settle.append(dict(statistic="robust sd of z" if what == "z" else "tau (pp)",
                               scope=scope, n_cuts=len(ks),
                               spearman=rho(idx, what, ks), lo=lo, hi=hi))
    settle = pd.DataFrame(settle)

    # anchors
    a = anchors[(anchors.error.fillna("") == "") & np.isfinite(anchors.z)].copy()
    anc = []
    for patch in FACTORS:
        for scope, g in (("all saved pairs", a[a.patch == patch]),
                         ("all-offers pairs", a[(a.patch == patch) & (a.fit_on == "all offers")])):
            g = g.reset_index(drop=True)
            zs, zn = g.z_saved.to_numpy(), g.z.to_numpy()
            bt = cluster_boot(g.pseudo_card, lambda i: (robust_sd(zn[i]), robust_sd(zs[i]),
                                                        robust_sd(zn[i]) / robust_sd(zs[i])))
            tau, _ = mle(100 * g.beta, 100 * g.se)
            tau0, _ = mle(100 * g.beta_saved, 100 * g.se_saved)
            anc.append(dict(
                patch=patch, scope=scope, n_pairs=len(g), n_failed=int(
                    ((anchors.patch == patch) & ~anchors.index.isin(a.index)).sum()),
                factor=FACTORS[patch], saved_robust_sd=robust_sd(zs), robust_sd_3plus3=robust_sd(zn),
                lo=pct(bt[:, 0])[0], hi=pct(bt[:, 0])[1], ratio=robust_sd(zn) / robust_sd(zs),
                ratio_lo=pct(bt[:, 2])[0], ratio_hi=pct(bt[:, 2])[1], sd_saved=zs.std(ddof=1),
                sd_3plus3=zn.std(ddof=1), share_gt2_3plus3=(np.abs(zn) > 2).mean(),
                median_se_saved_pp=100 * g.se_saved.median(), median_se_3plus3_pp=100 * g.se.median(),
                tau_saved_pp=tau0, tau_3plus3_pp=tau, corr_beta=np.corrcoef(g.beta, g.beta_saved)[0, 1]))
    anc = pd.DataFrame(anc)

    # adjacent boundaries
    adj = []
    bl = cuts[cuts.kind == "boundary"]
    for c1, c2 in zip(bl.itertuples(), bl.iloc[1:].itertuples()):
        g1, g2 = f[f.cut_id == c1.cut_id], f[f.cut_id == c2.cut_id]
        m = g1.merge(g2, on=["color", "pseudo_card"], suffixes=("_1", "_2"))
        if len(m) < 10:
            adj.append(dict(first=c1.cut_id, second=c2.cut_id, n_cards=len(m)))
            continue
        b1, b2 = 100 * m.beta_1.to_numpy(), 100 * m.beta_2.to_numpy()
        d1 = b1 - m.groupby("color").beta_1.transform("mean").to_numpy() * 100
        d2 = b2 - m.groupby("color").beta_2.transform("mean").to_numpy() * 100
        bt = cluster_boot(np.arange(len(m)), lambda i: np.corrcoef(d1[i], d2[i])[0, 1])
        # the middle build's blocks: after block of the first cut, before block of the second
        pm = (m.rate_after_1 + m.rate_before_2) / 2
        shared = 1e4 * pm * (1 - pm) / np.maximum(m.pseudo_offers_after_1, m.pseudo_offers_before_2)
        same_days = (c2.cut - c1.cut) <= BLOCK       # the two blocks are the same offers
        t1, _ = mle(b1, 100 * m.se_1, pd.factorize(m.color)[0])
        t2, _ = mle(b2, 100 * m.se_2, pd.factorize(m.color)[0])
        den = np.sqrt(d1.var(ddof=1) * d2.var(ddof=1))
        noise = -shared.mean() / den if same_days else 0.0
        adj.append(dict(first=c1.cut_id, second=c2.cut_id, n_cards=len(m),
                        corr_beta=np.corrcoef(d1, d2)[0, 1], lo=pct(bt)[0], hi=pct(bt)[1],
                        middle_build_days=(c2.cut - c1.cut).days,
                        middle_blocks_share_offers=bool(same_days),
                        expected_from_shared_noise=noise,
                        expected_with_nudge=noise - 0.5 * t1 * t2 / den,
                        tau_1_pp=t1, tau_2_pp=t2))
    adj = pd.DataFrame(adj)
    return per, pooled, bench, settle, anc, adj


# ---------------------------------------------------------------------- part 4 (post hoc)

def posthoc_offer():
    """Added after reading part 2: its robust sd is honest but the plain sd isn't, so which
    cards hold the offer-rate tail, and do they miss on pick rate too?"""
    o = pd.read_csv(f"{OUT}/q_offer_rows.csv")
    p = pd.read_csv(f"{OUT}/q_tau_pairs.csv")
    key = ["color", "before_builds", "after_builds"]
    tail = o[o.z_binom_rarity.abs() > 3].copy()
    tail["share_change_vs_rarity_median"] = np.expm1(tail.log_share_ratio
                                                     - tail.controls_median_rarity)
    both = tail.groupby("card_id").patch.nunique()
    tail["tail_in_both_patches"] = tail.card_id.map(both) == 2
    m = p[p.fit_on == "all offers"].merge(
        o[key + ["card_id", "z_binom_rarity"]].rename(columns=dict(
            card_id="pseudo_card", z_binom_rarity="z_offer")), on=key + ["pseudo_card"])
    tail = tail.merge(m[key + ["pseudo_card", "z"]].rename(columns=dict(
        pseudo_card="card_id", z="placebo_z")), on=key + ["card_id"], how="left")
    cols = ["patch", "color", "card_id", "rarity", "offers_before", "offers_after",
            "share_change_vs_rarity_median", "z_binom_rarity", "z_boot_rarity",
            "tail_in_both_patches", "placebo_z"]
    tail = tail.sort_values("z_binom_rarity", key=np.abs, ascending=False)[cols]
    rows = []
    for name, g in [("all", m)] + list(m.groupby("patch")):
        g = g.reset_index(drop=True)
        zs, zo = g.z.to_numpy(), g.z_offer.to_numpy()
        bt = cluster_boot(g.pseudo_card, lambda i: (
            stats.spearmanr(zs[i], zo[i]).statistic,
            stats.spearmanr(np.abs(zs[i]), np.abs(zo[i])).statistic))
        t = o if name == "all" else o[o.patch == name]
        rows.append(dict(
            patch=name, n_offer_rows=len(t), n_offer_abs_z_gt3=int((t.z_binom_rarity.abs() > 3).sum()),
            n_gt3_positive=int((t.z_binom_rarity > 3).sum()), n_pairs=len(g),
            spearman_signed=stats.spearmanr(zs, zo).statistic, signed_lo=pct(bt[:, 0])[0],
            signed_hi=pct(bt[:, 0])[1],
            spearman_abs=stats.spearmanr(np.abs(zs), np.abs(zo)).statistic,
            abs_lo=pct(bt[:, 1])[0], abs_hi=pct(bt[:, 1])[1],
            placebo_robust_sd=robust_sd(zs),
            placebo_robust_sd_offer_z_le2=robust_sd(zs[np.abs(zo) <= 2]),
            n_offer_z_le2=int((np.abs(zo) <= 2).sum()),
            placebo_robust_sd_offer_z_gt3=robust_sd(zs[np.abs(zo) > 3]),
            n_offer_z_gt3=int((np.abs(zo) > 3).sum())))
    return tail, pd.DataFrame(rows)


def asides(pairs):
    """Descriptive only, asked for by Phil while part 3 ran (after his q_z_vs_offers.py look):
    (a) the second patch's top offer bin; (b) the first patch's one-sided offer-rate tail and
    the pool changes on file for each card's rarity in that window."""
    d = pairs.assign(beta_pp=100 * pairs.beta, se_pp=100 * pairs.se,
                     rarity=pairs.pseudo_card.map(RARITY).fillna(""))
    d["offer_bin"] = d.groupby("patch").n_treated_offers.transform(      # q_z_vs_offers.py's
        lambda s: pd.qcut(np.log10(s), 6, labels=False))                 # six bins per patch
    bins = d.groupby(["patch", "offer_bin"]).agg(
        n_pairs=("z", "size"), offers_min=("n_treated_offers", "min"),
        offers_median=("n_treated_offers", "median"), offers_max=("n_treated_offers", "max"),
        median_se_pp=("se_pp", "median"), robust_sd_z=("z", robust_sd),
        robust_sd_beta_pp=("beta_pp", robust_sd), sd_beta_pp=("beta_pp", "std"),
        share_common=("rarity", lambda r: (r == "Common").mean())).reset_index()
    top = d[(d.patch == "second") & (d.offer_bin == 5)].sort_values("z")
    top = top[["color", "pseudo_card", "rarity", "fit_on", "n_treated_offers",
               "treated_rate_before", "beta_pp", "se_pp", "z"]]

    o = pd.read_csv(f"{OUT}/q_offer_rows.csv")
    t = o[(o.patch == "first") & (o.z_binom_rarity > 3)].copy()
    cc = did._csv("reference/card_changes.csv")
    cc = cc[(cc.stable_build == "v0.103.2")
            & cc.change_kind.str.contains("added|removed|rarity_change")]
    changed = did.window_changes(*REAL["first"])[0]
    notes = {}                                         # (color, rarity) -> pool changes
    for card, g in cc.groupby("card_id"):
        color = g.color.iloc[0] or "color not on file"
        r = g[g.field == "rarity"]
        if len(r):
            hits = [(r.old.iloc[0], f"{card} left ({r.old.iloc[0]} -> {r.new.iloc[0]})"),
                    (r.new.iloc[0], f"{card} joined ({r.old.iloc[0]} -> {r.new.iloc[0]})")]
        else:
            what = "added" if "added" in g.change_kind.iloc[0] else "removed"
            hits = [(g.rarity.iloc[0] or "rarity not on file", f"{card} {what}")]
        for rar, text in hits:
            notes.setdefault((color, rar), []).append(
                text + ("" if card in changed else " [not in window_changes]"))
    t["pool_change_in_rarity"] = [
        "; ".join(notes.get((c, r), [])) or "none" for c, r in zip(t.color, t.rarity)]
    t["share_change_vs_rarity_median"] = np.expm1(t.log_share_ratio - t.controls_median_rarity)
    t = t.sort_values("z_binom_rarity", ascending=False)[
        ["color", "card_id", "rarity", "offers_before", "offers_after",
         "share_change_vs_rarity_median", "z_binom_rarity", "pool_change_in_rarity"]]
    unplaced = "; ".join(f"{k[1]}: {', '.join(v)}" for k, v in notes.items()
                         if k[0] == "color not on file")
    return bins, top, t, unplaced


# ------------------------------------------------------------------------------------- main

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--part", type=int, choices=range(1, 5), action="append")
    ap.add_argument("--time", action="store_true")
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--interior-step", type=int, default=7)
    args = ap.parse_args()

    T0 = time.time()
    db.use_derived_colors()
    con = db.connect()
    patch_did(con)
    RAW = pd.read_parquet(PLACEBO)
    PAIRS = did.placebo_pairs(RAW)
    obs = {p: robust_sd(PAIRS.z[PAIRS.patch == p]) for p in FACTORS}
    if len(PAIRS) != 463 or any(abs(obs[p] - FACTORS[p]) > 0.011 for p in FACTORS):
        raise SystemExit(f"placebo_h3 does not give 463 pairs and 4.10 / 2.67: {len(PAIRS)}, {obs}")
    pd.set_option("display.width", 250, "display.max_columns", 60, "display.max_rows", 300,
                  "display.float_format", "{:.3f}".format)
    os.makedirs(OUT, exist_ok=True)
    parts = set(args.part or [])
    save = lambda t, name: t.to_csv(f"{OUT}/{name}.csv", index=False)

    if args.check:
        check_mle()
        gate(con, RAW)
    if 1 in parts:
        TAU, PRED, TP = part1(PAIRS)
        save(TAU, "q_tau"), save(PRED, "q_tau_predict"), save(TP, "q_tau_pairs")
        print(TAU.to_string(index=False), PRED.T.to_string(), sep="\n", flush=True)
    if 2 in parts:
        O = part2(con)
        save(O, "q_offer_rows")
        OS = offer_summary(O)
        save(OS, "q_offer_summary")
        print(OS.to_string(index=False), flush=True)
        for p, g in O.groupby("patch"):
            print(f"{p}: robust sd of z_binom_rarity {robust_sd(g.z_binom_rarity):.2f}: "
                  f"{band(robust_sd(g.z_binom_rarity))}")
    if 3 in parts:
        CUTS = cut_list(args.interior_step)
        if args.time:
            print(CUTS.to_string(index=False))
            time_fits(con, CUTS)
        else:
            if not args.summary:
                F, OF, INFO, ANC = sweep(con, CUTS, PAIRS)
                save(CUTS, "q_cuts"), save(F, "q_cut_fits"), save(OF, "q_cut_offer")
                save(INFO, "q_cut_info"), save(ANC, "q_anchor_pairs")
            rd = lambda name: pd.read_csv(f"{OUT}/{name}.csv")
            F, OF, INFO, ANC = (rd("q_cut_fits"), rd("q_cut_offer"), rd("q_cut_info"),
                                rd("q_anchor_pairs"))
            PER, POOL, BENCH, SET, AN, ADJ = summaries(CUTS, F, OF, INFO, ANC, PAIRS)
            for t, name in ((PER, "q_cut_summary"), (POOL, "q_pooled"),
                            (BENCH, "q_interior_benchmark"), (SET, "q_settling"),
                            (AN, "q_anchor"), (ADJ, "q_adjacent")):
                save(t, name)
                print(name, t.T.to_string() if len(t) < 8 else t.to_string(index=False),
                      sep="\n", flush=True)
            print(f"fits: {len(F)}, failed {(F.error.fillna('') != '').sum()}; anchors "
                  f"{len(ANC)}, failed {(ANC.error.fillna('') != '').sum()}")

    if 4 in parts:
        TAIL, LINK = posthoc_offer()
        save(TAIL, "q_posthoc_offer_tail"), save(LINK, "q_posthoc_offer_link")
        print(TAIL.to_string(index=False), LINK.T.to_string(), sep="\n", flush=True)
        BINS, TOP, FT, UNPLACED = asides(PAIRS)
        save(BINS, "q_aside_offer_bins"), save(TOP, "q_aside_second_top_bin")
        save(FT, "q_aside_first_offer_tail")
        print(BINS.to_string(index=False), TOP.to_string(index=False), FT.to_string(index=False),
              f"pool changes at v0.103.2 with no color on file: {UNPLACED}", sep="\n", flush=True)
        for name, g in (("second, top bin", TOP),):
            print(name, g.color.value_counts().to_dict(), g.rarity.value_counts().to_dict(),
                  g.fit_on.value_counts().to_dict(), f"z > 0: {(g.z > 0).sum()} of {len(g)}")

    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2 ** 30
    print(f"done in {time.time() - T0:.0f} s; peak RSS {rss:.1f} GB")
