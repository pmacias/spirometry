# Run file structure

Checked 2026-09-24 from a cloud session against 3 pages of `GET /api/exports/runs`
(`limit=1000`, 3 credits):

| Page | Request | Runs | Distinct (seed, start_time) | `start_time` range (UTC) |
|---|---|---|---|---|
| p1 | first page (no cursor) | 1,000 | 884 | 2026-03-05 – 2026-04-02 |
| p2 | cursor from p1 | 1,000 | 935 | 2026-03-05 – 2026-04-05 |
| p3 | `start=2026-09-01T00:00:00Z` | 1,000 | 845 | 2026-03-05 – 2026-09-01 |

The pages were kept in the session's scratch directory, not in the repo. All counts below
are from these 3,000 records unless a page is named. Nothing here is from the full snapshot.

## Short answer

- A card offer is `map_point_history[act][floor].player_stats[player].card_choices[i]`:
  `{"card": {"id": "CARD.X", ...}, "was_picked": bool}`. Strip `CARD.` and the id matches
  `card_id` in `reference/card_changes.csv` and `reference/raw/cards.json`. Upgrades are
  `card.current_upgrade_level: 1` (absent when unupgraded); enchantments are
  `card.enchantment {id, amount}`.
- **There is no source field.** Where the offer came from has to be read off the floor:
  `map_point_type`, `rooms[].room_type` and `rooms[].model_id` (`EVENT.NEOW`, …).
- **One list per player per floor.** A floor with two reward screens (Prayer Wheel, White
  Star, a Driftwood reroll, an Orrery bought in a shop) concatenates them into one
  `card_choices` list with no separator.
- **A skipped reward** is a list where every `was_picked` is false. Nothing else marks it.
- **Shops are different.** In solo runs the shop list holds the cards *left on the shelf*
  when the player walked out; bought cards are removed from it and appear only in
  `cards_gained` (colored) or `bought_colorless`. `was_picked` is never true in a solo shop.
  In co-op runs the shop list is inconsistent (see below).
- **`is_beta` is not in the export at all.** None of the 3,000 records has the key.
  `scripts/snapshot_export.py --count-only` computes `bool(run.get("is_beta"))`, so its
  `beta` column is 0 for every build whatever the branch. The earlier "first pages have no
  beta runs / `is_beta=false`" reading came from that. Branch has to come from
  `reference/builds.csv` via `build_id`.
- **Co-op runs are uploaded once per player** and the copies are identical except
  `run_hash`. Every copy holds every player's `player_stats`.
- **The recent page adds `schema_version` 10** (v0.111.0 beta only), two new per-floor
  fields, two uploader-added top-level fields, a `custom` game mode, modded runs, and 16
  cards that aren't in the current card list.

## Field tree

Types are JSON types. "Present in" is the share of the 3,000 records that have the path at
least once. Values under `event_choices[].variables` are collapsed (60+ event-specific
names).

### Top level

| Path | Type | Present in | Example values / notes |
|---|---|---|---|
| `acts` | list[str] | all | `["ACT.UNDERDOCKS","ACT.HIVE","ACT.GLORY"]`; act 1 is Underdocks or Overgrowth (≈50/50). 3 modded runs in p3 have `ACT.ACTSFROMTHEPAST-*` |
| `ascension` | int | all | 0–10 |
| `build_id` | str | all | `v0.98.2`, `v0.107.1`, `v0.111.0` |
| `game_mode` | str | all | `standard`, `daily`, `custom` |
| `killed_by_encounter` | str | all | `ENCOUNTER.ENTOMANCER_ELITE`; `NONE.NONE` if none |
| `killed_by_event` | str | all | `EVENT.NEOW`, `EVENT.SLIPPERY_BRIDGE`; `NONE.NONE` if none |
| `map_point_history` | list[list[floor]] | all | one inner list per act reached |
| `modifiers` | list[{id, props?}] | all (usually empty) | `{"id":"MODIFIER.SEALED_DECK"}`; `props` holds `model_ids`, `ints`, `bools`, `strings`, `int_arrays` (mostly mod modifiers) |
| `platform_type` | str | all | `steam` only |
| `players` | list[player] | all | 1–4 entries |
| `run_hash` | str (16 hex) | all | `ab7f7e8f6118dc26`; unique per record, **differs between co-op copies** |
| `run_time` | int (seconds) | all | `981` |
| `schema_version` | int | all | 8, 9, 10 |
| `seed` | str | all | `SYNTHS100006` |
| `start_time` | int (Unix s) | all | `1790000000` |
| `was_abandoned` | bool | all | |
| `win` | bool | all | |
| `_sts` | str | p3 only (364) | `slay-the-stats/v1.2.2`: the uploader tool; not part of the game file |
| `_spirecodex_damage` | object | p3 only (57) | `{damage_dealt, damage_taken, biggest_hit, combats, turns, by_card: {STRIKE_SILENT: 182, …, other: 194}}`: added by Spire Codex, not the game |

Not present anywhere: `is_beta`, `submitted_at`, a player name.

### `players[]`

| Path | Type | Example / notes |
|---|---|---|
| `id` | int | `1` in every solo run; 64-bit Steam ID (`76561198…`) in every co-op run. Hash these. |
| `character` | str | `CHARACTER.REGENT`, `IRONCLAD`, `SILENT`, `NECROBINDER`, `DEFECT` |
| `deck[]` | {id, floor_added_to_deck, current_upgrade_level?, enchantment?, props?} | final deck |
| `relics[]` | {id, floor_added_to_deck, props?} | `props` = relic state (`ints` like `AttacksPlayed`, `cards` like `AncientCard`, …) |
| `potions[]` | {id, slot_index} | |
| `max_potion_slot_count` | int | |
| `badges[]` | {id, rarity} | rare (41 records): `ELITE`, `GLUTTON`, `KACHING`; `bronze/silver/gold` |

### Floor: `map_point_history[act][floor]`

| Path | Type | Example / notes |
|---|---|---|
| `map_point_type` | str | `monster`, `elite`, `boss`, `shop`, `rest_site`, `treasure`, `ancient`, `unknown` (a `?` node) |
| `rooms[]` | list | usually 1; 2 when a `?` event turns into a fight (`event` + `monster`) |
| `rooms[].room_type` | str | `monster`, `elite`, `boss`, `event`, `shop`, `rest_site`, `treasure` |
| `rooms[].model_id` | str | `ENCOUNTER.SLUDGE_SPINNER_WEAK`, `EVENT.NEOW`; absent for shop/rest/treasure |
| `rooms[].monster_ids` | list[str] | `["MONSTER.CORPSE_SLUG","MONSTER.CORPSE_SLUG"]` |
| `rooms[].turns_taken` | int | 0 for non-combat |
| `player_stats[]` | list | exactly one entry per player, in `players` order (45 two-player floors out of 87k had another order; join on `player_id`) |

Floor number: `floor_added_to_deck` on a picked card equals the 1-based cumulative index of
the floor across acts (43,639 of 43,639 picks). Neow is floor 1.

### `player_stats[]` (per player per floor)

Always present: `player_id`, `current_hp`, `max_hp`, `damage_taken`, `hp_healed`,
`max_hp_gained`, `max_hp_lost`, `current_gold`, `gold_gained`, `gold_lost`, `gold_spent`,
`gold_stolen` (all int).

Present when non-empty:

| Path | Type | Example / notes |
|---|---|---|
| `card_choices[]` | {card, was_picked} | see next section |
| `cards_gained[]` | card object | every card added this floor, from any source |
| `cards_removed[]` | card object | shop removal, events |
| `cards_transformed[]` | {original_card, final_card} | |
| `cards_enchanted[]` | {card, enchantment: str} | |
| `upgraded_cards[]`, `downgraded_cards[]` | list[str] | `CARD.FALLING_STAR` |
| `relic_choices[]` | {choice, was_picked} | `RELIC.ARCANE_SCROLL` |
| `ancient_choice[]` | {TextKey, title{key,table}, was_chosen} | Neow / ancient relic offer |
| `potion_choices[]` | {choice, was_picked} | |
| `event_choices[]` | {title{key,table}, variables?} | `DROWNING_BEACON.pages.INITIAL.options.CLIMB.title`; `variables` = `{Name: {type, decimal_value, bool_value, string_value}}` |
| `rest_site_choices[]` | list[str] | `SMITH`, `HEAL`, `MEND`, `COOK`, `DIG`, `CLONE`, `HATCH`, `LIFT`, `KINDLE` |
| `bought_relics[]`, `bought_potions[]`, `bought_colorless[]` | list[str] | shop purchases |
| `potion_used[]`, `potion_discarded[]` | list[str] | |
| `relics_removed[]` | list[str] | |
| `completed_quests[]` | list[str] | `CARD.LANTERN_KEY`, `CARD.SPOILS_MAP` |
| `stolen_loot` | int | schema 9 on v0.107.1 and schema 10 only |
| `is_affected_by_fur_coat` | bool | schema 10 only |

### Card object (in `card_choices[].card`, `cards_gained`, `deck`, …)

| Key | Type | Example / notes |
|---|---|---|
| `id` | str | `CARD.COLLISION_COURSE` |
| `current_upgrade_level` | int | `1`; absent = unupgraded. Never seen above 1 |
| `enchantment` | {id, amount, props?} | `{"id":"ENCHANTMENT.NIMBLE","amount":2}` |
| `props` | {ints?, bools?} | card state, e.g. Genetic Algorithm `{"ints":[{"name":"CurrentBlock","value":1},{"name":"IncreasedBlock","value":0}]}` |
| `floor_added_to_deck` | int | in `card_choices`, present **iff picked** (43,639 picks, all have it; 109 unpicked entries have it too, all where the same card was picked from another set on that floor) |
| `save_dict_List[BaseLib.Abstracts.CardModifier+ModifierSave]` | dict | only in modded runs (p3, 21 runs): the BaseLib mod loader |

## How a card offer identifies a card

- **ID format.** Always `CARD.<ID>` (all 213,734 offers). `<ID>` is the upper-snake id used
  by Spire Codex, the same as `card_id` in `card_changes.csv`, `text_only_labels.csv` and
  `raw/cards.json`. 104 of card_changes' 119 card ids appear as offers in this sample under
  exactly that id. The other 15 are never offered as rewards by rarity: Token (`SHIV`,
  `SOVEREIGN_BLADE`, 3 `MINION_*`), Ancient (`BREAK`, `NEOWS_FURY`, `THE_SEALED_THRONE`),
  Event (`EXTERMINATE`, `MAD_SCIENCE`, `RIP_AND_TEAR`, `STACK`), Basic (`FALLING_STAR`),
  Curse (`FOLLY`), Status (`WITHER`). Those enter decks through `cards_gained`, not offers.
- **Ids not in the current card list** (`raw/cards.json`, 577 cards):
  - removed cards: `GRAPPLE` and `FOLLOW_THROUGH` (both in card_changes as `removed`),
    offered on v0.98.0–v0.103.2;
  - `PREPARE`: 103 offers, all on v0.100.0. A beta-only card. Not in card_changes (it never
    reached stable) — a candidate for `beta_card_changes.csv`;
  - 16 cards only on v0.111.0 beta (`BLADE_SYMPHONY`, `BLAZE`, `CACOPHONY`, `CONCOCT`,
    `CONSTELLATION`, `FADE`, `HIBERNATE`, `IMITATION_LEARNING`, `MIDNIGHT`, `ONE_FOR_ALL`,
    `OUTRAGE`, `PLOT`, `SIDESTEP`, `SOULBOUND`, `THE_BALL`, `TUTOR`, `UNDERWORLD`): beta
    content the stable card list doesn't have yet;
  - mod cards, recognisable by a `-` in the id: `CARD.MULTIPLAYEREXPANDED-VULTURE`,
    `CARD.THEHEROEXPANSION-AKUMETSU`, `CARD.UNCAPPEDSPIRE-…` (42 offers, 19 ids, p3 only).
- **Upgrades.** `current_upgrade_level: 1` on 13% of offers. For combat rewards the upgraded
  share rises by act: 3% in act 1, 20% in act 2, 44% in act 3. So upgraded is part of what
  was offered and should be a column, not folded into the card id.
- **Other modifiers on an offered card.** `enchantment` (1.3% of offers; mostly `GLAM`,
  `NIMBLE`, `SWIFT` on combat rewards), `props` (Genetic Algorithm's growth, etc.), and the
  mod-only `save_dict_*` key. No other keys occur on offered cards.

## Where cards are offered or gained

Counts are player-floors (one player's stats on one floor) with a non-empty `card_choices`.

| Source | How to recognise it | Player-floors with offers | List size | Picks per list |
|---|---|---|---|---|
| Normal fight reward | `map_point_type` `monster`, or `unknown` with `room_type` `monster` (a `?` that was a fight) | 36,099 | 3 (95%); 4, 6, 9, 12 | 0 or 1 (0 in 26%) |
| Elite reward | `map_point_type` `elite` (or `unknown` + `elite`) | 11,289 | 3; 4, 6 | 0 or 1 (0 in 29%) |
| Boss reward | `map_point_type` `boss` | 4,243 | 3; 4, 6 | 0 or 1 (0 in 10%) |
| Event that became a fight | `unknown`, rooms `event`+`monster` (`EVENT.PUNCH_OFF`, `DENSE_VEGETATION`, `THE_LANTERN_KEY`, `FAKE_MERCHANT`) | 314 | 3–7 | 0–2 |
| Event offer | `unknown`, room `event` | 1,052 | 3, 4, 6, 9, 15 | 0–3 |
| Neow / ancient | `map_point_type` `ancient`, room `event`, `model_id` `EVENT.NEOW` (act 1) or another ancient | 728 | 1–3, 6, 15, 30 | 0–10 |
| Shop | `map_point_type` `shop` (or `unknown` + `shop`) | 7,454 | usually 5–7 (solo) | solo: always 0 |
| Rest site | `rest_site` | 105 | 3–4 | 0 or 1 |

Events with card offers: `COLORFUL_PHILOSOPHERS` (choose a character, then 9 cards of its
color), `NEOW`, `THE_FUTURE_OF_POTIONS`, `CRYSTAL_SPHERE`, `BRAIN_LEECH`, `THE_LANTERN_KEY`,
`OROBAS`, `ROOM_FULL_OF_CHEESE` (p3 only), `TRIAL`, `DENSE_VEGETATION`, `PUNCH_OFF`,
`FAKE_MERCHANT`.

Notes by source:

- **Combat rewards** are the clean case: one or more screens of 3 (4 with Lasting Candy,
  which is held on 66% of 4-card floors vs ~1% of 3-card floors), at most one pick per
  screen. 6-card floors go with Prayer Wheel (37% of them), Driftwood (27%; a reroll keeps
  the rejected screen in the list, probably) and White Star.
- **Neow / ancients** mix relic effects that offer cards (lists of 1–3, and 15- or 30-card
  lists with several picks) with gains that have no
  offer at all (Neow's starting card). Some Neow floors list a card offer that doesn't match
  `cards_gained` (e.g. offered `INTERCEPT`, gained `PROWESS`), so the two can't be assumed
  to line up there.
- **Shops (solo).** The list is the unsold shelf at exit. Colored cards on the shelf plus
  colored cards gained add to 5, and colorless on the shelf plus `bought_colorless` add to
  2, on 3,786 of the 3,877 solo shop floors with a list of 1–7 cards (the rest are 6/7 colored or 3 colorless: relic or
  event effects on shop size). Bought cards never appear in `card_choices` (checked: 0 of
  3,877 solo shops list a gained card as unpicked, apart from 3 exceptions). An offer set
  for a shop has to be reconstructed as *shelf ∪ bought*. Orrery bought in a shop adds its
  cards to the same list, and those are marked `was_picked` normally.
- **Shops (co-op)** come in four shapes: only the bought cards, all `was_picked=true`
  (common in schema 8: 694 player-floors), shelf only (1,353), shelf plus the bought cards
  marked picked (532, mostly schema 9–10), or nothing (375). Co-op shop offers aren't
  reliable as offers.
- **Rest sites** very rarely offer cards (105 player-floors); these look like relic
  triggers.
- **Cards gained with no offer**: 3,695 player-floors in events (`TRASH_HEAP` → `STACK`,
  curses like `INJURY` or `DEBT`, `BRAIN_LEECH` → `DEFILE`), 1,793 on ancient floors,
  122 at rest sites, 59 at shops, 4 after fights. Every picked offer is in `cards_gained`
  on that floor (43,639 of 43,639).
- **Treasure** floors never have card offers.
- Transforms (`cards_transformed`), enchants and removals are separate lists and aren't
  offers.

## Skipped rewards and multiple sets per floor

- A skip is a `card_choices` list with no `was_picked: true`. There is no skip record,
  skip reason, or "Singing Bowl"-style alternative field. No pick in 25% of normal-fight
  lists, 29% of elite lists and 10% of boss lists.
- A combat player-floor without `card_choices` is almost always the floor the run ended on
  (3,501 of 3,693; the rest are 163 boss floors, e.g. the first of two act-3 bosses, and 29
  normal fights). So "reward never shown" and "skipped" are distinguishable: absent vs
  all-false.
- **Yes, a floor can hold more than one set**, and the list doesn't mark the boundary. In
  combat rewards (normal, elite, boss, `?` fights: 51,631 lists) 2.5% have more than 4
  cards and 0.9% have 2–3 picks. Splitting into screens needs the reward size (3, or 4 with Lasting Candy) and
  the assumption that each screen is contiguous in the list. The same card can appear in
  two screens on one floor (`HIGH_FIVE` twice in one 6-card list).

## Co-op runs

- 592 of 3,000 records are co-op (2–4 players); they are 20%, 11%, 27% of p1–p3.
- Every co-op record has one `player_stats` entry per player on every floor and a
  `players` entry per player, each with its own `id` (Steam ID), `character`, `deck`,
  `relics`. Characters can repeat within a run (136 of 592 co-op records have a duplicate
  character).
- Each player uploads the same run. The 254 duplicate pairs found are identical except
  `run_hash`. Dedup key `(seed, start_time)` works; it merges 2–4 copies. Two groups had 4
  copies of a 2-player run (uploaded twice each). The 3 pages have no cross-page
  duplicates by `run_hash`; 2 `(seed, start_time)` keys are shared by p1 and p2.
- `win`, `was_abandoned`, `killed_by_*`, `ascension` and `run_time` are run-level: one
  outcome shared by all players.
- Co-op-only differences found so far: the shop list shapes above, and multiplayer-only
  cards (card list has a `multiplayer_only` flag).

## Abandoned runs

- `was_abandoned` true on 430 of 3,000 (5.8%, 22.7%, 14.5% of p1–p3). `win` is always
  false for them.
- 127 are abandoned on floor 1 (Neow). Those have `killed_by_event: EVENT.NEOW`, which
  otherwise reads like "died to Neow". 161 abandoned runs have a non-`NONE`
  `killed_by_encounter`: abandoned mid-fight, recorded as a death to that encounter.
- Median `run_time` 246 s for abandoned runs vs 2,185 s for the rest.
- Abandoned runs still carry every offer made before quitting; whether to keep those offers
  is a decision (they're real offers with real picks, but the run has no outcome).
- No non-abandoned loss had both `killed_by_*` fields `NONE.NONE`.

## Value counts

| Field | p1 | p2 | p3 |
|---|---|---|---|
| `schema_version` | 8: 948, 9: 52 | 8: 801, 9: 199 | 8: 158, 9: 555, 10: 287 |
| `game_mode` | standard 998, daily 2 | standard 1,000 | standard 958, daily 29, custom 13 |
| `platform_type` | steam 1,000 | steam 1,000 | steam 1,000 |
| `modifiers` non-empty | 2 | 3 | 54 |
| players 1 / 2 / 3 / 4 | 794 / 136 / 54 / 16 | 886 / 72 / 18 / 24 | 728 / 174 / 78 / 20 |

`schema_version` by build: 8 = v0.98.0–v0.100.0; 9 = v0.101.0–v0.107.1; 10 = v0.111.0.

`modifiers` ids across the 3 pages (records containing each): `DEADLY_EVENTS` 41,
`SEALED_DECK` 27, `BIG_GAME_HUNTER` 21, `HOARDER` 17, `CHARACTER_CARDS` 16 (can repeat
within a run), `CURSED_RUN` 13, `FLIGHT` 13, `INSANITY` 11, `TERMINAL` 11, `ALL_STAR` 10,
`MURDEROUS` 9, `DRAFT` 7, `SPECIALIZED` 5, `VINTAGE` 5, `NIGHT_TERRORS` 2, and three from
mods: `HEXTECH_MAYHEM_MODIFIER`, `UNCAPPED_SPIRE_MODIFIER`, `LIMITLESS_MODIFIER` (1 each).

- Daily runs always have modifiers (31 of 31). Custom runs always have modifiers.
- **15 `standard` runs have modifiers**: 12 on v0.99.1 with custom-run modifier sets
  (`SEALED_DECK`, `FLIGHT`, …; `custom` only appears as a mode from v0.107.1 in this sample), plus
  3 with a mod modifier. So `game_mode == 'standard'` is not enough to filter custom runs on early
  builds; filter on `modifiers` being empty.
- Modded runs (any of: a mod modifier, a `-` in a card id, `save_dict_*` keys,
  `ACTSFROMTHEPAST` acts): 0 in p1, 0 in p2, 24 in p3. Some mods (e.g. the BaseLib loader
  alone) leave no mark other than `save_dict_*`, so there may be more that can't be seen.

## Runs per build, with branch from `builds.csv`

`runs` = records, `dedup` = distinct `(seed, start_time)`. Branch is the `branch` column of
`reference/builds.csv` (blank there for v0.98.0–v0.99.1).

| Build | Branch | p1 runs | p1 dedup | p2 runs | p2 dedup | p3 runs | p3 dedup |
|---|---|---|---|---|---|---|---|
| v0.98.0 | (blank) | 27 | 24 | 10 | 6 | 3 | 2 |
| v0.98.1 | (blank) | 60 | 57 | 30 | 29 | 6 | 4 |
| v0.98.2 | (blank) | 227 | 191 | 99 | 95 | 16 | 10 |
| v0.98.3 | (blank) | 326 | 297 | 217 | 213 | 49 | 46 |
| v0.99.1 | (blank) | 213 | 177 | 199 | 164 | 84 | 73 |
| v0.100.0 | beta | 95 | 90 | 246 | 235 | | |
| v0.101.0 | beta | 52 | 48 | 158 | 152 | | |
| v0.102.0 | beta | | | 41 | 41 | | |
| v0.103.2 | stable | | | | | 29 | 27 |
| v0.103.3 | not in builds.csv | | | | | 1 | 1 |
| v0.107.1 | stable | | | | | 525 | 439 |
| v0.111.0 | beta | | | | | 287 | 243 |

- The first two pages already hold 592 beta runs (v0.100.0–v0.102.0), 30% of them. The
  earlier "no beta" finding came from the missing `is_beta` field.
- p3, the page from `start=2026-09-01`, still has 158 runs on v0.98.x–v0.99.1: the export
  is ordered by submission time, and players upload old history late. `start` bounds
  submission, not play.
- `v0.103.3` appears once and isn't in builds.csv (added in Part 2 of this PR from the
  wiki's patch-note list).
- In early September, stable (v0.107.1) and beta (v0.111.0) are live side by side; beta is
  34% of that page's runs on v0.103.2 or later.

## Early pages vs the recent page

| | p1–p2 | p3 |
|---|---|---|
| `schema_version` | 8, 9 | 8, 9, 10 (10 = v0.111.0) |
| `stolen_loot` (per floor) | absent | on v0.107.1 (schema 9) and v0.111.0 |
| `is_affected_by_fur_coat` (per floor) | absent | v0.111.0 only |
| `_sts` (uploader tag) | absent | 364 records, all builds including old ones |
| `_spirecodex_damage` | absent | 57 records (v0.107.1, v0.111.0) |
| `game_mode: custom` | absent | 13 |
| Modded runs | none seen | 24 |
| Card ids not in the card list | removed cards + `PREPARE` | removed cards + 16 v0.111.0 beta cards + mod cards |
| Events with offers | — | adds `ROOM_FULL_OF_CHEESE` |
| Rest-site options | — | same set |
| Shop list sizes | ≤7 in solo | up to 25 (relics and modded runs) |

The structure used for offers (`card_choices`, `card.id`, `was_picked`,
`current_upgrade_level`, `enchantment`, `floor_added_to_deck`) is the same across all
three schema versions. `_sts` and `_spirecodex_damage` aren't game data; `_spirecodex_damage`
is the only per-card combat information in any record, and it's on 2% of p3.

## Proposal: `runs` and `card_offers` columns

Not code. Types are DuckDB types.

### `runs` — one row per record (keep co-op copies; dedup is a view)

| Column | Type | From |
|---|---|---|
| `run_hash` | VARCHAR | `run_hash` (primary key) |
| `run_key` | VARCHAR | hash of `(seed, start_time)`: the dedup key shared by co-op copies |
| `source_page` | INTEGER | export page the record came from (for tracing) |
| `build_id` | VARCHAR | `build_id` |
| `branch` | VARCHAR | joined from `builds.csv`; NULL where builds.csv is blank |
| `schema_version` | SMALLINT | |
| `start_time` | TIMESTAMP | `start_time` (UTC) |
| `run_time_s` | INTEGER | `run_time` |
| `game_mode` | VARCHAR | |
| `modifiers` | VARCHAR[] | `modifiers[].id` |
| `is_custom` | BOOLEAN | `modifiers` non-empty (any mode) |
| `is_modded` | BOOLEAN | mod markers listed above |
| `ascension` | SMALLINT | |
| `n_players` | SMALLINT | `len(players)` |
| `win`, `was_abandoned` | BOOLEAN | |
| `abandoned_at_neow` | BOOLEAN | abandoned with 1 floor |
| `acts_reached` | SMALLINT | `len(map_point_history)` |
| `floors_reached` | SMALLINT | total floors |
| `act1` | VARCHAR | `acts[0]` (Underdocks / Overgrowth) |
| `killed_by_encounter`, `killed_by_event` | VARCHAR | NULL for `NONE.NONE` |
| `uploader_tag` | VARCHAR | `_sts` |

And `run_players` (one row per record × player): `run_hash`, `player_idx`,
`player_hash` (hashed `id`; `1` stays solo), `character`, `final_deck_size`.

### `card_offers` — one row per card in `card_choices`

| Column | Type | From |
|---|---|---|
| `run_hash` | VARCHAR | |
| `run_key` | VARCHAR | for dedup |
| `player_idx` | SMALLINT | position in `players` (joined on `player_id`) |
| `player_hash` | VARCHAR | hashed `player_id` |
| `character` | VARCHAR | the offered player's character |
| `act` | SMALLINT | outer index, 1-based |
| `floor` | SMALLINT | cumulative floor, 1-based (matches `floor_added_to_deck`) |
| `map_point_type` | VARCHAR | |
| `room_types` | VARCHAR | e.g. `event+monster` |
| `room_model_id` | VARCHAR | `ENCOUNTER.*` / `EVENT.*` |
| `source` | VARCHAR | derived: `combat`, `elite`, `boss`, `event_combat`, `event`, `ancient`, `shop`, `rest_site` |
| `list_pos` | SMALLINT | index in `card_choices` |
| `list_len` | SMALLINT | length of the floor's list |
| `set_idx` | SMALLINT | screen within the floor (combat only; NULL where it can't be split) |
| `card_id` | VARCHAR | `card.id` without `CARD.` |
| `upgraded` | BOOLEAN | `current_upgrade_level >= 1` |
| `enchantment` | VARCHAR | `enchantment.id` |
| `enchantment_amount` | SMALLINT | |
| `picked` | BOOLEAN | `was_picked`; for solo shops, see decisions |
| `set_picked_any` | BOOLEAN | whether anything in this card's screen was picked (skip flag) |
| `in_card_list` | BOOLEAN | card id found in `raw/cards.json` (false for beta-only, removed, mod cards) |

For solo shops, an optional second source row per bought card
(`source = 'shop'`, `picked = true`) rebuilt from `cards_gained` / `bought_colorless`.

## Decisions needed

1. **Which sources count as offers.** Proposed: combat, elite, boss rewards (including `?`
   fights) are the core set; events and Neow/ancients kept but flagged, and left out of the
   main pick-rate DiD because the offer pool and pick rules differ by event; rest sites
   dropped.
2. **Shop offers.** Keep them? If so, solo shops need the shelf plus bought cards rebuilt,
   and "picked" means bought (a gold decision, not a free pick). Co-op shops look unusable.
   Proposed: separate `shop_offers` table, not in `card_offers`' main analysis.
3. **Co-op.** Options: (a) solo only; (b) keep co-op, dedup copies by `run_key`, and treat
   each player's offers as offers, clustering standard errors by run; (c) run-level unit.
   Co-op offers are real choices, but one player's picks depend on the others' decks, and
   the win is shared. Proposed: (b) with a `n_players` covariate and a solo-only robustness
   check.
4. **Multi-set floors.** Split into screens using the reward size, or keep the floor as one
   "offer set" and drop floors with more than one pick? Proposed: split when the list length
   is a multiple of 3 (or 4 with Lasting Candy); otherwise leave `set_idx` NULL. Affects ~3%
   of combat lists.
5. **Abandoned runs.** Keep their offers for pick-rate analysis (picks are real) but drop
   them from win analysis? Proposed: yes; always drop runs abandoned at Neow.
6. **Custom, daily and modded runs.** Proposed: drop any record with non-empty `modifiers`,
   a mod card, or mod markers from everything. Daily runs have fixed modifiers, so they go
   too.
7. **Upgraded and enchanted offers.** Same card, different offer. Proposed: keep as columns
   and control for them (upgraded share depends on act), rather than dropping.
8. **Beta-only and mod card ids.** Keep beta-only cards (they're treatments of their own);
   drop mod cards.
9. **Early builds with blank branch** (v0.98.0–v0.99.1; 1,566 of the 3,000 records). Part 2
   of this PR fills them from the patch notes where the wiki says so.

## Test fixture

`tests/fixtures/sample_runs.jsonl` holds 6 runs from these pages, the only run data in git:
a solo win (v0.98.3), a loss with a 6-card reward floor (v0.100.0), a run abandoned
mid-fight (v0.98.3), a 2-player co-op run (v0.99.1), a beta run offering `PREPARE`
(v0.100.0), and a v0.111.0 run from the recent page (schema 10). In the co-op run the
Steam IDs are replaced by 1001 and 1002 in `players[].id` and every `player_stats[].player_id`.
