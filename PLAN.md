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
09aa195): every file in `data/analysis/`, `results/` and `triage/out/` comes from that build.
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
1. **Offer-rate check** (design validity): a patch shouldn't move how often a card is offered.
   If it does, something else changed (card pool, rarity) and that card's comparison is suspect.
2. **Pick-rate DiD for numeric tweaks** — the minimum result.
3. **Dose-response on pick rate:** effect against change size.
4. **Win effects within a build:** intent-to-treat (offered → win), then IV (effect of
   picking, with the offer as instrument).
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
guide on the 1,393-page tables). Publishing undecided. Built from `writeup/` (Typst) by
`python -m spirometry.writeup build`; every number comes from the generated
`writeup/numbers.json` (`python -m spirometry.numbers`), and every figure from
`scripts/writeup/figures.py`, so a rebuild never leaves stale numbers. The build runs a privacy
check either way. README results section: drafted on the 1,513-page numbers, marked
provisional.
*Status: planned (tasks in Next up 15).*

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
   bulk dump, stable-only hotfixes, when `player_token` was added).
5. ~~Final rebuild on the complete snapshot~~ (done 2026-10-09: 2,071 pages, 0 failed;
   Phase 3) ~~and copy `data/analysis/` to `data/analysis_p1873/`~~ (done 2026-10-09)
   ~~and rerun notebooks 01–05, the placebo calibration, the export and the sensitivity
   tables on the final tables~~ (done 2026-10-10, item 15 task 8; numbers in SPIROMETRY.md,
   nothing moved by more than one SE from the 1,873-page fits). Left: task 7's scripts, once
   built. The audit notebook still reads the interim `data/audit/` tables (rebuilt on all
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
   thin second-patch before block is the first candidate). *On the placebo scale they are
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
12. Release checklist (only if something is published): send the maintainer message (item 4);
   clear notebook 02's output cells that show top-uploader run counts (the hashed IDs are
   gone since task 6);
   review the licenses and attribution of `reference/raw/` (wiki pages CC BY-SA, Spire Codex
   caches); aggregates only.
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
   7. Scripts for the run-level pieces: fake patch, control scope at weeks 0–3, token subset
      and stayers, slope by week, the pre-declared aggregates, per-group dose lines; each
      states its spec and prediction before it runs (CC).
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
   9. Win effects: power check on a few cards of one build with a stop rule; continue to all
      cards of v0.107.1 only if it passes (CC script; Phil runs and decides).
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
   11. Write-up skeleton: Typst, boxes, chapter stubs, generated numbers appendix, lint for
      hand-typed numbers, one build command (CC).
   12. Chapters 0–3 draft, for a voice check before the rest (CC drafts; Phil reads).
   13. Figure script for every figure (CC; Phil runs it and looks).
   14. Remaining chapters in four PRs; Phil writes the "what was found" passages and the
      conclusion (CC drafts).
   15. Docs: final numbers into SPIROMETRY.md, README and PLAN (CC). *Pick-rate,
      anticipation, placebo and audit numbers updated 2026-10-10 from the final rerun; redo
      for anything the later tasks add.*
      Tests: 210 passed, 5 skipped (smoke tests need real data), run locally 2026-10-14. 
      The cloud sandbox can’t read reference/raw/, so the parser, patch-history and treatment 
      tests only run locally.
   16. Only if Phil decides to publish: release checklist (item 12), then publish (Phil).

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
  - Thin before blocks (the second patch's v0.103.3): no special handling; `n_runs_*`,
    `n_offered_*` and `n_picked_*` per block are in the summary, and the se's carry the
    thinness. No pooling with v0.103.2 (Phase 5 first-pass decision: v0.103.3 alone).
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
