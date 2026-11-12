# Spirometry plan

Roadmap and status. `SPIROMETRY.md` is the reference (scope, data, known issues); this file
says what the project is trying to answer, what gets built in what order, by whom, and what
"done" means.

## Research questions

For each card change (the post-change version going live in a build):

1. **Behavior.** Effect on pick rate given offered: change in P(picked | offered),
   post vs. pre, net of the same change for unchanged cards of the same character
   (difference-in-differences).
2. **Strength.** Effect on winning: within each build, the offer (decided by the game's
   RNG) instruments picking, giving a selection-free effect of picking the card on
   winning. Compare pre vs. post, net of unchanged cards.
3. **Perception vs. strength.** Do pick-rate changes track strength changes, or do
   players over- or under-react to patches?
4. **Dose-response.** For numeric tweaks, effect size against change size.

Unit: one card offer (run, floor, card, build). Treatment: card version live in the
run's build. Main threats: other changes in the same patch, player learning, meta drift,
uploader mix. Unchanged cards are the control for all of these, except changes to
interacting cards (synergies), which need to be flagged.

**Minimum result:** pick-rate DiD with uncertainty for every numeric tweak, plotted against
change size. Win effects (noisier: a single card is a small part of a run, and the
instrumented estimate divides by the pick rate) and the perception-vs-strength comparison
follow.

Reworks change what a card is, not how much of it there is, so they get before/after
estimates but no place on the dose-response curve.

## How work flows

- **GitHub `main` is the source of truth.** Everything else catches up from it.
- **CC cloud sessions** build pipeline code on a branch and open a PR. They develop against a
  page or two of runs they fetch themselves; they never touch the full snapshot.
- **Phil** reviews every PR ("Files changed"), merges (squash), then `git pull` locally and
  syncs the claude.ai project.
- **Heavy data runs locally.** The raw snapshot and anything derived from it live on Phil's Mac
  and are git-ignored. Only code, small reference tables, and notes are committed.
- **Analysis is Phil's.** CC builds tables and tooling; Phil writes the analysis notebooks and
  makes the plots.

## Phases

### 0. Scoping and access — done
Data source chosen (Spire Codex), export and cloud access verified, repo and cloud environment
set up, patch history endpoints checked (`notes/patch_history.md`).

### 1. Data acquisition — in progress
- [x] Full run snapshot (local). Done when the export reports its end and
      `--count-only` has been run. Record the start date as "snapshot as of."
      *Status: complete. The export reached its end on 2026-10-04 12:22 PDT: 2,071 pages
      (files 0–2,070; `snapshot.log` numbers pages from 1, so its last line says "page 2071",
      a short page of 668 runs). `--count-only` (same log): 2,069,493 records, including the
      75,996 re-downloaded repeats below; 1,525,369 distinct by (seed, start_time); 345,006
      with a `player_token`. The run tables of 2026-10-02 (1,873 pages, 1,871,830 records)
      predated the end and missed the last 198 pages; the final rebuild of 2026-10-09 covers
      all 2,071 (Phase 3). Snapshot start date: not in the part of the log checked (left
      blank). A daily request cap was found during the download. Pages 873–948 were fetched
      again once, as files 949–1024 (identical apart from `player_token`; dropped by the
      parsers; see SPIROMETRY.md). Download log checked 2026-09-28: no other overlap.*
- [ ] Card patch dataset (CC): `reference/builds.csv`, `reference/card_changes.csv`,
      excluded fields, text-only changes. Done when merged and Phil has reviewed the
      whitelist, the text-only list, and the build mapping.
      *Status: built and merged; text-only changes hand-labeled (`text_only_labels.csv`).
      Cross-checked against the official patch notes (PR): 115 of 128 card-patches are in
      the notes, all 69 with comparable numbers match, 4 `tweak`s look like reworks,
      12 notes-only changes. builds.csv reconciled with the wiki's version list (4
      versions added, hotfix branches and dates filled). Phil's decisions applied by the
      build scripts (PR): 4 relabels to rework, 12 notes-only `mechanic` rows, 3 `artifact`
      card-patches in `card_changes.csv` and 5 in `beta_card_changes.csv`; numeric-tweak
      set = 50 card-patches.*
- [x] Run file structure (CC): `notes/run_schema.md`, from 3 export pages. Merged;
      decisions in the decision log.

### 2. Data audit — Phil
Look at the data before building anything on it. Notebook `01_data_audit`.
- Runs per build, raw and deduplicated; which builds are too thin to use.
- Beta vs. stable run counts (decides whether the staggered-rollout design is possible).
- Cheated / modded / abandoned runs: how many, how to filter.
- Character and ascension mix per build; uploader mix over time (self-selection check).
- Decide the unit of analysis: run or player-run (co-op).
Done when the filters and the unit are written into `SPIROMETRY.md`.
*Status: first pass done on 949 pages, rerun 2026-09-29 on 1,513 pages, with interim
tooling: `scripts/audit_extract.py` writes aggregate tables to `data/audit/` (git-ignored), read by
`notebooks/01_data_audit.ipynb`. Findings so far are in SPIROMETRY.md (Known data issues):
non-release builds, runs dated before release, `_sts` = SlayTheStats upload stamp and the
ranking difference between uploader groups, mod-marker counts, cheat candidates. Unit:
card offer, solo runs (already in the decision log). Decisions written into SPIROMETRY.md
("Audit decisions"): primary population, thin-build pooling rule, staggered rollout feasible
within branch, snapshot reach and backfill, uploader groups, within-build win-rate drift.
Rerun: decisions unchanged; backfill numbers recorded (provisional); thin builds now
v0.99.0, v0.103.1 and v0.110.0 (v0.105.0 and v0.109.1 no longer thin); rising ascension
does not explain the within-build drift (mean ascension fell). Open: the thin-build check
and backfill numbers on the finished snapshot; v0.110.0's patch notes for the pooling
rule. The notebook moves to the Phase 3 tables once they're built on the full snapshot.*

### 3. Run tables — CC builds, Phil runs locally
Parse raw runs into DuckDB/Parquet. Player IDs hashed.
- `runs`: one row per run (build, branch, character, ascension, win, floor reached, flags).
- `card_offers`: one row per card offered (run, floor, act, card, upgraded, picked). This is
  the core table for every design below.
- `deck_final`, `deaths` (encounter, floor), and relic/event choices later.
Done when tests pass on sample pages and the full snapshot builds locally without errors.
*Status: parser merged: `python -m spirometry.runs build` writes `runs`,
`run_players`, `card_offers`, `shop_offers` (Parquet, one file per page) and `runs.duckdb`
with views `runs_dedup`, `card_offers_dedup`, `primary_offers`. Tested on the fixture and
2 fetched pages (~1.5 s per page per worker). Follow-up PR (CC, parser 1.1.0): `runs` flags
`released`, `before_release`, `neow_start`, `has_player_token`; mod characters by the
five-character list; `primary_offers` applies the audit's primary population and keeps
event-then-fight floors (`event_fight`); counts in `build_info`. Tested on the fixture and
2 fetched pages. The first full build (949 pages) crashed on an enchantment amount too
large for SMALLINT in three modded runs; fix PR (parser 1.2.0): wider integer types, a
failing page is skipped and reported instead of aborting the build, and enchantments
outside the game's list are a mod marker. Parser 1.3.0 (PR): events, encounters and
monsters outside the game's lists are a mod marker too (`runs.mod_markers`,
`runs.mod_entities`; `build_info.runs_mod_entity_only` counts the runs it newly flags).
Parser 1.5.0 (PR, CC): `primary_offers` takes runs from `runs_dedup`, so a solo run
uploaded twice under different `run_hash`es counts once; `build_info` counts such
`run_key`s (`solo_run_keys_multi_record`) and the rows removed
(`primary_offers_dedup_removed`). Fixture-tested; 0 and 0 on 2 fetched pages.
Parser 1.6.0 (PR, CC): `run_key` also hashes the sorted players' characters and the
ascension, so different runs sharing seed and start time stay apart; `build_info` counts
the old keys it splits (`old_run_keys_split`, `run_keys_split_from_old_key`,
`solo_old_run_keys_split`). On 2 fetched pages the co-op multi-record keys stay at 137 and
nothing splits. Every `run_key` value changes: regenerate anything keyed on the old one.
Parser 1.7.0 (PR, CC): `runs_dedup.retried` (copies differ in win, floors reached or
abandonment; also on `primary_offers`), `card_offers.deck_size_before` and
`run_players.deck_size_start`; `build_info` counts retried keys (`solo_run_keys_retried`,
`primary_run_keys_retried`) and checks the starting deck (`deck_start_nonstandard`: 0 of
1,405 on 2 fetched pages). Fixture-tested; 0 retried on 2 fetched pages.
Full build 2026-09-29 (parser 1.7.0, 1,513 pages, about 5 min): 0 pages failed, 0
unparseable lines; 75,996 exact repeats dropped (the re-downloaded pages); solo multi-record
keys 124; `primary_run_keys_retried` 74; `runs_mod_entity_only` 453;
`primary_offers_dedup_removed` 4,130 (1,393-page build: 119, 72, 425, 4,061). `deck_final`, `deaths` and relic/event choices not
started. Rebuilt 2026-10-02 22:32 UTC (parser 1.7.0, 1,873 pages, 1,871,830 records; commit
198a6d8): every file in `data/analysis/`, `results/` and `triage/out/` comes from that build.
Final build on the complete snapshot (Phil, 2026-10-09 21:18 UTC, parser 1.7.0): 2,071 pages
(0–2,070), 2,069,493 records read, 75,996 exact repeats dropped, 0 pages failed. Before
anything is refitted on it, `data/analysis/` (the 1,873-page fits) was copied to
`data/analysis_p1873/`. Final rerun on it (`scripts/final_rerun.sh`, 2026-10-09 22:40 to
2026-10-10 00:17 UTC, 5,852 s, no errors): `data/analysis/`, `data/analysis/writeup/` and
`results/` now come from the 2,071-page build; `triage/out/` stays on the 1,873-page one.*

### 4. Treatment table — CC
*Status: reference tables built (PR), `python -m spirometry.treatment`:
`change_events.csv` (262 card change events + 64 behavior events), `change_event_fields.csv`,
`card_versions.csv` (every card × build), `windows.csv` (per event and branch: before/after
builds, clean or not, control exclusions, behavior flags); notes in
`notes/treatment_table.md`. Stable-window check: 0 mismatches against `card_changes.csv`.
Card-patch level (the minimum result's unit: net change between stable builds,
`windows.csv` `level = card_patch`, `card_patch_fields.csv`): all 50 numeric tweaks have a
clean window. At event level 47 do on stable; Parry, Untouchable (v0.103.2) and Reflect
(v0.107.1) changed twice within beta, so their steps are clean only on beta (Parry's and
Untouchable's first steps nowhere). `kind_source` says where each label comes from. Ambiguous and left blank: 2 events with
unknown beta timing (Tear Asunder, Seven Stars, both wording), 9 events on 4 cards where
update-history can't say which beta changed a field (none a numeric tweak). Optional
`offers_with_version` view added to `runs.duckdb` (parser 1.4.0; fixture-tested). Next:
Phil reviews the rule-labeled kinds (116 events) and the choices in the decision log,
then builds the run tables with parser 1.4.0 to get the view (built; the review is
open).*
Join `card_offers` to the card version live in each run's build: for each (card, build), which
version was live and whether it's pre- or post-change. Also list, for each change, the other
cards of the same character changed in the same patch (candidates to exclude from its control
group). Done when every offer in a changed card's window has an unambiguous version.

Card versions accumulate along each branch. A beta build carries every earlier beta's
changes since the last stable (v0.110.0 has v0.108.0's and v0.109.0's changes too), and a
stable build carries every beta change before it (v0.107.1 = v0.103.2 + v0.104.0–v0.107.0).
`card_changes.csv` covers only changes that reached stable, netted over each window, so it
can't say which version a beta run had. That needs a per-build card version table: for
each (card, build), the card's version on that build, built by applying the beta changes
in order (`beta_card_changes.csv`, update-history, the notes) and checked against the
stable diffs. It also has to hold changes that were revised or reverted within beta
(Parry 8(11) on v0.100.0, 10(14) from v0.101.0) and the bug-fix behavior changes
(`behavior_changes.csv`) that no card field shows.

### 5. Analysis — Phil, in this order
*Prep (CC, PR): `pyfixest` added to the `analysis` extra (unpinned); `primary_offers`
deduplicated by `run_key` (parser 1.5.0).*
*Tooling (CC, PR): `reference/tweak_sizes.csv` (`python -m spirometry.tweaks`, 50 numeric
tweaks, 43 solo-estimable) and `spirometry.did` (load_window, control_cards,
offer_rate_check, fit_did, fit_event_study, to_log_odds, run_all); tested on synthetic
offers and smoke-tested on 2 fetched pages (first window only: the pages have no v0.103.3
runs). Next: Phil runs it on the full build (parser 1.5.0) in the analysis notebook.*
*First pass (2026-09-26, 949-page tables, parser 1.4.0): `notebooks/02_pick_rate_did.ipynb`
ran steps 1–3 on all 43 solo-estimable tweaks; results and caveats in SPIROMETRY.md
(now "Phase 5 results", superseded by the v3 rerun below).*
*Follow-up tooling (CC, PR): `fit_did` returns `se_hc` (heteroskedasticity-robust, same
fit) and takes `max_week_after` (fixed horizon; `run_all` passes it to the placebo too);
`offer_rate_check` adds `rarity` and same-rarity z-scores/flag (`flag_rarity`); dedup key
fixed (parser 1.6.0). Tested on synthetic offers; not run on real pages (the 2 fetched
pages have no v0.103.2 runs). Next: Phil rebuilds with parser 1.6.0 and reruns the
notebook with `se_hc`, `max_week_after=3` and `flag_rarity`.*
*Notebook v2 (2026-09-26, same 949-page tables): robust SEs, fixed horizon, same-rarity
flags and patch terms run; results in SPIROMETRY.md. New question: the second patch shows
no dose-response.*
*Win-effect tooling, steps 4–5 (CC, PR, parser 1.7.0): `spirometry.wins` (early_runs,
early_offers, load_early, reach_share, itt, first_stage, iv, naive, run_all_cards) on the
first K = 3 reward screens of each run, retried and abandoned runs out; `spirometry.did`
gets `load_window(extra_cols=True)`, `fit_did(card_act_fe=..., picked_screens_only=...)`
(through `run_all`) and `set_picked_any` in `load_window`'s default columns. Tested on
synthetic runs (planted effect, null, survival bias of "ever offered", weak instrument,
retried runs) and smoke-tested on 2 fetched pages (97.3% of runs reach screen 3). Merged
(PR #12). Next: `run_all_cards` per character within the stable builds (background:
`notebooks/iv_primer.ipynb`, a simulation of naive vs. ITT vs. IV); then step 5 (IV pre vs.
post).*
*Notebook v3 (2026-09-29, 1,513-page tables, parser 1.7.0): steps 1–3 rerun with every
check, including the heavy-uploader check (top 10 uploaders; no effect). Headline holds
(first patch 23 of 26 clearly nonzero, second 7 of 17, all toward the change; dose-response
slopes 1.44 ± 0.19 and 0.04 ± 0.31 by patch). The two patches' tweaks match in size (median
|ln ratio| 0.17 and 0.18) and precision (median SE 0.052 and 0.051 log-odds) but the second
patch moved picks about a third as much (median |β| 1.5 against 4.2 points on the line). Two
upgrade-only placebos (Royalties, Untouchable v0.107.1) are 2.6σ and 3.2σ below zero;
tagged-only fits diverge more. Results in SPIROMETRY.md ("Phase 5 results").*
*Anticipation check (CC, PR): `reference/beta_exposure.csv` (`python -m
spirometry.exposure`: first beta, lead days, beta steps per tweak) and `did`'s
`old_version_builds`, `load_anticipation`, `anticipation_check`, `anticipation_weekly`,
`anticipation_all`: does the treated card's gap move at its first-beta date on builds that
still have the old card? Tested on synthetic offers (ramp, change at stable only, steady
drift, uninformative cases); on 2 fetched pages all 43 run and all are uninformative.
Run on the 1,513-page tables 2026-09-29 (`notebooks/03_anticipation.ipynb`): 14 of 43
tweaks are informative (3 first patch, 11 second; the earlier count of 17 was never
verified), 29 are not (too few treated offers or days before the first beta date). Of the
10 informative tweaks with a clearly nonzero main effect, the post-beta gap is small or on
the other side of zero (median ratio to the main effect −0.11 for 3 first-patch tweaks,
−0.25 for 7 second-patch tweaks): no sign that anticipation inflates the main estimates,
and no support for it as the reason the second patch has no dose-response, for the tweaks
it can test. The date-versus-build comparison for the second patch agrees for the
informative tweaks. Results in SPIROMETRY.md ("Anticipation").*
*Strength-change tooling, step 5 (CC, PR): `spirometry.strength` (block_estimates,
strength_change, strength_all, save/load, balance_check, balance_all): the win-effect fits
on each window's before and after builds for the treated card and every control, the
change with its se, net of the controls' median, z-scores against the controls' spread and
against the card's own se, plus a robustness version against the controls matched on
first stage in each block (`_m`); balance checks for the offer. Tested on synthetic runs (planted
change, null, level drift, shared drift, pick-rate-only change, weak first stage, balance
with random and skill-dependent offers). On 2 fetched pages the first window runs end to
end (estimates blank or meaningless at that size); the second has no v0.103.3 runs. Not yet
run on the full tables. Next: Phil runs `strength_all` (main, `K=1`, `screen_mix=True`) and
`balance_all` per character and block in a notebook.*
*Results export (CC, PR): `spirometry.export` (`python -m spirometry.export`) turns the saved
fits in `data/analysis/` into aggregate tables in `results/` (per tweak, per event-study
week, dose-response coefficients, robustness fits, anticipation) plus `meta.json`;
`meta_regression` moved from notebook 02 into `spirometry.meta` (the notebook still has its
copy; a test checks they agree). Tested on synthetic saved fits with the notebooks' column
layout (`spirometry.sample_results`). The offer-rate flags stay
blank until notebook 02 saves its section 3 table (`offer_rate.parquet`). Run 2026-10-02 on
the 1,873-page fits (`results/meta.json`: 1,873 pages, tables built 22:32 UTC); notebook 02
now saves `offer_rate.parquet`.*
*Control-scope tooling (CC, PR): `control_scope` on `control_cards`, `load_window` /
`load_block_data`, `fit_did`, `fit_event_study` and `run_all`: `"color"` (default, the
same-color controls, unchanged), `"all"` (every character's unchanged cards), `"other"`
(the other characters' only). `did.window_changes` derives the cards changed or
bug-fix-flagged between two blocks for every color from `card_versions.csv` (it reproduces
`windows.csv`'s same-color columns on all 137 card-patch windows); no reference table
changed. `run_all` rows carry `control_scope` and `n_control_cards`;
`did.control_pool_sizes` tabulates control cards and offers per tweak and scope. Tested on
synthetic offers (`"color"` reproduces the earlier numbers; with a 2-point shock to every
card of the treated color and no effect, `"color"` ≈ 0, `"all"` ≈ 0.02 × (1 − the treated
color's share of the controls), `"other"` ≈ 0.02). Not run on real data. Next: Phil runs
`fit_all("ctrl_all", control_scope="all")`, `fit_all("ctrl_other", control_scope="other")`
and `did.control_pool_sizes(con)` in notebook 02.*
*Placebo calibration (CC, branch `placebo-calibration`): `did.placebo_fit`, `placebo_all`,
`placebo_summary`: the same DiD with an unchanged same-color card as the pseudo-treated
card (true effect zero), to tell whether the clustered errors are honest (prompted by
early- vs late-uploaded fits of the 43 tweaks giving z-differences with sd 1.48). Tested
on synthetic offers (no effects: sd(z) ≈ 1; a group × card taste shared across runs,
clustered by run only: sd(z) > 1.5). Run once on the local 1,513-page tables (2026-10-02,
default options, 20 cards per tweak, seed 0, 40 min): 860 fits on 43 tweaks, no errors,
`data/analysis/placebo_main.parquet`. min_offers came out at 50 (set by an upgrade-only
tweak's upgraded offers, so it barely binds for the all-offers tweaks). Summary as
printed, not interpreted: mean z −0.01, sd z 4.10, |z| > 2 in 57%, > 3 in 38%; first
patch sd 4.89 (520 fits), second 2.45 (340); small / large pseudo cards (median 15,361
offers) sd 3.42 / 4.64. The 860 rows hold 463 distinct (window, pseudo card) pairs: tweaks
sharing a window draw the same cards with near-identical z; one row per pair, sd z 3.68.
Diagnostics (same branch, from the saved parquets, no refit): `placebo_summary(dedupe=True)`
with robust columns, `placebo_vs_real` / `placebo_vs_real_by_patch`, `sign_agreement`,
`placebo_spread_by_feature`, `dose_response_sensitivity` (with
`meta.dose_response_fits(se_inflation=...)`, default unchanged); tables in
`data/analysis/placebo_diagnostics_*.csv`, numbers in SPIROMETRY.md ("Placebo calibration
of the DiD errors"), where "the clustered standard errors are calibrated" is marked not met.
Tested on synthetic fixtures. Next: Phil analyses the tables.*
*Final rerun (2026-10-10, 2,071-page tables, `scripts/final_rerun.sh`): every step above refit
on the complete snapshot, plus notebook 02's weeks 0–3 checks; numbers in SPIROMETRY.md
("Phase 5 results", "Placebo calibration of the DiD errors", "Audit decisions"). Against the
1,873-page fits no estimate moved by more than its old SE; the classifications that changed
(Furnace v0.107.1 now clearly nonzero, Patter v0.107.1 no longer flagged against all
controls, Reflect informative for anticipation) are listed there.*
*Status (CC, 2026-11-10): triage sections O (forensics on the largest placebo misses,
`triage/scripts/o_forensics.py`) and P (archetype spillover, `triage/scripts/p_archetype.py`)
run on the final tables, exploratory, outputs in `triage/out_final/o_*.csv` and `p_*.csv`;
no factor, number or headline changes. Results in `triage/TRIAGE.md` and SPIROMETRY.md (open
question 8); the cause of the placebo spread is still not fully verified. Next: Phil reviews
both sections.*
*Status (CC, 2026-11-11): triage section Q (the release nudge, `triage/scripts/q_nudge.py`)
run on the final tables, exploratory, outputs in `triage/out_final/q_*.csv`; no factor, number
or headline changes. Results in `triage/TRIAGE.md`; SPIROMETRY.md's open question 8 is
updated with Phil's text (2026-11-11). Not committed: `.git` was not writable
in the session. Next: Phil reviews the section and commits it with his
`triage/scripts/q_z_vs_offers.py`.*
*Status (CC, 2026-11-11): triage section R (dose and same players, `triage/scripts/r_dose.py`)
run on the final tables, exploratory, outputs in `triage/out_final/r_*.csv`; no factor, number
or headline changes. Results in `triage/TRIAGE.md`; SPIROMETRY.md's open question 8 is updated
with R's line and a revised Q passage, at Phil's direction (2026-11-11). Not committed (git
not attempted, as instructed). Next: Phil reviews the section.*
*Status (CC, 2026-11-11): triage section S (an additive calibration of the DiD errors, a
declared sensitivity check, `triage/scripts/s_additive.py`) run on the saved tables, outputs
in `triage/out_final/s_*.csv`; no factor, number or headline changes. The additive model
fails its declared test on the placebos in both patches, so its counts (8 of 26, 0 of 17)
are descriptive only and the calibrated counts stay 13 of 26 and 2 of 17. Results in
`triage/TRIAGE.md`. On Phil's instruction (2026-11-11) the range is now stated where the
counts are: README finding 1 and SPIROMETRY.md, "Placebo calibration of the DiD errors",
give the first-patch count as between about 8 (additive) and 13 (multiplicative, the
declared headline) and the second-patch count as between 0 and 2. Not committed (git not
attempted, as instructed).*
1. **Offer-rate check** (design validity): a patch shouldn't move how often a card is offered.
   If it does, something else changed (card pool, rarity) and that card's comparison is suspect.
2. **Pick-rate DiD for numeric tweaks** — the minimum result.
3. **Dose-response on pick rate:** effect against change size.
4. **Win effects within a build:** intent-to-treat (offered → win), then IV (effect of
   picking, with the offer as instrument).
   *Future work, not planned (Phil, 2026-10-16): the power check (item 15 task 9) is not run.*
5. **Strength change across a patch:** IV estimates pre vs. post, net of unchanged cards.
   *Future work, not planned for field guide v2: run only if step 4's power check shows
   per-card IV errors far smaller than predicted (decision log 2026-10-09).*
6. **Perception vs. strength:** pick-rate effects against strength effects. *Future work
   (needs step 5).*
7. **Hierarchical Bayes:** partial pooling across cards, characters, and ascension, so rarely
   offered cards don't get extreme estimates. *Future work, not planned.*
8. **Staggered rollout** (beta before stable), if the audit shows enough beta runs. *Future
   work, not planned.*
9. **Reworks:** before/after estimates, reported separately. *Future work, not planned.*

### 6. Metric and dashboard
Selection-corrected card strength metric; dashboard (Streamlit or Observable, undecided).
*Status: results export and Streamlit skeleton built (CC, PR): `dashboard/app.py` (Overview
forest plot, Dose-response, Card, Anticipation, About) reads `results/`, else the synthetic
`results_sample/` with a SAMPLE DATA banner. Local only; no deployment until the release
checklist (Next up 12) is done. Not yet run on the real export. The strength metric is not
started. Not planned for field guide v2 (future work).*

### 7. Write-up
Field guide v2: a personal study guide (PDF) that teaches the statistics through the project's
own data, in the voice and format of v1 (`notes/spirometry_stats_field_guide_v1.pdf`, a study
guide on the 1,393-page tables). The PDF stays unpublished for now: publish as a GitHub Release
asset after the chapter 7-14 review. Built from `writeup/` (Typst) by
`python -m spirometry.writeup build`; every number comes from the generated
`writeup/numbers.json` (`python -m spirometry.numbers`), and every figure from
`scripts/writeup/figures.py`, so a rebuild never leaves stale numbers. The build runs a privacy
check either way. README results section: drafted on the 1,513-page numbers, marked
provisional.
*Status: learning map and build skeleton done (CC, 2026-10-14; Next up 15, task 11):
`writeup/OUTLINE.md` (15 chapters and four appendices, glossary, readiness), `writeup/main.typ`,
`style.typ` and stub chapters; `python -m spirometry.writeup build` compiles a 21-page stub
PDF on the final numbers.json (typst 0.15.0, the `writeup` extra). Chapters next (task 12).*
*Scope (Phil, 2026-10-16): the project ends with field guide v2; win effects (task 9), the
release step and publishing are future work. Task A (CC, 2026-10-16), the code side of the
whole guide: notebook 01 saves its aggregates; the export copies build_info's dedup counts;
distinct runs settled (1,525,329); weeks 0–3 placebo tooling; the triage's design checks
rerunnable on the final tables (`triage/out_final/`) and summarised by `spirometry.checks`;
numbers keys for every chapter (123 → about 6,050 on the final outputs); one run script
(`scripts/writeup/phil_runs.sh`, not yet run) and the figure script
(`scripts/writeup/figures.py`, 25 figures, tested on synthetic outputs only). Task B writes
the whole guide.*
*Done (task B, CC, 2026-10-16): chapters 0–14 and appendices A–E written
(`writeup/chapters/`, new `e_talking.typ`: a one-minute and a five-minute version and ten
interview questions), on Phil's run of `phil_runs.sh` and `figures.py` (all 25 figures, no
placeholders). `python -m spirometry.writeup build` gives a 96-page
`writeup/build/field_guide_v2.pdf`; lint and privacy pass; 469 keys used, all in
numbers.json. The guide leads with the calibrated weeks 0–3 counts (13 of 26, 2 of 17), labels
the pre-declared aggregates as measured on the 1,873-page tables, and states once (chapter 12)
that no main estimate moved by more than one SE between those tables and the final ones.
Future work (not planned): win effects and the power check (task 9), the strength change
(step 5), perception against strength (step 6), partial pooling (step 7), the staggered
rollout (step 8), reworks (step 9), the stayers-only token fit, the pre-declared aggregates on
the final tables, the dashboard, the release checklist and publishing.*
*Rework (Phil, 2026-10-22; `writeup/REWORK.md` tracks it): typeset math, code listings from
the source and the reading notes ported in, in four phases, one PR each. Phase 1 (CC,
2026-10-22): infrastructure and chapter 6 as the pilot. `spirometry.teaching_sims` (19 toys,
tested), `toy.*` keys in `spirometry.numbers`, 15 toy figures in `figures.py`, the digit lint
extended to math and inline code, code listings extracted at build time
(`python -m spirometry.writeup listings`), equations numbered by chapter, the COMMON MIX-UP /
THE MATH, IN FULL / IN CODE boxes, a notation table in Appendix B; chapter 6 rewritten
(additions 6A–6D, teaching notes §5, §16, §18, §19, 18 equations, 7 listings). The real build
is 112 pages (96 before). Waits on Phil's review of the pilot before phase 2 (chapters 0–5).*

## Next up
1. ~~Review and merge the card-decisions + mod-entity PR; rerun the full build and read
   `runs_mod_entity_only`.~~ Done: 453 on the 1,513-page build (425 on 1,393), all mod content.
2. ~~Audit follow-up: does rising ascension explain the within-build win-rate drift.~~ No:
   mean ascension fell while win rates fell (v0.103.2). Candidate: stronger players moving
   to the betas.
3. ~~Let the snapshot finish; run `--count-only`.~~ Done 2026-10-04 (Phase 1). Pages 0–948
   are not re-downloaded for `player_token` (the triage's token work used the pages that have
   it).
4. Send the maintainer message (budget per IP or per client, the daily cap, short pages,
   bulk dump, stable-only hotfixes, when `player_token` was added). *The maintainer has since
   approved publishing `reference/raw/` (item 12); whether these questions were asked or
   answered isn't recorded.*
5. ~~Final rebuild on the complete snapshot~~ (done 2026-10-09: 2,071 pages, 0 failed;
   Phase 3) ~~and copy `data/analysis/` to `data/analysis_p1873/`~~ (done 2026-10-09)
   ~~and rerun notebooks 01–05, the placebo calibration, the export and the sensitivity
   tables on the final tables~~ (done 2026-10-10, item 15 task 8; numbers in SPIROMETRY.md,
   nothing moved by more than one SE from the 1,873-page fits). Task 7 is replaced by the
   triage reruns in `scripts/writeup/phil_runs.sh` (2026-10-16; not yet run). The audit notebook still reads the interim `data/audit/` tables (rebuilt on all
   2,071 pages in the rerun); moving it onto the run tables is not planned.
6. Phase 4: review the treatment tables (`notes/treatment_table.md`). (The rebuild with
   `offers_with_version` and the deduplicated `primary_offers` is done.)
7. Phase 5 follow-ups. Done (numbers from the 1,513-page rerun): (a) same-rarity offer-rate
   check: Patter and Sculpting Strike are card-specific, not pool changes (The Scythe,
   flagged on the first pass, no longer flags); (b) fixed horizon: not the cause
   of the gap between patches; (c) patch term: the second patch has no dose-response (slope
   0.04 ± 0.31 against 1.44 ± 0.19); (d) robust SEs: clustering adds about 3%; (e) dedup key
   fixed in parser 1.6.0; (f) heavy-uploader check: dropping the top 10 uploaders moves
   estimates by a median 0.04 SE (only records from page 1025 on carry `uploader_hash`).
   On the 1,873-page rebuild (triage, `triage/TRIAGE.md` A): (c) 1.41 ± 0.19 against
   0.03 ± 0.31; (f) 0.17 SE. Final rerun (2,071 pages): (c) 1.40 ± 0.19 against
   0.05 ± 0.31 (primary spec 0.09 ± 0.40); (f) 0.18 SE (weeks 0–3: 0.14).
   Next: (g) fit per patch within each
   uploader group (the tooltip hypothesis) and by kind of main field. *Token subset done
   (triage G3: same pattern); kind of main field done (triage B). The per-group fits saved so
   far (`did_tagged`, `did_untagged`) are all weeks; weeks 0–3 versions are in the final
   rerun (`did_h3_tagged`, `did_h3_untagged`: median shift from `did_h3` 1.94 and 0.58 SE).* (h) where the flagged
   cards' extra offers come from (act, floor type, event fights; tooling:
   `load_window(extra_cols=True)`). *Not planned; stays a caveat.* (i) duplicated runs:
   answered (mostly retries from a restored save; not the downloads). Rule: keep one copy
   for pick rates, drop runs whose copies differ in win, floors or abandonment from win
   analyses (done in parser 1.7.0: `runs_dedup.retried`); (j) a robustness row: the DiD on
   screens where something was picked (choice among cards, no deck-size effect; tooling:
   `picked_screens_only`). *Run in the final rerun at weeks 0–3
   (`did_h3_picked_screens_only`): median shift 0.76 SE from `did_h3`, 30% beyond 2 SE, no
   sign flips.* (k) optional: card × act fixed
   effects (timing balance says it can't change a conclusion; tooling: `card_act_fe`). *Not
   planned.* (l) the upgrade-only placebos on
   Royalties and Untouchable (v0.107.1), 2.6σ and 3.2σ below zero on the 1,513-page rerun,
   2.1σ and 5.0σ on the final one (drift in the
   short, smaller second-patch before block is the first candidate). *On the placebo scale they are
   within or at the edge of what unchanged cards show (triage, Part 1 side results).* (m)
   recheck "When in the run" at fixed floors on the new tables. *Only if the field guide uses
   the figure.* Win effects (steps 4–5): tooling in
   `spirometry.wins`, ready to run; a power check comes first (item 15). Strength change
   (step 5, IV before vs. after, net of
   unchanged cards): tooling in `spirometry.strength`, ready to run; about 40 tweaks get a
   row (43 solo-estimable minus 3 upgrade-only), so the notebook should say how many rows
   were tested; partial pooling (step 7) is the planned answer to multiple comparisons.
   (n) Control-group scope: how much the per-card effects move with same-color, all, or
   other-character controls (tooling: `control_scope`, `control_pool_sizes`; Phil runs it).
   *Done in the triage (L): z −3.55 ("other"), −3.60 ("all"); first-patch slope −12%.*
   (o) Placebo calibration of the DiD errors: run and tabulated (`placebo_main.parquet`,
   `placebo_diagnostics_*.csv`; SPIROMETRY.md, "Placebo calibration of the DiD errors").
   *Analysed in the triage (C, G4): the spread is card-level and persistent; the patch
   difference survives calibrated errors.*
8. When official act 4 (or other new content) ships: re-cache the game lists for the new
   builds and switch the mod-entity rule to per-build lists (see SPIROMETRY.md, custom and
   modded runs). The cached lists for v0.99.0 and v0.110.1 are empty: re-fetch them or fall
   back to a neighbouring build first, or every v0.110.1 run would look modded.
9. Anticipation (done, 2026-09-29): 14 of 43 informative, no sign of inflation; the first
   patch can't be tested beyond 3 tweaks. Final rerun (2026-10-10): 16 of 43 informative (3
   and 13); of the 12 with a clearly nonzero main effect, Crescent Spear and Furnace have a
   post-beta gap on the same side as the main effect and larger (SPIROMETRY.md,
   "Anticipation").
10. Results export and dashboard (CC brief: `ccc_prompt_dashboard_v2.md`): built (PR) on
   synthetic saved fits. Notebook 02 saves `offer_rate.parquet`, and the export was run
   2026-10-02 on the 1,873-page fits and 2026-10-10 on the final ones (`results/`). The dashboard is not planned for field
   guide v2 (future work). No deployment until the release checklist below is done.
11. README results section: drafted on the 1,513-page numbers with figure slots; numbers
   updated to the final rerun 2026-10-10. Figure slots wait on the field guide's figure
   script.
12. Release checklist (only if something is published): ~~send the maintainer message (item 4)~~
   *(done for publishing: the Spire Codex maintainer approved publishing `reference/raw/`,
   noted in `reference/raw/README.md`; item 4's questions stay open)*;
   ~~clear notebook 02's output cells that show top-uploader run counts (the hashed IDs are
   gone since task 6)~~ *(checked 2026-11-06: cells 27 and 41 have no outputs)*;
   ~~review the licenses and attribution of `reference/raw/` (wiki pages CC BY-SA, Spire Codex
   caches)~~ *(README, "License and attribution"; `reference/raw/README.md`)*;
   ~~aggregates only~~ *(checked 2026-11-06 outside `reference/raw/`: no run, player or
   uploader ID columns or values in tracked files; the 7 records in the test fixture are
   synthetic)*. All done; item 20 has what is still open.
13. Set `MIN_RUNS` (notebook 01, "Runs per build") from a power calculation. It is a working
   threshold now: 2,000 primary runs, chosen by hand. *Not planned (the windows are fixed, so
   it changes no result).*
14. Open questions moved out of the notebooks' "What to write down" checklists (the rest of
   those checklists is already in SPIROMETRY.md, "Phase 5 results" and "Anticipation"):
   (a) ascension as one fixed-effect level each, or banded (notebook 02: check
   `n_singletons_dropped` in the main table); (b) how many heavy uploaders the robustness
   check should drop (10 now); (c) notebook 03 section 6: which informative tweaks' weekly
   panels show a step, a ramp, or a straight-line drift at the first-beta date, by card (not
   yet recorded).
15. Field guide v2 (Phase 7), one task at a time, in this order. CC = a Claude Code task
   ending in a PR; Phil = notebook, plots or decision.
   1. ~~Decisions~~ (Phil, 2026-10-09; decision log).
   2. ~~Triage record on main~~ (#19).
   3. ~~Docs: status, decisions, structure, no new numbers~~ (#20).
   4. ~~Final rebuild~~ (Phil, 2026-10-09; item 5), with `data/analysis_p1873/` saved first.
   5. `spirometry.sensitivity`: the triage's saved-fit computations as tested tooling (rulers,
      mixed-tweak doses, Debilitate on/off, SE inflation, leave-one-out, character terms,
      power simulation) and the IV primer's simulation (`spirometry.iv_sim`), writing tables
      to `data/analysis/writeup/`; done when it reproduces the triage's printed numbers on the
      current `did_h3` (CC; Phil checks). *Built (CC, 2026-10-09). On the 1,873-page fits it
      reproduces triage B (all nine rulers), B2, C (SE factors, both horizons), D (the power
      table exactly, same seed) and K1/K2; `iv_sim` reproduces the primer's saved outputs.
      First number under the 2026-10-09 primary spec (Reflect on, Debilitate v0.107.1 off
      the ln line), 1,873-page fits: slope1 1.41 ± 0.19, slope2 0.08 ± 0.40, z diff −3.00
      (the plan expected about −2.5 to −2.7). Phil checks by rerunning.*
   6. Notebook 02 for the final rerun: weeks 0–3 versions of every robustness check
      (tagged / untagged = the tooltip check), `picked_screens_only`; remove the cells that
      print hashed uploader IDs (Phil). *Edited, not run (CC, 2026-10-09): section 7 gets
      "Weeks 0–3 versions of the checks": every check of section 7 (pooled_groups, tagged,
      untagged, drop_shared_screens, drop_behavior_flags, drop_top_uploaders) refit with
      `max_week_after=3` and saved as `did_h3_<check>.parquet`, plus
      `did_h3_picked_screens_only.parquet`, summarized against `did_h3` (section 7's
      `compare` / new `summarize` take a `base`, default main as before); the second patch's
      before-block variants at weeks 0–3 go to `second_patch_checks_h3.parquet`
      (`second_patch_checks` takes `max_week_after`). Cells 27 and 41 print uploader run
      counts only, no hashed IDs; their outputs are cleared. No other cell changed.*
   7. ~~Scripts for the run-level pieces: fake patch, control scope at weeks 0–3, token subset
      and stayers, slope by week, the pre-declared aggregates, per-group dose lines; each
      states its spec and prediction before it runs (CC).~~ *Replaced (Phil, 2026-10-16) by
      rerunning the triage's own scripts on the final tables (task A, part 6): fake patch
      (I), regression to the mean and slope by week (J), token subset (G3/G4), control scope
      at weeks 0–3 (L), all into `triage/out_final/` by `scripts/writeup/phil_runs.sh`; the
      per-group dose lines come from notebook 02's saved tagged / untagged fits
      (`sensitivity.group_line_table`, already on the final tables). Not rerun: stayers (no
      script exists) and the pre-declared aggregates (H; not among the five checks; printed
      in TRIAGE.md on the 1,873-page tables only). Not yet run (Phil).*
   8. Copy `data/analysis/` to `data/analysis_p1873/`; final rerun of notebooks 01–05,
      placebo, export and the scripts of 5 and 7 (Phil). *`scripts/final_rerun.sh` (CC,
      2026-10-09, not run): audit extract, notebooks 01–05, placebo calibration and
      diagnostics, export, `spirometry.sensitivity`, `spirometry.iv_sim`, stopping at the
      first error; `--from <step>` resumes at a step without moving `data/analysis/`
      aside. The scripts of 7 aren't built yet, so it doesn't run them. Expected run
      time about 1 h 45 min (estimate from the 1,873-page run times, not measured).*
      *Run by Phil 2026-10-09/10 (log `logs/final_rerun.log`): 5,852 s, every step
      finished, no fit errors; notebook 02 2,642 s, placebo 2,569 s. Done except the
      scripts of 7, which follow when built.*
   9. ~~Win effects: power check on a few cards of one build with a stop rule; continue to all
      cards of v0.107.1 only if it passes (CC script; Phil runs and decides).~~ *Future work,
      not planned (Phil, 2026-10-16). Chapter 13 teaches instruments with the IV simulation
      only.*
   10. spirometry.numbers: the generated numbers table, with staleness and privacy checks (CC).
       Built (CC, 2026-10-14): python -m spirometry.numbers --analysis data/analysis --results 
       results --out writeup/numbers.json writes numbers.json and numbers.csv (git-ignored). 
       The build stamp comes from results/meta.json, and the module never opens the database. 
       It refuses inputs older than the stamp, a sample export without --allow-sample, missing 
       values and anything the export's privacy check catches. First batch on the final rerun: 
       96 keys (snapshot pages, tweak counts, clearly nonzero and toward-the-change counts per 
       patch and horizon, median |β|, dose-response slopes under the triage and primary specs 
       and with placebo-scaled SEs, placebo z spread). Left out: records, distinct runs (two
       sources disagree), date range, calibrated clearly-nonzero counts (rule not decided).
       Tested on synthetic outputs (sample_results.write_numbers_inputs).
       Follow-up (CC, 2026-10-14): snapshot keys: records (2,069,493) and last page (2,071)
       from snapshot.log; play-date range from meta.json, which the export now fills from the
       run tables with --db (primary runs). Calibrated "clearly nonzero"
       (sensitivity.calibrated_counts, data/analysis/writeup/calibrated_counts.csv), all
       weeks: first patch 13 of 26 (12 toward the change), second 4 of 17 (4); uncalibrated
       22 and 9. Weeks 0–3 calibrated counts missing: the saved placebo fits are all weeks
       (max_week_after empty on all 860); they need a weeks 0–3 placebo run
       (did.placebo_all, max_week_after=3, about 45 min). Uncalibrated keys renamed
       did.<h>.<patch>.uncalibrated.*. Phil reruns the export (--db), sensitivity and
       numbers before numbers.json has the new keys.
       *Task A (CC, 2026-10-16): distinct runs settled: the guide prints 1,525,329 (the
       audit's distinct (seed, start_time)); `--count-only`'s 1,525,369 sums distinct runs
       within each build, and 40 runs carry two build ids (per-build counts identical in both
       sources for all 26 released builds). Keys `snapshot.distinct_runs`,
       `snapshot.distinct_runs_per_build_sum`, `snapshot.runs_in_several_builds`, with a
       guard that the audit's per-build sum equals the log's total. Weeks 0–3 placebos:
       `did.placebo_run` saves `placebo_h3.parquet` beside `placebo_main.parquet`, and
       `sensitivity.load_placebo_fits` reads both, so the weeks 0–3 calibrated counts and
       `placebo.h3.*` appear after Phil's run (synthetic test passes). Keys for every chapter
       the saved outputs supply: on the final outputs (sensitivity and checks written to a
       scratch copy) 6,024 keys, 5,901 new; the families are in the module docstring.
       Missing until the run: the weeks 0–3 calibrated counts and placebo spread, the
       dedup counts.*
   11. ~~Write-up skeleton: Typst, boxes, chapter stubs, generated numbers appendix, lint for
      hand-typed numbers, one build command (CC).~~ *Done (CC, 2026-10-14).*
      - *`writeup/OUTLINE.md`: for each chapter, its question, terms in order, analogies,
        numbers (keys that exist; missing ones by what would supply them) and figures with
        their inputs. Also the decision-log entries each chapter explains, what it must label
        unverified or pending, and what it waits on; a glossary; v1 changes; readiness.*
      - *Ready (numbers in saved final-rerun outputs, keys to add): chapters 0 and 3–7,
        10, 11.*
      - *Partly ready:*
        - *1: audit aggregates and `build_info` fields in `meta.json`.*
        - *2: audit, or the primer example.*
        - *8, 9: the weeks 0–3 placebo run.*
        - *13: task 9.*
      - *Waits: 12 (task 7).*
      - *Skeleton: `writeup/main.typ`, `style.typ` (#n, v1's boxes plus a skill box,
        stop-and-check with a generated answer key, figure placeholders, table style),
        `chapters/NN_slug.typ` stubs (headings only).*
      - *`python -m spirometry.writeup build`: numbers (reused; `--refresh-numbers`), digit
        lint, privacy, figure freshness, typst compile to `writeup/build/field_guide_v2.pdf`.
        21 pages on the final numbers.json.*
      - *Tests: `tests/test_writeup.py`.*
   12. ~~Chapters 0–3 draft, for a voice check before the rest (CC drafts; Phil reads).~~
       *Folded into task B (CC, 2026-10-16): every chapter written in one pass.*
   13. Figure script for every figure (CC; Phil runs it and looks). *Built (CC, 2026-10-16):
       `scripts/writeup/figures.py`, the 25 figures of OUTLINE.md that saved outputs supply
       (all but `fig_power_check`, task 9), tested on synthetic outputs; not run on real data.*
   14. Remaining chapters in four PRs; Phil writes the "what was found" passages and the
      conclusion (CC drafts). *Replaced (Phil, 2026-10-16): task B, CC writes the whole guide,
      "what was found" passages and conclusion included; Phil's review is reading the PDF.*
   15. ~~Docs: final numbers into SPIROMETRY.md, README and PLAN (CC).~~ *Pick-rate,
      anticipation, placebo and audit numbers updated 2026-10-10 from the final rerun. Task B
      (2026-10-16): SPIROMETRY.md gets the calibrated weeks 0–3 counts, the weeks 0–3 placebo
      factors and the triage checks rerun on the final tables; README the status, the
      calibrated counts and the build order; this file the item 15 status. Item 15 is done.*
      Tests: 210 passed, 5 skipped (smoke tests need real data), run locally 2026-10-14.
      Task B (2026-10-16, in the sandbox): 218 passed, 5 skipped; the 47 tests that read
      `reference/raw/` fail there on permission (the sandbox can't read it), as before; Phil
      reruns them locally. 
      The cloud sandbox can’t read reference/raw/, so the parser, patch-history and treatment 
      tests only run locally.
   16. ~~Only if Phil decides to publish: release checklist (item 12), then publish (Phil).~~
      *Future work, not planned (Phil, 2026-10-16).* *Reopened for the repository (Phil,
      2026-11-06): the checklist is done and the repo is being made public (item 20).
      The field guide PDF stays unpublished for now: publish as a GitHub Release asset after
      the chapter 7-14 review.*
   17. Rework of field guide v2: math, code listings and the reading notes (Phil, 2026-10-22;
      tracker `writeup/REWORK.md`), four CC phases, one PR each. *Phase 1 (infrastructure and
      chapter 6) done (CC, 2026-10-22); Phil approved chapter 6 as the template. Phase 2
      (chapters 0–5, Appendix B's rows for them) done (CC, 2026-10-22): 152 pages on the real
      outputs (112 after phase 1). Next: phase 3 (7–10), then phase 4 (11–14, appendices,
      read-through).*
   18. Website deliverables from notebook 02 (Phil, 2026-10-27): `notebooks/06_site_figures.ipynb`
      with `src/spirometry/site_figures.py`, into `figures/site/`. *Selection and Parry figure
      done (CC, 2026-10-27; from saved fits only; contrast card The Scythe). Calibrated
      version (CC, 2026-11-05): Parry's band, the export's `n_clear`, no `sentence` field,
      `scripts/site_publish.sh`. Code and docs done; Phil runs the script (notebook 06 needs
      `data/`, the CC sandbox can't write to the website repo). Until then
      `spirometry_cards.json` still says 21 and 8, and the PNG and PDF come from `results/`.*
   19. Loose ends from the calibrated site (2026-11-05), all open:
      (a) Debilitate: calibrated z 1.96, so its site band reads +0.0 to +12.1 while it is not
      one of the 13 (|z| > 2). Phil decides whether to keep it or add a note.
      (b) The card selection rules (notebook 06) still use clustered SEs (|β| > 2 se), by
      design; they were fixed before the picks.
      (c) The factors live in two places (`PLACEBO_FACTORS_H3`, `CAL`); the script checks
      them but nothing checks them on a plain `index.html` edit.
      (d) `index.html`'s prose hard-codes 26, 13, 4.4, 17, 1.9, 2 and "about 1.1 million"
      (1,122,054 primary runs), so an export change won't reach it.
      (e) Why the placebo spread is so large is still not verified (SPIROMETRY.md, "Placebo
      calibration of the DiD errors"); the band's 95% is the factor's scaling, not a
      measured coverage.
      (f) The PDF stays in this repo; the site loads only the PNG.
      (g) `spirometry_patch1.png` is built but not on the page: `index.html` still shows Parry.
      The swap needs a new src, alt and caption, and that `.fig-slot` off its 4:3 box (the
      image is 1600×1850, so 4:3 shrinks it below the 10 pt floor).
      (h) The forest plot's ±2 and the Parry band's and widget's ±1.96 differ on purpose
      (decision log); Debilitate is the only card they split.
      (i) Leading Strike is a buff on the forest plot, `rework` in `spirometry_cards.json`,
      and mixed with `change` nerf in `results/`.
20. Repository move (Phil, 2026-11-06). History rewritten on 2026-11-06 with `git filter-repo`
   (uploader-ID outputs, local paths, old emails and the real-run fixture removed) and pushed to
   a new `pmacias/spirometry`; the old repository is archived privately. Every commit hash
   changed. The one commit cited in tracked docs (here, Phase 3, and `triage/TRIAGE.md`) now
   carries its new hash. PR numbers in commit subjects and in these docs (`#19`, `PR #12`) are
   the old repository's; those PRs aren't in this one, and new PRs here number from #1 again.
   Release checklist: item 12. `results/` and `writeup/numbers.json` / `numbers.csv` are
   committed for the release (checked 2026-11-06: nothing below card level, nothing over 5 MB).
   `writeup/figures/` and the field guide PDF stay git-ignored; the PDF's plan is in item 15,
   task 16.
   Tests (2026-11-06, in the sandbox, which can't read `reference/raw/` or start a process
   pool): 262 passed, 6 skipped, 46 stop on the `reference/raw/` permission, the worker tests
   among them; Phil reruns them locally. The worker-test failure after the dashboard test is
   fixed (decision log) and was checked with a spawned process in a copy without `results/`.
21. Export a calibrated column alongside `clearly_nonzero` and `clearly_nonzero_h` in
   `results/pick_rate_did.csv` (CC). Those columns use uncalibrated clustered errors (21 of 26
   and 8 of 17 at weeks 0–3), while the headline 13 of 26 and 2 of 17 apply the placebo factors
   (SPIROMETRY.md), so the file can't reproduce them. *Done (CC, 2026-11-06): the export writes
   `clearly_nonzero_h_cal` and `clearly_nonzero_cal`; the old columns stay. Tested on synthetic
   fits, and the estimates in `results/` give 13 and 2 at weeks 0–3, 13 and 4 at all weeks.
   `results/` and `results_sample/` regenerated by Phil (not from the CC session).*
22. `tests/test_dashboard.py` skips whenever `results/pick_rate_did.csv` exists, so with
   `results/` committed it never runs, and it is the only test that reads `results_sample/`.
   Make it run against `results_sample/` explicitly instead of skipping (CC; `results_dir` in
   `dashboard/data.py` picks the folder). Keep its `__main__` restore. *Done (CC, 2026-11-06):
   the test points `data.RESULTS` at an empty folder, so it runs with `results/` present.*

## Decision log
- Spire Codex export is the primary source; sts2runs.com only for cross-checks.
- Standard registered tier, not academia (no current university affiliation).
- Raw snapshot stays local; cloud sessions develop on sample pages.
- Dependencies live only in `pyproject.toml` (mamba locally, pip in cloud/CI).
- PRs are squash-merged; Phil merges, CC never merges.
- Card changes are classified from structured fields only; description text is truncated in
  both endpoints. Cost changes and text-only changes get their own labels for manual review.
- Unit of analysis for the causal designs is the card offer; pick-rate DiD on numeric tweaks
  is the first result.
- Only changelogs 1.1.0 (stable v0.103.2) and 1.2.0 (stable v0.107.1) count as game
  releases; other changelogs' card diffs are parser fixes and are excluded (listed in
  `excluded_fields.csv`).
- Stable release dates are Spire Codex changelog dates; beta dates are update-history dates.
  Branch is never taken from run files' `is_beta` (it says false even for beta versions).
- update-history's V0.98.0-beta / V0.99.0-beta entries are ignored for beta timing: on every
  card they are a change and its exact reversal.
- `change_kind` labels combine with `+` (e.g. `rework+cost_change`); `rarity_change` added
  alongside the requested labels, and whole-card `added` / `removed` rows are included.
- `snapshot_export.py` moved to `scripts/` (unchanged behaviour; run from the repo root).
- Correction: run export records have **no** `is_beta` field (3 pages checked,
  `notes/run_schema.md`); "it says false" above came from counting a missing key. Branch
  comes only from `builds.csv` via `build_id`.
- The official patch notes (wiki mirror, CC BY-SA 4.0) are a third source. They fill
  branch and date for stable-only hotfixes and add versions Spire Codex doesn't list.
  Where the wiki conflicts with `builds.csv` (four dates, one day apart), the existing
  value is kept and the conflict noted.
- Stable-only hotfixes (v0.98.1–v0.98.3, v0.99.1, v0.103.3) are assumed to have made no
  card changes unless the patch notes say so. Their notes list only bug fixes (v0.99.1's
  one balance item is an HP cap). v0.103.3 brings some beta bug fixes to stable that change
  how a card plays (Summon Forth, Scrape), tracked in `behavior_changes.csv`. To be checked
  in the audit by looking for offer-rate and pick-rate jumps at those builds.
- Text-only changes are hand-labeled in `text_only_labels.csv`: 12 `mechanic` (treat as a
  rework), 12 `wording` (no gameplay change), 2 `exclude` (Mad Science, dropped from all
  analyses). The official patch notes agree with every label they touch.
- Cost changes stay labeled separately (`cost_change`). How to put them on a common scale
  with numeric tweaks (before/after only, a fixed energy exchange rate, or an estimated
  rate with a Strike/Defend-based prior) is decided in the analysis phase. The minimum
  result uses the pure numeric tweaks only.
- Patch-note parsing (CC's choices, open to review): one row per card mention plus one
  per numeric change; only `subject` mentions count in the cross-check; notes are grouped
  into the same stable windows as `card_changes.csv`; numbers are chained across betas;
  `Spoils of War` (v0.101.0) and `Sealed Throne` are aliases of Spoils of Battle and The
  Sealed Throne. v0.99.1 is labeled stable (it had a beta hotfix page three days earlier).
- Run-file conventions for the table proposal (CC's choices, open to review): floor number
  = 1-based cumulative index (matches `floor_added_to_deck`); dedup key
  `(seed, start_time)`; solo shop offers rebuilt as shelf + bought; custom runs detected by
  non-empty `modifiers`, not `game_mode`.
- Primary analysis uses card-reward offers only; shop offers are secondary (table keeps them:
  unsold cards plus purchases from `cards_gained`).
- Primary analysis is solo runs only; deduplicated co-op runs are a later, separate analysis.
- Floors with several merged reward screens: recover screen boundaries if possible; otherwise
  pick rates only, with the limitation noted.
- Abandoned runs: offers kept for pick rates; excluded from win analyses, with a both-ways check.
- Any run with modifiers or mods is dropped from the primary analysis (game mode is unreliable).
- Glow, Grave Warden, Shatter and Tesla Coil are reclassified from tweak to rework (patch notes
  describe more than numbers); the numeric-tweak set for the minimum result is now 50.
- Changes found only in the patch notes get rows, so those cards leave control groups.
- Bug-fix behavior changes are not hand-checked; flagged cards are used for a sensitivity
  analysis (excluded from controls only in comparison windows spanning the fix's build).
- Artifact rows (Folly, Shiv, Sacrifice) stay in the tables labeled `artifact` and are excluded
  from analyses.
- Snapshot script: leave unchanged until the download finishes, then remove the beta column
  (branch comes from `builds.csv` at analysis time).
- Run tables (CC's choices, open to review): `card_offers` keeps every `card_choices` entry,
  shop rows included (`source = 'shop'`); `shop_offers` is the shop analysis table (solo:
  the list plus purchases rebuilt from `cards_gained`, `bought_colorless` flagged; co-op: the
  list as recorded, `usable = false`). `?` fights count as combat/elite/boss; a `?` event that
  turns into a fight (`event_combat`) is left out of `primary_offers` because its list can
  mix event and fight offers. `primary_offers` = solo, no modifiers, not modded,
  combat/elite/boss, not a mod card; abandoned runs stay in, flagged. *Superseded
  (follow-up PR): `event_combat` lists are fight rewards (event cards go to
  `cards_gained`), so they are split into screens like combat and kept in
  `primary_offers` with `event_fight = true`. On 2 fetched pages (2026-09-25, 2,000
  records) the 87 solo event-fight lists were 84 of 3 cards, 1 of 4 (Lasting Candy held)
  and 2 of 6 (The Lantern Key; one with Driftwood, one on v0.98.3 with none of Prayer
  Wheel, Driftwood or White Star, cause unknown).*
- Lasting Candy adds a card on some fights only (solo, candy held: 216 three-card vs 159
  four-card lists on 2 pages), so a candy holder's screen size is 3 or 4: a combat list is
  split when exactly one of them divides its length (12 with candy stays NULL).
- Player IDs and the export's `player_token` are HMAC-SHA256 hashed (first 16 hex); key from
  `SPIROMETRY_SALT` or the git-ignored `.spirometry_salt` (`init-salt` creates it). Solo id 1
  stays `'1'`. The key's fingerprint goes in `build_info` so builds can be checked for the
  same key. `run_key` is a plain SHA-256 of `seed|start_time` (not personal data); from
  parser 1.6.0 of `seed|start_time|characters|ascension` (see below).
- Modded = a quoted id with a `-` anywhere in the record (cards, characters, acts,
  monsters, ...), a `save_dict_*` key, or a modifier id ending `_MODIFIER`.
- Mod enchantments: any `ENCHANTMENT.<id>` in the record (on any card, or in
  `cards_enchanted`) whose id isn't in the game's list (`/api/enchantments`, cached in
  `reference/raw/enchantments.json`, 22 ids) is a mod marker, like the five-character rule.
  `card_offers.is_mod_enchantment` flags the offer. Found because `RUNE_OF_CORRUPTION`
  (amounts 110,111–123,013) broke the first full build.
- Run-table integer types (CC's choices, open to review): SMALLINT only where the game
  bounds the value (`act`, `acts_reached`, and position/length within one floor's list:
  `list_pos`, `list_len`, `list_n_picked`, `screen_size`, `set_idx`). Values copied from
  the record or counted over lists a mod or edited save can grow are INTEGER; `run_time_s`
  is BIGINT. Values are stored unchanged, never clipped.
- A page that fails to parse or write is skipped whole (no partial files), reported with
  the exception and run_hash (and the column and value for a type overflow), listed in
  `build_info` (`pages_failed`, `pages_failed_detail`); the build finishes the other pages
  and exits 1. `records_read` counts written pages only.
- Exact repeats (same `run_hash`) are dropped from the base tables, keeping the first by
  (page, line); `build_info` counts them and how many repeats differed in content.
- Primary population (audit): also drop non-release builds (not in `builds.csv`) and runs
  whose start date is before their build's release date. Parser flags: `runs.released`,
  `runs.before_release` (false where `builds.csv` has no date, e.g. v0.98.0).
- Run-table follow-up (CC's choices, open to review): `primary_offers` = solo, no
  modifiers, not modded (the five-character check included), `released`, not
  `before_release`, `neow_start`, sources combat/elite/boss/`event_combat`, not a mod card;
  it also carries `event_fight` and `uploader_tag`. `has_player_token` is NULL when the
  record has no `player_token` key (page downloaded before ~2026-09-25), false when the key
  is null, true when it holds a token.
- Mod characters: anything outside the five real characters is a mod marker (supersedes
  relying on a `-` in the id; `CHARACTER.WATCHER` has none).
- Event-then-fight floors (rooms `[event, monster]`) are kept in `primary_offers` with an
  `event_fight` flag, superseding their exclusion above. In 3 local pages, 118 of 121 solo
  lists were plain 3-card rewards, the 6-card ones came with Prayer Wheel or Driftwood as
  on plain combat, and event rewards go to `cards_gained`, not `card_choices`.
- `_sts` is the SlayTheStats mod's upload stamp (see SPIROMETRY.md). Uploader groups
  (tagged vs. untagged) rank cards differently, so pick-rate estimates are made within
  group or with uploader group as a covariate; pooled estimates are a robustness check.
  Tagged share by play date is not used as a population measure.
- Audit tooling (`scripts/audit_extract.py`, `notebooks/01_data_audit.ipynb`) is interim:
  aggregate tables only, no player IDs. Column names follow the run tables where they
  overlap; the notebook moves to the Phase 3 tables once they exist for the full snapshot.
- Cheat candidates (fast or impossible wins) are flagged, not filtered: 70 of ~98k wins.
- Runs whose first floor isn't Neow are dropped from primary (~15% of v0.98.0, ~5% of
  v0.98.1, ~0 after; launch builds outside the patch windows).
- Thin builds: pooled with a same-branch neighbour when no card change falls between them;
  otherwise left out of windows they can't fill. Comparisons use windows, not single builds.
- Staggered rollout is feasible on volume (every stable build overlapped 1–4 betas with
  21k–44k runs each); estimated within branch or with branch-specific trends.
- Uploader groups differ already before community tooltips (v0.103.2: sd z 3.76, Spearman
  0.93; v0.107.1: 4.95, 0.86): treated as selection, estimates stratified or adjusted.
- Win rates drift within a build over calendar time (v0.103.2, both uploader groups): win
  analyses control for week or ascension, not only build.
- Card-change decisions are applied in the build scripts (CC's choices, open to review):
  `patch_history.RELABELS` / `ARTIFACTS` name the card-patches and the label the classifier
  must give (the build stops if it no longer does); `classified_as` keeps the classifier's
  label and `decision` says what changed. Notes-only rows are generated from
  `crosscheck.csv`'s "notes only: missing from card_changes" rows by
  `notes_crosscheck` (field `(patch notes)`, `old`/`new` blank, `beta_build` = the beta
  whose notes list the change as subject in a content/balance section, the first if
  several do (Dazed, Prepared: v0.100.0, also v0.101.0, named in `decision`), notes quoted
  in `decision`); the cross-check itself compares only the
  changelog rows, so the result doesn't feed back into it. All 12 notes-only rows are
  added, including Dazed (the notes change encounters that apply it) and Prepare/Prepared
  (reworked and restored within the window). `patch_history build` also reruns the
  cross-check, so one command rebuilds everything.
- `card_changes.csv` carries `multiplayer_only`, `rarity` and `color` from the cached card
  list (current card, not the card at the time of the change). Nothing is filtered on them;
  the build's tweak report lists the 7 of 50 numeric tweaks that character card rewards
  can't offer (colorless, Basic, Token; Believe in You is also multiplayer-only), so the
  analysis can say which changes the solo design can estimate.
- Artifact rows in `beta_card_changes.csv`: an update-history entry with no changelog
  behind it whose every field goes to `none` (the five v0.106.1 entries). Wither's v0.106.0
  entry (cost, keywords, damage change) stays unlabeled.
- Thin betas: no card change between v0.99.0 and v0.99.1, v0.103.0 and v0.103.1, or v0.105.0
  and v0.105.1 (card_changes, beta_card_changes, behavior_changes, update-history, patch
  notes). v0.103.1 carries one bug-fix behavior change (Not Yet no longer generated in
  combat; sensitivity list only). v0.103.x and v0.105.x pool.
- v0.99.0 is left out of all windows rather than pooled with v0.99.1 (Phil): the pair
  crosses branches (v0.99.0 beta, v0.99.1 stable), and v0.99.0 has 295 primary runs.
- Mod events, encounters and monsters: any `EVENT.`/`ENCOUNTER.`/`MONSTER.` id in the record
  that isn't in the game's lists is a mod marker, like the enchantment rule. "The game's
  lists" = Spire Codex's stable list, each beta build's list (`?version=`), and every id a
  cached changelog adds, removes or changes, so removed content (Doormaker, Toadpoles,
  Door) and beta-only content (`BATTLEWORN_DUMMY_EVENT_V2_ENCOUNTER`, v0.108.0+) are not
  markers. `runs.mod_markers` lists which markers a record carries.
- Treatment tables (CC's choices, open to review): an event is one card changing on one
  build. Stable-window card-patches are split into one event per beta that touched them
  (`beta_build`, "field also changed in", the card's notes and `beta_card_changes.csv` in
  the window); a field several betas touched is split by a patch-note chain from its old
  to its new value, or else marked `?` between the first and last beta (not guessed).
  Events carry the card-patch's `change_kind` when they hold card_changes fields; the
  others (notes-only steps, everything after v0.107.1) get a kind by rule
  (`treatment.notes_kind`). `stable_build` is blank for events reverted before stable.
- Treatment windows at two levels (Phil): `event` (one card change on one build, both
  branches) and `card_patch` (a card_changes card-patch, stable only; the minimum result
  compares these). `kind_source` = card_changes / notes-only / beta_card_changes /
  text rule / behavior, so analyses can keep curated labels only.
- Card versions (CC's choices, open to review): betas carry every event first seen on a
  beta at or before them; stables carry every event of their window and earlier ones,
  reverted pairs included; hotfixes carry none of their own. Stable-only events reach betas
  released after them; a stable bug-fix row with a pending beta row of the same card is
  that fix's stable copy and doesn't reach betas. `version` numbers each distinct set of
  carried card events in release-date order (a revert gets a new number); behavior events
  are listed apart and never change the version. Blank: v0.98.0, the `-beta`
  pseudo-versions, and betas where an event's timing is unknown.
- Windows (CC's choices, open to review): per event and branch, after = the first block
  carrying the event, before = the block just before; clean when the card's event sets
  differ by that event only. Blocks = single builds, except the audit's thin builds
  (v0.103.1, v0.105.0, v0.109.1) pooled with a neighbour carrying the same card events for
  every card. Stable windows run v0.99.1 → v0.103.2 and v0.103.3 → v0.107.1. Control
  exclusions = same-color cards whose card events differ between the blocks; behavior
  events are flags only. v0.110.1 isn't on the thin list (the audit's snapshot ends
  before it), so it isn't pooled.
- Mod-entity rule, to change when new content ships: it checks ids against the union of
  all cached game lists. When official act 4 (or any new content) ships, re-cache the lists
  for the new builds and check each run against its own build's lists, plus a backstop
  (act 4 content on a build before its release = modded), so a mod id that collides with
  a new official one doesn't un-flag earlier modded runs.
- `pyfixest` for Phase 5's fixed-effects regressions (CC's choice, open to review): added
  to the `analysis` extra unpinned, like the other dependencies; 0.60.0 installs and
  imports on Python 3.11. Pin it (or set a floor) if a result must be reproduced exactly.
- Tweak sizes (CC's choices, open to review): main field and ratio as in
  `spirometry.tweaks`; the upgrade delta is assumed to apply to the main field when both
  changed (true for all 50). Upgrade-only tweaks have no main field; their upgraded ratio
  needs the base value, taken from an earlier card-patch of the matching field when there
  is one (Untouchable v0.107.1: block 6), else blank (Serpent Form, Royalties).
  `mixed_direction` compares the sign of every changed numeric field, vars and upgrade
  included. `direction` = +1 for all 50 (`tweaks.DIRECTION` is empty). Death March is
  flagged in `note` (`tweaks.NOTES`), not upgrade-only.
- DiD tooling (CC's choices, open to review): its own module `spirometry.did` and its own
  `spirometry.tweaks` (not a treatment subcommand). `uploader_hash` comes from joining
  `runs` (it isn't in `primary_offers`). "Character's offers" = offers to that character of
  cards of its color (colorless and other cards dropped); offer shares use that total.
  `control_cards` takes the data frame to know which cards were seen (without it, the
  card list's cards of that color). `offer_rate_check`'s binomial z measures the log ratio
  against the controls' median, not zero (shares sum to one, so one card's jump moves all
  the others), and z/flag are computed for every card. Rows with NULL ascension are
  dropped from fits. pyfixest's default singleton drop is kept and counted. The screen
  filter (`drop_shared_screens`) runs before the upgraded/group filters, on screens as
  offered. `fit_did` refuses a fit with no treated or control offers in a block (reason in
  `run_all`'s `error`). The event study also takes `upgraded`, `group`, `pooled_groups`.
- `primary_offers` deduplicated by run (CC's choices, open to review, parser 1.5.0): it
  joins `runs_dedup` instead of `runs`, so a solo run uploaded twice (same `run_key`,
  different `run_hash`) counts once. The copy kept is the one `runs_dedup` keeps (first by
  page, line), not the one with an `_sts` tag or a `player_token`; the filters and
  `uploader_tag` come from that copy. `build_info` gets `solo_run_keys_multi_record` and
  `primary_offers_dedup_removed`. Test variants of a fixture run now get their own seed
  (a new `run_key`) so they stay separate runs.
- Phase 5 first pass (Phil): the second patch's before block stays v0.103.3 alone. Dropping
  first-patch cards from its controls changes nothing; pooling v0.103.2 moves several
  estimates because the treated cards drift over time, not the controls.
- Pre-trends are judged by the weekly slope before release; the χ² screen is a flag only
  (it ignores correlation between weeks).
- Uploader-group terms stay in the main model although they changed nothing on the first
  pass (the tagged share moved little); the pooled fit stays a robustness check.
- Clustering is judged against heteroskedasticity-robust SEs, not iid ones: the iid ratio
  mostly measures differences in p(1−p) between cards.
- The heavy-uploader check is deferred: the 949-page tables have no `uploader_hash`.
  (Superseded 2026-09-29: run on the 1,393-page tables, top 10 uploaders by solo runs.)
- Phase 5 follow-up tooling (CC's choices, open to review):
  - `se_hc` is pyfixest's `"hetero"` (HC1) on the same fit; `se` (clustered by `run_key`)
    stays the main error and the only one `ci95` and `run_all`'s `se_lo` use.
  - `max_week_after` filters on `load_window`'s `week` (whole weeks from the first
    after-build's release date), inclusive, after the other filters (the shared-screen
    filter still sees screens as offered). Offers of before-builds played after the release
    are before-block offers and are kept at any week. The event study doesn't take it (it
    already estimates each week separately). The output also carries `after_week_max`, the
    latest after-block week actually in the fit, so an uncapped fit shows its horizon.
  - Same-rarity comparison: rarity from the cached card list (current rarity, with
    `card_changes.csv` as fallback for cards not in it); a card's comparison group is
    the controls of its rarity with a finite log ratio, the card itself included when it
    is a control (as in the all-controls statistics). Fewer than 5 such controls, or no
    rarity, falls back to all controls with a note. The binomial SE is the same as for
    the all-controls z.
  - Dedup key: the brief's suggestion, `run_key` itself rather than a separate key for
    `runs_dedup`, so every table and the DiD's clustering use the same notion of a run.
    Characters are sorted (co-op copies can list players in different orders; seen once
    on 2 pages) and joined as text; a missing ascension or character hashes as `None`.
    `scripts/audit_extract.py` keeps its own `seed|start_time` key (not part of this
    change). `build_info` reports the split at the level of old keys
    (`old_run_keys_split`, and `solo_old_run_keys_split` among solo records, the number
    comparable to the 18) plus the new keys in them (`run_keys_split_from_old_key`).
  - The collision fixture is built in the test (records derived from the sample file, as
    the other variant tests do) rather than added to `sample_runs.jsonl`, so the fixture's
    existing counts don't change.
- Dose-response uses fixed-horizon estimates, after-build weeks 0–3 (Phil), so the two
  patches compare at the same horizon; all-weeks estimates are the check.
- Clustering measured against robust SEs: median 1.03, range 1.00–1.20 on the 43 tweaks.
  (An earlier "about 8%" was an approximation from iid ratios and is superseded.)
- Retried runs (Phil): solo runs whose copies share seed and start time but differ in win,
  floors reached or abandonment (a restored save; 54 on the 949-page tables, 72 primary on
  the 1,393-page tables) are dropped from win analyses; pick-rate analyses keep one copy.
- Deck size / timing: no control added. Offers are random in timing and the act mix moved
  alike for a character's cards (checked per tweak); deck size is partly caused by earlier
  picks, so it is described, not controlled for.
- Win-effect tooling and parser 1.7.0 (CC's choices, open to review):
  - First K screens: combat, elite, boss and event-fight rewards (the `primary_offers`
    sources), numbered by floor then `set_idx`; a two-screen floor (Prayer Wheel) counts
    as two screens. A list that couldn't be split into screens counts as one row in the
    numbering and marks the run `ambiguous_screens`; such runs stay in the tables and leave
    the fits (0 of 1,277 on 2 pages: the 13 unsplit lists in non-abandoned primary runs
    all come at screen 8 or later; no single relic behind them, 12 are 4-card lists
    without Lasting Candy). Runs with no reward screen at all stay in `early_runs` with
    `n_screens_reached = 0`.
  - Win population: `runs.PRIMARY_RUN_FILTER` (factored out of `PRIMARY_FILTER`, same
    conditions) on the record `runs_dedup` keeps, not abandoned, not retried; character
    from `run_players` (player 0). Runs without ascension or week are left out of fits.
  - `week` in `spirometry.wins` = whole weeks from the run's own build's release date (per
    build, unlike `did`'s window-relative week). v0.98.0 has no release date: no week, so
    its runs leave the fits (it is outside every patch window anyway).
  - Estimators take a `load_early` result (runs + offers, with K) rather than a flat data
    frame; `early_offers` returns the flat (run, card) table the brief describes. `K` on
    an estimator only checks that the data was loaded with that K. Functions, not views
    (lighter on memory: only the selected character and builds reach pandas).
  - Fixed effects as precomputed combined columns (`build_group`, `build_week`, `asc`);
    within one group or with `pooled_groups`, build alone. Errors HC1 (`"hetero"`). First
    stage F = (coef/se)² with those errors (with one instrument this is the robust Wald F);
    `weak` = F < 10. Singleton cells are dropped (pyfixest's default) and counted.
  - `naive` is on all runs, as the brief says; `among_offered=True` gives the
    took-vs-passed comparison among offered runs. `run_all_cards` counts offered runs
    among the runs the fits use and keeps cards of the character's color only.
  - Added beyond the brief: `screen_mix` (first K screens' sources as a fixed effect: an
    early elite is a choice and offers rarer cards; 9.6% of runs on 2 pages), off by
    default so the main model is the brief's; `reach_share`.
  - `retried` compares min and max of `win`, `floors_reached`, `was_abandoned` over the
    `run_key`'s copies (NULL counts as its own value). `build_info`:
    `solo_run_keys_retried`, `primary_run_keys_retried` (the kept copy passes the primary
    filter).
  - `deck_size_before` = deck at the start of the offer's floor: starting deck (final deck
    − all gains + all removals) + gains − removals on earlier floors; transforms count as
    zero. The starting deck is derived, not assumed; the game's starting sizes (10, Silent
    12, +1 Ascender's Bane from A5) are used only for the `build_info` check.
    `run_players.deck_size_start` added for that check.
  - `did.load_window` returns `set_picked_any` by default (the brief allowed it); the
    extra columns come only with `extra_cols=True`. `picked_screens_only` drops offers
    from unsplit lists (their screen is unknown). `card_act_fe` drops the separate act
    term (nested in card^upg^act).
- Win-effect review round (PR #12):
  - Treatment = took X on one of the first K screens (not later rewards, shops or
    events); stated in the docstrings and SPIROMETRY.md.
  - Short runs (Phil asked for keeping them as the default; CC kept dropping them; merged
    as is after review, K = 1 is the planned check): every run that doesn't reach screen K lost and had fewer screens on which
    to be offered, so counting unreached screens as "not offered" gives every card a fake
    positive ITT (synthetic null: +0.08, z ≈ 13). Dropping them is biased only if an early
    offer changes survival to screen K; the check for that is K = 1 (every offered run
    reached screen 1), which recovers the total effect in a synthetic test where an early
    offer kills. `include_short_runs=True` stays as a check.
  - Retried: `RETRIED_SQL` coalesces NULL to −1 before min/max, so a NULL copy next to a
    non-NULL one counts as a difference; all-NULL copies agree. Tested.
  - One row per run: the fits' HC1 errors (no clustering) rely on it; `load_early` and
    `run_frame` raise on a repeated `run_key`.
  - `screen_mix` stays off by default until the full-table results (Phil).
  - `did.run_all` output: the pre-PR columns plus `card_act_fe` and `picked_screens_only`
    (settings echoes, like `max_week_after`); notebook 02 loads files saved before them.
- Rerun on the 1,393-page tables (2026-09-28/29): no decision changed. v0.110.0 (331
  primary runs, superseded by the v0.110.1 hotfix the next day) is thin; the reference
  tables show no card change on v0.110.1, so by the pooling rule it pools with v0.110.1
  (to confirm against the patch notes; it only matters for the beta designs).
- Strength-change tooling (CC's choices, open to review):
  - Its own module, `spirometry.strength` (wins.py stays within one set of builds). It
    reuses `wins`' run frame, fixed effects, formulas and errors; `block_estimates` builds
    the run frame once per block and gives the same numbers as `wins.itt`/`first_stage`/
    `iv` (tested).
  - Differencing two fits, not one stacked fit. The blocks are different builds, so
    different runs, and `build^group` and `week^build` are already block-specific: a
    stacked fit with the ascension term also interacted with the block is the same
    regression (same ITT change, same se up to HC1's dof factor; tested), and
    pyfixest's IV refuses more than one endogenous variable, so a stacked IV would need
    hand-rolled 2SLS for nothing. A stacked fit with a shared ascension term would
    assume ascension affects winning the same way in both blocks, which the drift within
    builds doesn't support.
    "Net of controls" is then the median of the controls' changes (robust to a few odd
    controls), not a regression term.
  - "Unusual next to controls": all of `z_spread` (against the controls' MAD), `z_se`
    (against the card's own se, the median's se added: with 8 controls in the synthetic
    test, one null seed gave z_se 3.1 without it (raw z 1.8); the median's se is about
    0.2 MAD with 40 controls) and `z_total` (both: own se and the spread between cards
    beyond noise, τ).
    Computed for every card, so the controls' distribution of z's is the reference;
    `controls_share_abs_z_se_gt2` says whether the se's hold up (about 0.05 expected).
  - ITT and first-stage changes are reported beside the IV change, with the same net-of-
    controls columns. The ITT change is not a strength change when the pick rate moves
    (ITT = first stage × effect); the first-stage change is the pick-rate change on the
    same runs.
  - Weak first stage (F < 10) in either block, for the treated card or a control: the IV
    change is blank with `iv_reason` (block and F), the control is left out of the median
    and counted (`n_controls_skipped_weak`); ITT and first-stage changes stay. Fewer than
    `min_offered` (500) offered runs in a block: every change blank, counted
    (`n_controls_skipped_few`). Fit errors counted as `n_controls_error`.
  - Short, smaller before blocks (the second patch's v0.103.3: about three weeks and about
    half the runs of v0.99.1 or v0.103.2; not a thin build, which means under 2,000 primary
    runs): no special handling; `n_runs_*`, `n_offered_*` and `n_picked_*` per block are in
    the summary, and the se's carry the smaller counts. No pooling with v0.103.2 (Phase 5 first-pass decision: v0.103.3 alone).
  - Multiple comparisons: nothing adjusted in the tooling; the summary has one row per
    tweak (43, 3 of them skipped as upgrade-only), so the notebook can count. Partial
    pooling (step 7) is the planned answer.
  - Upgrade-only tweaks (Serpent Form v0.103.2, Royalties and Untouchable v0.107.1) are
    out for now, listed in the summary with `skipped`.
  - Controls = color cards offered in either block, minus the treated card and
    `control_exclusions` (`did.control_cards`); a control seen in one block only gets a
    blank change with the reason.
  - `balance_check`'s joint test is conditional on build (the fits have build fixed
    effects; a pooled block's builds may offer a card at different rates without harming
    the design), HC1 Wald by hand (numpy) rather than a pyfixest call; levels with fewer
    than 20 runs are pooled into the reference level (single-run cells fit exactly and
    made the robust test reject 22 of 47 cards on the 2 pages; 2 after pooling).
    `screen_sources` is tested separately (`p_screens`): failing it points to
    `screen_mix`, not to a broken RNG.
  - Controls matched on first stage (Phil, review round): `_m` columns for iv and itt,
    the all-controls columns stay the headline. k = 20 nearest controls by first stage,
    matched in each block separately; the net is then taken on each block's levels
    (card − matched median) and differenced, since the two blocks' sets need not be the
    same cards. CC's choices, open to review: the controls' strength differences between
    the two sets enter `net_m` and are counted in its error (each block's median se from
    the MAD of the matched controls' estimates, which includes the spread between
    cards); eligible controls are those with a non-weak fit in that block (a change in
    both blocks isn't required); every card gets the columns, a control matched against
    the others; no `fs` matched columns (matching on fs makes them ≈ 0 by construction).
    Caveat: if strength rises with pick rate, a card taken more after a buff meets
    stronger controls after than before, which pulls `net_m` toward zero or below.
    Synthetic Parry-like case (k = 3): all-controls net +0.20 (z 2.4), matched −0.01.
  - Complier shift (Phil): the IV is the effect for runs that take the card when offered;
    after a buff the takers change, so an IV change can be a change in who takes it.
    Documented next to the ITT caveat; `fs_change` measures it.
  - Runtime: about 0.1 s a fit on 30,000-run synthetic blocks. Full tables: at most
    9 (character, window) groups × ~88 color cards × 2 blocks × 3 fits ≈ 4,700 fits,
    fewer after `min_offered`; one per (card, block) is shared by the window's tweaks.
    Estimated 10–15 minutes per option set (not yet verified); `strength_all` prints
    each window's elapsed time to check it; `save`/`load` cache the result as parquet.
- Anticipation check (CC's choices, open to review):
  - `beta_exposure.csv` from its own module (`spirometry.exposure`), since it reads the
    event tables `tweaks` doesn't. First beta = the earliest `first_beta` of the
    card-patch's member events (for revised changes, the first step; Phil's suggestion).
    Upgrade-only tweaks list the upgrade field's steps. `other_events_after_first_beta`
    counts the card's non-member events with a release date from the first-beta date to
    before the stable date (0 for all 43).
  - The widened before window is the default of `anticipation_check`
    (`widen=False` for the window's before builds only), and only for this check. Rule:
    stable builds with identical card versions for every card of the color, among the
    builds some card-patch window uses. Confirmed from `card_versions.csv`: v0.103.2 and
    v0.103.3 differ on 0 cards (every color) in version and in card events (tested); they differ
    in bug-fix behavior events on Bad Luck, Stardust and Summon Forth, which are dropped
    from the controls by default. v0.98.x also match v0.99.1 but are left out (launch
    builds, outside every window).
  - Thresholds: 2,000 treated offers and 3 days with a treated offer on each side
    (arguments). 2,000 a side gives a pick-rate se of about 1.4 points at a 25% pick rate.
    Rough count (not yet verified): 17 of 43 informative at real sizes.
  - Split by the run's UTC start date (as `before_release`), never by build; runs started
    on or after the new stable's release dropped (`until_stable`). For the second patch
    the pre-beta side is v0.103.2 only and the post side is mostly v0.103.3, so a
    build-level change shows up as anticipation; `treated_offers_by_build` shows it and
    `builds=["v0.103.2"]` keeps it within one build. No build fixed effect in the main
    call (it would absorb most of the split).
  - Beyond the brief: `total_implied` and `share_before_release`. `ratio_to_main` is kept
    as asked, but under anticipation beta_main is itself too small by
    main_postbeta_share × beta_postbeta (synthetic ramp: ratio 0.51–0.62 while the true
    share is 0.5).
  - A steady drift through the beta date is returned as a nonzero `beta_postbeta`; not
    corrected. `pre_slope` and the weekly table are the diagnostics.
- Rerun on the 1,513-page tables (2026-09-29), notebooks 01, 02 and 03: no decision
  changed. The anticipation check's informative rule (at least 2,000 treated offers on each
  side of the first-beta date and at least 3 days before it) is the tooling default, left
  as is; 14 of 43 tweaks pass.
- Same-size comparison added to notebook 02 (section 8): the two patches' tweaks match in
  size and precision, so the second patch's flat slope is not a power or change-size
  artifact. Recorded as a finding, not explained.
- Dashboard and results export (open to review; nothing built yet): aggregates only, from the
  saved fits, with no run-level rows or uploader identifiers; Streamlit as the default; no
  deployment until the release checklist (Next up 12) is done.
- Results export and dashboard (CC's choices, open to review):
  - Inputs are only the files the notebooks save; nothing is refitted. The export reads
    `did_main`, `did_h3` (`--horizon`), every other `did_*.parquet` as a robustness check
    (`robustness.csv`, beyond the brief), `event_studies`, `did_second_patch_checks`
    (their variants go into `flags.csv`), `anticipation_main` (optional) and
    `offer_rate.parquet` (optional: notebook 02 doesn't save its offer-rate table, so the
    flag columns stay blank until it does; a note in `meta.json` says so).
  - `patch` = first / second by the stable build's release date in `builds.csv`;
    `window` = "before -> after builds". The notebook's window labels aren't saved.
  - `beta_lo` / `se_lo` are recomputed from each fit (delta method with that fit's
    treated pick rate before) for both horizons (`_h` for weeks 0–3); the dose-response
    table has both horizons, four models each, so the dashboard switches without
    refitting. Extra columns beyond the brief: `character`, `change` (buff / nerf, as the
    notebook's forest plot colors them), `dose_x`, `dose_x_upgraded`, `ci_lo_h`/`ci_hi_h`,
    `clearly_nonzero_h`, the upgrade fields; `se_main`, first-beta build/date and stable date
    in `anticipation.csv` (from `beta_exposure.csv`).
  - `toward_change` is computed for every tweak with a single direction, not only the
    clearly nonzero ones; the dashboard counts "clearly nonzero and toward the change".
  - Pre-trend slope = the notebook's `pretrend_summary` slope (weighted, before-block
    weeks < 0), without the χ² screen; blank with fewer than two such weeks besides the
    reference week (as in the notebook).
  - Privacy checks on every output: identifier column names (`uploader_hash`, `run_key`,
    `run_hash`, `seed`, `player_*`), string cells that look like a hashed id (16 or 64
    hex characters) and repeated keys stop the export. Event-study cells with fewer than 10
    treated offers are dropped (`--min-cell-offers`); the dashboard hides cells under 100
    by default, as the notebook's plots do.
  - Error rows (`error`, anticipation `status = error`) stop the export; `--skip-errors`
    leaves them out and lists them in `meta.json`. A failed placebo only blanks the placebo.
  - `meta.json`: `build_info` only with `--db` (read-only). `build_info` has no
    snapshot end date, so it stays blank unless given with `--snapshot-end`.
  - `results/` is git-ignored until the release checklist is done; `results_sample/`
    (synthetic, cards named SAMPLE_01…, generated by running the real export on
    `spirometry.sample_results`) is committed so the dashboard runs out of the box.
  - Dashboard: Streamlit + Altair (Altair ships with Streamlit and its declarative charts
    read close to the notebooks' matplotlib). Observable Framework would give a static site
    that is easier to host later, but it isn't clearly better for a local, Python-only
    project. Colors: Okabe-Ito blue / vermillion for buff / nerf, goldenrod / purple plus
    circle / square for the patches, checked for colorblind separation on the light theme
    (`.streamlit/config.toml` pins it). No result numbers or interpretation in the code;
    the About page points to SPIROMETRY.md.
- Workflow: Phil pushes and merges everything himself. CC sessions open pull requests and
  stop; documentation edits are prepared as `_new` files against a synced copy and moved
  into place by Phil.
- Notebook prose pass (one-time, 2026-10-02, CC at Phil's request; an exception to "analysis
  notebooks are Phil's"): markdown cells only in notebooks 01–05 and `iv_primer`. Questions
  used as headings, transitions or prompts rewritten as statements (fill-in cells kept, their
  headings made plain labels); terms defined at first use; stale "Draft, not yet run" notes
  and wrong cross-references fixed. Code cells, outputs, execution counts and metadata
  unchanged (hash-checked); no notebook was run. Follow-up on the same PR (Phil's decisions):
  notes cells, the decision-rule cell and the review checklists removed (notebooks hold no
  notes or checklists; what the notebook can't test stays as prose); prose numbers corrected
  where an output or `builds.csv` gives the value; notebook 02's version history moved out of
  its opening (see the next entry).
- Notebook 02 versions: v1 = first pass (949-page tables, parser 1.4.0, 2026-09-26; saved fits
  in `data/analysis_p949/`); v2 = after PR #11 (robust SEs, fixed horizon in section 6b,
  same-rarity offer-rate flags, patch term in the dose-response, section 0's check of what
  differs between copies of a duplicated run); v3 = after PR #12, 1,513-page tables, parser
  1.7.0, with the heavy-uploader check.
- Control scope (`did`'s `control_scope`, 2026-10-02): `"color"` stays the default and
  exactly the old definition. Colorless (and token, status, curse, event, quest) cards are
  controls under no scope: under `"color"` they never were; they are offered to every
  character, so under `"other"` they would bring the treated character's own runs and
  screens back into a group meant to have none; and they are rare in the reward offers the
  fit uses (shop, events and ancients are their sources). Each card's offers come only
  from its own character's runs (a card offered from another color's pool is not loaded),
  so `"all"` is `"color"` plus `"other"`. Other colors' changed and bug-fix-flagged cards
  are derived at run time from `card_versions.csv` with `windows.csv`'s rule (no new
  reference columns); the flags use its `behavior_event_ids`, which come from
  `behavior_changes.csv`, rather than reparsing that file, so the rule is the same one.
  The model (fixed effects, covariates, clustering) is identical across scopes, with no
  color or character terms, so differences come from the choice of controls alone.
- Placebo calibration (`did.placebo_fit` / `placebo_all` / `placebo_summary`, 2026-10-02):
  the pseudo-treated card is a same-color control card (`control_cards` with
  `control_scope="color"` and the fit's `drop_behavior_flags`), whatever `control_scope`
  the controls use; the window's real treated card is out of the data, the pseudo card out
  of the controls; model, clustering and options are fit_did's (upgrade-only tweaks on
  upgraded offers, as `run_all`'s main fit). Minimum offers: fit_did itself needs only one
  treated offer per block, so "what real tweaks need" is taken as what the least-offered
  real tweak has: a pseudo card needs at least the smallest min(before, after) treated
  offer count over all 43 solo-estimable tweaks (counted as loaded, ascension known,
  upgraded only where the fit is, after weeks capped by `max_week_after`; before the other
  fit filters), overridable with `min_offers`. Sampling is seeded per tweak by
  (seed, card_patch_id), so a subset run draws the same cards. Tweaks sharing a window can
  draw the same pseudo card (fits differ only in which treated card is left out), so the
  rows are not independent. Size split in `placebo_summary`: at the median of the pseudo
  card's offers in the fit. Not added to `spirometry.export`: its robustness table has one
  row per (tweak, check) for the real treated card, and placebo rows are several per tweak
  on other cards.
- Placebo diagnostics (2026-10-02, branch `placebo-calibration`; tables and tooling only,
  in `did` and `meta`, no notebook changes): dedupe rule: one row per (window, pseudo
  card), window = color + before/after builds + fit_on; beta, se, z and the size columns
  are the mean over the tweaks sharing the pair (their fits differ only in which real
  treated card is left out, so they are near duplicates; z is the mean of the z's).
  Robust summaries (median |z|, 1.4826 × MAD, quantiles) sit next to sd and the |z| shares
  because a few extreme fits can drive an sd. `placebo_vs_real` compares each tweak with the
  placebos of its own window (same color, builds and fit), not the pooled set: those share
  the tweak's players, weeks and fit, so the comparison holds them fixed; it needs at least
  5 placebo pairs (`MIN_PLACEBO_CARDS`), else empirical_p and calibrated_z are blank. The
  dose-response sensitivity inflates each patch's se_lo by a factor and refits the
  random-effects model (τ² re-estimated); factors come from the deduped summary by patch.
  Placebo fits are all weeks, so the sensitivity uses the all-weeks estimates, not weeks 0-3.
- Triage (2026-10-07/08, `triage/TRIAGE.md`, merged as #19): read-only investigation of the
  flat second patch, Parts 1 and 2, on the 1,873-page tables. Its numbers are not results until
  rerun on the final tables (Next up 15).
- Primary ruler: ln(new/old). The other rulers, Phil's card-review calls (Grand Finale off,
  Crescent Spear at 0.223) and the hybrid ruler (proposed after notebook 04's results, so post
  hoc) are sensitivity variants (Phil, 2026-10-09).
- Debilitate v0.107.1: a nerf whose size can't be measured (it depends on the build, fight
  length and other sources of Weak and Vulnerable). Sign ruler only. The ln dose-response is
  reported without it (primary) and, as a sensitivity row, with it at the table dose, with the
  reason stated (Phil, 2026-10-09). The triage's z for these two cases (−2.4 and −3.8) are
  from fits with Reflect off; both are recomputed with Reflect on (next entry).
- Mixed-tweak rule (triage B2) adopted (Phil, 2026-10-09), replacing the Strength-range rule
  of 2026-10-07: a tweak is mixed only if the card's total printed output, in the unit of its
  main field, moves in different directions for the base and the upgraded card, or two changed
  numbers in different units move in opposite directions. Direction = the patch-note label.
  Dose = ln(new total / old total) for the un-upgraded card at Strength and Dexterity 0,
  counting generated cards at their printed values. A dose of 0 or of the wrong sign keeps the
  tweak off the line (sign ruler only); game-state ranges are sensitivity only. Leading Strike
  stays off (11 → 11 damage); Reflect is not mixed (17 → 15, upgraded 21 → 20) and goes on the
  line at −0.125. A Shiv deals 4 damage (upgraded 6): verified from
  `notes/patch_history_samples/changelog_1.1.0.json`.
- Weeks 0–3 is the primary horizon for every estimate in field guide v2; all weeks is
  secondary (Phil, 2026-10-09).
- Week 0 stays at the `builds.csv` date. The stable population switched about 25 hours later
  for v0.103.2 and v0.107.1 (about 01:00 UTC on 04-17 and 06-19; triage G1), the same offset in
  both patches, so it can't make a patch difference.
- Field guide v2 (Phil, 2026-10-09): a personal study guide in v1's voice ("your data", "your
  notebooks") and depth, about 46 pages or longer if a chapter needs it; no reproducibility
  appendix. Publishing undecided. Title "What Did the Patch Do?", with "Spirometry" above it.
  Every number through the generated numbers table and every figure from a script, so a rebuild
  can't leave stale numbers. "Clearly nonzero" is counted with clustered and with
  placebo-scaled errors, the calibrated count first. CC drafts the teaching and method text;
  Phil writes the "what was found" passages and the conclusion. Only if published: the
  generated numbers, figures and PDF are committed at release, after the release checklist
  (Next up 12); the build's privacy check runs either way.
- Win effects for the field guide: a power check on a few cards of v0.107.1 first, with a
  stop rule; the strength change across patches (step 5), hierarchical Bayes, the staggered
  rollout, reworks and the dashboard are future work (Phil, 2026-10-09).
- Before the final rerun overwrites `data/analysis/`, it is copied to `data/analysis_p1873/`
  (as `data/analysis_p949/` and `data/analysis_p1393/`) (Phil, 2026-10-09).
- Sensitivity tooling (CC's choices, open to review, 2026-10-09):
  - The triage's saved-fit computations live in `spirometry.sensitivity`, not in
    `triage/scripts/`, which stays a frozen record. Same model and formulas as the triage
    (`spirometry.meta.meta_regression`, slope per patch, difference from the coefficient
    covariance, ratio by the delta method), so the triage's numbers are the check.
  - Line membership is a named spec (`SPECS`): "triage" (the notebooks' 38), "primary"
    (Reflect at ln(15/17), Debilitate v0.107.1 off the ln line), "primary, Debilitate at
    table dose", "Reflect off, Debilitate off". The mixed-tweak rule's outcome for Leading
    Strike and Reflect is written in as `MIXED_RULE` (the tables hold no card text, so the
    rule can't be applied by code); Reflect's rule dose equals its table dose.
  - Under the primary spec the sign ruler also carries the sign-only tweaks: Leading
    Strike +1 (label), Debilitate v0.107.1 −1. The other rulers use the ln line's tweaks;
    rank and per-kind medians are recomputed on each set, as notebook 04 does.
  - The hybrid ruler is in every ruler table, flagged `post_hoc`.
  - The power simulation keeps the triage's design (seed 20261007, 1,000 draws, planted
    0 / 0.3 / 0.7 / 1.0 / 1.44, three settings), run for the triage and primary specs.
  - The IV primer's game is a module (`spirometry.iv_sim`) rather than a script, so it is
    tested; its functions are the notebook's, unchanged (a test checks the source).
  - Outputs: CSVs in `data/analysis/writeup/` (git-ignored), each passed through the
    export's privacy check before writing.
- Final rerun tooling (CC's choices, open to review, 2026-10-09):
  - Notebook 02's weeks 0–3 checks are compared with `did_h3`, not `did_main`, so a shift
    measures the check, not the horizon.
  - The second patch's before-block variants at weeks 0–3 are saved as
    `second_patch_checks_h3.parquet`, not `did_h3_second_patch_checks.parquet`: the export
    reads every `did_*.parquet` except `did_main`, `did_second_patch_checks` and the horizon
    file as a one-row-per-tweak check, and three rows per tweak would stop it (repeated
    `card_patch_id, check`). The `did_h3_<check>` files do go into `results/robustness.csv`,
    as checks named `h3_<check>`.
  - `scripts/final_rerun.sh` forces refits by moving `data/analysis/` to
    `data/analysis_before_final_<UTC time>/` (a rename; nothing is deleted) and starting
    from an empty one, instead of editing the notebooks' `FORCE` flags. Notebook 02 already
    has `FORCE = True` (the script checks it); notebook 03 refits when its file is missing.
    Old fits that nothing in the rerun remakes (e.g. `did_ctrl_all`) are left behind with
    the rest, so they can't reach the export as if they were current.
  - The placebo calibration and its diagnostics had no script (they ran from a session, as
    in README's `did` snippet); the script runs them inline with the 2026-10-02 defaults.
    The diagnostics CSV names other than `summary`, `vs_real_by_patch` and
    `dose_sensitivity` (named in SPIROMETRY.md / TRIAGE.md) follow the function names; the
    earlier files' other names weren't recorded. `dose_sensitivity` uses
    `sensitivity.placebo_factors` (factor 1, by-patch and one-factor sd and robust sd), a
    superset of the three settings in SPIROMETRY.md.
- Final rerun docs (CC's choices, open to review, 2026-10-10):
  - "Moved by more than one SE" compares each final estimate with the 1,873-page one in units
    of the 1,873-page SE: per tweak for every saved fit present in both
    (`did_main`, `did_h3`, the six all-weeks checks, the second-patch variants), and per
    coefficient for the dose-response, sensitivity and anticipation tables. The 1,873-page
    aggregates were rebuilt from `data/analysis_p1873/` with the same export and sensitivity
    code (into a scratch folder, not `results/`). The weeks 0–3 checks have no 1,873-page
    counterpart. Counts that changed class without a 1-SE move are reported too.
  - Where an existing sentence no longer matched the numbers it was replaced by the numbers:
    "about a third as much" (now median 1.9 against 4.1 points, a bit under half), and the
    anticipation summary "small or on the opposite side of zero" (Crescent Spear and Furnace
    now have same-side, larger post-beta gaps; Crescent Spear already did on the 1,873
    pages). Interpretive text that the numbers still fit was kept as it was.
  - Notebook 02 keeps `FORCE = True`: it has been committed that way since 2026-09-29
    (`False` before), and `scripts/final_rerun.sh` requires it. Notebook 03 keeps `False`.  
  - Numbers table (CC's choices, open to review, 2026-10-14): one key per printed number, 
    dotted lower-case. Estimates come as three keys: <key>, <key>_se and <key>_pm. 
    Negatives print with U+2212. Percent shares are rounded to whole points. Weeks 
    0–3 "toward the change" uses the export's rule on beta_h. The privacy check skips 
    numeric values, because 16 digits of a float match the hashed-id pattern. Only 
    provenance rows are flagged appendix.
- Calibrated "clearly nonzero" (Phil, 2026-10-14): calibrated z = a tweak's z divided by its
  patch's robust placebo sd: `did.placebo_summary`'s `robust_sd_z` (1.4826 × MAD), on the
  deduplicated (window, pseudo card) pairs, the same factor as `se_inflation`'s "robust sd by
  patch". `median_abs_z` is the other robust column; it isn't used because it would need a
  new scale (÷ 0.674). One factor per patch, from placebo fits at the estimate's own horizon
  (weeks 0–3 placebos for weeks 0–3 estimates, primary; all weeks for all weeks, secondary).
  Clearly nonzero = |calibrated z| > 2; toward the change by `export.toward_change`. The
  plain placebo sd is the sensitivity row. The uncalibrated counts stay, labelled
  `uncalibrated`.
- Snapshot dates (CC's choice, open to review, 2026-10-14): `snapshot_start_date` /
  `snapshot_end_date` = the first and last UTC play date over the primary population
  (`runs.PRIMARY_RUN_FILTER`), so launch, playtest and wrong-clock runs can't set the range;
  the same over every record goes in `meta.json` as `play_dates_all_records`.
  `--snapshot-end` still overrides the end date.
- Snapshot size in the numbers table: records and last page come from `snapshot.log` (its
  "total" line and its last page line, numbered from 1), checked against `meta.json`'s page
  count. Distinct runs stays out while 1,525,369 (`--count-only`) and 1,525,329 (audit)
  disagree.
- Field guide skeleton (CC's choices, open to review, 2026-10-14):
  - Chapter plan in `writeup/OUTLINE.md`: 15 chapters (0–14) and appendices A–D. Changes from
    v1:
    - A data chapter.
    - The placebo calibration as its own chapter.
    - Results split from dose-response.
    - Two chapters for the second-patch puzzle.
    - Instruments after the pick-rate story.
    - v1's "next PR" checklist dropped.
    - A skill box in every section.
  - Departures from the Phase 7 / item 11 design:
    - No "generated numbers appendix" listing every key. The decision of 2026-10-09 (no
      reproducibility appendix) wins. The build stamp is on the title page, and Appendix C
      is a one-page recap built from keys.
    - The build reuses `writeup/numbers.json` and rebuilds it only with `--refresh-numbers`.
  - Digit lint:
    - It applies to every chapter file, headings and captions included, after removing
      comments, `#n(...)` calls, `#fig` names and `#import`/`#include` lines.
    - The allowlist is a short list of fixed-term patterns in `spirometry.writeup.ALLOW`,
      each with a comment: weeks 0–3, build names, years, p(1 − p), |z| > 2, 95%, F < 10,
      2×2, step/task/item/notebook/section numbers, and notebook file names. It does not
      exempt whole lines.
  - Figures: `writeup/figures/<name>.png`. A missing file prints a labelled placeholder. A
    file older than the build stamp stops the build.
  - Answers: each stop-and-check question carries its answer in the source
    (`#check(([q], [a]), ...)`), and Appendix A collects them, so they can't drift apart.
  - Chapters are numbered from 0, as in v1; sections are unnumbered.
  - typst from PyPI, pinned at 0.15.0 in the `writeup` extra.
- Field guide v2 scope (Phil, 2026-10-16):
  - The project ends with field guide v2. Item 15 task 9 (win-effect power check), the release
    step and publishing are future work, not planned. Task 7 is replaced by rerunning the
    triage's scripts on the final tables (task A, part 6).
  - CC writes the whole guide, "what was found" passages and the conclusion included; Phil's
    review is reading the PDF. Replaces the task 14 split of 2026-10-09.
  - Chapter 12: the triage checks never rerun on the final tables (fake patch, regression to
    the mean, token subset, control scope at weeks 0–3, per-group dose lines) are rerun by
    their existing scripts where that is cheap; any that can't be are printed from
    `triage/out/` with numbers labelled "1,873-page tables".
  - Chapter 13 teaches instruments with the IV simulation; real win effects are future work.
  - The weeks 0–3 placebo run stays: it supplies the calibrated "clearly nonzero" counts at
    the primary horizon.
- Field guide task A (CC's choices, open to review, 2026-10-16):
  - Distinct runs: the guide prints the audit's 1,525,329 (a run counted once whatever its
    build); `--count-only`'s 1,525,369 counts distinct (seed, start_time) within each build
    and sums, so the 40 runs recorded under two build ids count twice. Shown from the code
    (`snapshot_export.count`'s per-build sets) and the logs (per-build counts equal in
    `snapshot.log` and notebook 01's output for all 26 released builds); notebook 01's saved
    summary confirms it (40 keys in several builds). The run tables' own distinct count
    (`run_key` with characters and ascension, parser 1.6.0) is not in `build_info` and is not
    used.
  - Notebook 01 saves `audit_summary.csv` (one row per number: key, label, value, unit,
    population, definition), `audit_runs_per_build.csv` and `audit_upload_lag.csv` (the two
    chapter 1 figures). Run counts use distinct runs (the funnel's `d`); upload lag, thin
    builds and fast wins use records, as the cells that print them. Tagged against untagged
    win rate: finished primary runs, all builds and v0.103.2.
  - The CSVs were first written by running the notebook's code cells as a script (this
    sandbox can't start a Jupyter kernel); the run script reruns the notebook (18 s) so its
    outputs match.
  - Export: `meta.json` gets `dedup` (records read, exact repeats and how many differed, solo
    multi-record keys, primary offers removed by dedup, retried solo and primary keys) from
    `build_info` with `--db`; missing fields are listed in `blank_reasons`.
  - Weeks 0–3 placebos: one file per horizon (`placebo_main.parquet`, `placebo_h3.parquet`,
    named by `did.placebo_file`); `sensitivity.load_placebo_fits` refuses a file whose rows
    are another horizon. The se-inflation and spread tables keep using the all-weeks fits.
  - Triage scripts: paths by environment variable (`TRIAGE_AN`, `TRIAGE_OUT`, `TRIAGE_DB`,
    `TRIAGE_COLORS=reference` for `reference/raw/cards.json`'s colors, as the saved fits);
    defaults unchanged, so the triage record still reruns as it was. `j_reversion.py` now
    also saves its tables; `i_fake_patch.py` reads the second patch's placebo robust sd from
    the same tables' summary (2.07) instead of the 1,873-page 2.09. The run script checks
    `triage/out/` is unchanged. Printout-only scripts (`g3_analysis.py`, `l_compare.py`) don't
    stop the run.
  - `spirometry.checks` summarises the checks for the numbers table (the triage's
    definitions); a check comes from `triage/out_final/` when all its files are there and
    newer than the tables, else `triage/out/` (1,873 pages), and each row says which; the
    1,873-page comparisons use `data/analysis_p1873/`. The fake patch's expected count uses
    the summary's share of |z| > 2 (5.5 of 14 on 1,873 pages, where TRIAGE.md's 6.1 used a
    different pair set).
  - Numbers keys: one family per tweak (`tweak.<card>.<stable build>.*`, about 60 keys each)
    rather than only the cards OUTLINE.md names, so a chapter can use any tweak; a field
    blank in its source gets no key. Placebo fits are read for `min_offers` only.
  - Figures: matplotlib, the dashboard's colors and shapes; card examples default to Parry
    and Corrosive Wave; `fig_event_study`'s second card is the steepest pre-trend
    (|slope / se|); `fig_forest` draws the placebo-scaled interval with the weeks 0–3 factor
    when it exists, else the all-weeks one, and says which.
- Field guide task B (CC's choices, open to review, 2026-10-16):
  - One new key, `const.earlier_tables.pages` (1,873, from `spirometry.checks.TRIAGE_PAGES`),
    so the guide can label numbers measured on the triage's tables without a hand-typed digit.
    No other key added; numbers.json otherwise unchanged (6,123 keys).
  - Digit lint: two allowlist entries, the game's name ("Slay the Spire 2") and a capitalised
    "Weeks 0–3" in table headers. Illustrative numbers in pictures and questions ("ten coin
    flips") are spelled out; every data number goes through `#n`.
  - `style.typ`: `lead` (chapter subtitle), `rest` (a flexible column width, so tables carry
    no digits), `small-table`, `qa` (Appendix E); boxes no longer break across pages (labels
    were stranded at page bottoms). Typst swallows a `;` written right after `#n(...)`, so
    chapters write `\;` there.
  - Cross-references use heading labels (`@ch-did` prints "Chapter 5"), because chapter
    numbers in the text would fail the lint.
  - `tests/test_writeup.py`: the synthetic-build fixture cuts every chapter to its title (the
    written chapters name real cards the synthetic outputs don't have); new tests check that
    every figure the chapters use is one `figures.py` draws and that every key the chapters
    use is in the real numbers.json (skipped where it is missing or a sample).
  - Interpretation stated in the guide, for review: the second patch's tweaks moved choices
    much less than the first's ("indistinguishable, as a group, from no change"), not "none";
    the patch difference depends on the ruler and on Regent's cards and the Debilitate and
    Reflect calls; the first patch's slope is trimmed, not explained away, by other
    characters' controls; tooltips can be at most part of the explanation.
  - Toward-the-change counts follow the export's rule (Reflect has no direction), while the
    dose line follows the 2026-10-09 mixed-tweak rule (Reflect on as a nerf); chapter 9 says
    so. The forest figure colours Leading Strike as a nerf by its main field; its caption says
    so.
- Field guide v2 rework (Phil, 2026-10-22): typeset math throughout, code listings from the
  source, the reading notes ported in, COMMON MIX-UP / THE MATH, IN FULL / IN CODE boxes, no
  page target (supersedes "about 46 pages"). Four phases, one PR each: infrastructure and
  chapter 6 (Phil reviews before the rest), chapters 0–5, chapters 7–10, chapters 11–14 and the
  appendices. `writeup/REWORK.md` is the tracker every rework session reads first.
- Field guide rework, phase 1 (CC's choices, open to review, 2026-10-22):
  - Digit lint in math and code: inside `$...$` (display equations over several lines
    included) and inline code, single-digit integers are structure; a decimal or a
    multi-digit integer is an error unless `ALLOW` names it. The error gives the line of the
    offending token. `ALLOW` entries added: 1.96 and 1.4826 as constants of the normal
    distribution (not keys: they are not measured), and the estimator names HC1, CR1 and
    CRV1.
  - Listings: chapters name a listing (`#listing("name", [caption])`, or `#incode(...)` with a
    walk-through); the build extracts it with `ast` into `writeup/listings/<name>.py`
    (git-ignored) with an index of source file, functions and line numbers, which reaches
    Typst as `sys.inputs.listings` (so a compile outside the build fails on a listing, where
    figures print placeholders). A name is `<module>.<function>` under `spirometry`, or a
    `writeup.LISTINGS` entry for several functions in one listing or an excerpt (start and end
    patterns on the code; `# ...` marks the cut and has no line number). A name or pattern
    that no longer resolves, or a listing over 60 lines, stops the build. The gutter shows the
    source file's own line numbers. Listings of 45 lines or fewer never break across pages.
  - Equations: every display equation is numbered by chapter, (6.3), and by letter in the
    appendices. References go through a show rule, so a reference from another chapter gets
    the equation's own chapter (a numbering function alone took the referencing chapter's).
  - Box labels stick to the box's next block, so a label is never alone at a page's foot.
    Figure widths by name (`small`, `medium`), so chapter files carry no digits.
  - `spirometry.teaching_sims`: one function per toy, the notes' code with its seeds (the
    regression toy's second part has its own seed, 161, instead of continuing the first
    part's generator). Numbers go out as one long table (`teaching_sims.csv`: toy, quantity,
    value, kind, decimals) that `spirometry.numbers` formats; the figures read
    `toy_<toy>_<part>.csv`. Worked examples that are arithmetic, not simulation (one offer's
    SD, the SE of a difference, a log-odds push, false alarms), are titled "Worked example,
    not your data". The synthetic build runs the real toys with `--quick`.
  - `phil_runs.sh` gets a `toys` step before `numbers`, which now needs `teaching_sims.csv`.
  - New key family `did.hand_vs_model.*` (median and largest |model − hand 2×2| in SEs over the
    43 tweaks, all weeks): a summary of two existing columns, like the SE ratios, so chapter 6
    can say the model and the hand calculation agree for every tweak (median 0.10 SE, at most
    0.42), not only Parry. Flagged for Phil: it is a new statement about real data.
  - Chapter 6's model uses named subscripts (card, upg, grp, blk, act, asc), the columns of
    `fit_did`'s formula, so they don't clash with the 2×2 regression's a, b, c, d; the
    formula's `card_id^group` term is φ, beside the brief's α, γ, δ, η and β.
  - Corrections item 6 applied wherever the term appeared: "short, smaller before block" for
    v0.103.3 (here, chapter 7's answer, chapter 14's open list, SPIROMETRY.md), not "thin",
    the term for builds under 2,000 primary runs.
- Field guide rework, phase 2 (CC's choices, open to review, 2026-10-22):
  - Potential-outcomes notation set up in chapter 2 for the whole guide ($D_i$, $Y_i(1)$,
    $Y_i(0)$, $τ_i$, $τ_ATE$, $τ_ATT$, $E[·]$), with the naive comparison written as $τ_ATT$ plus
    selection bias. Chapter 5 writes each simpler comparison as the effect plus a named term
    (baseline gap, time change) and the DiD as the effect plus the difference in untreated
    trends; parallel trends is the statement that this term is zero.
  - One meaning per letter (Appendix B's notation table says so): chapter 6's interaction
    coefficient θ → λ and its number of columns k → K (k is picks); chapter 1's build is $B$, the
    hashing key "salt", the hash function "hash"; spillover ψ, a week $u$, the Wilson half-width
    "hw", bias written out. Chapter 1 now defines $y_i$ and chapter 5 the 2×2 cell notation and
    the DiD; chapter 6 refers back to them.
  - Corrections item 1's replacement goes in chapter 2's WATCH OUT (the box that held "Error
    bars measure luck only"); chapter 4 gets §6 as a section (precision, accuracy, MSE, a fixed
    bias growing in SEs). Item 6 is a chapter 1 mix-up (v0.103.3 is short and smaller, about half
    the offers of v0.103.2; not thin). Item 3 is named in chapter 5 as not checked (red label),
    with the type-level placebo pointed to chapter 14 for phase 4.
  - Listings can name a module-level constant (`NAME = ...`, with the comment block above it),
    so chapter 1 shows the primary-population filter and the deduplicating views as the SQL
    strings `runs.py` actually runs. New `LISTINGS` entries: `numbers.build_start` (an excerpt),
    `numbers.table_add`, `runs.keys`, `runs.primary_filter`, `runs.dedup_views`,
    `teaching_sims.intervals`, `teaching_sims.spillover_all`.
  - Digit lint: `ALLOW` gains the hash function's name (SHA-256, HMAC-SHA256,
    `hashlib.sha256`, any case).
  - Two toy figures redrawn for legibility: the Bernoulli SD curve's label at a half sat on the
    curve; the fixed-bias legend covered the first histogram (now below the panels).
  - No new keys. Statements in chapters 1–5 that summarise or read existing real-data keys are
    listed under "For Phil to check" in `writeup/REWORK.md`.
- Website cards (Phil, 2026-10-27; notebook 06). Headline horizon weeks 0–3. Kept: Parry,
  Debilitate (first patch), Leading Strike labelled a rework (11 → 11 total damage). Corrosive
  Wave dropped (pre-trend screen p = 0.008) for the cleanest first-patch nerf by a rule fixed
  before running it (first-patch, solo-estimable, nerf, |β_h3| > 2 se, pre-trend p > 0.05, no
  offer-rate flag, no sign flip in a weeks 0–3 check; largest |β_h3|): Untouchable v0.103.2.
  Contrast card: the first rule (second-patch, |β_h3| < 2 se, no flag; most treated offers)
  picked Crescent Spear, dropped (clear at all weeks, +2.3 se with the pooled before block,
  anticipation gap). The stricter rule (also |β| < 2 se at all weeks and with the pooled
  before block, no informative anticipation gap > 2 se) picked Juggernaut v0.107.1. For
  consistency with the nerf rule, pre-trend p > 0.05 and no weeks 0–3 check moving it > 2 se
  were then added. Juggernaut (p = 0.011, tagged −5.3 se), Hyperbeam (p = 0.014) and
  Untouchable v0.107.1 (p = 0.005) drop out. Pick: The Scythe v0.107.1, damage scaling 3 → 4,
  −1.38 pts at weeks 0–3, +0.40 at all weeks. Parry figure: percentage points, not %, since
  the rate itself is a percentage; the caption has no CI because the placebo check says the
  intervals are too narrow. "Second patch weaker" is the median |β| comparison at weeks 0–3 (4.40 vs. 1.95 pts).
  Parry's change is Block (6(9) → 10(14) when you play Sovereign Blade), not Vigor.
- Calibrated site numbers (Phil, 2026-11-05): the weeks 0–3 band is the 95% interval widened
  by the patch's weeks 0–3 placebo factor (`site_figures.PLACEBO_FACTORS_H3`: 4.10, 2.67),
  around the rounded beta as `index.html`'s `calCI` does; the weekly bars stay clustered and
  say so. `spirometry_cards.json` keeps raw headline CIs because the site widens them at draw
  time, and `n_clear` is the calibrated count. The factors are in two places on purpose (two
  repos); `index.html`'s `CAL` must match. The `sentence` field is gone: nothing read it.
- First-patch forest plot (Phil, 2026-11-05): replaces Parry as the site's static figure, 25
  cards (Serpent Form out). Intervals are ±2 placebo-scaled SEs (`site_figures.CAL_Z`), not
  ±1.96, so the count clear of zero is the calibrated rule's: 13 of 25. At ±1.96 it was 14,
  because Debilitate's calibrated z is 1.961. Uses the rounded 4.10; the unrounded factor was
  not chased. Leading Strike is a buff, per the patch notes.
- Repository move (Phil, 2026-11-06): history rewritten with `git filter-repo` and pushed to a
  new `pmacias/spirometry`, the old repository archived privately (Next up 20). The release
  step, future work since 2026-10-16, is done for the repository: the Spire Codex maintainer
  approved publishing `reference/raw/` (`reference/raw/README.md`). Commit citations use the
  new hashes. Docs don't link the archive.
- Dashboard test (CC, 2026-11-06): Streamlit's script runner replaces `sys.modules["__main__"]`
  with `dashboard/app.py` and doesn't restore it, so a spawned worker in any later test re-ran
  the app and failed on `import charts`. `tests/test_dashboard.py` restores it. The test only
  runs without `results/`, so the failure needs a clone without that folder; an editable
  install doesn't change it (reproduced with one present).
- Release contents (Phil, 2026-11-06): `results/` and `writeup/numbers.json` / `numbers.csv` are
  committed. The field guide PDF is not, replacing the 2026-10-09 plan to commit it at release:
  it goes out as a GitHub Release asset after the chapter 7-14 review.
- Calibrated columns (CC's choices, open to review, 2026-11-06): `results/pick_rate_did.csv`
  gets both horizons, because all weeks has a placebo factor too (`calibrated_counts.csv`: 4.52,
  2.07; 13 of 26, 4 of 17). `PLACEBO_FACTORS_H3` and `CAL_Z` move from `site_figures` to
  `export`, with the new `PLACEBO_FACTORS_ALL`: `site_figures` needs pyfixest, which the export
  doesn't, and it imports them back, so `scripts/site_publish.sh` is unchanged. The factors are
  the rounded ones the site uses; the test checks them against `numbers.json`.
- Spillover diagnostics (triage M, exploratory; CC's choices, open to review, 2026-11-06): no
  factor, number or headline changes. Signed dose is direction × log_ratio, because `direction`
  is +1 on every row of `tweak_sizes.csv`, so direction × |log_ratio| would be unsigned. The
  "clean" Defect window has no numeric tweak but three substantive changes (Hotfix, Voltaic,
  Rocket Punch) and three wording changes; all six stay out of the fits. A robust sd between 2
  and the factor counts as unresolved, which is where the declared 2.73 [0.81, 4.14] landed.
  Outputs go to `triage/out_final/` since they use the final tables.
- Drift diagnostics (triage N, exploratory; CC's choices, open to review, 2026-11-06): no factor,
  number or headline changes. Builds v0.99.1, v0.103.2, v0.107.1, chosen from a listing before any
  drift number; v0.103.3 has 2 full weeks. Rarity is derived from offer tiers (95 of 97 on file
  match), since `reference/raw/` stays closed; card type is not computed in the sandbox. Test 4's
  declared rule, using a corrected SE, turned out to reward noise, so a noise-only benchmark was
  added post hoc and the reading rests on it. Detrending is not a calibration option.
- Forensics on the largest placebo misses (triage O, exploratory; CC's choices, open to review,
  2026-11-10): no factor, number or headline changes. The top-10% rule (> 50% tail-driven, < 25%
  broad) is reported as given, next to a normal benchmark, because a plain normal already gives
  0.46–0.51 and "< 25%" can't happen; the reading rests on the drop table. "Untagged" is run both
  ways: no uploader token, and no SlayTheStats tag. The top 25 are ranked over both patches
  together. A driver is split into precision only and of β, and that split still passed two weak
  cases. XGBoost settings were fixed in advance and not tuned; they overfit, so the R² rule was a
  harsh test. xgboost is a new optional extra (`forensics`), used by that script only. Card type
  is not in the model in the sandbox. The refit tolerance is 1e-04, since derived colors drop two
  two-offer control cards from one window.
- Archetype spillover (triage P, exploratory; CC's choices, open to review, 2026-11-10): no
  factor, number or headline changes. Archetypes are keyword rules on card text, one list for all
  characters plus character keywords, a card in every archetype it matches, an archetype needing
  3 reward-pool members. Text comes from `reference/raw/cards.json` (v0.107.1), rolled back with
  `card_changes.csv` and old wordings quoted in the patch notes; the sandbox keeps that folder
  closed, so Phil copied the file for the session and the script takes `P_CARDS`. A card's
  direction is the patch notes' verb (all Buffed, all Nerfed, else unclear); a card whose text
  enters an archetype counts as a buff to it and one that leaves as a nerf; an archetype's net
  is the majority. The deciding p is two-sided, from shuffling labels within character-window.
  That shuffle treats cards as independent, which the result itself contradicts, so an
  archetype-level table was added post hoc and the reading rests on both. Two archetypes'
  direction was known from section O before the rules were written; the test is also reported
  without O's pairs.
- Release nudge (triage Q, exploratory; CC's choices, open to review, 2026-11-11): no factor,
  number or headline changes. Phil's rules as given; mine where the prompt left a choice. At a
  boundary the before block is the older build's last 21 days (play after the release left out)
  and the after block the newer build's weeks 0–2. "Last day with play" is read as the last
  day the build was the current stable, which gives 11 interior cuts, 10 of them in v0.107.1.
  The second anchor is read as v0.103.3 → v0.107.1, the real window, where the prompt says
  v0.103.2 → v0.107.1. Each character's cards are sampled in one fixed order, so cards recur
  across cuts. Rarity for the offer-rate z is derived (file where present, else offer tier),
  since `reference/raw/` stays closed. The run-clustered bootstrap runs on every offer row,
  not 100, because it is cheap. Added by me and declared before running: excess variance and
  τ in pp beside z, a benchmark for what interior cuts would show with the boundaries' τ, and
  the correlation of a card's β across consecutive boundaries. Post hoc: the offer-rate tail.
  The sweep's summary step crashed once after the fits were saved and was rerun from them.
  SPIROMETRY.md's open question 8 was first left alone (the prompt asked for proposed text
  only) and then updated with Phil's wording, plus two things merged from the section's own
  proposed line: the rule's "mixed" label with the excess variances (1.2 against 5.0 pp²),
  and the offer-rate robust sds (1.16 / 0.93). Phil added that the two boundaries with card
  changes are also the two major updates (triage R is to test this).
- Dose and same players (triage R, exploratory; CC's choices, open to review, 2026-11-11): no
  factor, number or headline changes. Phil's rules as given; mine where the prompt left a
  choice. Hotfix merges by the 3-day rule: v0.99.0, v0.105.1, v0.106.1, v0.110.1 on beta and
  v0.98.2 on stable. "Consecutive" boundaries are literal, so no boundary skips a build that
  fails the run rule; the rule (3,000 runs) is applied to each side's capped 3-week block.
  Blocks are each build's first 3 weeks, so R's stable rows are not Q's (Q used the older
  build's last 3 weeks). Dose counts a character's own cards with a differing event that is
  not wording-only; unknown versions, text-only and behavior changes are counted apart. In
  part 2 a token is in the subset with one offer of the character's cards in each block, and
  the ratio τ(ii)/τ(i) decides by its point value; pairs with ≥ 51 subset offers are reported
  beside all pairs, which turned out to be needed (one 25-offer pair breaks the all-pairs τ).
  Declared by me before running: the within-boundary and total-dose correlations and the gap
  check. Added after the rules: Phil's within-boundary contrast (descriptive) and a post hoc
  per-boundary τ table. Fits are saved per unit or window and reruns resume from them.
  SPIROMETRY.md's open question 8 was then updated at Phil's direction: R's proposed line
  applied; Q's passage revised, since the v0.103.3 boundary's 1.2 pp was measured late in
  v0.103.2 and R gets 2.69 pp from its first three weeks, so "releases that change cards" is
  dropped; the "(triage R tests this)" clause replaced by what R found; Q's leading reading
  (re-evaluation when a character's cards change) replaced by R's; and Phil's inferred
  random-walk sentence added.
- Additive calibration (triage S, a declared sensitivity check; CC's choices, open to review,
  2026-11-11): no factor, number or headline changes; SPIROMETRY.md not edited (proposed text
  only). Phil's rules as given; mine where the prompt left a choice. The pass rule is applied
  per patch and the model passes only if both do. τ is refit without the pair's character
  (three other characters in the first patch, four in the second). Bins are by rank of offers
  within the patch. Declared before running, because the band [0.8, 1.25] is strict for bins
  of about 40 pairs: a benchmark simulating the additive model as exactly true (it passes all
  six bins about one time in five). Rarity of a pseudo card is R's; of a tweak card, the one
  in `offer_rate.parquet`. Tweak offers are the weeks 0–3 fit's (`did_h3.parquet`), not the
  all-weeks column in `pick_rate_did.csv`. The empirical rule (e) pools both kinds of fit and
  uses k / n. For the dose-response, "the existing calibrated version" is `se_inflation.csv`'s
  weeks 0–3 rows, which use the all-weeks factors (4.52, 2.07); the weeks 0–3 factors are
  added beside them, and the additive error is built in pp and converted to log-odds per
  tweak, with τ on the log-odds scale as a secondary. Outcome: the additive model fails in
  both patches (too wide for the most-offered cards, all Commons), so no sensitivity row is
  proposed for the guide or README; a one-sentence caveat on the headline count is offered
  for Phil to decide. Added after the rules: Q and df in the dose table.
- Count range stated beside the headline (Phil, 2026-11-11, after reading triage S): README
  finding 1 and SPIROMETRY.md ("Placebo calibration of the DiD errors") now say the
  first-patch count is between about 8 (additive) and 13 (multiplicative, the declared
  headline) and the second-patch count between 0 and 2, the difference coming from heavily
  offered Commons. The headline, factors, numbers module, guide and `results/` are unchanged.
