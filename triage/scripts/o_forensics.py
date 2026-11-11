"""Section O (EXPLORATORY): forensics on the largest placebo misses.

Proposed after sections M and N were seen. Reads the final tables; changes no factor, number or
result. The rules and what each outcome means are in TRIAGE.md section O, written before this
ran. Uses the 463 one-per-pair placebo rows at weeks 0-3 (data/analysis/placebo_h3.parquet).

    python triage/scripts/o_forensics.py --check     # saved z back; uploader shares two ways
    python triage/scripts/o_forensics.py --part 1    # concentration of the excess
    python triage/scripts/o_forensics.py --part 2    # influence on the top 25 (about 35 min)
    python triage/scripts/o_forensics.py --part 3    # predicting misses (needs xgboost)
    python triage/scripts/o_forensics.py --part 4    # POST HOC, added after reading part 3:
                                                     # the same model on the features that set
                                                     # the SE, and on the rest

Run from the repository root. Output: triage/out_final/o_*.csv (TRIAGE_OUT overrides), keyed by
window and card. Uploaders appear as ranks within a card, never as hashes; no run IDs.
runs.duckdb is opened read-only. Colors are derived (db.py). Card type exists only in
reference/raw/cards.json: with TRIAGE_COLORS=reference it is read from there, otherwise the
feature is blank and left out of the model. Part 3 reads m_exposure_pairs.csv and n_slopes.csv
from the same output directory.

xgboost is in pyproject.toml's `forensics` extra. Where the environment can't be written,
FORENSICS_PYLIB names a directory holding it (pip install --target); it goes last on sys.path,
so the environment's own pandas and numpy are the ones used.

Part 1  o_concentration.csv, o_concentration_curve.csv, o_drop_top.csv
Part 2  o_top_pairs.csv (one row per top pair), o_influence.csv (one row per pair and slice),
        o_top_weekly.csv (weekly pick rate of each top card and its controls, for plotting)
Part 3  o_features.csv, o_cv.csv, o_transfer.csv, o_shap.csv
Part 4  o_posthoc_split.csv; from part 2's tables: o_posthoc_slices.csv (beta kept and delta z
        by slice over the top pairs), o_posthoc_step.csv (each top card's gap to its controls,
        before against after, next to its week-to-week sd before)
"""
import argparse
import json
import os
import pathlib
import resource
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, "triage/scripts")
import db  # noqa: E402
from spirometry import did  # noqa: E402

OUT = os.environ.get("TRIAGE_OUT", "triage/out_final")
PLACEBO = "data/analysis/placebo_h3.parquet"
WEEKS = 3
FACTOR_FIRST = 4.10
KEY = ["color", "before_builds", "after_builds"]
PAIR = KEY + ["fit_on", "pseudo_card"]
SEED, N_BOOT, N_SIM = 20261110, 2000, 10000
DROPS = (0, 5, 10, 20, 46)
N_TOP, N_UPLOADERS, Z_DRIVER = 25, 10, 2.0
BANDS = [("A0", 0, 0), ("A1-4", 1, 4), ("A5-8", 5, 8), ("A9-10", 9, 99)]      # as n_drift
RARITY_BUILDS = ["v0.99.1", "v0.103.2", "v0.107.1"]                           # as n_drift
PRE_BUILD = {"first": "v0.99.1", "second": "v0.103.2"}    # the build before the window with a slope
XGB = dict(max_depth=3, eta=0.05, subsample=0.8, colsample_bytree=0.8, min_child_weight=5,
           objective="reg:squarederror", nthread=1, verbosity=0)
N_TREES, N_FOLDS, N_SPLITS, N_PERM = 200, 5, 20, 200


def robust_sd(z):
    z = np.asarray(z, float)
    return 1.4826 * np.median(np.abs(z - np.median(z)))


# ---------------------------------------------------------------------------------- part 1

def top_share(z, frac=0.1):
    """Share of the total excess (z^2 - 1) carried by the top `frac` of pairs by z^2."""
    e = np.sort(np.asarray(z, float) ** 2)[::-1] - 1
    return e[:int(np.ceil(frac * len(e)))].sum() / e.sum()


def scopes(P):
    return [("pooled", P)] + [(p, g) for p, g in P.groupby("patch")]


def simulate(P):
    """Normal benchmark: every z normal with its patch's plain sd, same number of pairs.
    Returns an (N_SIM, n pairs) array in P's row order."""
    rng = np.random.default_rng(SEED)
    sd = P.patch.map(P.groupby("patch").z.std()).to_numpy()
    return rng.standard_normal((N_SIM, len(P))) * sd


def concentration(P):
    sim = simulate(P)
    rng = np.random.default_rng(SEED + 1)
    rows, curve = [], []
    for name, g in scopes(P):
        z = g.z.to_numpy()
        cols = np.flatnonzero(P.index.isin(g.index))
        row = dict(scope=name, n_pairs=len(g), robust_sd_z=robust_sd(z), sd_z=z.std(ddof=1),
                   mean_z2=(z ** 2).mean(), total_excess=(z ** 2 - 1).sum(),
                   share_abs_z_gt2=(np.abs(z) > 2).mean())
        for frac in (0.05, 0.1, 0.2):
            s = top_share(z, frac)
            b = np.array([top_share(r, frac) for r in sim[:, cols]])
            boot = [top_share(z[rng.integers(0, len(z), len(z))], frac) for _ in range(N_BOOT)]
            lo, hi = np.percentile(b, [2.5, 97.5])
            k = f"top{round(frac * 100):02d}"
            row.update({f"{k}_share": s, f"{k}_boot_lo": np.percentile(boot, 2.5),
                        f"{k}_boot_hi": np.percentile(boot, 97.5), f"{k}_normal": b.mean(),
                        f"{k}_normal_lo": lo, f"{k}_normal_hi": hi})
        s = row["top10_share"]
        row["rule_as_given"] = "tail-driven" if s > 0.5 else "broad" if s < 0.25 else "mixed"
        row["against_normal"] = ("heavier tails than a normal" if s > row["top10_normal_hi"] else
                                 "lighter" if s < row["top10_normal_lo"] else "a normal's")
        rows.append(row)
        o = g.assign(z2=g.z ** 2).sort_values("z2", ascending=False)
        o["rank"] = np.arange(1, len(o) + 1)
        o["pair_share"] = o["rank"] / len(o)
        o["cum_excess_share"] = (o.z2 - 1).cumsum() / (o.z2 - 1).sum()
        curve.append(o.assign(scope=name)[["scope", "rank", "pair_share", "cum_excess_share", "z2",
                                           "z", "patch", "color", "fit_on", "pseudo_card"]])
    return pd.DataFrame(rows), pd.concat(curve, ignore_index=True)


def drop_table(P):
    """sds of z after dropping the k pairs with the largest z^2 (pooled ranking), with the
    normal benchmark's mean for the same drop."""
    sim = simulate(P)
    order = np.argsort(-(P.z.to_numpy() ** 2))
    sim_order = np.argsort(-(sim ** 2), axis=1)
    first = (P.patch == "first").to_numpy()
    rows = []
    for k in DROPS:
        keep = np.ones(len(P), bool)
        keep[order[:k]] = False
        sim_keep = np.ones(sim.shape, bool)
        np.put_along_axis(sim_keep, sim_order[:, :k], False, axis=1)
        for name, m in (("pooled", np.ones(len(P), bool)), ("first", first), ("second", ~first)):
            z = P.z.to_numpy()[keep & m]
            b = [(robust_sd(r[kk & m]), r[kk & m].std(ddof=1)) for r, kk in zip(sim[:2000], sim_keep)]
            b = np.array(b)
            rows.append(dict(dropped=k, scope=name, n_left=len(z), n_dropped=int((~keep & m).sum()),
                             robust_sd_z=robust_sd(z), sd_z=z.std(ddof=1),
                             share_abs_z_gt2=(np.abs(z) > 2).mean(),
                             normal_robust_sd=b[:, 0].mean(), normal_sd=b[:, 1].mean(),
                             normal_n_dropped=float((~sim_keep[:, m]).sum(axis=1).mean())))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------- part 2

def fit_kw(fit_on):
    return dict(max_week_after=WEEKS, **({"upgraded": True} if fit_on == "upgraded offers" else {}))


def band_of(asc):
    out = pd.Series("", index=asc.index, dtype=object)
    for name, lo, hi in BANDS:
        out[(asc >= lo) & (asc <= hi)] = name
    return out


def slices(df, d):
    """(kind, label, rows of df to remove) for one top pair; d is its fit data."""
    card = d[d.is_treated]
    top = card.uploader_hash.value_counts()
    top = top[top > 0].index[:N_UPLOADERS]
    out = [("uploader", f"uploader rank {i + 1}", df.uploader_hash == h) for i, h in enumerate(top)]
    out += [("uploader", "no token", df.uploader_hash.isna()),
            ("tag", "untagged", df.group == "untagged"), ("tag", "tagged", df.group == "tagged")]
    before = df.block == "before"
    for w in sorted(card.week[~card.after & (card.week < 0)].unique()):
        out.append(("week", f"before, week {w}", before & (df.week == w)))
    out.append(("week", "before, played after release", before & (df.week >= 0)))
    for w in range(WEEKS + 1):
        out.append(("week", f"after, week {w}", ~before & (df.week == w)))
    band = band_of(df.ascension)
    out += [("ascension", name, band == name) for name, _, _ in BANDS]
    return out


def weekly(d, key):
    """Offers and pick rate by block and week: the card, and its controls pooled and as the
    mean of card rates."""
    d = d.assign(week=d.week.astype(int))
    g = d.groupby(["is_treated", "block", "week", "card_id"], observed=True).picked.agg(["size", "sum"])
    g = g.reset_index()
    rows = []
    for (blk, w), c in g.groupby(["block", "week"], observed=True):
        t, ctl = c[c.is_treated], c[~c.is_treated]
        rows.append(dict(key, block=blk, week=w, card_offers=int(t["size"].sum()),
                         card_picks=int(t["sum"].sum()),
                         card_rate=t["sum"].sum() / t["size"].sum() if len(t) else np.nan,
                         control_offers=int(ctl["size"].sum()),
                         control_rate_pooled=ctl["sum"].sum() / ctl["size"].sum() if len(ctl) else np.nan,
                         control_rate_card_mean=(ctl["sum"] / ctl["size"]).mean(),
                         n_control_cards=len(ctl)))
    return rows


def influence(con, P, raw, only=None):
    top = P.assign(abs_z=P.z.abs()).nlargest(N_TOP, "abs_z")
    top["rank"] = np.arange(1, len(top) + 1)
    if only:
        top = top.head(only)
    saved = raw.set_index(["card_patch_id", "pseudo_card"]).z
    rows, weeks, summary = [], [], []
    for (color, before, after), g in top.groupby(KEY, sort=False):
        df = did.load_block_data(con, color, before, after)
        for r in g.itertuples():
            t0 = time.time()
            kw = fit_kw(r.fit_on)
            key = dict(rank=r.rank, patch=r.patch, color=color, window=r.window, fit_on=r.fit_on,
                       pseudo_card=r.pseudo_card)
            base = did.placebo_fit(df, r.card_patch_id, r.pseudo_card, **kw)
            z0 = base["beta"] / base["se"]
            # 1e-4, not 1e-6: with derived colors a window can lose a control card with a
            # couple of offers (Haunt: 69 controls against 71, 2 offers of 1.16 million, |dz| 9e-6)
            if abs(z0 - saved[(r.card_patch_id, r.pseudo_card)]) > 1e-4:
                raise SystemExit(f"{r.pseudo_card}: refit z {z0} is not the saved z")
            d, _ = did._subset(df, r.card_patch_id, pseudo=r.pseudo_card, **kw)
            card_rows = d.index[d.is_treated]
            weeks += weekly(d, key)
            mine = []
            for kind, label, mask in slices(df, d):
                share = float(mask.reindex(card_rows).mean())
                row = dict(key, kind=kind, slice=label, card_offer_share=share, z_base=z0,
                           beta_base=base["beta"], se_base=base["se"], error="")
                try:
                    f = did.placebo_fit(df[~mask.to_numpy()], r.card_patch_id, r.pseudo_card, **kw)
                    z = f["beta"] / f["se"]
                    row.update(beta=f["beta"], se=f["se"], z=z, delta_z=z - z0,
                               z_beta_fixed=base["beta"] / f["se"],
                               n_treated_offers=f["n_treated_offers"])
                    row["driver"] = abs(z) < Z_DRIVER
                    row["driver_kind"] = ("" if not row["driver"] else "precision only"
                                          if abs(row["z_beta_fixed"]) < Z_DRIVER else "of beta")
                except Exception as e:                  # e.g. no offers left in a block
                    row["error"] = f"{type(e).__name__}: {e}"
                mine.append(row)
            rows += mine
            m = pd.DataFrame(mine)
            ok = m[m.error == ""]
            big = ok.loc[ok.delta_z.abs().idxmax()]
            drv = ok[ok.driver_kind == "of beta"]
            summary.append(dict(
                key, z_pair=r.z, z_first_tweak=z0, beta_pp=100 * base["beta"],
                se_pp=100 * base["se"], n_treated_offers=base["n_treated_offers"],
                n_slices=len(m), n_failed=int((m.error != "").sum()),
                largest_abs_delta_z=abs(big.delta_z), largest_slice=big.slice,
                largest_kind=big.kind, largest_share=big.card_offer_share, z_without_it=big.z,
                z_beta_fixed_without_it=big.z_beta_fixed,
                n_drivers_rule=int(ok.driver.sum()), n_drivers_of_beta=len(drv),
                drivers_precision_only=" | ".join(ok.slice[ok.driver_kind == "precision only"]),
                drivers_of_beta=" | ".join(drv.slice),
                min_abs_z_any_slice=ok.z.abs().min(),
                top_uploader_share=float(m.card_offer_share[m.slice == "uploader rank 1"].max())
                if (m.slice == "uploader rank 1").any() else 0.0))
            print(f"  {r.rank:2d} {r.patch} {color} {r.pseudo_card}: z {z0:+.2f}, {len(m)} slices, "
                  f"largest |dz| {abs(big.delta_z):.2f} ({big.slice}), drivers of beta "
                  f"{len(drv)}, {time.time() - t0:.0f} s", flush=True)
        del df
    return pd.DataFrame(summary), pd.DataFrame(rows), pd.DataFrame(weeks)


# ---------------------------------------------------------------------------------- part 3

SHARE_SQL = """
SELECT o.card_id, r.uploader_hash AS u, o.uploader_tag IS NOT NULL AS tagged, count(*) AS n
FROM offers_with_version o JOIN runs r USING (run_hash)
WHERE o.character = $character AND list_contains($builds, o.build_id)
  AND list_contains($pseudo, o.card_id) AND o.ascension IS NOT NULL
  AND (NOT list_contains($after, o.build_id) OR o.start_time < $cutoff)
  AND (o.upgraded OR NOT $upgraded_only)
GROUP BY ALL
"""
RARITY_SQL = """
SELECT character, card_id, count(*) AS n FROM offers_with_version
WHERE list_contains(?, build_id) AND ascension IS NOT NULL GROUP BY ALL
"""


def uploader_shares(con, P):
    """Per pair, on the offers its fit uses: the largest token's share, the top 10's, and the
    shares without a token and without the SlayTheStats tag."""
    out = []
    for (color, before, after, fit_on), g in P.groupby(KEY + ["fit_on"], sort=False):
        b, a = before.split(), after.split()
        cutoff = did.release_date(a[0]) + pd.Timedelta(seconds=(WEEKS + 1) * did.WEEK)
        n = con.execute(SHARE_SQL, dict(
            character=did._character(color), builds=b + a, after=a, cutoff=cutoff.to_pydatetime(),
            pseudo=sorted(g.pseudo_card.unique()), upgraded_only=fit_on == "upgraded offers")).df()
        for card, c in n.groupby("card_id"):
            tot = c.n.sum()
            by = c.dropna(subset=["u"]).groupby("u").n.sum().sort_values(ascending=False)
            out.append(dict(color=color, before_builds=before, after_builds=after, fit_on=fit_on,
                            pseudo_card=card, share_offers=int(tot),
                            top_uploader_share=by.iloc[0] / tot if len(by) else 0.0,
                            top10_uploader_share=by.iloc[:10].sum() / tot,
                            no_token_share=c.n[c.u.isna()].sum() / tot,
                            untagged_share=c.n[~c.tagged].sum() / tot))
    return pd.DataFrame(out)


def derive_rarity(con):
    """n_drift.derive_rarity: tier by offers relative to the character's most offered card."""
    n = con.execute(RARITY_SQL, [RARITY_BUILDS]).df()
    n["color"] = n.character.str.replace("CHARACTER.", "", regex=False).str.lower()
    n = n[(n.card_id.map(did.card_colors()) == n.color).to_numpy()]
    r = n.n / n.groupby("color").n.transform("max")
    n["rarity"] = np.select([r >= 0.6, r >= 0.25], [0, 1], 2)        # Common, Uncommon, Rare
    return n.set_index("card_id").rarity


def card_types():
    if os.environ.get("TRIAGE_COLORS") != "reference":
        return {}
    cards = json.loads(pathlib.Path("reference/raw/cards.json").read_bytes())
    return {c["id"]: c.get("type") or "" for c in cards}


def behavior_events(before, after):
    """card -> number of behavior events that appear after the window's first build."""
    builds = before.split() + after.split()
    cv = did._csv("reference/card_versions.csv")
    cv = cv[cv.build_id.isin(builds)]
    out = {}
    for card, g in cv.groupby("card_id", sort=False):
        rows = dict(zip(g.build_id, g.behavior_event_ids))
        if builds[0] not in rows:
            continue
        start = set(rows[builds[0]].split())
        new = set().union(*(set(rows[b].split()) for b in builds[1:] if b in rows)) - start
        out[card] = len(new)
    return out


def features(con, P):
    F = P[PAIR + ["patch", "z", "beta", "se", "treated_rate_before", "pseudo_offers_before",
                  "pseudo_offers_after", "n_treated_offers"]].copy()
    F["z2"], F["abs_z"], F["beta2_pp"] = F.z ** 2, F.z.abs(), (100 * F.beta) ** 2
    for c in did.CHARACTER_COLORS:
        F[f"char_{c}"] = (F.color == c).astype(float)
    F["rarity"] = F.pseudo_card.map(derive_rarity(con)).astype(float)
    types = card_types()
    F["type"] = F.pseudo_card.map(types) if types else ""
    for t in sorted(set(types.values()) - {""}):
        F[f"type_{t.lower()}"] = (F.type == t).astype(float)
    F["base_rate"] = F.treated_rate_before
    F["log_offers_before"] = np.log(F.pseudo_offers_before)
    F["log_offers_after"] = np.log(F.pseudo_offers_after)
    s = pd.read_csv(f"{OUT}/n_slopes.csv")
    s = s[(s.scale == "pp") & (s.horizon == "matched")]
    s = s.assign(lack_of_fit=s.chi2 / (s.n_weeks - 2).clip(lower=1))
    s = s.rename(columns=dict(card_id="pseudo_card", dev="slope_dev", build="pre_build"))
    F["pre_build"] = F.patch.map(PRE_BUILD)
    F = F.merge(s[["pre_build", "color", "pseudo_card", "slope_dev", "lack_of_fit"]],
                on=["pre_build", "color", "pseudo_card"], how="left")
    F["slope_abs"] = F.slope_dev.abs()
    m = pd.read_csv(f"{OUT}/m_exposure_pairs.csv")
    F = F.merge(m[PAIR + ["signed_exposure_after", "screen_subst_after", "run_subst_after"]],
                on=PAIR, how="left")
    F["behavior_flag"], F["n_behavior_events"] = 0.0, 0.0
    for (before, after), g in F.groupby(["before_builds", "after_builds"]):
        _, flagged = did.window_changes(before, after)
        n_ev = behavior_events(before, after)
        F.loc[g.index, "behavior_flag"] = g.pseudo_card.isin(flagged).astype(float)
        F.loc[g.index, "n_behavior_events"] = g.pseudo_card.map(n_ev).fillna(0).astype(float)
    F = F.merge(uploader_shares(con, P), on=PAIR, how="left")
    F["fit_upgraded"] = (F.fit_on == "upgraded offers").astype(float)
    return F


def feature_names(F):
    cols = [f"char_{c}" for c in did.CHARACTER_COLORS] + ["rarity"]
    cols += [c for c in F.columns if c.startswith("type_")]
    cols += ["base_rate", "log_offers_before", "log_offers_after", "slope_dev", "slope_abs",
             "lack_of_fit", "signed_exposure_after", "screen_subst_after", "run_subst_after",
             "behavior_flag", "n_behavior_events", "top_uploader_share", "top10_uploader_share",
             "no_token_share", "untagged_share", "fit_upgraded"]
    return cols


def xgb_fit(X, y, seed):
    return xgb.train(dict(XGB, seed=seed), xgb.DMatrix(X, label=y), N_TREES)


def cv_r2(X, y, groups, seed):
    """Grouped K-fold R^2 out of fold: 1 - SSE / SST, SST around each training fold's mean."""
    rng = np.random.default_rng(seed)
    ids = np.unique(groups)
    fold = dict(zip(rng.permutation(ids), np.arange(len(ids)) % N_FOLDS))
    f = np.array([fold[g] for g in groups])
    sse = sst = 0.0
    for k in range(N_FOLDS):
        tr, te = f != k, f == k
        pred = xgb_fit(X[tr], y[tr], seed).predict(xgb.DMatrix(X[te]))
        sse += ((y[te] - pred) ** 2).sum()
        sst += ((y[te] - y[tr].mean()) ** 2).sum()
    return 1 - sse / sst


def cv_table(F, cols):
    rows = []
    rng = np.random.default_rng(SEED + 3)
    patch_only = (F.patch == "second").to_numpy(float)[:, None]
    for target in ("z2", "abs_z", "beta2_pp"):
        for scope, g in scopes(F):
            X, y, grp = g[cols].to_numpy(float), g[target].to_numpy(float), g.pseudo_card.to_numpy()
            r2 = [cv_r2(X, y, grp, SEED + i) for i in range(N_SPLITS)]
            patch = g.patch.to_numpy()
            null = []
            for i in range(N_PERM):                     # target shuffled within patch
                yp = y.copy()
                for p in np.unique(patch):
                    idx = np.flatnonzero(patch == p)
                    yp[idx] = y[rng.permutation(idx)]
                null.append(cv_r2(X, yp, grp, SEED + 1000 + i))
            row = dict(target=target, scope=scope, model="declared features", n_pairs=len(g),
                       n_cards=len(set(grp)), n_features=len(cols), cv_r2=np.mean(r2),
                       cv_r2_min=np.min(r2), cv_r2_max=np.max(r2), null_mean=np.mean(null),
                       null_q95=np.percentile(null, 95),
                       p_perm=(1 + np.sum(np.array(null) >= np.mean(r2))) / (1 + N_PERM))
            rows.append(row)
            if scope == "pooled":
                r2p = [cv_r2(patch_only, y, grp, SEED + i) for i in range(N_SPLITS)]
                rows.append(dict(target=target, scope=scope, model="patch only", n_pairs=len(g),
                                 n_cards=len(set(grp)), n_features=1, cv_r2=np.mean(r2p),
                                 cv_r2_min=np.min(r2p), cv_r2_max=np.max(r2p)))
            print(pd.DataFrame(rows).tail(2).to_string(index=False), flush=True)
    return pd.DataFrame(rows)


def spearman(a, b):
    return pd.Series(a).rank().corr(pd.Series(b).rank())


def transfer(F, cols):
    """Train on the first patch, score the second with no refit."""
    a, b = F[F.patch == "first"], F[F.patch == "second"].reset_index(drop=True)
    new = ~b.pseudo_card.isin(a.pseudo_card).to_numpy()
    rng = np.random.default_rng(SEED + 4)
    rows = []
    for target in ("z2", "abs_z", "beta2_pp"):
        model = xgb_fit(a[cols].to_numpy(float), a[target].to_numpy(float), SEED)
        pred = model.predict(xgb.DMatrix(b[cols].to_numpy(float)))
        y = b[target].to_numpy(float)
        for name, m in (("all second-patch pairs", np.ones(len(b), bool)),
                        ("cards not in the first patch", new), ("cards in both patches", ~new)):
            idx = pd.Series(np.flatnonzero(m)).groupby(b.pseudo_card.to_numpy()[m]).apply(np.array)
            idx = idx.tolist()
            boot = []
            for _ in range(N_BOOT):
                take = np.concatenate([idx[i] for i in rng.integers(0, len(idx), len(idx))])
                boot.append(spearman(pred[take], y[take]))
            lo, hi = np.nanpercentile(boot, [2.5, 97.5])
            rows.append(dict(
                target=target, scored_on=name, n_pairs=int(m.sum()), n_cards=len(idx),
                spearman=spearman(pred[m], y[m]), spearman_lo=lo, spearman_hi=hi,
                transfer=bool(lo > 0),
                r2_no_refit=1 - ((y[m] - pred[m]) ** 2).sum() / ((y[m] - y[m].mean()) ** 2).sum(),
                mean_predicted=pred[m].mean(), mean_actual=y[m].mean()))
    return pd.DataFrame(rows)


def shap_table(F, cols):
    rows = []
    X = F[cols].to_numpy(float)
    for target in ("z2", "abs_z", "beta2_pp"):
        model = xgb_fit(X, F[target].to_numpy(float), SEED)
        s = model.predict(xgb.DMatrix(X), pred_contribs=True)[:, :-1]
        for j, c in enumerate(cols):
            rows.append(dict(target=target, feature=c, mean_abs_shap=np.abs(s[:, j]).mean(),
                             share=np.abs(s[:, j]).mean() / np.abs(s).mean(axis=0).sum(),
                             spearman_value_shap=spearman(X[:, j], s[:, j]),
                             n_missing=int(np.isnan(X[:, j]).sum())))
    out = pd.DataFrame(rows)
    return out.sort_values(["target", "mean_abs_shap"], ascending=[True, False])


PRECISION = ["base_rate", "log_offers_before", "log_offers_after", "fit_upgraded"]


def posthoc_split(F, cols):
    """POST HOC. CV R^2 and first-to-second transfer for the features that set the SE (offers,
    base rate, upgraded-offers fit) and for the declared features without them."""
    rows = []
    sets = [("declared features", cols), ("precision only", PRECISION),
            ("declared without precision", [c for c in cols if c not in PRECISION])]
    for name, cs in sets:
        tr = transfer(F, cs)
        tr = tr[tr.scored_on == "all second-patch pairs"].set_index("target")
        for target in ("z2", "abs_z", "beta2_pp"):
            row = dict(features=name, n_features=len(cs), target=target)
            for scope, g in scopes(F):
                X, y = g[cs].to_numpy(float), g[target].to_numpy(float)
                r2 = [cv_r2(X, y, g.pseudo_card.to_numpy(), SEED + i) for i in range(N_SPLITS)]
                row[f"cv_r2_{scope}"] = np.mean(r2)
            t = tr.loc[target]
            row.update(transfer_spearman=t.spearman, transfer_lo=t.spearman_lo,
                       transfer_hi=t.spearman_hi)
            rows.append(row)
    return pd.DataFrame(rows)


def posthoc_slices():
    """POST HOC. Per slice label over the top pairs: share of the card's offers, beta kept
    (refit beta / baseline beta) and delta z. Tokens are pooled as one row."""
    i = pd.read_csv(f"{OUT}/o_influence.csv")
    i = i[i.error.isna()].assign(beta_kept=lambda d: d.beta / d.beta_base,
                                 abs_dz=lambda d: d.delta_z.abs(), abs_z=lambda d: d.z.abs())
    i["slice"] = i.slice.where(~i.slice.str.startswith("uploader rank"), "any one token (top 10)")
    g = i.groupby(["kind", "slice"], sort=False)
    return g.agg(n=("z", "size"), median_share=("card_offer_share", "median"),
                 max_share=("card_offer_share", "max"), median_beta_kept=("beta_kept", "median"),
                 min_beta_kept=("beta_kept", "min"), max_beta_kept=("beta_kept", "max"),
                 median_delta_z=("delta_z", "median"), max_abs_delta_z=("abs_dz", "max"),
                 min_abs_z=("abs_z", "min"), n_below_2=("driver", "sum")).reset_index()


def posthoc_step():
    """POST HOC. Per top card: its weekly gap to the controls' pooled rate; the offer-weighted
    mean gap after minus before (before-build offers played after the release left out), the
    sd of the weekly gap before, and the gap in the first and last week of each block."""
    w = pd.read_csv(f"{OUT}/o_top_weekly.csv")
    w = w[(w.block == "after") | (w.week < 0)].assign(gap=lambda d: d.card_rate - d.control_rate_pooled)
    rows = []
    for (rank, card, patch), g in w.groupby(["rank", "pseudo_card", "patch"]):
        b, a = g[g.block == "before"].sort_values("week"), g[g.block == "after"].sort_values("week")
        step = np.average(a.gap, weights=a.card_offers) - np.average(b.gap, weights=b.card_offers)
        rows.append(dict(rank=rank, patch=patch, pseudo_card=card, weeks_before=len(b),
                         gap_before_first=b.gap.iloc[0], gap_before_last=b.gap.iloc[-1],
                         gap_after_week0=a.gap.iloc[0], gap_after_week3=a.gap.iloc[-1],
                         step=step, sd_weekly_gap_before=b.gap.std(),
                         step_over_sd=abs(step) / b.gap.std(),
                         last_before_to_week0=a.gap.iloc[0] - b.gap.iloc[-1],
                         share_of_step_in_week0=(a.gap.iloc[0] - b.gap.iloc[-1]) / step))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------- main

def check(con, P, raw):
    """Saved z back through this script's fit path, and the SQL uploader shares against the
    same shares counted in the fit data."""
    pick = pd.concat([P[P.patch == p].assign(a=lambda d: d.z.abs()).nlargest(1, "a")
                      for p in ("first", "second")])
    sh = uploader_shares(con, pick).set_index(["before_builds", "pseudo_card"])
    for r in pick.itertuples():
        df = did.load_block_data(con, r.color, r.before_builds, r.after_builds)
        kw = fit_kw(r.fit_on)
        f = did.placebo_fit(df, r.card_patch_id, r.pseudo_card, **kw)
        z = raw.z[(raw.card_patch_id == r.card_patch_id) & (raw.pseudo_card == r.pseudo_card)].iloc[0]
        d, _ = did._subset(df, r.card_patch_id, pseudo=r.pseudo_card, **kw)
        c = d[d.is_treated]
        top = c.uploader_hash.value_counts().iloc[0] / len(c)
        unt = (c.group == "untagged").mean()
        s = sh.loc[(r.before_builds, r.pseudo_card)]
        print(f"{r.pseudo_card}: |dz| {abs(f['beta'] / f['se'] - z):.1e}; offers {len(c)} / "
              f"{s.share_offers}; top uploader {top:.5f} / {s.top_uploader_share:.5f}; untagged "
              f"{unt:.5f} / {s.untagged_share:.5f}", flush=True)
        if (abs(f["beta"] / f["se"] - z) > 1e-6 or len(c) != s.share_offers
                or abs(top - s.top_uploader_share) > 1e-9 or abs(unt - s.untagged_share) > 1e-9):
            raise SystemExit("check failed")
    assert abs(top_share(np.r_[np.full(9, 1.0), 3.0]) - 1.0) < 1e-12      # all excess in one pair
    rng = np.random.default_rng(0)
    assert abs(top_share(4.1 * rng.standard_normal(2_000_000)) - 0.4608) < 0.003
    print("top_share: ok")


ap = argparse.ArgumentParser()
ap.add_argument("--check", action="store_true")
ap.add_argument("--part", type=int, choices=[1, 2, 3, 4], action="append")
ap.add_argument("--only", type=int, help="part 2: the first N of the top pairs (a dry run)")
args = ap.parse_args()

T0 = time.time()
db.use_derived_colors()
con = db.connect()
RAW = pd.read_parquet(PLACEBO)
PAIRS = did.placebo_pairs(RAW)
if len(PAIRS) != 463 or round(robust_sd(PAIRS.z[PAIRS.patch == "first"]), 2) != FACTOR_FIRST:
    raise SystemExit("placebo_h3 does not give 463 pairs and the 4.10 factor")
pd.set_option("display.width", 250, "display.max_columns", 40, "display.max_rows", 400,
              "display.float_format", "{:.3f}".format)
os.makedirs(OUT, exist_ok=True)
parts = set(args.part or [])

if args.check:
    check(con, PAIRS, RAW)
if 1 in parts:
    C, CURVE = concentration(PAIRS)
    D = drop_table(PAIRS)
    C.to_csv(f"{OUT}/o_concentration.csv", index=False)
    CURVE.to_csv(f"{OUT}/o_concentration_curve.csv", index=False)
    D.to_csv(f"{OUT}/o_drop_top.csv", index=False)
    print(C.T.to_string(), D.to_string(index=False), sep="\n", flush=True)
if 2 in parts:
    S, I, W = influence(con, PAIRS, RAW, args.only)
    tag = "_dry" if args.only else ""
    S.to_csv(f"{OUT}/o_top_pairs{tag}.csv", index=False)
    I.to_csv(f"{OUT}/o_influence{tag}.csv", index=False)
    W.to_csv(f"{OUT}/o_top_weekly{tag}.csv", index=False)
    print(S.to_string(index=False), flush=True)
if parts & {3, 4}:
    try:
        import xgboost as xgb
    except ImportError:
        sys.path.append(os.environ["FORENSICS_PYLIB"])
        import xgboost as xgb
    F = features(con, PAIRS)
    COLS = feature_names(F)
if 3 in parts:
    F.drop(columns=["z", "beta", "se", "treated_rate_before"]).to_csv(
        f"{OUT}/o_features.csv", index=False)
    print("features:", COLS)
    print(F[COLS].describe().T[["count", "mean", "std", "min", "max"]].to_string(), flush=True)
    CV = cv_table(F, COLS)
    CV.to_csv(f"{OUT}/o_cv.csv", index=False)
    TR = transfer(F, COLS)
    TR.to_csv(f"{OUT}/o_transfer.csv", index=False)
    SH = shap_table(F, COLS)
    SH.to_csv(f"{OUT}/o_shap.csv", index=False)
    print(CV.to_string(index=False), TR.to_string(index=False), SH.to_string(index=False),
          sep="\n", flush=True)

if 4 in parts:
    PS = posthoc_split(F, COLS)
    PS.to_csv(f"{OUT}/o_posthoc_split.csv", index=False)
    print(PS.to_string(index=False), flush=True)
    for name, tab in (("o_posthoc_slices", posthoc_slices()), ("o_posthoc_step", posthoc_step())):
        tab.to_csv(f"{OUT}/{name}.csv", index=False)
        print(name, tab.to_string(index=False), sep="\n", flush=True)

rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2 ** 30
print(f"done in {time.time() - T0:.0f} s; peak RSS {rss:.1f} GB")
