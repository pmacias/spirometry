# Spirometry

Measuring what Slay the Spire 2's balance patches actually did.

Status: Phase 5, pick-rate results and the anticipation check rerun on the 1,513-page
tables; win-effect tooling built, not yet run on the full tables.
The pipeline is complete through Phase 4 (reference tables, run tables, treatment tables).
The full snapshot is still downloading; the run tables are built from the first 1,513 pages
(submissions to about 2026-08-30, parser 1.7.0, built 2026-09-29). Pick-rate results for the
numeric tweaks are under "Phase 5 results"; the design and the reasoning behind it are in
`notes/phase5_deck_v3.pdf` (made for the first pass; its numbers are from the 949-page
tables).

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
    of the first 1,393 had 466 runs). Probably server-side filtering after the page is cut;
    the cursor still advances normally.
  - Export is ordered oldest submission first, and the order is the same from any client
    (Mac and cloud session agree). The first 5 pages covered v0.98.0–v0.103.2. That
    includes beta builds (v0.100.0–v0.103.1 are beta per `reference/builds.csv`; 30% of the
    first two pages). The earlier "no beta" reading came from counting `is_beta`, a field
    the export records don't have (`notes/run_schema.md`).
  - `start` / `end` bound submission time, not play time: a page from `start=2026-09-01`
    still had 16% of its runs on v0.98.x–v0.99.1.
  - Snapshot so far (2026-09-29): 1,513 pages, 1,511,837 records (1,435,841 after dropping
    the repeats below; 1,100,090 distinct runs), covering submissions up to about 2026-08-30
    (the date in the saved cursor, 2026-08-30 14:58 UTC; the newest play date in the
    tables is 2026-08-30 14:57 UTC). 119,979 records were added since the 1,393-page state.
    Size on disk not rechecked (1,393 pages: 4.6 GB, ~3.3 MB per page). The total is still
    unknown; the site's ~1.8M figure would mean a few hundred more pages. The download is
    paused on the rate limit until it resets.
  - Pages 873–948 were downloaded twice: two download processes ran at once (the older
    one woke from a rate-limit sleep and refetched the same cursor chain into the same file
    numbers, so the overwritten files got identical content), and the 2026-09-26 restart
    resumed from the slower one's cursor. The repeats are files 949–1024 (0-based), 75,996
    records, identical to 873–948 in records and order except that the re-downloads carry
    `player_token`. Both the parser and the audit extractor drop them on `run_hash`,
    keeping the first copy (so the kept copies have no token). The download log shows no
    other overlap; since the lock file was added, a crash can only re-fetch a page, never
    skip one (the page is written before the cursor). Records carry no submission time, so
    gaps between pages can't be checked directly.
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
On the 1,393-page snapshot the key is on every record of pages 1025 on (about 28% of
records) and on none before; the top uploader made 1,284 solo runs. (Not recomputed on the
1,513 pages; the top 10 uploaders by solo runs there have 686 to 1,666 runs each.)

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
- `beta_exposure.csv` — one row per solo-estimable numeric tweak (43; 3 upgrade-only,
  flagged), built by `python -m spirometry.exposure` from `tweak_sizes.csv`, `windows.csv`
  (`members`), `change_events.csv`, `change_event_fields.csv` and `builds.csv`:
  `first_beta_build` / `first_beta_date` (the earliest `first_beta` among the card-patch's
  member events: for Parry, Untouchable v0.103.2 and Reflect, revised on a later beta, the
  first step), `stable_build` / `stable_date`, `lead_days` (stable − first beta),
  `step_field` (the main field; the upgrade field for upgrade-only tweaks), `n_beta_steps`
  and `beta_steps` (`build:date:old>new; ...`), `member_events`, `revised_or_reverted`
  (from `change_events.status`), `other_events_after_first_beta` / `other_event_ids` (the
  card's other events, any kind, from the first-beta date to before the stable date),
  `beta_timing_note` (member field rows whose beta placement the treatment tables mark as
  uncertain). Blank where a source doesn't say. Every beta step matches Phil's reading of
  the same files (2026-09-29); no tweak has other events in its lead time and none has an
  uncertain beta placement. 21 of the 26 first-patch tweaks first appeared on v0.100.0
  (2026-03-19), two days after v0.99.1; lead times are 7–28 days (first patch) and 14–56
  days (second).

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
- `run_players`: one row per record × player (`player_hash`, `character`,
  `final_deck_size`, `final_relic_count`, `deck_size_start` from parser 1.7.0: the
  starting deck implied by the final deck, see `card_offers.deck_size_before`).
- `card_offers`: one row per `card_choices` entry, every source, with `source`, `set_idx`
  (combat/elite/boss/`event_combat` screens; NULL when the list can't be split), `set_picked_any`,
  `upgraded`, `enchantment`, `enchantment_amount` (as recorded, unclipped), `in_card_list`,
  `is_mod_card`, `is_mod_enchantment`. `card_id` has no `CARD.` prefix. Parser 1.7.0 adds
  `deck_size_before`: the player's deck size at the start of the offer's floor = starting
  deck + cards gained − cards removed on earlier floors. The starting deck is the final
  deck − every `cards_gained` + every `cards_removed` over the run; `cards_transformed`
  swaps one card for one and doesn't count. Gains and removals on the offer's own floor
  (its reward pick, a shop removal) count from the next floor, so the second screen of a
  two-screen floor has the same value as the first. For description (pick rate against deck
  size), not as a control: deck size is partly caused by earlier picks.
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
- Views: `runs_dedup` (first record per `run_key`, with `n_copies`, and from parser 1.7.0
  `retried`: the `run_key`'s copies differ in `win`, `floors_reached` or `was_abandoned`,
  most likely a restored save played on; co-op copies and exact double submissions agree
  on all three), `card_offers_dedup`,
  `primary_offers` (the primary population below: solo, no modifiers, not modded, released
  build, not before release, Neow start; combat/elite/boss rewards plus event-then-fight
  floors with `event_fight = true`; no mod cards; abandoned runs kept with
  `was_abandoned`; carries `uploader_tag` for uploader groups). From parser 1.5.0
  `primary_offers` (and so `offers_with_version`) takes its runs from `runs_dedup`: a solo
  run uploaded twice (same `run_key`, different `run_hash`) counts once, as the record
  `runs_dedup` keeps (first by page, line). The population filters apply to that record,
  and its `uploader_tag` is the one the offers carry. `primary_offers` also carries
  `retried` (parser 1.7.0); pick-rate tables keep retried runs (one copy), win tables
  (`spirometry.wins`) drop them.
- `build_info` also counts runs not released, before release, not starting at Neow, modded,
  tagged, and with `player_token` absent/present, runs with a mod event/encounter/monster
  (`runs_mod_entity`) and runs flagged by that marker alone (`runs_mod_entity_only`), plus
  event-fight lists by length. Parser 1.5.0 adds `solo_run_keys_multi_record` (solo
  `run_key`s with more than one record) and `primary_offers_dedup_removed` (primary offer
  rows the extra records would add without the dedup). Parser 1.6.0 adds the key
  collisions it now separates: `old_run_keys_split` (`(seed, start_time)` pairs, the old
  key, that now hold more than one `run_key`), `run_keys_split_from_old_key` (the
  `run_key`s in them) and `solo_old_run_keys_split` (the pairs split among solo records).
  Parser 1.7.0 adds `solo_run_keys_retried` and `primary_run_keys_retried` (retried
  `run_key`s among solo records / in the primary population: the runs win analyses drop),
  and `deck_start_checked` / `deck_start_nonstandard` (solo records without modifiers or
  mods, and those whose `deck_size_start` isn't the game's starting deck: 10 cards, Silent
  12, plus Ascender's Bane from ascension 5).

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
On the 1,513-page tables: 124 of 869,813 solo `run_key`s have more than one record (0.01%);
4 differ in the SlayTheStats tag; the copies differ in win (25), floors reached (81) or
abandonment (37). See "Phase 5 results".
Parser 1.7.0 on 2 pages fetched 2026-09-28 (`start=2026-05-01` and `start=2026-07-01`,
2,000 records): 0 retried `run_key`s (0 solo multi-record keys at all). On the 1,393-page
tables `primary_run_keys_retried` = 72 (74 on the 1,513 pages). Deck size: the implied
starting deck is the game's (10, Silent 12, +1 Ascender's Bane from A5) on all 1,405 solo
records without modifiers or mods; every A5+ run whose start was one card larger had
Ascender's Bane in its final deck. Custom runs (e.g. Sealed Deck) start smaller. 53 co-op
players have an implied start of 0 or 1 (an empty or near-empty final `deck` in the
record; not checked further, co-op is outside the primary population). In
`primary_offers`, `deck_size_before` runs 8–156 (median 19) and rises from about 11 at
floor 2 to about 31 at floor 44.

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
  `build_id`, `uploader_hash`, `set_picked_any` (the player took a card on the offer's
  screen; NA for lists that couldn't be split; added to the default columns for
  `picked_screens_only`). Categorical columns to keep memory down. `extra_cols=True` adds
  where the offers come from: `source`, `map_point_type`, `floor`, `event_fight`,
  `list_len`, `set_idx` (for breaking down the extra offers of Patter, Sculpting Strike and
  The Scythe by act, floor type and event fights). `control_scope="all"` / `"other"` (also
  on `load_block_data`) adds the other four characters' cards that are unchanged between
  the blocks, each from its own character's runs (`"other"` keeps only the changed cards of
  the treated color, the possible treated cards); the filter is in the DuckDB query.
- **Control group.** `control_cards(card_patch_id, drop_behavior_flags=False, df=...,
  control_scope="color")`: the cards seen in the window in the scope's colors, minus the
  treated card, minus cards changed between the before and after blocks (and bug-fix-flagged
  cards if asked). Scopes:
  - `"color"` (default, the definition used for every result so far): the treated card's
    color, minus `windows.csv`'s `control_exclusions` (and `control_behavior_flags`).
    Same-color controls share offers, screens and players with the treated card, which
    absorbs character-level shocks, but they compete with it for picks.
  - `"all"`: the five character colors, the treated color included.
  - `"other"`: the other four characters' colors only (no shared runs or screens).

  For `"all"` and `"other"`, `window_changes(before_builds, after_builds)` gives the
  changed and flagged cards of every color from `card_versions.csv`, by the rule
  `windows.csv` uses for its same-color columns (it reproduces them on all 137 card-patch
  windows). Colorless, token, status, curse, event and quest cards are controls under no
  scope, and a card offered outside its own character's runs is not loaded, so `"all"` is
  `"color"` plus `"other"` (decision log). The fit is the same under every scope (no color
  or character terms), so under the wider scopes `block^group` pools the characters: a
  shock to the treated character alone is not absorbed. That difference is what comparing
  the scopes measures. `control_pool_sizes(con, scopes=...)`: control cards, control
  offers (before, after, and the treated color's share) and treated offers per tweak and
  scope, as loaded (before `fit_did`'s filters), from one aggregate query per window.
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
  unchanged), `control_scope` (above; `drop_shared_screens` can only drop same-color
  controls, `drop_behavior_flags` drops flagged controls of every color in the scope). Returns beta (probability units), se (clustered by `run_key`, the main
  error; ci95 uses it), se_hc (heteroskedasticity-robust, pyfixest `"hetero"`, same fit:
  the comparison for clustering), se_iid, ci95, `max_week_after` (the setting, None when
  unset) and `after_week_max` (latest after-block week in the fit data), counts and the
  four pick rates. pyfixest drops singleton fixed-effect cells;
  `n_singletons_dropped` counts them. Two robustness options (both passed through by
  `run_all`, both reported back in the result): `card_act_fe` (card_id^upg^act in place of
  card_id^upg and the act term: each card its own act profile, for cards whose value
  depends on when in the run they're offered) and `picked_screens_only` (only offers on
  screens where the player took a card, `set_picked_any`; offers from unsplit lists leave
  too. Most of the fall in pick rate through a run is whether to take anything at all, so
  this estimand is the choice among cards, free of that deck-size effect. Applied after
  `drop_shared_screens`, which sees screens as offered).
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
  (e.g. an empty block) gets the reason in `error`. `control_scope` loads and fits with
  that scope; every row carries `control_scope` and `n_control_cards` (controls with an
  offer in the fit data). Saved fits made before this have neither column (they are
  `"color"`).

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
Not run on the 2 fetched pages (no v0.103.2 runs); run on the full tables since (see
"Phase 5 results").
New options (synthetic): a card picked 30 points more in act 3 whose after-block offers
shift toward act 3 shows a fake effect with one act term and none with `card_act_fe`;
`picked_screens_only` keeps exactly the screens with a pick. On 2 pages fetched 2026-09-28
(`start=2026-05-01`, `start=2026-07-01`) the first stable window runs end to end with
`extra_cols`, `card_act_fe` and `picked_screens_only`, and the smoke test passes.
Control scope (synthetic, three characters of 8 cards, 2,000 runs per character and
block): `"color"` gives the pre-change numbers to 1e-9 and the same fit on data loaded for
`"all"`. Every card of the treated color picked 2 points more after the change, true effect
0: `"color"` −0.002 ± 0.006, `"all"` 0.014 ± 0.006 (expected 0.02 × (1 − 6/21) = 0.014, 6 of
21 controls of the treated color), `"other"` 0.021 ± 0.006 (expected 0.02); over six seeds
`"all"` − `"color"` is 0.012 to 0.017. A card changed in another color is neither a control
nor loaded; colorless cards and a card offered in another character's runs never enter.
Not run on real data.

**Anticipation check** (does the stable "before" period already contain the change?). Every
change was on a beta build, with public notes, before its stable release; for 21 of the 26
first-patch tweaks that is two days after v0.99.1 shipped. If stable players started picking
differently when the beta appeared, part of the effect sits in the main design's before
block and the DiD understates it. The check stays on builds where stable players still
have the old card and splits them at the card's first-beta date:
- `old_version_builds(card_patch_id, widen=True)`: stable builds on which every card of the
  character has the same card version (`card_versions.csv`) as the window's before builds.
  With `widen` (default), such builds that are before or after builds of some card-patch
  window are added: v0.103.2 joins v0.103.3 for the second patch (identical versions on
  every card of every color, checked in the tests); v0.98.x, identical to v0.99.1 but
  outside every window per the audit, stay out, so the first patch uses v0.99.1 only.
  Also returns the cards whose bug-fix behavior events differ between those builds (Bad
  Luck, Stardust and Summon Forth between v0.103.2 and v0.103.3), which the check drops
  from the controls by default (`drop_behavior_diff`).
- `load_anticipation(con, card_patch_id, ...)`: those builds' offers, `block` = before /
  after the first-beta date by the run's UTC start date (as `before_release`), `week` from
  that date. `until_stable` (default) drops runs started on or after the new stable's
  release (stragglers on an old build, when the new card is out). `main_postbeta_share`:
  the share of the treated card's offers in the main design's before block (all dates)
  from runs started on or after the beta date.
- `anticipation_check(con, card_patch_id, ...)`: `fit_did`'s model with the split at the
  beta date, `picked ~ treat_postbeta | (same fixed effects)`, clustered by run, controls as
  `control_cards`. Returns `beta_postbeta`, se, ci, treated offers, all offers, runs and
  days (distinct dates with a treated offer) on each side, first and last day, treated
  offers per build and side, `status` / `reason`: `uninformative` when a side has fewer
  than `min_offers` (2,000) treated offers or `min_days` (3) days (the fit still runs when
  both sides have data; with none on a side there is no fit). Against the main design:
  `beta_main` / `se_main` (refit, or passed in), `ratio_to_main` = beta_postbeta /
  beta_main, `total_implied` = beta_main + main_postbeta_share × beta_postbeta (the total
  move if the pre-release move is real: the main before block already carries that share
  of it), `share_before_release` = beta_postbeta / total_implied; both ratios blank unless
  |beta_main| > 2 se. `ratio_to_main` is not the share of the total move: with anticipation
  the main DiD is itself too small. Diagnostics for drift: `pre_slope` (weekly slope of the
  gap before the beta date) and `week_gap` (mean week of post-beta minus pre-beta treated
  offers).
- `anticipation_weekly(...)`: `fit_event_study` on the same data, weeks from the beta date
  (week −1 the reference), range −6 to +8 clipped to where the old builds have data;
  `week_start` and `first_beta_date` for a plot with a line at the beta date.
- `anticipation_all(con, main=None, ...)`: every row of `beta_exposure.csv`, one data load
  per (character, old builds), upgrade-only tweaks on upgraded offers (flagged); `main` = a
  `run_all` result to take `beta_main` from instead of refitting. Options echoed as
  columns; flat and parquet-ready.

**Limitation: a steady drift looks like anticipation.** The split compares two periods, so
a trend in the treated card that runs through the beta date gives `beta_postbeta` ≈ slope ×
`week_gap` with no jump anywhere. Nothing corrects it. Read the weekly table (a straight
line through the beta date, not a step) and `pre_slope`, which is noisy with the few
pre-beta weeks the real data have.

**Date vs. build.** For the second patch the two sides are largely different builds:
before the beta date is v0.103.2 only; after it, the rest of v0.103.2 plus all of v0.103.3,
which also brought bug fixes and a new player mix. The fixed effects have no build term, so
a build-level change in how the treated card is picked, relative to the controls, shows up
as anticipation. `treated_offers_by_build` shows the mix; `builds=["v0.103.2"]` keeps the
comparison within one build. The first patch's sides are both v0.99.1 (no such issue),
but its pre-beta side is 2 days for 21 tweaks. Old builds are played for weeks after they
are replaced; `until_stable` drops runs started after the new stable is out, and the split
is by start date, never by build.

Checked on synthetic offers (`tests/test_anticipation.py`; old build 03-01 to 04-09, beta
03-21, new stable 04-10, 4,000 old-build runs, a 12-point move D):
- Linear ramp from the beta date to the stable date: `beta_postbeta` 0.051 ± 0.007
  (truth D/2 = 0.06), `beta_main` 0.100 ± 0.005 (truth 0.75 D = 0.09: the before block is
  half post-beta), `total_implied` 0.125 (truth 0.12), `share_before_release` 0.41 (truth
  0.5), `ratio_to_main` 0.51 (truth 2/3; 0.51–0.62 over three seeds).
- Change at the stable date only: `beta_postbeta` 0.000 ± 0.007, `share_before_release`
  0.00, `beta_main` 0.112 ± 0.005.
- Steady drift of 0.01 a week, no jump: `beta_postbeta` 0.030 ± 0.007 (= slope × week_gap
  2.96), `share_before_release` 0.44: indistinguishable from anticipation by these
  numbers. `pre_slope` 0.003 ± 0.006 (three pre-beta weeks can't see it); the weekly
  table's coefficients lie on a line of slope ≈ 0.01.
- A beta two days after the old build: `uninformative`, "2 days pre-beta (< 3)"; no data
  before the beta date: no fit, reason "no treated offers in the before block".
Rough count (not yet verified): with each build's offers (above) spread evenly over its
time as the current stable and an equal share per card of a color, 17 of the 43 would be
informative (3 first-patch: Glitterstream, Refine Blade, Leading Strike; 14 second-patch);
rare cards are offered less than that, so probably fewer. On 2 fetched pages (2026-09-29)
all 43 run end to end and all are uninformative (1–75 treated offers a side); the pages
have v0.103.2 runs to 2026-05-18 and none on v0.103.3.

## Results export (`spirometry.export`) and dashboard

`python -m spirometry.export --analysis data/analysis --out results [--db runs.duckdb]` reads
the files notebooks 02 and 03 save and writes aggregate tables for `dashboard/app.py`:
`pick_rate_did.csv` (one row per tweak: main fit, weeks 0–3 fit, tweak size, log-odds
versions, clearly nonzero, toward the change), `flags.csv` (offer-rate flags, pre-trend
slope, upgrade-only placebo, second-patch before-block variants), `weekly.csv` (event study
per week and block), `dose_response.csv` (the four meta-regression models of notebook 02
section 8, both horizons; `spirometry.meta`), `robustness.csv`, `anticipation.csv` and
`meta.json`. Column definitions are in the module docstring. No run-level rows or uploader
identifiers; the export checks every table before writing.
- Notebook 02 does not save its offer-rate table (section 3's `orc`), so `flags.csv`'s
  offer-rate columns are blank until `data/analysis/offer_rate.parquet` exists.
- `build_info` records pages parsed, not a submission end date: `meta.json`'s snapshot
  end date is blank unless given with `--snapshot-end`.
- Tested on synthetic saved fits with the notebooks' column layout
  (`spirometry.sample_results`, `tests/test_export.py`); not yet run on Phil's saved fits.
  `results_sample/` holds the synthetic export the dashboard falls back to.

## Win-effect tooling (`spirometry.wins`)

Phase 5 steps 4–5: within a build, does picking card X make a run more likely to win?
Tables only. Input: a read-only connection to `runs.duckdb` (parser 1.7.0 or later:
`runs_dedup.retried`, `run_players`, `offers_with_version`) and `builds.csv` (week) and the
cached card list (colors).

**Design.** Players pick cards because their run is going well (or badly), so runs that
picked X aren't comparable with runs that didn't. Which cards a reward screen offers is
the game's RNG: the offer is an experiment with non-compliance. Intent-to-treat (ITT) = win
rate of runs offered X against runs not offered X; the IV estimate = ITT / (how much being
offered raises picking X). "Offered X anywhere in the run" is not random: runs that survive
longer see more reward screens, so they are offered more cards and also win more. So only
the **first K reward screens** of each run count (combat, elite, boss and event-fight
rewards, in floor order then `set_idx`; default K = 3). Nearly every run reaches them, and
within them the offers are the RNG's. A run is `offered` when X was on any of its first K
screens and `picked` when it took X on one of them. **The treatment is "took X on one of
the first K screens"**, not "has X at some point": later rewards, shops and events don't
count, so a run not offered X early that gets it later has `picked` = 0. The estimate is
the effect of getting X early, against what those runs did otherwise (including getting it
later). The survival still in the design is the share of runs that reach screen K
(`reach_share`); by default runs that don't are left out. On 2 fetched pages
(2026-09-28): 97.3% of 1,277 runs reach screen 3 (per build × character 87.5–100%). A
synthetic test shows the point of the design: with no effect and later screens reached
mostly by skilled runs, "ever offered" gives a clearly positive ITT and the first 3
screens don't.

**Runs that don't reach screen K** (`include_short_runs=False`, the default). Every such
run died before screen K, so it lost, and it had fewer screens on which to be offered X.
Keeping them with their unreached screens counted as "not offered" puts the early deaths
mostly in the "not offered" group, for every card: a fake positive ITT. In a synthetic
null with 16% of runs dying before screen 3 (less skilled runs more often), keeping them
gave ITT +0.08 (z ≈ 13) and IV +0.19; the default gave ≈ 0. On the 2 pages, 35 of 1,277
runs don't reach screen 3 and all 35 lost. Dropping them biases the estimate only if an
early offer changes the chance of reaching screen K; the default is then the effect among
runs that reach screen K. For the total effect, deaths before screen K included, load the
data with **K = 1**: every run that was offered anything reached screen 1, so nothing is
selected after the offer (fewer offered runs: less power). Synthetic check: when an offer
of X on screen 1 or 2 raises the chance of dying before screen 3 by 15 points (and X does
nothing else), the default gives ≈ 0 (no fake effect among runs reaching screen 3) and
K = 1 gives about −0.03, the total effect.

**Population.** Primary runs (`runs.PRIMARY_RUN_FILTER` on the record `runs_dedup` keeps),
minus abandoned runs (no outcome; abandoned at Neow included) and retried runs
(`runs_dedup.retried`). Runs whose first K screens include a list that couldn't be split
into screens (`ambiguous_screens`) are kept in the tables and left out of the fits. On the
2 pages that is 0 runs: the 13 unsplit lists in non-abandoned primary runs all come at
screen 8 or later (12 are 4-card lists with none of Lasting Candy, Prayer Wheel, Driftwood
or White Star; 1 a 7-card list with Driftwood; no relic in common beyond starter
relics). Runs without ascension, or on a build with no release date in `builds.csv` (no
week), are left out of the fits.

**Tables.** Built in DuckDB (screens numbered with a window function, one aggregate per
(run, card)); pandas gets one row per run and one per (run, card offered on the first K
screens), categorical keys, for one character (or all) and a list of builds. A function,
not a view: a view would still be materialised whole by the notebook, while the function
returns only the selection.
- `early_runs(con, character, builds, K=3)`: one row per run: `run_key`, `build_id`,
  `branch`, `character`, `ascension`, `group` (tagged / untagged as in `did`), `week` (whole
  weeks from the run's own build's release date), `start_time`, `win`, `floors_reached`,
  `n_screens_reached` (≤ K), `ambiguous_screens`, `screen_sources` (e.g.
  `combat>combat>elite`).
- `early_offers(con, character, builds, K=3)`: one row per (run, card) offered on the first
  K screens: `offered_screens`, `offered`, `picked`, `first_screen` (1..K),
  `upgraded_offer`, plus the run columns.
- `load_early(...)`: both at once (offers without the run columns repeated), the input to
  the estimators. `reach_share(runs)`: runs, runs reaching screen K and their share, and
  ambiguous runs, per build and character.

**Estimators** (linear probability models with pyfixest, errors heteroskedasticity-robust
(`"hetero"`, HC1), not clustered: every fit has exactly one row per run, since
`runs_dedup` has one record per `run_key` and it joins `run_players` on player 0; the load
and `run_frame` refuse a table with a repeated `run_key`):
- `itt(data, card)`: `win ~ offered | build^group + ascension + week^build`. Returns beta,
  se, raw win rates offered / not offered, `n_runs` (after pyfixest's singleton drop),
  `n_offered`, `n_picked`.
- `first_stage(data, card)`: `picked ~ offered`, same fixed effects. Coefficient, se, F
  (robust Wald F = (coef/se)², one instrument), `weak` (F < 10), raw pick rate of offered
  runs. Runs not offered X can't pick it on those screens (one-sided non-compliance).
- `iv(data, card)`: 2SLS `win ~ 1 | fe | picked ~ offered`. The effect of taking X on one
  of the first K screens for runs that take it when offered (with one-sided
  non-compliance, the effect on those who took it). Also returns the first-stage F.
- `naive(data, card)`: `win ~ picked | fe` on all runs, the confounded comparison, for
  contrast only (`among_offered=True`: took it vs. passed on it).
- `run_all_cards(con, character, builds)`: all four for every card of the character's
  color with at least `min_offered` (500) offered runs among the fit's runs, one row per
  card, one data load; a failed fit gets `error`.

Fixed effects: build^group (win rates differ by build and uploader group; tagged players
win about 8 points more), ascension (difficulty), week^build (win rates drift within a build
over calendar time; see Audit decisions). In the formulas they appear as `build_group`,
`asc`, `build_week` (precomputed combined columns).

**`screen_mix`** (off by default; Phil decides after the full-table results). The offer is
random only given the screen type: elites offer rarer cards, and taking an early elite is a
choice that may track skill. On the 2 pages, runs with an elite among their first 3
screens saw about 2–3.5 times as many Rare offers there (Regent 0.25 against 0.072 per run,
Necrobinder 0.154 against 0.076), and the same number of Commons and Uncommons. The early-
elite share doesn't rise with ascension there (9.8% at A0–4 and at A5–10). Synthetic
check: when skilled runs take early elites more often and elites offer a rare card ten
times as often, a rare card with no effect shows ITT +0.057 (z ≈ 9) and IV +0.14 without
`screen_mix` and ≈ 0 with it; its error bars widen ×1.10 (ITT) and ×1.23 (IV). A common
card is ≈ 0 both ways (slightly negative without it: elites displace it), error bars
unchanged. On the pages, the two versions differ by a median 0.04–0.05 SE for Commons and
Uncommons (no Rare had enough offered runs to fit).

**Options** (every estimator; `run_all_cards` passes them on): `K` (a check: screens are
counted when the data is loaded, so a different K means `load_early(..., K=...)`),
`include_short_runs` (keep runs that reached fewer than K screens, unreached screens as
not offered: biased upward, see above; a check only), `group` (within one uploader
group), `pooled_groups` (no group terms), `screen_mix` (adds the first K screens' sources
as a fixed effect: elites offer rarer cards and taking an elite early is a choice; on the 2
pages 9.6% of runs had an elite among their first 3 screens).

**What the IV estimate means.** Being offered X on a screen also means not being offered
the card it displaced, and a run not offered X early can still take it later; the estimate
is the effect of taking X early against what those runs would otherwise have done (take
another card or skip, or get X later). It also conditions on reaching screen K (see above;
K = 1 is the check).

Checked on synthetic runs (`tests/test_wins.py`, a hidden skill that raises both picking
and winning, 20,000 runs): with a planted effect of +0.10 the IV recovers it within 2 SE,
naive is biased upward by more than 3 SE, and ITT ≈ effect × first-stage coefficient; with
no effect IV ≈ 0 and naive stays positive; a card almost never taken gives F < 10 and the
flag. On 2 fetched pages it runs end to end (smoke test); the estimates mean nothing at
that size.

### Strength change across a patch (`spirometry.strength`)

Phase 5 step 5, for research question 3: after a patch, is taking card X on one of the
first K reward screens worth more or less for winning than before, compared with the
character's unchanged cards? Tables only. Same input as `spirometry.wins`, plus
`windows.csv` (`level = card_patch`) and `tweak_sizes.csv`.

- `block_estimates(data, cards, ...)`: `wins.itt`, `first_stage` and `iv` for a list of
  cards on one block's `load_early` data, one row per card (the run frame is built once;
  the numbers equal the `wins` functions', tested). A card with fewer than `min_offered`
  (500) offered runs, or whose fit fails, gets blank estimates and a `reason`; `weak`
  (F < 10) is reported, not acted on.
- `strength_change(con, card_patch_id, ...)`: loads the treated card's character once for
  the window's `before_builds` and once for its `after_builds`, fits the treated card and
  every control (`did.control_cards`, `control_exclusions` applied, color cards offered in
  either block) in each block, and returns `Strength(blocks, changes, summary)`. `blocks`:
  one row per (card, block): ITT, first stage (coef, se, F, `weak`), IV, `n_runs`,
  `n_offered`, `n_picked`, raw rates. `changes`: one row per card: for `iv`, `itt` and `fs`
  (first stage) the before, after, change (after − before) and its se
  = sqrt(se_before² + se_after²), valid because the two blocks are different runs (checked:
  a `run_key` in both blocks is refused; a stacked fit with every fixed effect interacted
  with the block gives the same ITT change and se, tested). Net of unchanged cards: `net`
  = change − the controls' median change; `z_raw` (change / se, against zero), `z_spread`
  (net / the controls' scaled MAD, as `offer_rate_check`), `z_se` (net / sqrt(se² + the
  median's se²), median se = 1.2533 MAD / √n), `z_total` (net / sqrt(that² + τ²), τ² = MAD²
  minus the controls' median se², the spread between cards beyond noise). Computed for
  every row, so the controls' own z's show what "unusual" looks like. `summary`: the
  treated card's row with the controls' median, its se, MAD, τ, how many controls have a
  change, how many were skipped (`n_controls_skipped_few`, `n_controls_skipped_weak`,
  `n_controls_error`), `controls_share_abs_z_se_gt2` (about 0.05 if the se's are right and
  the controls didn't change), runs, offered and picked runs per block, the treated card's
  balance p-values per block, and the options (`K`, `min_offered`, `include_short_runs`,
  `group`, `pooled_groups`, `screen_mix`; also echoed in `blocks` and `changes`). A block
  with F < 10 blanks the IV change (`iv_reason` says which block and the F); the weak
  control is counted and left out of the median. ITT and first-stage changes are kept
  (they don't divide by the first stage).
- **Controls matched on first stage** (robustness; columns with suffix `_m`, for `iv` and
  `itt`; the all-controls columns stay the headline). The k controls (`k_match`, default
  20, all if fewer) whose first stage in a block is closest to the card's, chosen
  separately in each block because the card's own first stage moves with the patch
  (Parry: about 13% → 28% against controls near 27%). `net_m` = (card − median of the
  matched controls, after) − (card − median of the matched controls, before);
  `matched_change` is the difference of the two medians. Because the two blocks' matched
  sets can hold different cards, the controls' own strength differences enter `net_m`;
  its errors count them: `z_se_m` adds each block's median se (1.2533 × MAD of the matched
  controls' estimates / √k, so it includes the spread between those cards), `z_spread_m`
  divides by sqrt(MAD_before² + MAD_after²), `z_total_m` adds the spread beyond noise. If
  card strength rises with pick rate (likely), a card taken more after a buff is compared
  with stronger controls after than before, which pulls `net_m` down: read it as a check
  on the headline, not a replacement. The summary gives `k_match`, the controls actually
  used per block (`iv_n_matched_before`/`_after`) and their median first stage
  (`iv_fs_matched_before`/`_after`). Every card gets the columns (a control is matched
  against the other controls, never itself).
- **Reading the three changes.** The IV change is the strength change. The ITT change is
  first stage × effect, so it also moves when only the pick rate moves: a card players
  take three times as eagerly, same effect, shows a clear ITT change and no IV change
  (synthetic, below). `fs_change` is the pick-rate change on the same runs (the first
  stage's scale, not the DiD's). **The IV change can also be a change in who takes the
  card.** The IV estimate is the effect for runs that take the card when it is offered.
  After a big buff more runs take it, and the added takers may differ from the earlier
  ones, so a change in the IV can be a change in who takes the card and not only in what
  the card does; `fs_change` shows how much the taker group moved. A drift that acts per offer on every card alike (e.g. a
  changed card that shares the screens) is common on the ITT scale and divided by each
  card's first stage on the IV scale, so the IV net of all controls removes it only for
  cards taken about as often as the median control; the matched columns handle cards
  taken much more or less often.
- `strength_all(con, ...)`: `strength_change` for every solo-estimable numeric tweak in
  `tweak_sizes.csv`, one data load per (character, before builds, after builds), and one
  fit per (card, block) shared by that window's tweaks. The 3 upgrade-only tweaks (Serpent
  Form v0.103.2, Royalties and Untouchable v0.107.1) are not estimated: they get a summary
  row whose `skipped` says so (the treatment "took the card early" doesn't separate the
  upgraded card). The summary carries the `tweak_sizes` columns. With `verbose=True` (the
  default) it prints each window's elapsed time and number of fits. `save(res, dir, name)` /
  `load(dir, name)` write and read `strength_<name>_{blocks,changes,summary}.parquet`.
- `balance_check(data, card)`: the independence check from `notebooks/iv_primer.ipynb`: on
  the runs the fits use, offered vs. not-offered runs on ascension, week, uploader group,
  build and `screen_sources`. A table of standardized differences (difference over the
  pooled sd) with a χ² test of independence per covariate, and `p_joint`: an HC1 Wald test,
  in a regression of `offered` on build dummies plus ascension, week-within-build and
  group-within-build dummies, that the last three are all zero (conditional on build
  because the fits have build fixed effects; `p_build` separately). Levels with fewer than
  20 runs are pooled (a level with a run or two fits exactly, and the robust test then
  rejects for no reason: on the 2 fetched pages 22 of 47 Silent cards "failed" before
  pooling, 2 after). `p_screens`: χ² across `screen_sources`; a rare card fails it when
  elites offer it more, which is what `screen_mix` is for.
- `balance_all(data, character, ...)`: `balance_check` for every card with at least
  `min_offered` offered runs; the share whose `p_joint` < 0.05 against the 5% chance gives
  (one-sided binomial p; the cards share runs and compete for slots, so a guide only), and
  the same for `p_screens`.

Checked on synthetic runs (`tests/test_strength.py`: two blocks of 30,000 runs, 10 cards,
three screens each, hidden skill raising both picking and winning, C9 changed in the same
patch and excluded from the 8 controls). One seed each:

| Case | IV change ± se | Controls' median | z_se (net) | Other |
|---|---|---|---|---|
| Planted +0.05 → +0.10 | +0.037 ± 0.019 | +0.007 | 1.1 | within 2 se of +0.05 |
| No change | +0.008 ± 0.019 | −0.001 | 0.4 | 10 seeds: raw z −2.1 to 1.8; controls' raw z sd 1.06 (80 draws) |
| Win rates −10 points, every run | +0.024 ± 0.019 | −0.013 | 1.6 | a level drift cancels within each block, raw or net |
| Every card's effect +0.13 (C9 nerfed) | +0.133 ± 0.041 (z 3.3) | +0.127 | 0.1 | raw moves, net ≈ 0; 10 seeds: raw z 1.6–4.9, net z_se −1.4 to 2.2 |
| Pick weight ×3, effect unchanged | +0.010 ± 0.017 | −0.006 | 0.9 | first stage +0.126 (z 29), ITT net z 2.2 |
| Weak first stage after (F = 2.0) | blank, `iv_reason` | +0.031 | – | the raw after-block IV is +66; weak control C8 counted as skipped |
| Parry-like: pick weight 0.3 → 0.9, same effect, plus the C9 drift | +0.298 ± 0.085 | +0.096 | 2.4 | matched (k = 3): `net_m` −0.007, z_se_m −0.1; 5 seeds: all-controls net +0.13 to +0.26, `net_m` −0.09 to +0.14 |

Balance: with random offers `p_joint` = 0.77 and 0 of 10 cards fail; with iv_primer's
"offer depends on skill" (X's offer weight exp(0.5 u), ascension rising with skill)
`p_joint` < 1e-15, ascension's standardized difference 0.56, all 10 cards fail (the other
cards lose the slots X takes), and the IV shows +0.097 ± 0.013 for a card with no effect.
Runtime: 54 fits on 30,000-run blocks in about 7 s (≈ 0.1 s a fit). On the full
tables, 10–15 minutes per option set is an estimate, not yet verified (`strength_all`
prints each window's time).

On 2 fetched pages (2026-09-29, `start=2026-05-01` and `start=2026-07-01`,
`min_offered=5`): the first stable window (v0.99.1 → v0.103.2) runs end to end for all 26
tweaks (25 fitted, Serpent Form skipped as upgrade-only), as do `K=1` and
`screen_mix=True`; 23–83 runs a block per character, so nearly every change is blank
(few offered runs, weak first stages, collinear fits). The second window has no runnable
before block: the pages hold no v0.103.3 runs (`n_runs_before` = 0 for all 15). Nothing
there means anything at that size.

## Phase 5 results (rerun 2026-09-29, 1,513-page tables)

From `notebooks/02_pick_rate_did.ipynb` (version 3) and `notebooks/03_anticipation.ipynb` on
the run tables built 2026-09-29 from the first 1,513 export pages (submissions to about
2026-08-30, parser 1.7.0, deduplicated by `run_key`). Results are saved in `data/analysis/`
(git-ignored); the first pass (949 pages, parser 1.4.0, 2026-09-26) is kept in
`data/analysis_p949/`. Still provisional: the snapshot isn't finished, and late uploads keep
adding runs to the stable windows. What changed from the 1,393-page rerun is listed at the
end of this section.

**Data checks.** 124 of 869,813 solo `run_key`s (0.01%) have more than one record; 4 of them
differ in the SlayTheStats tag, none look like key collisions (parser 1.6.0 separates the old
key's collisions: `solo_old_run_keys_split` = 32). The copies differ in win (25 keys), floors
reached (81) or abandonment (37); `build_info.primary_run_keys_retried` = 74, the runs win
analyses drop. `primary_offers_dedup_removed` = 4,130 rows.
Offers per stable build: v0.99.1 3.36M (85k runs), v0.103.2 3.80M (98k), v0.103.3 2.12M
(57k), v0.107.1 7.18M (193k).
Duplicated solo runs (first pass, `notebooks/scratch_queries.ipynb`, git-ignored): two
kinds, exact double submissions (e.g. the same record a few lines apart on one page) and
**retries**, whose copies differ in floors reached (e.g. one copy ends at floor 17 after
11 minutes, the other reaches floor 49 after 44). Same seed and start time, so most likely
the player died or quit, restored a save (or used an undo mod) and played on; each attempt
wrote a run file. For pick rates keeping one copy is fine (the shared early screens are the
same). For win analyses, keeping the most complete copy would keep the retry that went
better, so runs whose copies differ in win, floors reached or abandonment are dropped from
win analyses altogether (`retried`, parser 1.7.0).

**Offer-rate check.** 3 of 43 flagged, against all controls and against controls of their
own rarity (Common): Patter in both patches and Sculpting Strike. Log share ratio minus the
controls' median: Patter +0.20 (first patch) and +0.10 (second), Sculpting Strike +0.13
(about +23%, +11% and +13%). Flagging against the card's own rarity too means it isn't a
rarity pool change: something specific to these cards changed how often they're offered.
Their pick-rate estimates carry a caveat until this is explained. The Scythe, flagged on the
first pass, does not flag. Regent's Commons have only 8 controls in the first window.

**Pick-rate DiD, 43 tweaks** (β in percentage points, relative to unchanged cards of the
same character; "clearly nonzero" = |β| > 2 SE):

| | First patch (26) | Second patch (17) |
|---|---|---|
| Clearly nonzero | 23 | 7 |
| …in the direction of the change | 18 (of 22 counted) | 7 |
| Median \|β\|, all tweaks | 4.7 | 1.5 |

"In the direction of the change" leaves out mixed-direction and upgrade-only tweaks (the
first patch's Leading Strike is clearly nonzero but mixed).

- Largest: Corrosive Wave −16.4 (pick rate 43% → 29%), Parry +14.7 (13% → 28%), Leading
  Strike +10.3 (mixed: damage 7 → 3, Shivs 1 → 2), Untouchable (v0.103.2) −9.5, Pinpoint
  −9.1, Fight Me +9.0, Danse Macabre +7.8 (7% → 16%). Royalties (+9.6 ± 6.4) and Serpent
  Form (+6.9 ± 6.9) are upgrade-only tweaks fitted on a few hundred upgraded offers:
  uninformative.
- Against the direction of the change (first patch): Grand Finale −3.9, Memento Mori −4.1,
  Solar Strike −1.9 (buffs with lower picks), Sculpting Strike −0.8 ± 0.4 (buff, just past
  2 SE), and Leading Strike (mixed, counted by its main field). Second patch: all 7 clearly
  nonzero estimates go the expected way (Patter, Death March, Sic 'Em, Synthesis, Uproar,
  Unrelenting, Pounce). Debilitate's nerf shows +1.5 ± 0.8 (its first-patch buff was still
  rising).
- Parry by hand: controls 27.6% → 27.4%, Parry 13.0% → 27.7%; raw DiD +14.8, regression
  +14.75 ± 0.73 (95% interval +13.3 to +16.2); every robustness option between +14.7 and
  +14.8 (weeks 0–3 only: +14.2 ± 0.8).
- The second patch's effects are smaller at similar change sizes, and it isn't the
  horizon. The first patch's after period runs 15–17 weeks against 10 for the second, but
  over after-build weeks 0–3 alone the median |β| is 4.4 against 1.5 points (21 and 7
  clearly nonzero). Most of each effect arrives in the first month: Leading Strike +9.5 at
  weeks 0–3 against +10.3 overall, Pinpoint −8.2 against −9.1.

**Error bars.** Clustered SE ÷ plain (iid) SE ranged 0.60–1.25, median 0.99. That ratio
mostly measures unequal noise between cards: a 0/1 outcome's variance is p(1−p), plain OLS
assumes one variance for all offers, and the ratio tracks √(p(1−p)) with correlation 0.95.
Against heteroskedasticity-robust errors, which allow that, clustering by run widens the bars
by about 3% (clustered ÷ robust: median 1.03, range 0.99–1.19), most for common cards
offered many times per run (Crescent Spear 1.19, Uproar 1.19, Collision Course 1.13). Parry:
1.08. Compare clustered errors with robust ones, not plain ones.

**Pre-trends.** Mostly flat. Weekly drift before the release of about 2 SE or more: Patter
v0.103.2 (rising, about 1.8 points a week, 2.8 SE), Fight Me (falling, 1.8, 2.4 SE) and
Anticipate (rising, 1.0, 2.2 SE). Weaker (1.5–2 SE): Kingly Kick, Untouchable v0.103.2
(rising), Untouchable v0.107.1 (falling, but from only 2 before-weeks), Memento Mori
(falling), Gather Light (rising) and I Am Invincible (falling). Over a month or more after
release a drift of that size is comparable to the effects, so these are reported with a
caveat or a trend adjustment (Anticipate's nerf is probably understated). The second patch
has only 2 before-weeks per card, the first 4. The notebook's χ² screen flags eight cards at
p < 0.01 on single odd weeks (Collision Course, Corrosive Wave, Uproar, Fight Me, Anticipate,
Hyperbeam, Untouchable v0.107.1, Bulwark); it ignores correlation between weeks, so the
slopes decide.

**When in the run.** *(First-pass numbers, 949-page tables; not yet rechecked on the
1,513-page tables: the notebook's summary now gives first and last floor per act, which
land on boss floors.)* Picking falls off through a run (v0.103.2 + v0.107.1, by floor): the
share of screens where the player takes nothing rises within each act and resets at each
boss: act 1 from 5% (floor 2) to 19% (floor 15), act 2 about 26% → 33%, act 3 about 39–43%.
The pick rate per offered card falls correspondingly (32% → 27%, 24% → 22%, about 20%), and
is close to (1 − skip rate) / 3. So nearly all of the decline is "take anything at all?",
not "which card?". Timing balance (rechecked): each tweak's share of act-3 offers moved by
−2.9 to +1.2 points between its blocks (median −0.1), and the moves go together by character
and patch (first-patch Silent cards mostly −1 to −2; second-patch cards mostly up), which the
character's block term absorbs. The card-specific part is at most 1.6 points of act-3 share,
worth about 0.2 point of pick rate (first-pass estimate), against effects of 1–15 points: timing composition
doesn't bias the estimates. A cleaner estimand for later: the DiD on screens where
something was picked (choice among cards, free of the deck-size effect; tooling:
`fit_did(picked_screens_only=True)`).

**Robustness** (shift of each check from the main estimate, in main-estimate SEs):

| Check | Median shift | Note |
|---|---|---|
| No uploader-group terms | 0.10 | Largest single shift 0.37 SE |
| Tagged uploaders only | 1.92 | ~¼ of the data, SE about 2× larger; 49% move by more than 2 main SEs; 1 sign flip (as the notebook counts them) |
| Untagged uploaders only | 0.47 | |
| Drop shared screens | 0.04 | Competition on the screen doesn't matter |
| Drop bug-fix-flagged controls | 0.02 | |
| Drop top 10 uploaders | 0.04 | By `uploader_hash`, which only records from page 1025 on carry |

Tagged and untagged estimates correlate at 0.68 (χ² of their differences 79 on 43): mostly
the same answer, with a few cards where tagged players respond more (Danse Macabre, 3.7σ
apart; Refine Blade, Glitterstream, Leading Strike about 2σ) or less (Patter v0.107.1,
Untouchable v0.103.2, Solar Strike). The tagged-only fits' SE is about 2× the main one,
which alone would put the median shift near 1 SE; the observed 1.9 means the groups
genuinely respond differently to some changes (input for the tooltip question, PLAN item 7
(g)).

Second patch's before block: dropping first-patch cards from the controls changes nothing
(every estimate within 0.3 points); pooling v0.103.2 into the before block moves several
(Furnace 0.0 → +4.1, Crescent Spear +0.9 → +2.4, Reflect +1.6 → −0.2). The controls aren't
the cause, so it is the treated cards drifting over time: v0.103.3 alone stays the main
design.

**Anticipation** (`notebooks/03_anticipation.ipynb`, `did.anticipation_all`). Players can react
to a change when the beta patch notes appear, before the stable release, which would put part
of the effect into the "before" block and shrink the main estimate. The check runs on stable
builds where players still have the old card (v0.99.1 for the first patch; v0.103.2 and
v0.103.3 for the second) and asks whether the gap between the treated card and its controls
moves at the first-beta date. Lead time from the first beta to the stable release: 7–28 days
(median 28) for the first patch's 26 tweaks, 14–56 (median 28) for the second's 17.
- **14 of 43 tweaks are informative** (3 of the first patch, 11 of the second); 29 are not
  (23 first-patch, 6 second-patch). The rule: at least 2,000 treated offers on each side of
  the first-beta date and at least 3 days before it. 21 of the 29 fail both tests; for the
  first patch that is typically about 2 days of old-card play before the first beta date.
  The earlier rough count of 17 was never verified; it does not match.
- Of the 14, 10 have a clearly nonzero main effect. Post-beta gap divided by main effect:
  median −0.11 (3 first-patch tweaks) and −0.25 (7 second-patch tweaks). The post-beta gaps
  are small or on the opposite side of zero from the main effect, which is not what
  anticipation would inflate. Examples: Uproar main +2.3, post-beta −2.5 ± 0.5; Patter main
  −2.5, post-beta +3.5 ± 0.7 (Patter also fails the offer-rate check); Furnace main 0.0,
  post-beta +5.9 ± 1.0. Opposite-sign gaps look like drift or a build-level change, not a
  reaction to the notes.
- **Date versus build** (second patch, `builds=["v0.103.2"]` against both old builds): the
  informative tweaks agree between the two (Uproar −2.5 → −2.6, Patter +3.5 → +3.9,
  Crescent Spear +2.5 → +1.7, Bulwark −2.1 → −3.2 pp); the uninformative ones swing more
  (Sic 'Em −0.7 → −21.2 on a thin sample). So the post-beta gap is not just the move from
  v0.103.2 to v0.103.3.
- This does not settle the second patch's flat dose-response. It gives no support to
  anticipation as the explanation for the tweaks it can test, and it can't test most of the
  first patch.

Informative tweaks (pp; post-beta = change in the treated–control gap after the first beta
date, on old-card builds):

| Tweak | Patch | Lead (days) | Main β | Post-beta gap ± SE |
|---|---|---|---|---|
| Refine Blade | 1 | 21 | +5.1 | −0.9 ± 0.7 |
| Glitterstream | 1 | 21 | +3.3 | −0.4 ± 0.6 |
| Leading Strike | 1 | 14 | +10.3 | +0.4 ± 0.6 |
| Uproar | 2 | 42 | +2.3 | −2.5 ± 0.5 |
| Bulwark | 2 | 42 | −0.3 | −2.1 ± 1.1 |
| Debilitate | 2 | 28 | +1.5 | −0.8 ± 0.9 |
| Death March | 2 | 28 | +1.8 | −0.7 ± 0.7 |
| Sic 'Em | 2 | 14 | +2.9 | −0.7 ± 1.0 |
| Synthesis | 2 | 28 | +1.2 | −0.1 ± 0.7 |
| Pounce | 2 | 28 | +2.6 | +0.4 ± 0.6 |
| Unrelenting | 2 | 28 | +5.7 | +0.6 ± 0.8 |
| Crescent Spear | 2 | 42 | +0.9 | +2.5 ± 0.5 |
| Patter | 2 | 42 | −2.5 | +3.5 ± 0.7 |
| Furnace | 2 | 28 | 0.0 | +5.9 ± 1.0 |

**Dose-response** (38 tweaks; mixed-direction and upgrade-only kept off the line: Leading
Strike, Reflect, Royalties, Serpent Form). x = direction × ln(new/old) of the main field; y =
β in log-odds (delta method), from after-build weeks 0–3 so both patches share a horizon;
random-effects meta-regression. A refit on the all-weeks estimates (same model) gives the
same picture.
- One slope: 1.04 ± 0.18 log-odds per unit of ln(new/old) (all weeks: 1.14 ± 0.18);
  intercept −0.02 ± 0.05, so no sign that appearing in the patch notes moves picks by
  itself. +1 damage on a 7-damage card (ln(8/7) = 0.13) ≈ +0.14 log-odds ≈ +2.3 points at
  a 20% pick rate.
- **By patch: first 1.44 ± 0.19, second 0.04 ± 0.31** (all weeks: 1.52 ± 0.20 and
  0.19 ± 0.32). The second patch shows no dose-response: in June, a bigger tweak didn't move
  picks more than a small one. A level shift alone (−0.10 ± 0.09) doesn't capture the
  difference; the slope does. Cause open.
- **Same size, same precision, different effect.** The two patches' tweaks on the line match
  in size and in how well each is measured, and differ in how much picks moved:

  | | Tweaks | Median \|x\| (ln ratio) | Median \|β\| (points) | Median SE (log-odds) |
  |---|---|---|---|---|
  | First patch | 24 | 0.172 | 4.2 | 0.052 |
  | Second patch | 14 | 0.182 | 1.5 | 0.051 |

  So the flat second-patch slope isn't a power problem or a smaller-changes problem: second
  patch tweaks moved picks about a third as much for the same size of change. Candidates:
  the SlayTheStats mod's community-stats tooltips (from 2026-06-19, the day after
  v0.107.1), drift in the thin before block (v0.103.3, stable for about three weeks; the
  upgrade-only placebos below point that way), more experienced players and a settled meta, the kind of number changed
  (several second-patch mains are power amounts or Forge). Anticipation (above) is not
  supported for the tweaks it can test.
- Between-card scatter: τ ≈ 0.24 log-odds (Q = 1,102 on 36 df). Same-sized changes had very
  different effects on different cards.
- Buffs vs. nerfs, with the patch term: buff slope 1.60 ± 0.37, nerf slope 0.46 ± 0.40.
  Not distinguishable on 8 nerfs.

**Upgrade-only placebos.** Un-upgraded offers should show no effect. Serpent Form's moved
+0.05 ± 1.1 points, but Royalties' moved −3.0 ± 1.2 (2.6σ below zero) and Untouchable
(v0.107.1)'s −1.5 ± 0.5 (3.2σ). Both are second-patch cards, whose before block is thin and
whose treated cards drift (see the before-block check above), so drift is the first
candidate; a patch-notes attention effect would more likely push picks up after a buff, not
down. Open. The upgraded-offer estimates are uninformative for Serpent Form and Royalties
(204 and 177 treated offers); Untouchable's is about zero (−0.4 ± 1.2).

**Changes from the 1,393-page rerun:** the headline holds. First patch 23 of 26 clearly
nonzero (same); second patch 7 of 17 (was 6), all in the direction of the change. Dose-response
slopes 1.44 and 0.04 (were 1.47 and 0.03). Median |β| 4.7 and 1.5 points (were 4.5 and 1.6).
Parry +14.7 (was +15.1). The Untouchable (v0.107.1) placebo is −1.5 ± 0.5 (was −1.3 ± 0.5),
now 3.2σ. Tagged-only fits still diverge (median shift 1.9 SE, was 2.3; correlation 0.68,
was 0.72). Patter v0.103.2's pre-trend rose to 2.8 SE and Pinpoint's fell below 1.5 SE.
The offer-rate flags are the same three cards. New: the anticipation check on full tables.

**Open.** Why the second patch has no dose-response (fit per patch within each uploader
group; by kind of main field); why Patter and Sculpting Strike are offered more often
(tooling: `load_window(extra_cols=True)`); the negative placebos on Royalties and Untouchable
(v0.107.1); the DiD restricted to screens where something was picked
(`picked_screens_only`); the "When in the run" numbers on the new tables; a final rerun
once the snapshot is complete.

## Audit decisions (rerun 2026-09-29: 1,513 pages, submissions to ~2026-08-30)

From `notebooks/01_data_audit.ipynb` (interim tables from `scripts/audit_extract.py`). These
define the populations every analysis starts from; the parser flags that implement them are
listed in PLAN.md. The first pass (949 pages, submissions to ~2026-07-19) is kept in
`data/audit_p949/`; the decisions didn't change.

**Primary population** (the main analysis): solo runs; no modifiers; no mod markers (a
`save_dict_*` key, a mod modifier, a mod card, a mod act, or a character outside the five
real ones); a released build (in `builds.csv`); start date (UTC) on or after the build's
release date; first floor is Neow. Offers come from combat, elite and boss rewards,
including `?` fights and event-then-fight floors (flagged). Abandoned runs stay in for pick
rates and leave win analyses. On the 1,513 pages, primary is 815,997 runs, 74.2% of
distinct runs (1,100,090; first pass ~75%). Not abandoned (win analyses): 656,486 (59.7%).

- **Cheats:** no filter. No cheat flag exists; 103 of ~143k primary wins took under 15
  minutes (1,393 pages: 95 of ~132k; first pass 70 of ~98k), none before act 3 or with zero
  combat turns; the earlier "two look impossible" count wasn't rechecked. Flagged for a
  robustness check only.
- **Runs that don't start at Neow:** dropped. About 15% of v0.98.0 runs and 5% of v0.98.1,
  close to zero from v0.98.2 on. They start without the Neow bonus (a different setup) and
  sit in launch builds outside the patch windows.

**Thin builds.** Pick-rate comparisons use windows of builds (before vs. after a change), so
a build only needs to stand alone if it can't be pooled. Rule: a build is pooled with its
neighbour on the same branch when no card change falls between them; otherwise it is left
out of any window it can't fill. Under 2,000 primary runs on the 1,513 pages: v0.99.0 (beta,
3 days, 360), v0.103.1 (beta hotfix, 1 day, 1,531) and v0.110.0 (beta, superseded by the
v0.110.1 hotfix the next day, 356). v0.105.0 (2,491) and v0.109.1 (9,861), thin on the first
pass, no longer are. Checked (2026-09-25) against
`card_changes`, `beta_card_changes`, `behavior_changes`, update-history and the patch notes:
no card change between v0.99.0 and v0.99.1, v0.103.0 and v0.103.1, or v0.105.0 and
v0.105.1. The later pages hold only bug fixes; the card-related ones are v0.99.1's
(multiplayer softlock and state fixes, Brightest Flame's Max HP floor, Hand Drill with
Burn, Hellraiser with no targets), v0.103.1's Not Yet no longer generated in combat
(`behavior_changes.csv`, mid-combat generation, not offers) and v0.105.1's Silken Tress
co-op fix (non-host card rewards). v0.103.0/v0.103.1 and v0.105.0/v0.105.1 pool. v0.99.0 is
beta and v0.99.1 stable (on beta for its first three days), so the pair crosses branches:
v0.99.0 is left out of all windows (decision log). v0.110.0 carries 21 card events;
`change_events`, `beta_card_changes` and `behavior_changes` have none on v0.110.1, so by
the rule v0.110.0 pools with v0.110.1 (patch notes not yet checked; both are after the last
stable window, so this only matters for the beta designs).

**Staggered rollout (beta before stable): feasible on volume.** Every stable build ran
alongside betas: v0.103.2 (Apr 16 – May 29) with v0.104.0–v0.106.1, v0.103.3 with v0.107.0,
v0.107.1 with v0.108–v0.109. The betas have 25k–50k distinct runs each (v0.104.0,
v0.105.1, v0.106.1, v0.107.0) against 83k–135k for the stable builds running at the same
time (v0.103.3, v0.103.2). Beta and stable players differ (win and skip rates differ by
branch), so comparisons are within branch or allow branch-specific trends, never a pooled
before/after.

**Snapshot reach and backfill.** As of 2026-09-29: 1,513 pages, submissions to about
2026-08-30 (the saved cursor), play dates to 2026-08-30; the download continues. Backfill
is heavy: from about page 20 on, every page holds runs played as far back as March, because
players upload their history in bulk (the SlayTheStats mod uploads a whole local history,
oldest first). Upload lag (section 2 of the notebook; primary runs; a page's 99th-percentile
play date stands in for its submission date): median 18 days; 56% of runs arrive more than
7 days after being played, 44% more than 30 and 18% more than 90. Tagged runs lag far more
(median 65 days, untagged 5.5). Provisional until the snapshot is finished. Recent builds, and
tagged runs most of all, are under-counted until then.

**Uploader groups.** `_sts`-tagged uploads (SlayTheStats mod users) differ from the rest:

| Build | Cards | sd of per-card z | Spearman | typical gap (pick rate) |
|---|---|---|---|---|
| v0.103.2 (before community tooltips) | 400 | 3.77 | 0.94 | 0.039 |
| v0.107.1 (after) | 400 | 5.94 | 0.88 | 0.062 |

(First pass: 3.76, 0.93, 0.046 and 4.95, 0.86, 0.074; 1,393 pages: 3.91, 0.94, 0.043 and 5.88, 0.87, 0.068. The sd of z grows with the sample for
the same gap, since z scales with √n; the typical gap beyond noise is the number to compare
across snapshots.) The groups already differed before the mod showed community stats, and
the same cards lead both builds (tagged players pick Setup Strike, Perfected Strike and
Flick Flack less, Footwork and Well-Laid Plans more), so this is mainly selection, possibly
larger after June (different builds and upload timing, so not a clean comparison). A
typical gap of 4–6 points is as large as many patch effects: pick-rate estimates are made
within uploader group or with it as a covariate, pooled as a robustness check. Tagged
players also win about 8 points more (v0.103.2, finished runs: 0.27 against 0.20).

**Win rates drift within a build.** In v0.103.2 alone (same card versions throughout), the
win rate of finished primary runs fell from April to May in both groups (untagged 0.23 →
0.17, tagged 0.30 → 0.23), and the tagged share fell from ~32% to ~14%. So calendar time
matters beyond build: win analyses need week (or ascension) controls, not only build.
**Rising ascension doesn't explain it:** mean ascension fell over the same weeks (untagged
5.0 → 4.0, tagged 6.5 → 5.4), which should have raised win rates. A candidate to check:
stronger players moving to the betas that ran alongside v0.103.2 (v0.104.0–v0.106.1),
leaving a weaker population on stable. The wins tooling's week × build fixed effects absorb
the drift either way.

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
  this). Tagged uploaders rank cards differently from untagged ones (v0.107.1, 1,513 pages:
  400 cards, Spearman 0.88, per-card z sd 5.94, mean z −1.00). Whether that is selection or the mod's
  tooltips is being checked against v0.103.2, which was played before community tooltips
  existed. Solo runs can't be grouped by player, so part of the gap may be a few heavy
  uploaders. Analyses stratify by uploader group or include it as a covariate.
- **Co-op duplicates.** A multiplayer run gets uploaded once per player (seen in a sample:
  two records with the same run time, same death, timestamps 40 ms apart). The first 5
  pages had 4,641 records and 4,279 distinct (seed, start_time): about 8% co-op
  duplicates. On the first 1,513 pages: 1,435,841 records (after the repeated pages),
  1,100,090 distinct runs; solo runs are 79% of distinct runs (869,780). `scripts/snapshot_export.py` reports a `dedup` column on this key; raw `runs` counts
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
  earlier modded runs. Audit counts (records, 1,513 pages): `save_dict_*` 26,556, mod modifier
  9,274, mod card 5,690, mod character 1,362, mod acts 1,500. The parser's entity rule flags
  453 more runs on those pages (`runs_mod_entity_only`); the ids are mod content
  (`ANCIENTSAWAKENED-…`, `HADESANCIENTS-…`, `REBALANCED_SPIRE_…`, STS1's Corrupt Heart, an
  act-4 architect boss on v0.99.1, player-vs-player encounters), not new official content.
- **Treatment timing.** Assign builds from each run's own `build_id` and `start_time`, not
  `submitted_at` — players often upload their whole history folder at once (the
  SlayTheStats mod does exactly that). This also means early builds can keep gaining runs
  late in the export.
- **Runs dated before their build's release.** 8,046 runs (~0.7% of distinct runs, 1,513 pages) start before
  their build's `release_date`, by 1 day up to ~4.5 months (median a few days). Most likely saved on the old
  build and finished after an update, so their early floors may be on the old card
  versions. Filter: start date (UTC) ≥ release date (`runs.before_release`). Runs that
  cross an update on the release day itself can't be detected.
- **Non-release builds.** Pre-early-access playtest builds (v0.84.0–v0.97.0, 25 runs),
  release candidates (`-rc.N`, 13 runs) and `NON-RELEASE-VERSION` (321 runs) are in the
  export but not in `builds.csv`. Dropped (`runs.released = false`).
- **Old builds keep being played.** Every stable build has runs dated months after it was
  replaced (v0.98.x into August). The build still sets the card versions, so this doesn't
  affect treatment assignment.
- **Cheated / modded runs.** No cheat flag in the export. Audit (primary runs, 1,513 pages):
  103 of about 143,000 wins took under 15 minutes; the two that looked impossible on 1,393 pages
  (7,355 gold with 39 relics; an empty deck) are still there. No win before act 3. Too few to matter for pick rates: flagged, not
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

1. Run the full snapshot (in progress locally; 1,513 pages so far, see Data sources).
   Audit on those pages: every build from v0.98.1 on except v0.99.0, v0.103.1 and v0.110.0
   has ≥2,000 primary runs; on the 1,393 pages, 40 of the 47 numeric-tweak cards had 4.6k or
   more primary offers on each side of their stable change (4 are never offered as rewards,
   3 have under ~140; not recounted on the 1,513 pages).
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
