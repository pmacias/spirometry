# Spirometry

Measuring what Slay the Spire 2's balance patches actually did.

Status: data acquisition. Data access confirmed from my Mac and from CC cloud sessions;
5-page test done (4,641 runs, v0.98.0–v0.103.2, including beta builds v0.100.0–v0.103.1);
patch history endpoints checked (`notes/patch_history.md`); card patch dataset built and
cross-checked against the official patch notes (`notes/patch_notes_crosscheck.md`); run file
structure documented from 3 pages (`notes/run_schema.md`). Full snapshot running locally.

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
  of 120 credits/hour. **Verified working** from my Mac and from a CC cloud session.
  - Cost: 1 credit per page (`limit=1000`), ~2.3 MB gzipped per page.
  - Most pages are full (1,000 runs). Now and then a page comes back short: 1 of the first
    5 had 641 runs (4,641 total). Probably server-side filtering after the page is cut;
    the cursor still advances normally.
  - Export is ordered oldest submission first, and the order is the same from any client
    (Mac and cloud session agree). The first 5 pages covered v0.98.0–v0.103.2. That
    includes beta builds (v0.100.0–v0.103.1 are beta per `reference/builds.csv`; 30% of the
    first two pages). The earlier "no beta" reading came from counting `is_beta`, a field
    the export records don't have (`notes/run_schema.md`).
  - `start` / `end` bound submission time, not play time: a page from `start=2026-09-01`
    still had 16% of its runs on v0.98.x–v0.99.1.
  - Projected full snapshot: ~1,800 pages, ~4 GB, ~15 h of rate budget at 120/h
    (assuming ~1.8M runs and ~1000 runs/page).
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
`run_hash`. No `is_beta`. Some recent records also carry `_sts` (uploader tool) and
`_spirecodex_damage` (added by Spire Codex), which aren't game data. Pages fetched on
2026-09-25 also have a top-level `player_token` on every record (null on most, a 16-character
string on 170 of 2,000); it wasn't in the 2026-09-24 pages, so older snapshot pages may lack
it. It probably identifies the uploader and is hashed like player IDs.

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
~60 min for a cold cache). Cards only so far.

- `builds.csv` — one row per game version (from update-history, changelog text, and the run
  data): `build_id` (lowercase, as in run files), `branch`, `release_date`, `source`,
  `notes`. Blank where no source says; `notes` explains. Stable dates are Spire Codex
  changelog dates (an upper bound on the Steam release); beta dates are update-history dates.
- `card_changes.csv` — one row per (card, field, stable patch): `old`/`new` from the
  changelog, `beta_build`/`beta_date` (first beta where update-history shows that field
  changing), `stable_build`/`stable_date`, `change_kind` (tweak, rework, cost_change,
  rarity_change, text_only, added, removed; `+`-joined, e.g. `rework+cost_change`),
  `changed_fields` (every field in that card-patch, for reclassifying), `source`.
  Two stable patches so far: v0.103.2 (85 card-patches) and v0.107.1 (43).
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
  notes plus update-history.

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
split into screens, the hashing key's fingerprint). Columns follow `notes/run_schema.md`.

- `runs`: one row per record (co-op copies kept). `branch` from `builds.csv`, NULL where
  blank or missing. Flags: `is_custom` (any modifier), `is_modded`, `was_abandoned`,
  `abandoned_at_neow`. `source_page` / `source_line` locate the raw record.
- `run_players`: one row per record × player (`player_hash`, `character`).
- `card_offers`: one row per `card_choices` entry, every source, with `source`, `set_idx`
  (combat/elite/boss screens; NULL when the list can't be split), `set_picked_any`,
  `upgraded`, `enchantment`, `in_card_list`, `is_mod_card`. `card_id` has no `CARD.` prefix.
- `shop_offers`: solo shops as the list plus purchases (`origin = 'gained'`, `picked` =
  bought); co-op shops as recorded, `usable = false`.
- Views: `runs_dedup` (first record per `run_key`, with `n_copies`), `card_offers_dedup`,
  `primary_offers` (solo, no modifiers, not modded, combat/elite/boss, no mod cards;
  abandoned runs kept with `was_abandoned`).

On the 2 fetched pages, 0.55% of combat reward lists (0.19% of `primary_offers` rows)
couldn't be split; none of the 966 split multi-screen lists had two picks in one screen.

## Known data issues

- **Self-selection.** Uploaders install a companion app or mod; likely more dedicated and
  more skilled than the average player. State as a limitation; check whether the uploader
  mix shifts over time.
- **Co-op duplicates.** A multiplayer run gets uploaded once per player (seen in a sample:
  two records with the same run time, same death, timestamps 40 ms apart). The first 5
  pages had 4,641 records and 4,279 distinct (seed, start_time): about 8% co-op
  duplicates. `scripts/snapshot_export.py` reports a `dedup` column on this key; raw `runs` counts
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
  1 run on 2 pages), so the parser flags any quoted id with a `-`.
- **Treatment timing.** Assign builds from each run's own `build_id` and `start_time`, not
  `submitted_at` — players often upload their whole history folder at once. This also
  means early builds can keep gaining runs late in the export.
- **Cheated / modded runs.** Need a filter (check `modifiers`, `game_mode`, mod markers,
  and anything Spire Codex flags).

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
  jupyter — for later). Locally a mamba env with `pip install -e .`; plain `pip install -e .` in
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

1. Run the full snapshot (in progress locally): runs per build (after dedup), and whether
   early builds have enough runs. (The <1000/page shortfall is explained: occasional
   short pages, see Data sources.)
2. ~~Verify the patch history endpoints.~~ Done — `notes/patch_history.md`.
   ~~Build the card change table and the version → branch → date table.~~ Done —
   `reference/`. ~~Label the text-only changes.~~ Done — `text_only_labels.csv`.
   ~~Cross-check against the official patch notes.~~ Done —
   `notes/patch_notes_crosscheck.md`. Next: decide on the four tweak/rework
   disagreements, the notes-only changes and the bug-fix behavior changes (decisions
   listed there); review `excluded_fields.csv` and `history_unmatched.csv`; extend to
   relics, monsters, and encounters.
2b. ~~Document the run file structure.~~ Done — `notes/run_schema.md`, with a proposal
   for the `runs` and `card_offers` columns and the decisions they need.
3. ~~Estimate total snapshot size and rate-budget cost per page.~~ Done — see Data sources.
4. Message the Spire Codex maintainer: describe the project, ask about the academia tier
   and whether it raises the export budget, confirm they're fine with the use.
5. ~~Push the repo to GitHub, then test whether a CC cloud session can clone it and reach
   spire-codex.com.~~ Done — passed.
6. ~~Claim the cloud credit (`/claim-credit` in CC) before October 7, 2026.~~ Done.
7. Keep Clickworthy moving in parallel (currently on Stage 1).
