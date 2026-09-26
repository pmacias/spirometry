# Treatment table: card versions per build and DiD windows

Built 2026-09-26 by `python -m spirometry.treatment` from the committed reference tables
(`builds.csv`, `card_changes.csv`, `beta_card_changes.csv`, `behavior_changes.csv`,
`patch_notes_cards.csv`, `text_only_labels.csv`, and the cached card list for colors). No
run data. Rebuilding gives byte-identical CSVs (tested).

| File | Rows | One row per |
|---|---|---|
| `reference/change_events.csv` | 326 | card change event (262) or bug-fix behavior event (64) |
| `reference/change_event_fields.csv` | 602 | (event, field): old → new, relative change |
| `reference/card_versions.csv` | 16,744 | (card, build): 598 cards × 28 builds |
| `reference/windows.csv` | 649 | `level = event`: (event, branch) where that branch carries the event (512); `level = card_patch`: one stable window per card_changes card-patch (137) |
| `reference/card_patch_fields.csv` | 326 | (card-patch, field): net old → new over the stable window, relative change, member events |

## How versions are built

**Events.** An event is one card changing on one build. `event_id` = `CARD@build`
(behavior events `CARD@build/fixN`).

- *Stable windows (v0.103.2, v0.107.1)*: each card-patch in `card_changes.csv` (artifact
  rows left out) is split into one event per beta that touched it. The betas come from the
  row's `beta_build`, the "field also changed in ..." list in `source`, the card's
  content/balance patch notes in the window, and `beta_card_changes.csv` rows in the window.
  So Parry is `PARRY@v0.100.0` (6(9) → 8(11)) and `PARRY@v0.101.0` (→ 10(14)); Capture
  Spirit is `@v0.100.0` (nerf) and `@v0.101.0` (revert); Speedster's v0.102.0 damage nerf,
  undone in v0.103.0, is its own event.
- *Per-field values*: a field one beta touched gets card_changes' old → new at that beta.
  A field several betas touched is split with the patch-note numbers: a chain of note
  steps that starts at `old` and ends at `new` gives the intermediate values (Parry,
  Untouchable, Reflect, Spoils of Battle's Forge, Cinder's damage). Upgrade deltas are
  split the same way (upgraded total − base). The notes' own numbers are also listed as
  `notes:<quantity>` fields, and update-history's as `history:<field>`.
- *After v0.107.1*: one event per (card, beta) in `beta_card_changes.csv`
  (`after_last_stable`), artifact rows left out.
- *Behavior events*: one per `behavior_changes.csv` row, `change_kind = behavior`,
  `sensitivity_only = yes`. They never change a card's version index; `card_versions`
  lists them in their own column.
- `change_kind` and `kind_source` (where the label comes from, so an analysis can keep the
  curated ones):
  - `card_changes` (134 events): the card-patch's label from `card_changes.csv`, for
    every event that carries card_changes fields (classifier plus Phil's relabels).
  - `notes-only` (12): the 12 notes-only `mechanic` rows in `card_changes.csv` (Phil's
    decision), e.g. Tyranny, Tag Team, Dazed's first step.
  - `beta_card_changes` (0): a label written in `beta_card_changes.csv`. Its only labels
    today are the `artifact` rows, which are left out, so no event uses it yet.
  - `behavior` (64): `behavior_changes.csv` rows.
  - `text rule` (116, 108 of them after v0.107.1): events known only from the notes or
    update-history, labeled by rule (`notes_kind` in the code): Added → added, Reworked/Deprecated → rework,
  numbers → tweak (cost_change for a cost), "rarity" or two rarities named → rarity_change,
  a clause without a numeric change that says now/no longer/instead/... or has its own
  before → after → mechanic, a tweak with a mechanic clause → rework (as Glow, Shatter),
  a pure "Reverted" item → revert.
- `stable_build`: the stable build in whose window the event falls; blank when
  `beta_card_changes.csv` says it was reverted before stable (Capture Spirit, Borrowed
  Time's v0.100.0 nerf and v0.101.0 revert) or it's after v0.107.1. `window_stable` keeps
  the window either way.

**Accumulation** (`carries` in the code):

- A beta build carries every event first seen on a beta at or before it (version order),
  on top of everything its last stable carries. v0.110.0 carries v0.108.0's and v0.109.0's
  events.
- A stable build carries every event of its window and of earlier windows: v0.107.1 =
  v0.103.2 + v0.104.0–v0.107.0. Reverted pairs are carried too; they net out.
- Stable-only hotfixes (v0.98.1–v0.98.3, v0.99.1, v0.103.3) carry no card events of their
  own. v0.103.3's three `behavior_changes` rows are its only events (behavior).
- Stable-only events (update-history dates the change to the stable build: Stack, and
  behavior rows dated to a stable) are carried by later stables and by betas that are both
  later in version and released on or after that date. A stable behavior row whose card
  has an earlier beta row still pending (e.g. Summon Forth: beta v0.104.0, stable copies
  v0.103.3 and v0.107.1) is that fix's stable copy (17 rows): betas carry the beta row,
  not the copy.
- `version` = index of the card's set of carried card events, numbered in release-date
  order (0 = no events yet). Parry: 0 up to v0.99.1, 1 on v0.100.0, 2 from v0.101.0
  (v0.103.2 and v0.103.3 included), 3 from v0.104.0 and on v0.107.1. A revert gets a new
  index even though the card is back to its old numbers (Capture Spirit 0 → 1 → 2); the
  event list says what happened.
- Blank version: v0.98.0 (branch unknown), update-history's v0.98.0-beta/v0.99.0-beta
  (not run builds), and betas where an event's timing is unknown (below). The `note`
  column says why.
- Cards in `card_versions` = the cached card list (577) plus cards that only appear in
  events (removed, beta-only, renamed, added after v0.107.1).

## Checks

- **Stable windows**: for v0.103.2 and v0.107.1, the events each carries beyond the
  previous stable (v0.99.1, v0.103.3), applied in order, must give card_changes' old → new
  for every field; a field that ends where it started must not be in card_changes, and
  each event must start where the previous one left the field. **0 mismatches.** For
  fields taken from one beta this only checks the accumulation (which events land on
  which stable). The notes-split fields also check that the chained note numbers reach
  the changelog's value. The build prints every mismatch, and a test breaks the check on
  purpose.
- Every stable build carries the same events as the stable before it plus its window;
  v0.103.3 = v0.103.2 for every card event (tests on synthetic histories: accumulation
  across branches, a beta revert, a hotfix with no events).
- Rebuilding twice gives identical files; the committed CSVs equal a fresh build (test).
- Fixture check for the optional view: every `primary_offers` row joins to one
  `card_versions` row, and every offer outside v0.98.0 gets a version.

## Windows (`windows.csv`)

For each event and each branch that carries it: `after_builds` = the first block on that
branch that carries it, `before_builds` = the block just before. **Clean** = the card's
event sets on the two blocks differ by this event only. For behavior events the
comparison includes the card's behavior events. Decision log rules applied:

- v0.99.0 is in no window: every v0.100.0 event's beta window is marked not clean with
  that reason (62 rows).
- Thin betas pool with a same-branch neighbour when every card's card-event set is equal
  on both (no card change event between them). The audit's thin list is v0.103.1,
  v0.105.0, v0.109.1, which gives the blocks v0.103.0+v0.103.1, v0.105.0+v0.105.1,
  v0.109.0+v0.109.1. v0.103.1's Not Yet fix doesn't block pooling (behavior only); it
  shows as a behavior flag.
- Non-release builds aren't in `builds.csv`, so they are in no window. Neither are
  v0.98.0 and the `-beta` pseudo-versions.
- `control_exclusions`: other cards of the same color (the card list's `color`;
  colorless, status, curse and event cards count as their own "character") whose
  card-event sets differ between the two blocks. `control_behavior_flags`: same-color
  cards with a behavior event in the window (sensitivity only, per the decision log).
  `behavior_in_window` / `behavior_event_ids`: the event's own card.

Stable windows compare the previous stable with the new one: v0.99.1 → v0.103.2 and
v0.103.3 → v0.107.1. On stable, a card with several events in a window gets them all at
once, so none of them is clean there at event level.

**Card-patch windows** (`level = card_patch`, stable branch only): one row per
`card_changes.csv` card-patch (card × stable build, artifact rows left out; `event_id` =
`CARD@stable/patch`, `members` = the card's card change events in that window, reverted
steps included). This is the unit of the minimum result: the net change from one stable
build to the next. Clean when the card's event sets on the two stable builds differ by
exactly the members. Net old → new per field is in `card_patch_fields.csv` (from
`card_changes.csv`; the stable-window check shows the members compose to it). Control
exclusions and behavior flags are computed as for events. **All 137 card-patch windows are
clean, including all 50 numeric tweaks** (Parry, Untouchable, Reflect too). That is
expected: the stable builds between windows (v0.103.3) carry no card events, so only a
card event on a hotfix could make one unclean. A test drops a member on purpose to check
that case is caught. Card-patches with no `card_changes` row (Capture Spirit's
nerf and revert, net zero) get no card-patch row.

## Counts

Events by kind and which clean windows they have (card events, then behavior):

| Group | change_kind | Events | Clean stable only | Clean beta only | Both | Neither |
|---|---|---|---|---|---|---|
| stable window | tweak | 55 | 23 | 5 | 24 | 3 |
| stable window | tweak+cost_change | 2 | 2 | 0 | 0 | 0 |
| stable window | cost_change | 5 | 3 | 0 | 2 | 0 |
| stable window | rework | 30 | 15 | 6 | 6 | 3 |
| stable window | rework+cost_change | 9 | 2 | 4 | 2 | 1 |
| stable window | rework+rarity_change | 1 | 0 | 0 | 1 | 0 |
| stable window | rarity_change | 4 | 1 | 0 | 3 | 0 |
| stable window | mechanic | 15 | 1 | 3 | 9 | 2 |
| stable window | text_only | 27 | 7 | 1 | 18 | 1 |
| stable window | added | 3 | 0 | 1 | 2 | 0 |
| stable window | removed | 2 | 0 | 0 | 2 | 0 |
| stable window | revert | 1 | 0 | 1 | 0 | 0 |
| after v0.107.1 | tweak | 39 | – | 39 | – | 0 |
| after v0.107.1 | tweak+cost_change | 1 | – | 1 | – | 0 |
| after v0.107.1 | tweak+rarity_change | 1 | – | 1 | – | 0 |
| after v0.107.1 | cost_change | 5 | – | 5 | – | 0 |
| after v0.107.1 | mechanic | 16 | – | 16 | – | 0 |
| after v0.107.1 | mechanic+cost_change | 3 | – | 3 | – | 0 |
| after v0.107.1 | rework | 13 | – | 13 | – | 0 |
| after v0.107.1 | rework+rarity_change | 2 | – | 2 | – | 0 |
| after v0.107.1 | rarity_change | 9 | – | 9 | – | 0 |
| after v0.107.1 | added | 19 | – | 19 | – | 0 |
| behavior | behavior | 64 | 3 | 30 | 7 | 24 |

"Clean beta" for stable-window events mostly means v0.101.0–v0.107.0 events: every
v0.100.0 event's beta window starts at v0.99.0. The stable-window tweaks include
Speedster's v0.102.0 nerf and Capture Spirit's v0.100.0 nerf (both notes-only, labeled by
rule). The 24 behavior events with no clean window are mostly the stable copies, which
land together with other fixes.

### Numeric tweaks without a clean event-level window

The minimum result's set is the 50 `tweak` card-patches in `card_changes.csv` (53 events).
**All 50 have a clean card-patch window.** At event level, 47 have a clean stable window
(one event each). Three don't:

| Card-patch | Events | Stable window | Beta window |
|---|---|---|---|
| Parry (v0.103.2) | `@v0.100.0` 6(9) → 8(11), `@v0.101.0` → 10(14) | not clean: both steps arrive together on v0.103.2 | `@v0.100.0`: none (before build v0.99.0); `@v0.101.0`: clean, v0.100.0 → v0.101.0 |
| Untouchable (v0.103.2) | `@v0.100.0` 9(12) → 7(9), `@v0.102.0` → 6(8) | not clean: both steps together | `@v0.100.0`: none (v0.99.0); `@v0.102.0`: clean, v0.101.0 → v0.102.0 |
| Reflect (v0.107.1) | `@v0.104.0` 17(21) → 16(20), `@v0.107.0` → 15(20) | not clean: both steps together | both clean: v0.103.0+v0.103.1 → v0.104.0, and v0.106.1 → v0.107.0 |

So every numeric tweak step has a clean window somewhere, except Parry's and
Untouchable's first steps. Their net stable change (Parry 6 → 10, Untouchable 9 → 6,
Reflect 17 → 15) is in the clean card-patch windows. Two notes-only
tweak events have no clean stable window either: Speedster `@v0.102.0` (undone in
v0.103.0, clean beta window) and Capture Spirit `@v0.100.0` (reverted, before build
v0.99.0: no window).

The 41 tweak events after v0.107.1 are beta-only (nothing after v0.107.1 has reached
stable). All have a clean beta window. Their sizes come from the patch notes
(`notes:<quantity>`) or update-history (`history:<field>`: Minion Sacrifice, Giant Rock).

## Ambiguous (left unresolved, not guessed)

- **Beta timing unknown** (2 events): `TEAR_ASUNDER@v0.103.2` and `SEVEN_STARS@v0.107.1`
  (text_only, labeled wording). card_changes has no beta for them and the card has no
  other event in the window. Their version is blank on the window's betas (v0.100.0–v0.103.1
  and v0.104.0–v0.107.0), with a note, and those beta windows aren't clean.
- **Which beta changed a field** (9 events, 4 cards, none a numeric tweak): update-history
  matched some fields only on the whole dict (`vars`, `upgrade`, `powers applied`) in
  several betas, and no note chain splits them. The field goes `old → ?` on the first
  beta, `? → new` on the last (`?` = not known). Borrowed Time (nerf, revert, rework in
  v0.100.0–v0.102.0: Doom, Energy, ExtraCost, upgrade energy), Cinder (`vars.CardsToExhaust`,
  v0.100.0 or v0.101.0), Spoils of Battle (`vars.Cards`, v0.100.0 or v0.101.0; `cards_draw`
  itself is v0.101.0), Rocket Punch (`description_raw`, no update-history match; spread
  over its v0.100.0 and v0.103.0 events). The events themselves (which betas the card
  changed on) aren't in doubt.
- Summon Forth's `description_raw` (v0.107.1) has no update-history match either. The card
  has one event in the window (v0.104.0), so the field is put there.
- **Event kinds by rule**: the 116 `kind_source = text rule` events are the ones to review. Examples of
  judgment calls: Blade Symphony v0.109.0 (cost 1 → 2(1), upgrade no longer adds a Shiv)
  → mechanic+cost_change; Mirage v0.111.0 → mechanic+cost_change; Sacrifice v0.110.0
  ("double → triple Osty's Max HP", no digits) → mechanic; Pillar of Creation and Mirage
  v0.110.0 (partial reverts plus a change) → rework.
- Stable-window events keep their card-patch's label, including steps whose own content
  is narrower (Shatter's v0.106.0 damage nerf is `rework` because Phil relabeled the
  v0.107.1 card-patch; its v0.105.0 "Evokes twice" step is `mechanic`).
- **Stable-only events on betas** released between the stable's version and date: none
  among card events. Behavior rows at v0.103.3 without a beta row (Bad Luck) are "may
  carry" on v0.104.0–v0.106.1 (in `note`).
- **v0.110.1** isn't on the audit's thin list (the audit's snapshot ends before it), so it
  doesn't pool with v0.110.0 (no card change between them). v0.111.0's beta windows start
  at v0.110.1 alone.
- Stardust's stable copy on v0.103.3 ("replaying Stardust for 0 Stars") is matched to its
  v0.104.0 beta row ("not correctly playing Stardust"). The texts differ, so the match may
  be wrong; it only affects behavior flags.

## Optional view

`python -m spirometry.runs build` (parser 1.4.0) adds `offers_with_version` to
`runs.duckdb` when `reference/card_versions.csv` exists: `primary_offers` LEFT JOIN
`card_versions` on (card_id, build_id), with `card_version` (INTEGER), `event_ids`,
`behavior_event_ids`. The CSV is read at query time (absolute path). Tested on the
fixture only; Phil runs it on the full build.
