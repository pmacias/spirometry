"""Loading the exported tables for the dashboard.

The dashboard reads only the aggregate tables `python -m spirometry.export` writes:
results/ when it exists, otherwise results_sample/ (synthetic, from
scripts/make_sample_results.py). Nothing here touches run data.
"""
import json
import pathlib

import pandas as pd
import streamlit as st

ROOT = pathlib.Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
SAMPLE = ROOT / "results_sample"
TABLES = ["pick_rate_did", "flags", "weekly", "dose_response", "robustness", "anticipation"]


def results_dir():
    """(folder, is_sample): results/ if it holds an export, else results_sample/."""
    if (RESULTS / "pick_rate_did.csv").exists():
        return RESULTS, False
    return SAMPLE, True


@st.cache_data
def _read(path, mtime):                       # mtime: reload when the export is rerun
    text = {c: str for c in ["old", "new", "upgrade_old", "upgrade_new", "reason"]}
    return pd.read_csv(path, keep_default_na=False, na_values=[""], dtype=text)


def load():
    """Every table that exists, as DataFrames, plus 'meta' (dict) and 'is_sample'."""
    folder, is_sample = results_dir()
    if not (folder / "pick_rate_did.csv").exists():
        st.error(f"No exported tables in {folder}. Run `python -m spirometry.export` or "
                 "`python scripts/make_sample_results.py` first.")
        st.stop()
    out = {}
    for name in TABLES:
        path = folder / f"{name}.csv"
        if path.exists():
            out[name] = _read(str(path), path.stat().st_mtime)
    meta_path = folder / "meta.json"
    out["meta"] = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    out["is_sample"] = is_sample or bool(out["meta"].get("sample"))
    out["folder"] = folder
    for name in ["pick_rate_did", "anticipation"]:
        if name in out:
            out[name] = out[name].assign(label=card_labels(out[name]))
    return out


def card_name(card_id):
    """PARRY -> Parry, SIC_EM -> Sic Em (as the notebooks label cards)."""
    return str(card_id).replace("_", " ").title()


def card_labels(df):
    """Card name, plus the stable build when a card has more than one tweak in the table
    (Untouchable changed in both patches)."""
    names = df.card_id.map(card_name)
    repeated = names.duplicated(keep=False)
    build = df.card_patch_id.str.extract(r"@([^/]+)/")[0]
    return names.where(~repeated, names + " (" + build + ")")
