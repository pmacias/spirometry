# Spirometry

Measuring what Slay the Spire 2's balance patches actually did.

Status: scoping. Data access confirmed from my Mac and from CC cloud sessions; 5-page test
done (4,641 runs, v0.98.0–v0.103.2, no beta); patch history endpoints checked (see
`notes/patch_history.md`). Full snapshot running locally.

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
    (Mac and cloud session agree). The first 5 pages covered v0.98.0–v0.103.2, all stable
    (no beta).
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
  A version → branch → date table has to be built by hand.
- Rate tiers: no key 15/min, registered 60/min, **academia 100/min (on request)**.
  Unknown whether the academia tier also raises the export's 120/h budget.
- Size: the community stats page claims ~1.8M submitted runs.
- Privacy policy: submitted runs and persona names are "public by design." Players can
  request deletion.

### STS2 Runs (secondary) — sts2runs.com

One monthly dump available: `runs-all-before-2026-06.json.gz`, 6,796 runs, ~15 MB,
gzipped NDJSON. Cheated runs included and flagged (`_isCheated`, `_cheatedReasons`).
Too small and too early to be the main source; possibly useful for cross-checks and
early-build coverage.

## What a run record contains

Top level: `acts`, `ascension`, `build_id`, `is_beta`, `schema_version`, `seed`,
`start_time`, `run_time`, `game_mode`, `modifiers`, `win`, `was_abandoned`,
`killed_by_encounter`, `killed_by_event`, `platform_type`, `players`, `map_point_history`.

`map_point_history` is a list of acts, each a list of floors. Each floor has:

- `map_point_type`: monster, elite, boss, shop, rest_site, treasure, ancient, unknown
- `rooms`: `model_id` (e.g. `ENCOUNTER.NIBBITS_WEAK`, `EVENT.NEOW`), `monster_ids`,
  `room_type`, `turns_taken`
- `player_stats` (one entry per player):
  - `card_choices`: every card offered, each with `was_picked`
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

## Known data issues

- **Self-selection.** Uploaders install a companion app or mod; likely more dedicated and
  more skilled than the average player. State as a limitation; check whether the uploader
  mix shifts over time.
- **Co-op duplicates.** A multiplayer run gets uploaded once per player (seen in a sample:
  two records with the same run time, same death, timestamps 40 ms apart). The first 5
  pages had 4,641 records and 4,279 distinct (seed, start_time): about 8% co-op
  duplicates. `snapshot_export.py` reports a `dedup` column on this key; raw `runs` counts
  are upper bounds. Whether the unit of analysis is the run or the player-run gets decided
  at parsing (a co-op run has one outcome but several players' choices).
- **Player IDs.** Solo runs use `player_id: 1`. Multiplayer runs carry real 64-bit Steam
  IDs. Hash these in the pipeline; publish aggregates only. Not planning player-level
  analysis. Raw snapshot data is git-ignored and never committed.
- **Beta vs. stable.** Two branches run different card versions at the same time
  (e.g. stable v0.107.1 and beta v0.111.0 in September 2026). Always key on `build_id`.
- **Treatment timing.** Assign builds from each run's own `build_id` and `start_time`, not
  `submitted_at` — players often upload their whole history folder at once. This also
  means early builds can keep gaining runs late in the export.
- **Cheated / modded runs.** Need a filter (check `modifiers`, `game_mode`, and anything
  Spire Codex flags).

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

- Current contents: `snapshot_export.py`, `SPIROMETRY.md`, `pyproject.toml`, `.gitignore`,
  `.claude/settings.json`, `notes/` (endpoint investigations, raw API samples).
- Environment: dependencies live only in `pyproject.toml` (`requests` as the only core
  dependency; an `analysis` extra — duckdb, pandas, pyarrow, numpy, matplotlib, jupyter —
  for later). Locally a mamba env with `pip install -e .`; plain `pip install -e .` in
  cloud sessions and CI. No separate environment.yml / requirements.txt. Move to the
  `src/` layout when the parsing pipeline starts.
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
  (`python snapshot_export.py --pages 1`), and the finished pipeline runs locally on the
  full snapshot.

## Open questions / next steps

1. Run the full snapshot (in progress locally): runs per build (after dedup), and whether
   early builds have enough runs. (The <1000/page shortfall is explained: occasional
   short pages, see Data sources.)
2. ~~Verify the patch history endpoints.~~ Done — `notes/patch_history.md`. Next: pull all
   changelog details + update-history for changed entities, build the change table and
   the version → branch → date table, and check coverage of v0.98–v0.99 and stable
   hotfixes.
3. ~~Estimate total snapshot size and rate-budget cost per page.~~ Done — see Data sources.
4. Message the Spire Codex maintainer: describe the project, ask about the academia tier
   and whether it raises the export budget, confirm they're fine with the use.
5. ~~Push the repo to GitHub, then test whether a CC cloud session can clone it and reach
   spire-codex.com.~~ Done — passed.
6. ~~Claim the cloud credit (`/claim-credit` in CC) before October 7, 2026.~~ Done.
7. Keep Clickworthy moving in parallel (currently on Stage 1).
