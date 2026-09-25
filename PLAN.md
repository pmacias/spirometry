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
- [ ] Full run snapshot (local, running). Done when the export reports its end and
      `--count-only` has been run. Record the start date as "snapshot as of."
- [ ] Card patch dataset (CC): `reference/builds.csv`, `reference/card_changes.csv`,
      excluded fields, text-only changes. Done when merged and Phil has reviewed the
      whitelist, the text-only list, and the build mapping.
      *Status: built, in review (PR). 128 card-patches across two stable patches (v0.103.2,
      v0.107.1); 26 text-only for review; 5 card-patches with no beta build.*

### 2. Data audit — Phil
Look at the data before building anything on it. Notebook `01_data_audit`.
- Runs per build, raw and deduplicated; which builds are too thin to use.
- Beta vs. stable run counts (decides whether the staggered-rollout design is possible).
- Cheated / modded / abandoned runs: how many, how to filter.
- Character and ascension mix per build; uploader mix over time (self-selection check).
- Decide the unit of analysis: run or player-run (co-op).
Done when the filters and the unit are written into `SPIROMETRY.md`.

### 3. Run tables — CC builds, Phil runs locally
Parse raw runs into DuckDB/Parquet. Player IDs hashed.
- `runs`: one row per run (build, branch, character, ascension, win, floor reached, flags).
- `card_offers`: one row per card offered (run, floor, act, card, upgraded, picked). This is
  the core table for every design below.
- `deck_final`, `deaths` (encounter, floor), and relic/event choices later.
Done when tests pass on sample pages and the full snapshot builds locally without errors.

### 4. Treatment table — CC
Join `card_offers` to the card version live in each run's build: for each (card, build), which
version was live and whether it's pre- or post-change. Also list, for each change, the other
cards of the same character changed in the same patch (candidates to exclude from its control
group). Done when every offer in a changed card's window has an unambiguous version.

### 5. Analysis — Phil, in this order
1. **Offer-rate check** (design validity): a patch shouldn't move how often a card is offered.
   If it does, something else changed (card pool, rarity) and that card's comparison is suspect.
2. **Pick-rate DiD for numeric tweaks** — the minimum result.
3. **Dose-response on pick rate:** effect against change size.
4. **Win effects within a build:** intent-to-treat (offered → win), then IV (effect of
   picking, with the offer as instrument).
5. **Strength change across a patch:** IV estimates pre vs. post, net of unchanged cards.
6. **Perception vs. strength:** pick-rate effects against strength effects.
7. **Hierarchical Bayes:** partial pooling across cards, characters, and ascension, so rarely
   offered cards don't get extreme estimates.
8. **Staggered rollout** (beta before stable), if the audit shows enough beta runs.
9. **Reworks:** before/after estimates, reported separately.

### 6. Metric and dashboard
Selection-corrected card strength metric; dashboard (Streamlit or Observable, undecided).

### 7. Write-up
README with results, portfolio card on pmacias.github.io.

## Next up
1. Review and merge the card patch dataset PR.
2. Let the snapshot finish; run `--count-only`.
3. Send the maintainer message (budget per IP or per client, short pages, bulk dump,
   stable-only hotfixes).
4. Phase 2 audit.

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
