"""Dump a notebook's cells and saved text outputs to plain text (read-only; no execution).

Usage: python triage/scripts/dump_notebook.py notebooks/04_dose_diagnostics.ipynb OUT.txt
Images are replaced by a placeholder; hex strings of 12+ characters (hashed IDs) are
redacted. Used to read saved outputs for the triage.
"""
import json
import re
import sys

nb = json.load(open(sys.argv[1]))
out = []
for i, c in enumerate(nb["cells"]):
    src = "".join(c.get("source", ""))
    out.append(f"\n===== cell {i} [{c['cell_type']}] =====\n{src}")
    for o in c.get("outputs", []):
        if "text" in o:
            out.append("--- out ---\n" + "".join(o["text"]))
        elif "data" in o:
            d = o["data"]
            if "text/plain" in d:
                out.append("--- out ---\n" + "".join(d["text/plain"]))
            elif "image/png" in d:
                out.append("--- out --- [image]")
        elif o.get("output_type") == "error":
            out.append("--- error --- " + o.get("ename", "") + ": " + o.get("evalue", ""))
text = re.sub(r"\b[0-9a-f]{12,}\b", "<REDACTED>", "\n".join(out))
open(sys.argv[2], "w").write(text)
