# Field guide v2: learning map

"What Did the Patch Do?" (Spirometry), Phil's study guide and the project's final deliverable
(PLAN.md decision log, 2026-10-09). This file is the map: what each chapter teaches, in what
order, from which saved outputs. It is for review before any chapter is written. No chapter text
here.

**Sources read for this map:**
- PLAN.md: decision log and item 15.
- SPIROMETRY.md: Phase 5 results, placebo calibration, audit decisions, known issues, open
  questions.
- triage/TRIAGE.md, its section list and final synthesis.
- The markdown and section structure of notebooks 01–05 and the IV primer.
- The module docstrings for export, numbers and sensitivity.
- writeup/numbers.csv (123 keys, final rerun).
- The column layouts of results/*.csv, data/analysis/writeup/*.csv, the placebo diagnostics
  and the saved fits.
- The v1 PDF, for structure and voice only. No number below comes from it.

**Headings carry no digits.** The lint applies to headings too, so a count in a title would
have to come through `#n`. The stubs word around it.

**How to read the number lists.** "Exists" = a key in writeup/numbers.json now. "Missing" = a
number the chapter needs that has no key yet, with what would supply it:
- **saved**: a final-rerun file already holds it. The chapter's task adds a key to
  `spirometry.numbers`; nothing is computed beyond selecting or summarising rows.
- **audit**: notebook 01 prints it from the final `data/audit/` tables but saves no file.
  Notebook 01 (Phil's) or a small script over `data/audit/` has to save an aggregate table
  first.
- **build_info**: a count in `runs.duckdb`'s `build_info`. The export (which already reads
  `build_info` with `--db`) would copy it into `results/meta.json`.
- **task 7 / task 9 / placebo h3**: waits on that task: the run-level scripts, the win-effect
  power check, and the weeks 0–3 placebo run (`did.placebo_all`, `max_week_after=3`).
- **new computation**: not in any saved output.

**Figures** are code in `scripts/writeup/figures.py` (task 13), run by Phil. None are produced
yet. Each figure names its input file. The build prints a labelled placeholder until the file
exists.

**Every section has the same parts, in v1's order:**
1. "A picture to hold on to": the analogy.
2. The term.
3. "In your project": the real number.
4. "In plain words" / "Watch out" where they help.
5. A "Skill" line naming the general data-science skill.
6. "Stop and check": 3–5 questions; the answers go to Appendix A.

A term's one-line meaning is repeated when it returns after a gap. Passages marked
**(Phil writes)** are "what was found" text and the conclusion (decision log 2026-10-09). CC drafts
the teaching and method text around them.

**Readiness** (summary at the end):
- **Ready**: every number it prints is in a saved final-rerun output (keys may still need
  adding).
- **Partly ready**: some numbers wait on something listed.
- **Waits**: the chapter's core depends on a pending task.

---

## Front matter

- Title page:
  - "Spirometry" above the title "What Did the Patch Do?" (decision log).
  - Build stamp from numbers.json: `build.tables_built_at`, `snapshot.pages`,
    `build.parser_version`.
  - A SAMPLE banner when numbers.json comes from synthetic outputs.
- Contents.
- Box "How the numbers in this guide are marked": "your data" = the final rerun; "simulation" =
  the IV primer's game, where the truth is known; "unverified" and "pending" are labelled where
  they appear. Every number is generated, none typed by hand.

---

## Chapter 0. The project on one page (`00_project`)

- **Question:** What does this project try to answer about each balance patch, and with
  which tools?
- **Sections:**
  - Two questions about every patch
  - What a patch changes
  - How this guide is built
- **New terms:** balance patch; card change; numeric tweak; rework; run.
- **Named without definition** (pointers to later chapters; the one place the build-up rule
  is broken on purpose): difference-in-differences (ch 5), instrument (ch 13),
  dose-response (ch 10).
- **Analogies:** a patch as a recipe change in a restaurant chain: the same dish with more
  salt, served to thousands of diners whose plates come back to the kitchen.
- **Numbers.**
  - Exists: `snapshot.pages`, `snapshot.records`, `snapshot.start_date`,
    `snapshot.end_date`, `tweaks.solo_estimable`, `tweaks.first`, `tweaks.second`.
  - Missing:
    - Numeric tweaks in total (50) and how many are reworks: saved
      (`reference/tweak_sizes.csv`, `reference/card_changes.csv`; numbers.py would read
      `reference/` too).
    - Distinct runs: **pending**. Two sources disagree (1,525,369 `--count-only`, 1,525,329
      audit). Left out and labelled.
- **Figures:** `fig_timeline`: builds on a calendar, stable and beta, with the two stable
  patches and their windows marked. Input: `reference/builds.csv`, `results/pick_rate_did.csv`
  (window labels).
- **Decision log explained:**
  - Spire Codex as the primary source.
  - Card changes classified from structured fields.
  - Only changelogs 1.1.0 and 1.2.0 count as releases.
  - The unit is the card offer.
  - Pick-rate DiD first.
  - Win effects: a power check first, the rest future work (2026-10-09).
- **Must label:** distinct runs pending. The second patch's flat response is named as the
  puzzle; its cause is open.
- **Waits on:** nothing. **Skill:** turning a vague question into ones data can answer.
- **Readiness:** ready (once the reference key is added).

## Chapter 1. The data: run files, offers, and which runs count (`01_data`)

- **Question:** What is in a run file, and which runs does the analysis use?
- **Sections:**
  - What a run file records
  - Builds, branches and patch windows
  - The snapshot and the backfill
  - Duplicates and retries
  - The primary population
  - Thin builds
- **New terms:** run file (record); reward screen; offer; build; stable and beta branch;
  patch window, before block, after block; snapshot; backfill (upload lag); duplicate record
  and run key; retried run; sample and population; primary population; thin build; uploader
  group (tagged / untagged, the SlayTheStats `_sts` stamp).
- **Analogies:**
  - A run file is a flight recorder for one game. An offer is a hand of cards dealt, kept or
    passed.
  - Stable and beta are the main road and the test track.
  - Backfill is holiday photos uploaded months later, so the album for a date keeps growing.
  - A duplicate is a guest who signed the guest book twice. A retried run is a level replayed
    from a save.
  - The primary population is the guest list for the study.
  - A thin build is a shop open for a day.
  - Uploader groups are two tills reporting sales from the same shop.
- **Numbers.**
  - Exists: `snapshot.*`, `build.parser_version`.
  - Missing:
    - Primary runs (1,122,054, 73.6% of distinct runs) and runs not abandoned: audit (the
      share also needs distinct runs, pending).
    - Upload lag: median days, and shares later than 7, 30 and 90 days, overall and by
      uploader group: audit.
    - Thin builds and their primary runs: audit.
    - Exact repeats dropped (75,996): build_info.
    - Solo run keys with more than one record (175 of 1,204,275): build_info.
    - `primary_offers_dedup_removed`: build_info.
    - Retried primary keys: build_info.
    - Offers per stable build: new computation (notebook 02 section 2 prints it; no file),
      or audit's offer counts.
- **Figures:**
  - `fig_runs_per_build`: primary runs per build, by branch.
  - `fig_upload_lag`: share of runs uploaded later than d days, tagged against untagged.
  - Input for both: an aggregate saved from `data/audit/` (audit). Not drawn from run-level
    files.
- **Decision log explained:**
  - Solo runs only for the primary analysis.
  - Card-reward offers only (shops secondary).
  - Modded and custom runs dropped (and the mod-marker rules).
  - Non-Neow starts dropped.
  - Non-release and before-release runs dropped.
  - Abandoned runs kept for pick rates.
  - Exact repeats dropped.
  - `run_key` deduplication (parser 1.5.0 and 1.6.0).
  - Retried runs dropped from win analyses.
  - Branch taken from `builds.csv`, never from the run file.
  - The thin-build pooling rule; v0.99.0 left out.
  - Cheat candidates flagged, not filtered.
- **Must label:**
  - Distinct runs pending.
  - v0.110.0 pooling: the patch notes are not checked (beta designs only).
  - The "two impossible wins" not rechecked.
  - The snapshot under-counts the last weeks' tagged runs (backfill).
- **Waits on:** audit aggregates and build_info fields (no new analysis).
- **Skill:** auditing a dataset before analysing it; defining the population.
- **Readiness:** partly ready (prose and structure yes; most numbers need audit or
  build_info keys).

## Chapter 2. Why "just compare" doesn't work (`02_confounding`)

- **Question:** Why can't we compare runs that took a card with runs that didn't?
- **Sections:**
  - A picture to hold on to
  - The words
  - The uploader groups as a live example
  - Why more data doesn't fix it
- **New terms:** outcome; treatment; confounder; selection; causal effect; counterfactual.
- **Reused:** run, offer, uploader group (ch 1).
- **Analogies:** vitamins and health-conscious people (v1); the counterfactual as the road
  not taken.
- **Numbers.**
  - Exists: none needed beyond reuse.
  - Missing:
    - Uploader groups' card rankings, per build: sd of per-card z, Spearman, typical gap in
      points (v0.103.2 and v0.107.1): audit.
    - The IV primer's naive estimate against the truth (confounding shown where the truth
      is known): saved (`data/analysis/writeup/iv_sim_single.csv`).
    - The tagged-versus-untagged win rate (v1 used it): **not rechecked on the final
      tables** (SPIROMETRY.md: 1,513 pages, not printed). Leave it out, or recompute it as
      audit.
- **Figures:** `fig_confounding_dag`: skill points to picking and to winning; picking points to
  winning. No data input (drawn).
- **Decision log explained:**
  - Uploader groups differ before the tooltips existed, so they are treated as selection;
    estimates are stratified or adjusted.
  - Win rates drift within a build, so win analyses control for week.
- **Must label:** the tagged win gap is unverified on the final tables if it is used.
- **Waits on:** audit aggregates for the uploader-group example.
- **Skill:** asking "compared with what?" and spotting confounding.
- **Readiness:** partly ready (ready if the example uses the primer's saved numbers).

## Chapter 3. Counting: rates, averages and percentage points (`03_counting`)

- **Question:** What does a pick rate measure, and how do we state a change in it?
- **Sections:**
  - Pick rate is an average of ones and zeros
  - Percentage points against percent
  - Average, middle and spread
- **New terms:** pick rate; conditional probability P(picked | offered); percentage point
  against percent; mean and median; variance and standard deviation; p(1 − p).
- **Reused:** offer, sample and population (ch 1).
- **Analogies:** a basketball free-throw percentage; an interest rate going from 2% to 3% (one
  point, fifty percent).
- **Numbers.**
  - Exists: `did.all.first.median_abs_beta_pp` and its partners (as a median example).
  - Missing:
    - Parry's and Corrosive Wave's pick rates before and after, and their controls'
      rates: saved (`results/pick_rate_did.csv`: `treated_rate_before/after`,
      `control_rate_before/after`).
    - The relative change: derived from the same row (division).
- **Figures:** `fig_before_after`: Parry and Corrosive Wave, before and after, with their
  controls. Input: `results/pick_rate_did.csv`.
- **Decision log explained:** the unit is the card offer; effects are reported in percentage
  points.
- **Waits on:** nothing.
- **Skill:** choosing the unit and stating a change without ambiguity.
- **Readiness:** ready.

## Chapter 4. Noise: standard errors, intervals, and "clearly nonzero" (`04_noise`)

- **Question:** How much could a number move by luck alone, and when is an estimate clearly
  different from zero?
- **Sections:**
  - The soup and the coin
  - Confidence intervals and "clearly nonzero"
  - Two things a standard error does not cover
- **New terms:** standard error; the square-root rule; 95% confidence interval; z (estimate ÷
  SE); "clearly nonzero" (|z| > 2); bias; multiple comparisons.
- **Reused:** pick rate, variance (ch 3).
- **Analogies:** tasting soup with one spoonful; ten coin flips against ten thousand (v1);
  multiple comparisons as buying many lottery tickets.
- **Numbers.**
  - Exists: `did.all.{first,second}.uncalibrated.clearly_nonzero` (labelled uncalibrated;
    ch 8 adds the calibrated ones).
  - Missing:
    - Parry's β, SE and 95% interval: saved (`pick_rate_did.csv`: `beta`, `se`, `ci_lo`,
      `ci_hi`).
    - Sculpting Strike's β and SE (an estimate near the 2-SE edge): saved, same file.
    - Expected false alarms among 43 at 2 SE: derived (43 × 0.046), a new derived key.
- **Figures:** `fig_se_curve`: SE of a pick rate against number of offers (formula), with
  Parry's offers marked. Input: `results/pick_rate_did.csv` (`n_treated_offers`,
  `treated_rate_before`).
- **Decision log explained:** "clearly nonzero" is counted with clustered and with
  placebo-scaled errors, the calibrated count first (introduced here, delivered in ch 8).
- **Must label:** uncalibrated counts as uncalibrated.
- **Waits on:** nothing. **Skill:** quantifying uncertainty.
- **Readiness:** ready.

## Chapter 5. Difference-in-differences (`05_did`)

- **Question:** How do we separate what the patch did from everything else that changed at
  the same time?
- **Sections:**
  - Two plants on a windowsill
  - Parry by hand
  - Why not the simpler comparisons
  - The one assumption: parallel trends
  - Choosing the controls
- **New terms:** difference-in-differences (DiD); treated card; control cards; control
  exclusions; parallel trends; fixed horizon (weeks 0–3) against all weeks.
- **Reused:** before block, after block, patch window (ch 1); percentage points (ch 3); SE
  (ch 4).
- **Analogies:** two plants on one windowsill (v1); the controls as the plant that got no
  fertilizer.
- **Numbers.**
  - Missing:
    - Parry's treated and control rates in each block, the raw 2×2 DiD (arithmetic on
      them), and the regression β ± SE: saved (`pick_rate_did.csv`).
    - Parry's control-card count: saved (`data/analysis/did_main.parquet`,
      `n_control_cards`).
    - Parry at weeks 0–3: saved (`beta_h`, `se_h`).
- **Figures:**
  - `fig_parry_did`: Parry and its controls before and after, with the counterfactual
    dashed. Input: `results/pick_rate_did.csv`.
  - `fig_parry_weekly`: Parry's weekly gap. Input: `results/weekly.csv`.
- **Decision log explained:**
  - The windows: stable v0.99.1 → v0.103.2 and v0.103.3 → v0.107.1, with the card-patch
    level.
  - Control exclusions: same-colour cards changed in the window.
  - The second patch's before block is v0.103.3 alone.
  - Bug-fix flags are a sensitivity check, not exclusions.
  - Weeks 0–3 is the primary horizon (2026-10-09).
  - Week 0 stays at the `builds.csv` date; the one-day offset is the same in both patches.
- **Waits on:** nothing. **Skill:** choosing a comparison group.
- **Readiness:** ready.

## Chapter 6. Regression: comparing like with like (`06_regression`)

- **Question:** What does the model in notebook 02 add to the hand calculation, and how are
  its error bars built?
- **Sections:**
  - A line through points, or a difference of averages
  - Reading the model line
  - Why several kinds of standard error
  - Log-odds, briefly
- **New terms:** regression; coefficient (β); linear probability model; fixed effects;
  singleton; iid SE; robust (heteroskedasticity-robust) SE; clustered SE; log-odds; delta
  method.
- **Reused:** DiD, treated and control (ch 5); variance p(1 − p) (ch 3); uploader group
  (ch 1).
- **Analogies:**
  - Fixed effects: grading students within their own class (v1).
  - Clustering: ten people from one family against ten strangers (v1).
  - Log-odds: betting odds, where two points mean more for a long shot.
- **Numbers.**
  - Missing:
    - Clustered ÷ robust SE: median and range over the 43, and Parry's ratio: saved
      (`pick_rate_did.csv` `se`, `se_hc`).
    - Clustered ÷ iid: median and range: saved (`did_main.parquet` `se_iid`).
    - Singletons dropped: saved (`did_main.parquet` `n_singletons_dropped`).
    - Parry's β in log-odds: saved (`beta_lo`).
- **Figures:** `fig_se_ratio`: clustered ÷ robust SE per tweak, against the treated card's
  offers. Input: `results/pick_rate_did.csv`.
- **Decision log explained:**
  - Clustering is judged against robust SEs, not iid.
  - `se_hc` is HC1.
  - Uploader-group terms stay in the main model.
  - Rows with no ascension are dropped.
  - pyfixest drops and counts singletons.
  - pyfixest was chosen as the package.
- **Must label:** ascension as one level each or banded is open (PLAN item 14a).
- **Waits on:** nothing.
- **Skill:** reading a model specification; matching error bars to the data's structure.
- **Readiness:** ready.

## Chapter 7. Checking the design (`07_checks`)

- **Question:** How does the analysis try to break its own result?
- **Sections:**
  - The offer-rate check
  - Pre-trends and the event study
  - Upgrade-only tweaks: a built-in placebo
  - Anticipation: reacting to the beta
  - The robustness table
  - The second patch's before block
- **New terms:** offer-rate check; rarity; pre-trend; event study; placebo test; anticipation
  (first-beta date, lead time, informative tweak); robustness check (shift in SEs);
  sensitivity analysis.
- **Reused:** parallel trends, control cards (ch 5); fixed effects (ch 6); z (ch 4); beta
  branch (ch 1).
- **Analogies:**
  - The offer-rate check: checking that the dealer didn't change the deck.
  - The event study: a time-lapse of the gap.
  - The placebo: a sugar pill that should do nothing.
  - Anticipation: umbrella sales rising when the forecast is published, before the rain.
  - Robustness: weighing again on another scale.
- **Numbers.** Missing, all saved:
  - Offer-rate flags (all controls and same rarity), Patter's and Sculpting Strike's
    ratios and z: `results/flags.csv`, `data/analysis/offer_rate.parquet`.
  - Pre-trend slopes ± SE for the flagged cards: `results/flags.csv`.
  - Upgrade-only placebos (Serpent Form, Royalties, Untouchable v0.107.1) β ± SE:
    `results/flags.csv`.
  - Anticipation counts (informative by patch; clearly nonzero among them), lead days, and
    the median ratio to the main effect: `results/anticipation.csv`.
  - Robustness median shifts per check, both horizons, and the tagged / untagged
    correlation: derived summaries of `results/robustness.csv` with
    `results/pick_rate_did.csv`, as notebook 02 section 7 computes them.
  - The second patch's pooled-before shifts: `data/analysis/did_second_patch_checks.parquet`
    and `second_patch_checks_h3.parquet`.
- **Figures:**
  - `fig_offer_rate`: offer-share log ratio against the controls, per tweak. Input:
    `results/flags.csv`.
  - `fig_event_study`: weekly gaps for Parry and one pre-trend card. Input:
    `results/weekly.csv`.
  - `fig_robustness`: shift in SEs per check. Input: `results/robustness.csv`,
    `results/pick_rate_did.csv`.
  - `fig_anticipation`: post-beta gap against the main effect, informative tweaks. Input:
    `results/anticipation.csv`.
- **Decision log explained:**
  - Pre-trends judged by slope; χ² is a flag only.
  - The same-rarity comparison rules.
  - The anticipation rule (2,000 offers and 3 days a side; split by date, not build).
  - The heavy-uploader check.
  - Picked-screens-only as a robustness row.
  - Card × act fixed effects not planned (timing balance).
  - The pooled v0.103.2 variant stays a check.
- **Must label:**
  - Why Patter and Sculpting Strike are offered more (open).
  - The negative upgrade-only placebos (open; drift is the first candidate).
  - The weekly panel shapes at the first-beta date are not recorded (PLAN 14c).
  - "When in the run" is not rechecked on the final tables: not used.
- **Waits on:** nothing. **Skill:** stress-testing a result.
- **Readiness:** ready.

## Chapter 8. Are the error bars honest? The placebo calibration (`08_placebo`)

- **Question:** If the same method is run on cards that did not change, does it find "no
  effect" as often as its error bars promise?
- **Sections:**
  - A smoke alarm tested without fire
  - The placebo design
  - What came out
  - Calibrated "clearly nonzero"
  - What it does and doesn't explain
- **New terms:** pseudo-treated card; standard normal (what z should look like); sd of z;
  robust sd (MAD); window–card pair (deduplication); calibration factor; calibrated z;
  empirical p.
- **Reused:** placebo test (ch 7); z, "clearly nonzero" (ch 4); clustered SE (ch 6).
- **Analogies:** testing a smoke alarm with no fire; a bathroom scale checked with known
  weights (the factor says how far off it reads).
- **Numbers.**
  - Exists:
    - `placebo.fits.*` and `placebo.pairs.*` (sd z, robust sd z, share |z| > 2, n).
    - `did.all.{first,second}.calibrated.*` and `.calibrated_plain_sd.*` (factor,
      n_placebo, counts).
    - `did.all.*.uncalibrated.*`.
  - Missing:
    - What honest errors give (share |z| > 2 ≈ 0.046; median |z| 0.674): constants, not
      outputs. A small fixed-term allowlist entry or a constant key.
    - Empirical p < 0.05 counts by patch, and median |β| real against placebo: saved
      (`placebo_diagnostics_vs_real_by_patch.csv`).
    - Spread by pseudo-card pick rate and size: saved
      (`placebo_diagnostics_spread_by_feature.csv`).
    - min_offers: saved (`placebo_main.parquet` `min_offers`).
    - **Weeks 0–3 calibrated counts: placebo h3 (pending).**
- **Figures:**
  - `fig_placebo_z`: histogram of placebo z by patch against the standard normal. Input:
    `data/analysis/placebo_main.parquet` (one row per fit; pseudo card names only).
  - `fig_real_vs_placebo`: |β| of real tweaks against their own window's placebos. Input:
    `data/analysis/placebo_diagnostics_vs_real.csv`.
- **Decision log explained:**
  - The placebo design (pseudo card, min_offers, seeding).
  - The dedupe rule.
  - `placebo_vs_real` within the window.
  - The calibration rule (Phil, 2026-10-14).
  - "Clearly nonzero" calibrated first (2026-10-09).
- **Must label:**
  - "The clustered SEs are calibrated" is not met.
  - The cause of the large placebo spread is not verified (open question 8).
  - The weeks 0–3 calibrated counts are pending.
- **Waits on:** the weeks 0–3 placebo run, for the primary-horizon counts.
- **Skill:** checking your error bars are honest.
- **Readiness:** partly ready (all-weeks complete; weeks 0–3 pending).

## Chapter 9. What the patches did to picks: the tweaks one by one (`09_results`)

- **Question:** How did pick rates move for each changed card?
- **Sections:**
  - The counts
  - The forest plot
  - The largest movers
  - Against the change
  - What was found **(Phil writes)**
- **New terms:** forest plot; buff and nerf; toward the change; mixed-direction tweak;
  upgrade-only tweak.
- **Reused:** "clearly nonzero" calibrated and uncalibrated (ch 4, 8); fixed horizon (ch 5).
- **Analogies:** a forest plot as a row of thermometers, each with its own error.
- **Numbers.**
  - Exists:
    - The calibrated counts, all weeks, with `_toward` and `_with_direction`.
    - The uncalibrated counts, both horizons.
    - `did.*.median_abs_beta_pp`.
  - Missing:
    - The largest movers' β ± SE and rates (Corrosive Wave, Parry, Leading Strike,
      Untouchable v0.103.2, Fight Me, Pinpoint, Danse Macabre), and the against-the-change
      cards: saved (`pick_rate_did.csv`).
    - Serpent Form's and Royalties' upgraded-offer counts: saved (`n_treated_offers`).
    - **Weeks 0–3 calibrated counts: placebo h3 (pending)**. Weeks 0–3 is the primary
      horizon, so the lead count waits on it.
- **Figures:** `fig_forest`: every tweak's β with clustered and placebo-scaled 95% intervals,
  by patch. Input: `results/pick_rate_did.csv`,
  `data/analysis/writeup/calibrated_counts.csv` (factors).
- **Decision log explained:**
  - Weeks 0–3 primary.
  - Calibrated count first.
  - The toward-the-change rule (single-direction tweaks only).
  - The mixed-tweak rule (the labels).
  - Phil writes the findings.
- **Must label:** the weeks 0–3 calibrated counts pending; Patter's and Sculpting Strike's
  offer-rate caveat.
- **Waits on:** the weeks 0–3 placebo run (lead count); Phil's passage.
- **Skill:** summarising many estimates without overclaiming.
- **Readiness:** partly ready.

## Chapter 10. Dose-response: do bigger changes move picks more? (`10_dose`)

- **Question:** Is the effect on picks in proportion to the size of the number change?
- **Sections:**
  - The dose and the ruler
  - Meta-regression
  - One slope, then one per patch
  - Same size, same precision, different effect
  - What was found **(Phil writes)**
- **New terms:** dose; ruler, ln(new/old); meta-regression; weighting by precision;
  between-card scatter (τ); random effects; intercept; slope per patch; patch difference
  (z diff).
- **Reused:** log-odds and delta method (ch 6); SE, z (ch 4); calibrated SEs (ch 8).
- **Analogies:**
  - Dose: a medicine dose.
  - Meta-regression: combining thermometers weighted by how accurate each one is.
  - τ: patients responding differently to the same dose.
- **Numbers.**
  - Exists:
    - `dose.triage.*` (the notebooks' 38: one slope and per-patch slopes, both horizons).
    - `dose.primary.h3.*` (per-patch slopes, n, z diff).
    - `dose.primary.h3.placebo_*` (placebo-scaled).
  - Missing:
    - Intercept, τ, Q, and buff / nerf slopes: saved (`results/dose_response.csv`).
    - The worked example (+1 on a 7-damage card): ln(8/7), and the implied log-odds and
      points at a 20% pick rate. Derived from the one-slope key; a new derived key.
    - The same-size table (median |x|, median |β|, median SE per patch on the line):
      derived from `dose_points.csv` (primary spec).
- **Figures:** `fig_dose`: β (log-odds) against dose, by patch, with the per-patch fitted
  lines, primary spec. Input: `data/analysis/writeup/dose_points.csv`,
  `data/analysis/writeup/rulers.csv`.
- **Decision log explained:**
  - Primary ruler ln(new/old).
  - Weeks 0–3 primary, all weeks secondary.
  - Reworks and cost changes off the line.
  - The mixed-tweak rule (Reflect on at ln(15/17), Leading Strike off).
  - Debilitate v0.107.1 off the ln line (sign only), with the sensitivity row.
- **Must label:** the cause of the flat second patch is open; the notebooks' 38 and the
  primary spec differ in two tweaks, and the text says which spec each number is.
- **Waits on:** Phil's passage. **Skill:** modelling an effect against a continuous dose.
- **Readiness:** ready.

## Chapter 11. Is it the measuring stick? Rulers and doses (`11_rulers`)

- **Question:** Does the second patch look flat only because of how the size of a change was
  measured?
- **Sections:**
  - Many rulers and a post-hoc one
  - Mixed tweaks
  - Hard-to-measure doses: Debilitate and Reflect
  - Leave one out
  - The review calls
- **New terms:** sign, absolute, rank and per-kind rulers; post hoc; measurement error in the
  dose (attenuation); leave-one-out; influential point; review call.
- **Reused:** dose, ruler, meta-regression, z diff (ch 10); sensitivity analysis (ch 7).
- **Analogies:** measuring a room in metres, in footsteps or by ranking rooms by size;
  leave-one-out as checking whether the verdict changes when one juror leaves.
- **Numbers.** Missing, all saved:
  - Slopes and z diff per ruler and spec, with the post-hoc flag:
    `data/analysis/writeup/rulers.csv`.
  - The review-call variants: `review_calls.csv`.
  - The mixed-tweak variants: `mixed.csv`.
  - Leave-one-out (Debilitate v0.107.1's leverage): `leave_out.csv`.
  - Character terms: `character.csv`, `character_counts.csv`.
  - With Debilitate at its table dose: `rulers.csv`, spec "primary, Debilitate at table
    dose".
- **Figures:**
  - `fig_rulers`: z diff by ruler and spec. Input: `rulers.csv`.
  - `fig_leave_out`: slope 2 with each tweak left out. Input: `leave_out.csv`.
- **Decision log explained:**
  - ln(new/old) primary; other rulers, review calls and the hybrid are sensitivity (hybrid
    post hoc).
  - The mixed-tweak rule (2026-10-09).
  - Debilitate v0.107.1 sign only.
  - The Shiv value verified from the changelog sample.
- **Must label:**
  - Dose measurement error is open.
  - The Debilitate and Reflect calls are decisions, not measurements.
  - The hybrid ruler is post hoc.
- **Waits on:** nothing.
- **Skill:** checking whether a conclusion depends on how you measured.
- **Readiness:** ready.

## Chapter 12. Is it the design? Power, drift, controls and players (`12_explanations`)

- **Question:** Could low power, a drifting before block, the choice of controls, or a change
  in who plays explain the flat second patch?
- **Sections:**
  - Power by simulation
  - A fake patch
  - Regression to the mean
  - Spillover and the choice of controls
  - Who was playing
  - Pre-declared aggregates
  - What was found **(Phil writes)**
- **New terms:** statistical power; simulation; fake patch; regression to the mean; spillover
  (substitution); control scope; player token and stayers; pre-declared analysis.
- **Reused:** placebo (ch 7, 8); control cards (ch 5); uploader group (ch 1); slope per
  patch, τ (ch 10).
- **Analogies:**
  - Power: a metal detector's sensitivity.
  - Fake patch: a rehearsal where nothing changed on stage.
  - Regression to the mean: a best-ever exam followed by an ordinary one.
  - Spillover: a discount on one brand moves its rival's sales.
  - Pre-declared: writing the bet down before the race.
- **Numbers.**
  - Exists: `dose.primary.h3.placebo_*`.
  - Missing:
    - Power table (detection share for planted slopes): saved (`power.csv`).
    - Placebo spread against real spread: saved (`spread.csv`).
    - Fake patch v0.103.2 → v0.103.3: task 7.
    - Regression to the mean (pre-release movement): task 7, the "pre-declared
      aggregates" and "slope by week" scripts.
    - Control scope at weeks 0–3: task 7.
    - Token subset and stayers: task 7.
    - Per-group dose lines: task 7.
    - The release-week aggregates (ascension jump): task 7.
- **Figures:**
  - `fig_power`: detection share against planted slope. Input: `power.csv`.
  - `fig_fake_patch`: fake against real effect spread. Input: the task 7 output.
  - `fig_slope_by_week`: per-patch slope by after-week. Input: the task 7 output.
- **Decision log explained:**
  - Triage numbers are not results until rerun on the final tables.
  - Control scope default "color"; colorless cards are controls under no scope.
  - The second patch's before block stays v0.103.3.
  - The week 0 offset.
- **Must label:** every triage number not yet rerun; why the second patch did less is open.
- **Waits on:** **task 7** (most sections).
- **Skill:** ruling out alternative explanations.
- **Readiness:** waits.

## Chapter 13. From picks to wins: instruments (`13_wins`)

- **Question:** Does taking a card make a run more likely to win, and how can we tell when the
  players who take it differ?
- **Sections:**
  - The lottery for free gym passes
  - Why it works, in a simulation
  - Three assumptions
  - Why only the first reward screens
  - Who the estimate is about
  - When the instrument is weak or broken
  - The power check on real runs **(Phil writes the finding)**
- **New terms:** instrument; intent-to-treat (ITT); first stage; IV estimate (Wald, 2SLS);
  non-compliance and compliers; relevance, independence, exclusion; weak instrument (F < 10);
  first K screens; survival bias; balance check; complier shift.
- **Reused:** confounder, selection (ch 2); simulation (ch 12); SE, coverage (ch 4);
  retried run (ch 1).
- **Analogies:** the gym-pass lottery (v1).
- **Numbers.**
  - Missing:
    - The simulated game (naive, ITT, first stage, IV, truth): saved (`iv_sim_single.csv`).
    - The 300 draws (means, coverage): saved (`iv_sim_draws_summary.csv`).
    - The weak-instrument spread: saved (`iv_sim_weak.csv`).
    - The broken instruments: saved (`iv_sim_broken.csv`).
    - The heterogeneous case: saved (`iv_sim_het.csv`).
    - **The real power check: task 9.**
- **Figures:**
  - `fig_iv_three`: ITT, first stage, IV. Input: `iv_sim_single.csv`.
  - `fig_iv_draws`: naive against IV over 300 draws. Input: `iv_sim_draws.csv`.
  - `fig_iv_weak`: IV spread against F. Input: `iv_sim_weak.csv`.
  - `fig_power_check`: the real check. Input: the task 9 output.
- **Decision log explained:**
  - Treatment = took X on one of the first K screens.
  - Short runs dropped (K = 1 check).
  - Retried runs dropped.
  - HC1 errors, one row per run.
  - `screen_mix` off by default.
  - week × build fixed effects.
  - The power check with a stop rule.
  - The strength change (step 5) is future work.
- **Must label:**
  - `screen_mix` undecided.
  - The real-data balance check not yet run.
  - Real win effects pending task 9.
- **Waits on:** **task 9** (real part); the simulation part is ready.
- **Skill:** using randomness the system already has.
- **Readiness:** partly ready.

## Chapter 14. What is settled, what is open, what could come next (`14_open`)

- **Question:** What does the project conclude, and what is still unknown?
- **Sections:**
  - Conclusion **(Phil writes)**
  - Still open
  - Future work
- **New terms:** partial pooling (hierarchical Bayes); staggered rollout; perception against
  strength.
- **Reused:** most earlier terms (each with its one-line meaning).
- **Analogies:** partial pooling as early-season batting averages pulled toward the league
  average.
- **Numbers.** None new (recap keys only).
- **Figures:** none.
- **Decision log explained:**
  - Future work (2026-10-09): strength change, hierarchical Bayes, staggered rollout,
    reworks, dashboard.
  - Publishing undecided.
- **Must label:** everything in Appendix D.
- **Waits on:** Phil's conclusion. **Skill:** stating limits honestly.
- **Readiness:** ready as structure; the conclusion is Phil's.

## Appendices

- **A. Answer key** (`a_answers`): generated from the stop-and-check boxes. Each question
  carries its answer in the source; the appendix collects them.
- **B. Glossary** (`b_glossary`): the table below, in order of first appearance.
- **C. Your numbers on one page** (`c_numbers`): a recap table built only from numbers.json
  keys, a study aid. It is not a reproducibility appendix: that stays out (decision log
  2026-10-09), and the build stamp is on the title page.
- **D. Still open, or not yet verified** (`d_open`): from SPIROMETRY.md and PLAN.md, each item
  labelled.

---

## Glossary, in order of first appearance

| Term | One-line meaning | Analogy | Ch |
|---|---|---|---|
| Balance patch | A game update that changes cards' numbers or rules | A recipe change at a restaurant chain | 0 |
| Card change | One card's difference between two builds | One dish's recipe edit | 0 |
| Numeric tweak | A change to a number on a card (6 damage to 8) | More salt in the same dish | 0 |
| Rework | A change to what a card does | A new dish under the old name | 0 |
| Run | One game, start to win or death | One diner's meal | 0 |
| Run file (record) | The uploaded log of one run | A flight recorder | 1 |
| Reward screen | The choice of cards after a fight | A hand dealt to you | 1 |
| Offer | One card shown on a reward screen | One card in the hand | 1 |
| Build | One game version (v0.103.2) | A software release | 1 |
| Stable / beta branch | The main release lane / the early-test lane | Main road / test track | 1 |
| Patch window; before / after block | The builds compared around one change | Before and after photos | 1 |
| Snapshot | The downloaded copy of the export | A photocopy of the guest book on one day | 1 |
| Backfill (upload lag) | Runs uploaded long after they were played | Holiday photos uploaded months later | 1 |
| Duplicate record; run key | The same run uploaded twice; the key that finds it | A guest who signed twice | 1 |
| Retried run | Copies of one run with different endings | Replaying a level from a save | 1 |
| Sample / population | The runs you have / all runs played | A spoonful / the pot | 1 |
| Primary population | The runs the main analysis uses | The study's guest list | 1 |
| Thin build | A build with too few runs to stand alone | A shop open for one day | 1 |
| Uploader group (tagged / untagged) | Runs uploaded with or without the SlayTheStats stamp | Two tills in one shop | 1 |
| Outcome | What you measure (picked, won) | The health check-up | 2 |
| Treatment | What you want the effect of (the patch, taking a card) | Taking vitamins | 2 |
| Confounder | Something that drives both treatment and outcome | Caring about your health | 2 |
| Selection | Treated and untreated differ by who chose | Who buys vitamins | 2 |
| Causal effect / counterfactual | What would change if only the treatment flipped / the world where it didn't | The road not taken | 2 |
| Pick rate | Picks ÷ offers; P(picked given offered) | Free-throw percentage | 3 |
| Percentage points vs percent | Subtracting rates vs dividing them | An interest rate from 2% to 3% | 3 |
| Mean / median | The average / the middle value | | 3 |
| Variance, standard deviation | How spread out values are; p(1 − p) for a 0/1 outcome | | 3 |
| Standard error (SE) | How far an estimate would move on a fresh sample | One spoonful of soup | 4 |
| Square-root rule | Noise shrinks as 1/√n | Ten coin flips vs ten thousand | 4 |
| 95% confidence interval | Estimate ± about 2 SE | | 4 |
| z | Estimate ÷ SE | | 4 |
| Clearly nonzero | \|z\| > 2 (calibrated version in ch 8) | | 4 |
| Bias | A systematic error more data doesn't fix | A scale that always reads heavy | 4 |
| Multiple comparisons | Test enough things and some pass by luck | Many lottery tickets | 4 |
| Difference-in-differences | Treated change minus control change | Two plants on a windowsill | 5 |
| Treated / control cards | The changed card / unchanged same-colour cards | Fertilized / unfertilized plant | 5 |
| Control exclusions | Same-colour cards changed in the window, left out | Plants moved to another window | 5 |
| Parallel trends | Without the patch, treated would move like controls | Both plants grow alike in the same sun | 5 |
| Fixed horizon (weeks 0–3) | Only the first four after-weeks count | Judging both races at the same lap | 5 |
| Regression; coefficient (β) | A fitted relation; the effect of one input | | 6 |
| Linear probability model | Regression on a 0/1 outcome | | 6 |
| Fixed effects | A separate baseline per group | Grading within a class | 6 |
| iid / robust / clustered SE | Error bars assuming independence / unequal noise / related offers within a run | Ten family members vs ten strangers | 6 |
| Log-odds; delta method | log(p/(1 − p)); approximate change of scale | Betting odds | 6 |
| Offer-rate check | The patch shouldn't change how often a card is offered | The dealer didn't change the deck | 7 |
| Pre-trend; event study | Drift before the patch; the gap week by week | A time-lapse | 7 |
| Placebo test | A test where the true effect is zero | A sugar pill | 7 |
| Anticipation | Players reacting at the beta notes, before stable | Umbrellas sold at the forecast | 7 |
| Robustness / sensitivity analysis | Change one choice, see how far the answer moves | Weighing on another scale | 7 |
| Pseudo-treated card | An unchanged card analysed as if changed | A smoke-alarm test without fire | 8 |
| Standard normal; sd of z | What z should look like with honest errors; its spread | | 8 |
| Robust sd (MAD) | A spread measure that a few outliers can't drag | | 8 |
| Calibration factor; calibrated z | The placebo spread; z divided by it | A scale checked with known weights | 8 |
| Empirical p | Share of placebos at least as large as the real effect | | 8 |
| Forest plot | Every estimate with its interval, in a column | A row of thermometers | 9 |
| Buff / nerf; toward the change | A card made stronger / weaker; the effect's sign matches | | 9 |
| Mixed-direction / upgrade-only tweak | Numbers moved both ways / only the upgrade changed | | 9 |
| Dose; ruler (ln(new/old)) | The size of a change; how it's measured | A medicine dose | 10 |
| Meta-regression | Regression across estimates, weighted by precision | Thermometers weighted by accuracy | 10 |
| Between-card scatter (τ); random effects | Real differences between cards beyond noise | Patients responding differently | 10 |
| Slope per patch; z diff | A separate line per patch; how far apart they are | | 10 |
| Post hoc | Chosen after seeing the results | Calling the shot after it lands | 11 |
| Measurement error (attenuation) | A noisy dose flattens the slope | A blurry ruler | 11 |
| Leave-one-out; influential point | Refit without each point; one that moves the answer | One juror leaving | 11 |
| Statistical power; simulation | The chance a real effect is detected; computing it by fake data | A metal detector's sensitivity | 12 |
| Fake patch | A comparison across builds with no card change | A rehearsal with nothing changed | 12 |
| Regression to the mean | Extreme values tend to be followed by ordinary ones | A best-ever exam, then an ordinary one | 12 |
| Spillover (substitution) | A change to one card moves picks of others | A discount moves the rival brand's sales | 12 |
| Control scope | Which cards serve as controls | | 12 |
| Pre-declared analysis | Spec and prediction written before running | Writing the bet down before the race | 12 |
| Instrument | A random push on the treatment that affects the outcome only through it | A gym-pass lottery | 13 |
| Intent-to-treat (ITT) | Effect of being offered | Effect of winning the pass | 13 |
| First stage | How much the offer raises picking | Share of winners who go | 13 |
| IV estimate (Wald, 2SLS) | ITT ÷ first stage | Effect of actually going | 13 |
| Compliers | Runs that take the card when offered | Winners who go | 13 |
| Relevance / independence / exclusion | The three IV assumptions | | 13 |
| Weak instrument (F < 10) | A first stage too small to trust IV | A lottery almost nobody uses | 13 |
| First K screens; survival bias | Only early screens count; later ones favour survivors | | 13 |
| Balance check | Offered and not-offered runs look alike before the offer | | 13 |
| Partial pooling (hierarchical Bayes) | Shrink noisy estimates toward the group | Early-season batting averages | 14 |
| Staggered rollout | Using beta-before-stable timing as a second experiment | | 14 |

**Where the build-up order can't hold:**
- **Ch 0** names DiD, instruments and dose-response as pointers, defined in ch 5, 13 and 10.
- **Ch 1** says retried runs leave the win analyses (ch 13) before wins are explained.
- **Ch 4** mentions partial pooling (ch 14) as the planned answer to multiple comparisons.
- **Ch 2** uses the IV primer's simulation as an example before "simulation" is defined
  (ch 12). The fix is to say "a made-up game where the answer is known" there.

---

## Where v1's structure changes, and why

1. **A data chapter (ch 1) before confounding.** v1 folded the population into "Counting".
   v2 has the complete snapshot, backfill, deduplication, retries and thin builds. Many
   decision-log entries are about them, and Phil must be able to defend them.
2. **The placebo calibration gets its own chapter (ch 8).** The decision log makes the
   calibrated count the lead number, so it has to be taught before the results.
3. **Results (ch 9) and dose-response (ch 10) are split.** v1 combined them; each now has
   Phil's "what was found" passage.
4. **Two chapters for the second-patch puzzle (ch 11–12)**, from the triage: measurement
   first (ready now), design explanations second (waits on task 7).
5. **v1's "Next PR" checklist chapter is dropped.** Step 5 is future work (2026-10-09). Its
   place goes to "settled, open, next" (ch 14).
6. **Instruments move after the pick-rate story (ch 13)** and gain the real power check
   (task 9) beside the simulation.
7. **A "Skill" line in every section** (new in v2).
8. **Back matter.**
   - The answer key is generated from the boxes, so questions and answers can't drift apart.
   - "Your numbers on one page" is built from keys.
   - No reproducibility appendix; the build stamp goes on the title page.
9. **The "how the numbers are marked" box** gains "pending" alongside "unverified", for the
   weeks 0–3 calibrated counts and the distinct-runs count.

---

## Readiness summary

| Chapter | Status | Waits on |
|---|---|---|
| 0 Project | Ready | reference key (50 tweaks); distinct runs stays pending |
| 1 Data | Partly ready | audit aggregates; build_info fields in meta.json |
| 2 Confounding | Partly ready | audit (uploader-group example); ready with the primer example |
| 3 Counting | Ready | |
| 4 Noise | Ready | |
| 5 DiD | Ready | |
| 6 Regression | Ready | |
| 7 Checks | Ready | |
| 8 Placebo | Partly ready | weeks 0–3 placebo run |
| 9 Results | Partly ready | weeks 0–3 placebo run; Phil's passage |
| 10 Dose-response | Ready | Phil's passage |
| 11 Rulers | Ready | |
| 12 Design explanations | Waits | task 7 |
| 13 Wins | Partly ready | task 9 |
| 14 Open | Ready (structure) | Phil's conclusion |

"Ready" means every number is in a saved final-rerun output. Keys are still to be added in
the chapter's task; no chapter's numbers are all in numbers.json today. The only number that
needs a decision rather than a key is distinct runs.
