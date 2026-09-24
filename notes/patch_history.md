# Patch history endpoints: first look

Checked 2026-09-24 from a cloud session. 7 requests in total (changelog list, two changelog
details, four card histories), spaced a few seconds apart. The raw responses are in
`patch_history_samples/`, saved unmodified.

## Short answer

Both endpoints give **before/after values** for every change, and the combination supports
the design. There are two catches:

1. **The two endpoints use different clocks.** `/api/update-history` dates each change to the
   **beta patch** where it first appeared (e.g. `V0.104.0`, "Beta Patch", 2026-04-23).
   `/api/changelogs` groups changes by **Spire Codex site release**, and a game-data release
   there matches the **stable** rollout (e.g. site 1.2.0 = stable v0.107.1, 2026-06-18),
   bundling several betas' worth of changes together. So a change has a beta date and a
   later stable date. That's the staggered-rollout setup, but we have to build the mapping
   ourselves.
2. **Neither endpoint is a clean list of game changes.** The changelogs mix real balance
   changes with site-side re-extraction noise (compendium order, text template fixes). The
   update-history is cleaner but shortens text and sometimes collapses fields.

## `/api/changelogs`

- The list returns 27 entries (`changelogs.json`): `tag`, `date`, `game_version` (actually the
  **site** version, 1.0.0–1.3.0), `build_id`, `title`, `summary` counts.
- `build_id` (the numeric Steam build) is filled for only 2 of 27 entries: 1.0.0 (`22238966`)
  and 1.2.0 (`23811903`). The game version (`v0.107.1`) appears only in the free-text title.
- Many entries are site-only releases (new features, SEO) with 0 changes. Others show large
  "changed" counts that are re-extraction fixes, not patches (1.0.1 "Description fixes":
  531 changed; 1.0.4 "SEO overhaul … data fixes": 978 changed).
- Detail: `GET /api/changelogs/{tag}` returns `categories` (cards, relics, monsters, powers,
  encounters, events, enchantments, potions, afflictions), each with `added`, `removed`, and
  `changed`. Each changed entity lists `{field, old, new}` as **strings** (numbers are strings
  too; missing is `"none"`; upgrades are `"+4"`).
- `from_ref` / `to_ref` are git refs (`v1.0.20` → `current`, `origin/main` → `current`). So a
  changelog is a diff between two data extractions, not a patch note.
- Noise: of 57 changed cards in 1.2.0, **17 changed only `compendium_order`**. In 1.1.0 it was
  **57 of 140**. Text-only template edits (`description_raw` only, e.g. `MAD_SCIENCE`,
  `SEVEN_STARS`) are also common.

## `/api/update-history/cards/{ID}`

A list of `{version, type, date, changes[]}`, newest first.

| Card | Version | Type | Date | What changed | Kind |
|---|---|---|---|---|---|
| Bulwark | V0.105.0 | Beta Patch | 2026-05-07 | Block 13 → 12 (upgrade 16 → 15) | numeric nerf |
| Debilitate | V0.100.0 | Beta Patch | 2026-03-19 | Damage 7 → 10 (upgrade 9 → 12) | numeric buff |
| Debilitate | V0.106.0 | Beta Patch | 2026-05-21 | Debilitate power 3 → 2 | numeric nerf |
| Conflagration | V0.104.0 | Beta Patch | 2026-04-23 | 8 dmg + 2 per other Attack → 2 dmg × 4 hits | rework |
| Drum of Battle | V0.104.0 | Beta Patch | 2026-04-23 | 0-cost Power (exhaust top card each turn) → 1-cost Skill (gain 2 energy when exhausted) | rework |

- **Build ID:** a version string only (`V0.104.0`), with no Steam `build_id`. It matches run
  files' `build_id` (`v0.104.0`) after lowercasing. It names the **beta** build.
- **Date:** yes, one per entry (day resolution).
- **Before/after:** yes, but `changes` is a list of **preformatted strings**
  (`"Block: 13 → 12"`), not structured fields. Descriptions are cut at ~50 characters and
  markup is stripped. For Debilitate V0.106.0, the before and after descriptions look
  identical because the difference falls after the cut. One entry is lossy:
  `"Vars: 3 fields → 3 fields"`. `description_raw` diffs are left out.
- The same diffs appear in the changelogs as structured `{field, old, new}`. **Correction
  (later check):** changelog text values are truncated as well (cut at ~80 characters with
  `...`), so neither endpoint has full description text. Conflagration and Drum of Battle's V0.104.0 changes and Debilitate's
  V0.106.0 change are all in changelog 1.2.0 (stable). Debilitate's V0.100.0 buff is in
  changelog 1.1.0 (2026-04-16, "Major Update #1 drops on stable"), about 4 weeks after its beta
  date.
- All 4 samples were "Beta Patch". Still unknown: whether stable-only hotfixes get their own
  entries, and how early builds (v0.98.x–v0.99.x, which are in the export) are covered. The
  earliest entry seen was V0.100.0.

## Reworks vs. numeric tweaks

They look clearly different in the diff, so a rule can sort them:

- **Numeric tweak:** only numeric fields move (`damage`, `block`, `vars.X`,
  `powers_applied[i].amount`, `upgrade.X`), and description text changes only in the numbers.
  The var *set* stays the same, and `description_raw` (the template) doesn't change.
- **Rework:** the var set changes (fields go to or from `"none"`: `vars.Repeat none → 4`,
  `vars.ExtraDamage 2 → none`), or `type`, `cost`, `hit_count`, `keywords`, or
  `powers_applied[i].power` changes, along with a `description_raw` change.
- **Not a gameplay change:** `compendium_order` only; `description_raw` only when the
  rendered `description` is unchanged (pluralization or markup fixes).

Borderline cases need a hand check: cost-only changes (Monarch's Gaze, Fusion), rarity changes
(Predator, Acrobatics; these also change the offer rate, so they matter for the offer-rate
check), and upgrade-only changes (Untouchable, Royalties).

## Follow-up: full pull (all 579 cards, all 27 changelogs)

Built into `reference/` by `src/spirometry/patch_history.py`; see SPIROMETRY.md.

- **Game vs. parser changelogs.** Only 1.1.0 (stable v0.103.2, "Major Update #1": "full
  rollup of beta content from v0.100.0 through v0.103.1 landing on stable") and 1.2.0
  (stable v0.107.1) carry game changes. The 1.0.x and 1.1.2 card diffs are parser fixes.
  1.3.0 says the changelog endpoint now mirrors Steam patch notes and that beta versions have
  their own changelogs — those aren't in the `/api/changelogs` list.
- **Entity typing.** Changelog details group entities under `categories[].id` (cards,
  relics, monsters, powers, events, encounters, enchantments, afflictions, potions, epochs,
  orbs, characters, intents, modifiers, stories). `FAKE_*` ids are all under relics
  (`FAKE_ANCHOR`, ...) and monsters (`FAKE_MERCHANT_MONSTER`).
- **update-history.** 218 of 579 cards have entries; the rest return 404 `No update
  history`. All 307 entries are typed "Beta Patch", including V0.103.2, the stable release.
  Labels sometimes name the whole dict (`Vars: 3 fields → 3 fields`) instead of the field.
  Card additions/removals appear as `Added.` / `Removed.`.
- **Stable hotfixes are not tracked.** No history entry for v0.98.1–v0.98.3, v0.99.1,
  v0.103.1, or v0.107.1. v0.103.1 and v0.99.1 are only mentioned in changelog prose.
- **Earliest version:** `V0.98.0-beta` (2026-03-05), then `V0.99.0-beta` (2026-03-12),
  13 cards each. On every one of those cards the V0.99.0-beta entry exactly reverses the
  V0.98.0-beta entry (e.g. Beat Into Shape damage 5 → 10, then 10 → 5), so they net to zero.
  Real history starts at V0.100.0 (2026-03-19).
- **Text truncation, corrected.** Changelog description values are truncated too: 1,624 of
  4,208 description values end in `...` at exactly 80 characters.
- **Inconsistencies.** Update-history dates the 1.1.2 parser fixes as game changes:
  35 `upgrade_description`-only entries at V0.103.2 (e.g. Bash upgrade "Apply 2 → 3
  Vulnerable", a text fix) and 13 `can_be_generated_in_combat: none → no` entries at
  V0.104.0 (2026-04-23), though changelog 1.1.2 introduced that field on 2026-04-20.
  Sacrifice's 1.2.0 `vars.CalculationBase` / `CalculationExtra` `none → 0/1` has no history
  entry at all (probably parser-side).

## Implications for the pipeline

- Build the change table from the **changelog details** (structured, every entity
  type). Use **update-history** to date each change to its beta version.
- Build a small hand-checked table: game version → branch (beta/stable) → release date.
  Stable versions come from changelog titles and the run data's `is_beta` + `build_id`.
- Treatment is keyed on the run's `build_id`, so the dates matter less than the
  version → change mapping. The dates matter for event-time plots and calendar-time controls.
- Pulling everything: about 26 changelog detail calls, plus update-history per changed entity
  (hundreds of calls). That's fine at 15/min without a key, but do it once and cache it in
  `data/` (git-ignored) or commit the small derived table.
- Rate headers on these endpoints: `x-ratelimit-limit: 300`, served through the Cloudflare
  cache (`cf-cache-status: HIT`). This is separate from the export's 120/h credit budget.
