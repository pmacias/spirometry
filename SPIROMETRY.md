# Spirometry

Measuring what Slay the Spire 2's balance patches actually did.

Status: Phase 5, first pass done. The pipeline is complete through Phase 4 (reference tables,
run tables, treatment tables). The full snapshot is still downloading; the run tables used so
far are built from the first 949 pages (submissions to about 2026-07-19, parser 1.4.0).
First-pass pick-rate results for the numeric tweaks are under "Phase 5 results, first pass";
the design and the reasoning behind it are in `notes/phase5_deck_v3.pdf`.

---

## What this is

Slay the Spire 2 has been in early access since March 2026. For the first several
months, Mega Crit shipped significant updates roughly every two weeks: small number
changes (a card going from 6 to 8 damage), full reworks (a card that used to block now
gives energy), and changes to enemies, bosses, relics, and events.

The community has collected well over a million runs of these games as raw run files. Every
run is tagged with the game build it was played on. Lining up those builds with the patch
history turns early access into a long series of natural experiments: dozens of known
interventions, with known dates and known sizes, on a population of runs we can observe
before and after.

The central question: **when a card (or relic, or enemy) was changed, what did the change
actually do to how it was picked, and to whether runs that had it won?**

Community stats sites answer a simpler question, "what's this card's win rate," and those
numbers are badly confounded. Strong runs see more card rewards; desperate runs take
different picks; cards are offered at particular points in a run. Separating "this card is
strong" from "strong runs pick this card" is the project.

## Why it's worth doing (job-search framing)

- Game balance analytics maps directly to live-ops data science at gaming companies
  (PlayStation is a target).
- The methods are the core of product DS generally: experiments with non-compliance,
  difference-in-differences, staggered rollouts, metric design, dashboards.
- It fills gaps from the Google/Magic Eye gap analysis: causal inference and experiments,
  hierarchical Bayes, metric development. It also produces my first real dashboard.
- It's real data about real product changes, not a simulation or a Kaggle set.

It complements Clickworthy rather than duplicating it. Clickworthy tests observational
methods against real randomized A/B tests (aggregate, per-headline data). Spirometry
applies quasi-experimental designs to run-level data with repeated, known interventions.

## Data sources

### Spire Codex (primary) — spire-codex.com

Fan-run database and API for STS2. Open source (github.com/ptrlrd/spire-codex). Not
affiliated with Mega Crit.

- **Raw runs:** `GET /api/exports/runs` — gzipped JSONL, one full raw game run file per
  line, as submitted by players. Params: `limit`, `start` / `end` (ISO-8601 bounds on
  `submitted_at`), `cursor` (from the `X-Next-Cursor` response header). Own rate budget
  of 120 credits/hour, **plus a daily cap**: after roughly 1,200–1,300 requests the server
  answered 429 with `Retry-After` of about 24 h, resetting around 23:08 Pacific (size not
  documented; estimated from the download log). `snapshot_export.py` obeys `Retry-After`, so
  it just sleeps. **Verified working** from my Mac and from a CC cloud session.
  - Cost: 1 credit per page (`limit=1000`), ~2.3 MB gzipped per page.
  - Most pages are full (1,000 runs). Now and then a page comes back short (the smallest
    of the first 949 had 466 runs). Probably server-side filtering after the page is cut;
    the cursor still advances normally.
  - Export is ordered oldest submission first, and the order is the same from any client
    (Mac and cloud session agree). The first 5 pages covered v0.98.0–v0.103.2. That
    includes beta builds (v0.100.0–v0.103.1 are beta per `reference/builds.csv`; 30% of the
    first two pages). The earlier "no beta" reading came from counting `is_beta`, a field
    the export records don't have (`notes/run_schema.md`).
  - `start` / `end` bound submission time, not play time: a page from `start=2026-09-01`
    still had 16% of its runs on v0.98.x–v0.99.1.
  - Snapshot so far (2026-09-25): 949 pages, 947,885 records (727,714 distinct runs),
    2.9 GB, ~3.1 MB per page, covering submissions up to about 2026-07-19. The total is
    still unknown; the earlier ~1,800-page projection assumed ~1.8M runs.
  - Pages 873–948 get downloaded twice: two download processes ran at once, and the
    restart resumed from the slower one's cursor. The repeats land in pages 950 onward and
    are dropped on `run_hash` by both the parser and the audit extractor.
- **Run summaries:** `GET /api/runs/list` — one row per run, filterable by build, card,
  relic, character, ascension, player count. Only covers the most recent ~10,000 runs.
- **Pre-aggregated stats:** `/api/runs/community-stats`, `/api/charts/...` — useful for
  sanity checks only.
- **Game data:** cards, relics, monsters, events, encounters, etc., extracted from the
  game files, in 15 languages. Also a bulk ZIP per language (`/api/exports/{lang}`).
- **Patch history:** `GET /api/update-history/{entity_type}/{entity_id}` (per-entity
  game-patch history) and `/api/changelogs` (+ `/api/changelogs/{tag}`). **Checked** — see
  `notes/patch_history.md`. Summary: both give before/after values; update-history dates
  each change to the *beta* version it first appeared in (e.g. `V0.104.0`, 2026-04-23),
  while changelogs are Spire Codex site releases whose game-data diffs line up with
  *stable* rollouts (e.g. site 1.2.0 = stable v0.107.1, 2026-06-18) and include
  re-extraction noise. Reworks and numeric tweaks are distinguishable from the field diffs.
  A version → branch → date table has to be built by hand. Description text is
  **truncated in both endpoints** (the changelog's `description` / `description_raw` /
  `upgrade_description` values are cut at ~80 characters too, not full text), so text is
  never used to classify changes. Only changelogs 1.1.0 (stable v0.103.2) and 1.2.0
  (stable v0.107.1) are game releases; the other card diffs are parser fixes. Built into
  `reference/` — see Reference data below.
- Rate tiers: no key 15/min, registered 60/min, **academia 100/min (on request)**.
  Unknown whether the academia tier also raises the export's 120/h budget.
- Size: the community stats page claims ~1.8M submitted runs.
- Privacy policy: submitted runs and persona names are "public by design." Players can
  request deletion.

### Official patch notes (third source) — Slay the Spire Wiki

Mega Crit's patch notes, one wiki page per version, mirrored at
<https://slaythespire.wiki.gg/wiki/Slay_the_Spire_2:Patch_Notes> (CC BY-SA 4.0). The
early-access pages (V0.98.1–V0.111.0, 26 pages for 25 versions) are cached as raw wikitext
in `reference/raw/wiki/` and parsed by `python -m spirometry.patch_notes`. Each page header
gives version, type (Beta Patch, Beta Hotfix, Hotfix, Patch, Major Update) and release
date; the notes name cards and usually give before/after numbers ("7(9) -> 10(12)").
They are the only source for changes that don't show in card fields (trigger order,
multiplayer rules, bug fixes that change behavior) and for the stable-only hotfixes. The
wiki occasionally adds editor notes ("(not mentioned in patch notes)"), flagged in the
parsed table. Cross-checked against the Spire Codex tables in
`notes/patch_notes_crosscheck.md`.

### STS2 Runs (secondary) — sts2runs.com

One monthly dump available: `runs-all-before-2026-06.json.gz`, 6,796 runs, ~15 MB,
gzipped NDJSON. Cheated runs included and flagged (`_isCheated`, `_cheatedReasons`).
Too small and too early to be the main source; possibly useful for cross-checks and
early-build coverage.

## What a run record contains

Full field tree, offer sources, co-op and abandoned runs: `notes/run_schema.md` (3 pages,
checked 2026-09-24).

Top level: `acts`, `ascension`, `build_id`, `schema_version` (8, 9, 10), `seed`,
`start_time`, `run_time`, `game_mode`, `modifiers`, `win`, `was_abandoned`,
`killed_by_encounter`, `killed_by_event`, `platform_type`, `players`, `map_point_history`,
`run_hash`. No `is_beta`. Some records also carry `_sts` (the SlayTheStats mod's upload
stamp, see Known data issues) and `_spirecodex_damage` (added by Spire Codex), which aren't
game data. Pages fetched on
2026-09-25 also have a top-level `player_token` on every record (null on most, a 16-character
string on 170 of 2,000); it wasn't in the 2026-09-24 pages, and the local snapshot pages
checked (0, 500, 948, downloaded 2026-09-24/25) don't have it either, although page 0 holds
the same records as today's first page. So `player_token` appeared in the export around
2026-09-25, and pages downloaded before that lack it: whether a record has it depends on
when its page was downloaded, not on the run. The run tables record a missing key as
`has_player_token` NULL (unknown), not false. It probably identifies the uploader and is
hashed like player IDs (`uploader_hash`).

Probe on 2026-09-26 (3 fresh pages): the token is filled on 1.8% of records at the start of
the export, 12% on a page submitted mid-June and 31% on one from mid-September, from 2, 5
and 33 distinct uploaders. The export fills it in retroactively where it knows the uploader.
It never appears together with `_sts`, so it marks a separate upload route (probably Spire
Codex's own), not the SlayTheStats mod. Uploads are concentrated: one uploader made 259 of
the 1,000 records on the September page. Decision: the first 949 pages are **not**
re-downloaded for now (about a day of the cap for tokens on a few percent of those runs);
resuming the download brings the recent, token-rich submissions. If tokens on the old pages
matter later, fetch them into a separate folder and keep only a `run_hash → player_token`
table to merge in. Uses: clustering standard errors by uploader, a drop-the-top-uploaders
robustness check, and within-player before/after comparisons for a few heavy uploaders.

`map_point_history` is a list of acts, each a list of floors. Each floor has:

- `map_point_type`: monster, elite, boss, shop, rest_site, treasure, ancient, unknown
- `rooms`: `model_id` (e.g. `ENCOUNTER.NIBBITS_WEAK`, `EVENT.NEOW`), `monster_ids`,
  `room_type`, `turns_taken`
- `player_stats` (one entry per player):
  - `card_choices`: every card offered, each with `was_picked` (`CARD.<card_id>`, plus
    `current_upgrade_level` and `enchantment`). There's no source field: the floor type
    says where the offer came from, and several reward screens on one floor share one
    list. In solo shops the list is the unsold shelf, and bought cards are only in
    `cards_gained` (see `notes/run_schema.md`)
  - `relic_choices`, `potion_choices`, `ancient_choice`: same pattern
  - `event_choices`: option taken (localization key, e.g.
    `BYRDONIS_NEST.pages.INITIAL.options.EAT.title`)
  - `cards_gained`, HP (`current_hp`, `max_hp`, `damage_taken`, `hp_healed`, ...),
    gold (`current_gold`, `gold_gained`, `gold_spent`, ...)
  - `player_id`

`players` holds each player's final `deck` (with `floor_added_to_deck`), `relics`,
`potions`, and `character`.

**What's missing:** nothing about what cards did in combat (damage per card, plays per
turn). "Was this card good in this run" can't be read directly off the file.

## Reference data (`reference/`)

Built by `python -m spirometry.patch_history` (fetches into `reference/raw/`, cached and
committed — no player data — then builds the CSVs from the cache; at most 10 requests/min,
~60 min for a cold cache). Cards only so far. The cache also holds the game lists that
`spirometry.runs` checks run ids against (mod markers): enchantments
(`raw/enchantments.json`, `/api/enchantments`), and events, encounters and monsters
(`raw/{events,encounters,monsters}.json` from `/api/<name>`, the stable build's data, plus
`raw/<name>/<version>.json` from `/api/<name>?version=<v>` for every beta in `builds.csv`).
The per-version endpoint returns data for v0.100.0–v0.111.0 and an empty list for v0.99.0
and v0.110.1. The lists differ only in the Doormaker → Aeonglass boss swap (Doormaker on
betas up to v0.104.0, Aeonglass from v0.105.0) and three beta-only encounters from v0.108.0
(`BATTLEWORN_DUMMY_EVENT_V1/V2/V3_ENCOUNTER`). Content removed before v0.100.0 isn't in any
list; the changelogs' added/removed entries cover it (Toadpoles, Door in 1.1.0).

- `builds.csv` — one row per game version (from update-history, changelog text, and the run
  data): `build_id` (lowercase, as in run files), `branch`, `release_date`, `source`,
  `notes`. Blank where no source says; `notes` explains. Stable dates are Spire Codex
  changelog dates (an upper bound on the Steam release); beta dates are update-history dates.
- `card_changes.csv` — one row per (card, field, stable patch): `old`/`new` from the
  changelog, `beta_build`/`beta_date` (first beta where update-history shows that field
  changing), `stable_build`/`stable_date`, `change_kind` (tweak, rework, cost_change,
  rarity_change, text_only, added, removed, mechanic, artifact; `+`-joined, e.g.
  `rework+cost_change`), `classified_as` (the classifier's label before any decision),
  `changed_fields` (every field in that card-patch, for reclassifying), `source`,
  `decision` (blank unless a decision in PLAN.md's log changed the row), and from the
  cached card list `multiplayer_only` (`yes`/`no`; the API sets the key only when true),
  `rarity` and `color`. Those three describe the card as it is in the stable card list
  now, not at the time of the change (4 card-patches are rarity changes), and are blank
  for cards not in the list (Grapple, Follow Through, Prepare). Two stable
  patches so far: v0.103.2 (85 card-patches from the changelog + 4 notes-only) and v0.107.1
  (43 + 8). The decisions are applied by the build scripts, not by hand
  (`patch_history.RELABELS` / `ARTIFACTS`, `notes_crosscheck.notes_only_rows`):
  - Glow, Grave Warden (v0.103.2), Shatter, Tesla Coil (v0.107.1): `rework`
    (`classified_as` tweak); the patch notes describe more than a number.
  - Folly, Shiv (v0.103.2), Sacrifice (v0.107.1): `artifact` (parser changes; kept, excluded
    from analyses).
  - One row per notes-only change (12: Beacon of Hope, Dazed, Prepare, Prepared in
    v0.103.2; Blade of Ink, Entrench, Gold Axe, Lantern Key, Nightmare, Stratagem, Tag Team,
    Tyranny in v0.107.1): `change_kind = mechanic`, `source = patch notes`,
    `field = (patch notes)`, `old`/`new` blank, `beta_build` = the beta whose patch notes
    list the change (`patch_notes_cards.csv`, `role = subject`, content/balance; the first
    if several betas do: Dazed and Prepared, v0.100.0 and v0.101.0), the notes quoted in
    `decision`. Phase 4 uses `beta_build` to decide which betas carry the change. Taken from `crosscheck.csv`'s "notes only: missing"
    rows, so those cards leave control groups. Dazed's notes are about encounters that
    apply it; Prepare/Prepared were reworked and restored within the window.
  - Numeric tweaks (`change_kind = tweak`, the minimum result's set): 50 card-patches, 31
    in v0.103.2 and 19 in v0.107.1 (`patch_history.numeric_tweaks`). None filtered, but 7
    can't come from character card rewards, so the solo reward design has little or no
    data on them (`patch_history.tweak_report`, printed by the build): Believe in You
    (multiplayer-only, colorless), Eternal Armor, Seeker Strike (v0.103.2) and Fasten
    (v0.107.1) (colorless: shop, events, ancients), Falling Star (Regent's Basic starter),
    Minion Strike (v0.103.2) and Minion Sacrifice (v0.107.1) (Token). On the first export
    page: 2 Fasten and 1 Seeker Strike offers in `primary_offers`, none for the other five.
    The other 43 are Common/Uncommon/Rare character cards, none multiplayer-only.
- `text_only_changes.csv` — the text_only card-patches, for manual review.
- `excluded_fields.csv` — every card field left out, with counts and the reason (not in
  the gameplay whitelist, a `*_key` mirror, or from a site/parser changelog).
- `history_unmatched.csv` — update-history entries up to v0.107.1 that no changelog row
  explains (reverted beta changes, parser fixes that history dates as game changes, the
  V0.98.0-beta/V0.99.0-beta flip pairs).
- `text_only_labels.csv` — Phil's hand labels for the 26 text_only card-patches
  (`card_id`, `stable_build`, `label`, `basis`, `note`). `mechanic` = the text change
  changes play, treat it as a rework (12); `wording` = no gameplay change (12);
  `exclude` = drop the card from all analyses (2, Mad Science). Hand-maintained: no
  script writes it.

From the official patch notes, built by `python -m spirometry.patch_notes` (fetches the wiki
pages into `reference/raw/wiki/` if missing, at most 10 requests/min, then builds everything
below from the cache; `python -m spirometry.patch_history build` also re-applies the wiki's
version list to `builds.csv`):

- `builds.csv` is reconciled with the wiki's version list: missing versions added (v0.99.0,
  v0.103.3, v0.105.1, v0.110.1), blank branch and date filled from the page header, the
  wiki recorded in `source`, and conflicts noted in `notes` (prefixed `wiki:`) rather than
  overwritten.
- `patch_notes_cards.csv` — one row per card mention in the notes (and one per numeric
  change when an item gives several): `version`, `page_type`, `branch`, `date`, `section`
  (content, balance, content+balance, writing, bug fix, or another heading such as art),
  `subsection`, `verb` as written (Buffed, Nerfed, Changed, Reworked, Added, Deprecated,
  Removed, Reverted, Adjusted, or blank), `card_name`, `card_id` (from the card list;
  `in_card_list = no` for beta-only, removed or renamed cards), `role` (`subject` = what
  the item is about, `context` = mentioned in passing), `wiki_only` (a wiki editor's note,
  not Mega Crit's), `quantity`, `before_base`, `before_upg`, `after_base`, `after_upg` (as
  written; blank = not given, never assumed equal), `raw_text`.
- `crosscheck.csv` — one row per (card, stable window): in the notes, in card_changes, and
  whether they agree (numbers chained across betas; see `notes/patch_notes_crosscheck.md`).
- `behavior_changes.csv` — bug-fix items that change how a card plays (timing, generation,
  interactions, multiplayer), from a keyword heuristic. Candidates to leave out of control
  groups around that build, not treatments.
- `beta_card_changes.csv` — card changes that never reached stable as written: everything
  after v0.107.1, beta values revised or reverted before stable, beta-only cards, from the
  notes plus update-history. `change_kind` is `artifact` for the 5 v0.106.1 update-history
  entries whose every field goes to `none` with no changelog behind it (Ascender's Bane,
  Folly, Genetic Algorithm, Summon Forth, The Scythe); blank on other rows.

From those tables, built by `python -m spirometry.treatment` (no fetching, no run data;
details and counts in `notes/treatment_table.md`):

- `change_events.csv` — one row per card change event: a card changing on one build
  (`event_id` = `CARD@build`). Stable-window card-patches are split per beta (Parry
  `@v0.100.0` 6(9) → 8(11), `@v0.101.0` → 10(14)); beta revisions and reverts are their own
  events; betas after v0.107.1 come from `beta_card_changes.csv`; bug fixes from
  `behavior_changes.csv` are `change_kind = behavior`, `sensitivity_only = yes`
  (`CARD@build/fixN`). Columns: `event_build`, `first_beta` (blank for stable-only
  events), `stable_build` (blank if reverted before stable or after v0.107.1),
  `window_stable`, `timing` (beta, stable_only, unknown), `change_kind` + `kind_source`
  (`card_changes`, `notes-only` (card_changes' notes-only rows), `beta_card_changes`,
  `text rule` (labeled by rule from the notes/update-history text), `behavior`), `text_only_label`,
  `status` (reverted, revised, after_last_stable, ...), `field_changes` (summary).
- `change_event_fields.csv` — per (event, field): `old`, `new`, `rel_change`
  ((new − old)/|old|, blank if not numeric or old = 0), `via`. Changelog fields as in
  card_changes; `notes:<quantity>` (and `(upgraded)`) from the patch notes;
  `history:<field>` from update-history. `?` = the value between two betas isn't known.
- `card_versions.csv` — every card (card list plus event-only cards) × every build in
  `builds.csv`: `version` (0 = no events; each distinct set of carried events gets the next
  number in release-date order), `event_ids` carried so far, `behavior_event_ids`, `note`.
  Betas carry every earlier beta event, stables every event of their window and before,
  hotfixes nothing of their own. Blank for v0.98.0, the `-beta` pseudo-versions, and
  Tear Asunder / Seven Stars on the betas of their window (timing unknown).
- `card_patch_fields.csv` — per (card-patch, field): the net old → new from one stable
  build to the next (`card_changes.csv`, artifacts left out), `rel_change`, and the
  member events. `card_patch_id` = `CARD@stable/patch`.
- `windows.csv` — `level = event`: per (event, branch); `level = card_patch`: one stable
  window per card-patch, clean when the card differs by exactly its member events (all
  137 are, including all 50 numeric tweaks). Columns: `before_builds`, `after_builds`, `clean` (the card
  differs by this event only), `reason`, `control_exclusions` (same-color cards changed
  between the two blocks), `behavior_in_window`, `control_behavior_flags`. v0.99.0 is in
  no window; the thin betas pool (v0.103.0+v0.103.1, v0.105.0+v0.105.1,
  v0.109.0+v0.109.1).
- `tweak_sizes.csv` — one row per numeric tweak card-patch (50), built by
  `python -m spirometry.tweaks` from `card_patch_fields.csv`, `windows.csv` and
  `card_changes.csv`: window builds, `main_field` (first of damage, block, energy_gain,
  powers_applied[0].amount, else the single changed vars.* field) with `old`, `new`,
  `log_ratio` = ln(new/old); the changed upgrade delta (`upgrade_field`, `upgrade_old`,
  `upgrade_new`) and `upgraded_log_ratio`; `upgrade_only` (Serpent Form, Royalties,
  Untouchable v0.107.1), `mixed_direction` (Leading Strike, Reflect), `solo_estimable`
  (no for the 7 in `patch_history.tweak_report`), `direction` (+1 = bigger number is
  stronger; exceptions in `tweaks.DIRECTION`, none so far), `note`. Death March is not
  upgrade-only (base `vars.ExtraDamage` changes too; noted). Serpent Form and Royalties have
  no upgraded ratio (their base value isn't in the change tables); Untouchable v0.107.1's
  uses base block 6 from its v0.103.2 card-patch.

Caveats: update-history types every entry "Beta Patch" (including stable v0.103.2) and has
no entries for stable-only hotfixes (v0.98.1–v0.98.3, v0.99.1, v0.103.1). The wiki fills
their branch and date. Run export records have no `is_beta` field at all, so branch always
comes from `builds.csv`. Details in `notes/patch_history.md` and
`notes/patch_notes_crosscheck.md`.

## Run tables (`data/runs/`)

Built locally by `python -m spirometry.runs build` from `sts2_snapshot/` (git-ignored). One
Parquet file per snapshot page per table, plus `runs.duckdb`, which only holds views over
those files (absolute paths: rebuild if the folder moves) and a `build_info` table (parser
version, build time, record and duplicate counts, share of combat lists that couldn't be
split into screens, the hashing key's fingerprint, and skipped pages with their errors).
Columns and their types follow `notes/run_schema.md`: SMALLINT only for values the game
bounds (act, position and length within one floor's list), INTEGER for values copied from
the record or counted over lists (a mod or edited save can inflate them), BIGINT for
`run_time_s`. A page that fails to parse or write is skipped and reported (file, exception,
run_hash); the build finishes the other pages and exits 1.

- `runs`: one row per record (co-op copies kept). `branch` from `builds.csv`, NULL where
  blank or missing. Flags: `is_custom` (any modifier), `is_modded` (mod markers, including a
  character outside the five real ones, an enchantment outside the game's list, and an
  event, encounter or monster outside the game's lists), `mod_markers` (which markers),
  `mod_entities` (the unknown event/encounter/monster ids), `was_abandoned`,
  `abandoned_at_neow`, `released`
  (`build_id` in `builds.csv`), `before_release` (UTC start date before the build's
  `release_date`; false where the date is blank), `neow_start` (first floor has
  `EVENT.NEOW`). Uploader fields: `uploader_tag` (raw `_sts`, e.g. `slay-the-stats/v1.2.2`),
  `has_player_token` (NULL when the record has no `player_token` key, i.e. its page was
  downloaded before ~2026-09-25), `uploader_hash` (hashed token). `source_page` /
  `source_line` locate the raw record.
- `run_players`: one row per record × player (`player_hash`, `character`).
- `card_offers`: one row per `card_choices` entry, every source, with `source`, `set_idx`
  (combat/elite/boss/`event_combat` screens; NULL when the list can't be split), `set_picked_any`,
  `upgraded`, `enchantment`, `enchantment_amount` (as recorded, unclipped), `in_card_list`,
  `is_mod_card`, `is_mod_enchantment`. `card_id` has no `CARD.` prefix.
- `shop_offers`: solo shops as the list plus purchases (`origin = 'gained'`, `picked` =
  bought); co-op shops as recorded, `usable = false`.
- `offers_with_version` (parser 1.4.0, when `reference/card_versions.csv` exists):
  `primary_offers` joined to `card_versions` on (card_id, build_id), adding
  `card_version`, `event_ids`, `behavior_event_ids`. NULL version on v0.98.0 by design.
- `run_key` (the dedup key, parser 1.6.0): SHA-256 of `seed|start_time|characters|ascension`,
  where `characters` is every player's character, sorted (co-op copies can list the players
  in a different order). Co-op copies of one run carry the same players list, so they share
  it; different runs that happen to share seed and start time (18 solo `run_key`s on the
  949-page tables, differing in character or ascension) get different keys. Up to parser
  1.5.0 it was `seed|start_time` only. Every `run_key` value changed with 1.6.0: anything
  keyed on an older `run_key` has to be regenerated.
- Views: `runs_dedup` (first record per `run_key`, with `n_copies`), `card_offers_dedup`,
  `primary_offers` (the primary population below: solo, no modifiers, not modded, released
  build, not before release, Neow start; combat/elite/boss rewards plus event-then-fight
  floors with `event_fight = true`; no mod cards; abandoned runs kept with
  `was_abandoned`; carries `uploader_tag` for uploader groups). From parser 1.5.0
  `primary_offers` (and so `offers_with_version`) takes its runs from `runs_dedup`: a solo
  run uploaded twice (same `run_key`, different `run_hash`) counts once, as the record
  `runs_dedup` keeps (first by page, line). The population filters apply to that record,
  and its `uploader_tag` is the one the offers carry.
- `build_info` also counts runs not released, before release, not starting at Neow, modded,
  tagged, and with `player_token` absent/present, runs with a mod event/encounter/monster
  (`runs_mod_entity`) and runs flagged by that marker alone (`runs_mod_entity_only`), plus
  event-fight lists by length. Parser 1.5.0 adds `solo_run_keys_multi_record` (solo
  `run_key`s with more than one record) and `primary_offers_dedup_removed` (primary offer
  rows the extra records would add without the dedup). Parser 1.6.0 adds the key
  collisions it now separates: `old_run_keys_split` (`(seed, start_time)` pairs, the old
  key, that now hold more than one `run_key`), `run_keys_split_from_old_key` (the
  `run_key`s in them) and `solo_old_run_keys_split` (the pairs split among solo records).

On the 2 fetched pages, 0.55% of combat reward lists (0.19% of `primary_offers` rows)
couldn't be split; none of the 966 split multi-screen lists had two picks in one screen.
Parser 1.1.0 on 2 pages fetched 2026-09-25 (first page and `start=2026-09-01`, 2,000
records): 0 non-release builds, 6 runs before release, 12 not starting at Neow (all solo:
v0.98.0 3 of 22, v0.98.1 5 of 57, v0.98.2 1, v0.107.1 1, v0.111.0 2), 25 modded, 364
tagged, `player_token` present on all 2,000 (non-null on 170). Solo event-fight lists:
84 of 3 cards, 1 of 4 (Lasting Candy), 2 of 6 (The Lantern Key: one with Driftwood, one
with none of Prayer Wheel, Driftwood or White Star; cause unknown). 0.62% of combat lists
(event fights included) couldn't be split. `primary_offers`: 58,678 rows from 1,416 runs.
Parser 1.5.0 on the first 2 pages fetched 2026-09-26 (2,000 records, 1,680 solo, play dates
2026-03-05 to 2026-04-05): 0 solo `run_key`s with more than one record, so the dedup
removes 0 `primary_offers` rows (67,513 rows from 1,580 runs). All 137 multi-record
`run_key`s are co-op copies (differing only in `run_hash`); one 2-player run has 4 records.
Parser 1.6.0 on the same 2 pages (fetched again 2026-09-26): 137 multi-record `run_key`s,
all co-op, the same as with the old key (in one of them the copies list the players in a
different order; characters and ascension never differ within one); 0 keys split; 67,513
`primary_offers` rows from 1,580 runs, unchanged. The pages have no solo duplicates, so the
split is tested on the fixture only.
Not yet verified on the full snapshot: how often a solo run is uploaded twice, and what
differs between the copies (`_sts`, `player_token`).

## Phase 5 tooling (`spirometry.did`)

Functions that return tables for the analysis notebook (no plotting). Input: a read-only
connection to `runs.duckdb` (`offers_with_version`, plus `runs` for `uploader_hash`) and the
reference CSVs (`windows.csv` at `level = card_patch`, `builds.csv`, `tweak_sizes.csv`, the
cached card list for colors).

- `load_window(con, card_patch_id)`: the window's offers for the treated card's character,
  that character's cards only, on `before_builds` + `after_builds`: `run_key`, `card_id`,
  `block`, `picked`, `upgraded`, `act`, `ascension`, `group` (tagged / untagged, from the
  copy `runs_dedup` keeps), `screen_id` (run_key|floor|set_idx, or |list when set_idx is
  NULL), `start_time`, `week` (whole weeks from the first after-build's release date),
  `build_id`, `uploader_hash`. Categorical columns to keep memory down.
- `control_cards(card_patch_id, drop_behavior_flags=False, df=...)`: same-color cards seen
  in the window minus the treated card and `control_exclusions` (and
  `control_behavior_flags` if asked).
- `offer_rate_check(df, card_patch_id)` (step 1): per card, offers and share of the
  character's offers before/after, log share ratio, `z_spread` (against the controls'
  median and scaled MAD), `z_binom` (log ratio minus the controls' median over its binomial
  SE), `flag` when both |z| > 3. `rarity` (from the cached card list: the card's rarity
  now, not during the window; 4 card-patches changed rarity) and the same statistics
  against the controls of the card's own rarity: `z_spread_rarity`, `z_binom_rarity`,
  `flag_rarity`, with `controls_median_rarity`, `controls_mad_rarity`,
  `n_controls_rarity`. A change in one rarity's pool moves every card of that rarity; this
  comparison doesn't flag it. A rarity with fewer than 5 controls (or a card with no
  rarity in the list: Follow Through, Prepare and Grapple on the 2 fetched pages) falls
  back to all controls, with a note in `rarity_note`.
- `fit_did(df, card_patch_id, ...)` (step 2): linear probability model with pyfixest,
  errors clustered by `run_key`:
  `picked ~ treat_post | card_id^upgraded + card_id^group + block^group + act + ascension`
  (ascension one level each; group terms dropped when the data have one group). Options:
  `upgraded` (fit on upgraded or un-upgraded offers: upgrade-only tweaks and their placebo),
  `group` (within one uploader group), `pooled_groups` (no group terms: how much the
  adjustment matters), `drop_shared_screens` (control offers that shared a screen with the
  treated card: competition on the screen), `drop_behavior_flags` (bug-fixed controls),
  `drop_uploaders` (heavy-uploader check), `max_week_after` (fixed horizon: keep only
  after-block offers with `week` <= the cap, 0 = release week; the before block is
  unchanged). Returns beta (probability units), se (clustered by `run_key`, the main
  error; ci95 uses it), se_hc (heteroskedasticity-robust, pyfixest `"hetero"`, same fit:
  the comparison for clustering), se_iid, ci95, `max_week_after` (the setting, None when
  unset) and `after_week_max` (latest after-block week in the fit data), counts and the
  four pick rates. pyfixest drops singleton fixed-effect cells;
  `n_singletons_dropped` counts them.
- `fit_event_study(df, card_patch_id, weeks=(-6, 8), ref_week=-1)` (step 2b): the treated
  card's gap per (week, block) cell, week^block^group fixed effects, the before-block
  `ref_week` cell omitted; weeks outside the range binned into the end weeks; before-build
  offers played after the release are their own cells.
- `to_log_odds(beta, se, p_before)`: delta-method conversion, beta / (p(1-p)); an
  approximation, not a logit coefficient.
- `run_all(con, ...)`: `fit_did` for every solo-estimable tweak plus its `tweak_sizes`
  columns and log-odds versions, one data load per window × character. Upgrade-only tweaks
  are fit on upgraded offers, with the un-upgraded fit as `placebo_*`. Fit options (e.g.
  `max_week_after=3`) go to both the main and the placebo fit. A fit that can't run
  (e.g. an empty block) gets the reason in `error`.

Checked on synthetic offers (`tests/test_did.py`): a planted effect is recovered and a
planted null gives ~0; with the tagged share moving 10% → 70% and a 20-point group gap on
the treated card, the pooled fit shows a +0.11 fake effect and the group-term fit doesn't;
a run × card random effect makes the clustered SE larger than the iid one (x1.27), while a
run effect shared by all cards cancels in the treated-vs-control contrast and doesn't. On
2 fetched pages (2026-09-26, `start=2026-05-01` and `start=2026-07-01`) the first stable
window fits end to end; the second has no v0.103.3 runs (no before block). Those estimates
mean nothing at that size.
Added checks (synthetic): with the treated card picked ~5% and controls ~30–60%, and no
within-run correlation, se/se_iid = 0.71 but se/se_hc = 1.00; adding a run × card effect
gives se/se_hc = 1.30 (while se/se_iid is 1.01: the two effects cancel). An effect growing
2 points a week (0.02 + 0.02 × week, weeks 0–9): `max_week_after=3` gives 0.047 ± 0.009
(truth 0.05), uncapped 0.106 ± 0.007 (truth 0.11). With every Uncommon card offered 1.5× as
often after the patch, all six Uncommon cards flag against all controls (|z_binom| ≈ 25–30)
and none against the Uncommon controls (|z_binom_rarity| ≤ 3.3, |z_spread_rarity| ≤ 2).
Not yet run on real pages: the 2 pages fetched for this have no v0.103.2 runs.

## Phase 5 results, first pass (2026-09-26)

From `notebooks/02_pick_rate_did.ipynb` on the run tables built from the first 949 pages
(parser 1.4.0, not yet deduplicated by `run_key`). Results are saved in `data/analysis/`
(git-ignored). Provisional: rerun after the rebuild on the full snapshot. Updated the same
day with notebook version 2 (after the follow-up PR): robust error bars, a fixed horizon,
same-rarity offer-rate flags and patch terms in the dose-response fit.

**Data checks.** 106 of 577,092 solo `run_key`s (0.02%) have more than one record, so the
missing dedup doesn't matter here. 18 of the 106 differ in character or ascension: different
runs that share a seed and start time, which the 1.5.0 dedup would merge (fixed in parser 1.6.0: the key now includes the
characters and ascension).
Offers per stable build: v0.99.1 2.46M (62k runs), v0.103.2 2.98M (78k), v0.103.3 1.89M
(51k), v0.107.1 3.95M (106k). v0.103.3 is not thin.
Copies of the same solo `run_key` often differ in the game itself: of the 106, the win
differs in 24, floors reached in 70, abandonment in 33 (the 18 collisions included). So a
duplicated run is not always one record uploaded twice; possibly a run reloaded from a save,
or uploaded before it ended. Keeping the first copy by page can keep the less complete one.
Negligible at 0.02%; recheck on the 1.6.0 tables.

**Offer-rate check.** 3 of 43 flagged against all controls: Patter in both patches (offer
share +17% and +12% against the controls' median) and Sculpting Strike (+11%). All three
still flag against controls of their own rarity (Common), so it isn't a rarity pool change:
something specific to these cards changed how often they're offered. The Scythe (Rare,
second patch) flags only against its own rarity (+6% against the Rares' −4%). Their
pick-rate estimates carry a caveat until this is explained. Regent's Commons have only 8
controls in the first window.

**Pick-rate DiD, 43 tweaks** (β in percentage points, relative to unchanged cards of the
same character; "clearly nonzero" = |β| > 2 SE):

| | First patch (26) | Second patch (17) |
|---|---|---|
| Clearly nonzero | 22 | 6 |
| …in the direction of the change | 18 | 4 |
| Median \|β\| | 4.5 | 1.3 |

- Largest: Corrosive Wave −16.6 (pick rate 43% → 29%), Parry +14.9 (13% → 28%), Leading
  Strike +10.3 (mixed: damage 7 → 3, Shivs 1 → 2), Fight Me +9.7, Untouchable (v0.103.2)
  −9.6, Danse Macabre +7.6 (7% → 16%).
- Buffs with lower picks: Grand Finale −4.4, Memento Mori −3.9, Solar Strike −1.7. Second
  patch: Debilitate's nerf shows +2.6 (its first-patch buff was still rising).
- Parry by hand: controls 27.5% → 27.5%, Parry 12.9% → 27.9%; raw DiD +15.0, regression
  +14.9 ± 0.8; every robustness option between +14.7 and +15.7.
- The second patch's effects are smaller at similar change sizes, and it isn't the
  horizon. The first patch's after period runs 11–14 weeks against 5, but over after-build
  weeks 0–3 alone the median |β| is still 4.8 against 1.3 points (21 and 7 clearly nonzero).
  Most of each effect arrives in the first month: Leading Strike +9.4 at weeks 0–3 against
  +10.4 overall, Pinpoint −7.6 against −8.6.

**Error bars.** Clustered SE ÷ plain (iid) SE ranged 0.59–1.26, median 0.99. That ratio
mostly measures unequal noise between cards: a 0/1 outcome's variance is p(1−p), plain OLS
assumes one variance for all offers, and the ratio tracks √(p(1−p)) with correlation 0.96.
Against heteroskedasticity-robust errors, which allow that, clustering by run widens the bars
by about 3% (clustered ÷ robust: median 1.03, range 1.00–1.20), most for common cards
offered many times per run (Crescent Spear 1.20, Uproar 1.19, Collision Course 1.13). Parry:
1.08. Compare clustered errors with robust ones, not plain ones.

**Pre-trends.** Mostly flat. Weekly drift before the release of about 2 SE or more:
Anticipate, Patter (v0.103.2), Gather Light (rising, about 1.5 points a week); weaker
falling drift for Fight Me and Heirloom Hammer. Over a month or more after release that is
comparable to the effects, so these are reported with a caveat or a trend adjustment
(Anticipate's nerf is probably understated). The notebook's χ² screen flags six more cards
at p < 0.01 on single odd weeks; it ignores correlation between weeks, so the slopes decide.
Old-build offers after the release: 8,315 in week 0 and about 1,500 spread over all later
weeks, so mostly release-day timing.

**Robustness** (shift of each check from the main estimate, in main-estimate SEs):

| Check | Median shift | Note |
|---|---|---|
| No uploader-group terms | 0.14 | The tagged share barely moved (≈25% → 22%) |
| Tagged uploaders only | 1.48 | ~¼ of the data, SE about 2× larger; 1 sign flip |
| Untagged uploaders only | 0.30 | |
| Drop shared screens | 0.04 | Competition on the screen doesn't matter |
| Drop bug-fix-flagged controls | 0.02 | |
| Drop top uploaders | – | Not run: these tables have no `uploader_hash` |

Tagged and untagged estimates correlate at 0.68 (χ² of their differences 63 on 43):
mostly the same answer, with a few cards where tagged players respond more (Danse Macabre,
Refine Blade, Debilitate v0.103.2) or less (Patter v0.107.1).

Second patch's before block: dropping first-patch cards from the controls changes nothing;
pooling v0.103.2 into the before block moves several estimates (Furnace +0.2 → +2.9). The
controls aren't the cause, so it is the treated cards drifting over time: v0.103.3 alone
stays the main design.

**Dose-response** (38 tweaks; mixed-direction and upgrade-only kept off the line). x =
direction × ln(new/old) of the main field; y = β in log-odds (delta method), from after-build
weeks 0–3 so both patches share a horizon; random-effects meta-regression. The all-weeks
estimates give the same picture.
- One slope: 1.03 ± 0.18 log-odds per unit of ln(new/old) (all weeks: 1.10 ± 0.18);
  intercept −0.01 ± 0.05, so no sign that appearing in the patch notes moves picks by
  itself. +1 damage on a 7-damage card (ln(8/7) = 0.13) ≈ +0.14 log-odds ≈ +2.2 points at
  a 20% pick rate.
- **By patch: first 1.44 ± 0.19, second 0.02 ± 0.31.** The second patch shows no
  dose-response: in June, a bigger tweak didn't move picks more than a small one. A level
  shift alone (−0.11 ± 0.09) doesn't capture the difference; the slope does. Cause open.
  Candidates: the SlayTheStats mod's community-stats tooltips (from 2026-06-19, the day
  after v0.107.1), more experienced players and a settled meta, the kind of number changed
  (several second-patch mains are power amounts or Forge).
- Between-card scatter: τ ≈ 0.25 log-odds (Q = 881 on 36 df). Same-sized changes had very
  different effects on different cards.
- Buffs vs. nerfs, with the patch term: buff slope 1.62 ± 0.38, nerf slope 0.43 ± 0.40.
  About 2σ apart on 8 nerfs: suggestive only.

**Upgrade-only placebos.** Un-upgraded offers of Serpent Form, Royalties and Untouchable
(v0.107.1) moved −0.5 to +0.1 points, all within about 1.6 SE of zero: no attention effect.
The upgraded-offer estimates are uninformative for Serpent Form and Royalties (126–162
offers); Untouchable's is about zero.

**Open.** Why the second patch has no dose-response (fit per patch within each uploader
group; by kind of main field); why Patter, Sculpting Strike and The Scythe are offered more
often; which copy of a duplicated run to keep; the heavy-uploader check and the rerun after
the rebuild on the full snapshot (parser 1.6.0).

## Audit decisions (first pass: 949 pages, submissions to ~2026-07-19)

From `notebooks/01_data_audit.ipynb` (interim tables from `scripts/audit_extract.py`). These
define the populations every analysis starts from; the parser flags that implement them are
listed in PLAN.md.

**Primary population** (the main analysis): solo runs; no modifiers; no mod markers (a
`save_dict_*` key, a mod modifier, a mod card, a mod act, or a character outside the five
real ones); a released build (in `builds.csv`); start date (UTC) on or after the build's
release date; first floor is Neow. Offers come from combat, elite and boss rewards,
including `?` fights and event-then-fight floors (flagged). Abandoned runs stay in for pick
rates and leave win analyses. On the first 949 pages, primary is ~75% of distinct runs.

- **Cheats:** no filter. No cheat flag exists; 70 of ~98k primary wins took under 15
  minutes and two look impossible. Flagged for a robustness check only.
- **Runs that don't start at Neow:** dropped. About 15% of v0.98.0 runs and 5% of v0.98.1,
  close to zero from v0.98.2 on. They start without the Neow bonus (a different setup) and
  sit in launch builds outside the patch windows.

**Thin builds.** Pick-rate comparisons use windows of builds (before vs. after a change), so
a build only needs to stand alone if it can't be pooled. Rule: a build is pooled with its
neighbour on the same branch when no card change falls between them; otherwise it is left
out of any window it can't fill. Under 2,000 primary runs on the first pass: v0.99.0 (beta,
3 days), v0.103.1 (beta hotfix, 1 day), v0.105.0 (beta, superseded the next day), and
v0.109.1, thin only because the snapshot stops in July. Checked (2026-09-25) against
`card_changes`, `beta_card_changes`, `behavior_changes`, update-history and the patch notes:
no card change between v0.99.0 and v0.99.1, v0.103.0 and v0.103.1, or v0.105.0 and
v0.105.1. The later pages hold only bug fixes; the card-related ones are v0.99.1's
(multiplayer softlock and state fixes, Brightest Flame's Max HP floor, Hand Drill with
Burn, Hellraiser with no targets), v0.103.1's Not Yet no longer generated in combat
(`behavior_changes.csv`, mid-combat generation, not offers) and v0.105.1's Silken Tress
co-op fix (non-host card rewards). v0.103.0/v0.103.1 and v0.105.0/v0.105.1 pool. v0.99.0 is
beta and v0.99.1 stable (on beta for its first three days), so the pair crosses branches:
v0.99.0 (295 primary runs) is left out of all windows (decision log).

**Staggered rollout (beta before stable): feasible on volume.** Every stable build ran
alongside betas: v0.103.2 (Apr 16 – May 29) with v0.104.0–v0.106.1, v0.103.3 with v0.107.0,
v0.107.1 with v0.108–v0.109. The betas have 21k–44k distinct runs each (v0.104.0–v0.107.0)
against 77k–113k for the stable builds running at the same time. Beta and stable players
differ (win and skip rates differ by branch), so comparisons are within branch or allow
branch-specific trends, never a pooled before/after.

**Snapshot reach and backfill.** As of 2026-09-25: 949 pages, submissions to about
2026-07-19, play dates to 2026-07-26; the download continues. Backfill is heavy: from about
page 20 on, every page holds runs played as far back as March, because players upload their
history in bulk (the SlayTheStats mod uploads a whole local history, oldest first). The
notebook measures the upload lag (section 2); record the numbers here after the rerun on the
finished snapshot. Recent builds are under-counted until the snapshot is complete.

**Uploader groups.** `_sts`-tagged uploads (SlayTheStats mod users) differ from the rest:

| Build | Cards | sd of per-card z | Spearman | typical gap (pick rate) |
|---|---|---|---|---|
| v0.103.2 (before community tooltips) | 400 | 3.76 | 0.93 | 0.046 |
| v0.107.1 (after) | 400 | 4.95 | 0.86 | 0.074 |

The groups already differed before the mod showed community stats, and the same cards lead
both builds (tagged players pick Setup Strike, Perfected Strike and Flick Flack less,
Footwork and Well-Laid Plans more), so this is mainly selection, possibly larger after June
(different builds and upload timing, so not a clean comparison). A typical gap of 5–7
points is as large as many patch effects: pick-rate estimates are made within uploader group
or with it as a covariate, pooled as a robustness check. Tagged players also win about 8
points more (v0.103.2, finished runs).

**Win rates drift within a build.** In v0.103.2 alone (same card versions throughout), the
win rate of finished primary runs fell from April to May in both groups (untagged 0.23 →
0.17, tagged 0.32 → 0.24), and the tagged share fell from ~30% to ~10%. So calendar time
matters beyond build: win analyses need week (or ascension) controls, not only build.
Whether rising ascension explains it is the next check (the notebook now shows mean
ascension per week).

## Known data issues

- **Self-selection.** Uploaders install a companion app or mod; likely more dedicated and
  more skilled than the average player. State as a limitation.
- **`_sts` = SlayTheStats mod upload stamp** (`"slay-the-stats/vX"`; added in
  `SlayTheStats/Community/RunSubmitter.cs`, github.com/giulianoconte/slay-the-stats, not in
  its README). The mod adds it to every run it uploads (opt-in), starting with v1.2.0 on
  2026-06-19, and uploads each user's whole local history, oldest first, at most 200 runs
  per game launch. So tagged runs cover every build but were all submitted after June 19,
  and the tagged share by play date depends on upload timing and on where the snapshot ends.
  It isn't a population measure (the mid-May drop in tagged share in the audit is most likely
  this). Tagged uploaders rank cards differently from untagged ones (v0.107.1: 400 cards,
  Spearman 0.86, per-card z sd 4.95, mean z −0.54). Whether that is selection or the mod's
  tooltips is being checked against v0.103.2, which was played before community tooltips
  existed. Solo runs can't be grouped by player, so part of the gap may be a few heavy
  uploaders. Analyses stratify by uploader group or include it as a covariate.
- **Co-op duplicates.** A multiplayer run gets uploaded once per player (seen in a sample:
  two records with the same run time, same death, timestamps 40 ms apart). The first 5
  pages had 4,641 records and 4,279 distinct (seed, start_time): about 8% co-op
  duplicates. On the first 949 pages: 947,885 records, 727,714 distinct runs; solo runs
  are 79% of distinct runs. `scripts/snapshot_export.py` reports a `dedup` column on this key; raw `runs` counts
  are upper bounds. Whether the unit of analysis is the run or the player-run gets decided
  at parsing (a co-op run has one outcome but several players' choices).
- **Player IDs.** Solo runs use `player_id: 1`. Multiplayer runs carry real 64-bit Steam
  IDs. Hash these in the pipeline; publish aggregates only. Not planning player-level
  analysis. Raw snapshot data is git-ignored and never committed. `spirometry.runs` hashes
  Steam IDs and `player_token` with a keyed hash (HMAC-SHA256, key in `SPIROMETRY_SALT` or
  the git-ignored `.spirometry_salt`); a plain hash of a Steam ID could be reversed by
  enumeration.
- **Beta vs. stable.** Two branches run different card versions at the same time
  (e.g. stable v0.107.1 and beta v0.111.0 in September 2026). Always key on `build_id`.
- **Branch comes from `builds.csv` via `build_id`, never from the run file.** The export's
  records have no `is_beta` field (earlier notes said it was false; it's absent), so
  `scripts/snapshot_export.py --count-only`'s `beta` column is always 0. v0.100.0–v0.103.1
  are beta. v0.99.1 was on beta for three days before stable (2026-03-14 → 03-17), so its
  runs are mostly but not only stable.
- **Some behavior changes come only from bug fixes** and appear in no card field (e.g.
  Bombardment and Howl from Beyond playing from Exhaust after the draw, v0.104.0; Summon
  Forth's Forge order). Others are in the notes but not in card data (Tyranny's trigger
  order, Tag Team, Entrench, Stratagem's pool change). Listed in `behavior_changes.csv`
  and `crosscheck.csv`; without them those cards look unchanged.
- **Offers aren't uniform.** Shops, events, Neow and relic effects (Prayer Wheel, Lasting
  Candy, Driftwood, Orrery) all write into `card_choices`, and a floor can hold several
  screens in one list. Solo shops list only the unsold shelf. See `notes/run_schema.md`.
  Lasting Candy adds a fourth card on some fights only (solo, candy held: 216 three-card
  and 159 four-card combat lists on 2 pages). Every `bought_colorless` card is also in that
  floor's `cards_gained` (468 of 468), so purchases come from `cards_gained` alone. Co-op
  combat lists sometimes have 4 cards with no Lasting Candy on any player (144 on 2 pages;
  cause unknown).
- **Custom and modded runs.** Early builds record custom runs as `game_mode: standard`;
  filter on `modifiers` being empty. Recent pages include modded runs (mod card ids with
  a `-`, BaseLib keys). Some mods leave only a mod character (`CHARACTER.HERMIT-HERMIT`,
  1 run on 2 pages), so the parser flags any quoted id with a `-`. Mod characters don't
  always have a `-` (`CHARACTER.WATCHER`); the audit found non-vanilla characters on 824
  records, so the check is a list of the five real characters (parser 1.1.0 does this).
  Mod enchantments don't always have a `-` either: `ENCHANTMENT.RUNE_OF_CORRUPTION`, with
  amounts of 110,111–123,013, is on three modded runs in the last ~50 local pages (905,
  928, 942; they crashed parser 1.1.0's first full build). The game has 22 enchantments
  (`/api/enchantments`, cached in `reference/raw/enchantments.json`), and game
  enchantments' amounts are 0–25 on those pages, so any other enchantment id is a mod marker
  (parser 1.2.0). On 2 pages fetched 2026-09-25, 3 records carry a non-game enchantment
  (`MULTIPLAYEREXPANDED-FATED`, `UNCAPPEDSPIRE-MULTI_ENCHANTMENT`), all already flagged by
  the `-` rule. `MIDAS` is a game modifier, not a mod marker. Mod events and encounters
  likewise: `EVENT.NINE_TAILED_FOX_EVENT` + `ENCOUNTER.SHANGHAI_JIAOTONG_ENCOUNTER` in the full
  local build (6 solo event-fight lists, no other marker). Parser 1.3.0 flags any
  `EVENT.`/`ENCOUNTER.`/`MONSTER.` id outside the game's lists (stable + every beta + the
  changelogs' added/removed ids, see Reference data). The stable list alone isn't enough:
  on the first export page (fetched 2026-09-25) it would flag 223 of 1,000 records for
  removed content (`ENCOUNTER.DOORMAKER_BOSS`, `ENCOUNTER.TOADPOLES_NORMAL`, `MONSTER.DOOR`,
  `MONSTER.DOORMAKER`); with the full lists that page has 0. That page is early data with no
  modded runs at all, so how many runs the rule newly flags is for the full build
  (`build_info.runs_mod_entity_only`). The rule checks against the union of every cached
  list, which works while official content only gets added or removed. When official act 4
  (or other new content) ships, re-cache the lists for the new builds and check each run
  against its own build's lists, with a backstop (act 4 content on a build before its
  release = modded), so a mod id that collides with a new official id doesn't un-flag
  earlier modded runs. Audit counts (records, 949 pages): `save_dict_*` 13,164, mod modifier
  5,233, mod card 2,532, mod character 824, mod acts 1,008.
- **Treatment timing.** Assign builds from each run's own `build_id` and `start_time`, not
  `submitted_at` — players often upload their whole history folder at once (the
  SlayTheStats mod does exactly that). This also means early builds can keep gaining runs
  late in the export.
- **Runs dated before their build's release.** 5,566 runs (~0.6%) start before their build's
  `release_date`, by 1 day up to ~4 months (median a few days). Most likely saved on the old
  build and finished after an update, so their early floors may be on the old card
  versions. Filter: start date (UTC) ≥ release date (`runs.before_release`). Runs that
  cross an update on the release day itself can't be detected.
- **Non-release builds.** Pre-early-access playtest builds (v0.84.0–v0.97.0, 25 runs),
  release candidates (`-rc.N`, 13 runs) and `NON-RELEASE-VERSION` (286 runs) are in the
  export but not in `builds.csv`. Dropped (`runs.released = false`).
- **Old builds keep being played.** Every stable build has runs dated months after it was
  replaced (v0.98.x into July). The build still sets the card versions, so this doesn't
  affect treatment assignment.
- **Cheated / modded runs.** No cheat flag in the export. Audit (primary runs): 70 of
  98,371 wins took under 15 minutes, and two look impossible (7,355 gold with 39 relics; an
  empty deck). No win before act 3. Too few to matter for pick rates: flagged, not
  filtered. Modded runs are filtered via the mod markers above.

## Analysis ideas

The key fact: **which cards get offered is decided by the game's RNG**, and the run file
records every offer, picked or not. So, conditional on game state, being offered a card is
close to randomized. That supports:

1. **Offer rate as a check.** A buff shouldn't change how often a card is offered, only how
   often it's picked. If offer rates move after a patch, something else changed.
2. **Intent-to-treat.** Effect of being offered card X on winning, before vs. after a patch.
3. **Effect of picking, using the offer as an instrument.** Selection-corrected card
   strength — the A/B-test-with-non-compliance setup.
4. **Difference-in-differences.** Changed cards vs. unchanged cards for the same character,
   across the same patch window. Controls for players improving and for meta drift.
5. **Dose-response.** Many small buffs and nerfs of known size: model effect size against
   change size. Separate numeric tweaks from reworks.
6. **Spillovers.** Nerfing one card shifts picks to its substitutes. SUTVA violation, but
   also a finding: patches move the whole meta.
7. **Staggered rollout.** Beta gets changes before stable. Staggered-adoption DiD.
8. **Survival.** Floor of death as a survival curve; hazard by encounter to find the real
   difficulty walls, and how patches to enemies/bosses moved them.
9. **Hierarchical Bayes.** Card effects with partial pooling across characters and
   ascension levels, so rarely offered cards don't get extreme estimates.
10. **Metric design.** A selection-corrected "card strength" metric as a headline product.

## Deliverables (eventually)

- GitHub repo, same shape as Flashpoint and Clickworthy: `pyproject.toml`, `src/` package,
  numbered notebooks, DuckDB data layer.
- A dashboard (Streamlit or Observable Framework — undecided): card strength by build,
  patch-by-patch effects, encounter difficulty, event choices.
- A portfolio card on pmacias.github.io.

## Repo and environment

- Current contents: see the repository table in `README.md` (`src/spirometry/`,
  `scripts/snapshot_export.py`, `reference/`, `tests/`, `notes/`, plus PLAN/README/CLAUDE).
- Snapshot command (moved from the repo root; behaviour, output folder `sts2_snapshot/`
  and checkpoint `sts2_snapshot/cursor.txt` unchanged — paths are relative to the working
  directory, so run it from the repo root): `python scripts/snapshot_export.py`. A download
  started with the old path keeps running; resume it with the new path.
- Environment: dependencies live only in `pyproject.toml` (core: `requests`, and `duckdb`
  and `pyarrow` for the run tables; an `analysis` extra — pandas, numpy, matplotlib,
  jupyter, scipy, pyfixest — for the notebooks and Phase 5). Locally a mamba env with `pip install -e .`; plain `pip install -e .` in
  cloud sessions and CI. No separate environment.yml / requirements.txt. `src/` layout
  (`[tool.setuptools.packages.find] where = ["src"]`).
- Cloud session check passed: spire-codex.com reachable, `pip install -e .` works,
  Python 3.11.
- Data (`sts2_snapshot/`, `data/`, `*.duckdb`) is git-ignored and stays local (see network
  fallback below).

## How the work gets split

- **CC cloud sessions (the $100 promo credit):** hands-off pipeline work — fetching and
  snapshotting the export, parsing nested JSON into DuckDB tables, deduplication, joining
  patch history, a GitHub Actions workflow for refreshes, dashboard scaffolding.
- **Me, on regular usage:** the analysis and the plots. I want to run and look at the
  results myself, and these are the parts I need to be able to explain in interviews.
- **Network fallback:** the raw snapshot stays local and is never published. Cloud
  sessions develop against a page or two of the export that they fetch themselves
  (`python scripts/snapshot_export.py --pages 1`), and the finished pipeline runs locally on the
  full snapshot.

## Open questions / next steps

1. Run the full snapshot (in progress locally; 949 pages so far, see Data sources).
   First audit pass on those pages: every build from v0.98.1 on except v0.99.0, v0.103.1,
   v0.105.0 and v0.109.1 has ≥2,000 primary runs; 40 of the 47 numeric-tweak cards have
   4k–30k primary offers on each side of their stable change (4 are never offered as
   rewards, 3 have under ~120).
2. ~~Verify the patch history endpoints.~~ Done — `notes/patch_history.md`.
   ~~Build the card change table and the version → branch → date table.~~ Done —
   `reference/`. ~~Label the text-only changes.~~ Done — `text_only_labels.csv`.
   ~~Cross-check against the official patch notes.~~ Done —
   `notes/patch_notes_crosscheck.md`. ~~Decide and apply the four tweak/rework
   relabels, the notes-only rows and the artifact labels.~~ Done (see Reference data).
   Next: review `excluded_fields.csv` and `history_unmatched.csv`; extend to relics,
   monsters, and encounters.
2b. ~~Document the run file structure.~~ Done — `notes/run_schema.md`, with a proposal
   for the `runs` and `card_offers` columns and the decisions they need.
3. ~~Estimate total snapshot size and rate-budget cost per page.~~ Done — see Data sources.
4. Message the Spire Codex maintainer: describe the project, ask about the academia tier
   and whether it raises the export budget, confirm they're fine with the use.
5. ~~Push the repo to GitHub, then test whether a CC cloud session can clone it and reach
   spire-codex.com.~~ Done — passed.
6. ~~Claim the cloud credit (`/claim-credit` in CC) before October 7, 2026.~~ Done.
7. Keep Clickworthy moving in parallel (currently on Stage 1).
