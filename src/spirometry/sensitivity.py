"""Sensitivity of the dose-response to how the dose is measured and how sure the errors are.

The triage's saved-fit computations (`triage/TRIAGE.md` sections B, B2, C, D, K1, K2) as
tested functions, so they can be rerun on any set of saved fits and written out as tables for
the field guide. Input: a `did_*.parquet` saved by notebook 02 (one row per tweak, indexed by
`card_patch_id`) and the placebo tables. No run-level data. numpy and pandas; the model
is `spirometry.meta.meta_regression`; the calibrated counts use `spirometry.did`'s placebo
summary (imported only there).

Calibrated "clearly nonzero" (`calibrated_counts.csv`, Phil's rule of 2026-10-14): each
tweak's z = beta / se divided by its patch's robust placebo sd (did.placebo_summary's
robust_sd_z, 1.4826 x MAD, on the deduplicated (window, pseudo card) pairs, the same factors
as se_inflation's "robust sd by patch"), from placebo fits at the estimate's own horizon;
clearly nonzero = |calibrated z| > 2; the plain placebo sd is the sensitivity row. Written
only when placebo_main.parquet exists; a horizon without placebo fits gets blank rows.

The model throughout is the notebook's "slope per patch":
    y = a + c [second] + b1 x [first] + b2 x [second],   weights 1 / (se^2 + tau^2)
y = beta in log-odds (beta_lo), x = the dose. The patch difference is b2 - b1, its se from the
coefficient covariance.

Which tweaks are on the line (`SPECS`):
- "triage": the 38 of notebooks 02 and 04 (mixed-direction and upgrade-only tweaks off). It
  reproduces the triage's printed numbers.
- "primary" (decided 2026-10-09, PLAN.md decision log): the triage's mixed-tweak rule puts
  Reflect on the line at its base-card dose ln(15/17) (Leading Strike stays off), and
  Debilitate v0.107.1, whose size can't be measured, leaves the ln line. Both enter the sign
  ruler: Leading Strike +1 ("Buffed"), Debilitate v0.107.1 -1 (a nerf).
- "primary, Debilitate at table dose": as primary, with Debilitate v0.107.1 on the line at
  its table dose (the sensitivity row the decision asks for).
- "Reflect off, Debilitate off": the triage's K2 single call, to reconcile with the z diff
  quoted when the decisions were made.

Rulers (`add_rulers`): the triage's nine plus the hybrid ruler. The hybrid ruler was proposed
after notebook 04's results were known, so every table marks it `post_hoc`.

    python -m spirometry.sensitivity --analysis data/analysis --out data/analysis/writeup
"""
import argparse
import pathlib

import numpy as np
import pandas as pd

from spirometry.meta import meta_regression

SECOND_BEFORE = "v0.103.3"                 # before block of the second stable window
LEADING_STRIKE = "LEADING_STRIKE@v0.103.2/patch"
REFLECT = "REFLECT@v0.107.1/patch"
DEBILITATE_2 = "DEBILITATE@v0.107.1/patch"
GRAND_FINALE = "GRAND_FINALE@v0.103.2/patch"
CRESCENT_SPEAR = "CRESCENT_SPEAR@v0.107.1/patch"
C_DIFF = np.array([0.0, 0.0, -1.0, 1.0])   # b2 - b1 in the slope-per-patch design
Z_CRIT = 1.959963984540054                 # two-sided alpha = 0.05

# The mixed-tweak rule's outcome for the two tweaks flagged mixed in tweak_sizes.csv
# (derived from the card text in TRIAGE.md B2; the rule can't be applied from the tables,
# which hold no card text). dose None = off the ln line; sign = the patch-note label.
MIXED_RULE = {
    LEADING_STRIKE: dict(dose=None, sign=1.0,
                         why="7 damage + 1 Shiv -> 3 damage + 2 Shivs; total 11 -> 11 at "
                             "Strength 0, label Buffed: dose 0, off the line"),
    REFLECT: dict(dose=float(np.log(15 / 17)), sign=-1.0,
                  why="block 17 -> 15, upgraded 21 -> 20: same direction, not mixed; "
                      "base-card dose ln(15/17)"),
}
# Tweaks whose size can't be measured: sign ruler only.
SIGN_ONLY = {
    DEBILITATE_2: dict(sign=-1.0, why="debuff duration 3 -> 2 turns; size depends on the "
                                      "build, fight length and other Weak/Vulnerable sources"),
}
SPECS = {
    "triage": dict(add={}, drop=[], sign_extra={}),
    "primary": dict(add={REFLECT: MIXED_RULE[REFLECT]["dose"]}, drop=[DEBILITATE_2],
                    sign_extra={LEADING_STRIKE: MIXED_RULE[LEADING_STRIKE]["sign"],
                                DEBILITATE_2: SIGN_ONLY[DEBILITATE_2]["sign"]}),
    "primary, Debilitate at table dose": dict(
        add={REFLECT: MIXED_RULE[REFLECT]["dose"]}, drop=[],
        sign_extra={LEADING_STRIKE: MIXED_RULE[LEADING_STRIKE]["sign"]}),
    "Reflect off, Debilitate off": dict(add={}, drop=[DEBILITATE_2], sign_extra={}),
}
PRIMARY = "primary"


# ------------------------------------------------------------------------------ inputs

def _num(s):
    return pd.to_numeric(pd.Series(s).astype(str).str.replace("+", "", regex=False),
                         errors="coerce").to_numpy()


def kind_of(field):
    """Kind of the changed number: damage, block, power amount or other."""
    if field == "damage":
        return "damage"
    if field == "block":
        return "block"
    if str(field).startswith("powers_applied"):
        return "power amount"
    return "other"


def prepare(fits):
    """A saved `run_all` table -> every fitted tweak with dose columns (mixed and upgrade-only
    kept, flagged). `fits` is indexed by card_patch_id or has that column."""
    d = fits.set_index("card_patch_id") if "card_patch_id" in fits.columns else fits
    d = d[d.error.fillna("") == ""].copy()
    d["second"] = (d.before_builds == SECOND_BEFORE).astype(float)
    d["patch"] = np.where(d.second == 1, "second", "first")
    d["x"] = d.direction * d.log_ratio
    d["old_n"], d["new_n"] = _num(d.old), _num(d.new)
    d["x_abs"] = d.direction * (d.new_n - d.old_n)
    d["kind"] = d.main_field.map(kind_of)
    k = (d.beta / d.beta_lo).abs()            # p(1-p) of the log-odds conversion
    d["beta_pp"], d["se_pp"] = d.beta, d.se_lo * k
    return d


def notebook_line(d):
    """Notebooks 02 and 04's line: no mixed-direction or upgrade-only tweaks (38)."""
    return d[(d.mixed_direction != "yes") & (d.upgrade_only != "yes") & d.x.notna()
             & d.beta_lo.notna() & (d.se_lo > 0)].copy()


def dose_line(d, spec=PRIMARY):
    """The tweaks on the ln line under a spec, with x set to their dose."""
    s = SPECS[spec]
    L = notebook_line(d).drop(index=[c for c in s["drop"] if c in d.index], errors="ignore")
    for cpid, x in s["add"].items():
        if cpid in d.index:
            row = d.loc[[cpid]].copy()
            row["x"] = x
            L = pd.concat([L, row])
    return L


def sign_line(d, spec=PRIMARY):
    """The sign ruler's tweaks: the line plus the spec's sign-only tweaks, x = the sign."""
    L = dose_line(d, spec)
    for cpid, sg in SPECS[spec]["sign_extra"].items():
        if cpid in d.index and cpid not in L.index:
            row = d.loc[[cpid]].copy()
            row["x"] = sg
            L = pd.concat([L, row])
    L["x_sign"] = np.sign(L.x)
    return L


# ------------------------------------------------------------------------------ rulers

def _kind_scaled(s, kind):
    return s / s.groupby(kind).transform(lambda v: v.abs().median())


def add_rulers(L):
    """Every ruler's dose, computed on the given tweaks together (pooled over patches), as
    notebook 04 does. Recompute after changing the set: rank and per-kind medians depend
    on it."""
    L = L.copy()
    L["x_pct"] = L.direction * (L.new_n - L.old_n) / L.old_n
    L["x_rank"] = L.x.rank(pct=True) - 0.5
    L["x_kind"] = _kind_scaled(L.x, L.kind)
    L["x_sign"] = np.sign(L.x)
    L["x_abs_kind"] = _kind_scaled(L.x_abs, L.kind)
    up = L.direction * L.upgraded_log_ratio
    L["x_baseupg"] = np.where(up.notna(), (L.x + up) / 2, L.x)
    raw = pd.Series(np.where(L.kind.isin(["damage", "block"]), L.x_abs, L.x), index=L.index)
    L["x_hybrid"] = _kind_scaled(raw, L.kind)
    return L


# (name, dose column, outcome column, se column, post hoc)
RULERS = [
    ("ln(new/old)", "x", "beta_lo", "se_lo", False),
    ("outcome in pp, ln dose", "x", "beta_pp", "se_pp", False),
    ("absolute (new - old)", "x_abs", "beta_lo", "se_lo", False),
    ("rank", "x_rank", "beta_lo", "se_lo", False),
    ("percent", "x_pct", "beta_lo", "se_lo", False),
    ("ln / kind's median |ln|", "x_kind", "beta_lo", "se_lo", False),
    ("sign only", "x_sign", "beta_lo", "se_lo", False),
    ("(new - old) / kind's median |new - old|", "x_abs_kind", "beta_lo", "se_lo", False),
    ("mean of base and upgraded ln", "x_baseupg", "beta_lo", "se_lo", False),
    ("hybrid: abs for damage/block, ln for power/other, / kind's median", "x_hybrid",
     "beta_lo", "se_lo", True),
]


# ------------------------------------------------------------------------------ the model

def fit(y, se, X):
    """meta_regression plus the coefficients' covariance (same weights)."""
    y, se, X = np.asarray(y, float), np.asarray(se, float), np.asarray(X, float)
    b, _, tau2, Q, dof = meta_regression(y, se, X)
    cov = np.linalg.inv((X.T * (1 / (se ** 2 + tau2))) @ X)
    return b, cov, tau2, Q, dof


def per_patch_design(x, second):
    x, second = np.asarray(x, float), np.asarray(second, float)
    return np.column_stack([np.ones(len(x)), second, x * (1 - second), x * second])


def slopes_by_patch(d, x="x", y="beta_lo", s="se_lo", se_factor=(1.0, 1.0)):
    """Slope per patch: both slopes, their difference and z, the ratio slope2 / slope1 with a
    delta-method se, the second-patch shift, tau2, Q. se_factor multiplies each patch's se."""
    d = d[d[x].notna() & d[y].notna() & (d[s] > 0)]
    sec = d.second.to_numpy()
    se = d[s].to_numpy() * np.where(sec == 1, se_factor[1], se_factor[0])
    b, cov, tau2, Q, dof = fit(d[y], se, per_patch_design(d[x], sec))
    diff, se_diff = C_DIFF @ b, np.sqrt(C_DIFF @ cov @ C_DIFF)
    b1, b2 = b[2], b[3]
    g = np.array([0, 0, -b2 / b1 ** 2, 1 / b1])
    return dict(n1=int((sec == 0).sum()), n2=int(sec.sum()), slope1=b1, se1=np.sqrt(cov[2, 2]),
                slope2=b2, se2=np.sqrt(cov[3, 3]), diff=diff, se_diff=se_diff,
                z_diff=diff / se_diff, ratio=b2 / b1, se_ratio=np.sqrt(g @ cov @ g),
                shift=b[1], se_shift=np.sqrt(cov[1, 1]), tau2=tau2, Q=Q, df=dof)


def _row(r):
    r = dict(r)
    r["z1"], r["z2"] = r["slope1"] / r["se1"], r["slope2"] / r["se2"]
    r["ratio_lo"] = r["ratio"] - Z_CRIT * r["se_ratio"]
    r["ratio_hi"] = r["ratio"] + Z_CRIT * r["se_ratio"]
    return r


# ------------------------------------------------------------------------------ tables

def ruler_table(d, spec=PRIMARY):
    """Every ruler under one spec. The sign ruler uses `sign_line` (the spec's sign-only
    tweaks included); the others the spec's ln line."""
    L = add_rulers(dose_line(d, spec))
    S = sign_line(d, spec)
    rows = []
    for name, x, y, s, post_hoc in RULERS:
        r = slopes_by_patch(S if x == "x_sign" else L, x, y, s)
        rows.append(dict(spec=spec, ruler=name, post_hoc=post_hoc, **_row(r)))
    return pd.DataFrame(rows)


def dose_points(d, spec=PRIMARY):
    """The points of the spec's ln line and sign ruler, for the dose-response figure."""
    L = dose_line(d, spec)
    S = sign_line(d, spec)
    out = S[["card_id", "color", "patch", "kind", "x", "beta_lo", "se_lo", "beta_pp",
             "se_pp"]].copy()
    out["x_ln"] = L.x.reindex(out.index)
    out["on_ln_line"] = out.index.isin(L.index)
    out["x_sign"] = np.sign(S.x)
    out = out.drop(columns="x").rename_axis("card_patch_id").reset_index()
    out.insert(0, "spec", spec)
    return out


def review_calls(L):
    """Phil's card-review calls as one variant: Grand Finale off, Debilitate v0.107.1 off,
    Crescent Spear at its effective damage 8 -> 10 (x = ln(10/8), absolute +2). Rulers must be
    recomputed on the result."""
    V = L.drop(index=[GRAND_FINALE, DEBILITATE_2], errors="ignore").copy()
    if CRESCENT_SPEAR in V.index:
        dr = V.loc[CRESCENT_SPEAR, "direction"]
        V.loc[CRESCENT_SPEAR, ["old_n", "new_n"]] = [8.0, 10.0]
        V.loc[CRESCENT_SPEAR, "x"] = dr * np.log(10 / 8)
        V.loc[CRESCENT_SPEAR, "x_abs"] = dr * 2.0
    return V


def review_call_table(d, spec="triage"):
    """Every ruler on the spec's line and on the review-call variant of it (triage K2)."""
    base = dose_line(d, spec)
    rows = []
    for variant, L in [("as specified", base), ("review calls", review_calls(base))]:
        L = add_rulers(L)
        for name, x, y, s, post_hoc in RULERS:
            rows.append(dict(spec=spec, variant=variant, ruler=name, post_hoc=post_hoc,
                             **_row(slopes_by_patch(L, x, y, s))))
    for label, drop, cs in [("Grand Finale off", [GRAND_FINALE], False),
                            ("Debilitate v0.107.1 off", [DEBILITATE_2], False),
                            ("Crescent Spear at ln(10/8)", [], True)]:
        W = base.drop(index=drop, errors="ignore").copy()
        if cs and CRESCENT_SPEAR in W.index:
            W.loc[CRESCENT_SPEAR, "x"] = W.loc[CRESCENT_SPEAR, "direction"] * np.log(10 / 8)
        rows.append(dict(spec=spec, variant=f"one call: {label}", ruler="ln(new/old)",
                         post_hoc=False, **_row(slopes_by_patch(W))))
    return pd.DataFrame(rows)


LS_DOSES = {**{f"damage-equivalent S={s}": float(np.log((11 + 3 * s) / (11 + 2 * s)))
               for s in range(4)},
            "naive main field": float(np.log(3 / 7))}
RF_DOSES = {"base block": float(np.log(15 / 17)), "upgraded total": float(np.log(20 / 21)),
            "mean of the two": float((np.log(15 / 17) + np.log(20 / 21)) / 2)}


def mixed_table(d):
    """The two mixed tweaks at fixed doses, added to the notebooks' 38 (triage B2): ln
    variants, then the sign ruler with each one's label."""
    base = notebook_line(d)

    def with_points(extra):
        L = base.copy()
        for cpid, x in extra.items():
            if cpid in d.index:
                row = d.loc[[cpid]].copy()
                row["x"] = x
                L = pd.concat([L, row])
        return L

    variants = [("both off", {})]
    variants += [(f"Leading Strike {k}", {LEADING_STRIKE: v}) for k, v in LS_DOSES.items()]
    variants += [(f"Reflect {k}", {REFLECT: v}) for k, v in RF_DOSES.items()]
    variants += [(f"Leading Strike {kl} + Reflect {kr}", {LEADING_STRIKE: vl, REFLECT: vr})
                 for kl, vl in LS_DOSES.items() for kr, vr in RF_DOSES.items()]
    rows = [dict(ruler="ln(new/old)", variant=n, **_row(slopes_by_patch(with_points(e))))
            for n, e in variants]
    for n, e in [("both off", {}), ("Leading Strike +1", {LEADING_STRIKE: 1.0}),
                 ("Reflect -1", {REFLECT: -1.0}),
                 ("both", {LEADING_STRIKE: 1.0, REFLECT: -1.0})]:
        L = add_rulers(with_points(e))
        rows.append(dict(ruler="sign only", variant=n, **_row(slopes_by_patch(L, "x_sign"))))
    return pd.DataFrame(rows)


def leave_out_table(d, spec=PRIMARY):
    """Leverage, ln ruler: the fit without each tweak, and without each character."""
    L = dose_line(d, spec)
    base = slopes_by_patch(L)
    rows = [dict(spec=spec, left_out="(none)", level="none", card_id="", patch="",
                 **_row(base))]
    for cpid in L.index:
        r = slopes_by_patch(L.drop(index=cpid))
        rows.append(dict(spec=spec, left_out=cpid, level="tweak", card_id=L.loc[cpid, "card_id"],
                         patch=L.loc[cpid, "patch"], **_row(r)))
    for c in sorted(L.color.unique()):
        rows.append(dict(spec=spec, left_out=c, level="character", card_id="", patch="",
                         **_row(slopes_by_patch(L[L.color != c]))))
    T = pd.DataFrame(rows)
    T["d_slope1_in_se"] = (T.slope1 - base["slope1"]) / base["se1"]
    T["d_slope2_in_se"] = (T.slope2 - base["slope2"]) / base["se2"]
    return T


def character_table(d, spec=PRIMARY):
    """Character terms in the slope-per-patch model (triage K1 b, c): character intercepts,
    character x patch intercepts, and per-character slopes where a character has >= 4 points
    in a patch (descriptive)."""
    L = dose_line(d, spec)
    rows = []
    D = pd.get_dummies(L.color, drop_first=True).astype(float)
    X = np.column_stack([per_patch_design(L.x, L.second), D.to_numpy()])
    b, cov, tau2, Q, dof = fit(L.beta_lo, L.se_lo, X)
    c = np.r_[C_DIFF, np.zeros(D.shape[1])]
    rows.append(dict(model="character intercepts", slope1=b[2], se1=np.sqrt(cov[2, 2]),
                     slope2=b[3], se2=np.sqrt(cov[3, 3]),
                     z_diff=(c @ b) / np.sqrt(c @ cov @ c), tau2=tau2, n=len(L)))
    DI = pd.get_dummies(L.color + "_" + L.patch, drop_first=True).astype(float)
    X2 = np.column_stack([L.x * (1 - L.second), L.x * L.second, np.ones(len(L)), DI.to_numpy()])
    b2, cov2, t2, *_ = fit(L.beta_lo, L.se_lo, X2)
    c2 = np.r_[-1, 1, np.zeros(X2.shape[1] - 2)]
    rows.append(dict(model="character x patch intercepts", slope1=b2[0],
                     se1=np.sqrt(cov2[0, 0]), slope2=b2[1], se2=np.sqrt(cov2[1, 1]),
                     z_diff=(c2 @ b2) / np.sqrt(c2 @ cov2 @ c2), tau2=t2, n=len(L)))
    for (col, pt), g in L.groupby(["color", "patch"]):
        if len(g) < 4:
            continue
        bg, cg, tg, *_ = fit(g.beta_lo, g.se_lo, np.column_stack([np.ones(len(g)), g.x]))
        rows.append(dict(model=f"slope within {col}, {pt} patch (descriptive)",
                         slope=bg[1], se=np.sqrt(cg[1, 1]), tau2=tg, n=len(g)))
    T = pd.DataFrame(rows)
    T.insert(0, "spec", spec)
    counts = pd.crosstab(L.color, L.patch)
    return T, counts


# ------------------------------------------------------------------------------ errors

def placebo_factors(summary):
    """SE inflation settings from placebo_diagnostics_summary.csv (one row per window/card
    pair): {name: (first-patch factor, second-patch factor)}."""
    p = summary[summary.dedupe.astype(str).str.lower() == "true"].set_index(["split", "level"])
    rob = (float(p.loc[("patch", "first"), "robust_sd_z"]),
           float(p.loc[("patch", "second"), "robust_sd_z"]))
    sd = (float(p.loc[("patch", "first"), "sd_z"]), float(p.loc[("patch", "second"), "sd_z"]))
    a_rob, a_sd = float(p.loc[("all", "all"), "robust_sd_z"]), float(p.loc[("all", "all"), "sd_z"])
    return {"none": (1.0, 1.0), "robust sd by patch": rob, "sd by patch": sd,
            "robust sd, one factor": (a_rob, a_rob), "sd, one factor": (a_sd, a_sd)}


def placebo_pairs(placebo):
    """placebo_main.parquet -> one row per (window, pseudo card), with log-odds columns."""
    P = placebo[placebo.error.fillna("") == ""].copy()
    k = P.treated_rate_before * (1 - P.treated_rate_before)
    P["beta_lo"], P["se_lo"] = P.beta / k, P.se / k
    return P.drop_duplicates(["color", "stable_build", "fit_on", "pseudo_card"])


def se_inflation_table(L, factors, pairs=None, label=""):
    """Slope per patch with each patch's se times a placebo factor (shared tau2), and as a
    check with a separate tau2 per patch (two meta-regressions). With `pairs`, also the
    additive version: each patch's excess placebo variance (log-odds^2) added to se^2."""
    rows = []
    for name, f in factors.items():
        r = _row(slopes_by_patch(L, se_factor=f))
        sep = {}
        for pt, fac in [("first", f[0]), ("second", f[1])]:
            g = L[L.patch == pt]
            b, cov, tau2, *_ = fit(g.beta_lo, g.se_lo * fac,
                                   np.column_stack([np.ones(len(g)), g.x]))
            sep[pt] = (b[1], np.sqrt(cov[1, 1]), tau2)
        rows.append(dict(label=label, setting=name, factor1=f[0], factor2=f[1], **r,
                         sep_slope1=sep["first"][0], sep_se1=sep["first"][1],
                         sep_tau2_1=sep["first"][2], sep_slope2=sep["second"][0],
                         sep_se2=sep["second"][1], sep_tau2_2=sep["second"][2],
                         sep_z_diff=(sep["second"][0] - sep["first"][0])
                         / np.hypot(sep["second"][1], sep["first"][1])))
    if pairs is not None:
        add = {}
        for pt in ["first", "second"]:
            q = pairs[(pairs.patch == pt) & (pairs.fit_on == "all offers")]
            add[pt] = max(float(q.beta_lo.var() - (q.se_lo ** 2).mean()), 0.0)
        A = L.assign(se_lo=np.sqrt(L.se_lo ** 2 + np.where(L.patch == "second", add["second"],
                                                            add["first"])))
        rows.append(dict(label=label, setting="additive placebo variance",
                         add_var1=add["first"], add_var2=add["second"],
                         **_row(slopes_by_patch(A))))
    return pd.DataFrame(rows)


def spread_table(L, pairs):
    """Real tweaks' scatter against placebo scatter, log-odds, by patch (triage C)."""
    rows = []
    for pt in ["first", "second"]:
        q = pairs[(pairs.patch == pt) & (pairs.fit_on == "all offers")]
        real = L[L.patch == pt]
        rows.append(dict(patch=pt, n_real=len(real), sd_real=real.beta_lo.std(),
                         median_se_real=real.se_lo.median(), n_placebo=len(q),
                         sd_placebo=q.beta_lo.std(), median_se_placebo=q.se_lo.median()))
    return pd.DataFrame(rows)


# --------------------------------------------------------------- calibrated counts

SPREADS = {"none": None, "robust sd": "robust_sd_z", "sd": "sd_z"}   # spread -> column


def horizon_label(max_week_after):
    """A fit's horizon from its max_week_after column: all missing -> "all weeks",
    one value k -> "weeks 0-k"; several values is an error (a mixed table)."""
    v = pd.to_numeric(pd.Series(max_week_after), errors="coerce").dropna().unique()
    if len(v) == 0:
        return "all weeks"
    if len(v) > 1:
        raise ValueError(f"fits mix horizons: max_week_after {sorted(v)}")
    return f"weeks 0-{int(v[0])}"


def placebo_factors_by_horizon(placebo, ref="reference"):
    """{(horizon, patch): dict(robust_sd=..., sd=..., n_placebo=...)} from placebo_main
    (did.placebo_all's rows): the fits are split by their own horizon (max_week_after;
    missing = all weeks) and each part goes through did.placebo_summary(dedupe=True), the
    diagnostics' own estimator: robust_sd_z = 1.4826 x MAD of z, sd_z, and n_placebo = the
    number of (window, pseudo card) pairs behind them. A horizon with no placebo fits has no
    entry."""
    from spirometry import did
    mwa = placebo["max_week_after"] if "max_week_after" in placebo else pd.Series(
        np.nan, index=placebo.index)
    labels = pd.to_numeric(mwa, errors="coerce").map(
        lambda v: "all weeks" if pd.isna(v) else f"weeks 0-{int(v)}")
    out = {}
    for h, g in placebo.groupby(labels):
        summ = did.placebo_summary(g, dedupe=True, ref=ref)
        for r in summ[summ.split == "patch"].itertuples():
            out[(h, r.level)] = dict(robust_sd=float(r.robust_sd_z), sd=float(r.sd_z),
                                     n_placebo=int(r.n_fits))
    return out


def calibrated_counts(fits, factors):
    """"Clearly nonzero" with the z's scaled by the placebo spread (Phil's rule,
    2026-10-14): calibrated z = (beta / se) / factor, factor = the tweak's patch's placebo
    spread at the fit's horizon; clearly nonzero = |calibrated z| > 2; toward the change =
    the export's rule (export.toward_change), counted among the clearly nonzero tweaks with
    a single direction.

    fits: {horizon: prepared fit table (prepare())}; factors: placebo_factors_by_horizon's
    dict. One row per (patch, horizon, spread): spread "none" (factor 1: the uncalibrated
    count on clustered SEs, as the export's clearly_nonzero), "robust sd" (primary) and
    "sd" (sensitivity). Where no placebo fits exist at the horizon the row has a blank
    factor and counts, and `status` says why."""
    from spirometry.export import toward_change

    rows = []
    for horizon, d in fits.items():
        d = d[d.beta.notna() & (d.se > 0)]
        single = (d.mixed_direction != "yes") & (d.upgrade_only != "yes")
        toward = toward_change(d.beta, d.x, single)
        z = d.beta / d.se
        for patch in ["first", "second"]:
            g = d.patch == patch
            f = factors.get((horizon, patch))
            for spread, col in SPREADS.items():
                base = dict(patch=patch, horizon=horizon, spread=spread,
                            n_tweaks=int(g.sum()))
                if col is not None and f is None:
                    rows.append(dict(base, factor=np.nan, n_placebo=np.nan,
                                     n_clearly_nonzero=np.nan,
                                     n_clearly_nonzero_with_direction=np.nan,
                                     n_toward=np.nan,
                                     status=f"missing: no placebo fits at {horizon}"))
                    continue
                factor = 1.0 if col is None else f[col.replace("_z", "")]
                clear = g & ((z / factor).abs() > 2)
                rows.append(dict(base, factor=factor,
                                 n_placebo=np.nan if col is None else f["n_placebo"],
                                 n_clearly_nonzero=int(clear.sum()),
                                 n_clearly_nonzero_with_direction=int(
                                     (clear & (toward != "")).sum()),
                                 n_toward=int((clear & (toward == "yes")).sum()),
                                 status="ok"))
    return pd.DataFrame(rows, columns=[
        "patch", "horizon", "spread", "factor", "n_placebo", "n_tweaks", "n_clearly_nonzero",
        "n_clearly_nonzero_with_direction", "n_toward", "status"])


# ------------------------------------------------------------------------------ power

POWER_SEED = 20261007
PLANTED = (0.0, 0.3, 0.7, 1.0, 1.44)


def power_simulation(L, inflated, n_sim=1000, seed=POWER_SEED, planted=PLANTED,
                     se_scale=1.0, se_scale_first=1.0, tau2=None, simulate_first=False):
    """Could a patch-1-sized slope be seen in patch 2? (triage D; design fixed there.)

    For each setting, fit the slope-per-patch model to L with that setting's se's; then keep
    the first-patch points (or, with simulate_first, redraw them from the fitted line) and
    redraw the second-patch points as (a + c) + b x + N(0, se^2 + tau2) for each planted b,
    refit, and count detections (|estimate / se| > 1.96) of slope2 != 0 and slope2 != slope1.
    Settings: "honest" (se as fitted), "placebo-inflated" (each patch's se times `inflated`,
    the placebo robust sd), "honest, patch-2 tau2" (noise with a patch-2-only fit's tau2).
    se_scale / se_scale_first multiply the second / first patch's se's (for subsets); tau2
    overrides the generating tau2. One generator, settings in that order (reproducible)."""
    settings = [("honest", (1.0, 1.0), "shared"), ("placebo-inflated", tuple(inflated), "shared"),
                ("honest, patch-2 tau2", (1.0, 1.0), "patch2")]
    sec = L.second.to_numpy()
    x, y_obs, se_obs = L.x.to_numpy(), L.beta_lo.to_numpy(), L.se_lo.to_numpy()
    X = per_patch_design(x, sec)
    i2 = sec == 1
    rng = np.random.default_rng(seed)
    rows = []
    for name, (f1, f2), tau_src in settings:
        se_fit = se_obs * np.where(i2, f2 * se_scale, f1 * se_scale_first)
        b_real, _, tau2_real, *_ = fit(y_obs, se_fit, X)
        if tau2 is not None:
            tau2_gen = tau2
        elif tau_src == "patch2":
            tau2_gen = fit(y_obs[i2], se_fit[i2], np.column_stack([np.ones(i2.sum()), x[i2]]))[2]
        else:
            tau2_gen = tau2_real
        a2 = b_real[0] + b_real[1]
        sd2 = np.sqrt(se_fit[i2] ** 2 + tau2_gen)
        sd1 = np.sqrt(se_fit[~i2] ** 2 + tau2_gen)
        for b in planted:
            est = np.empty((n_sim, 5))
            for k in range(n_sim):
                y = y_obs.copy()
                y[i2] = a2 + b * x[i2] + rng.normal(0.0, sd2)
                if simulate_first:
                    y[~i2] = b_real[0] + b_real[2] * x[~i2] + rng.normal(0.0, sd1)
                bb, cov, t2, *_ = fit(y, se_fit, X)
                est[k] = (bb[3], np.sqrt(cov[3, 3]), C_DIFF @ bb,
                          np.sqrt(C_DIFF @ cov @ C_DIFF), t2)
            s2, s2se, dd, dse, t2 = est.T
            rows.append(dict(setting=name, planted=b, tau2_gen=tau2_gen,
                             slope1_obs=b_real[2], mean_slope2=s2.mean(), sd_slope2=s2.std(),
                             q025=np.quantile(s2, 0.025), q975=np.quantile(s2, 0.975),
                             median_se2=np.median(s2se),
                             power_slope2_ne_0=np.mean(np.abs(s2 / s2se) > Z_CRIT),
                             power_diff_ne_0=np.mean(np.abs(dd / dse) > Z_CRIT),
                             cover_planted=np.mean(np.abs(s2 - b) <= Z_CRIT * s2se),
                             median_tau2_fit=np.median(t2), n_sim=n_sim, sim_seed=seed,
                             se_scale=se_scale, se_scale_first=se_scale_first,
                             simulate_first=simulate_first))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------ run

def run(analysis="data/analysis", out=None, fits="h3", all_weeks="main",
        specs=tuple(SPECS), n_sim=1000, ref="reference"):
    """Every table, from the saved fits in `analysis`. Returns {name: DataFrame}; with `out`,
    writes `<name>.csv` there after the export's privacy check."""
    from spirometry.export import check_output

    an = pathlib.Path(analysis)
    D = prepare(pd.read_parquet(an / f"did_{fits}.parquet"))
    factors = placebo_factors(pd.read_csv(an / "placebo_diagnostics_summary.csv"))
    pp = an / "placebo_main.parquet"
    pairs = placebo_pairs(pd.read_parquet(pp)) if pp.exists() else None
    Dw = (prepare(pd.read_parquet(an / f"did_{all_weeks}.parquet"))
          if all_weeks and (an / f"did_{all_weeks}.parquet").exists() else None)

    t = {}
    t["rulers"] = pd.concat([ruler_table(D, s) for s in specs], ignore_index=True)
    t["dose_points"] = pd.concat([dose_points(D, s) for s in specs], ignore_index=True)
    t["review_calls"] = pd.concat([review_call_table(D, s) for s in ("triage", PRIMARY)],
                                  ignore_index=True)
    t["mixed"] = mixed_table(D)
    t["leave_out"] = pd.concat([leave_out_table(D, s) for s in ("triage", PRIMARY)],
                               ignore_index=True)
    ch = [character_table(D, s) for s in ("triage", PRIMARY)]
    t["character"] = pd.concat([c[0] for c in ch], ignore_index=True)
    t["character_counts"] = pd.concat(
        [c[1].rename_axis("color").reset_index().assign(spec=s)
         for c, s in zip(ch, ("triage", PRIMARY))], ignore_index=True)
    se_rows = []
    for s in specs:
        se_rows.append(se_inflation_table(dose_line(D, s), factors, pairs,
                                          label=f"{s}, weeks 0-3 (did_{fits})"))
        if Dw is not None:
            se_rows.append(se_inflation_table(dose_line(Dw, s), factors, pairs,
                                              label=f"{s}, all weeks (did_{all_weeks})"))
    t["se_inflation"] = pd.concat(se_rows, ignore_index=True)
    if pairs is not None:
        t["spread"] = pd.concat([spread_table(dose_line(D, s), pairs).assign(spec=s)
                                 for s in specs], ignore_index=True)
    if pp.exists():
        fits_by_h = {horizon_label(D.get("max_week_after")): D}
        if Dw is not None:
            hw = horizon_label(Dw.get("max_week_after"))
            if hw in fits_by_h:
                raise ValueError(f"did_{fits} and did_{all_weeks} are both {hw}")
            fits_by_h[hw] = Dw
        t["calibrated_counts"] = calibrated_counts(
            fits_by_h, placebo_factors_by_horizon(pd.read_parquet(pp), ref=ref))
    t["power"] = pd.concat(
        [power_simulation(dose_line(D, s), factors["robust sd by patch"], n_sim=n_sim)
         .assign(spec=s) for s in ("triage", PRIMARY)], ignore_index=True)
    for v in t.values():
        v.insert(0, "fits", f"did_{fits}")
    if out:
        o = pathlib.Path(out)
        o.mkdir(parents=True, exist_ok=True)
        for name, df in t.items():
            check_output(name, df)
            df.to_csv(o / f"{name}.csv", index=False)
    return t


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--analysis", default="data/analysis")
    p.add_argument("--out", default="data/analysis/writeup")
    p.add_argument("--fits", default="h3", help="saved fit for the dose line: did_<fits>.parquet")
    p.add_argument("--all-weeks", default="main", help="all-weeks fit for the se table")
    p.add_argument("--n-sim", type=int, default=1000)
    p.add_argument("--ref", default="reference", help="tweak_sizes.csv for the placebo pairs")
    a = p.parse_args(argv)
    t = run(a.analysis, a.out, a.fits, a.all_weeks, n_sim=a.n_sim, ref=a.ref)
    for name, df in t.items():
        print(f"{name + '.csv':24s} {len(df):5d} rows")
    r = t["rulers"]
    ln = r[r.ruler == "ln(new/old)"].set_index("spec")
    print("\nln ruler, slope per patch:")
    for s, row in ln.iterrows():
        print(f"  {s:36s} n {row.n1}+{row.n2}  slope1 {row.slope1:.3f} ± {row.se1:.3f}  "
              f"slope2 {row.slope2:+.3f} ± {row.se2:.3f}  z diff {row.z_diff:+.2f}")
    if "calibrated_counts" in t:
        print("\nclearly nonzero (toward the change / with a direction), by placebo spread:")
        c = t["calibrated_counts"]
        for r in c.itertuples():
            n = ("missing" if r.status != "ok" else
                 f"{r.n_clearly_nonzero:.0f} of {r.n_tweaks} ({r.n_toward:.0f} / "
                 f"{r.n_clearly_nonzero_with_direction:.0f})")
            print(f"  {r.horizon:10s} {r.patch:7s} {r.spread:10s} factor {r.factor:5.2f}  {n}")
    print(f"-> {a.out}/")


if __name__ == "__main__":
    main()
