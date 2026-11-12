"""Section R (EXPLORATORY): does the release shake scale with how much changed, and does it
happen within the same players?

Proposed after section Q was seen. Reads the final tables; changes no factor, number or
result. Rules, definitions and what each outcome means are in TRIAGE.md section R, written
before this ran.

    python triage/scripts/r_dose.py --part 1 --time    # 10 fits, runtime estimate, saves nothing
    python triage/scripts/r_dose.py --part 1           # dose: fits per character x boundary, tests
    python triage/scripts/r_dose.py --part 2           # same players: token subset, token x card FE
    python triage/scripts/r_dose.py --part 3           # asides: rarity tau, rarity tide, offer sources
    python triage/scripts/r_dose.py --part 1 --analyze # tables from the saved fits only

Fits are appended to triage/out_final/r_*_fits.csv as each unit (part 1) or window (parts 2,
3b) finishes, and a rerun skips what is there: a pause or restart redoes nothing. Delete a
fits file to redo it.

Run from the repository root. Output: triage/out_final/r_*.csv (TRIAGE_OUT overrides), keyed by
boundary, window and card. Uploaders appear only as counts: no token, hash or run ID is
printed or written. runs.duckdb is opened read-only. Colors and rarities are derived as in
q_nudge.py, whose loader, fit and likelihood this script reuses.
"""
import argparse
import os
import resource
import sys
import time

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, "triage/scripts")
import db  # noqa: E402
import q_nudge as q  # noqa: E402
from spirometry import did  # noqa: E402

OUT = q.OUT
MIN_RUNS, MIN_PAIRS, HOTFIX_DAYS = 3000, 15, 3
BLOCK = pd.Timedelta(days=21)
N_BOOT = q.N_BOOT
pct, robust_sd, mle, cluster_boot = q.pct, q.robust_sd, q.mle, q.cluster_boot


# ------------------------------------------------------------------------------ saved fits

class Store:
    """Rows appended to one CSV, a chunk at a time; `done` is the chunks already there."""

    def __init__(self, name, columns):
        self.path, self.columns = f"{OUT}/{name}.csv", columns
        self.done = set()
        if os.path.exists(self.path):
            self.done = set(pd.read_csv(self.path, usecols=["chunk"]).chunk.astype(str))

    def add(self, chunk, rows):
        d = pd.DataFrame(rows).assign(chunk=chunk).reindex(columns=["chunk"] + self.columns)
        d.to_csv(self.path, mode="a", header=not os.path.exists(self.path), index=False)
        self.done.add(chunk)

    def read(self):
        return pd.read_csv(self.path)


def tau_ci(g, n=N_BOOT, unit=None):
    """tau (pp) of rows g (beta, se in probability units; pseudo_card), one mu per `unit`
    level, with a card-resampling interval."""
    b, s = 100 * g.beta.to_numpy(float), 100 * g.se.to_numpy(float)
    u = np.zeros(len(g), int) if unit is None else pd.factorize(g[unit])[0]
    tau, _ = mle(b, s, u)
    bt = cluster_boot(g.pseudo_card.to_numpy(), lambda i: mle(b[i], s[i], pd.factorize(u[i])[0])[0],
                      n=n)
    return tau, pct(bt)[0], pct(bt)[1]


def spearman_ci(x, y, n=N_BOOT, seed=q.BOOT_SEED):
    """Spearman of two arrays over units, interval by resampling units."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    rng = np.random.default_rng(seed)
    bt = []
    for _ in range(n):
        i = rng.integers(0, len(x), len(x))
        bt.append(stats.spearmanr(x[i], y[i]).statistic if len(set(x[i])) > 1 else np.nan)
    return stats.spearmanr(x, y).statistic, pct(bt)[0], pct(bt)[1]


# ------------------------------------------------------------------------------------ part 1

def build_groups(branch):
    """The branch's builds in release order, a hotfix (<= 3 days after the build before it)
    merged into that build."""
    b = did._csv("reference/builds.csv")
    b = b[(b.branch == branch) & (b.release_date != "")].copy()
    b["date"] = pd.to_datetime(b.release_date)
    b = b.sort_values("date", kind="stable")
    groups, last = [], None
    for r in b.itertuples():
        if last is not None and (r.date - last).days <= HOTFIX_DAYS:
            groups[-1]["builds"].append(r.build_id)
        else:
            groups.append(dict(builds=[r.build_id], release=r.date, branch=branch))
        last = r.date
    for g in groups:
        g["label"] = g["builds"][0] + ("" if len(g["builds"]) == 1 else
                                       " (+" + ", ".join(g["builds"][1:]) + ")")
    return groups


def boundaries():
    out = []
    for branch in ("beta", "stable"):
        gs = build_groups(branch)
        out += [dict(boundary=f"{a['label']} -> {b['label']}", branch=branch, old=a, new=b)
                for a, b in zip(gs, gs[1:])]
    return out


RUNS_SQL = """
SELECT character, count(DISTINCT run_key) AS runs,
       count(DISTINCT CASE WHEN start_time >= $t0 AND start_time < $t1 THEN run_key END) AS runs_3w
FROM offers_with_version WHERE list_contains($builds, build_id) GROUP BY ALL
"""


def run_counts(con, group):
    t0 = group["release"]
    n = con.execute(RUNS_SQL, dict(builds=group["builds"], t0=t0.to_pydatetime(),
                                   t1=(t0 + BLOCK).to_pydatetime())).df()
    n["color"] = n.character.map(db.CHARS)
    return n.dropna(subset=["color"]).set_index("color")[["runs", "runs_3w"]]


_CE = {}


def change_tables():
    if not _CE:
        ce = did._csv("reference/change_events.csv")
        _CE["wording"] = set(ce.event_id[(ce.change_kind == "text_only")
                                         & ce.text_only_label.isin(["wording", "exclude"])])
        _CE["known"] = set(ce.event_id)
        col = ce[ce.color != ""].drop_duplicates("card_id").set_index("card_id").color
        _CE["color"] = {**did.card_colors(), **col.to_dict()}
        _CE["cv"] = did._csv("reference/card_versions.csv")
    return _CE


def dose(old, new):
    """Per character: cards changed across the boundary by kind. substantive (the dose):
    some differing event that is not a wording-only text change; text_only: only wording
    events differ; unknown: marked changed for a blank version or missing row, or its event
    is not in change_events.csv; behavior: window_changes' bug-fix flag."""
    t = change_tables()
    changed, flagged = did.window_changes(" ".join(old["builds"]), " ".join(new["builds"]))
    cv = t["cv"][t["cv"].build_id.isin(old["builds"] + new["builds"])
                 & t["cv"].card_id.isin(changed)]
    rows = []
    for card, g in cv.groupby("card_id"):
        ev = lambda blds: set(" ".join(g.event_ids[g.build_id.isin(blds)]).split())
        diff = ev(old["builds"]) ^ ev(new["builds"])
        kind = ("unknown" if not diff or not diff <= t["known"] else
                "text_only" if diff <= t["wording"] else "substantive")
        rows.append(dict(card_id=card, color=t["color"].get(card, ""), kind=kind))
    rows += [dict(card_id=c, color=t["color"].get(c, ""), kind="behavior") for c in flagged]
    d = pd.DataFrame(rows, columns=["card_id", "color", "kind"])
    n = d.groupby(["color", "kind"]).size().unstack("kind").reindex(
        columns=["substantive", "text_only", "unknown", "behavior"]).fillna(0).astype(int)
    return n.reindex(did.CHARACTER_COLORS).fillna(0).astype(int), changed


def load_side(con, color, group):
    raw = did._load_offers(con, color, group["builds"])
    t0 = group["release"]
    return raw[(raw.start_time >= t0) & (raw.start_time < t0 + BLOCK)]


def unit_df(sides, bd):
    b, a = sides[bd["old"]["label"]], sides[bd["new"]["label"]]
    df = pd.concat([b.assign(block="before"), a.assign(block="after")], ignore_index=True)
    df["week"] = np.floor((df.start_time - bd["new"]["release"]).dt.total_seconds()
                          / did.WEEK).astype("int16")
    return did._finish(df)


FIT_COLS = ["boundary", "branch", "color", "pseudo_card", "beta", "se", "z", "n_offers", "n_runs",
            "pseudo_offers_before", "pseudo_offers_after", "rate_before", "rate_after",
            "n_control_cards", "n_eligible", "error"]
UNIT_COLS = ["boundary", "branch", "color", "old", "new", "old_release", "new_release",
             "runs_old", "runs_new", "runs_old_3w", "runs_new_3w", "status", "reason",
             "dose", "n_text_only", "n_unknown", "n_behavior", "boundary_dose", "n_offers_before",
             "n_offers_after", "gap_days", "n_control_cards", "n_eligible"]


def part1_plan(con):
    """Every character x boundary with its run counts, dose and whether it is used."""
    counts, rows = {}, []
    for bd in boundaries():
        for g in (bd["old"], bd["new"]):
            if g["label"] not in counts:
                counts[g["label"]] = run_counts(con, g)
        ds, changed = dose(bd["old"], bd["new"])
        for color in did.CHARACTER_COLORS:
            c = {s: counts[bd[s]["label"]].reindex([color]).fillna(0).iloc[0] for s in ("old", "new")}
            short = [f"{s} side {int(c[s].runs_3w)} runs" for s in ("old", "new")
                     if c[s].runs_3w < MIN_RUNS]
            rows.append(dict(
                boundary=bd["boundary"], branch=bd["branch"], color=color, old=bd["old"]["label"],
                new=bd["new"]["label"], old_release=str(bd["old"]["release"].date()),
                new_release=str(bd["new"]["release"].date()), runs_old=int(c["old"].runs),
                runs_new=int(c["new"].runs), runs_old_3w=int(c["old"].runs_3w),
                runs_new_3w=int(c["new"].runs_3w), status="dropped" if short else "used",
                reason="; ".join(short) + (f" (< {MIN_RUNS})" if short else ""),
                dose=int(ds.loc[color, "substantive"]), n_text_only=int(ds.loc[color, "text_only"]),
                n_unknown=int(ds.loc[color, "unknown"]), n_behavior=int(ds.loc[color, "behavior"]),
                boundary_dose=int(ds.substantive.sum())))
    return pd.DataFrame(rows)


def part1_fits(con, plan, time_only=False):
    fits, units = Store("r_dose_fits", FIT_COLS), Store("r_units", UNIT_COLS)
    bds = {b["boundary"]: b for b in boundaries()}
    todo = plan[(plan.status == "used")]
    if time_only:
        u = todo.sort_values("runs_new_3w").iloc[-1]
        bd = bds[u.boundary]
        t0 = time.time()
        sides = {bd[s]["label"]: load_side(con, u.color, bd[s]) for s in ("old", "new")}
        df = unit_df(sides, bd)
        key = q.fake_host(u.color, "R:TIME", dose(bd["old"], bd["new"])[1])
        el = q.eligible(df, key, q.card_order(u.color))
        t_load = time.time() - t0
        t0 = time.time()
        for c in el[:10]:
            q.fit(df, key, c)
        t = (time.time() - t0) / 10
        left = todo[~(todo.boundary + "|" + todo.color).isin(fits.done)]
        print(f"part 1 timing, largest unit ({u.color}, {u.boundary}, {len(df):,} offers): load "
              f"{t_load:.0f} s, {t:.2f} s per fit. {len(todo)} units used, {len(left)} left: at "
              f"most {len(left) * (20 * t + t_load) / 60:.0f} min (smaller units are faster)")
        return
    for color in did.CHARACTER_COLORS:
        order, sides = q.card_order(color), {}
        for u in todo[todo.color == color].itertuples():
            chunk = f"{u.boundary}|{color}"
            if chunk in fits.done and chunk in units.done:
                continue
            t0 = time.time()
            bd = bds[u.boundary]
            for s in ("old", "new"):
                if bd[s]["label"] not in sides:
                    sides[bd[s]["label"]] = load_side(con, color, bd[s])
            sides = {k: v for k, v in sides.items() if k in (bd["old"]["label"], bd["new"]["label"])}
            df = unit_df(sides, bd)
            key = q.fake_host(color, f"R:{color}:{u.boundary}", dose(bd["old"], bd["new"])[1])
            el = q.eligible(df, key, order)
            base = dict(boundary=u.boundary, branch=u.branch, color=color, n_eligible=len(el))
            rows = []
            for c in el[:q.N_PSEUDO]:
                row = dict(base, pseudo_card=c, error="")
                try:
                    row.update(q.fit(df, key, c))
                    row["z"] = row["beta"] / row["se"]
                except Exception as e:
                    row["error"] = f"{type(e).__name__}: {e}"
                rows.append(row)
            if not rows:
                rows = [dict(base, error="no eligible pseudo card")]
            st = df.start_time
            info = dict(u._asdict(), n_offers_before=int((df.block == "before").sum()),
                        n_offers_after=int((df.block == "after").sum()),
                        gap_days=(st[df.block == "after"].mean()
                                  - st[df.block == "before"].mean()).total_seconds() / 86400,
                        n_control_cards=len(did.control_cards(key, df=df)), n_eligible=len(el))
            if chunk not in fits.done:
                fits.add(chunk, rows)
            if chunk not in units.done:
                units.add(chunk, [info])
            print(f"  {color} {u.boundary}: dose {u.dose}, {len(rows)} fits, "
                  f"{time.time() - t0:.0f} s", flush=True)


def part1_tables(plan):
    f = Store("r_dose_fits", FIT_COLS).read()
    u = Store("r_units", UNIT_COLS).read()
    f = f[f.error.fillna("").eq("") & np.isfinite(f.z)].merge(
        u[["boundary", "color", "dose", "boundary_dose", "gap_days"]], on=["boundary", "color"])
    f["unit"] = f.boundary + "|" + f.color
    rows = []
    for (bd, color), g in f.groupby(["boundary", "color"], sort=False):
        tau, lo, hi = tau_ci(g) if len(g) >= 5 else (np.nan,) * 3
        rows.append(dict(boundary=bd, color=color, n_pairs=len(g), tau_pp=tau, tau_lo=lo, tau_hi=hi,
                         robust_sd_z=robust_sd(g.z), median_se_pp=100 * g.se.median(),
                         sd_beta_pp=100 * g.beta.std()))
    ut = u.merge(pd.DataFrame(rows), on=["boundary", "color"], how="left")

    tests = []

    def test_a(name, d):
        for label, g in (("dose 0", d[d.dose == 0]), ("dose >= 1", d[d.dose >= 1])):
            if g.unit.nunique() < 2:
                tests.append(dict(test="a", scope=name, group=label, n_units=g.unit.nunique()))
                continue
            g = g.reset_index(drop=True)
            tau, lo, hi = tau_ci(g, unit="unit")
            b, s, un = 100 * g.beta.to_numpy(), 100 * g.se.to_numpy(), pd.factorize(g.unit)[0]
            bu = cluster_boot(un, lambda i: mle(b[i], s[i], pd.factorize(un[i])[0])[0])
            tests.append(dict(test="a", scope=name, group=label, n_units=g.unit.nunique(),
                              n_pairs=len(g), estimate=tau, lo=lo, hi=hi, lo_units=pct(bu)[0],
                              hi_units=pct(bu)[1], robust_sd_z=robust_sd(g.z),
                              median_se_pp=100 * g.se.median()))

    def test_b(name, d, x="dose", label="Spearman of unit tau against dose"):
        d = d[(d.n_pairs >= MIN_PAIRS) & d.tau_pp.notna()]
        if len(d) < 5 or d[x].nunique() < 2:
            tests.append(dict(test="b", scope=name, group=label, n_units=len(d)))
            return
        r, lo, hi = spearman_ci(d[x], d.tau_pp)
        tests.append(dict(test="b", scope=name, group=label, n_units=len(d), estimate=r, lo=lo,
                          hi=hi))

    used = ut[ut.status == "used"]
    for name, br in (("all units [rule]", None), ("beta units", "beta"), ("stable units", "stable")):
        test_a(name, f if br is None else f[f.boundary.isin(used.boundary[used.branch == br])])
        test_b(name, used if br is None else used[used.branch == br])
    test_b("all units", used, "boundary_dose", "Spearman of unit tau against the boundary's total dose")
    test_b("all units", used, "gap_days", "Spearman of unit tau against the gap between blocks (days)")
    test_b("all units", used.assign(d2=used.dose), "n_text_only",
           "Spearman of unit tau against text-only changes")
    w = used[(used.n_pairs >= MIN_PAIRS) & used.tau_pp.notna()].copy()
    w = w[w.groupby("boundary").color.transform("size") >= 2]
    w["tau_dev"] = w.tau_pp - w.groupby("boundary").tau_pp.transform("mean")
    w["dose_dev"] = w.dose - w.groupby("boundary").dose.transform("mean")
    w = w[w.groupby("boundary").dose.transform("nunique") > 1]
    if len(w) >= 5:
        r, lo, hi = spearman_ci(w.dose_dev, w.tau_dev)
        tests.append(dict(test="within boundary", scope="boundaries with >= 2 units and doses "
                          "that differ", group="Spearman of tau against dose, both as deviations "
                          "from the boundary's mean", n_units=len(w), estimate=r, lo=lo, hi=hi))
    # Phil's addition after the rules (descriptive): same boundary, dose >= 1 against dose 0
    con_rows = []
    for bd, g in f.groupby("boundary", sort=False):
        z, p = g[g.dose == 0].reset_index(drop=True), g[g.dose >= 1].reset_index(drop=True)
        if z.empty or p.empty:
            continue
        t0, t1 = tau_ci(z, unit="unit"), tau_ci(p, unit="unit")
        both = pd.concat([z.assign(side=0), p.assign(side=1)], ignore_index=True)
        b, s_ = 100 * both.beta.to_numpy(), 100 * both.se.to_numpy()
        side, un = both.side.to_numpy(), pd.factorize(both.unit)[0]

        def diff(i):
            m = side[i] == 1
            if m.all() or not m.any():
                return np.nan
            return (mle(b[i][m], s_[i][m], pd.factorize(un[i][m])[0])[0]
                    - mle(b[i][~m], s_[i][~m], pd.factorize(un[i][~m])[0])[0])

        bt = cluster_boot(both.pseudo_card.to_numpy(), diff)
        con_rows.append(dict(
            boundary=bd, branch=used.branch[used.boundary == bd].iloc[0],
            units_dose0=" ".join(sorted(z.color.unique())), units_dose_ge1=" ".join(
                f"{c}:{d}" for c, d in sorted(set(zip(p.color, p.dose)))),
            n_pairs_dose0=len(z), n_pairs_dose_ge1=len(p), tau_dose0=t0[0], tau_dose0_lo=t0[1],
            tau_dose0_hi=t0[2], tau_dose_ge1=t1[0], tau_dose_ge1_lo=t1[1], tau_dose_ge1_hi=t1[2],
            difference=t1[0] - t0[0], diff_lo=pct(bt)[0], diff_hi=pct(bt)[1]))
    con = pd.DataFrame(con_rows)
    if len(con):
        d = con.difference.to_numpy()
        rng = np.random.default_rng(q.BOOT_SEED)
        bt = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(N_BOOT)]
        con = pd.concat([con, pd.DataFrame([dict(
            boundary=f"mean over {len(d)} boundaries (interval resamples boundaries)",
            difference=d.mean(), diff_lo=pct(bt)[0], diff_hi=pct(bt)[1])])], ignore_index=True)
    # post hoc, added after reading the tests: tau per boundary, beside its gap and dose
    ph = []
    for bd, g in f.groupby("boundary", sort=False):
        g = g.reset_index(drop=True)
        t = tau_ci(g, unit="unit")
        m = used[used.boundary == bd]
        ph.append(dict(boundary=bd, branch=m.branch.iloc[0], n_units=len(m), n_pairs=len(g),
                       boundary_dose=int(m.boundary_dose.iloc[0]),
                       unit_doses=" ".join(str(x) for x in sorted(m.dose)),
                       gap_days=m.gap_days.mean(), tau_pp=t[0], tau_lo=t[1], tau_hi=t[2],
                       robust_sd_z=robust_sd(g.z), median_se_pp=100 * g.se.median()))
    return ut, pd.DataFrame(tests), con, pd.DataFrame(ph)


# ------------------------------------------------------------------------------------ part 2

def fit_fe(df, key, pseudo, extra_fe=(), add=None, **kw):
    """q.fit's model with extra fixed effects; also the singleton drop."""
    d, _ = did._subset(df, key, pseudo=pseudo, **kw)
    if add:
        add(d)
    fe = did._fixed_effects(d, None, False) + list(extra_fe)
    f = did._feols("picked ~ treat_post | " + " + ".join(fe), d)
    t = d[d.is_treated]
    return dict(beta=float(f.coef()["treat_post"]), se=float(f.se()["treat_post"]),
                n_rows=len(d), n_offers=int(f._N), n_dropped=len(d) - int(f._N),
                n_runs=int(d.run_key.nunique()), pseudo_offers_before=int((~t.after).sum()),
                pseudo_offers_after=int(t.after.sum()),
                pseudo_tokens=int(t.uploader_hash.nunique()))


TOK_COLS = ["window", "patch", "color", "fit_on", "pseudo_card", "card_patch_id", "model", "beta",
            "se", "z", "n_rows", "n_offers", "n_dropped", "n_runs", "pseudo_offers_before",
            "pseudo_offers_after", "pseudo_tokens", "beta_saved", "se_saved", "z_saved", "error"]
WIN_COLS = ["window", "patch", "color", "n_runs_all", "n_offers_all", "n_tokens_any",
            "n_tokens_both", "n_runs_subset", "n_offers_subset", "n_offers_subset_before",
            "n_offers_subset_after", "share_of_offers", "share_of_token_offers"]
MODELS = {"i": (), "ii": ("uploader_hash^card_id",)}


def windows(pairs):
    return pairs.groupby(["color", "before_builds", "after_builds"], sort=False)


def load_h3(con, color, before, after):
    df = did.load_block_data(con, color, before, after)
    return df[(df.block != "after") | (df.week <= 3)]


def token_subset(df):
    t = df[df.uploader_hash.notna()]
    n = t.groupby(["uploader_hash", "block"], observed=True).size().unstack("block").fillna(0)
    both = n.index[(n.reindex(columns=["before", "after"]).fillna(0) > 0).all(axis=1)]
    sub = t[t.uploader_hash.isin(both)].copy()
    sub["uploader_hash"] = sub.uploader_hash.cat.remove_unused_categories()
    info = dict(n_runs_all=df.run_key.nunique(), n_offers_all=len(df), n_tokens_any=len(n),
                n_tokens_both=len(both), n_runs_subset=sub.run_key.nunique(),
                n_offers_subset=len(sub), n_offers_subset_before=int((sub.block == "before").sum()),
                n_offers_subset_after=int((sub.block == "after").sum()),
                share_of_offers=len(sub) / len(df), share_of_token_offers=len(sub) / len(t))
    return sub, info


def part2_fits(con, pairs, time_only=False):
    fits, wins = Store("r_token_fits", TOK_COLS), Store("r_token_windows", WIN_COLS)
    for (color, before, after), g in windows(pairs):
        w = f"{color} {before} -> {after}"
        if w in fits.done and w in wins.done and not time_only:
            continue
        t0 = time.time()
        sub, info = token_subset(load_h3(con, color, before, after))
        t_load = time.time() - t0
        rows = []
        for r in (g.head(5) if time_only else g).itertuples():
            up = True if r.fit_on == "upgraded offers" else None
            for m, fe in MODELS.items():
                row = dict(window=w, patch=r.patch, color=color, fit_on=r.fit_on,
                           pseudo_card=r.pseudo_card, card_patch_id=r.card_patch_id, model=m,
                           beta_saved=r.beta, se_saved=r.se, z_saved=r.z, error="")
                try:
                    row.update(fit_fe(sub, r.card_patch_id, r.pseudo_card, fe, upgraded=up))
                    row["z"] = row["beta"] / row["se"]
                except Exception as e:
                    row["error"] = f"{type(e).__name__}: {e}"
                rows.append(row)
        if time_only:
            t = (time.time() - t0 - t_load) / len(rows)
            print(f"part 2 timing ({w}, {info['n_offers_subset']:,} subset offers, "
                  f"{info['n_tokens_both']} tokens): load {t_load:.0f} s, {t:.2f} s per fit; "
                  f"926 fits and 9 loads: about {(926 * t + 9 * t_load) / 60:.0f} min")
            return
        if w not in fits.done:
            fits.add(w, rows)
        if w not in wins.done:
            wins.add(w, [dict(info, window=w, patch=g.patch.iloc[0], color=color)])
        print(f"  {w}: {info['n_tokens_both']} tokens on both sides, {len(rows)} fits, "
              f"{time.time() - t0:.0f} s", flush=True)


def part2_tables():
    f = Store("r_token_fits", TOK_COLS).read()
    n_all = f.groupby("model").size().to_dict()
    ok = f[f.error.fillna("").eq("") & np.isfinite(f.z) & (f.se > 0)]
    key = ["window", "fit_on", "pseudo_card"]
    wide = ok[ok.model == "i"].merge(ok[ok.model == "ii"], on=key + ["patch"], suffixes=("_i", "_ii"))
    rows = []
    for scope, d in (("all pairs fit under both models", wide),
                     (">= 51 subset offers of the pseudo card in each block",
                      wide[(wide.pseudo_offers_before_i >= 51) & (wide.pseudo_offers_after_i >= 51)])):
        for patch, g in d.groupby("patch"):
            g = g.reset_index(drop=True)
            arr = {m: (100 * g[f"beta_{m}"].to_numpy(), 100 * g[f"se_{m}"].to_numpy())
                   for m in ("i", "ii")}
            arr["saved"] = (100 * g.beta_saved_i.to_numpy(), 100 * g.se_saved_i.to_numpy())
            est = {m: mle(*a)[0] for m, a in arr.items()}
            bt = cluster_boot(g.pseudo_card.to_numpy(), lambda i: [
                mle(arr[m][0][i], arr[m][1][i])[0] for m in ("saved", "i", "ii")])
            ratio = np.where(bt[:, 1] > 0, bt[:, 2] / np.where(bt[:, 1] > 0, bt[:, 1], 1), np.nan)
            row = dict(scope=scope, patch=patch, n_pairs=len(g), n_cards=g.pseudo_card.nunique())
            for j, m in enumerate(("saved", "i", "ii")):
                row.update({f"tau_{m}": est[m], f"tau_{m}_lo": pct(bt[:, j])[0],
                            f"tau_{m}_hi": pct(bt[:, j])[1],
                            f"median_se_{m}_pp": float(np.median(arr[m][1]))})
            row.update(ratio_ii_over_i=est["ii"] / est["i"] if est["i"] > 0 else np.nan,
                       ratio_lo=pct(ratio)[0], ratio_hi=pct(ratio)[1],
                       ratio_i_over_saved=est["i"] / est["saved"],
                       robust_sd_z_saved=robust_sd(g.z_saved_i), robust_sd_z_i=robust_sd(g.z_i),
                       robust_sd_z_ii=robust_sd(g.z_ii),
                       corr_beta_i_ii=np.corrcoef(g.beta_i, g.beta_ii)[0, 1],
                       corr_beta_saved_i=np.corrcoef(g.beta_saved_i, g.beta_i)[0, 1],
                       singleton_share_i=g.n_dropped_i.sum() / g.n_rows_i.sum(),
                       singleton_share_ii=g.n_dropped_ii.sum() / g.n_rows_ii.sum(),
                       median_pseudo_tokens=g.pseudo_tokens_i.median(),
                       median_pseudo_offers_before=g.pseudo_offers_before_i.median(),
                       median_pseudo_offers_after=g.pseudo_offers_after_i.median())
            x = row["ratio_ii_over_i"]
            row["outcome"] = ("within the same players (>= 0.75)" if x >= 0.75 else
                              "mostly who plays (<= 0.5)" if x <= 0.5 else "mixed")
            rows.append(row)
    print(f"  token fits: {n_all}; usable under both models: {len(wide)} of 463 pairs")
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------ part 3

def part3a(pairs):
    d = pairs.assign(rarity=pairs.pseudo_card.map(q.RARITY).fillna("none"))
    rows = []
    for (patch, rar), g in d.groupby(["patch", "rarity"]):
        g = g.reset_index(drop=True)
        kk = g.treated_rate_before * (1 - g.treated_rate_before)     # to_log_odds' divisor
        row = dict(patch=patch, rarity=rar, n_pairs=len(g), median_rate_before=g.treated_rate_before.median())
        for scale, gg in (("pp", g), ("lo", g.assign(beta=g.beta / kk / 100, se=g.se / kk / 100))):
            tau, lo, hi = tau_ci(gg)
            row.update({f"tau_{scale}": tau, f"tau_{scale}_lo": lo, f"tau_{scale}_hi": hi,
                        f"median_se_{scale}": 100 * gg.se.median()})
        row["robust_sd_z"] = robust_sd(g.z)
        rows.append(row)
    return pd.DataFrame(rows)


RAR_COLS = ["window", "patch", "color", "fit_on", "pseudo_card", "card_patch_id", "beta", "se", "z",
            "n_rows", "n_offers", "n_dropped", "beta_saved", "se_saved", "z_saved", "rarity",
            "error"]


def add_rarity(d):
    d["rar"] = pd.Categorical(d.card_id.astype(object).map(q.RARITY).fillna("none"))


def part3b_fits(con, pairs, time_only=False):
    fits = Store("r_rarity_fits", RAR_COLS)
    for (color, before, after), g in windows(pairs):
        w = f"{color} {before} -> {after}"
        if w in fits.done and not time_only:
            continue
        t0 = time.time()
        df = load_h3(con, color, before, after)
        t_load = time.time() - t0
        rows = []
        for r in (g.head(10) if time_only else g).itertuples():
            up = True if r.fit_on == "upgraded offers" else None
            row = dict(window=w, patch=r.patch, color=color, fit_on=r.fit_on, error="",
                       pseudo_card=r.pseudo_card, card_patch_id=r.card_patch_id, beta_saved=r.beta,
                       se_saved=r.se, z_saved=r.z, rarity=q.RARITY.get(r.pseudo_card, "none"))
            try:
                row.update(fit_fe(df, r.card_patch_id, r.pseudo_card, ("block^rar",),
                                  add=add_rarity, upgraded=up))
                row["z"] = row["beta"] / row["se"]
            except Exception as e:
                row["error"] = f"{type(e).__name__}: {e}"
            rows.append(row)
        if time_only:
            t = (time.time() - t0 - t_load) / len(rows)
            print(f"part 3b timing ({w}, {len(df):,} offers): load {t_load:.0f} s, {t:.2f} s per "
                  f"fit; 463 fits and 9 loads: about {(463 * t + 9 * t_load) / 60:.0f} min")
            return
        fits.add(w, rows)
        print(f"  {w}: {len(rows)} fits, {time.time() - t0:.0f} s", flush=True)


def part3b_table():
    f = Store("r_rarity_fits", RAR_COLS).read()
    ok = f[f.error.fillna("").eq("") & np.isfinite(f.z)]
    rows = []
    for patch, g in ok.groupby("patch"):
        g = g.reset_index(drop=True)
        t1 = tau_ci(g)
        t0 = tau_ci(g.assign(beta=g.beta_saved, se=g.se_saved))
        zs, zn = g.z_saved.to_numpy(), g.z.to_numpy()
        bt = cluster_boot(g.pseudo_card.to_numpy(), lambda i: robust_sd(zn[i]))
        rows.append(dict(patch=patch, n_pairs=len(g), n_failed=int((f.patch == patch).sum() - len(g)),
                         factor=q.FACTORS[patch], robust_sd_saved=robust_sd(zs),
                         robust_sd_block_x_rarity=robust_sd(zn), lo=pct(bt)[0], hi=pct(bt)[1],
                         sd_saved=zs.std(ddof=1), sd_block_x_rarity=zn.std(ddof=1),
                         tau_saved=t0[0], tau_saved_lo=t0[1], tau_saved_hi=t0[2],
                         tau_block_x_rarity=t1[0], tau_lo=t1[1], tau_hi=t1[2],
                         median_se_saved_pp=100 * g.se_saved.median(), median_se_pp=100 * g.se.median(),
                         corr_beta=np.corrcoef(g.beta, g.beta_saved)[0, 1],
                         mean_z_common_saved=zs[g.rarity == "Common"].mean(),
                         mean_z_common=zn[g.rarity == "Common"].mean()))
    return pd.DataFrame(rows)


SOURCE_SQL = """
SELECT character, card_id, source, build_id = $after AS after, count(*) AS n
FROM offers_with_version
WHERE list_contains([$before, $after], build_id) AND (build_id = $before OR start_time < $cutoff)
GROUP BY ALL
"""


def part3c(con):
    """Offers by source for the first patch's 20-card offer-rate tail (q_aside_first_offer_tail)
    against every other card of the same character, v0.99.1 against v0.103.2 weeks 0-3."""
    tail = pd.read_csv(f"{OUT}/q_aside_first_offer_tail.csv")
    old, new = q.REAL["first"]
    cutoff = q.release(new) + pd.Timedelta(seconds=4 * did.WEEK)
    n = con.execute(SOURCE_SQL, dict(before=old, after=new, cutoff=cutoff.to_pydatetime())).df()
    n["color"] = n.character.map(db.CHARS)
    n = n[(n.card_id.map(did.card_colors()) == n.color).to_numpy()]
    n["block"] = np.where(n.after, "after", "before")
    n["who"] = np.where(n.card_id.isin(tail.card_id), "tail cards", "other cards")
    rows = []

    def table(label, color, g, tot):
        """g: the group's offers; tot: all offers of the character(s), both by source, block."""
        gs = g.groupby(["source", "block"]).n.sum().unstack("block").reindex(
            columns=["before", "after"]).fillna(0)
        ts = tot.groupby(["source", "block"]).n.sum().unstack("block")[["before", "after"]]
        gs = gs.reindex(ts.index).fillna(0)
        share_b, share_a = gs.before.sum() / ts.before.sum(), gs.after.sum() / ts.after.sum()
        for src in ts.index:
            mix_b, mix_a = ts.before[src] / ts.before.sum(), ts.after[src] / ts.after.sum()
            in_b, in_a = gs.before[src] / ts.before[src], gs.after[src] / ts.after[src]
            rows.append(dict(
                group=label, color=color, source=src, offers_before=int(gs.before[src]),
                offers_after=int(gs.after[src]),
                source_share_of_group_before=gs.before[src] / gs.before.sum(),
                source_share_of_group_after=gs.after[src] / gs.after.sum(),
                source_share_of_all_offers_before=mix_b, source_share_of_all_offers_after=mix_a,
                group_share_within_source_before=in_b, group_share_within_source_after=in_a,
                log_ratio_within_source=np.log(in_a / in_b) if in_a > 0 and in_b > 0 else np.nan,
                # change of the group's overall share, split: within-source change at the mean
                # mix, and mix change at the mean within-source share
                contribution_within=(in_a - in_b) * (mix_a + mix_b) / 2,
                contribution_mix=(mix_a - mix_b) * (in_a + in_b) / 2,
                group_share_before=share_b, group_share_after=share_a))

    for color, tot in n.groupby("color"):
        if color not in set(tail.color):
            continue
        for who, g in tot.groupby("who"):
            table(who, color, g, tot)
        for card, g in tot[tot.who == "tail cards"].groupby("card_id"):
            table(card, color, g, tot)
    out = pd.DataFrame(rows)
    out["share_of_total_change"] = (out.contribution_within + out.contribution_mix) / (
        out.group_share_after - out.group_share_before)
    return out


# ------------------------------------------------------------------------------------- main

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", type=int, choices=(1, 2, 3), action="append", required=True)
    ap.add_argument("--time", action="store_true")
    ap.add_argument("--analyze", action="store_true")
    args = ap.parse_args()

    T0 = time.time()
    db.use_derived_colors()
    con = db.connect()
    q.patch_did(con)
    PAIRS = did.placebo_pairs(pd.read_parquet(q.PLACEBO))
    if len(PAIRS) != 463:
        raise SystemExit("placebo_h3 does not give 463 pairs")
    pd.set_option("display.width", 250, "display.max_columns", 60, "display.max_rows", 300,
                  "display.float_format", "{:.3f}".format)
    os.makedirs(OUT, exist_ok=True)
    save = lambda t, name: t.to_csv(f"{OUT}/{name}.csv", index=False)
    show = lambda name, t: print(name, t.to_string(index=False), sep="\n", flush=True)

    if 1 in args.part:
        PLAN = part1_plan(con)
        save(PLAN, "r_plan")
        if args.time:
            show("r_plan", PLAN.drop(columns=["old", "new"]))
        if not args.analyze:
            part1_fits(con, PLAN, time_only=args.time)
        if not args.time:
            UT, TESTS, CONTRAST, PH = part1_tables(PLAN)
            save(UT, "r_unit_tau"), save(TESTS, "r_dose_tests")
            save(CONTRAST, "r_within_boundary"), save(PH, "r_posthoc_boundary")
            show("r_posthoc_boundary", PH)
            show("r_unit_tau", UT[UT.status == "used"][
                ["boundary", "branch", "color", "dose", "n_text_only", "n_behavior", "boundary_dose",
                 "gap_days", "n_pairs", "tau_pp", "tau_lo", "tau_hi", "robust_sd_z", "median_se_pp"]])
            show("r_dose_tests", TESTS)
            print("r_within_boundary", CONTRAST.T.to_string(), sep="\n", flush=True)
    if 2 in args.part:
        if not args.analyze:
            part2_fits(con, PAIRS, time_only=args.time)
        if not args.time:
            show("r_token_windows", Store("r_token_windows", WIN_COLS).read())
            T2 = part2_tables()
            save(T2, "r_token_tau")
            print(T2.T.to_string(), flush=True)
    if 3 in args.part:
        if not args.analyze:
            part3b_fits(con, PAIRS, time_only=args.time)
        if not args.time:
            A, B, C = part3a(PAIRS), part3b_table(), part3c(con)
            save(A, "r_rarity_tau"), save(B, "r_rarity_tide"), save(C, "r_offer_sources")
            show("r_rarity_tau", A)
            print(B.T.to_string(), flush=True)
            show("r_offer_sources", C[C.group.isin(["tail cards", "other cards"])])

    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2 ** 30
    print(f"done in {time.time() - T0:.0f} s; peak RSS {rss:.1f} GB")
