"""Random-effects meta-regression for the dose-response (Phase 5 step 3). numpy only.

Moved from notebooks/02_pick_rate_did.ipynb, section 8 (meta_regression is unchanged;
tests/test_meta.py checks it against the notebook's copy). dose_response_fits builds the
notebook's four designs from a table of estimates, so the export and the notebook fit the
same models:

    one slope          y = a + b x
    + patch shift      y = a + b x + c [second]
    slope per patch    y = a + c [second] + b1 x [first] + b2 x [second]
    buff/nerf + patch  y = a + c [second] + b+ max(x, 0) + b- min(x, 0)

y = beta in log-odds (beta_lo), x = direction x ln(new/old) of the main field, weights
1 / (se^2 + tau^2).
"""
import numpy as np
import pandas as pd


def meta_regression(y, se, X):
    '''Random-effects meta-regression. Returns (coef, coef_se, tau2, Q, df).
    tau2 by method of moments (DerSimonian-Laird generalized to regression):
      Q = sum w (y - X b_fe)^2 with w = 1/se^2,
      tau2 = max(0, (Q - (k - p)) / (sum w - tr((X'WX)^-1 X'W^2 X))).
    Then weighted least squares with w* = 1/(se^2 + tau2).'''
    y, se, X = np.asarray(y, float), np.asarray(se, float), np.asarray(X, float)
    k, p = X.shape
    w = 1 / se ** 2
    XtW = X.T * w
    b_fe = np.linalg.solve(XtW @ X, XtW @ y)
    Q = float((w * (y - X @ b_fe) ** 2).sum())
    denom = w.sum() - np.trace(np.linalg.solve(XtW @ X, (X.T * w ** 2) @ X))
    tau2 = max(0.0, (Q - (k - p)) / denom)
    ws = 1 / (se ** 2 + tau2)
    XtWs = X.T * ws
    cov = np.linalg.inv(XtWs @ X)
    b = cov @ (XtWs @ y)
    return b, np.sqrt(np.diag(cov)), tau2, Q, k - p


# (model, [(term key, term label as in the notebook)]). The keys are what the dashboard
# uses to draw the lines; the labels are the notebook's.
MODELS = {
    "one slope": [("intercept", "intercept a"), ("slope", "slope b")],
    "+ patch shift": [("intercept", "intercept a"), ("slope", "slope b"),
                      ("second", "second-patch shift c")],
    "slope per patch": [("intercept", "intercept a"), ("second", "second-patch shift c"),
                        ("slope_first", "slope, first patch"),
                        ("slope_second", "slope, second patch")],
    "buff/nerf + patch": [("intercept", "intercept a"), ("second", "second-patch shift c"),
                          ("slope_buff", "buff slope b+"), ("slope_nerf", "nerf slope b-")],
}


def designs(x, second):
    """The design matrix of each model in MODELS, columns in MODELS' order. x: signed log
    change; second: 1 for a second-patch tweak, else 0."""
    x, second = np.asarray(x, float), np.asarray(second, float)
    one = np.ones(len(x))
    return {
        "one slope": np.column_stack([one, x]),
        "+ patch shift": np.column_stack([one, x, second]),
        "slope per patch": np.column_stack([one, second, x * (1 - second), x * second]),
        "buff/nerf + patch": np.column_stack([one, second, np.clip(x, 0, None),
                                              np.clip(x, None, 0)]),
    }


def dose_response_fits(y, se, x, second, se_inflation=None):
    """Fit the four models; one row per (model, term): model, term, term_label, coef, se,
    z, tau2, Q, df, n_tweaks.

    se_inflation: optional (first-patch factor, second-patch factor); each tweak's se is
    multiplied by its patch's factor before fitting (tau2 is re-estimated on the inflated
    errors). None (default) leaves se as given, so existing results are unchanged; the
    placebo calibration (spirometry.did.dose_response_sensitivity) uses it."""
    if se_inflation is not None:
        f1, f2 = se_inflation
        se = np.asarray(se, float) * np.where(np.asarray(second, float) == 1, f2, f1)
    rows = []
    for model, X in designs(x, second).items():
        b, s, tau2, Q, dof = meta_regression(y, se, X)
        for (key, label), bi, si in zip(MODELS[model], b, s):
            rows.append(dict(model=model, term=key, term_label=label, coef=bi, se=si,
                             z=bi / si, tau2=tau2, Q=Q, df=dof, n_tweaks=len(x)))
    return pd.DataFrame(rows)


def predict(coefs, model, x, second):
    """Fitted log-odds at x for one model, from a {term key: coef} dict (a dose_response
    table's rows for that model): the lines the dashboard draws."""
    X = designs(x, np.broadcast_to(np.asarray(second, float), np.shape(x)))[model]
    return X @ np.array([coefs[k] for k, _ in MODELS[model]])
