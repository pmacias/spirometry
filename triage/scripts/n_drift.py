"""Section N (EXPLORATORY): is card-level drift the cause of the placebo spread?

Proposed after the results were seen. Reads the final tables; changes no factor, number or
result. Predictions, definitions and what each outcome means are in TRIAGE.md section N,
written before this ran.

    python triage/scripts/n_drift.py --check        # same model path as the placebo: saved z back
    python triage/scripts/n_drift.py --part 0       # builds: weeks and offers; rarity check
    python triage/scripts/n_drift.py --part 1       # within-build slopes, sigma_g
    python triage/scripts/n_drift.py --part 2       # gap scan
    python triage/scripts/n_drift.py --part 3       # budget (reads parts 1 and 2)
    python triage/scripts/n_drift.py --part 4       # detrended placebo
    python triage/scripts/n_drift.py --part 5       # mix check
    python triage/scripts/n_drift.py --part 6       # POST HOC, added after reading tests 1-5:
                                                    # release-week and late-build slopes, scans
                                                    # one by one, test 4's noise-only benchmark,
                                                    # direct variance budget

Run from the repository root. Output: triage/out_final/n_*.csv (TRIAGE_OUT overrides), keyed by
build, window and card; no run IDs. runs.duckdb is opened read-only. Colors are derived (db.py).
Card type exists only in reference/raw/cards.json: with TRIAGE_COLORS=reference it is read from
there, otherwise that split stays blank.
"""
import argparse
import json
import os
import pathlib
import resource
import sys
import time
import zlib

import numpy as np
import pandas as pd

sys.path.insert(0, "triage/scripts")
import db  # noqa: E402
from spirometry import did  # noqa: E402

OUT = os.environ.get("TRIAGE_OUT", "triage/out_final")
PLACEBO = "data/analysis/placebo_h3.parquet"
MIN_OFFERS = 51                 # placebo_h3's min_offers
WEEKS_AFTER = 3
FACTORS = {"first": 4.10, "second": 2.67}
N_BOOT, BOOT_SEED, SEED, N_PSEUDO = 2000, 20261106, 0, 20
# build -> (current-stable start, full weeks, entry window, exit window)
BUILDS = {
    "v0.99.1": ("2026-03-17", 4, ("v0.98.3", "v0.99.1"), ("v0.99.1", "v0.103.2")),
    "v0.103.2": ("2026-04-16", 6, ("v0.99.1", "v0.103.2"), ("v0.103.2", "v0.103.3")),
    "v0.107.1": ("2026-06-18", 15, ("v0.103.3", "v0.107.1"), None),
}
HORIZON = {"v0.99.1": 4, "v0.103.2": 6, "v0.107.1": 6}       # one horizon across builds
SCANS = [("v0.99.1", 1, (1, 2)), ("v0.103.2", 1, (1, 2, 4)),
         ("v0.107.1", 1, (1, 2, 4, 6)), ("v0.107.1", 8, (1, 2, 4, 6))]
BANDS = "CASE WHEN ascension = 0 THEN 'A0' WHEN ascension <= 4 THEN 'A1-4' " \
        "WHEN ascension <= 8 THEN 'A5-8' ELSE 'A9-10' END"

CELLS_SQL = f"""
SELECT character, card_id, cast(floor((epoch(start_time) - epoch($t0::TIMESTAMP)) / 604800)
         AS INTEGER) AS week,
       act, {BANDS} AS band, count(*) AS n, sum(picked::INTEGER) AS k
FROM offers_with_version
WHERE build_id = $build AND ascension IS NOT NULL
  AND start_time >= $t0::TIMESTAMP AND start_time < $t1::TIMESTAMP
GROUP BY ALL
"""
RARITY_SQL = """
SELECT character, card_id, count(*) AS n FROM offers_with_version
WHERE list_contains(?, build_id) AND ascension IS NOT NULL GROUP BY ALL
"""
DAYS_SQL = """
SELECT list_contains($after, build_id) AS after,
       floor((epoch(start_time) - epoch($t0::TIMESTAMP)) / 86400) AS day, count(*) AS n
FROM offers_with_version
WHERE character = $character AND list_contains($builds, build_id) AND ascension IS NOT NULL
  AND (NOT list_contains($after, build_id) OR start_time < $cutoff)
GROUP BY ALL
"""


def robust_sd(z):
    z = pd.Series(z).dropna()
    return 1.4826 * (z - z.median()).abs().median()


def unchanged(build):
    """Cards changed entering or leaving the build (every kind of change)."""
    _, _, entry, leave = BUILDS[build]
    out = set()
    for w in (entry, leave):
        if w:
            out |= did.window_changes(*w)[0]
    return out


def load_cells(con):
    """Offers and picks per build, own-color unchanged card, week, act and ascension band,
    in the weeks each build was the current stable."""
    colors, frames = did.card_colors(), []
    for build, (start, weeks, _, _) in BUILDS.items():
        t0 = pd.Timestamp(start)
        c = con.execute(CELLS_SQL, dict(build=build, t0=str(t0),
                                        t1=str(t0 + pd.Timedelta(weeks=weeks)))).df()
        c["color"] = c.character.str.replace("CHARACTER.", "", regex=False).str.lower()
        c = c[(c.card_id.map(colors) == c.color).to_numpy()]
        c = c[~c.card_id.isin(unchanged(build))]
        frames.append(c.assign(build=build))
    return pd.concat(frames, ignore_index=True).drop(columns="character")


def derive_rarity(con):
    """Tier by offers relative to the character's most offered card, on all three builds and
    before any card is excluded (the rarities on file are mostly changed cards). Offers are
    tri-modal: Rare about 0.17, Uncommon 0.36, Common 1.0. Checked against the rarities on file
    (part 0)."""
    n = con.execute(RARITY_SQL, [list(BUILDS)]).df()
    n["color"] = n.character.str.replace("CHARACTER.", "", regex=False).str.lower()
    n = n[(n.card_id.map(did.card_colors()) == n.color).to_numpy()]
    r = n.n / n.groupby("color").n.transform("max")
    n["rarity"] = np.select([r >= 0.6, r >= 0.25], ["Common", "Uncommon"], "Rare")
    return n.set_index("card_id").rarity, r.set_axis(n.card_id)


def rarity_on_file():
    a = pd.read_parquet("data/analysis/offer_rate.parquet")[["card", "rarity"]]
    b = did._csv("reference/card_changes.csv")[["card_id", "rarity"]]
    b = b[b.rarity != ""].rename(columns=dict(card_id="card"))
    return pd.concat([a, b]).drop_duplicates("card").set_index("card").rarity


def card_types():
    if os.environ.get("TRIAGE_COLORS") != "reference":
        return {}
    cards = json.loads(pathlib.Path("reference/raw/cards.json").read_bytes())
    return {c["id"]: c.get("type") or "" for c in cards}


# ---------------------------------------------------------------------------------- test 1

def lines(d, keys):
    """Weighted line of y on week per group; d has keys, week, y, w (1 / var of y)."""
    d = d.assign(wt=d.w * d.week, wy=d.w * d.y)
    g = d.groupby(keys, sort=False)
    sw, st, sy = g.w.transform("sum"), g.wt.transform("sum"), g.wy.transform("sum")
    tc = d.week - st / sw
    d = d.assign(a=d.w * tc * tc, b=d.w * tc * d.y)
    g = d.groupby(keys, sort=False)
    out = g[["a", "b"]].sum()
    out["slope"] = out.b / out.a
    out["se"] = 1 / np.sqrt(out.a)
    d["res"] = d.y - sy / sw - d.groupby(keys, sort=False).b.transform("sum") / \
        d.groupby(keys, sort=False).a.transform("sum") * tc
    out["chi2"] = (d.w * d.res ** 2).groupby([d[k] for k in keys], sort=False).sum()
    out["n_weeks"] = g.size()
    return out.drop(columns=["a", "b"]).reset_index()


def full_cards(w, need):
    """Rows of cards with at least MIN_OFFERS in every one of `need` weeks."""
    w = w[w.week < need]
    ok = w[w.n >= MIN_OFFERS].groupby(["build", "color", "card_id"]).week.transform("nunique")
    keep = w[w.n >= MIN_OFFERS][ok == need][["build", "color", "card_id"]].drop_duplicates()
    return w.merge(keep, on=["build", "color", "card_id"])


def card_slopes(cells, horizon=None, scale="logit"):
    """One slope per (build, color, card): weekly empirical logit (or pp) on week."""
    rows = []
    for build, (_, weeks, _, _) in BUILDS.items():
        need = (horizon or {}).get(build, weeks)
        w = cells[cells.build == build].groupby(
            ["build", "color", "card_id", "week"], as_index=False)[["n", "k"]].sum()
        if len(w):
            rows.append(full_cards(w, need))
    w = pd.concat(rows, ignore_index=True)
    p = (w.k + 0.5) / (w.n + 1)
    if scale == "logit":
        w["y"], w["w"] = np.log(p / (1 - p)), w.n * p * (1 - p)
    else:
        w["y"], w["w"] = 100 * w.k / w.n, w.n / (p * (1 - p) * 1e4)
    return lines(w, ["build", "color", "card_id"])


def add_dev(s):
    """Slope minus its build x character mean, scaled so dev^2 is unbiased for the variance."""
    g = s.groupby(["build", "color"]).slope
    n = g.transform("size")
    return s.assign(dev=(s.slope - g.transform("mean")) * np.sqrt(n / (n - 1)))


def boot_sigma2(s):
    """Percentile interval of mean(dev^2 - se^2), resampling cards (a card's builds together)."""
    v = (s.dev ** 2 - s.se ** 2).to_numpy()
    ids = pd.factorize(s.card_id)[0]
    idx = [np.flatnonzero(ids == i) for i in range(ids.max() + 1)]
    rng = np.random.default_rng(BOOT_SEED)
    out = []
    for _ in range(N_BOOT):
        take = np.concatenate([idx[i] for i in rng.integers(0, len(idx), len(idx))])
        out.append(v[take].mean())
    return np.percentile(out, [2.5, 97.5]), np.var(out, ddof=1)


def sigma_row(s, **label):
    est = (s.dev ** 2 - s.se ** 2).mean()
    (lo, hi), bvar = boot_sigma2(s)
    df = (s.n_weeks - 2).clip(lower=1)
    lof = float((s.chi2.sum() / df.sum()))
    est_lof = (s.dev ** 2).mean() - lof * (s.se ** 2).mean()
    root = lambda x: np.sqrt(max(x, 0))
    return dict(**label, n_cards=s.card_id.nunique(), n_slopes=len(s), var_g=(s.dev ** 2).mean(),
                mean_se2=(s.se ** 2).mean(), sigma2=est, sigma2_lo=lo, sigma2_hi=hi, boot_var=bvar,
                sigma_g=root(est), sigma_lo=root(lo), sigma_hi=root(hi), lack_of_fit=lof,
                sigma2_lof=est_lof, sigma_g_lof=root(est_lof))


def part1(cells, rarity, types):
    rows = []
    sets = {}
    for scale in ("logit", "pp"):
        full = add_dev(card_slopes(cells, None, scale)).assign(scale=scale, horizon="full")
        hor = add_dev(card_slopes(cells, HORIZON, scale)).assign(scale=scale, horizon="matched")
        sets[scale] = (full, hor)
        rows.append(sigma_row(hor, scale=scale, split="overall (matched horizon)", level="all"))
        for b, g in hor.groupby("build", sort=False):
            rows.append(sigma_row(g, scale=scale, split="build, matched", level=b))
        for b, g in full.groupby("build", sort=False):
            rows.append(sigma_row(g, scale=scale, split="build, full", level=b))
        for c, g in hor.groupby("color"):
            rows.append(sigma_row(g, scale=scale, split="character", level=c))
        for r, g in hor.groupby(hor.card_id.map(rarity).fillna("")):
            rows.append(sigma_row(g, scale=scale, split="rarity (derived)", level=r))
        if types:
            for t, g in hor.groupby(hor.card_id.map(types).fillna("")):
                rows.append(sigma_row(g, scale=scale, split="card type", level=t))
    t = pd.DataFrame(rows)
    # partially pooled per-character sigma^2: shrink toward the overall by method of moments
    pooled = []
    for scale, g in t[t.split == "character"].groupby("scale"):
        ov = t[(t.scale == scale) & (t.split.str.startswith("overall"))].sigma2.iloc[0]
        tau2 = max(0.0, g.sigma2.var(ddof=1) - g.boot_var.mean())
        for r in g.itertuples():
            w = tau2 / (tau2 + r.boot_var) if tau2 + r.boot_var > 0 else 0.0
            est = w * r.sigma2 + (1 - w) * ov
            pooled.append(dict(scale=scale, color=r.level, raw_sigma_g=r.sigma_g,
                               raw_lo=r.sigma_lo, raw_hi=r.sigma_hi, weight_on_own=w,
                               pooled_sigma_g=np.sqrt(max(est, 0)), tau2=tau2))
    slopes = pd.concat([sets["logit"][0], sets["logit"][1], sets["pp"][0], sets["pp"][1]])
    return t, pd.DataFrame(pooled), slopes


# ---------------------------------------------------------------------------------- test 2

def fake_host(color, key, drop):
    """A window row for did's model code: a card id of this color that is in no data, with
    the build's changed cards excluded from the controls."""
    card = f"__FAKE_{color}"
    FAKE_ROWS[key] = dict(card_id=card, control_exclusions=" ".join(sorted(drop)),
                          control_behavior_flags="", before_builds="", after_builds="")
    FAKE_COLORS[card] = color
    return key


FAKE_ROWS, FAKE_COLORS = {}, {}


def patch_did():
    window, colors = did.window, did.card_colors
    did.window = lambda cpid, ref=did.REF: FAKE_ROWS[cpid] if cpid in FAKE_ROWS else window(cpid, ref)
    did.card_colors = lambda ref=did.REF: {**colors(ref), **FAKE_COLORS}


def fit_y(df, cpid, pseudo, y="picked", **kw):
    """The placebo's model on outcome y: did._subset's data, did._fixed_effects, did._feols."""
    d, _ = did._subset(df, cpid, pseudo=pseudo, **kw)
    fit = did._feols(f"{y} ~ treat_post | " + " + ".join(did._fixed_effects(d, None, False)), d)
    return float(fit.coef()["treat_post"]), float(fit.se()["treat_post"]), d


def load_build(con, color, build):
    t0 = pd.Timestamp(BUILDS[build][0])
    df = did._load_offers(con, color, [build])
    df["week"] = np.floor((df.start_time - t0).dt.total_seconds() / did.WEEK).astype("int16")
    df = df[(df.week >= 0) & (df.week < BUILDS[build][1])].copy()
    df["block"] = "before"
    return did._finish(df)


def gap_fits(con):
    rows = []
    for color in did.CHARACTER_COLORS:
        loaded = {}
        for build, s0, gaps in SCANS:
            t0 = time.time()
            df = loaded.setdefault(build, load_build(con, color, build))
            key = fake_host(color, f"FAKE:{color}:{build}", unchanged(build))
            scan = f"{build} from week {s0}"
            used = [s0] + [s0 + g for g in gaps]
            n = df[df.week.isin(used)].groupby(["card_id", "week"], observed=True).size()
            n = n.unstack("week").reindex(columns=used).fillna(0)
            pool = set(did.control_cards(key, False, df=df))
            eligible = sorted(c for c in n.index[(n >= MIN_OFFERS).all(axis=1)] if c in pool)
            rng = np.random.default_rng([SEED, zlib.crc32(f"{color}|{scan}".encode())])
            picks = sorted(rng.choice(eligible, min(N_PSEUDO, len(eligible)), replace=False))
            for g in gaps:
                sub = df[df.week.isin([s0, s0 + g])].copy()
                sub["block"] = pd.Categorical(np.where(sub.week == s0, "before", "after"))
                for c in picks:
                    b, se, _ = fit_y(sub, key, c)
                    rows.append(dict(color=color, build=build, scan=scan, gap=g, pseudo_card=c,
                                     beta_pp=100 * b, se_pp=100 * se, z=b / se,
                                     n_eligible=len(eligible)))
            print(f"  {color} {scan}: {len(eligible)} eligible, "
                  f"{time.time() - t0:.0f} s", flush=True)
    return pd.DataFrame(rows)


def excess(g):
    return (g.beta_pp.var(ddof=1) - (g.se_pp ** 2).mean())


def gap_slope(f):
    """OLS of log(excess sd) on log(gap), free intercept per scan; cells with no positive
    excess variance can't enter and are counted. Returns slope, n cells used, intercept mean."""
    t = f.groupby(["scan", "gap"]).apply(excess, include_groups=False).rename("ex").reset_index()
    used = t[t.ex > 0].copy()
    if used.groupby("scan").size().max() < 2 or len(used) < 3:
        return np.nan, len(used), np.nan
    used["ly"], used["lx"] = 0.5 * np.log(used.ex), np.log(used.gap)
    used = used[used.groupby("scan").gap.transform("size") >= 2]
    dy = used.ly - used.groupby("scan").ly.transform("mean")
    dx = used.lx - used.groupby("scan").lx.transform("mean")
    b = (dx * dy).sum() / (dx ** 2).sum()
    a = (used.ly - b * used.lx).mean()
    return b, len(used), a


def gap_tables(f):
    rows = []
    groups = list(f.groupby(["scan", "gap"], sort=False)) + list(
        f.groupby(["gap"], sort=False))
    for key, g in groups:
        key = key if isinstance(key, tuple) and len(key) == 2 else ("all scans", key[0])
        rows.append(dict(scan=key[0], gap=key[1], n_fits=len(g), robust_sd_z=robust_sd(g.z),
                         sd_z=g.z.std(), sd_beta_pp=g.beta_pp.std(), mean_se_pp=g.se_pp.mean(),
                         excess_var=excess(g),
                         excess_var_robust=robust_sd(g.beta_pp) ** 2 - g.se_pp.median() ** 2))
    b, n, a = gap_slope(f)
    groups = {k: g for k, g in f.groupby(["scan", "color", "pseudo_card"], sort=False)}
    by = {}
    for (scan, color, card), g in groups.items():
        by.setdefault((scan, color), []).append(g)
    rng = np.random.default_rng(BOOT_SEED)
    boots, undefined = [], 0
    for _ in range(N_BOOT):
        parts = [gs[i] for gs in by.values() for i in rng.integers(0, len(gs), len(gs))]
        s = gap_slope(pd.concat(parts, ignore_index=True))[0]
        undefined += int(np.isnan(s))
        boots.append(s)
    lo, hi = np.nanpercentile(boots, [2.5, 97.5])
    slope = pd.DataFrame([dict(slope=b, ci_lo=lo, ci_hi=hi, n_cells_used=n,
                               n_cells=f.groupby(["scan", "gap"]).ngroups, boot_undefined=undefined,
                               excess_sd_at_gap1_pp=np.exp(a))])
    return pd.DataFrame(rows), slope


# ---------------------------------------------------------------------------------- test 3

def days(con, color, before, after):
    b, a = before.split(), after.split()
    t0 = did.release_date(a[0])
    cutoff = t0 + pd.Timedelta(seconds=(WEEKS_AFTER + 1) * did.WEEK)
    n = con.execute(DAYS_SQL, dict(after=a, builds=b + a, character=did._character(color),
                                   t0=str(t0), cutoff=cutoff.to_pydatetime())).df()
    get = lambda f: (n.day[n.after == f].to_numpy(float) / 7, n.n[n.after == f].to_numpy(float))
    return get(False), get(True)


def block_var(a, b, h):
    """Var(mean over block a - mean over block b) for unit increments |dt|^(2h), by the
    fractional Brownian covariance. h = 1 gives (mean(a) - mean(b))^2."""
    def e(x, y):
        wt = np.outer(x[1] / x[1].sum(), y[1] / y[1].sum())
        return (wt * np.abs(x[0][:, None] - y[0][None, :]) ** (2 * h)).sum()
    return e(a, b) - 0.5 * e(a, a) - 0.5 * e(b, b)


def sim_sd(v, se, reps=400):
    """Robust and plain sd of z when beta has variance se^2 + v."""
    rng = np.random.default_rng(BOOT_SEED)
    z = rng.standard_normal((reps, len(se))) * np.sqrt(1 + v / se ** 2)
    med = np.median(z, axis=1, keepdims=True)
    return (1.4826 * np.median(np.abs(z - med), axis=1)).mean(), z.std(axis=1, ddof=1).mean()


def part3(con, pairs):
    t = pd.read_csv(f"{OUT}/n_sigma.csv")
    gs = pd.read_csv(f"{OUT}/n_gap_slope.csv").iloc[0]
    get = lambda scale, split, lvl, col: float(
        t[(t.scale == scale) & (t.split == split) & (t.level == lvl)][col].iloc[0])
    ov = "overall (matched horizon)"
    build_rates = {"first": ["v0.99.1", "v0.103.2"], "second": ["v0.103.2", "v0.107.1"]}
    win = []
    for (color, before, after), g in pairs.groupby(["color", "before_builds", "after_builds"],
                                                   sort=False):
        a, b = days(con, color, before, after)
        win.append(dict(color=color, before_builds=before, after_builds=after,
                        delta_weeks=np.average(b[0], weights=b[1]) - np.average(a[0], weights=a[1]),
                        v_h1=block_var(a, b, 1.0), v_h05=block_var(a, b, 0.5),
                        v_hb=block_var(a, b, gs.slope) if np.isfinite(gs.slope) else np.nan))
    win = pd.DataFrame(win)
    d = pairs.merge(win, on=["color", "before_builds", "after_builds"])
    se, p = 100 * d.se.to_numpy(float), d.treated_rate_before.to_numpy(float)
    c2 = (gs.excess_sd_at_gap1_pp ** 2)
    specs = {}
    for name, col in (("point", "sigma2"), ("hi", "sigma2_hi")):
        pp, lg = get("pp", ov, "all", col), get("logit", ov, "all", col)
        specs[f"trend, pooled sigma_g pp ({name})"] = max(pp, 0) * d.v_h1
        specs[f"trend, pooled sigma_g logit ({name})"] = (
            max(lg, 0) * d.v_h1 * (100 * p * (1 - p)) ** 2)
    specs["trend, sigma_g pp of the neighbouring builds"] = sum(
        d.patch.map(lambda x: max(get("pp", "build, matched", build_rates[x][i], "sigma2"), 0))
        for i in (0, 1)) / 2 * d.v_h1
    specs["trend, sigma_g with lack-of-fit SE"] = (
        max(get("pp", ov, "all", "sigma2_lof"), 0) * d.v_h1)
    specs["test 2 shape, fitted exponent"] = c2 * d.v_hb
    specs["test 2 scale, random walk (h = 0.5)"] = c2 * d.v_h05
    specs["test 2 scale, steady trend (h = 1)"] = c2 * d.v_h1
    rows = []
    for name, v in specs.items():
        v = np.asarray(v, float)
        for patch, factor in FACTORS.items():
            m = (d.patch == patch).to_numpy()
            if not np.isfinite(v[m]).all():
                continue
            rob, sd = sim_sd(v[m], se[m])
            actual = robust_sd(d.z[m])
            rows.append(dict(spec=name, patch=patch, n_pairs=int(m.sum()),
                             mean_delta_weeks=d.delta_weeks[m].mean(),
                             predicted_robust_sd=rob, predicted_sd=sd, actual_robust_sd=actual,
                             factor=factor, share=(rob ** 2 - 1) / (actual ** 2 - 1)))
    return pd.DataFrame(rows), win


# ---------------------------------------------------------------------------------- test 4

def detrend(df, t0, upgraded):
    """y* = picked minus the card's before-block line (fit on before-block offers with
    week < 0, demeaned by card x upgraded). Returns df with ystar, and per-card slope and se.
    Stragglers (before-block play after the release) use t capped at the end of the after
    horizon, so a line isn't projected months out."""
    df = df[df.ascension.notna()].copy()
    t = (df.start_time - t0).dt.total_seconds().to_numpy() / did.WEEK
    df["t"] = np.minimum(t, WEEKS_AFTER + 1.0)
    p = df[(df.block == "before") & (df.week < 0)]
    if upgraded:
        p = p[p.upgraded]
    p = p[["card_id", "upgraded", "picked", "t"]].assign(y=p.picked.astype(float))
    g = p.groupby(["card_id", "upgraded"], observed=True)
    p = p.assign(dt=p.t - g.t.transform("mean"), dy=p.y - g.y.transform("mean"))
    p = p.assign(ab=p.dt * p.dy, aa=p.dt * p.dt)
    s = p.groupby("card_id", observed=True)[["ab", "aa"]].sum()
    rate = p.groupby("card_id", observed=True).y.mean()
    s["slope"] = s.ab / s.aa
    s["se"] = np.sqrt(rate * (1 - rate) / s.aa)
    tbar = p.groupby("card_id", observed=True).t.mean()
    slope = df.card_id.astype(object).map(s.slope).fillna(0.0).to_numpy(float)
    center = df.card_id.astype(object).map(tbar).fillna(0.0).to_numpy(float)
    df["ystar"] = df.picked.astype(float).to_numpy() - slope * (df.t.to_numpy() - center)
    return df, s[["slope", "se"]], tbar


def part4(con, raw, pairs, only=None):
    saved = raw.set_index(["card_patch_id", "pseudo_card"])
    rows = []
    for (color, before, after, fit_on), g in pairs.groupby(
            ["color", "before_builds", "after_builds", "fit_on"], sort=False):
        t0 = time.time()
        up = fit_on == "upgraded offers"
        df = did.load_block_data(con, color, before, after)
        rel = did.release_date(after.split()[0])
        df, s, tbar = detrend(df, rel, up)
        kw = dict(max_week_after=WEEKS_AFTER, upgraded=True if up else None)
        for r in g.itertuples():
            b0 = saved.loc[(r.card_patch_id, r.pseudo_card)]
            b, se, d = fit_y(df, r.card_patch_id, r.pseudo_card, y="ystar", **kw)
            cu = d[d.is_treated & d.after]
            delta = cu.t.mean() - tbar.get(r.pseudo_card, np.nan)
            se_b = s.se.get(r.pseudo_card, np.nan)
            se_c = np.sqrt(se ** 2 + (delta * se_b) ** 2)
            rows.append(dict(patch=r.patch, color=color, before_builds=before, fit_on=fit_on,
                             card_patch_id=r.card_patch_id, pseudo_card=r.pseudo_card,
                             beta0=float(b0.beta), se0=float(b0.se), z0=float(b0.z),
                             beta=b, se=se, z_clustered=b / se, delta_weeks=delta, slope=
                             s.slope.get(r.pseudo_card, np.nan), slope_se=se_b, se_corrected=se_c,
                             z=b / se_c))
        print(f"  {color} {before} ({fit_on}): {len(g)} fits, {time.time() - t0:.0f} s", flush=True)
    return pd.DataFrame(rows)


def detrend_summary(d):
    rows = []
    for name, g in [("all", d)] + list(d.groupby("patch")):
        proj = g.slope * g.delta_weeks
        rows.append(dict(patch=name, n_pairs=len(g), factor=FACTORS.get(name, np.nan),
                         robust_sd_z0=robust_sd(g.z0), robust_sd_z_clustered=robust_sd(g.z_clustered),
                         robust_sd_z_corrected=robust_sd(g.z), sd_z0=g.z0.std(),
                         sd_z_corrected=g.z.std(), sd_beta0_pp=100 * g.beta0.std(),
                         sd_beta_pp=100 * g.beta.std(),
                         corr_projection_beta0=proj.corr(g.beta0),
                         slope_beta0_on_projection=proj.cov(g.beta0) / proj.var(),
                         median_se0_pp=100 * g.se0.median(),
                         median_se_corrected_pp=100 * g.se_corrected.median()))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------- test 5

def standardized(cells):
    """Direct standardization: each card's weekly rate at its own band x act mix over the
    horizon; cells unseen in a week drop out and the weights renormalize. Logit by the delta
    method."""
    rows = []
    for build, need in HORIZON.items():
        c = cells[(cells.build == build) & (cells.week < need)]
        keep = c.groupby(["color", "card_id", "week"], as_index=False).n.sum()
        keep = keep[keep.n >= MIN_OFFERS]
        keep = keep[keep.groupby(["color", "card_id"]).week.transform("nunique") == need]
        c = c.merge(keep[["color", "card_id"]].drop_duplicates(), on=["color", "card_id"])
        mix = c.groupby(["color", "card_id", "band", "act"], as_index=False).n.sum().rename(
            columns=dict(n="mix"))
        c = c.groupby(["color", "card_id", "week", "band", "act"], as_index=False)[
            ["n", "k"]].sum().merge(mix, on=["color", "card_id", "band", "act"])
        c["p"] = c.k / c.n
        c["pv"] = (c.k + 0.5) / (c.n + 1)
        c["wp"] = c.mix * c.p
        c["w2v"] = c.mix ** 2 * c.pv * (1 - c.pv) / c.n
        g = c.groupby(["color", "card_id", "week"], as_index=False).agg(
            mix=("mix", "sum"), wp=("wp", "sum"), w2v=("w2v", "sum"))
        r = (g.wp / g.mix).clip(1e-4, 1 - 1e-4)
        g["y"] = np.log(r / (1 - r))
        g["w"] = 1 / (g.w2v / g.mix ** 2 / (r * (1 - r)) ** 2)
        rows.append(g.assign(build=build))
    return lines(pd.concat(rows, ignore_index=True), ["build", "color", "card_id"])


def part5(cells):
    rows = []
    base = add_dev(card_slopes(cells, HORIZON))
    key = ["build", "color", "card_id"]
    rows.append(sigma_row(base, view="unstratified", level="all cards"))
    std = add_dev(standardized(cells))
    rows.append(sigma_row(std, view="fixed band x act mix", level="all cards"))
    same = base.merge(std[key], on=key)
    rows.append(sigma_row(add_dev(same), view="unstratified, same cards", level="for the mix row"))
    for band, c in cells.groupby("band"):
        s = add_dev(card_slopes(c, HORIZON))
        rows.append(sigma_row(s, view="within band", level=band))
        rows.append(sigma_row(add_dev(base.merge(s[key], on=key)), view="unstratified, same cards",
                              level=band))
    for b in HORIZON:
        rows.append(sigma_row(std[std.build == b], view="fixed mix, by build", level=b))
        rows.append(sigma_row(base[base.build == b], view="unstratified, by build", level=b))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------- part 6 (post hoc)

def shifted(cells, build, first, n):
    c = cells[(cells.build == build) & (cells.week >= first)].assign(build=build)
    return c.assign(week=c.week - first), {build: n}


def posthoc_slopes(cells):
    """sigma_g by stretch of a build, so test 1 and test 2 compare on the same weeks."""
    rows = []
    stretches = [("v0.99.1", 0, 4), ("v0.99.1", 1, 3), ("v0.103.2", 0, 6), ("v0.103.2", 1, 5),
                 ("v0.107.1", 0, 6), ("v0.107.1", 1, 5), ("v0.107.1", 1, 7), ("v0.107.1", 8, 7)]
    for build, first, n in stretches:
        c, h = shifted(cells, build, first, n)
        for scale in ("logit", "pp"):
            s = add_dev(card_slopes(c, h, scale))
            rows.append(sigma_row(s, scale=scale, build=build, first_week=first, n_weeks_fit=n))
    parts = {}
    for scale in ("logit", "pp"):
        frames = []
        for build, n in (("v0.99.1", 3), ("v0.103.2", 5), ("v0.107.1", 5)):
            c, h = shifted(cells, build, 1, n)
            frames.append(add_dev(card_slopes(c, h, scale)))
        parts[scale] = pd.concat(frames, ignore_index=True)
        rows.append(sigma_row(parts[scale], scale=scale, build="all three", first_week=1,
                              n_weeks_fit=-1))
    return pd.DataFrame(rows)


def scan_slopes():
    """Test 2's fit one scan at a time."""
    f = pd.read_csv(f"{OUT}/n_gap_fits.csv")
    rows = []
    for scan, g in list(f.groupby("scan", sort=False)):
        if g.gap.nunique() < 3:
            rows.append(dict(scan=scan, slope=np.nan, note="fewer than 3 gaps"))
            continue
        cards = {k: v for k, v in g.groupby(["color", "pseudo_card"])}
        by = {}
        for (color, _), v in cards.items():
            by.setdefault(color, []).append(v)
        ex = g.groupby("gap").apply(excess, include_groups=False)
        rng = np.random.default_rng(BOOT_SEED)
        boots = []
        for _ in range(N_BOOT):
            d = pd.concat([gs[i] for gs in by.values() for i in rng.integers(0, len(gs), len(gs))])
            boots.append(gap_slope(d)[0])
        lo, hi = np.nanpercentile(boots, [2.5, 97.5])
        rows.append(dict(scan=scan, slope=gap_slope(g)[0], ci_lo=lo, ci_hi=hi,
                         n_negative_cells=int((ex <= 0).sum()),
                         excess_by_gap=" ".join(f"{k}:{v:.2f}" for k, v in ex.items())))
    return pd.DataFrame(rows)


def detrend_bench():
    """Does detrending remove anything? Noise-only benchmark: z if the pre-slope were pure
    noise (beta0 + noise of the projection, over the corrected SE). And the coefficient of
    beta0 on the projection, against the reliability of the pre-slope: if pre-trends carried
    on across the release the coefficient would be near the reliability; zero means they
    don't carry on."""
    d = pd.read_csv(f"{OUT}/n_detrended_pairs.csv")
    d["proj"], d["noise_sd"] = d.slope * d.delta_weeks, (d.slope_se * d.delta_weeks).abs()
    rows = []
    allo = d[d.fit_on == "all offers"]       # upgraded-offers pairs have few offers: their
    views = [("all", d)] + list(d.groupby("patch"))           # noise swamps the mean noise
    views += [(f"{k}, all-offers pairs", g) for k, g in allo.groupby("patch")]
    for name, g in views:
        g = g.dropna(subset=["proj", "noise_sd"]).reset_index(drop=True)
        rng = np.random.default_rng(BOOT_SEED)
        sims = [robust_sd((g.beta0 + rng.normal(0, g.noise_sd)) / np.hypot(g.se0, g.noise_sd))
                for _ in range(300)]
        ids = pd.factorize(g.pseudo_card)[0]
        idx = [np.flatnonzero(ids == i) for i in range(ids.max() + 1)]
        p, b = g.proj.to_numpy(), g.beta0.to_numpy()
        boots = []
        for _ in range(N_BOOT):
            t = np.concatenate([idx[i] for i in rng.integers(0, len(idx), len(idx))])
            boots.append(np.cov(p[t], b[t])[0, 1] / p[t].var(ddof=1))
        rows.append(dict(
            patch=name, n_pairs=len(g), robust_sd_z_corrected=robust_sd(g.z),
            noise_only_robust_sd=np.mean(sims), sd_z_corrected=g.z.std(),
            coef_beta0_on_projection=np.cov(p, b)[0, 1] / p.var(ddof=1),
            coef_lo=np.percentile(boots, 2.5), coef_hi=np.percentile(boots, 97.5),
            reliability_pre_slope=1 - (g.noise_sd ** 2).mean() / p.var(ddof=1),
            r2=np.corrcoef(p, b)[0, 1] ** 2))
    return pd.DataFrame(rows)


def direct_budget(pairs):
    """Excess variance of the real placebo betas against the within-build scan at the gap
    nearest the real blocks' distance. Model-free, and 1-week blocks keep shocks the real
    multi-week blocks average out, so this flatters the within-build side."""
    g = pd.read_csv(f"{OUT}/n_gap_summary.csv")
    rows = []
    for patch, d in pairs.groupby("patch"):
        real = 1e4 * (d.beta.var(ddof=1) - (d.se ** 2).mean())
        for scan, gap in (("all scans", 4), ("v0.103.2 from week 1", 4),
                          ("v0.107.1 from week 1", 4), ("v0.107.1 from week 8", 4)):
            ex = g[(g.scan == scan) & (g.gap == gap)].excess_var.iloc[0]
            rows.append(dict(patch=patch, real_excess_var=real, scan=scan, gap=gap,
                             scan_excess_var=ex, share=ex / real))
    return pd.DataFrame(rows)


def posthoc_budget(pairs, ph):
    """Test 3 with sigma_g from the weeks test 2 sees (release week out)."""
    w = pd.read_csv(f"{OUT}/n_budget_windows.csv")
    d = pairs.merge(w, on=["color", "before_builds", "after_builds"])
    r = ph[(ph.scale == "pp") & (ph.build == "all three")].iloc[0]
    rows = []
    for name, s2 in (("trend, release week out", r.sigma2), ("same, lack-of-fit SE", r.sigma2_lof)):
        for patch in FACTORS:
            g = d[d.patch == patch]
            rob, sd = sim_sd(max(s2, 0) * g.v_h1.to_numpy(), 100 * g.se.to_numpy(float))
            act = robust_sd(g.z)
            rows.append(dict(spec=name, patch=patch, predicted_robust_sd=rob, predicted_sd=sd,
                             actual_robust_sd=act, share=(rob ** 2 - 1) / (act ** 2 - 1)))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------- main

def check(con, raw):
    """Model path check: y = picked through fit_y gives the saved beta and se; a fake window
    built from a real one (same blocks and exclusions) gives them too."""
    for cpid in ("HEMOKINESIS@v0.103.2/patch", "UPROAR@v0.107.1/patch"):
        w = did.window(cpid)
        s = raw[raw.card_patch_id == cpid].iloc[:2]
        color = s.color.iloc[0]
        df = did.load_block_data(con, color, w["before_builds"], w["after_builds"])
        key = fake_host(color, f"CHECK:{cpid}", {w["card_id"], *w["control_exclusions"].split()})
        for r in s.itertuples():
            b1, se1, _ = fit_y(df, cpid, r.pseudo_card, max_week_after=WEEKS_AFTER)
            b2, se2, _ = fit_y(df, key, r.pseudo_card, max_week_after=WEEKS_AFTER)
            print(f"{cpid} {r.pseudo_card}: saved {r.beta:.8f} / {r.se:.8f}; fit_y |db| "
                  f"{abs(b1 - r.beta):.1e}, fake host |db| {abs(b2 - r.beta):.1e}", flush=True)
            if max(abs(b1 - r.beta), abs(b2 - r.beta), abs(se1 - r.se), abs(se2 - r.se)) > 1e-8:
                raise SystemExit("check failed")
    # block_var: h = 1 is the squared difference of means; line() recovers a known line
    a, b = (np.array([0., 1.]), np.array([1., 3.])), (np.array([4., 5.]), np.array([2., 2.]))
    d = np.average(b[0], weights=b[1]) - np.average(a[0], weights=a[1])
    assert abs(block_var(a, b, 1.0) - d ** 2) < 1e-9
    t = pd.DataFrame(dict(c="x", week=[0, 1, 2, 3], y=[1., 1.5, 2., 2.5], w=[1., 2., 3., 4.]))
    assert abs(lines(t, ["c"]).slope.iloc[0] - 0.5) < 1e-12
    print("block_var and lines: ok")


ap = argparse.ArgumentParser()
ap.add_argument("--check", action="store_true")
ap.add_argument("--part", type=int, choices=range(7), action="append")
args = ap.parse_args()

T0 = time.time()
db.use_derived_colors()
patch_did()
con = db.connect()
RAW = pd.read_parquet(PLACEBO)
pd.set_option("display.width", 220, "display.max_columns", 40, "display.max_rows", 300,
              "display.float_format", "{:.4f}".format)
os.makedirs(OUT, exist_ok=True)
parts = set(args.part or [])

if args.check:
    check(con, RAW)
if parts & {0, 1, 5, 6}:
    CELLS = load_cells(con)
if parts & {3, 4, 6}:
    PAIRS = did.placebo_pairs(RAW)
    if len(PAIRS) != 463:
        raise SystemExit("placebo_h3 does not give 463 pairs")
if 0 in parts:
    rar, ratio = derive_rarity(con)
    t = CELLS.groupby("build").agg(offers=("n", "sum"), cards=("card_id", "nunique"),
                                   weeks=("week", "nunique"))
    w = CELLS.groupby(["build", "week"]).n.sum().unstack("build").round(0)
    print(t, w.T.to_string(), sep="\n")
    t.reset_index().to_csv(f"{OUT}/n_builds.csv", index=False)
    known = rarity_on_file()
    both = pd.DataFrame(dict(known=known, derived=rar)).dropna()
    print(pd.crosstab(both.known, both.derived))
    print("ratio quantiles", ratio.quantile([.1, .25, .5, .75, .9]).round(2).to_dict())
    print(rar.value_counts().to_dict())
if 1 in parts:
    rar, _ = derive_rarity(con)
    S, P, SL = part1(CELLS, rar, card_types())
    S.to_csv(f"{OUT}/n_sigma.csv", index=False)
    P.to_csv(f"{OUT}/n_sigma_pooled_character.csv", index=False)
    SL.to_csv(f"{OUT}/n_slopes.csv", index=False)
    cols = ["scale", "split", "level", "n_cards", "n_slopes", "var_g", "mean_se2", "sigma2",
            "sigma_g", "sigma_lo", "sigma_hi", "lack_of_fit", "sigma_g_lof"]
    print(S[cols].to_string(index=False), P.to_string(index=False), sep="\n", flush=True)
if 2 in parts:
    GF = gap_fits(con)
    GF.to_csv(f"{OUT}/n_gap_fits.csv", index=False)
    GT, GS = gap_tables(GF)
    GT.to_csv(f"{OUT}/n_gap_summary.csv", index=False)
    GS.to_csv(f"{OUT}/n_gap_slope.csv", index=False)
    print(GT.to_string(index=False), GS.T.to_string(), sep="\n", flush=True)
if 3 in parts:
    B, W = part3(con, PAIRS)
    B.to_csv(f"{OUT}/n_budget.csv", index=False)
    W.to_csv(f"{OUT}/n_budget_windows.csv", index=False)
    print(W.to_string(index=False), B.to_string(index=False), sep="\n", flush=True)
if 4 in parts:
    D = part4(con, RAW, PAIRS)
    D.to_csv(f"{OUT}/n_detrended_pairs.csv", index=False)
    DS = detrend_summary(D)
    DS.to_csv(f"{OUT}/n_detrended.csv", index=False)
    print(DS.T.to_string(), flush=True)
if 5 in parts:
    M = part5(CELLS)
    M.to_csv(f"{OUT}/n_mix.csv", index=False)
    print(M[["view", "level", "n_cards", "n_slopes", "var_g", "mean_se2", "sigma2", "sigma_g",
             "sigma_lo", "sigma_hi"]].to_string(index=False), flush=True)

if 6 in parts:
    PH = posthoc_slopes(CELLS)
    PH.to_csv(f"{OUT}/n_posthoc_sigma.csv", index=False)
    print(PH[["scale", "build", "first_week", "n_weeks_fit", "n_cards", "sigma_g", "sigma_lo",
              "sigma_hi", "lack_of_fit", "sigma_g_lof"]].to_string(index=False), flush=True)
    for name, tab in (("n_posthoc_scans", scan_slopes()), ("n_detrended_bench", detrend_bench()),
                      ("n_budget_direct", direct_budget(PAIRS)),
                      ("n_budget_posthoc", posthoc_budget(PAIRS, PH))):
        tab.to_csv(f"{OUT}/{name}.csv", index=False)
        print(name, tab.to_string(index=False), sep="\n", flush=True)

rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2 ** 30
print(f"done in {time.time() - T0:.0f} s; peak RSS {rss:.1f} GB")
