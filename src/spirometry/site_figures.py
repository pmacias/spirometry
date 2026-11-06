"""Website figures and data export from notebook 02's saved fits.

Everything here reads the saved results in data/analysis/ (did_main, did_h3, the weeks 0-3
checks, event_studies, offer_rate, second_patch_checks_h3, anticipation_main); nothing is
refit. The one exception is `weekly_cells`, which needs a window's offers
(did.load_block_data) for the raw per-week counts behind each event-study cell.

    saved = load_saved(ROOT / "data" / "analysis")
    nerf, steps = pick_nerf(saved)                  # the selection rules, with the filter counts
    null, steps = pick_null(saved)
    cells = weekly_cells(df, "PARRY@v0.103.2/patch", saved["es"])
    entry = card_entry(saved, "PARRY@v0.103.2/patch", cells, change_text=..., tweaks=TW)
    fig = plot_event_study_site(cells, entry, title=...)

Weeks 0-3 is the primary horizon (PLAN.md decision log, 2026-10-09), so every headline
number is the h3 fit. The event study itself runs over all after weeks, binned at -6 and 8.
"""
import numpy as np
import pandas as pd
from scipy import stats

from spirometry import did

HORIZON = 3                     # weeks 0-3: the headline horizon
HORIZON_LABEL = f"weeks 0–{HORIZON}"
WEEKS = (-6, 8)                 # fit_event_study's default bins
MIN_OFFERS = 100                # hide event-study cells with fewer treated offers (as notebook 02)
FIRST_BEFORE = "v0.99.1"        # the first patch's before block; anything else is the second
# Robust placebo sd by patch at weeks 0-3: SPIROMETRY.md, "Weeks 0–3 placebos" and the
# calibrated counts in "Phase 5 results". Multiplies a clustered SE as it divides a z.
# index.html's CAL (website repo) must match; scripts/site_publish.sh checks that it does.
PLACEBO_FACTORS_H3 = {"first": 4.10, "second": 2.67}
CAL_Z = 2                       # calibrated |z| cutoff: the calibrated counts' rule

H3_CHECKS = ["pooled_groups", "tagged", "untagged", "drop_shared_screens",
             "drop_behavior_flags", "drop_top_uploaders", "picked_screens_only"]

# Site palette (navy page). OLD_BUILD is the muted light blue-grey for the before build.
SITE_STYLE = {
    "figure.facecolor": "#284a72", "axes.facecolor": "#284a72", "savefig.facecolor": "#284a72",
    "text.color": "#f3f6fa", "axes.labelcolor": "#c9d6e6",
    "xtick.color": "#8ea6c3", "ytick.color": "#8ea6c3",
    "axes.edgecolor": "#8ea6c3", "grid.color": "#3d6290",
}
ACCENT = "#ff9273"
OLD_BUILD = "#a9bccf"
NERF = "#a9cdf5"
MINUS = "−"


# ---- saved results -----------------------------------------------------------------------

def load_saved(analysis):
    """notebook 02's saved tables, keyed by short name; `checks_h3` maps check -> table."""
    a = analysis
    return {
        "main": pd.read_parquet(a / "did_main.parquet"),
        "h3": pd.read_parquet(a / f"did_h{HORIZON}.parquet"),
        "orc": pd.read_parquet(a / "offer_rate.parquet"),
        "es": pd.read_parquet(a / "event_studies.parquet"),
        "sp_h3": pd.read_parquet(a / f"second_patch_checks_h{HORIZON}.parquet"),
        "anticipation": pd.read_parquet(a / "anticipation_main.parquet"),
        "checks_h3": {c: pd.read_parquet(a / f"did_h{HORIZON}_{c}.parquet") for c in H3_CHECKS},
    }


def patch_of(before_builds):
    return "first" if before_builds == FIRST_BEFORE else "second"


def pretrend_summary(es):
    """notebook 02's screen: before-build cells with week < 0. chi2 = sum (coef/se)^2 (a
    screen: it ignores the shared reference week), slope = weighted fit of coef on week."""
    pre = es[(es.block == "before") & (es.week < 0)].dropna(subset=["coef", "se"])
    if len(pre) < 2:
        return dict(n_pre=len(pre), chi2=np.nan, p=np.nan, slope=np.nan, slope_se=np.nan)
    z2 = ((pre.coef / pre.se) ** 2).sum()
    w = 1 / pre.se ** 2
    xm = np.average(pre.week, weights=w)
    sxx = (w * (pre.week - xm) ** 2).sum()
    slope = (w * (pre.week - xm) * pre.coef).sum() / sxx
    return dict(n_pre=len(pre), chi2=z2, p=stats.chi2.sf(z2, len(pre)), slope=slope,
                slope_se=1 / np.sqrt(sxx))


def check_shifts(saved, cpid):
    """Each weeks 0-3 check against the weeks 0-3 fit: the check's beta, the shift in h3 se,
    and whether the sign differs. Second-patch tweaks add the before-block variants."""
    b, s = saved["h3"].loc[cpid, ["beta", "se"]]
    rows = [(name, t.loc[cpid, "beta"], t.loc[cpid, "se"], t.loc[cpid, "error"])
            for name, t in saved["checks_h3"].items() if cpid in t.index]
    sp = saved["sp_h3"]
    rows += [(f"before block: {r.variant}", r.beta, r.se, "")
             for r in sp[(sp.card_patch_id == cpid) & (sp.variant != "main")].itertuples()]
    out = pd.DataFrame(rows, columns=["check", "beta", "se", "error"])
    out["shift_in_se"] = (out.beta - b) / s
    out["sign_flip"] = np.sign(out.beta) != np.sign(b)
    return out


def selection_report(saved, cpids):
    """One row per card-patch: weeks 0-3 and all-weeks beta with 95% CI (points), the
    pre-trend screen, the offer-rate z's and flags, and the weeks 0-3 checks that move it
    more than 2 se or flip its sign."""
    rows = []
    for cpid in cpids:
        h, m, o = saved["h3"].loc[cpid], saved["main"].loc[cpid], saved["orc"].loc[cpid]
        pre = pretrend_summary(saved["es"][saved["es"].card_patch_id == cpid])
        ch = check_shifts(saved, cpid)
        big = ch[ch.shift_in_se.abs() > 2]
        rows.append({
            "card_patch_id": cpid, "patch": patch_of(h.before_builds),
            "beta_h3_pts": 100 * h.beta, "ci_h3": f"{100 * h.ci_lo:+.2f} .. {100 * h.ci_hi:+.2f}",
            "beta_all_pts": 100 * m.beta, "ci_all": f"{100 * m.ci_lo:+.2f} .. {100 * m.ci_hi:+.2f}",
            "pre_chi2": pre["chi2"], "pre_p": pre["p"], "pre_slope_pts": 100 * pre["slope"],
            "pre_slope_se_pts": 100 * pre["slope_se"],
            "z_spread": o.z_spread, "z_binom": o.z_binom, "offer_flag": bool(o.flag),
            "offer_flag_rarity": bool(o.flag_rarity),
            "checks_beyond_2se": "; ".join(f"{r.check} {r.shift_in_se:+.1f}"
                                           for r in big.itertuples()) or "none",
            "sign_flips": "; ".join(ch.check[ch.sign_flip]) or "none",
            "n_treated_offers_h3": int(h.n_treated_offers)})
    return pd.DataFrame(rows).set_index("card_patch_id")


def offer_flagged(orc):
    """The offer-rate check's flag against all controls or against same-rarity ones."""
    return orc.flag.astype(bool) | orc.flag_rarity.astype(bool)


def signed_dose(t):
    """direction x the change's sign, as notebook 02's forest plot: the upgrade change for
    upgrade-only tweaks, ln(new/old) otherwise. Positive = buff."""
    num = lambda s: pd.to_numeric(s.astype(str).str.replace("+", "", regex=False),
                                  errors="coerce")
    dose = np.where(t.upgrade_only == "yes", num(t.upgrade_new) - num(t.upgrade_old),
                    t.log_ratio)
    return t.direction * dose


def kind_of(t):
    """'rework' for mixed-direction tweaks (one number up, another down), else buff/nerf."""
    if t.mixed_direction == "yes":
        return "rework"
    return "buff" if float(signed_dose(t.to_frame().T).iloc[0]) > 0 else "nerf"


def _estimable(saved):
    h3 = saved["h3"]
    return h3[(h3.error == "") & (h3.solo_estimable == "yes")]


def _pretrend_p(saved, cpids):
    es = saved["es"]
    return pd.Series([pretrend_summary(es[es.card_patch_id == c])["p"] for c in cpids],
                     index=cpids, dtype=float)


def _steps(steps):
    return pd.DataFrame([{"filter": n, "n": len(d), "cards": ", ".join(d.card_id)}
                         for n, d in steps])


def pick_nerf(saved):
    """The cleanest first-patch nerf (rule fixed 2026-10-27): first-patch, solo-estimable,
    a nerf (not mixed), |beta_h3| > 2 se, pre-trend p > 0.05, no offer-rate flag, no sign
    flip in any weeks 0-3 check; the largest |beta_h3|. Returns (card_patch_id or None, the
    filter steps)."""
    t = _estimable(saved)
    t = t[t.before_builds == FIRST_BEFORE]
    steps = [("first-patch, solo-estimable", t)]
    t = t[(signed_dose(t) < 0) & (t.mixed_direction != "yes")]
    steps.append(("nerf (not mixed)", t))
    t = t[t.beta.abs() > 2 * t.se]
    steps.append(("|β| > 2 se (weeks 0–3)", t))
    t = t.loc[(_pretrend_p(saved, t.index) > 0.05).to_numpy()]
    steps.append(("pre-trend p > 0.05", t))
    t = t[~offer_flagged(saved["orc"]).reindex(t.index, fill_value=True)]
    steps.append(("no offer-rate flag", t))
    t = t.loc[np.array([not check_shifts(saved, c).sign_flip.any() for c in t.index],
                       dtype=bool)]
    steps.append(("no sign flip in a weeks 0–3 check", t))
    pick = t.beta.abs().idxmax() if len(t) else None
    return pick, _steps(steps)


def pick_null(saved):
    """The second-patch 'no clear change' card (stricter rule, fixed 2026-10-27):
    second-patch, solo-estimable, no offer-rate flag, |beta| < 2 se at weeks 0-3, at all
    weeks and with the pooled before block, and no anticipation gap beyond 2 se where that
    check is informative; then, as in the nerf rule (2026-10-27, for consistency), pre-trend
    p > 0.05 and no weeks 0-3 check (before-block variants included) moving it more than
    2 se; the most treated offers (weeks 0-3). Returns (card_patch_id or None, the filter
    steps)."""
    t = _estimable(saved)
    t = t[t.before_builds != FIRST_BEFORE]
    steps = [("second-patch, solo-estimable", t)]
    t = t[~offer_flagged(saved["orc"]).reindex(t.index, fill_value=True)]
    steps.append(("no offer-rate flag", t))
    t = t[t.beta.abs() < 2 * t.se]
    steps.append(("|β| < 2 se, weeks 0–3", t))
    m = saved["main"].reindex(t.index)
    t = t[(m.beta.abs() < 2 * m.se).to_numpy()]
    steps.append(("|β| < 2 se, all weeks", t))
    sp = saved["sp_h3"]
    pb = sp[sp.variant == "pooled before"].set_index("card_patch_id").reindex(t.index)
    t = t[(pb.beta.abs() < 2 * pb.se).to_numpy()]
    steps.append(("|β| < 2 se, pooled before block", t))
    an = saved["anticipation"]
    inf = an[an.status == "informative"].set_index("card_patch_id")
    gap = lambda c: c in inf.index and bool((inf.loc[[c]].beta_postbeta.abs()
                                              > 2 * inf.loc[[c]].se).any())
    t = t.loc[np.array([not gap(c) for c in t.index], dtype=bool)]
    steps.append(("no anticipation gap > 2 se (where informative)", t))
    t = t.loc[(_pretrend_p(saved, t.index) > 0.05).to_numpy()]
    steps.append(("pre-trend p > 0.05", t))
    t = t.loc[np.array([not (check_shifts(saved, c).shift_in_se.abs() > 2).any()
                        for c in t.index], dtype=bool)]
    steps.append(("no weeks 0–3 check moves it > 2 se", t))
    pick = t.n_treated_offers.idxmax() if len(t) else None
    return pick, _steps(steps)


def patch_summary(saved):
    """Per patch at weeks 0-3: median |beta| in points, tweaks clearly nonzero on the
    calibrated scale (|beta / se| / PLACEBO_FACTORS_H3 > 2, SPIROMETRY.md's calibrated
    counts), tweaks."""
    t = _estimable(saved)
    out = {}
    for patch, g in t.groupby(t.before_builds.map(patch_of)):
        out[patch] = {"median_abs_beta_pts": round(100 * float(g.beta.abs().median()), 2),
                      "n_clear": int((g.beta.abs() / g.se / PLACEBO_FACTORS_H3[patch] > 2).sum()),
                      "n": len(g)}
    return {k: out[k] for k in ("first", "second") if k in out}


# ---- per-week cells -----------------------------------------------------------------------

def es_cells(es, cpid):
    """The saved event study's cells for one card-patch, in weekly_cells' layout (no raw
    counts; offers = the treated offers), plus the reference cell (week -1, before; coef 0,
    no se, offers unknown). Enough for the figure."""
    e = es[es.card_patch_id == cpid][["week", "block", "coef", "se", "n_offers"]]
    e = e.rename(columns={"n_offers": "offers"}).assign(is_ref=False)
    ref_row = pd.DataFrame([{"week": -1, "block": "before", "coef": 0.0, "se": np.nan,
                             "offers": np.nan, "is_ref": True}])
    return pd.concat([ref_row, e], ignore_index=True)

def weekly_cells(df, cpid, es, *, upgraded=None, weeks=WEEKS, ref=did.REF):
    """One row per (week, block) cell of the treated card, as fit_event_study builds them:
    same subset (treated + controls, rows with an ascension), weeks binned into `weeks`.
    Raw counts (offers, picks, pick_rate, control_pick_rate) next to the saved event-study
    coef and se; the reference cell (week -1, before) has coef 0 and no se. Raises if the
    treated offers differ from the saved event study's n_offers (a different data build)."""
    d, treated = did._subset(df, cpid, upgraded=upgraded, ref=ref)
    d["wk"] = d.week.clip(*weeks).astype("int16")
    g = d.groupby(["wk", "block", "is_treated"], observed=True).picked.agg(["size", "sum"])
    g = g.reset_index()
    tr = g[g.is_treated].rename(columns={"size": "offers", "sum": "picks"})
    ct = g[~g.is_treated].rename(columns={"size": "c_offers", "sum": "c_picks"})
    cells = tr.drop(columns="is_treated").merge(ct.drop(columns="is_treated"),
                                                on=["wk", "block"], how="left")
    cells = cells.rename(columns={"wk": "week"})
    cells["block"] = cells.block.astype(str)
    cells["pick_rate"] = cells.picks / cells.offers
    cells["control_pick_rate"] = cells.c_picks / cells.c_offers
    e = es[es.card_patch_id == cpid][["week", "block", "coef", "se", "n_offers"]]
    cells = cells.merge(e, on=["week", "block"], how="left")
    is_ref = (cells.week == -1) & (cells.block == "before")
    cells.loc[is_ref, "coef"] = 0.0
    bad = cells[~is_ref & (cells.n_offers != cells.offers)]
    if len(bad):
        raise ValueError(f"{cpid}: treated offers differ from the saved event study in "
                         f"{len(bad)} cells (rebuilt run tables?)")
    cells["is_ref"] = is_ref
    return (cells.drop(columns=["n_offers", "c_offers", "c_picks"])
            .sort_values(["block", "week"], key=lambda s: s.map({"before": 0, "after": 1})
                         if s.name == "block" else s)
            .reset_index(drop=True))


# ---- JSON entries ---------------------------------------------------------------------------

def _num(x, nd):
    return None if pd.isna(x) else round(float(x), nd)


def _pts(x):
    """Points with a real minus sign, one decimal."""
    return f"{x:+.1f}".replace("-", MINUS)


def card_entry(saved, cpid, cells, *, change_text, tweaks, builds, name, kind=None,
               note=None, min_offers=MIN_OFFERS):
    """The JSON entry for one card-patch: headline at weeks 0-3, with the raw clustered CI
    (the site widens it at draw time, so don't widen it here), and the week cells
    (weekly_cells) with at least `min_offers` treated offers; cells=None leaves the
    weeks out. `tweaks` is tweak_sizes.csv indexed by card_patch_id, `builds` builds.csv
    indexed by build_id."""
    t = tweaks.loc[cpid]
    h = saved["h3"].loc[cpid]
    character = t.color.title()
    beta, lo, hi = (100 * h.beta, 100 * h.ci_lo, 100 * h.ci_hi)
    after = t.after_builds.split()[0]
    entry = {
        "card_patch_id": cpid, "name": name, "character": character,
        "patch": patch_of(t.before_builds),
        "builds": f"{t.before_builds} → {t.after_builds}",
        "release_date": builds.loc[after, "release_date"] or None,
        "change_text": change_text, "kind": kind or kind_of(t),
        "headline": {
            "horizon": HORIZON_LABEL, "beta_pts": _num(beta, 2), "ci_lo_pts": _num(lo, 2),
            "ci_hi_pts": _num(hi, 2),
            **{c: _num(h[c], 4) for c in ["treated_rate_before", "treated_rate_after",
                                          "control_rate_before", "control_rate_after"]},
            "n_controls": int(h.n_control_cards), "n_treated_offers": int(h.n_treated_offers)},
    }
    if note:
        entry["note"] = note
    if cells is None:                       # headline only (the figure needs no raw counts)
        return entry
    shown = cells[cells.offers >= min_offers]
    entry["weeks"] = [
        {"week": int(r.week), "block": r.block, "coef_pts": _num(100 * r.coef, 2),
         "se_pts": _num(100 * r.se, 2), "offers": int(r.offers), "picks": int(r.picks),
         "pick_rate": _num(r.pick_rate, 4), "control_pick_rate": _num(r.control_pick_rate, 4)}
        for r in shown.itertuples()]
    return entry


# ---- static figures --------------------------------------------------------------------------

def forest_table(saved, tweaks, names, *, patch="first", kinds=None):
    """One row per estimable tweak of a patch at weeks 0-3, upgrade-only tweaks dropped,
    sorted by estimate (largest first): name, kind (buff/nerf; `kinds` overrides by
    card_patch_id, and a rework left over raises), beta_pts, and lo_pts/hi_pts at
    +- CAL_Z placebo-scaled SEs, so `clear` is the calibrated count's rule. `names` maps
    card_id to display name."""
    kinds = kinds or {}
    t = _estimable(saved)
    t = t[t.before_builds.map(patch_of) == patch]
    t = t[tweaks.loc[t.index, "upgrade_only"] != "yes"]
    half = 100 * CAL_Z * t.se * PLACEBO_FACTORS_H3[patch]
    out = pd.DataFrame({
        "name": [names[tweaks.loc[c, "card_id"]] for c in t.index],
        "kind": [kinds.get(c) or kind_of(tweaks.loc[c]) for c in t.index],
        "beta_pts": 100 * t.beta, "lo_pts": 100 * t.beta - half, "hi_pts": 100 * t.beta + half},
        index=t.index)
    bad = out.index[~out.kind.isin(["buff", "nerf"])]
    if len(bad):
        raise ValueError(f"give these a buff or nerf in `kinds`: {list(bad)}")
    out["clear"] = (out.lo_pts > 0) | (out.hi_pts < 0)
    return out.sort_values("beta_pts", ascending=False)


def plot_forest_site(table, *, title, subtitle, xlabel):
    """Forest plot of forest_table's rows: buffs in ACCENT, nerfs in NERF, a line at 0.
    Text is 13 pt or more, about 10 pt on a 600 px wide page. Call inside
    plt.rc_context(SITE_STYLE). Returns the figure."""
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    colors = {"buff": ACCENT, "nerf": NERF}
    n = len(table)
    top_in, bottom_in, row_in = 1.2, 0.8, 0.29
    height = top_in + bottom_in + n * row_in
    fig, ax = plt.subplots(figsize=(8, height), dpi=200)
    y = np.arange(n)[::-1]
    c = table.kind.map(colors)
    ax.hlines(y, table.lo_pts, table.hi_pts, colors=c, lw=2.2, zorder=3)
    ax.scatter(table.beta_pts, y, c=c, s=52, zorder=4, linewidths=0)
    ax.axvline(0, color="#c9d6e6", lw=1.2, zorder=2)
    ax.grid(True, axis="x", lw=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.set_ylim(-0.7, n - 0.3)
    ax.set_yticks(y, table.name)
    ax.xaxis.set_major_locator(plt.MultipleLocator(10))
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:+.0f}".replace("-", MINUS) if v else "0")
    ax.tick_params(axis="y", labelsize=13, length=0, labelcolor="#f3f6fa")
    ax.tick_params(axis="x", labelsize=13, length=0)
    fig.subplots_adjust(left=0.235, right=0.97, top=1 - top_in / height,
                        bottom=bottom_in / height)
    fig.text(0.5, 0.2 / height, xlabel, ha="center", va="bottom", fontsize=13, color="#c9d6e6")
    fig.text(0.04, 1 - 0.14 / height, title, ha="left", va="top", fontsize=20,
             fontweight="bold")
    fig.text(0.04, 1 - 0.62 / height, subtitle, ha="left", va="top", fontsize=14,
             color="#c9d6e6")
    handles = [Line2D([], [], color=col, marker="o", ms=7, lw=2.2) for col in colors.values()]
    ax.legend(handles, list(colors), loc="upper left", frameon=False, fontsize=13,
              labelcolor="#f3f6fa", handletextpad=0.5)
    return fig



def plot_event_study_site(cells, entry, *, title, change_label, min_offers=MIN_OFFERS):
    """Site version of notebook 02's event-study plot for one card, in percentage points:
    old build in OLD_BUILD (squares), new build in ACCENT (circles), 95% clustered intervals
    (sampling error only), cells with fewer than `min_offers` treated offers hidden, the
    release as a dashed line, the weeks 0-3 estimate as a band across weeks 0-3 with its
    label. The band is the 95% interval widened by the patch's PLACEBO_FACTORS_H3 around
    the rounded beta, as index.html's calCI does. Call inside plt.rc_context(SITE_STYLE).
    Returns the figure."""
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    hd = entry["headline"]
    fig, ax = plt.subplots(figsize=(8, 6), dpi=200)
    ax.grid(True, axis="y", lw=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    # weeks 0-3 estimate: placebo-calibrated band and line across the headline weeks
    x0, x1 = -0.5, HORIZON + 0.5
    half = (hd["ci_hi_pts"] - hd["ci_lo_pts"]) / 2 * PLACEBO_FACTORS_H3[entry["patch"]]
    ax.fill_between([x0, x1], hd["beta_pts"] - half, hd["beta_pts"] + half, color=ACCENT,
                    alpha=0.18, lw=0, zorder=1)
    ax.plot([x0, x1], [hd["beta_pts"]] * 2, color=ACCENT, lw=1.5, alpha=0.7, zorder=1)

    c = cells[(cells.offers >= min_offers) | cells.is_ref]       # the reference is always 0
    builds = entry["builds"].split(" → ")
    for blk, color, marker, dx, lab in [
            ("before", OLD_BUILD, "s", -0.1, f"old build ({builds[0]})"),
            ("after", ACCENT, "o", 0.1, f"new build ({builds[1]})")]:
        e = c[(c.block == blk) & ~c.is_ref]
        ax.errorbar(e.week + dx, 100 * e.coef, yerr=196 * e.se, fmt=marker, ms=6.5,
                    color=color, ecolor=color, elinewidth=1.6, capsize=0, label=lab, zorder=3)
    r = c[c.is_ref]
    if len(r):
        ax.plot(r.week - 0.1, [0] * len(r), "s", ms=6.5, mfc="#284a72", mec=OLD_BUILD,
                mew=1.6, zorder=3, label="reference week (set to 0)")
    ax.axhline(0, color="#8ea6c3", lw=0.9, zorder=2)
    ax.axvline(-0.5, ymax=0.8, color="#c9d6e6", lw=1.1, ls="--", zorder=2)  # stops under the headline

    ymax = float((100 * (c.coef + 1.96 * c.se.fillna(0))).max()) if len(c) else 1.0
    top = ymax + 13                         # headroom for the headline above the data
    ax.set_ylim(min(-4, ax.get_ylim()[0]), top)
    ax.text(-0.38, -3.6, "patch released", fontsize=10.5, color="#c9d6e6", va="bottom")
    # headline top left, over the flat pre-patch weeks, pointing at the weeks 0-3 band
    rates = (f"{hd['treated_rate_before']:.0%} → {hd['treated_rate_after']:.0%} of offers")
    ax.annotate(f"{_pts(hd['beta_pts'])} percentage points", xy=(x0 + 0.05, hd["beta_pts"]),
                xytext=(0.015, 0.97), textcoords="axes fraction", ha="left", va="top",
                fontsize=18, fontweight="bold", color=ACCENT,
                arrowprops=dict(arrowstyle="-|>", color=ACCENT, lw=1.4, shrinkA=30, shrinkB=2,
                                connectionstyle="arc3,rad=0.25", relpos=(0.32, 0.0)))
    ax.text(0.015, 0.875, f"average, {HORIZON_LABEL} ({rates})", transform=ax.transAxes,
            ha="left", va="top", fontsize=11.5, color="#f3f6fa")
    lo_w, hi_w = WEEKS
    ax.set_xlim(lo_w - 0.6, hi_w + 0.6)
    ticks = list(range(lo_w, hi_w + 1))
    ax.set_xticks(ticks, [f"≤{MINUS}{-lo_w}" if w == lo_w else f"{w}+" if w == hi_w
                          else str(w).replace("-", MINUS) for w in ticks])
    lo_y = ax.get_ylim()[0]
    ax.set_yticks([v for v in range(-100, 101, 5) if lo_y <= v <= ymax + 2])
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:+.0f}".replace("-", MINUS)
                                 if v else "0")
    ax.tick_params(labelsize=11, length=0)
    ax.set_xlabel("weeks since the patch", fontsize=12)
    ax.set_ylabel("change in pick rate vs. unchanged cards\n"
                  "(percentage points, relative to the week before)", fontsize=12)
    fig.suptitle(title, x=0.04, y=0.975, ha="left", fontsize=17, fontweight="bold")
    fig.text(0.04, 0.905, change_label, ha="left", fontsize=12.5, color="#c9d6e6")
    handles, labels = ax.get_legend_handles_labels()
    swatch = Line2D([], [], ls="none", marker="s", ms=10, mfc=ACCENT, mew=0, alpha=0.18)
    ax.legend([swatch] + handles, ["95% interval, placebo-calibrated"] + labels,
              loc="lower right", frameon=False, fontsize=10.5, labelcolor="#f3f6fa",
              handletextpad=0.4)
    ax.text(hi_w + 0.5, ymax + 0.7, "weekly bars: sampling error only", ha="right",
            va="bottom", fontsize=10.5, color="#c9d6e6")
    fig.subplots_adjust(left=0.13, right=0.97, top=0.85, bottom=0.11)
    return fig
