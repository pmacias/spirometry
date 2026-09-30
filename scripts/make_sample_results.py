"""Write results_sample/: synthetic results for the dashboard, made by running the real
export (spirometry.export) on synthetic saved fits (spirometry.sample_results). Nothing
here comes from run data; cards are named SAMPLE_01, SAMPLE_02, ...

    python scripts/make_sample_results.py            # run from the repo root
    python scripts/make_sample_results.py --seed 3 --out results_sample
"""
import argparse
import json
import pathlib
import tempfile

from spirometry import export, sample_results


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--out", default="results_sample")
    p.add_argument("--seed", type=int, default=0)
    a = p.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        sample_results.write_inputs(tmp / "analysis", tmp / "reference", seed=a.seed)
        t = export.export(tmp / "analysis", a.out, tmp / "reference", sample=True)
    # provenance for a synthetic export: no inputs on disk, and no snapshot to describe
    m = t["meta"]
    m.update(inputs={}, generator=f"scripts/make_sample_results.py --seed {a.seed}",
             exported_at_utc=m["exported_at_utc"][:10])
    m["blank_reasons"] = {k: "synthetic sample data" for k in m["blank_reasons"]}
    (pathlib.Path(a.out) / "meta.json").write_text(json.dumps(m, indent=2) + "\n")
    print(f"synthetic results -> {a.out}/")


if __name__ == "__main__":
    main()
