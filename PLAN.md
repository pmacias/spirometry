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
Next: Phil reruns the full build and reads both counts. `deck_final`, `deaths` and
relic/event choices not started.*

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
then builds the run tables with parser 1.4.0 to get the view.*
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
("Phase 5 results, first pass"). Provisional until the rebuild on the full snapshot.*
*Follow-up tooling (CC, PR): `fit_did` returns `se_hc` (heteroskedasticity-robust, same
fit) and takes `max_week_after` (fixed horizon; `run_all` passes it to the placebo too);
`offer_rate_check` adds `rarity` and same-rarity z-scores/flag (`flag_rarity`); dedup key
fixed (parser 1.6.0). Tested on synthetic offers; not run on real pages (the 2 fetched
pages have no v0.103.2 runs). Next: Phil rebuilds with parser 1.6.0 and reruns the
notebook with `se_hc`, `max_week_after=3` and `flag_rarity`.*
*Notebook v2 (2026-09-26, same 949-page tables): robust SEs, fixed horizon, same-rarity
flags and patch terms run; results in SPIROMETRY.md. New question: the second patch shows
no dose-response.*
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
1. Review and merge the card-decisions + mod-entity PR; rerun the full build (parser
   1.3.0) and read `runs_mod_entity_only` in `build_info`.
2. Audit follow-up: does rising ascension explain the within-build win-rate drift.
3. Let the snapshot finish; run `--count-only`. Decide whether to re-download pages 0–948
   for `player_token`.
4. Send the maintainer message (budget per IP or per client, the daily cap, short pages,
   bulk dump, stable-only hotfixes, when `player_token` was added).
5. Build the run tables on the full snapshot (`python -m spirometry.runs build`) and move
   the audit notebook onto them.
6. Phase 4: review the treatment tables (`notes/treatment_table.md`), then rebuild the
   run tables (parser 1.5.0) for `offers_with_version` and the deduplicated `primary_offers`.
7. Phase 5 follow-ups. Done on the 949-page tables: (a) same-rarity offer-rate check:
   Patter, Sculpting Strike and The Scythe are card-specific, not pool changes; (b) fixed
   horizon: not the cause of the gap between patches; (c) patch term: the second patch has no
   dose-response (slope 0.02 ± 0.31 against 1.44 ± 0.19); (d) robust SEs: clustering adds
   about 3%; (e) dedup key fixed in parser 1.6.0. Next: (g) fit per patch within each
   uploader group (the tooltip hypothesis) and by kind of main field; (h) where the flagged
   cards' extra offers come from (act, floor type, event fights); (i) after the rebuild,
   which copy of a duplicated run to keep (copies often differ in floors or win: e.g. keep
   the one with most floors); (f) the heavy-uploader check after the rebuild.
8. When official act 4 (or other new content) ships: re-cache the game lists for the new
   builds and switch the mod-entity rule to per-build lists (see SPIROMETRY.md, custom and
   modded runs).

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
