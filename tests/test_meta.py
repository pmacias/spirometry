"""spirometry.meta: the dose-response meta-regression, on synthetic estimates with a planted
slope, and against the copy in notebooks/02_pick_rate_did.ipynb it was moved from."""
import json
import pathlib

import numpy as np
import pytest

from spirometry import meta

NB = pathlib.Path(__file__).resolve().parents[1] / "notebooks" / "02_pick_rate_did.ipynb"


def planted(k=400, slope=1.3, intercept=0.05, tau=0.2, seed=1):
    rng = np.random.default_rng(seed)
    x = rng.uniform(-0.6, 0.6, k)
    se = rng.uniform(0.03, 0.1, k)
    y = intercept + slope * x + rng.normal(0, tau, k) + rng.normal(0, se)
    return x, y, se


def test_recovers_planted_slope_and_tau():
    x, y, se = planted()
    b, s, tau2, Q, dof = meta.meta_regression(y, se, np.column_stack([np.ones_like(x), x]))
    assert abs(b[1] - 1.3) < 2.5 * s[1]
    assert abs(b[0] - 0.05) < 2.5 * s[0]
    assert 0.15 < np.sqrt(tau2) < 0.25
    assert dof == len(x) - 2 and Q > dof


def test_no_scatter_is_inverse_variance_wls():
    rng = np.random.default_rng(2)
    x = rng.uniform(-0.5, 0.5, 200)
    se = rng.uniform(0.05, 0.2, 200)
    y = 0.8 * x + rng.normal(0, se)
    X = np.column_stack([np.ones_like(x), x])
    b, s, tau2, _, _ = meta.meta_regression(y, se, X)
    w = 1 / se ** 2
    b_wls = np.linalg.solve((X.T * w) @ X, (X.T * w) @ y)
    if tau2 == 0:
        np.testing.assert_allclose(b, b_wls)
    assert tau2 < 0.01


def test_slope_per_patch_recovers_both_slopes():
    rng = np.random.default_rng(3)
    x = rng.uniform(-0.6, 0.6, 600)
    second = (np.arange(600) % 2).astype(float)
    se = np.full(600, 0.05)
    y = np.where(second == 1, 0.2 * x - 0.1, 1.4 * x) + rng.normal(0, se)
    fits = meta.dose_response_fits(y, se, x, second).set_index(["model", "term"])
    f = fits.loc["slope per patch"]
    assert abs(f.loc["slope_first", "coef"] - 1.4) < 3 * f.loc["slope_first", "se"]
    assert abs(f.loc["slope_second", "coef"] - 0.2) < 3 * f.loc["slope_second", "se"]
    assert abs(f.loc["second", "coef"] + 0.1) < 3 * f.loc["second", "se"]
    assert set(fits.index.get_level_values("model")) == set(meta.MODELS)
    # predict() draws the same line the coefficients describe
    coefs = f.coef.to_dict()
    np.testing.assert_allclose(meta.predict(coefs, "slope per patch", np.array([0.0, 0.5]), 1),
                               [coefs["intercept"] + coefs["second"],
                                coefs["intercept"] + coefs["second"]
                                + 0.5 * coefs["slope_second"]])


def test_same_as_notebook_copy():
    """The function was moved verbatim: the notebook's definition gives the same numbers."""
    cells = json.loads(NB.read_text())["cells"]
    src = next((("".join(c["source"])) for c in cells if c["cell_type"] == "code"
                and "def meta_regression" in "".join(c["source"])), None)
    if src is None:
        pytest.skip("the notebook no longer defines meta_regression")
    start = src.index("def meta_regression")
    end = src.index("\n\n", src.index("return b, np.sqrt"))
    ns = {"np": np}
    exec(src[start:end], ns)
    x, y, se = planted(k=60, seed=4)
    X = np.column_stack([np.ones_like(x), x, np.clip(x, 0, None)])
    for a, b in zip(ns["meta_regression"](y, se, X), meta.meta_regression(y, se, X)):
        np.testing.assert_allclose(a, b)


def test_se_inflation_default_and_per_patch():
    # No factor or (1, 1): the existing fits, bit for bit. (f1, f2): the same as passing
    # se already multiplied by each tweak's patch factor.
    x, y, se = planted(k=60, seed=4)
    second = (np.arange(60) % 3 == 0).astype(float)
    base = meta.dose_response_fits(y, se, x, second)
    assert base.equals(meta.dose_response_fits(y, se, x, second, se_inflation=(1, 1)))
    infl = meta.dose_response_fits(y, se, x, second, se_inflation=(2.0, 3.5))
    manual = meta.dose_response_fits(y, se * np.where(second == 1, 3.5, 2.0), x, second)
    assert infl.equals(manual) and not infl.equals(base)
