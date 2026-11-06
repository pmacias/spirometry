"""The dashboard's default page (Overview) runs without an exception on the committed sample
tables (results_sample/, whatever results/ holds) and shows the SAMPLE DATA banner.
Streamlit's AppTest can't switch to st.navigation pages defined as functions, so the other
pages were checked in a browser. Skipped without the dashboard extra."""
import importlib
import pathlib
import sys

import pytest

pytest.importorskip("streamlit")
pytest.importorskip("altair")
from streamlit.testing.v1 import AppTest  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = ROOT / "dashboard" / "app.py"


def test_overview_runs_on_sample(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(APP.parent))
    # The app reads results/ when it holds an export, so point that at an empty folder. AppTest
    # runs in this process: the app's `import data` gets this same module.
    monkeypatch.setattr(importlib.import_module("data"), "RESULTS", tmp_path)
    # Streamlit's script runner replaces __main__ with the app and leaves it there; undo that,
    # or spawned workers in later tests (test_runs.py) re-run app.py and can't import charts.
    monkeypatch.setitem(sys.modules, "__main__", sys.modules["__main__"])
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("SAMPLE DATA" in w.value for w in at.warning)
    assert at.title[0].value == "Pick-rate change per tweak"
    assert any("results_sample" in c.value for c in at.sidebar.caption)
