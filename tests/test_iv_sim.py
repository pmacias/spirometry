"""spirometry.iv_sim: the IV primer's game reproduces the notebook's saved outputs (same
seeds), and the estimators behave as the primer says."""
import json
import pathlib

import numpy as np

from spirometry import iv_sim

NB = pathlib.Path(__file__).resolve().parents[1] / "notebooks" / "iv_primer.ipynb"


def test_single_dataset_matches_the_notebook():
    e = iv_sim.estimates(iv_sim.simulate(seed=2))
    # notebooks/iv_primer.ipynb section 3, saved output (4 decimals)
    for k, v in {"naive": 0.1301, "naive_se": 0.0077, "itt": 0.0265, "itt_se": 0.0046,
                 "first_stage": 0.2988, "fs_se": 0.0037, "iv": 0.0887, "iv_se": 0.0152}.items():
        assert abs(e[k] - v) < 5e-5, k
    assert np.isclose(e["iv"], e["itt"] / e["first_stage"])


def test_functions_match_the_notebook_source():
    """The module's copies of the estimators and the game are the notebook's code."""
    src = "\n".join("".join(c["source"]) for c in json.loads(NB.read_text())["cells"]
                    if c["cell_type"] == "code")
    import inspect
    for f in [iv_sim.slope, iv_sim.wald_iv, iv_sim.estimates]:
        assert inspect.getsource(f).strip() in src, f.__name__
    body = inspect.getsource(iv_sim.simulate).split('"""')[-1].strip()
    assert body in src


def test_iv_is_centered_where_naive_is_biased():
    r = iv_sim.replicate(40, n=20_000)
    s = iv_sim.summarize(r)
    assert s.loc["naive", "mean"] > 0.12
    assert abs(s.loc["iv", "mean"] - iv_sim.TAU) < 3 * s.loc["iv", "sd_across_draws"] / np.sqrt(40)


def test_run_writes_tables(tmp_path, monkeypatch):
    # shrink the replications so the test is fast; the table layout is what is checked
    real = iv_sim.replicate
    monkeypatch.setattr(iv_sim, "replicate", lambda n_reps, **kw: real(min(n_reps, 3), **kw))
    t = iv_sim.run(tmp_path)
    for name in ["single", "draws", "draws_summary", "weak", "confounding", "broken", "het"]:
        assert (tmp_path / f"iv_sim_{name}.csv").exists(), name
    assert list(t["single"].quantity) == ["naive", "itt", "first_stage", "iv"]
    assert len(t["weak"]) == 6 and len(t["broken"]) == 3
