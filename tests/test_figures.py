"""scripts/writeup/figures.py on synthetic outputs (sample_results.write_numbers_inputs):
every figure is drawn, a missing input is skipped and named. No run data."""
import importlib.util
import pathlib

import pytest

from spirometry import sample_results

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "writeup" / "figures.py"


@pytest.fixture(scope="module")
def figures():
    spec = importlib.util.spec_from_file_location("figures", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def dirs(tmp_path_factory):
    t = tmp_path_factory.mktemp("fig")
    a, r, ref = t / "analysis", t / "results", t / "ref"
    sample_results.write_numbers_inputs(a, r, ref, seed=2)
    return dict(analysis=a, results=r, ref=ref, triage=t / "triage")


def test_every_figure_drawn(figures, dirs, tmp_path):
    out = tmp_path / "figs"
    drawn, skipped = figures.draw(out=out, **dirs)
    assert skipped == {}
    assert drawn == [f.__name__ for f in figures.FIGURES]
    for name in drawn:
        p = out / f"{name}.png"
        assert p.exists() and p.stat().st_size > 5000, name
        assert p.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_missing_input_skipped_and_named(figures, dirs, tmp_path):
    d = dict(dirs, analysis=tmp_path / "empty")
    drawn, skipped = figures.draw(out=tmp_path / "f", only=["fig_dose", "fig_timeline"], **d)
    assert drawn == ["fig_timeline"] and "dose_points.csv" in skipped["fig_dose"]


def test_cli_only(figures, dirs, tmp_path, capsys):
    out = tmp_path / "c"
    figures.main(["--analysis", str(dirs["analysis"]), "--results", str(dirs["results"]),
                  "--ref", str(dirs["ref"]), "--triage", str(dirs["triage"]),
                  "--out", str(out), "--only", "fig_forest"])
    assert [p.name for p in out.iterdir()] == ["fig_forest.png"]
    with pytest.raises(SystemExit, match="unknown figure"):
        figures.main(["--only", "fig_nope"])
