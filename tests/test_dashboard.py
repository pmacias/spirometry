"""The dashboard's default page (Overview) runs without an exception on the committed sample
tables (results_sample/) and shows the SAMPLE DATA banner. Streamlit's AppTest can't switch
to st.navigation pages defined as functions, so the other pages were checked in a browser.
Skipped without the dashboard extra."""
import pathlib
import sys

import pytest

pytest.importorskip("streamlit")
pytest.importorskip("altair")
from streamlit.testing.v1 import AppTest  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = ROOT / "dashboard" / "app.py"


def test_overview_runs_on_sample(monkeypatch):
    if (ROOT / "results" / "pick_rate_did.csv").exists():
        pytest.skip("results/ exists; this test is for the sample tables")
    monkeypatch.syspath_prepend(str(APP.parent))
    # Streamlit's script runner replaces __main__ with the app and leaves it there; undo that,
    # or spawned workers in later tests (test_runs.py) re-run app.py and can't import charts.
    monkeypatch.setitem(sys.modules, "__main__", sys.modules["__main__"])
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("SAMPLE DATA" in w.value for w in at.warning)
    assert at.title[0].value == "Pick-rate change per tweak"
