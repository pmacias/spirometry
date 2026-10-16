"""Shared helpers for the triage scripts: the dose-response line as notebook 02/04 build it,
dose rulers, and a meta-regression wrapper that also returns the coefficient covariance.

Read-only: data/analysis/did_*.parquet and reference/tweak_sizes.csv. No run-level data.

Paths (added for the final-table rerun, scripts/writeup/phil_runs.sh; defaults are the
triage's): TRIAGE_AN = the saved fits read (default data/analysis), TRIAGE_OUT = where the
scripts write and the analysis scripts read their CSVs (default triage/out, the 1,873-page
record; the rerun uses triage/out_final).
"""
import os

import numpy as np
import pandas as pd

from spirometry.meta import meta_regression

AN = os.environ.get("TRIAGE_AN", "data/analysis")
OUT = os.environ.get("TRIAGE_OUT", "triage/out")
REF = "reference"
SECOND_BEFORE = "v0.103.3"
C_DIFF = np.array([0.0, 0.0, -1.0, 1.0])     # slope_second - slope_first in "slope per patch"


def to_num(s):
    return pd.to_numeric(pd.Series(s).astype(str).str.replace("+", "", regex=False),
                         errors="coerce").to_numpy()


def kind_of(field):
    if field == "damage":
        return "damage"
    if field == "block":
        return "block"
    if str(field).startswith("powers_applied"):
        return "power amount"
    return "other"


def load_fits(name="h3"):
    d = pd.read_parquet(f"{AN}/did_{name}.parquet")
    return d.set_index("card_patch_id") if "card_patch_id" in d.columns else d


def all_tweaks(name="h3"):
    """Every fitted tweak with dose columns (mixed and upgrade-only included, flagged)."""
    d = load_fits(name)
    d = d[d.error == ""].copy()
    d["second"] = (d.before_builds == SECOND_BEFORE).astype(float)
    d["patch"] = np.where(d.second == 1, "second", "first")
    d["x"] = d.direction * d.log_ratio
    d["old_n"], d["new_n"] = to_num(d.old), to_num(d.new)
    d["x_abs"] = d.direction * (d.new_n - d.old_n)
    d["kind"] = d.main_field.map(kind_of)
    k = (d.beta / d.beta_lo).abs()               # p(1-p) used in the log-odds conversion
    d["beta_pp"], d["se_pp"] = d.beta, d.se_lo * k
    return d


def on_line(d):
    """Notebook 02 section 8 / notebook 04 selection: 38 tweaks."""
    return d[(d.mixed_direction != "yes") & (d.upgrade_only != "yes") & d.x.notna()
             & d.beta_lo.notna() & (d.se_lo > 0)].copy()


def add_rulers(L):
    """Dose rulers on the line. The first seven are notebook 04's; the rest are new here.
    Every ruler is computed on the 38 line tweaks together (pooled over patches), as nb04."""
    L = L.copy()
    L["x_pct"] = L.direction * (L.new_n - L.old_n) / L.old_n
    L["x_rank"] = L.x.rank(pct=True) - 0.5
    L["x_kind"] = L.x / L.groupby("kind").x.transform(lambda s: s.abs().median())
    L["x_sign"] = np.sign(L.x)
    # new: absolute change in units of the kind's typical absolute change
    L["x_abs_kind"] = L.x_abs / L.groupby("kind").x_abs.transform(lambda s: s.abs().median())
    # new: mean of the base and the upgraded card's ln change (base alone where the upgrade
    # delta did not change; tweak_sizes' upgraded_log_ratio)
    up = L.direction * L.upgraded_log_ratio
    L["x_baseupg"] = np.where(up.notna(), (L.x + up) / 2, L.x)
    return L


RULERS = [
    ("ln(new/old) [baseline]", "x", "beta_lo", "se_lo"),
    ("outcome in pp, ln dose", "x", "beta_pp", "se_pp"),
    ("absolute (new - old)", "x_abs", "beta_lo", "se_lo"),
    ("rank", "x_rank", "beta_lo", "se_lo"),
    ("percent", "x_pct", "beta_lo", "se_lo"),
    ("ln / kind's median |ln|", "x_kind", "beta_lo", "se_lo"),
    ("sign only", "x_sign", "beta_lo", "se_lo"),
    ("NEW: (new-old) / kind's median |new-old|", "x_abs_kind", "beta_lo", "se_lo"),
    ("NEW: mean of base and upgraded ln", "x_baseupg", "beta_lo", "se_lo"),
]


def fit(y, se, X):
    """meta_regression plus the covariance of the coefficients (same weights)."""
    y, se, X = np.asarray(y, float), np.asarray(se, float), np.asarray(X, float)
    b, s, tau2, Q, dof = meta_regression(y, se, X)
    ws = 1 / (se ** 2 + tau2)
    cov = np.linalg.inv((X.T * ws) @ X)
    return b, cov, tau2, Q, dof


def per_patch_design(x, second):
    x, second = np.asarray(x, float), np.asarray(second, float)
    return np.column_stack([np.ones(len(x)), second, x * (1 - second), x * second])


def slopes_by_patch(d, x="x", y="beta_lo", s="se_lo", se_factor=(1.0, 1.0)):
    """'slope per patch' fit; returns a dict with both slopes, their difference, the ratio
    slope2/slope1 (delta-method se), tau2 and Q."""
    d = d[d[x].notna() & d[y].notna() & (d[s] > 0)]
    sec = d.second.to_numpy()
    se = d[s].to_numpy() * np.where(sec == 1, se_factor[1], se_factor[0])
    X = per_patch_design(d[x], sec)
    b, cov, tau2, Q, dof = fit(d[y], se, X)
    diff, se_diff = C_DIFF @ b, np.sqrt(C_DIFF @ cov @ C_DIFF)
    b1, b2 = b[2], b[3]
    r = b2 / b1
    g = np.array([0, 0, -b2 / b1 ** 2, 1 / b1])
    se_r = np.sqrt(g @ cov @ g)
    return dict(n1=int((sec == 0).sum()), n2=int(sec.sum()), slope1=b1, se1=np.sqrt(cov[2, 2]),
                slope2=b2, se2=np.sqrt(cov[3, 3]), diff=diff, se_diff=se_diff,
                z_diff=diff / se_diff, ratio=r, se_ratio=se_r, shift=b[1],
                se_shift=np.sqrt(cov[1, 1]), tau2=tau2, Q=Q, df=dof)
