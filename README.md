# Spirometry

Measuring what Slay the Spire 2's early-access balance patches actually did.

**Status:** the pick-rate analysis of the numeric tweaks is finished. Results and design checks
are below and in [SPIROMETRY.md](SPIROMETRY.md), from the final rerun on the complete run
snapshot (2,071 export pages, downloaded by 2026-10-04). The write-up is field guide v2, "What
Did the Patch Do?", a study guide built from `writeup/` (152 pages so far; chapters 0–6 have
their math and code listings, the rest are still being reworked). Win effects (tooling built
and tested in simulation), the strength change across patches, partial pooling, the staggered
rollout, reworks and the dashboard are future work ([PLAN.md](PLAN.md)).

## The question

Slay the Spire 2's developers changed cards every few weeks during early access. Each change
is a natural experiment: the same card, before and after, played across hundreds of thousands
of community-submitted runs. For each change, this project estimates two things:

- **Behavior:** did players pick the card more or less often when it was offered?
- **Strength:** did picking it actually help runs win more or less?

Raw win rates can't answer the second question, because strong runs make different choices
than weak ones. The designs here lean on the fact that the game's RNG decides which cards are
offered, and on unchanged cards as a control for everything else that shifts between patches.
See [PLAN.md](PLAN.md) for the research questions and methods.

## Results so far

> Computed on the complete run export (2,071 pages, about 1.5 million distinct runs, play
> dates to 2026-10-04). No estimate moved by more than one standard error from the previous
> rebuild (1,873 pages); see SPIROMETRY.md, "Phase 5 results".

**What was tested.** 43 card changes where a single number changed: 26 in patch v0.103.2 and
17 in v0.107.1. The data are about 1.12 million solo, unmodded runs. For each changed card, the
question is how much its pick rate (picked / offered) changed, compared with unchanged cards
of the same character over the same builds (a difference-in-differences). Before that, an
offer-rate check confirms the patch didn't change how often the card is offered, since the
game's RNG decides the offers.

**Findings**

1. **Players responded to the changes, more in the first patch than the second.** In the first
   patch, 22 of 26 tweaks moved the pick rate by more than two standard errors, and 18 of
   the 21 with one direction moved the way the change pointed (median size across all 26:
   4.7 percentage points). In the second patch, 9 of 17 did, all 9 in the direction of the
   change (median size 1.7 points). Caveat: a placebo check on unchanged cards found the
   standard errors too small (placebo |z| > 2 in 72% of first-patch and 37% of second-patch
   fits, against 5% expected),
   so these counts are not calibrated; see SPIROMETRY.md, "Placebo calibration of the DiD
   errors". With each patch's errors scaled by its placebo spread (the lead count in the
   field guide), over the first four weeks: 13 of 26 first-patch tweaks, all 12 with one
   direction toward the change, and 2 of 17 second-patch tweaks.
   In `results/pick_rate_did.csv`, `clearly_nonzero_h_cal` gives those 13 of 26 and 2 of 17,
   applying the placebo factors in SPIROMETRY.md, "Placebo calibration of the DiD errors";
   `clearly_nonzero_cal` does the same over all weeks (13 of 26, 4 of 17). `clearly_nonzero_h`
   (first four weeks: 21 of 26, 8 of 17) and `clearly_nonzero` (all weeks: the 22 and 9 above)
   use uncalibrated clustered errors.
2. **One worked example.** Parry (a Regent card, main number 6 → 10) went from a 13.1% to a
   27.1% pick rate, while the unchanged Regent cards went from 27.8% to 27.3%. The estimated
   change is +14.5 points (95% interval +13.2 to +15.8). The largest drop is Corrosive Wave
   (a nerf): 42.3% → 28.6%, −15.9 points.
3. **In the first patch, bigger changes moved picks more.** On the log-odds scale the slope is
   1.40 ± 0.19 per unit of ln(new/old) (first four weeks after each release). In the second
   patch it is 0.05 ± 0.31: tweaks of the same size, measured equally well, moved picks a bit
   under half as much (median 1.9 against 4.1 points), with no visible relationship to size.
   Under the dose rules decided on 2026-10-09 (Reflect on the line, Debilitate's second-patch
   nerf off it) the second slope is 0.09 ± 0.40 and the difference between the patches is
   z = −2.97 (−3.0 to −3.1 with standard errors scaled by the placebo check). Why is open;
   see below. Caveat:
   "measured equally well" compares standard errors that the placebo check did not find
   calibrated (by different amounts in the two patches), so equal precision is not
   established.
4. **Reacting to the beta notes doesn't explain it for most of the tweaks it can test.**
   Players can see changes in the public beta before the stable release. The data allow the
   check for 16 of 43 tweaks, 12 of them with a clear main effect. For 10 of those 12 the
   pick-rate gap before the stable release is small or points the other way from the main
   effect, which is not what a reaction to the notes would look like; for two second-patch
   cards (Crescent Spear and Furnace) it moved the same way as the main effect, by more.

<!-- FIGURE 1: forest plot, every tweak's estimated change with its 95% interval (docs/figures/forest.png) -->
<!-- FIGURE 2: dose-response, one point per tweak, first and second patch drawn separately (docs/figures/dose_response.png) -->

**Checks.** The main estimates barely move when the fit drops the most active uploaders,
drops offers that shared a screen with the changed card, or drops controls affected by bug
fixes. Uploaders who use a community stats mod pick cards differently from other uploaders,
so the fits adjust for uploader group; fits on the mod users alone are noisier and shift more.
Three card changes (Patter in both patches and Sculpting Strike) were also offered more
often after their patch, so their estimates carry a caveat. A placebo check (the same fit
with an unchanged card as the "changed" card, 860 fits) gave z-scores with sd 4.2 where
honest errors give 1:
the clustered standard errors are not calibrated, for reasons not yet verified.

**Open questions.**
- Why the second patch shows no size relationship. Candidates: drift in a short "before"
  period (two upgrade-only placebo checks in the second patch moved by 2.1 and 5.0 standard
  errors when they shouldn't have, which points at drift rather than a real reaction),
  community-stats tooltips that arrived the day after v0.107.1, and the kind of number
  changed.
- The analysis measures what players *did*. Whether the changes altered how often picking
  the card *wins* is future work (tooling built and tested in simulation, not run on the full
  data).

**Limits.** Uploaders are self-selected and probably more dedicated than average players.
Other changes in the same patch, player learning and meta drift are handled only through the
unchanged-card comparison. These are estimates of pick-rate change relative to unchanged
cards, not proof of why players changed their picks.

## Repository

| File | What it is |
|---|---|
| [PLAN.md](PLAN.md) | Research questions, phases, status, decision log |
| [SPIROMETRY.md](SPIROMETRY.md) | Reference: data sources, record structure, known data issues |
| [CLAUDE.md](CLAUDE.md) | Standing instructions for Claude Code sessions |
| [LICENSE](LICENSE) | MIT, for the code; see "License and attribution" for the data |
| `notes/` | Investigation notes: patch history endpoints (`patch_history.md`), run file structure and table proposal (`run_schema.md`), patch notes vs. card tables (`patch_notes_crosscheck.md`), card versions and DiD windows (`treatment_table.md`); the Phase 5 design decks (`phase5_deck_v1.pdf`, `phase5_deck_v3.pdf`). Field guide v1, an earlier study guide on the 1,393-page tables, is kept locally and isn't in this repository; v2 is built from `writeup/` |
| `src/spirometry/` | The package. `patch_history.py` builds the card patch dataset from Spire Codex; `patch_notes.py` parses the official patch notes and reconciles `builds.csv`; `notes_crosscheck.py` compares the two; `treatment.py` builds the per-build card versions and DiD windows from them; `tweaks.py` builds the tweak size table for the dose-response plot; `exposure.py` builds the beta exposure table (first beta date and lead time per tweak); `runs.py` parses the run snapshot into Parquet + DuckDB run tables; `did.py` holds the Phase 5 estimation functions (offer-rate check, pick-rate DiD, event study, anticipation check, placebo calibration of the errors) that the analysis notebook calls; `wins.py` the win-effect functions (intent-to-treat and IV on each run's first reward screens); `strength.py` the strength change across a patch (IV before vs. after, net of unchanged cards) and the offer balance checks; `meta.py` the dose-response meta-regression (moved from notebook 02; optional per-patch SE inflation); `export.py` the results export (aggregate tables from the saved fits, for the dashboard); `sample_results.py` synthetic saved fits for the export's tests and the sample data; `sensitivity.py` the dose-response's sensitivity tables for the field guide (rulers, dose specs, review calls, mixed tweaks, leave-one-out, character terms, SE inflation, power by simulation); `iv_sim.py` the IV primer's simulated game as tables; `teaching_sims.py` the field guide's toy simulations (every toy from the reading notes, seeded, with known truth; their numbers become `toy.*` keys and their figures `fig_toy_*`); `checks.py` the field guide's design checks (fake patch, regression to the mean, token subset, control scope, per-group dose lines) summarised from the triage scripts' outputs, each labelled with its tables; `numbers.py` the field guide's numbers table (every printed number by key, formatted, with source and build stamp); `writeup.py` the field guide build (digit lint, math included; code listings extracted from this package; privacy, figure check, Typst compile); `site_figures.py` the website figure and chart data from notebook 02's saved fits (selection rules, per-week raw cells, JSON entries, site-styled event study), called by notebook 06 |
| `scripts/snapshot_export.py` | Downloads the run export, resumable, rate-limit aware |
| `scripts/make_sample_results.py` | Writes `results_sample/` by running the export on synthetic saved fits |
| `scripts/writeup/phil_runs.sh` | Everything the field guide needs that reads the run database, in order: notebook 01, the weeks 0–3 placebo run, the triage's design checks (into `triage/out_final/`), export with `--db`, sensitivity, checks, the toy simulations, numbers; stops at the first error, logs to `logs/phil_runs.log`, ends with the numbers summary; `--from <step>` resumes. About 1 h 15 min (estimate) |
| `scripts/writeup/figures.py` | Every field guide figure the saved outputs supply, one function per figure (matplotlib, the dashboard's Okabe-Ito colors), into `writeup/figures/<name>.png`; run after `phil_runs.sh` |
| `scripts/site_publish.sh` | Reruns notebook 06, checks it (no `/Users/` paths, 13/26 and 2/17, `index.html`'s `CAL` matches `PLACEBO_FACTORS_H3`), then copies the PNGs and JSON into the website repo's working tree and rebuilds `spirometry_cards.js`; commits nothing |
| `scripts/audit_extract.py` | Interim: compact audit tables from the snapshot (runs, aggregated offer counts) into `data/audit/` |
| `scripts/final_rerun.sh` | The final rerun, in order: audit extract, notebooks 01–05, placebo calibration and diagnostics, export, sensitivity tables, IV simulation; stops at the first error. Moves `data/analysis/` to `data/analysis_before_final_<time>/` first so nothing cached is reused; `--from <step>` resumes at a step (names in the script's header) and leaves `data/analysis/` in place; notebook logs in `logs/`. About 1 h 45 min (estimate) |
| `notebooks/` | Analysis notebooks. `01_data_audit.ipynb`: integrity, coverage, filters, population mix, offers, power. `02_pick_rate_did.ipynb`: offer-rate check, pick-rate DiD, event studies, robustness, dose-response. `03_anticipation.ipynb`: does the gap between a changed card and its controls already move at the first-beta date, on builds where players still have the old card? `iv_primer.ipynb`: a simulation showing why the naive win effect is biased and how the offer as an instrument fixes it. `04_dose_diagnostics.ipynb`: the dose-response under other rulers, leave-one-out and slopes by kind of number. `05_tweak_ledger.ipynb`: every derived dose next to the numbers it came from (writes `data/analysis/tweak_ledger.csv`). `06_site_figures.ipynb`: website deliverables from notebook 02's saved fits: the card selection (rules and checks), the Parry event-study figure and the interactive chart's data (`figures/site/`); its section 3 reads `runs.duckdb` |
| `triage/` | Record of a read-only investigation of the flat second patch (2026-10-07/08): `TRIAGE.md` (report and final synthesis), `scripts/` (each says how to run it), `out/` (card-level estimates, aggregates only), `figures/`. On the 1,873-page tables; not a result until rerun on the final tables. `out_final/`: the same scripts rerun on the final tables by `scripts/writeup/phil_runs.sh` (`TRIAGE_OUT`, `TRIAGE_AN`, `TRIAGE_COLORS`, `TRIAGE_DB` in `scripts/common.py` and `db.py`); `out/` is never written by the rerun. Sections M and N (exploratory: spillover, and card-level drift, against the placebo spread) ran on the final tables: `scripts/m_spillover.py`, `scripts/n_drift.py`, `out_final/m_*.csv`, `out_final/n_*.csv` |
| `reference/` | Small committed reference tables: game builds, card changes, text-only labels, patch-note card mentions, cross-check, bug-fix behavior changes, beta-only changes, change events, card-patch net fields, per-build card versions, DiD windows, numeric tweak sizes, beta exposure (+ raw caches in `reference/raw/`: Spire Codex API incl. the game's enchantment, event, encounter and monster lists used as mod markers, wiki pages; its README lists each source and license) |
| `writeup/` | Field guide v2 ("What Did the Patch Do?"): `OUTLINE.md` (the learning map written before the chapters), `main.typ` and `style.typ` (number function `#n`, boxes including COMMON MIX-UP / THE MATH, IN FULL / IN CODE, code listings, equations numbered by chapter, figure placeholders, answer key), `chapters/` (chapters 0–14 and appendices A–E: answer key, glossary and notation, numbers on one page, open items, "Talking about it"), `REWORK.md` (tracker for the 2026-10-22 rework: math, code and the reading notes). `numbers.json`/`numbers.csv` are generated and committed; `figures/`, `listings/` and `build/` are generated and git-ignored |
| `figures/site/` | Website deliverables written by notebook 06: `spirometry_parry.png`/`.pdf` (Parry's event study, placebo-calibrated weeks 0–3 band), `spirometry_patch1.png` (first-patch forest plot, 25 cards) and `spirometry_cards.json` (aggregates per card and week, for the interactive chart: calibrated counts, raw headline CIs that the site widens) |
| `data/runs/` | Run tables built locally by `spirometry.runs` (git-ignored, never committed) |
| `data/audit/` | Audit tables built locally by `scripts/audit_extract.py` (git-ignored) |
| `data/analysis/` | Saved fits from notebooks 02, 03 and 05 and the placebo calibration (`placebo_main.parquet` all weeks, `placebo_h3.parquet` weeks 0–3), notebook 01's aggregates (`audit_summary.csv`, `audit_runs_per_build.csv`, `audit_upload_lag.csv`) and the field guide's tables in `writeup/` (git-ignored). Earlier sets are kept beside it: `analysis_p949/` (first pass), `analysis_p1393/` (1,393-page tables), `analysis_p1873/` (1,873-page tables), `analysis_before_final_<time>/` (what `scripts/final_rerun.sh` moved aside), `analysis_prev/` (earlier fits; which tables they came from is not recorded here) |
| `dashboard/` | Streamlit dashboard (`app.py` pages, `charts.py` plots, `data.py` loading) on the exported tables; local only, not deployed |
| `results/` | Aggregate tables written by `spirometry.export` (committed) |
| `results_sample/` | Synthetic tables in the same layout, the dashboard's fallback when `results/` has no export (every page then says SAMPLE DATA) |
| `.streamlit/config.toml` | Dashboard theme (light: the chart colors are checked against it) |
| `tests/` | pytest tests; `tests/fixtures/sample_runs.jsonl` holds 7 synthetic records (6 runs, one solo run uploaded twice) written by `tests/fixtures/make_sample_runs.py`; no real run data is in git |

## Setup

The first block below needs nothing but Python: the tests run on synthetic data, and the
dashboard opens on the committed results in `results/`, falling back to the synthetic
`results_sample/` if they're missing. Most later steps read the run snapshot, which you download
yourself (it isn't in this repository), or tables built from it.

```bash
mamba create -n spirometry python=3.11
mamba activate spirometry
pip install -e .                  # core
pip install -e ".[analysis]"      # notebooks and analysis
pip install -e ".[dashboard]"     # results dashboard (streamlit, altair)
pip install -e ".[dev]"           # tests
pip install -e ".[writeup]"       # field guide PDF (typst)
python -m pytest
```

Download the run snapshot (resumable; the export allows 120 pages an hour and has a daily
cap, so it takes a few days; the script sleeps through the limits):

```bash
python scripts/snapshot_export.py              # run from the repo root
python scripts/snapshot_export.py --count-only # runs per build from what's saved
```

Build the run tables from the snapshot (Parquet in `data/runs/<table>/`, views in
`data/runs/runs.duckdb`; rebuilding overwrites them). Player IDs are hashed with a key that
must stay the same between builds: create it once, keep a backup, never commit it.

```bash
python -m spirometry.runs init-salt          # once: writes .spirometry_salt (git-ignored)
python -m spirometry.runs build              # all pages, one worker per CPU
python -m spirometry.runs build --pages 2    # quick test on the first 2 pages
# options: --snapshot sts2_snapshot --out data/runs --workers N
# (or set SPIROMETRY_SALT instead of the file)
```

Data audit (interim tables from the raw snapshot, then the notebook):

```bash
python scripts/audit_extract.py              # all pages -> data/audit/*.parquet (a few minutes)
python scripts/audit_extract.py --pages 20   # quick test
# then run notebooks/01_data_audit.ipynb
```

Rebuild the card patch dataset in `reference/` (reads the committed API cache; fetches only
what's missing, at most 10 requests per minute). The build applies the card-change decisions
in PLAN.md's decision log and, when `patch_notes_cards.csv` exists, reruns the cross-check
and adds the notes-only rows to `card_changes.csv`:

```bash
python -m spirometry.patch_history          # fetch missing + build
python -m spirometry.patch_history build    # build from the cache only
```

Parse the official patch notes (wiki mirror, cached in `reference/raw/wiki/`), reconcile
`builds.csv`, and rebuild the cross-check tables:

```bash
python -m spirometry.patch_notes            # fetch missing pages + build
python -m spirometry.patch_notes build      # build from the cache only
```

Build the treatment tables (card change events, card-patch net fields, per-build card versions, DiD windows at event and card-patch level) from
the reference tables above; prints the stable-window check and the counts:

```bash
python -m spirometry.treatment
```

`python -m spirometry.runs build` then adds `offers_with_version` to `runs.duckdb`
(`primary_offers` with the card version on each run's build).

Build the tweak size table (`reference/tweak_sizes.csv`) from the treatment tables:

```bash
python -m spirometry.tweaks
```

Build the beta exposure table (`reference/beta_exposure.csv`: first beta build and date,
lead time and beta steps per numeric tweak) from the reference tables:

```bash
python -m spirometry.exposure
```

The Phase 5 functions in `spirometry.did` run on the run tables from a notebook:

```python
import duckdb
import pandas as pd
from spirometry import did
con = duckdb.connect("data/runs/runs.duckdb", read_only=True)
df = did.load_window(con, "PARRY@v0.103.2/patch")
did.offer_rate_check(df, "PARRY@v0.103.2/patch")
did.fit_did(df, "PARRY@v0.103.2/patch")
results = did.run_all(con)            # every solo-estimable tweak
wide = did.run_all(con, control_scope="all")         # controls from every character ("other": other characters only)
did.control_pool_sizes(con)           # control cards and offers per tweak and scope
placebo = did.placebo_all(con)        # unchanged cards as pseudo-treated: z should be N(0, 1)
placebo.to_parquet("data/analysis/placebo_main.parquet")
did.placebo_summary(placebo)          # mean / sd of z, share |z| > 2 and > 3, by patch and size
did.placebo_summary(placebo, dedupe=True)            # one row per (window, pseudo card), robust sd
main = pd.read_parquet("data/analysis/did_main.parquet")  # a saved run_all result
pvr = did.placebo_vs_real(main, placebo)             # each tweak against its window's placebos
did.placebo_vs_real_by_patch(pvr, placebo)           # |beta| quantiles, real vs placebo
did.sign_agreement(main)              # tweaks toward the change, per patch
did.placebo_spread_by_feature(placebo)               # z spread by pick-rate and n_runs tercile
did.dose_response_sensitivity(main, {"x": (4.3, 2.1)})  # slope per patch, SEs inflated
did.anticipation_check(con, "PARRY@v0.103.2/patch")   # does the gap move at the beta date?
did.anticipation_weekly(con, "BULWARK@v0.107.1/patch")
did.anticipation_all(con, main=results)              # every tweak, beta_main from run_all
```

The win-effect functions in `spirometry.wins` (run tables from parser 1.7.0 or later):

```python
from spirometry import wins
data = wins.load_early(con, "ironclad", ["v0.103.2"])        # first 3 reward screens per run
wins.itt(data, "SETUP_STRIKE"); wins.first_stage(data, "SETUP_STRIKE"); wins.iv(data, "SETUP_STRIKE")
wins.reach_share(wins.early_runs(con, None, ["v0.103.2"]))  # share of runs reaching screen 3
results = wins.run_all_cards(con, "ironclad", ["v0.103.2"])  # every card with >= 500 offered runs
```

Strength change across a patch (`spirometry.strength`: the win-effect fits before vs. after
each numeric tweak, net of unchanged cards) and the offer balance checks:

```python
from spirometry import strength
res = strength.strength_change(con, "PARRY@v0.103.2/patch")  # Strength(blocks, changes, summary)
res = strength.strength_all(con)                  # every solo-estimable numeric tweak
strength.save(res, "data/analysis", "main")       # parquet; strength.load(...) reads it back
strength.balance_all(data, "ironclad")            # is the offer unrelated to pre-offer traits?
```

Tables for the field guide, from the saved fits (no run tables needed; CSVs in
`data/analysis/writeup/`, git-ignored):

```bash
python -m spirometry.sensitivity --analysis data/analysis --out data/analysis/writeup  # ~3 s
python -m spirometry.iv_sim --out data/analysis/writeup                               # ~5 s
python -m spirometry.teaching_sims --out data/analysis/writeup                        # ~7 s
```

`teaching_sims` runs only simulations (no data): `teaching_sims.csv` (one row per number the
guide may print, read by `spirometry.numbers` as `toy.<toy>.<quantity>`) and
`toy_<toy>_<part>.csv` for the figures; `--quick` uses fewer draws (tests).

`sensitivity` also writes `calibrated_counts.csv` (clearly nonzero on z scaled by the
placebo spread, per patch and horizon) and `placebo_by_horizon.csv` from every saved placebo
run (`placebo_main.parquet`, all weeks; `placebo_h3.parquet`, weeks 0–3, from
`did.placebo_run(con, "data/analysis", max_week_after=3)`), and `group_lines.csv` (the dose
line within each uploader group) from notebook 02's tagged / untagged fits.

The design checks of the field guide's chapter 12, from the triage scripts' outputs
(`triage/out_final/` when rerun on the final tables, else `triage/out/`, 1,873 pages; every
row says which):

```bash
python -m spirometry.checks --triage triage --analysis data/analysis --results results --out data/analysis/writeup
```

Everything above that needs the run database, in one unattended run (about 1 h 15 min,
estimate), then the figures (never run on the database; from the saved outputs):

```bash
bash scripts/writeup/phil_runs.sh          # log: logs/phil_runs.log; --from <step> resumes
python scripts/writeup/figures.py          # -> writeup/figures/*.png
```

The field guide's numbers table, after the export (with `--db`, which puts the build stamp
and the snapshot's play dates into `results/meta.json`) and the two commands above. It reads
`results/`, `data/analysis/` and `snapshot.log`, never the run database; it stops if an input
is older than the tables in `results/meta.json`, if the play dates are blank, or on anything
identifying. Writes `writeup/numbers.json` and `writeup/numbers.csv`, both committed:

```bash
python -m spirometry.numbers --analysis data/analysis --results results --out writeup/numbers.json
```

Build the field guide PDF (`writeup/build/field_guide_v2.pdf`, 152 pages on the final outputs
after the rework's phase 2). The full order on a fresh rerun: `scripts/writeup/phil_runs.sh`,
then `scripts/writeup/figures.py`, then the build below. It reuses `writeup/numbers.json`
(`--refresh-numbers` rebuilds it first). It stops on a hand-typed digit in a chapter (numbers go
through `#n("key")`; inside math and inline code a single digit is structure, but a decimal or a
multi-digit number is an error), a key missing from numbers.json, a code listing that no longer
resolves, a hashed-id-looking string, or a figure in `writeup/figures/` older than the run
tables. A figure not drawn yet prints a placeholder. The build extracts each
`#listing("name", ...)` / `#incode("name", ...)` from the package source (a function, or a
module-level constant such as `runs.PRIMARY_FILTER`) into `writeup/listings/` (git-ignored)
first; `listings` does only that step:

```bash
python -m spirometry.writeup build
python -m spirometry.writeup listings     # just extract the code listings
```

Rebuilding the real PDF from the saved outputs (no run database), as after a chapter edit or a
change to the toys:

```bash
python -m spirometry.teaching_sims --out data/analysis/writeup
python -m spirometry.sensitivity --analysis data/analysis --out data/analysis/writeup
python -m spirometry.iv_sim --out data/analysis/writeup
python -m spirometry.numbers --analysis data/analysis --results results --out writeup/numbers.json
python scripts/writeup/figures.py
python -m spirometry.writeup build
```

Export the pick-rate results for the dashboard: aggregate tables per tweak / week from the
fits notebooks 02 and 03 saved in `data/analysis/` (no run-level rows, no uploader IDs; the
export stops if a fit has an `error` row unless `--skip-errors`). `--db` reads `build_info`
and the first and last play date of the primary runs (read-only, aggregates only) for the
provenance in `meta.json`; without it those fields stay blank:

```bash
python -m spirometry.export --analysis data/analysis --out results --db data/runs/runs.duckdb
# options: --horizon h3 (fixed-horizon fit file) --skip-errors
#          --snapshot-end YYYY-MM-DD (overrides the end date from --db)
```

Run the dashboard locally (reads `results/`, or the synthetic `results_sample/` when
`results/` is empty; nothing is deployed):

```bash
streamlit run dashboard/app.py               # from the repo root
python scripts/make_sample_results.py        # regenerate results_sample/
```

`SPIROMETRY_SMOKE_DB=path/to/runs.duckdb python -m pytest tests/test_did.py tests/test_wins.py tests/test_strength.py tests/test_anticipation.py`
also runs the smoke tests on a build from fetched pages.

## License and attribution

The code is under the [MIT license](LICENSE), copyright 2026 Phillip Macias.

Run data and game data come from [Spire Codex](https://spire-codex.com)
([source](https://github.com/ptrlrd/spire-codex)), a community database of Slay the Spire 2
runs and game files. Raw run data is not included in this repository: player IDs are hashed
in all derived tables, only aggregates are published, and the test fixture is synthetic. The
cached Spire Codex responses in `reference/raw/` are not under the MIT license; see
[its README](reference/raw/README.md).

Patch notes are Mega Crit's, as transcribed on the [Slay the Spire Wiki](https://slaythespire.wiki.gg/wiki/Slay_the_Spire_2:Patch_Notes).
The wiki-derived files in `reference/raw/` and the tables derived from them are under
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) and keep that license.

Slay the Spire 2 belongs to Mega Crit. This project isn't affiliated with Mega Crit, and
neither is Spire Codex.
