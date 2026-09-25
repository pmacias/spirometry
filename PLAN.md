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
      *Status: 949 pages (submissions to ~2026-07-19). Daily request cap found; resumes
      after each reset. Pages 873–948 are fetched again once (see SPIROMETRY.md).*
- [ ] Card patch dataset (CC): `reference/builds.csv`, `reference/card_changes.csv`,
      excluded fields, text-only changes. Done when merged and Phil has reviewed the
      whitelist, the text-only list, and the build mapping.
      *Status: built and merged; text-only changes hand-labeled (`text_only_labels.csv`).
      Cross-checked against the official patch notes (PR): 115 of 128 card-patches are in
      the notes, all 69 with comparable numbers match, 4 `tweak`s look like reworks,
      12 notes-only changes. builds.csv reconciled with the wiki's version list (4
      versions added, hotfix branches and dates filled). Phil's decisions are in the
      decision log; applying them to the CSVs (the 4 relabels, notes-only rows) is still
      to do.*
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
*Status: first pass done on 949 pages, with interim tooling: `scripts/audit_extract.py`
writes aggregate tables to `data/audit/` (git-ignored), read by
`notebooks/01_data_audit.ipynb`. Findings so far are in SPIROMETRY.md (Known data issues):
non-release builds, runs dated before release, `_sts` = SlayTheStats upload stamp and the
ranking difference between uploader groups, mod-marker counts, cheat candidates. Unit:
card offer, solo runs (already in the decision log). Decisions written into SPIROMETRY.md
("Audit decisions"): primary population, thin-build pooling rule, staggered rollout feasible
within branch, snapshot reach and backfill, uploader groups, within-build win-rate drift.
Open: backfill numbers and the thin-build check after the snapshot finishes; whether rising
ascension explains the within-build drift. The notebook moves to the Phase 3 tables once
they're built on the full snapshot.*

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
outside the game's list are a mod marker. Next: Phil reruns the full build. `deck_final`, `deaths` and relic/event choices not started.*

### 4. Treatment table — CC
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
1. Review and merge the run-table fix PR (integer types, per-page failures, mod
   enchantments); rerun the full build.
2. Audit follow-ups: does rising ascension explain the within-build win-rate drift; confirm
   the thin betas pool (no card change between neighbours).
3. Let the snapshot finish; run `--count-only`. Decide whether to re-download pages 0–948
   for `player_token`.
4. Send the maintainer message (budget per IP or per client, the daily cap, short pages,
   bulk dump, stable-only hotfixes, when `player_token` was added).
5. Build the run tables on the full snapshot (`python -m spirometry.runs build`) and move
   the audit notebook onto them.
6. Apply the card-change decisions to the CSVs (4 relabels, notes-only rows).

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
  same key. `run_key` is a plain SHA-256 of `seed|start_time` (not personal data).
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
