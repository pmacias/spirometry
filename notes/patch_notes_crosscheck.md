# Official patch notes vs. the card patch dataset

Built 2026-09-25 from Mega Crit's patch notes as mirrored on the Slay the Spire Wiki (26
early-access pages, V0.98.1–V0.111.0, cached in `reference/raw/wiki/`, CC BY-SA 4.0).
Rebuild with `python -m spirometry.patch_notes build` (runs the cross-check too).

## Short answer

- **The tables and the notes agree closely.** Of the 128 card-patches in
  `card_changes.csv`, 115 are in the notes. Where the notes give numbers, all 69 comparable
  card-patches match (net over the window, base and upgraded values). No change goes the
  opposite way, and no size disagrees.
- **4 card-patches are labeled `tweak` but the notes describe more than a number**
  (relabeled `rework` since, per the decisions at the end; the classifier's label is kept in
  `classified_as`): Glow
  (v0.103.2, "Reworked"), Grave Warden (upgrade "no longer upgrades the Soul"), Shatter
  ("now Evokes all of your Orbs twice") and Tesla Coil ("Lightning triggers once →
  twice"), the last two in v0.107.1. These would sit in the numeric-tweak dose-response
  set unless relabeled.
- **12 changes are in the notes but not in the tables** (plus 1 reverted within beta). Most
  are changes the card data can't show: multiplayer rules, interactions, trigger order.
- **13 card-patches are in the tables but not in the notes**: parser artifacts, token cards,
  cards added or removed, and Mad Science.
- **`text_only_labels.csv` agrees with the notes on every labeled card-patch the notes
  mention** (19 of 26). Nothing to flag against the hand labels, apart from two caveats
  below (Pact's End, Summon Forth).
- **Behavior changes that appear only in bug fixes**: 64 candidate rows, 40 cards
  (`behavior_changes.csv`), e.g. Bombardment and Howl from Beyond timing in v0.104.0.
  Bombardment's is in no card field at all.
- **Beta changes that never reached stable as written**: 127 rows (`beta_card_changes.csv`),
  mostly the 94 cards changed after v0.107.1.

## Method

- `patch_notes_cards.csv` has one row per card mention (575 rows, 509 card × version), and
  an extra row per numeric change when an item gives several. Only `role = subject` rows
  count below: "Changed Tyranny card: now triggers before Bombardment" is about Tyranny;
  Bombardment is `context`.
- Notes are grouped into **stable windows**: v0.100.0–v0.103.2 roll into stable v0.103.2,
  and v0.104.0–v0.107.1 into v0.107.1 (as `card_changes.csv` does). v0.98.x–v0.99.1 are
  launch hotfixes, v0.103.3 is a stable bug-fix patch, and v0.108.0+ hasn't reached stable.
  None of those fall in a window.
- Sections counted as "in the notes": content, balance, content+balance, writing. Bug fixes
  are kept apart (`behavior_changes.csv`).
- **Numbers**: the notes' changes for a card are chained through the window per quantity
  (Parry 6(9) → 8(11) in v0.100.0, then 8(11) → 10(14) in v0.101.0, gives 6(9) → 10(14)).
  When the major-update page (v0.107.1) gives numbers, those are used instead, since they
  are already net. Numbers from before a rework or revert in the same window are dropped.
  The net base change must equal some `card_changes` field's old → new. The upgraded
  total must match the table's `upgrade.*` delta (cost upgrades are absolute).
- Major Update 1 (v0.103.2) is a prose summary ("encapsulates all of the changes from
  v0.100.0 to v0.103.1"), so v0.103.2 comparisons use the beta pages.

## Counts (`reference/crosscheck.csv`, 141 rows, one per card × stable window)

| Agreement | v0.103.2 | v0.107.1 | Total |
|---|---|---|---|
| agree: numbers match | 44 | 22 | 66 |
| agree: no numbers to compare (reworks, keywords, rarity) | 27 | 10 | 37 |
| agree: writing note (text_only change listed under Writing) | 6 | 2 | 8 |
| kind relabeled tweak -> rework (was "disagree: kind") | 2 | 2 | 4 |
| notes only: missing from card_changes | 4 | 8 | 12 |
| notes only: reverted within beta | 1 | 0 | 1 |
| table only | 6 | 7 | 13 |

(Of the 4 kind disagreements, 3 also match on numbers: Grave Warden, Shatter, Tesla Coil.
With them, 69 card-patches have comparable numbers, and all 69 match.)

## In the notes, missing from our tables

| Card | Version | What the notes say | Why the tables miss it |
|---|---|---|---|
| Beacon of Hope | v0.100.0 | Nerfed: "can no longer be stacked" | power rule, not a card field (multiplayer card) |
| Dazed | v0.100.0, v0.101.0 | status changes (enemy-applied) | status card; the effect is on enemies |
| Prepared → Prepare | v0.100.0 / v0.101.0 | reworked into Prepare, then Prepare deprecated and Prepared restored | reverted within the window; `PREPARE` existed only on v0.100.0 (103 offers in the run sample) |
| Blade of Ink | v0.105.0 | Nerfed: Inky enchantment damage +2 → +1 | the change is on the enchantment, not the card |
| Entrench | v0.106.0 | Buffed: gains extra Block from enchantments like Nimble | interaction |
| Gold Axe | v0.105.0 | Buffed: counts cards played by ALL players in multiplayer | multiplayer rule |
| Lantern Key | v0.105.0 | "something special" with multiple copies | quest card rule |
| Nightmare | v0.104.0 | Afflictions removed from the copies | interaction |
| Stratagem | v0.104.0 | no longer banned from the multiplayer colorless pool | pool change (moves offer rates in co-op) |
| Tag Team | v0.104.0 | Replay now triggers on AoE attacks | interaction |
| Tyranny | v0.104.0 | now triggers before Bombardment | trigger order |

Reverted within beta (net zero, so correctly absent): Capture Spirit (v0.100.0 nerf,
v0.101.0 revert). Borrowed Time's v0.100.0 nerf was also reverted, then reworked in
v0.102.0; the rework is in the table.

Most of these can't be read from card data, so they can't come from Spire Codex. They
matter as treatments or confounders: Stratagem changes the co-op offer pool; Entrench, Tag
Team, Nightmare and Tyranny change how the card plays. Gold Axe, Beacon of Hope and Tag
Team are multiplayer-only effects.

## In our tables, not in the notes

| Card | Stable | change_kind | Likely reason |
|---|---|---|---|
| Folly | v0.103.2 | rework (keywords) | curse; the keyword list gains Ethereal. Not in the notes: a silent change or a parser fix, unclear |
| Shiv | v0.103.2 | rework (`vars.Calculation*` → none) | token; parser (same pattern as Sacrifice) |
| Rip and Tear | v0.103.2 | rarity_change | event card; mentioned only in a v0.100.0 bug fix (softlock) |
| Mad Science | v0.103.2, v0.107.1 | text_only (labeled exclude) | template fixes; a v0.105.0 bug fix mentions it |
| Stack, Tear Asunder | v0.103.2 | text_only (labeled wording) | parser, as the labels say |
| Seven Stars, Sovereign Blade | v0.107.1 | text_only (labeled wording) | template; Sovereign Blade's text changed because of Parry's rework |
| Summon Forth | v0.107.1 | text_only (labeled mechanic) | the change is a **bug fix** (v0.104.0, v0.103.3, v0.107.1): Sovereign Blades go to hand before Forging |
| Sacrifice | v0.107.1 | rework (`vars.Calculation*` none → 0/1) | parser (patch_history.md already suspects this) |
| Scare | v0.107.1 | added | Follow Through renamed to Scare (notes: "Reworked and renamed") |
| Wither | v0.107.1 | added | Aeonglass's status card, new with the boss in v0.105.0 |

## Disagreements

No direction or size disagreements. The four kind disagreements:

| Card | Stable | Table | Notes |
|---|---|---|---|
| Glow | v0.103.2 | tweak (draw 2 → 1) | v0.100.0 "Reworked": now "Draw 1 card. Next turn, draw 1 card." |
| Grave Warden | v0.103.2 | tweak (upgrade Block +2 → +3) | upgrade also "no longer upgrades the Soul" |
| Shatter | v0.107.1 | tweak (damage 11 → 7) | v0.105.0 "now Evokes all of your Orbs twice" |
| Tesla Coil | v0.107.1 | tweak (upgrade damage +3 → +1) | "Lightning triggers increased from once → twice" |

All four have a `description_raw` (template) change in `changed_fields`, which the
classifier ignores by design. They are the only pure tweaks with a template change, so a
rule "tweak + description_raw changed → review" would have caught exactly these.

Two notes on matching: Tesla Coil's notes quote the upgraded card ("Tesla Coil+ card:
damage 6 → 4"). It matches the table's `upgrade.damage` +3 → +1 on a base of 3. Neow's Fury's
"number of cards returned now upgrades from 2 → 3" matches `upgrade.cards` none → +1.

## Against `text_only_labels.csv` (not edited)

| Label | Card-patches | In notes, and where |
|---|---|---|
| wording | 12 | 8 under Writing (agree); 4 not mentioned (Stack, Tear Asunder, Seven Stars, Sovereign Blade) |
| mechanic | 12 | 10 under Content/Balance (agree); Pact's End only in a wiki editor's "(not mentioned in patch notes)" note, as the label's basis says; Summon Forth only in bug fixes |
| exclude | 2 | Mad Science: not in content/balance; one v0.105.0 bug fix |

No label contradicts the notes. Two things to know:

- **Howl from Beyond** is labeled wording for v0.103.2 (right: v0.100.0 wording note) and
  mechanic for v0.107.1 (right: v0.106.0 trigger move). The notes also have a v0.104.0
  *bug fix* that moved its Exhaust-pile play to after the hand is drawn. That is inside
  the v0.107.1 window, so it's covered by the mechanic label.
- **Bombardment** is labeled wording for v0.103.2 (right). But v0.104.0 changed its timing
  in a bug fix, and Tyranny's v0.104.0 change alters how the two interact. Bombardment has
  **no row in card_changes for v0.107.1**, so it would count as an unchanged control card
  across that patch. It's in `behavior_changes.csv`.

## Behavior changes only in bug fixes (`reference/behavior_changes.csv`)

64 rows, 40 cards: bug-fix items that name a card as the subject, with no crash, UI, text
or localization words, and a change cue ("now", "no longer", "instead", "before/after").
It's a keyword heuristic, so the rows are candidates. `kind`:

| kind | Rows | Example |
|---|---|---|
| timing | 13 | Bombardment and Howl from Beyond play from Exhaust after the hand is drawn (v0.104.0); I Am Invincible triggers before discarding (v0.104.0); Summon Forth (v0.103.3, v0.104.0) |
| interaction | 19 | Stardust with Whispering Earring; Equilibrium with Bookmark; Reboot with Perfect Fit |
| multiplayer | 13 | Pillar of Creation, Supermassive, Arsenal proc for the Largesse player (v0.104.0) |
| generation | 8 | Not Yet, Nightmare, Transfigure, Eidolon can no longer be generated in combat (changes how often they appear mid-combat, not offers) |
| rule | 11 | Reave no longer always bottom-decks its Soul; Scrape no longer discards Star-cost cards |

Beta rows (42) show the fix's first appearance; the stable copy (22 rows, mostly v0.107.1
and v0.103.3) shows when it reached the main branch. `in_card_changes = no` for 34 of the
40 cards, so these would otherwise count as unchanged. They are candidates to drop from
control groups around the build where the fix landed, not treatments.

## Beta changes that never reached stable as written (`reference/beta_card_changes.csv`)

| status | Rows | Meaning |
|---|---|---|
| after_last_stable | 108 (94 cards) | changed on v0.108.0–v0.111.0; nothing after v0.107.1 has reached stable |
| after_last_stable; reverted in v0.110.0 | 2 | Mirage and Pillar of Creation reworks in v0.109.0, reverted in v0.110.0 |
| revised | 5 | a beta value changed again before stable: Parry 8(11) (stable 10(14)), Spoils of Battle 12(17) (stable 5(8)), Untouchable 7(9) (stable 6(8)), Speedster 1(2) (stable 2), Reflect 16(20) (stable 15(20)) |
| reverted | 4 | Capture Spirit (2 rows) and Borrowed Time v0.100.0 nerfs, reverted in v0.101.0 |
| reverts_earlier_beta | 1 | Borrowed Time v0.101.0 revert (then reworked in v0.102.0) |
| beta_only_card | 1 | Prepare (v0.100.0 only) |
| not in a stable changelog | 6 | update-history entries no changelog explains (v0.106.0–v0.106.1: Wither, Ascender's Bane, Folly, Genetic Algorithm, Summon Forth, The Scythe); fields going to `none` look like parser changes |

Rows come from the notes, plus update-history for 3 post-v0.107.1 entries the notes don't
name (Fuel via Compact, Minion Sacrifice via GUARDS!!!, Giant Rock via Primal Force) and
the 6 unexplained entries above. Because betas accumulate, a v0.110.0 run has every beta
change since v0.107.1 (see PLAN.md phase 4).

## builds.csv

The wiki lists 26 early-access pages for 25 versions (V0.99.1 has a beta hotfix page and
a stable patch page). Changes to `builds.csv`:

- **Added** (4): v0.99.0 (beta, 2026-03-12; update-history's `v0.99.0-beta` is probably
  this version), v0.103.3 (stable patch, 2026-05-29), v0.105.1 (beta hotfix, 2026-05-08),
  v0.110.1 (beta hotfix, 2026-07-31).
- **Branch filled** (4): v0.98.1, v0.98.2, v0.98.3 (stable hotfixes) and v0.99.1 (stable;
  on beta 2026-03-14, then stable 2026-03-17).
- **Date filled** (6): v0.98.1–v0.98.3, v0.99.1, v0.103.1 (2026-04-15), v0.109.1
  (2026-07-25).
- **Date conflicts, kept ours** (4): v0.105.0 (wiki 05-08, ours 05-07), v0.107.1 (06-19 vs
  06-18), v0.108.0 (07-03 vs 07-02), v0.109.0 (07-17 vs 07-16). All one day apart, the
  wiki later, probably time zones. Ours for stable v0.107.1 is the Spire Codex changelog
  date.
- **Other**: v0.103.1's page title says "Beta Hotfix" but its Type field says "Beta Patch"
  (branch beta either way). No branch conflicts.
- Still blank: v0.98.0 (launch build; the wiki's early-access list starts at V0.98.1).
- The run-data note now says export records have no `is_beta` field (it used to say the
  field was false).

## Decisions for Phil

*Decided (PLAN.md decision log) and applied by the build scripts: 1. the four → `rework`;
2. every "notes only: missing" row → a `mechanic` row in `card_changes.csv` (source `patch
notes`); 3. bug-fix changes → sensitivity analysis only; 5. parser rows kept, labeled
`artifact`. The tables above describe the comparison before those labels; `crosscheck.csv`
compares only the changelog rows, so its counts are unchanged apart from the relabels.*

1. **Relabel the four tweak/rework disagreements?** Glow is clearly a rework. Shatter and
   Tesla Coil combine a number and a mechanic. Grave Warden's upgrade change is minor. Proposed:
   Glow → rework; the other three → `rework` or a new `tweak+mechanic` label, kept out of
   the dose-response set.
2. **Notes-only changes as treatments?** Tyranny, Entrench, Tag Team and Nightmare changed
   how the card plays but have no card-field change. Proposed: add them as rows
   (`change_kind = mechanic`, source = patch notes) so they leave the control group.
3. **Bug-fix behavior changes**: drop the 40 cards from control groups only around the
   build where the fix landed, or for the whole window? Do timing fixes (Bombardment, Howl
   from Beyond, I Am Invincible, Summon Forth) get treated as treatments?
4. **Multiplayer-only changes** (Gold Axe, Beacon of Hope, Tag Team, Stratagem's pool
   change, the Largesse fix): only relevant if co-op runs are kept.
5. **Parser rows** (Folly, Shiv, Sacrifice, v0.106.1 `→ none` entries): drop them from
   `card_changes.csv` or leave them labeled?
