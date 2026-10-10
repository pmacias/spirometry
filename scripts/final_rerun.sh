#!/usr/bin/env bash
# Final rerun on the final run tables (PLAN.md, Next up 15, task 8). In order: audit extract,
# notebooks 01-05, the placebo calibration and its diagnostics, the export, the sensitivity
# tables and the IV primer's simulation. Stops at the first failing step; each step is echoed
# with a UTC timestamp, and again with its run time when it finishes.
#
#   mamba activate spirometry
#   bash scripts/final_rerun.sh 2>&1 | tee logs/final_rerun.log
#   bash scripts/final_rerun.sh --from placebo 2>&1 | tee -a logs/final_rerun.log
#
# Steps, in order (names for --from):
#   audit         python scripts/audit_extract.py
#   nb01          notebooks/01_data_audit.ipynb
#   nb02          notebooks/02_pick_rate_did.ipynb
#   nb03          notebooks/03_anticipation.ipynb
#   nb04          notebooks/04_dose_diagnostics.ipynb
#   nb05          notebooks/05_tweak_ledger.ipynb
#   placebo       did.placebo_all -> data/analysis/placebo_main.parquet
#   diagnostics   data/analysis/placebo_diagnostics_*.csv (no refit)
#   export        python -m spirometry.export
#   sensitivity   python -m spirometry.sensitivity
#   iv_sim        python -m spirometry.iv_sim
#
# --from <step>: skip the steps before <step> (to resume after a failure). The checks still
# run, but data/analysis/ is NOT moved aside, so the skipped steps' outputs from the
# interrupted run stay in place for the later steps. (Notebook 03 reuses
# anticipation_main.parquet when it is newer than runs.duckdb.)
#
# Without --from no cached fit is reused: before anything runs, data/analysis/ is moved
# (renamed, nothing deleted) to data/analysis_before_final_<UTC time>/ and an empty
# data/analysis/ takes its place, so notebooks 02 and 03 refit everything and the export, the
# sensitivity tables and notebooks 04-05 read only fits made in this run. The script refuses
# to start without the backup data/analysis_p1873/.
#
# Notebooks run in place with no cell timeout. nbconvert writes a notebook only when every
# cell succeeds, so a failed notebook keeps its old outputs; its log is logs/<notebook>.log.
# Expected run time: about 1 h 45 min (PLAN.md, Phase 5, task 6 entry; an estimate).
set -Eeuo pipefail              # -E: the ERR trap below also fires inside functions

STEPS=(audit nb01 nb02 nb03 nb04 nb05 placebo diagnostics export sensitivity iv_sim)

usage() { echo "usage: $0 [--from <step>]   steps: ${STEPS[*]}" >&2; exit 2; }

FROM=""
while [ $# -gt 0 ]; do
    case $1 in
        --from) [ $# -ge 2 ] || usage; FROM=$2; shift 2 ;;
        --from=*) FROM=${1#--from=}; shift ;;
        -h|--help) usage ;;
        *) echo "unknown argument: $1" >&2; usage ;;
    esac
done
if [ -n "$FROM" ] && [[ " ${STEPS[*]} " != *" $FROM "* ]]; then
    echo "unknown step for --from: $FROM" >&2
    usage
fi

cd "$(dirname "$0")/.."

CURRENT="preflight"
ts() { date -u '+%Y-%m-%d %H:%M:%S UTC'; }
trap 'rc=$?; echo "[$(ts)] FAILED: $CURRENT (exit $rc)" >&2' ERR

# Steps before --from are skipped; STARTED flips when the --from step is reached.
STARTED=$([ -z "$FROM" ] && echo 1 || echo 0)

run() {
    local step=$1
    shift
    [ "$step" = "$FROM" ] && STARTED=1
    if [ "$STARTED" != 1 ]; then
        echo "[$(ts)] SKIP  $step (before --from $FROM)"
        return 0
    fi
    CURRENT=$step
    echo
    echo "[$(ts)] START $CURRENT"
    local t0=$SECONDS
    "$@"
    echo "[$(ts)] DONE  $CURRENT ($((SECONDS - t0)) s)"
}

notebook() {
    local log="logs/$1.log"
    if ! jupyter nbconvert --to notebook --execute --inplace \
            --ExecutePreprocessor.timeout=-1 "notebooks/$1.ipynb" >"$log" 2>&1; then
        tail -n 40 "$log" >&2
        return 1
    fi
}

preflight() {
    command -v python >/dev/null || { echo "python not found (activate the env)" >&2; return 1; }
    command -v jupyter >/dev/null || { echo "jupyter not found (activate the env)" >&2; return 1; }
    python -c "import spirometry.did, spirometry.export, spirometry.sensitivity, spirometry.iv_sim"
    [ -f data/runs/runs.duckdb ] || { echo "data/runs/runs.duckdb not found" >&2; return 1; }
    [ -d data/analysis_p1873 ] || { echo "backup data/analysis_p1873/ not found" >&2; return 1; }
    # Notebook 02 refits only with FORCE = True (notebook 03 refits when its file is missing).
    grep -q '"FORCE = True ' notebooks/02_pick_rate_did.ipynb \
        || { echo "notebooks/02_pick_rate_did.ipynb: FORCE is not True" >&2; return 1; }
    mkdir -p logs
    if [ -n "$FROM" ]; then
        [ -d data/analysis ] || { echo "--from given but data/analysis/ not found" >&2; return 1; }
        echo "--from $FROM: data/analysis/ left in place"
        return 0
    fi
    local aside
    aside="data/analysis_before_final_$(date -u '+%Y%m%dT%H%M%SZ')"
    if [ -d data/analysis ]; then
        mv data/analysis "$aside"
        echo "moved data/analysis/ to $aside/"
    fi
    mkdir -p data/analysis
}

placebo_calibration() {
    # did.placebo_all with the defaults of the 2026-10-02 run: all weeks, same-color
    # controls, 20 pseudo cards per tweak, seed 0. Reads did_main only through its tweaks.
    python - <<'PY'
import time
import duckdb
from spirometry import did

con = duckdb.connect("data/runs/runs.duckdb", read_only=True)
con.execute("SET enable_progress_bar = false")
t0 = time.time()
placebo = did.placebo_all(con)
con.close()
placebo.to_parquet("data/analysis/placebo_main.parquet")
n_err = int((placebo.error.fillna("") != "").sum())
print(f"placebo_all: {len(placebo)} fits on {placebo.card_patch_id.nunique()} tweaks, "
      f"{n_err} errors, {time.time() - t0:.0f} s")
PY
}

placebo_diagnostics() {
    # From the saved parquets, no refit: data/analysis/placebo_diagnostics_*.csv.
    python - <<'PY'
import pathlib
import pandas as pd
from spirometry import did, sensitivity

an = pathlib.Path("data/analysis")
placebo = pd.read_parquet(an / "placebo_main.parquet")
main = pd.read_parquet(an / "did_main.parquet")
summary = pd.concat([did.placebo_summary(placebo), did.placebo_summary(placebo, dedupe=True)],
                    ignore_index=True)
pvr = did.placebo_vs_real(main, placebo)
tables = {
    "summary": summary,
    "vs_real": pvr,
    "vs_real_by_patch": did.placebo_vs_real_by_patch(pvr, placebo),
    "sign_agreement": did.sign_agreement(main),
    "spread_by_feature": did.placebo_spread_by_feature(placebo),
    "dose_sensitivity": did.dose_response_sensitivity(main, sensitivity.placebo_factors(summary)),
}
for name, t in tables.items():
    t.to_csv(an / f"placebo_diagnostics_{name}.csv", index=False)
    print(f"placebo_diagnostics_{name}.csv: {len(t)} rows")
print(summary[summary.split.isin(["all", "patch"])]
      [["dedupe", "split", "level", "n_fits", "sd_z", "robust_sd_z"]].to_string(index=False))
PY
}

echo "[$(ts)] START preflight${FROM:+ (--from $FROM)}"
preflight                       # always runs, whatever --from says
echo "[$(ts)] DONE  preflight"
run "audit" python scripts/audit_extract.py
run "nb01" notebook 01_data_audit
run "nb02" notebook 02_pick_rate_did
run "nb03" notebook 03_anticipation
run "nb04" notebook 04_dose_diagnostics
run "nb05" notebook 05_tweak_ledger
run "placebo" placebo_calibration
run "diagnostics" placebo_diagnostics
run "export" python -m spirometry.export --analysis data/analysis --out results \
    --db data/runs/runs.duckdb
run "sensitivity" python -m spirometry.sensitivity --analysis data/analysis \
    --out data/analysis/writeup
run "iv_sim" python -m spirometry.iv_sim --out data/analysis/writeup

trap - ERR
echo
echo "[$(ts)] final rerun complete (${SECONDS} s)"
