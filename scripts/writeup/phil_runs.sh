#!/usr/bin/env bash
# Everything the field guide needs that reads the run database (PLAN.md, Next up 15, task A
# of 2026-10-16), in order, unattended. Stops at the first failing step; every step is
# echoed with a UTC timestamp and its run time; the whole run is appended to
# logs/phil_runs.log. Ends by printing the numbers table's summary.
#
#   mamba activate spirometry
#   bash scripts/writeup/phil_runs.sh                 # all steps
#   bash scripts/writeup/phil_runs.sh --from export   # resume at a step after a failure
#
# Steps (names for --from):
#   nb01        notebooks/01_data_audit.ipynb (reads data/audit/ only): refreshes its outputs
#               and writes data/analysis/audit_summary.csv, audit_runs_per_build.csv,
#               audit_upload_lag.csv. (The CSVs were written once by running the notebook's
#               code outside Jupyter; the sandbox that did it can't start a kernel.)
#   placebo_h3  did.placebo_run(max_week_after=3): the weeks 0-3 placebo calibration, the
#               2026-10-02 settings otherwise (same-color controls, 20 cards per tweak,
#               seed 0) -> data/analysis/placebo_h3.parquet, beside placebo_main.parquet.
#   triage      the design checks of chapter 12, rerun on the final tables by their triage
#               scripts -> triage/out_final/ (never triage/out/, which is checked unchanged):
#                 i_fake_patch.py               fake patch v0.103.2 -> v0.103.3
#                 j_reversion.py                regression to the mean (saved fits only)
#                 g3_token_subset.py --all      token subset and token-clustered placebos
#                 g3_analysis.py                (prints G3/G4 for the log)
#                 l_control_scope.py --scope other / --scope all   control scope, weeks 0-3
#                 l_compare.py                  (prints the scope x ruler table for the log)
#               Card colors come from reference/raw/cards.json, as in the saved fits
#               (TRIAGE_COLORS=reference). The per-group dose lines need no rerun: they come
#               from notebook 02's saved tagged / untagged fits (sensitivity step).
#   export      python -m spirometry.export --db (meta.json: build stamp, play dates and
#               build_info's dedup counts)
#   sensitivity python -m spirometry.sensitivity (calibrated counts at both horizons, the
#               placebo spread by horizon, the per-group dose lines, ...)
#   checks      python -m spirometry.checks -> data/analysis/writeup/design_checks.csv
#   numbers     python -m spirometry.numbers -> writeup/numbers.json (rebuilt from scratch)
#
# Expected run time: about 1 h 15 min (an estimate from the 2026-10-09/10 rerun and the
# triage's timings: placebo about 45 min, control scope about 25 min for both scopes, the
# rest a few minutes). Peak memory about 6 GB (control scope "all").
set -Eeuo pipefail

STEPS=(nb01 placebo_h3 triage export sensitivity checks numbers)
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

cd "$(dirname "$0")/../.."
mkdir -p logs

DB=data/runs/runs.duckdb
AN=data/analysis
TRIAGE_FINAL=triage/out_final
CURRENT="preflight"
ts() { date -u '+%Y-%m-%d %H:%M:%S UTC'; }

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

preflight() {
    command -v python >/dev/null || { echo "python not found (activate the env)" >&2; return 1; }
    command -v jupyter >/dev/null || { echo "jupyter not found (activate the env)" >&2; return 1; }
    python -c "import spirometry.did, spirometry.export, spirometry.sensitivity, spirometry.checks, spirometry.numbers"
    [ -f "$DB" ] || { echo "$DB not found" >&2; return 1; }
    for f in did_main did_h3 did_h3_tagged did_h3_untagged event_studies placebo_main; do
        [ -f "$AN/$f.parquet" ] || { echo "$AN/$f.parquet not found (final rerun first)" >&2; return 1; }
    done
    [ -f reference/raw/cards.json ] || { echo "reference/raw/cards.json not found" >&2; return 1; }
    [ -d data/audit ] || { echo "data/audit/ not found" >&2; return 1; }
}

notebook01() {
    local log="logs/01_data_audit.log" mark
    mark=$(mktemp)
    if ! jupyter nbconvert --to notebook --execute --inplace \
            --ExecutePreprocessor.timeout=-1 notebooks/01_data_audit.ipynb >"$log" 2>&1; then
        tail -n 40 "$log" >&2
        return 1
    fi
    for f in audit_summary audit_runs_per_build audit_upload_lag; do
        [ "$AN/$f.csv" -nt "$mark" ] || { echo "$AN/$f.csv not rewritten by the notebook" >&2; return 1; }
    done
    rm -f "$mark"
}

placebo_h3() {
    python - <<'PY'
import time
import duckdb
from spirometry import did

con = duckdb.connect("data/runs/runs.duckdb", read_only=True)
con.execute("SET enable_progress_bar = false")
t0 = time.time()
out = did.placebo_run(con, "data/analysis", max_week_after=3)
con.close()
n_err = int((out.error.fillna("") != "").sum())
print(f"placebo_all (weeks 0-3): {len(out)} fits on {out.card_patch_id.nunique()} tweaks, "
      f"{n_err} errors, {time.time() - t0:.0f} s -> data/analysis/placebo_h3.parquet")
if n_err:
    raise SystemExit(f"{n_err} placebo fits failed")
PY
}

triage() {
    local before after
    before=$(shasum triage/out/* | shasum)
    mkdir -p "$TRIAGE_FINAL"
    export TRIAGE_OUT=$TRIAGE_FINAL TRIAGE_AN=$AN TRIAGE_COLORS=reference TRIAGE_DB=$DB
    local t cmd
    # fits (a failure stops the run) and printouts (their inputs are saved; a failure there
    # is reported and the run goes on)
    for cmd in "fit i_fake_patch.py" "fit j_reversion.py" "fit g3_token_subset.py --all" \
               "print g3_analysis.py" "fit l_control_scope.py --scope other" \
               "fit l_control_scope.py --scope all" "print l_compare.py"; do
        t=$SECONDS
        echo "[$(ts)]   triage/scripts/${cmd#* }"
        if [ "${cmd%% *}" = print ]; then
            # shellcheck disable=SC2086
            python triage/scripts/${cmd#* } \
                || echo "[$(ts)]   WARNING: ${cmd#* } failed (printout only; run goes on)"
        else
            # shellcheck disable=SC2086
            python triage/scripts/${cmd#* }
        fi
        echo "[$(ts)]   ... $((SECONDS - t)) s"
    done
    unset TRIAGE_OUT TRIAGE_AN TRIAGE_COLORS TRIAGE_DB
    after=$(shasum triage/out/* | shasum)
    [ "$before" = "$after" ] || { echo "triage/out/ changed: it must stay the 1,873-page record" >&2; return 1; }
    ls -l "$TRIAGE_FINAL"
}

summary() {
    python - <<'PY'
import json
from collections import Counter
j = json.load(open("writeup/numbers.json"))
n = j["numbers"]
fam = Counter(k.split(".")[0] for k in n)
print(f"\nnumbers.json: {len(n)} keys; tables built {j['build']['tables_built_at_utc']}, "
      f"{j['build']['snapshot_pages']} pages")
print("  by family: " + ", ".join(f"{k} {v}" for k, v in sorted(fam.items())))
for k in ["snapshot.distinct_runs", "did.h3.first.calibrated.clearly_nonzero",
          "did.h3.second.calibrated.clearly_nonzero", "did.h3.first.calibrated.factor",
          "did.h3.second.calibrated.factor", "placebo.h3.pairs.all.robust_sd_z",
          "dedup.exact_repeats_dropped", "checks.fake_patch.h3.slope_pm",
          "checks.control_scope.other.primary.z_diff", "checks.token.subset.run_clustered.z_diff"]:
    r = n.get(k)
    print(f"  {k:48s} {r['text'] if r else 'MISSING'}" + (f"   [{r['spec']}]" if r and r["spec"] else ""))
tables = sorted({(k.split(".")[1], r["spec"]) for k, r in n.items() if k.startswith("checks.")})
print("  design checks: " + "; ".join(f"{c} ({s})" for c, s in tables))
for m in j["build"]["missing"]:
    print(f"  missing: {m['keys']} ({m['reason']})")
PY
}

main() {
    trap 'rc=$?; echo "[$(ts)] FAILED: $CURRENT (exit $rc); resume with --from $CURRENT" >&2' ERR
    echo "[$(ts)] START phil_runs${FROM:+ (--from $FROM)}"
    CURRENT=preflight
    preflight
    echo "[$(ts)] DONE  preflight"
    run nb01 notebook01
    run placebo_h3 placebo_h3
    run triage triage
    run export python -m spirometry.export --analysis "$AN" --out results --db "$DB"
    run sensitivity python -m spirometry.sensitivity --analysis "$AN" --out "$AN/writeup"
    run checks python -m spirometry.checks --triage triage --analysis "$AN" \
        --results results --out "$AN/writeup"
    run numbers python -m spirometry.numbers --analysis "$AN" --results results \
        --out writeup/numbers.json
    CURRENT=summary
    summary
    trap - ERR
    echo
    echo "[$(ts)] phil_runs complete (${SECONDS} s). Next: python scripts/writeup/figures.py"
}

# Everything through tee into the log (no prompts: it runs unattended); the exit status is
# main's, not tee's.
set +e
main 2>&1 | tee -a logs/phil_runs.log
exit "${PIPESTATUS[0]}"
