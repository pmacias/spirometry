# Spirometry triage, Part 1 (sections A–F)

Read-only investigation, 2026-10-07. Inputs: saved outputs of notebooks 02–05,
`data/analysis/*.parquet|csv`, `reference/*.csv`, `notes/`, `src/`, the docs. Nothing under
`data/runs/`, `sts2_snapshot/` or `reference/raw/` was opened; no notebook was run; no
existing file was changed. Scripts are in `triage/scripts/` (each says how to run it, and
each runs in seconds); `triage/scripts/plots.py` draws the B, B2 and D figures into
`triage/figures/` for Phil to run (not run here). Nothing here is a result until Phil reads it and reruns it in a
notebook.

Tags: **[computed]** = I ran it here (script named); **[inferred]** = reasoning from computed
or documented numbers; **[unverified]** = a claim I could not check with Tier 1 access.

Status: Part 1 complete (A–F, interim read, notes for Part 2). G and H not started (Part 2).

---

## A. Reconcile

Script: `triage/scripts/a_reconcile.py` (recomputes the docs' headline numbers from the saved
fits). Notebook outputs were read with `triage/scripts/dump_notebook.py` (hashed IDs redacted).

**The main finding of A: the saved outputs and the docs describe different run tables.**
[computed] Notebooks 02 and 03 print `build_info` as parser 1.7.0, built
2026-10-02 22:32 UTC, `records_read` 1,871,830 (the 1,513-page tables had 1,511,837 records).
Every file in `data/analysis/` was written 2026-10-02 15:50–19:23 local time, after that
build (commit 198a6d8 "Rebuild pipeline and re-run notebooks"). SPIROMETRY.md "Phase 5
results", "Anticipation" and PLAN.md item 7 still quote the 1,513-page (2026-09-29) numbers.
The placebo section says "1,513-page tables", but `placebo_main.parquet` was written
2026-10-02 18:27, about 3 hours after the rebuild, and its real-tweak comparison uses the
rebuilt `did_main.parquet`; so it almost certainly ran on the rebuilt tables [inferred from
file times; the parquet has no build stamp]. How many export pages the rebuild covers is not
recorded in what I can read (the docs' "about 1,800 pages" on 2026-10-07 is a later state);
left blank.

Everything below in this triage uses the saved (rebuilt) fits.

| Quantity | Docs (1,513 pages) | Saved outputs (rebuild) | Where |
|---|---|---|---|
| Dose-response slopes, weeks 0–3 | 1.44 ± 0.19 / 0.04 ± 0.31 | **1.413 ± 0.193 / 0.025 ± 0.310** | nb04 cell 4; a_reconcile |
| Same, all weeks | 1.52 ± 0.20 / 0.19 ± 0.32 | 1.496 ± 0.199 / 0.241 ± 0.318 | a_reconcile; dose_sensitivity.csv factor 1 |
| One slope (weeks 0–3) | 1.04 ± 0.18 | 1.016 ± 0.175 | a_reconcile |
| τ, Q (one slope) | ≈0.24, Q = 1,102 on 36 | τ² 0.059 (τ 0.24), Q = 1,249 on 36 | a_reconcile |
| Buff / nerf slopes | 1.60 ± 0.37 / 0.46 ± 0.40 | 1.57 ± 0.37 / 0.44 ± 0.40 | a_reconcile |
| Clearly nonzero, all weeks | 23 of 26 / 7 of 17 | **22 / 8** | nb02 cell 38; a_reconcile |
| Clearly nonzero, weeks 0–3 | 21 / 7 | 21 / 8 | nb02 cell 38 |
| Toward the change among clearly nonzero (all weeks) | 18 of 22 / 7 of 7 | 18 of 21 / 8 of 8 | a_reconcile |
| Same, weeks 0–3 (the horizon the dose line uses) | not in docs | 17 of 20 / **5 of 7** | a_reconcile |
| Median \|β\|, all tweaks, all weeks | 4.7 / 1.5 | 4.3 / 1.5 | nb02 cell 38 |
| Median \|β\| on the line (weeks 0–3) | 4.2 / 1.5 ("about a third") | **4.1 / 1.9 (about half)** | nb02 cell 52 |
| Median SE on the line (log-odds) | 0.052 / 0.051 | 0.048 / 0.050 | nb02 cell 52 |
| Upgrade-only placebo, Royalties | −3.0 ± 1.2 (2.6σ) | −2.6 ± 1.1 (2.4σ) | a_reconcile (did_main) |
| Upgrade-only placebo, Untouchable v0.107.1 | −1.5 ± 0.5 (3.2σ) | **−2.0 ± 0.44 (4.5σ)** | a_reconcile |
| Serpent Form placebo | +0.05 ± 1.1 | −0.28 ± 1.05 | a_reconcile |
| Drop top 10 uploaders, median shift | 0.04 SE | **0.17 SE** (max 1.08) | a_reconcile |
| Tagged only / untagged only, median shift | 1.92 / 0.47 SE | 2.55 / 0.59 SE (63% beyond 2 SE) | a_reconcile |
| Tagged vs untagged corr, χ² | 0.68, 79 on 43 | 0.75, 101 on 43 | a_reconcile |
| No group terms / drop shared screens / drop flagged | 0.10 / 0.04 / 0.02 SE | 0.07 / 0.05 / 0.01 SE | a_reconcile |
| Largest effects (pp) | CW −16.4, LS +10.3, Untouchable −9.5, Pinpoint −9.1 | −15.8, +10.0, −9.2, −8.9 (Parry +14.7 same) | a_reconcile |
| Offers per stable build (v0.99.1 / v0.103.2 / v0.103.3 / v0.107.1) | 3.36M / 3.80M / 2.12M / 7.18M | 4.01M / 4.33M / 2.24M / 9.48M | nb02 cell 12 |
| Solo run_keys with >1 record; dedup-removed rows | 124; 4,130 | 149; 4,905 | nb02 cells 4–5 |
| Anticipation: informative tweaks | 14 (3 + 11); 10 with nonzero main | **15 (3 + 12)**; 11 | nb03 cell 8, 13 |
| Anticipation medians (ratio to main) | −0.11 / −0.25 | +0.03 / −0.14 | nb03 cell 13 |
| Anticipation table entries | e.g. Refine Blade −0.9, Patter +3.5, Furnace +5.9 | −1.6, +3.9, +5.8; Hyperbeam now informative | anticipation_main.parquet |
| Pooled-before examples (Furnace, Crescent Spear, Reflect) | 0.0 → +4.1, +0.9 → +2.4, +1.6 → −0.2 | +1.6 → +5.8, +1.5 → +3.0, +1.5 → −0.7 | did_second_patch_checks.parquet |

Other inconsistencies:
- **The five exclusions.** [computed] The prompt's count is right: 38 on the line = 24 + 14,
  and the saved fits leave off exactly Leading Strike, Serpent Form (first patch), Reflect,
  Royalties, Untouchable v0.107.1 (second). SPIROMETRY.md "Dose-response" names only four
  ("Leading Strike, Reflect, Royalties, Serpent Form"). The cause is mechanical: notebooks 02
  and 04 print "left off" by `card_id`, and Untouchable's v0.103.2 tweak is on the line, so
  the v0.107.1 one disappears from the printout. The fit itself is right.
- [computed] Counts check out: 50 tweaks, 43 solo-estimable (26 + 17), 7 not estimable
  (5 first-patch, 2 second), 3 upgrade-only, 2 mixed (nb05 cell 6).
- SPIROMETRY.md contradicts itself on the all-weeks slopes (1.52/0.19 under Dose-response,
  1.50/0.24 under Placebo calibration): different tables, per the main finding.
- The second patch's 7 clearly nonzero estimates "all go the expected way" holds for all
  weeks (8 of 8 on the rebuild). On weeks 0–3, which feeds the dose line, it is 5 of 7, and
  only 7 of the 14 second-patch tweaks on the line point toward their change (first patch
  20 of 24). [computed]
- Notebook 04 prose (cell 20) gives v0.107.1's release as 2026-06-18 (builds.csv); the wiki
  page date in `patch_notes_cards.csv` is 2026-06-19, the same day the tooltips arrived per
  SPIROMETRY.md. Not a contradiction (builds.csv says stable dates are Spire Codex dates, an
  upper bound), but the "day after" timing of the tooltip hypothesis depends on which date.
- Notebook 02's top-uploader cells print hashed uploader IDs in saved outputs (cells 27, 41).
  Already on PLAN.md's release checklist (item 12); noting it because it is still there.

Nothing above was fixed.

---

## B. The ruler puzzle

Script: `triage/scripts/b_rulers.py h3` (weeks 0–3, the horizon of the dose line; `main` for
all weeks). Nine rulers: notebook 04's seven plus two new ones, (new − old) in units of the
kind's typical |new − old|, and the mean of the base and upgraded card's ln change. Every
ruler is one point in a sensitivity range; none is preferred. Slopes are in each ruler's own
units, so compare z and the unit-free ratio slope2 / slope1.

**Do the patches contain comparable tweaks?** Mostly yes. [computed]

| | First (24) | Second (14) |
|---|---|---|
| damage / block / power amount / other | 12 / 4 / 4 / 4 | 6 / 2 / 3 / 3 |
| median \|ln\| (all; power amount; other) | 0.17; 0.41; 0.37 | 0.18; 0.41; 0.29 |
| median \|new − old\| | 1 | 1 |
| median old value (damage) | 8.5 | 12 |
| share nerfs | 21% | 21% |
| also changed the upgraded card (same direction) | 8 | 1 (Death March) |

**Every ruler, weeks 0–3** [computed]:

| Ruler | slope1 (z) | slope2 (z) | z diff | slope2 / slope1 [95%] | τ² |
|---|---|---|---|---|---|
| ln(new/old) (baseline) | 1.41 (7.3) | 0.03 (0.08) | −3.80 | 0.02 [−0.41, 0.45] | 0.052 |
| outcome in pp, ln dose | 0.21 (8.0) | −0.00 (−0.06) | −4.23 | −0.01 [−0.41, 0.39] | 0.001 |
| absolute (new − old) | 0.05 (2.2) | 0.02 (0.32) | −0.42 | 0.42 [−2.21, 3.04] | 0.077 |
| rank | 1.14 (7.3) | 0.04 (0.16) | −3.91 | 0.03 [−0.37, 0.44] | 0.051 |
| percent | 1.40 (7.9) | 0.03 (0.11) | −4.02 | 0.02 [−0.38, 0.43] | 0.048 |
| ln / kind's median \|ln\| | 0.22 (4.8) | 0.04 (0.45) | −1.89 | 0.17 [−0.58, 0.93] | 0.069 |
| sign only | 0.35 (5.6) | 0.03 (0.32) | −3.13 | 0.07 [−0.39, 0.54] | 0.059 |
| NEW: (new − old) / kind's median \|new − old\| | 0.14 (4.0) | 0.01 (0.15) | −1.30 | 0.10 [−1.17, 1.37] | 0.069 |
| NEW: mean of base and upgraded ln | 1.38 (7.2) | 0.03 (0.09) | −3.74 | 0.02 [−0.42, 0.46] | 0.053 |

Range: z for slope2 −0.06 to 0.45; z for the difference −4.23 to −0.42; ratio 0.0 to 0.42.
All weeks (`main`): z for slope2 0.75 to 1.06, z diff −3.64 to +0.07, ratio 0.16 to 1.09,
same ordering of rulers. [computed]

**Why the absolute ruler kills the difference.** [computed] Under (new − old), the first
patch's own slope is weak (z 2.2), and one tweak sets it: Grand Finale (+10 damage on a
50-damage card, x = 10, effect −0.42 log-odds). Dropping it alone moves slope1 by +5.6 of its
SEs and z diff to −2.5. Within damage cards the absolute ruler predicts nothing (pooled kind
slope 0.007 ± 0.025 per point of damage). So z ≈ −0.4 does not mean the patches look alike on
that ruler; it means absolute change does not order effects in either patch, and the ratio's
interval (−2.2 to 3.0) carries no information. Under the two per-kind rulers, the big
power-amount doses are shrunk to "one typical change", patch 1's slope falls to z 4–5, and the
difference to z −1.3 to −1.9 with wide ratio intervals (up to 0.9–1.4).

**Is patch 1's slope carried by a few big power-amount changes?** Not on the ln ruler.
[computed] Leave-one-out on slope1 (ln): the largest pulls are Parry (−0.94 SE), Anticipate
(+0.76), Untouchable (+0.54), Danse Macabre (−0.53); z diff stays −3.45 to −4.05. Dropping the
named five (Parry, Fight Me, Anticipate, Corrosive Wave, Debilitate; note Debilitate's first
patch change is damage 7 → 10, not a power amount): slope1 1.28 ± 0.29, z diff −3.0 (ln),
−0.5 to −3.5 across rulers. Dropping all 8 first-patch power/other tweaks: slope1 1.18 ± 0.32,
z diff −2.7 (ln). Dropping power/other from both patches leaves 16 + 8 and z diff −0.96 (ln),
with slope2 0.49 ± 0.63: the difference fades there mainly because patch 2 has 8 points left
and its slope's SE doubles, not because slope1 collapses.

**Kind mix.** [computed] One slope per kind (pooled over patches) plus one common patch-2
slope difference d: on ln, d = −1.53 ± 0.40 (z −3.8), so the patch difference is not a kind-mix
artifact on that ruler; on ln / kind's median |ln|, z −2.4; on absolute, z −0.8. Kind slopes
(ln): power amount 1.81 ± 0.29, damage 1.27 ± 0.42, block 1.24 ± 0.52, other 1.05 ± 0.33.

**A ruler-free fact.** [computed] On the sign ruler (no size at all) the difference is z −3.1.
Mean effect in log-odds, weeks 0–3: first patch buffs +0.28 (19), nerfs −0.41 (5); second
patch buffs +0.06 (11), nerfs +0.01 (3). In the second patch the buffs are barely picked
more than the nerfs, whatever ruler is used for size. (All weeks: +0.14 and −0.03.)

**How much of "patch 2 is flat" depends on the ruler.** [computed/inferred]
- "Patch 2 shows no detectable dose-response": holds on every ruler (z for slope2 between
  −0.1 and 0.5 at weeks 0–3, below 1.1 at all weeks). But no ruler's SE is small enough to
  rule out a modest slope: the ratio's upper bound is 0.39–0.93 on the scale-preserving and
  per-kind rulers.
- "Patch 2's slope is smaller than patch 1's": clear (|z| > 3) on six of nine rulers (ln,
  pp outcome, rank, percent, sign, base+upgrade mean), weak (|z| 1.3–1.9) on the two per-kind
  rulers, absent on absolute change, where patch 1 has no clear slope either. All weeks it is
  weaker throughout (ln z −3.3).
- The sign-only result means the difference does not depend on how size is measured; it
  depends on whether size is measured in a way that lets the big ln changes (power amounts,
  Forge) count as big.

---

## B2. Mixed tweaks and dose measurement

Script: `triage/scripts/b2_mixed.py h3`. Doses for Leading Strike and Reflect are written in
the script before any fit; their effects are printed only for the record.

### What the main-field dose does not capture

Card text from the committed changelog samples (`notes/patch_history_samples/changelog_1.1.0.json`,
`changelog_1.2.0.json`; descriptions there are cut at ~80 characters) and the patch-note
wording in `reference/patch_notes_cards.csv`; field changes from `card_patch_fields.csv`.

- **Mixed direction (flagged in tweak_sizes):**
  - Leading Strike (patch-note label "Buffed"): "Deal 7 damage. Add 1 Shiv" → "Deal 3 damage.
    Add 2 Shivs" (upgraded 10 → 6, still 2 Shivs). **Shiv = 4 damage is verified** from the
    same changelog ("Deal 4 damage.", upgraded Shiv 6). [computed] So at Strength 0 the total
    printed damage is unchanged, 11 → 11 (upgraded 14 → 14), and Phil's formula
    ln((11 + 3S) / (11 + 2S)) is right for the printed numbers. Not in that formula: each Shiv
    is an extra 0-cost card play that exhausts, which interacts with Shiv and card-play
    synergies; that is a further buff the dose does not see. [inferred]
  - Reflect (label "Nerfed" in v0.104.0, v0.107.0 and v0.107.1 notes): Block 17 → 15, upgrade
    delta +4 → +5, so **the upgraded card's total also falls, 21 → 20**. [computed] Reflect is
    flagged mixed because its upgrade delta rose, but both the base and the upgraded card were
    nerfed. In card terms it is not mixed.
- **Changed upgrade delta, same direction** (on the line): Anticipate (upgraded 5 → 3 Dex),
  Collision Course (12 → 15), Danse Macabre (4 → 6), Grand Finale (60 → 75), Kingly Kick
  (30 → 35), Parry (9 → 14), Pinpoint (22 → 19), Untouchable v0.103.2 (12 → 8); second patch
  only Death March (4 → 6 per card drawn). The dose uses the base card. The ruler "mean of base
  and upgraded ln" changes nothing (z diff −3.74). [computed]
- **Scaling variables** (`vars.CalculatedDamage` / `CalculationBase`): Memento Mori (8 → 9,
  plus 4 per card discarded) and Crescent Spear (6 → 8, plus 2 per card with a star): the base
  is a fraction of the damage dealt, so ln(base) overstates the card-level change. [inferred]
- **"Other" main fields:** Corrosive Wave (Poison per card drawn this turn 3 → 2; per-trigger,
  so proportional), Glitterstream (11 Block now plus next-turn Block 4 → 5: the card's Block
  goes 15 → 16, ln 0.065, against the dose's 0.223), Wrought in War (7 damage plus Forge
  5 → 7), Refine Blade (Forge 6 → 9 plus 1 energy next turn), Furnace (Forge 4 → 5 every
  turn), Death March (8 damage plus 3 → 4 per card drawn), The Scythe (13 damage, permanent
  growth per play 3 → 4).
- **Power amounts:** Anticipate (Dexterity this turn), Danse Macabre (Block per 2+-cost card),
  Fight Me (self-Strength 2 → 3 on a card that also deals 5 × 2 and gives the enemy 1
  Strength), Parry (Block per Sovereign Blade), Debilitate v0.107.1 (debuff duration
  3 → 2 turns on a 10-damage card), Juggernaut (damage per Block gain), Sic 'Em (Osty summon
  2 → 3 on a card whose Osty damage is unchanged).

**Dose coverage** (my hand classification from that text, made after seeing notebook 05's
effects, so not blind; sensitivity only) [computed counts, inferred labels]: "whole" = the
changed number is the card's whole effect or a per-trigger amount it is proportional to;
"component" = the card keeps other value unchanged, so ln of the changed number overstates the
card-level change; "scaling" = base or increment of a state-dependent total.

| | First | Second |
|---|---|---|
| whole | 11 | 3 (Furnace, Hyperbeam, Juggernaut) |
| component | 12 | 8 |
| scaling | 1 (Memento Mori) | 3 (Crescent Spear, Death March, The Scythe) |

The second patch has proportionally more partial-coverage doses (11 of 14 against 13 of 24).
Kind mix is similar (above).

### Leading Strike and Reflect as sensitivity variants (primary keeps both off)

[computed] Weeks 0–3, ln ruler, slope per patch:

| Variant | slope1 | slope2 | diff | z diff |
|---|---|---|---|---|
| PRIMARY (both off) | 1.413 ± 0.193 | 0.025 ± 0.310 | −1.39 | −3.80 |
| LS at S = 0 / 1 / 2 / 3 (x = 0, 0.074, 0.125, 0.163) | 1.37 / 1.41 / 1.42 / 1.43 | 0.025 | −1.35 to −1.41 | −3.22 / −3.41 / −3.52 / −3.60 |
| LS naive (x = −0.847) | 0.69 ± 0.23 | 0.025 | −0.67 | −1.29 |
| Reflect at −0.125 / −0.087 / −0.049 | 1.413 | −0.010 / −0.005 / 0.000 | −1.41 to −1.42 | −4.08 / −4.03 / −3.98 |
| LS (S = 0..3) + Reflect (any of the three) | 1.37–1.43 | −0.010 to 0.000 | −1.37 to −1.44 | −3.38 to −3.87 |
| LS naive + Reflect (any) | 0.69 | −0.01 to 0.00 | −0.69 to −0.70 | −1.38 to −1.43 |
| Sign ruler: primary / LS +1 / Reflect −1 / both | 0.345 / 0.353 / 0.344 / 0.353 | 0.026 / 0.026 / 0.010 / 0.010 | | −3.13 / −3.10 / −3.54 / −3.50 |

Over all 23 ln variants: slope1 0.69–1.43, slope2 −0.01–0.03, z diff −4.08 to −1.29;
without the naive Leading Strike dose, z diff −4.08 to −3.22. [computed]

**Do the conclusions depend on these two cards?** Only through the naive Leading Strike dose,
which every other source (label, card text, damage arithmetic) says has the wrong sign. With
any label-consistent dose, slope1 moves by at most 0.04, slope2 by 0.035 and z diff stays
between −3.2 and −4.1. τ² rises when Leading Strike is added at a small dose (0.052 → 0.058–0.069):
its large effect at a near-zero dose is scatter the line cannot explain. [computed]

### A rule for mixed tweaks in future patches (written without looking at effects)

> A tweak is *mixed* only if the card's total printed output, in the unit of its main field,
> moves in a different direction for the base and the upgraded card, or if two changed numbers
> on the card are in different units and move in opposite directions. Its direction is the
> patch-note label. Its dose is ln(new total / old total) for the un-upgraded card at Strength 0
> (and Dexterity 0), counting cards it generates at their printed values. If that dose is 0 or
> has the opposite sign of the label, the tweak stays off the line and enters only the sign
> ruler. A range of game-state doses (as Phil's Strength 0–3) is reported as sensitivity, never
> as the primary dose.

What it does: **Leading Strike**: total 11 → 11 at Strength 0, dose 0 against label "Buffed":
off the line, +1 on the sign ruler (as now). **Reflect**: base total 17 → 15 and upgraded
21 → 20 move the same way, so it is not mixed; it goes on the line at −0.125 (z diff −4.08 in
the table above). **No other tweak** in the two patches is mixed under the rule (every other
changed upgrade delta moves the same way as its base, checked above). [inferred from the
listed text]

### Measurement error in the dose

- **Direction.** [inferred] If the dose is the true size plus noise unrelated to it (classical
  error), the slope is multiplied by λ = var(true) / var(observed) < 1: pulled toward zero,
  never past it. If instead the dose systematically overstates the change for some tweaks
  (partial-coverage cards: Glitterstream's 0.223 for a 0.065 change in total Block), those
  tweaks sit too far right, which also flattens a line through them.
- **Could it make patch 2 flat?** For patch-2-only error to take slope2 from patch 1's value to
  its upper 95% bound (ratio 0.45) needs λ ≈ 0.45, error variance 1.2 times the true dose
  variance; to the point estimate (0.02) needs λ near 0, a dose that is almost all noise.
  [computed arithmetic] The two patches use the same kinds of fields, so error that large in one
  patch only is implausible [inferred]. Partial coverage is more common in patch 2 (11 of 14
  against 13 of 24). Adding a term x × partial to the slope-per-patch model gives a negative
  coefficient (−0.50 ± 0.40, not clearly nonzero) and reduces z diff for the "whole" tweaks from
  −3.8 to −2.4 (slope2 for whole tweaks 0.50 ± 0.49, resting on 3 second-patch points). Dropping
  the 4 scaling tweaks: z diff −3.37. [computed; classification not blind]
- **Reading.** Dose measurement error can plausibly explain part of the gap (it points the
  right way, and patch 2 has more partial-coverage doses), not a near-zero slope by itself.
  Not claimed as the cause.

---

## C. Calibrated errors

Script: `triage/scripts/c_calibrated.py`. Factors from `placebo_diagnostics_summary.csv`, one
row per (window, pseudo card): robust sd 4.33 (first) / 2.09 (second); plain sd 4.69 / 2.46;
pooled 3.05 (robust) and 3.68 (sd) as single factors.

**`placebo_diagnostics_dose_sensitivity.csv` interpreted.** [computed, reproduced] It is on
the all-weeks fits (`did_main`), not weeks 0–3. Factor 1: slope1 1.50 ± 0.20, slope2
0.24 ± 0.32, τ² 0.055. Robust factors: 1.31 ± 0.18 and 0.25 ± 0.24, τ² 0.026. Plain sd:
1.29 ± 0.19 and 0.25 ± 0.25, τ² 0.024. The file has no difference column; with the
coefficient covariance: z diff −3.34 (factor 1), −3.46 (robust), −3.35 (sd).

**Weeks 0–3 (the dose line's horizon) and every factor set** [computed]:

| SE inflation | slope1 | slope2 | diff (z) | τ² shared | separate τ² (first / second), z diff |
|---|---|---|---|---|---|
| none | 1.41 ± 0.19 | 0.03 ± 0.31 | −1.39 ± 0.37 (−3.80) | 0.052 | 0.063 / 0.019, −4.81 |
| robust sd by patch (4.33 / 2.09) | 1.18 ± 0.18 | 0.04 ± 0.23 | −1.15 ± 0.30 (−3.87) | 0.021 | 0.036 / 0.011, −4.14 |
| sd by patch (4.69 / 2.46) | 1.16 ± 0.18 | 0.04 ± 0.23 | −1.12 ± 0.30 (−3.77) | 0.018 | 0.031 / 0.007, −4.07 |
| one factor 3.05 | 1.28 ± 0.19 | 0.04 ± 0.32 | −1.25 ± 0.37 (−3.35) | 0.037 | 0.050 / 0.000, −4.35 |
| one factor 3.68 | 1.23 ± 0.19 | 0.04 ± 0.32 | −1.19 ± 0.37 (−3.18) | 0.030 | 0.044 / 0.000, −3.85 |
| additive placebo variance (0.032 / 0.012 log-odds²) | 1.42 ± 0.23 | 0.03 ± 0.31 | (−3.67) | 0.039 left | |

All weeks: z diff −2.89 to −3.46 with a shared τ², −3.65 to −4.28 with separate τ².

**Why the error bars barely widen.** [computed numbers; inferred mechanism] The per-tweak
clustered SEs are tiny next to the between-tweak scatter: median se² ≈ 0.0025 against
τ² ≈ 0.052 (log-odds²), so each point's weight is set almost entirely by τ². τ² is estimated
by method of moments from the excess of the observed scatter over the stated se², so when the
se's are inflated, τ² falls by roughly what was added: under the robust factors the median
per-point variance goes from 0.054 to 0.065 (first patch) and to 0.032 (second patch: its
factor is smaller, and τ² is shared, so the second patch's points end up *more* precise
than before). The slope SEs change by −25% to +5%. The random-effects model was already
absorbing the excess spread the placebos found, which is what τ² is for. The placebo
miscalibration matters a lot for per-tweak "clearly nonzero" counts and hardly at all for the
meta-regression.

**Does "patch 2 differs from patch 1" survive?** [computed] Yes, on the ln ruler: z between
−3.2 and −3.9 (weeks 0–3) under every inflation, and −3.7 to −4.8 with a τ² per patch. The
honest error bar for the difference is about ±0.30–0.37 log-odds per unit ln around −1.1 to
−1.4. This does not change B's ruler dependence; it only says the error calibration is not
what drives the result.

**Two numbers worth keeping.** [computed]
- Separate τ² per patch: first 0.063, second 0.019 (honest SEs); second-patch τ² goes to 0
  under a single inflation factor. The second patch's real tweaks scatter no more than
  placebo-scale noise allows.
- Spread of effects in log-odds (all-offers fits, one row per pair): real first-patch tweaks
  sd 0.50 against placebo sd 0.18; real second-patch tweaks sd 0.13 against placebo 0.12. In
  the second patch, changed cards moved about as much as unchanged cards move anyway (this
  matches `placebo_diagnostics_vs_real_by_patch.csv`: median |β| 1.5 against 1.4 points, 1 of
  17 with empirical p < 0.05).

### Why placebo z has sd ≈ 4 when clustered SEs assume 1: hypotheses

What the saved placebo fits can show (463 one-per-pair rows; 860 including repeats):

| Diagnostic [computed] | Result | Bears on |
|---|---|---|
| Window-level shocks: sd of the 9 windows' mean z vs within-window sd | 0.34 vs 3.85 | Shared shocks to a whole character-window cancel (the controls absorb them). The spread is card by card. |
| Does placebo \|β\| shrink with the SE? sd of β by SE tercile | first 2.4 / 4.1 / 3.2 pp; second 1.6 / 2.1 / 2.2 pp (SE 0.45–1.15 pp) | β spread does not shrink with precision; sd(z) falls with SE (5.3 → 3.0; 3.1 → 2.0). |
| Fit β² = a + b·se² | first: additive sd 2.8 pp + factor 2.4; second: 1.6 pp + 1.5 | Both: a card-level component that does not average away with more runs, plus extra noise proportional to the SE. |
| Same pseudo card in both patches (95 cards): corr of its z | **+0.45** | Card-level drift persists across windows months apart: cards trend. |
| Clustered / robust SE in the placebo fits | median 1.03 (0.98–1.38) | Within-run correlation is small. |
| Placebo β by base pick rate | weak (corr −0.08 first, +0.12 second) | No strong regression to the mean by popularity. |
| By patch | sd z 4.7 (first) vs 2.5 (second) | Either more drift in March–May, or spillover from the first patch's larger real changes. |

Hypotheses (none claimed as the cause):
1. **Card-specific trends over calendar time** (players learning cards, guides and tier lists,
   tooltips, meta settling). Fits the additive component, the cross-patch persistence (+0.45)
   and the larger first-patch spread (earlier in early access). A before/after DiD with
   two blocks counts any such trend as an effect. [inferred; saved diagnostics support it, run-level
   data needed to show it: placebo event studies / pre-trends, a within-build time trend
   per pseudo card]
2. **Spillover from the patch's real changes**: unchanged cards that substitute for or combine
   with changed cards move when those cards move. Would make first-patch placebo spread larger
   (bigger real changes): observed, but hypothesis 1 predicts the same. [inferred; needs
   run-level: shared-screen or same-deck exposure of each pseudo card to the window's changed
   cards]
3. **Shocks shared within an uploader** (one heavy uploader's habits) that clustering by
   run_key does not capture. Would add a multiplicative component that grows with an uploader's
   share; consistent with the factor of 1.5–2.4. Dropping the top 10 uploaders moved real
   estimates by a median 0.17 SE, and only ~15% of records carry a token. [needs run-level:
   clustering by uploader_hash on the token subset; Part 2]
4. **Shared week or day shocks** (a video or patch-note discussion on one date moving one
   card). Card-specific and time-varying; the same family as 1 at a finer grain. [needs
   run-level: week × card terms for placebo cards]
5. **Population or mix change between the blocks** (tagged share, ascension, act mix), when
   cards are picked differently by different players. Group terms absorb tagged vs untagged
   only. Timing-balance and card-act checks on real tweaks were small. [needs run-level:
   `card_act_fe` or ascension-by-card terms on placebo fits]
6. **Cards sharing a screen** with a changed card in the after block (competition). The real
   tweaks' `drop_shared_screens` moved estimates by 0.05 SE, so probably small for placebos too.
   [inferred; placebo version needs run-level]

The saved diagnostics discriminate a window-level shock (ruled out) and an additive card-level
component (present, and persistent across patches) from pure within-run correlation (small).
They cannot separate learning trends (1, 4) from spillover (2), uploader clustering (3) or mix
change (5).

---

## D. Power by simulation

Script: `triage/scripts/d_power.py` (settings fixed in its header before running: 1,000
simulations per planted slope per setting, seed 20261007, detection = two-sided α = 0.05,
i.e. |estimate / se| > 1.96; runs in about a second). Weeks 0–3 fits, the 38 line tweaks.
Patch 2's 14 points are replaced by (a + c) + b·x + noise with the observed x and SEs and the
fitted τ²; patch 1 is kept as observed (default) or also simulated from its fitted line
(`--simulate-first`); the project's meta-regression is refitted each time. Placebo-inflated
= SEs × 4.33 (first) and × 2.09 (second).

[computed] Default (patch 1 as observed):

| Setting (τ² generating) | Planted slope2 | Mean est. (2.5–97.5%) | Median se | Detect slope2 ≠ 0 | Detect slope2 ≠ slope1 |
|---|---|---|---|---|---|
| honest (0.052), slope1 1.41 | 0 | 0.01 (−0.64, 0.62) | 0.33 | 4% | 98% |
| | 0.3 | 0.30 (−0.34, 0.89) | 0.33 | 13% | 87% |
| | 0.7 | 0.69 (0.10, 1.30) | 0.33 | 54% | 45% |
| | 1.0 | 0.99 (0.32, 1.58) | 0.33 | 85% | 15% |
| | 1.44 | 1.45 (0.82, 2.06) | 0.33 | 99% | 1% |
| placebo-inflated (0.021), slope1 1.18 | 0 | 0.00 (−0.43, 0.45) | 0.25 | 3% | 99% |
| | 0.3 | 0.28 (−0.17, 0.76) | 0.25 | 19% | 89% |
| | 0.7 | 0.71 (0.23, 1.15) | 0.25 | 81% | 28% |
| | 1.0 | 1.00 (0.54, 1.45) | 0.25 | 98% | 4% (planted < slope1 by 0.18) |
| | 1.44 | 1.44 (0.95, 1.92) | 0.25 | 100% | 6% (planted > slope1) |
| extra: honest SEs, patch-2-only τ² (0.019) | 0 / 0.3 / 0.7 / 1.0 / 1.44 | unbiased, sd ≈ 0.20 | 0.31 | 0% / 7% / 68% / 97% / 100% | 100% / 98% / 49% / 6% / 0% |

With patch 1 also simulated (`--simulate-first`, honest): slope2 ≠ 0 detected 8% / 18% / 63%
/ 90% / 100%, difference detected 96% / 88% / 51% / 22% / 6%. The 8% at a planted 0 (and 92–94%
interval coverage) says the DerSimonian–Laird-type meta-regression on 14 + 24 points is
slightly overconfident; worth knowing, not large.

**Answer.** [computed] Yes, a patch-1-sized slope in patch 2 would have been seen: planted at
1.44 it is detected as nonzero in 99–100% of simulations under every setting, and the
simulated estimates' 2.5th percentile (0.82 honest, 0.95 inflated) is far above the observed
0.025. A slope half the size (0.7) is detected about half the time with honest SEs and 81%
with inflated SEs. A flat patch 2 against patch 1 is detected 96–99%. So "patch 2 could not
have shown a dose-response at this size" is ruled out on the ln ruler; slopes up to about 0.3
(a fifth of patch 1's) would usually go unseen. This is conditional on the ln ruler and on
the model (B).

**For Part 2 (subset reuse).** [computed, assumption flagged] `--se-scale` multiplies the
second patch's SEs, `--se-scale-first` the first's; pass `--tau2 0.0517` (the full-data value)
and `--simulate-first`, otherwise the refit τ² shrinks to absorb the same observed scatter and
the noise barely grows. Previews, assuming the token subset's SEs are 2.6× larger (√(1/0.15),
from ~15% of records carrying a token; not measured): planted 1.44 detected 98.5%, a flat
patch 2 against patch 1 detected 89%. With the second patch's SEs 4× larger (its before block
has the thinnest fill, 6.4%): 95% and 82%. Because τ² (card-to-card scatter, ≈ 0.05) dwarfs
se² (≈ 0.0025), even several-fold larger SEs cost little power for the slopes, provided the
subset still has all 38 tweaks with estimable effects.

---

## E. The second patch's before block

Scripts: `triage/scripts/e_before_block.py` (dose line under notebook 02's before-block
variants), `triage/scripts/e_pretrends.py` (pre-release trends from `event_studies.parquet`
against dose).

**What the saved fits cover.** `did_second_patch_checks.parquet` has the 17 second-patch
tweaks under "main" (v0.103.3 before; identical to `did_main`, checked), "pooled before"
(v0.103.2 + v0.103.3) and "no first-patch controls". All three are **all-weeks** fits, so
they compare with the all-weeks dose line, not weeks 0–3. Log-odds conversion uses the main
design's p(1 − p), approximate for "pooled before"; the pp-scale fit needs no conversion.

[computed]

| Before block | slope2 (log-odds) | z diff (log-odds) | slope2 (pp) | z diff (pp) | toward the change (14) |
|---|---|---|---|---|---|
| v0.103.3 (main) | 0.24 ± 0.32 | −3.35 | 0.036 ± 0.044 | −3.64 | 11 |
| v0.103.2 + v0.103.3 | 0.24 ± 0.29 | −3.72 | 0.040 ± 0.041 | −3.86 | 12 |
| v0.103.3, no first-patch controls | 0.25 ± 0.32 | −3.32 | 0.037 ± 0.044 | −3.62 | 11 |

**The second patch's dose-response is the same under all three.** Pooling v0.103.2 moves
single cards a lot (Furnace +1.6 → +5.8 pp, Juggernaut 0.0 → +2.2, Crescent Spear
+1.5 → +3.0, Reflect +1.5 → −0.7; SPIROMETRY.md quotes the 1,513-page values) but not in a
way related to dose. Dropping first-patch controls changes nothing (as the docs say).

**Pre-release trends against dose** [computed]: weighted slope of each tweak's before-build
weekly gaps (weeks before release, against week −1), regressed on its dose.
- First patch (4 pre-weeks each): pre-trend on dose −1.26 ± 0.56 pp/week per unit ln
  (z −2.2); buffs drifting −0.15, nerfs +0.36 pp/week on average. Buffed cards were already
  slightly falling and nerfed ones rising: a selection-on-trend pattern (developers adjust
  cards that are losing or gaining ground). If those trends continued, they work *against*
  the measured effects, so the first patch's slope would be understated, not inflated.
  [computed; interpretation inferred]
- Second patch (2 pre-weeks each): +1.7 ± 3.2 pp/week per unit ln (z 0.5). Per-tweak pre-slope
  SEs are 1.1–3.7 pp/week, so a drift of 2 pp/week (8 points over four weeks, larger than most
  second-patch effects) can't be excluded for most cards. The saved data cannot test
  before-block drift in the second patch. [computed]

**So:** neither the control-set choice nor the before-block choice changes the second patch's
slope; drift *within* v0.103.3 remains untested because the block is too short to estimate a
trend. Drift would flatten the line only if it were related to dose (as it is, in the
opposite direction, in the first patch). [inferred]

**Run-level fits that would test it (not run; for Part 2 to decide):**
1. *Fake patch inside the old card versions.* DiD with before = v0.103.2, after = v0.103.3
   (no card changes between them; drop Stardust and Summon Forth as in notebook 03), for the
   14 second-patch line tweaks and the window's controls, weeks 0–3 after v0.103.3's release.
   Regress the fake effects on the eventual doses: a slope here is a dose-related trend that
   predates the patch. Tooling: `did.load_block_data(con, color, "v0.103.2", "v0.103.3")`
   and `fit_did(..., max_week_after=3)`; five color loads (≈ 5 s each, per notebook 02's
   timings) plus 14 fits (≈ 3–4 s each): about 1–2 minutes.
2. *Pooled-before, weeks 0–3.* The table above at the dose line's own horizon:
   `fit_did(..., max_week_after=3)` on `load_block_data(con, color, "v0.103.2 v0.103.3",
   "v0.107.1")` for the 17 tweaks: about 2 minutes.
3. *Detrended DiD.* Treated × linear calendar-week trend estimated on the pooled before
   block (≈ 9 weeks instead of 2), then the weeks 0–3 effect net of the extrapolated trend.
   Not in `did.py` (no trend option in `fit_did`); a small new function, then ≈ 1–2 minutes
   of fitting. Same for the first patch for symmetry (≈ 2 minutes).
Memory: each color load is 2–3 million offer rows (notebook 02 prints 1.5–2.8M per window);
pooled loads about 1.7×. Run one color at a time, as notebook 02 does.

---

## F. Spillover: the sign of same-offer substitution bias

Script: `triage/scripts/f_spillover.py` (direction of the existing `drop_shared_screens` shift).

**Setup.** A reward screen shows about three cards and the player takes at most one. Same-offer
substitution: when one card on the screen becomes more (less) attractive, the others on that
screen are taken less (more). Let s be the share of control offers that share a screen with
the treated card, and δ the treated card's true effect.

1. **Pick rate of a nerfed card** (DiD against same-color controls). [inferred] The nerf
   lowers the treated card's pick rate (δ < 0). On shared screens, some of the players who no
   longer take it take a control instead, so the controls' pick rate *rises* by about s × (the
   share of the lost picks that go to a co-offered card, not to skipping) × |δ|. The DiD
   subtracts the controls' change: estimate ≈ δ − (a positive number), more negative than δ.
   **The bias is away from zero**, not toward it. A buff is the mirror image (controls fall,
   estimate too large). The same holds for substitution across screens within a run (a deck
   that took the buffed card needs fewer of its substitutes later). Only complements (cards
   picked together, e.g. synergy partners) push the other way, toward zero.
2. **Pick rate of an unchanged control** (as a placebo or a spillover outcome). [inferred] Its
   estimated "effect" has the opposite sign to the change of the cards it shares screens with:
   a buff elsewhere makes it look nerfed. The placebo fits drop the window's real treated card
   from the data, but the pseudo card's own picks on screens it shared with changed cards are
   still there, so placebo β's carry this spillover from every card changed in the window. It
   would be larger in the first patch, where real changes were larger (C, hypothesis 2).
3. **Win rate.** [inferred] In the strength-change design (IV before vs after, net of the
   controls' median change), a control's effect is measured against what runs would otherwise
   have taken on that screen. After a buff to X, that alternative includes a better X where X
   was co-offered, so controls' measured effects fall; subtracting their median makes X's net
   change *larger*: away from zero again, and small (only co-offered screens count). The
   within-build ITT / IV has no before/after, so substitution there is part of the estimand
   ("X against what it displaced", already stated in SPIROMETRY.md), not a bias.

So "spillover pulls estimates toward zero" is backwards for the pick-rate DiD with same-color
controls under substitution; toward zero applies to complements, or to controls that move
with the treated card for other reasons.

**Reconciliation with `drop_shared_screens`.** [computed] Dropping the control offers that
shared a screen with the treated card (about 2% of offers in the fit, 0.5–5.8% by tweak)
shrinks |β| for 33 of 43 tweaks and 27 of 30 clearly nonzero ones, by a median 0.03 pp
(largest Leading Strike, 10.01 → 9.83; Untouchable v0.103.2, −9.22 → −9.09). Regressing the
shift on β gives −0.008: dropping shared screens takes off about 0.8% of each effect. That is
the sign derived above (shared-screen substitution inflates |β|) and confirms it is small: the
0.05 SE median shift in the docs is small because s is small, not because the bias points
toward zero. Cross-screen (within-run) substitution is not removed by this check; its size is
not measured. A bound: `control_scope="other"` (other characters' cards, no shared runs) has
no substitution at all; those fits are not among the saved files (`did_ctrl_*` absent), so
comparing scopes needs a run (PLAN item 7(n)).

---
## Interim read (Part 1 evidence only)

What the Part 1 evidence does to each explanation for the flat second patch. "Weakens" means
the evidence makes it a poor explanation of the *patch difference*; it may still matter
elsewhere.

| Explanation | Part 1 verdict | Evidence |
|---|---|---|
| **Ruler** (dose definition) | **Partly supports; not the whole story.** | Patch 2's own slope is near zero on all nine rulers. The patch *difference* is clear on six rulers, weak on the two per-kind rulers, absent on absolute change, where patch 1 has no clear slope either (B). It survives the sign-only ruler (z −3.1) and a kind-slope model (z −3.8). It depends on letting big ln changes (power amounts, Forge) count as big. |
| **Dose measurement error** | **Open; can explain part, not a near-zero slope alone.** | Right direction (toward zero); patch 2 has more partial-coverage doses (11/14 vs 13/24); an x × partial term cuts z diff for whole-card tweaks to −2.4. A near-zero slope would need patch-2 doses to be mostly noise (B2). Classification not blind. |
| **Power** | **Weakened.** | A patch-1-sized slope in patch 2 is detected in 99–100% of simulations; a flat patch 2 is distinguished from patch 1 in 96–99%. Slopes up to about 0.3 would usually go unseen (D). |
| **Miscalibrated errors** | **Weakened as the explanation of the difference; real for per-tweak claims.** | Inflating each patch's SEs by its placebo sd leaves z diff −3.2 to −3.9 (separate τ²: −3.9 to −4.8); τ² absorbs the excess (C). But second-patch tweaks scatter about as much as unchanged cards do (sd 0.13 vs 0.12 log-odds), so second-patch per-card "effects" are mostly indistinguishable from drift. |
| **Before-block drift** | **Open.** | Control set and pooled-before variants leave patch 2's slope unchanged (E). Two pre-weeks cannot detect a 2 pp/week drift. In patch 1, pre-trends *were* dose-related (buffed cards falling, z −2.2), so dose-related drift is plausible in principle; its direction there would hide effects, not create them. Needs the fake-patch fit (E, run-level 1). |
| **Spillover** | **Weakened.** | Same-screen substitution pushes estimates away from zero by about 1% (F); it would scale with the effects in both patches and cannot flatten one. |
| **Novelty fade** | **Weakened as stated; timing open.** | No novelty bump in either patch: intercept −0.02 ± 0.05, patch-2 shift +0.07 ± 0.09 log-odds (weeks 0–3). If anything, patch 2's effects show *more* at all weeks (slope 0.24; 11 of 14 toward the change) than at weeks 0–3 (0.03; 7 of 14): slower to appear, not fading. [computed; interpretation inferred] |
| **Population change** (who played v0.103.3 / v0.107.1; tooltips) | **Open.** | Not testable with Tier 1. Tagged-only fits diverge more on the rebuild (median shift 2.55 SE). Part 2. |
| **Patch really did less** (or players responded less) | **Consistent with everything here; not separable from "players responded less" with pick rates.** | Patch-2 buffs vs nerfs differ by 0.05 log-odds against 0.69 in patch 1; real patch-2 effects are about as dispersed as placebo drift; median \|β\| 1.5 vs placebo 1.4 points. |

Side results:
- The upgrade-only placebos, put on the placebo scale (÷ 2.09, the second patch's robust
  sd): Royalties −2.4σ → −1.2, Untouchable v0.107.1 −4.5σ → −2.2. Within or at the edge of
  the spread unchanged cards show. [computed arithmetic; the factor comes from all-offers
  fits, these are un-upgraded offers of upgrade-only cards]
- The placebo spread is mostly card-level and persistent across windows (+0.45), which reads
  more like cards trending in popularity than like a clustering defect. [computed / inferred]

## Notes for Part 2

1. **Rebaseline first.** All the docs' Phase 5, Anticipation and placebo numbers quote the
   1,513-page tables; every saved output is from the 2026-10-02 rebuild (1,871,830 records).
   The synthesis should quote one set (the rebuild's, unless Part 2 reruns), and record the
   rebuild's page count, which I could not read (A).
2. **The token subset is not pointless on power grounds**, provided it still has estimable
   effects for most of the 38 tweaks. τ² (≈ 0.05) dwarfs se² (≈ 0.0025), so 2.6× larger SEs
   still detect a patch-1-sized slope 98.5% of the time (D). Before fitting, count treated
   offers per tweak and block in the token subset (v0.103.3 has only 6.4% fill). Rerun
   `d_power.py --simulate-first --tau2 0.0517 --se-scale <measured> --se-scale-first <measured>`
   with the measured SE ratios.
3. **Clustering by token will only address part of the placebo spread.** The placebo β² fit
   has an additive part (1.6–2.8 pp, card-level, does not shrink with n) and a multiplicative
   part (×1.5–2.4). Uploader clustering can explain at most the multiplicative part (C). A
   within-token replication tests population change, not the error calibration.
4. **The cheapest decisive test of before-block drift is the fake patch** (E, run-level fit 1:
   v0.103.2 → v0.103.3, 14 tweaks, ≈ 1–2 min). It is also a natural within-build-style
   negative control for H's pre-declared list.
5. **Fix the horizon in advance.** Patch 2 looks different at weeks 0–3 vs all weeks (slope
   0.03 vs 0.24; toward the change 7 of 14 vs 11 of 14). Any new fit in G/H should say which
   horizon is primary before it runs.
6. **Spillover is away from zero.** Do not carry "toward zero" into the synthesis (F).
7. **Mixed-tweak rule.** Under the proposed rule Reflect is not mixed and joins the line at
   −0.125 (z diff −4.08); Leading Strike stays off. Shiv = 4 damage is now verified, so the
   "not yet verified" note in SPIROMETRY.md can be closed when Phil edits the docs (B2).
8. **Pre-trends are dose-related in patch 1** (z −2.2, against the change). If H or the
   synthesis discusses trend bias, it points toward understating patch 1, not inflating it (E).
9. Notebook 02's saved outputs still show hashed uploader IDs (cells 27, 41); relevant if any
   Part 2 output quotes those cells.

---
---

# Part 2 (sections I, J, K, L, G, H and the final synthesis)

Session of 2026-10-08. Tier 2 access as granted in the Part 2 brief: `data/runs/runs.duckdb`
opened with `read_only=True` only (its views read the Parquet files under `data/runs/`;
nothing else in `data/` or `sts2_snapshot/` was opened). Aggregates and fit estimates only;
no run-level IDs are printed or written. New scripts in `triage/scripts/`, card-level
estimates (keyed by `card_patch_id`) in `triage/out/`. Primary horizon for every new fit and
dose line: **weeks 0–3 after release**, declared before running; other horizons are shown
beside it as secondary.

Status: Part 2 complete (I, J, K, L, G, H and the final synthesis below).

**Card colors without `reference/raw/`.** [computed] `did.card_colors()` reads
`reference/raw/cards.json`, which the triage may not open (and the sandbox blocks).
`triage/scripts/db.py` rebuilds the map from the run tables: a card's color is the character
whose primary reward screens hold ≥ 90% of its offers, among cards with ≥ 1,000 offers (about
170 mod cards without a "-" in their id reach `primary_offers` with ≤ ~100 offers each; the
first attempt let 7 of them in as Defect controls and was off by 9 offers in the Uproar fit);
`card_changes.csv`'s color wins where it has the card (so Entrench and Exterminate, "event"
cards now, stay out, as in `did.py`). It is patched into `did` in-process (src/ untouched).
Check: refitting `did_h3` for one tweak of each character (Uproar, Bulwark, Pounce,
Juggernaut, Sic 'Em) reproduces beta, SE and `n_offers` exactly (beta to 10 digits, SE to
1e-10). Every Tier 2 fit below uses this map.

**Page count of the rebuild** (left blank in A). [computed] `build_info`: `pages_parsed`
1,873 (pages 0–1,872), `records_read` 1,871,830, built 2026-10-02 22:32 UTC.

---

## I. Fake patch: v0.103.2 → v0.103.3 (before-block drift)

Script: `triage/scripts/i_fake_patch.py` (spec in its header, fixed before running; output
`triage/out/i_fake_patch.csv`). Choices where TRIAGE.md E was not explicit: each of the 14
treated cards is fit with `fit_did` on its **real** v0.107.1 `card_patch_id`, so the treated
card, the control set (windows.csv's for the real window, i.e. cards changed in v0.107.1 are
not controls) and the model are the main analysis's; only the builds change (before =
v0.103.2, after = v0.103.3; weeks from v0.103.3's release, `max_week_after=3`). Stardust and
Summon Forth are removed from the data; Bad Luck has no character color and is never loaded.
No card changed between the two builds (`window_changes` finds 0). Runtime measured before
the full run: about 4 s per character load and 2–4 s per fit; the full run took 74 s, peak
memory 4.0 GB.

[computed] Weeks 0–3 (primary). β in pp; log-odds for the line; "real" = the tweak's actual
weeks 0–3 effect at v0.107.1 (did_h3):

| Card | eventual x | fake β (pp) ± SE | z | fake log-odds | real log-odds |
|---|---|---|---|---|---|
| Debilitate | −0.406 | −0.50 ± 0.87 | −0.57 | −0.026 | +0.118 |
| Patter | −0.118 | +1.43 ± 0.68 | +2.12 | +0.078 | −0.171 |
| Bulwark | −0.080 | +0.58 ± 1.07 | +0.54 | +0.023 | +0.092 |
| Hyperbeam | +0.074 | +0.86 ± 0.86 | +1.01 | +0.102 | −0.057 |
| Synthesis | +0.154 | −0.12 ± 0.66 | −0.18 | −0.011 | +0.081 |
| Unrelenting | +0.154 | −0.21 ± 0.76 | −0.28 | −0.012 | +0.244 |
| Pounce | +0.154 | +1.23 ± 0.63 | +1.95 | +0.106 | +0.146 |
| Uproar | +0.182 | −1.11 ± 0.40 | −2.75 | −0.129 | +0.291 |
| Juggernaut | +0.182 | +3.94 ± 1.12 | +3.52 | +0.231 | −0.099 |
| Furnace | +0.223 | +6.30 ± 1.03 | +6.14 | +0.301 | −0.028 |
| Death March | +0.288 | −1.88 ± 0.69 | −2.74 | −0.166 | +0.094 |
| The Scythe | +0.288 | +1.84 ± 1.28 | +1.44 | +0.097 | −0.054 |
| Crescent Spear | +0.288 | +2.37 ± 0.56 | +4.20 | +0.178 | −0.034 |
| Sic 'Em | +0.406 | −0.98 ± 0.90 | −1.09 | −0.053 | +0.107 |

- **Fake slope on the eventual dose: +0.05 ± 0.18 log-odds per unit ln (z +0.26)**;
  intercept +0.04 ± 0.04; τ² 0.015. With SEs × 2.09: +0.05 ± 0.17. All weeks (secondary;
  v0.103.3 was the current stable for about 3 weeks, so this adds almost nothing): +0.04 ±
  0.18. [computed]
- **Clearly nonzero fake effects:** honest SEs, 6 of 14 with |z| > 2 (3 beyond 3); z ÷ 2.09,
  2 of 14 (none beyond 3). What the second patch's placebo spread predicts (206 window ×
  pseudo-card pairs, `placebo_main.parquet`, one row per pair): |z| > 2 in 43.7% → 6.1 of
  14; |z| ÷ 2.09 > 2 in 14.1% → 2.0 of 14. The fake patch matches the placebo spread
  exactly. [computed]
- Fake effects point toward the eventual change for 7 of 14 (coin-flip). Their spread
  (sd 0.131 log-odds) equals the spread of the **real** second-patch effects (sd 0.131).
  [computed]
- **Fake and real effects are strongly negatively correlated: −0.66.** [computed] Cards
  that rose against their controls from v0.103.2 to v0.103.3 fell from v0.103.3 to
  v0.107.1, and the reverse (Furnace +0.30 then −0.03, Juggernaut +0.23 then −0.10, Crescent
  Spear +0.18 then −0.03; Uproar −0.13 then +0.29, Death March −0.17 then +0.09). Both
  differences share the v0.103.3 block with opposite signs, so a card-level deviation in
  v0.103.3 (a short-lived shock, or simply that block's card-level noise) shows up in both
  with opposite sign. [inferred] Adding the two (an approximate v0.107.1-against-v0.103.2
  effect, weeks differ; SEs combined as independent) gives a slope of +0.09 ± 0.16 on the
  eventual dose: still flat. [computed arithmetic; approximation]

**Reading.** [inferred] A clearly nonzero fake slope would have meant dose-related drift in
the before block; there is none (+0.05 ± 0.18, an interval that excludes patch 1's 1.41 by a
wide margin). The number of large fake effects is exactly what unchanged cards show in that
period. So "drift in v0.103.3 hides a real patch-2 dose-response" is **weakened**: the drift
that exists is card-level noise unrelated to dose, of the same size as the real patch-2
effects. Two further facts matter for the synthesis: (1) the real patch-2 effects are no
more spread out than a patch with no changes at all (sd 0.131 for both); (2) v0.103.3 card
levels are noisy enough that a card's real effect is partly the mirror image of its v0.103.3
deviation (corr −0.66). Comparing against v0.103.2 instead does not recover a slope (+0.09 ±
0.16, approximate; Part 1's all-weeks pooled-before fit gave 0.24 ± 0.29). This is one
fake-patch window; it tests drift between these two builds, not every possible drift.

---

## J. Regression to the mean in patch 1

Script: `triage/scripts/j_reversion.py` (Tier 1 only: `event_studies.parquet` and `did_h3`;
definitions fixed in its header before running). `event_studies.parquet` holds each tweak's
gap to its controls per (week, block) cell in pp, from the **all-weeks** event-study fits,
relative to the before block's week −1. Pre-movement = gap at week −1 minus gap at week −4,
converted to log-odds with the tweak's p(1 − p) as in did_h3.

### J1. Pre-release movement, patch 1 (24 line tweaks) [computed]

| Card | x | pre-move (log-odds) ± SE | weeks 0–3 effect (log-odds) | opposes the change? |
|---|---|---|---|---|
| Anticipate | −0.406 | +0.051 ± 0.056 | −0.280 | yes |
| Corrosive Wave | −0.406 | −0.204 ± 0.097 | −0.629 | no |
| Untouchable | −0.406 | −0.014 ± 0.047 | −0.375 | no |
| Flick Flack | −0.154 | +0.001 ± 0.049 | −0.358 | yes (≈ 0) |
| Pinpoint | −0.125 | −0.213 ± 0.076 | −0.414 | no |
| Hemokinesis | +0.069 | −0.089 ± 0.092 | +0.329 | yes |
| I Am Invincible | +0.105 | +0.043 ± 0.119 | +0.145 | no |
| Sculpting Strike | +0.118 | −0.171 ± 0.095 | −0.004 | yes |
| Solar Strike | +0.118 | −0.042 ± 0.053 | −0.117 | yes |
| Patter | +0.118 | +0.044 ± 0.072 | +0.343 | no |
| Memento Mori | +0.118 | −0.074 ± 0.098 | −0.315 | yes |
| Kingly Kick | +0.118 | −0.098 ± 0.097 | +0.211 | yes |
| Skewer | +0.134 | −0.155 ± 0.144 | +0.000 | yes |
| Gather Light | +0.134 | +0.041 ± 0.045 | +0.102 | no |
| Heirloom Hammer | +0.162 | −0.295 ± 0.143 | +0.025 | yes |
| Grand Finale | +0.182 | −0.379 ± 0.164 | −0.417 | yes |
| Collision Course | +0.201 | −0.286 ± 0.093 | +0.838 | yes |
| Glitterstream | +0.223 | +0.000 ± 0.066 | +0.313 | no |
| Danse Macabre | +0.288 | −0.129 ± 0.141 | +1.234 | yes |
| Wrought in War | +0.336 | −0.205 ± 0.072 | +0.054 | yes |
| Debilitate | +0.357 | −0.153 ± 0.092 | +0.401 | yes |
| Refine Blade | +0.406 | −0.207 ± 0.064 | +0.320 | yes |
| Fight Me | +0.406 | −0.268 ± 0.095 | +0.653 | yes |
| Parry | +0.511 | −0.092 ± 0.110 | +1.272 | yes |

- **17 of 24 pre-movements oppose the patch-note direction** (6 of the 8 beyond 2 SE). Buffs
  fell before release (mean −0.13 log-odds over the three weeks); nerfs also fell on
  average (−0.08: Corrosive Wave and Pinpoint fell, i.e. moved *with* their nerf). So the
  "opposes" pattern is carried by the buffs.
- Size: median |pre-movement| 0.11 log-odds (1.1 pp) against a median |weeks 0–3 effect|
  of 0.32 (4.1 pp); median pre SE 0.09, so most single pre-movements are within noise.
  corr(pre, x) −0.32 (the dose-related pre-trend of E); corr(pre, effect) −0.05.

### J2. Continuation or reversion: effect ~ dose + pre-movement [computed]

Patch 1's 24 tweaks, random-effects meta-regression as in the main analysis (declared
model):

| Model | slope on x | pre-movement coefficient | τ² |
|---|---|---|---|
| effect ~ x (same 24 points) | 1.42 ± 0.21 | | 0.063 |
| **effect ~ x + pre (declared)** | **1.54 ± 0.23** | **+0.80 ± 0.47 (z +1.7)** | 0.064 |
| sensitivity: pre = 3 × weighted pre-slope (weeks −5 to −1) | 1.63 ± 0.21 | +1.44 ± 0.46 (z +3.1) | |
| sensitivity: declared model without Grand Finale (largest \|pre\|) | 1.50 ± 0.23 | +0.34 ± 0.52 | |

- **The pre-movement coefficient is positive, not negative.** Cards that fell before
  release show *smaller* (more negative) effects afterwards, not bigger ones: the pre-release
  movement looks like a trend that continued, not a dip that reverted. The declared estimate
  is not clearly nonzero (z 1.7); the slope-based sensitivity is (z 3.1); without Grand
  Finale it shrinks to +0.34 ± 0.52. Under no variant is it negative. [computed]
- **Slope on dose rises once pre-movement is in the model** (1.42 → 1.54, or 1.63 with the
  pre-slope): adjusting for the pre-trend makes patch 1 steeper, not flatter. [computed]
- Caveats. [inferred] (1) The pre-movement is measured with error (median SE 0.09 against a
  median |pre| of 0.11), which pulls its coefficient toward zero; the sign is the informative
  part. (2) Week −4 and week −1 are inside the DiD's before block, so the two variables share
  some sampling noise; with the before block's other weeks this coupling is weak, and it
  cannot by itself produce a positive coefficient of this size. (3) 24 points.
- **Reading.** [inferred] The data favour continuation over reversion. Part 1's note 8 (if
  the pre-trends continued, patch 1's effects are *understated*) is the reading the data
  support; "patch 1 is inflated by regression to the mean" is **weakened**. It is not ruled
  out (z 1.7 on the declared model).

### J3. Later weeks [computed]

`event_studies.parquet` gives post-release cells week by week (all-weeks fits). v0.103.2 was
the current stable from 2026-04-16 to v0.103.3's release on 2026-05-29: **weeks 0–5 are
complete inside v0.103.2**, week 6 holds one day before v0.103.3 (and late v0.103.2 play),
weeks 7+ have under ~50 treated offers per cell (stragglers; not used). Slope per week of y =
cell gap minus the weighted mean of the before cells (log-odds; cells with ≥ 200 treated
offers):

| Post week | 0 | 1 | 2 | 3 | 4 | 5 | 6 (partial) |
|---|---|---|---|---|---|---|---|
| tweaks | 24 | 24 | 24 | 24 | 24 | 24 | 22 |
| slope | 1.35 ± 0.22 | 1.40 ± 0.22 | 1.37 ± 0.23 | 1.45 ± 0.26 | 1.58 ± 0.26 | 1.68 ± 0.24 | 1.45 ± 0.28 |
| same, relative to week −1 only | 1.40 | 1.45 | 1.42 | 1.49 | 1.63 | 1.73 | 1.50 |

- **The slope holds and, if anything, grows over weeks 0–5** (about +0.06 per week; the
  weekly slopes share cards, so no SE is given for the trend). No sign of a temporary bounce.
  This matches Part 1's all-weeks slope (1.50) being at least as steep as weeks 0–3 (1.41).
- What it does and does not test. [inferred] A *temporary* response (novelty, attention
  from the patch notes, a bounce that dies out) predicts a falling slope; that is not
  seen. **Regression to the mean is not a temporary effect**: a card returning to its usual
  level stays there, so it predicts a slope that holds, as does a real lasting effect. J3
  therefore rules out a fading response, not reversion; J2 is the test for reversion.
- Other explanations that would move the later-week slope: slow uptake (players learning
  the new numbers: rising slope, as seen); population change within v0.103.2 (the audit
  found the win rate and tagged share falling from April to May, with stronger players
  possibly moving to the betas; a change in who plays could steepen or flatten later
  weeks); late uploads changing the mix of weeks. Not separable here.

### J4. Patch 2's pre-release movement (2 pre-weeks) [computed]

Movement from week −3 to week −1 (v0.103.3 was the current stable for about 3 weeks):

| Card | x | pre-move ± SE | weeks 0–3 effect |
|---|---|---|---|
| Debilitate | −0.406 | −0.068 ± 0.099 | +0.118 |
| Patter | −0.118 | −0.122 ± 0.079 | −0.171 |
| Bulwark | −0.080 | +0.168 ± 0.095 | +0.092 |
| Hyperbeam | +0.074 | −0.393 ± 0.192 | −0.057 |
| Synthesis | +0.154 | +0.010 ± 0.124 | +0.081 |
| Unrelenting | +0.154 | +0.008 ± 0.091 | +0.244 |
| Pounce | +0.154 | +0.131 ± 0.101 | +0.146 |
| Uproar | +0.182 | −0.264 ± 0.110 | +0.291 |
| Juggernaut | +0.182 | +0.229 ± 0.119 | −0.099 |
| Furnace | +0.223 | −0.015 ± 0.099 | −0.028 |
| Crescent Spear | +0.288 | +0.045 ± 0.080 | −0.034 |
| Death March | +0.288 | −0.080 ± 0.133 | +0.094 |
| The Scythe | +0.288 | +0.017 ± 0.137 | −0.054 |
| Sic 'Em | +0.406 | +0.093 ± 0.102 | +0.107 |

- 5 of 14 oppose the change (2 of the 2 beyond 2 SE: Hyperbeam, Uproar); median |pre| 0.09
  log-odds against a median pre SE of 0.10 and a median |effect| of 0.10. corr(pre, x) +0.17.
- **Two weeks are too few to tell.** The pre-movement SEs are as large as the effects
  themselves; the pre-move coefficient in the same model (14 points) is −0.06 ± 0.27, which
  says nothing. Section I (the fake patch) is the stronger test of the second patch's
  before block. [computed / inferred]

---

## K. Character and review-call sensitivity (weeks 0–3, saved fits)

### K1. Is either patch carried by one character? [computed]

Script: `triage/scripts/k_character_review.py`. Line tweaks per character:

| | Defect | Ironclad | Necrobinder | Regent | Silent | all |
|---|---|---|---|---|---|---|
| first | 0 | 2 | 3 | 11 | 8 | 24 |
| second | 3 | 2 | 4 | 4 | 1 | 14 |

The two patches have very different character mixes: patch 1 is mostly Regent and Silent
(19 of 24, and all five of Silent's first-patch line nerfs), patch 2 is spread out.

(a) Leave one character out (ln ruler):

| Without | n | slope1 | slope2 | z diff |
|---|---|---|---|---|
| (none) | 24 + 14 | 1.41 ± 0.19 | +0.03 ± 0.31 | −3.80 |
| Defect | 24 + 11 | 1.41 ± 0.20 | −0.01 ± 0.32 | −3.84 |
| Ironclad | 22 + 12 | 1.40 ± 0.20 | +0.03 ± 0.31 | −3.69 |
| **Necrobinder** | 21 + 10 | 1.32 ± 0.20 | +0.29 ± 0.60 | **−1.62** |
| Regent | 13 + 10 | 1.29 ± 0.23 | −0.04 ± 0.36 | −3.11 |
| Silent | 16 + 13 | 1.77 ± 0.46 | +0.02 ± 0.32 | −3.15 |

**Removing Necrobinder brings |z diff| below 2.** It does so through patch 2: of Necrobinder's
four second-patch points, Debilitate v0.107.1 is the only large nerf in patch 2 (x −0.41) and
its effect went the wrong way (+0.12 log-odds); without it patch 2's slope is set by 10 points
with a narrow dose range and its SE doubles (0.60). Debilitate v0.107.1 alone off: slope2
+0.20 ± 0.46, z diff −2.41 (K2 below). So "patch 2 is flat" rests on 14 points with a
high-leverage point, and the *difference* rests partly on that point. Patch 1's slope does
not depend on one character (1.29–1.77). [computed]

(b) Character intercepts in the slope-per-patch model: slope1 **1.04 ± 0.25**, slope2 −0.00 ±
0.30, **z diff −2.64** (τ² 0.049). With character × patch intercepts: slope1 0.84 ± 0.27,
slope2 −0.02 ± 0.31, z diff −2.13. Silent's intercept is −0.35 ± 0.19 against Defect.
[computed] Part of patch 1's slope is a between-character contrast: Silent's tweaks were
mostly nerfs with negative effects and Regent's mostly buffs with positive ones, and the
intercepts take that contrast away (dose and character are confounded in patch 1, so the
intercepts also remove real dose variation; this is a lower-bound view of slope1, not a
better estimate). [inferred]

(c) Per-character slopes, ≥ 4 points (descriptive only): Regent first patch +1.81 ± 0.64 (11),
Silent first +0.29 ± 0.18 (8: four nerfs at −0.41/−0.15/−0.13, buffs Memento Mori, Skewer,
Grand Finale with zero or negative effects), Regent second +0.07 ± 0.38 (4), Necrobinder
second −0.07 ± 0.13 (4). Within Silent, patch 1 shows little dose-response. [computed]

### K2. Phil's card-review calls as one sensitivity variant [computed]

Variant: Grand Finale off, Debilitate v0.107.1 off, Crescent Spear at x = ln(10/8) = 0.223
(absolute +2, percent +25%; its upgraded-card ln kept as the table's). 36 tweaks; rank and
per-kind rulers recomputed on them. Primary (38) beside it. The **hybrid ruler** (absolute
change ÷ kind median for damage and block, ln ÷ kind median for power amounts and "other";
kind medians on the primary set: damage 2, block 1, power 0.41, other 0.29) **was proposed
after notebook 04's results were known**: it is post hoc.

| Ruler | Primary: slope1 / slope2 / z diff | Variant: slope1 | slope2 | z diff | ratio [±1 SE] |
|---|---|---|---|---|---|
| ln (baseline) | 1.41 / 0.03 / −3.80 | 1.45 ± 0.19 | 0.23 ± 0.46 | **−2.42** | 0.16 ± 0.32 |
| pp outcome, ln dose | 0.21 / −0.00 / −4.24 | 0.21 ± 0.03 | 0.03 ± 0.06 | −2.63 | 0.16 ± 0.30 |
| absolute (new − old) | 0.05 / 0.02 / −0.42 | 0.19 ± 0.03 | 0.04 ± 0.07 | −2.00 | 0.21 ± 0.36 |
| rank | 1.14 / 0.04 / −3.91 | 1.18 ± 0.15 | 0.11 ± 0.27 | −3.46 | 0.09 ± 0.23 |
| percent | 1.40 / 0.03 / −4.02 | 1.42 ± 0.18 | 0.19 ± 0.39 | −2.89 | 0.13 ± 0.27 |
| ln / kind median | 0.22 / 0.04 / −1.89 | 0.24 ± 0.05 | 0.08 ± 0.11 | −1.33 | 0.35 ± 0.45 |
| sign only | 0.35 / 0.03 / −3.13 | 0.36 ± 0.06 | 0.05 ± 0.09 | −2.77 | 0.14 ± 0.26 |
| abs / kind median | 0.14 / 0.01 / −1.30 | 0.24 ± 0.04 | 0.04 ± 0.10 | −1.97 | 0.15 ± 0.41 |
| mean of base and upgraded ln | 1.38 / 0.03 / −3.74 | 1.43 ± 0.19 | 0.23 ± 0.45 | −2.44 | 0.16 ± 0.32 |
| HYBRID (post hoc) | 0.11 / 0.03 / −0.79 | 0.27 ± 0.05 | 0.05 ± 0.10 | −1.90 | 0.19 ± 0.39 |

Each call alone (ln): Grand Finale off z −3.98 (slope1 1.45); **Debilitate v0.107.1 off z
−2.41** (slope2 +0.20); Crescent Spear at 0.223 z −3.73.

Reading. [inferred] Under Phil's calls the patch difference is **smaller but still there on
most rulers**: z −2.4 to −3.5 on six rulers, −1.3 to −2.0 on the per-kind, absolute and
hybrid rulers. Two things move: removing Grand Finale makes the absolute ruler work for
patch 1 (slope1 0.05 → 0.19 per point, z 6), which brings the absolute ruler's difference
from −0.4 to −2.0; removing Debilitate v0.107.1 gives patch 2 a slope of about 0.2 (ratio
about 0.15 of patch 1's) with a wide interval. Patch 2's slope stays below about a third of
patch 1's on every ruler (ratio 0.09–0.35), and its own z stays under 1. Phil's ruler lean
(the hybrid) gives z −1.9: not clearly different, not clearly the same.

### K3. Starting-point (threshold) check — EXPLORATORY [computed]

Proposed by Phil after seeing patch 2 flat; the predictions (1)–(3), including the
addendum's ceiling prediction, and the model were written into
`triage/scripts/k3_threshold.py` before it ran. The addendum arrived before K was started,
so it is folded into K3 rather than run separately. **Selection caveat, for every K3
result:** the developers chose which cards to change and by how much, probably looking at
their pick rates, so starting point and dose are not independent.

"All controls' rates": one before-block pick rate per (window, control card) for every
control of the 38 tweaks' windows (622 rates, one aggregate query): 25th percentile 0.207,
median 0.278, 75th 0.382 (first-patch windows 0.210 / 0.272 / 0.383, second 0.207 / 0.281 /
0.381). Floor = below 0.207, ceiling = above 0.382 (declared).

(a) Starting points:

| | n | median rate before | median controls | median log-odds gap | below 25th pct | above 75th pct |
|---|---|---|---|---|---|---|
| patch 1 buffs | 19 | 0.141 | 0.278 | −0.78 | 16 | 1 |
| patch 1 nerfs | 5 | 0.251 | 0.255 | −0.02 | 1 | 1 |
| patch 2 buffs | 11 | 0.194 | 0.267 | −0.36 | 6 | 0 |
| patch 2 nerfs | 3 | 0.262 | 0.255 | +0.03 | 0 | 1 |

Neither patch is bimodal. Patch 1's changed cards sit at the floor (17 of 24 below the 25th
percentile, 2 above the 75th); patch 2's are spread over the middle (6 below, 1 above).
**Patch 2's buffs started higher than patch 1's, not lower** (median 0.19 vs 0.14), and its
nerfs started about where patch 1's did (0.26 vs 0.25).

(b) Declared model, effect ~ patch intercepts + per-patch slopes + gap_c + x × gap_c:
**x × gap −0.63 ± 0.34 (z −1.8)**; gap −0.05 ± 0.07; slope1 1.43 ± 0.23, slope2 0.22 ± 0.35;
**z diff −3.20** (−3.80 without the gap terms). Patch 1 alone: x × gap −0.67 ± 0.43. The same
model with the outcome in pp: x × gap **+0.027 ± 0.047** (null), z diff −4.14.

(c) Near the floor: patch 1 17 (Anticipate, Grand Finale, Memento Mori, Skewer, Collision
Course, Glitterstream, Heirloom Hammer, Kingly Kick, Parry, Patter, Refine Blade, Wrought in
War, Danse Macabre, Debilitate, Sculpting Strike, Fight Me, Hemokinesis); patch 2 6 (Crescent
Spear, Death March, Hyperbeam, Synthesis, Uproar, Pounce). Near the ceiling: patch 1 2
(Corrosive Wave, Gather Light), patch 2 1 (Bulwark). Patch 2's three nerfs, described, not
fitted: Bulwark (x −0.08; rate 0.50 against controls 0.26, the ceiling card; effect +0.09 ±
0.04, wrong way), Patter (x −0.12; 0.26 vs 0.26; −0.17 ± 0.04, right way), Debilitate (x −0.41;
0.25 vs 0.26; +0.12 ± 0.05, wrong way). Two wrong-way nerfs, one at the ceiling and one in the
middle: three cards cannot test a ceiling.

Reading. [inferred]
- Prediction (2), floor composition flattening patch 2: **contradicted.** The patch with the
  floor cards is patch 1, and it has the steep slope.
- Prediction (1), smaller response for low starters: **not supported.** On the log-odds
  scale the interaction is negative (low starters respond *more* per unit dose, the sign
  regression to the mean predicts); on the pp scale it is zero. The log-odds conversion
  divides by p(1 − p), which is small for low starters, so the log-odds sign is partly a
  scale effect. The data favour neither the threshold story nor reversion here; J2 is the
  better reversion test and leans against it.
- Prediction (3), ceiling for nerfs: patch 2 has one ceiling card (Bulwark, whose nerf did
  nothing, consistent with a ceiling) against patch 1's two; the nerfs start at the same
  median. It cannot explain patch 2 as a whole.
- Even with the gap terms, z diff stays −3.2.
- 17 of patch 1's 24 starting below the 25th percentile is itself a finding: patch 1 mostly
  buffed unpopular cards. Patch 1's slope is mostly a slope among floor cards.

---

## L. Control scope

Script: `triage/scripts/l_control_scope.py` (`did.run_all(..., control_scope=<scope>,
max_week_after=3)`, every other setting as did_h3; derived card colors).

Test runs [computed]:

| Test | Runtime | Peak memory | Uproar weeks 0–3 β (pp) ± SE | control cards |
|---|---|---|---|---|
| Uproar, scope "color" | 8 s | 2.6 GB | +2.29 ± 0.42 (= did_h3) | 74 |
| Uproar, scope "other" | 30 s | 4.1 GB | +2.15 ± 0.41 | 290 |
| Uproar, scope "all" | 32 s | 4.9 GB | +2.17 ± 0.41 | 364 |
| Regent first patch (Parry, Refine Blade, Glitterstream), "all" | 51 s (load 10 s, 7.3M rows; ≈ 13 s per fit) | 5.0 GB | Parry +13.7 ± 0.75 (did_h3 +14.2) | 332 |

Estimate for the full run: 9 window × color loads (≈ 10 s each) and 43 fits plus 3 upgrade-only
placebo fits (≈ 13 s each): about 11–12 minutes per scope, 22–25 minutes for both, peak
memory about 5–6 GB. Over the 5-minute budget, so I asked first; Phil approved both scopes.

Full run [computed]: "other" 43 tweaks in 577 s, peak 5.3 GB; "all" 43 in 699 s, peak 5.7 GB;
no errors. Estimates in `triage/out/did_h3_ctrl_other.csv` and `did_h3_ctrl_all.csv`;
comparison by `triage/scripts/l_compare.py` (seconds). Control cards per fit: 74–100
("color"), 262–297 ("other"), 332–364 ("all").

**Per-card estimates (weeks 0–3, pp).** [computed]

| | other vs color | all vs color |
|---|---|---|
| sign changes | 3 (Heirloom Hammer +0.30 → −0.60, Wrought in War +0.63 → −0.27, Sculpting Strike −0.03 → +0.18), none clearly nonzero in either fit | the same 3 |
| moved by > 1 color-SE | 20 of 43: **20 of 26 first-patch, 0 of 17 second-patch** | 19 of 43 (19 / 0) |
| median \|shift\| | 1.85 SE (first), 0.21 SE (second) | 1.49 / 0.18 SE |
| shift regressed on the color estimate | −0.076 | −0.061 |

The first-patch shifts are **almost uniform within each character**: every Silent tweak
moves about +1.3 pp under "other" (Anticipate −3.9 → −2.6, Corrosive Wave −15.3 → −14.1,
Untouchable −7.9 → −6.6, Memento Mori −3.7 → −2.4, Grand Finale −3.8 → −2.5, Skewer 0.0 → +1.3);
every Regent tweak about −0.9 (Parry 14.4 → 13.5, Collision Course 5.7 → 4.8, Glitterstream
3.7 → 2.8, Patter 5.2 → 4.1); Ironclad about −1.0 (Hemokinesis, Fight Me); Necrobinder about
0 (Danse Macabre, Debilitate). Second-patch tweaks move 0.1–0.3 pp. So the scope changes a
*character-level* term: between v0.99.1 and v0.103.2, unchanged Silent cards were picked
about 1.3 points more relative to other characters' unchanged cards, and Regent's and
Ironclad's about 0.9–1.0 less. [computed]

**Dose-response by ruler and scope, weeks 0–3 (38 line tweaks).** [computed]

| Ruler | color: slope1 / slope2 / z diff | other | all |
|---|---|---|---|
| ln (baseline) | 1.41 / 0.03 / −3.80 | 1.24 / 0.03 / −3.55 | 1.27 / 0.03 / −3.60 |
| pp outcome, ln dose | 0.21 / −0.00 / −4.24 | 0.18 / −0.00 / −3.98 | 0.19 / −0.00 / −4.04 |
| absolute | 0.05 / 0.02 / −0.42 | 0.05 / 0.02 / −0.51 | 0.05 / 0.02 / −0.49 |
| rank | 1.14 / 0.04 / −3.91 | 1.02 / 0.05 / −3.68 | 1.04 / 0.05 / −3.73 |
| percent | 1.40 / 0.03 / −4.02 | 1.23 / 0.04 / −3.74 | 1.26 / 0.04 / −3.80 |
| ln / kind median | 0.22 / 0.04 / −1.89 | 0.19 / 0.04 / −1.80 | 0.20 / 0.04 / −1.82 |
| sign only | 0.35 / 0.03 / −3.13 | 0.30 / 0.02 / −2.90 | 0.31 / 0.02 / −2.95 |
| abs / kind median | 0.14 / 0.01 / −1.30 | 0.12 / 0.01 / −1.31 | 0.12 / 0.01 / −1.31 |
| mean base + upgraded ln | 1.38 / 0.03 / −3.74 | 1.22 / 0.03 / −3.49 | 1.25 / 0.03 / −3.55 |

ln, "other": slope1 1.24 ± 0.18, slope2 0.03 ± 0.29, τ² 0.045.

**Reading.** [inferred]
- The scope does not touch patch 2 (shifts ≤ 0.3 pp, slope2 identical) and lowers patch 1's
  slope by about 12% (1.41 → 1.24 on ln). The patch difference survives every scope on the
  rulers where it existed (z −3.5 to −4.0 on the scale-preserving rulers), and the ruler
  ordering is unchanged.
- Which reading of the character-level shift? The trade-off stated in `did.py`: same-color
  controls absorb character-wide shocks but compete with the treated card; other-color
  controls do not compete but are exposed to character-wide shocks. The direction fits
  **substitution across a character's own cards**: patch 1 nerfed five Silent cards (players
  then take more of the other Silent cards, so same-color controls rise and the nerf
  estimates are pushed away from zero) and buffed many Regent and Ironclad cards (the other
  Regent and Ironclad cards fall, so the buff estimates are pushed up). Under that reading the
  same-color estimates in patch 1 overstate |β| by about 1 point per card, and the
  substitution spillover is far larger than the same-screen part F measured (about 0.8% of
  each effect): it works across screens within a run, or through the character's whole pool.
  The other reading is a character-wide shock (e.g. Silent players picking more of
  everything after the patch, for reasons unrelated to substitution), which "other" fails to
  absorb. The pattern lines up with each character's net change direction (Silent net nerfed,
  Regent and Ironclad net buffed, Necrobinder mixed and about 0), which favours substitution,
  but the two cannot be separated with these fits. Either way the true patch-1 slope lies
  between the two scopes (about 1.24 to 1.41), not near zero.
- This revises F: "spillover is about 1% of each effect" holds for **same-screen**
  substitution only; whole-run or pool-level substitution (or a character shock) is about
  1 pp per card in patch 1 (12% of the slope), still pushing away from zero.

---

## G. Uploader token

### G1. Coverage on the primary population, and release timing [computed]

Script: `triage/scripts/g1_coverage.py`. Primary runs = `runs_dedup` with
`spirometry.runs.PRIMARY_RUN_FILTER` (solo, no modifiers, not modded, released build, not
before release, Neow start). Token filled = `uploader_hash` not null (the keyed hash of
`player_token`). Build pairs ordered by `builds.csv` release dates, not by name. Text order
is wrong here: as strings, "v0.99.1" sorts after "v0.107.1".

| Stable build | primary runs | token key absent (old pages) | key present | token filled | fill (all) | fill (key present) | distinct tokens | runs per token |
|---|---|---|---|---|---|---|---|---|
| v0.99.1 | 109,088 | 66,180 | 42,908 | 21,138 | 19.4% | 49.3% | 543 | 38.9 |
| v0.103.2 | 121,127 | 83,973 | 37,154 | 17,592 | 14.5% | 47.3% | 500 | 35.2 |
| v0.103.3 | 67,360 | 57,397 | 9,963 | 4,550 | 6.8% | 45.7% | 234 | 19.4 |
| v0.107.1 | 289,348 | 119,227 | 170,121 | 42,225 | 14.6% | 24.8% | 1,035 | 40.8 |

Tokens on both sides of each release (primary): v0.99.1 → v0.103.2: 397 (146 only before,
103 only after; their runs 18,669 / 14,313); v0.103.2 → v0.103.3: 185 (315 / 49; 8,697 /
3,709); **v0.103.3 → v0.107.1: 218 (16 only before, 817 only after; 4,378 / 13,800 runs)**:
93% of v0.103.3's tokens are also on v0.107.1.

Against Phil's numbers (all records, not solo-restricted): I get the same fill rates on all
records (17.7%, 13.8%, 6.5%, 13.8%), slightly more tokens (600 / 599 / 317 / 1,316 against
599 / 595 / 308 / 1,265) and pairs (476 and 308 against 472 and 297), probably because the
query ran on a later state of the tables or ordered the builds as text. On the primary population the fill rate is a little
higher for v0.99.1 (19.4%) and the same elsewhere; there are about 10–20% fewer tokens
(co-op and modded uploads drop out). The key is absent on pages 0 to about 950 (blocks of 100
pages: 0% key-present to page 999, where the block is half-sized, 100% from page 1,000); where
the key exists, 27–41% of primary runs carry a token per page block, so the token is not on
every upload, which fits an opt-in (or one upload route) but does not prove it. Whether it is
opt-in is still unknown. [computed; last point inferred]

**Release timing.** `start_time` is the record's Unix time stored as a naive UTC timestamp
(`notes/run_schema.md`), so all days here are UTC. Daily primary runs (selected builds):

| UTC day | v0.103.3 | v0.107.0 (beta) | v0.107.1 |
|---|---|---|---|
| 06-16 | 3,106 | 2,935 | 0 |
| 06-17 | 2,844 | 2,699 | 0 |
| 06-18 | 2,976 | 2,585 | 334 |
| 06-19 | 470 | 282 | 5,827 |
| 06-20 | 83 | 88 | 6,684 |
| 06-21 | 58 | 56 | 6,675 |
| 06-22 | 23 | 19 | 6,000 |

- v0.107.1 went live for the stable population at about **01:00 UTC on 2026-06-19** (the
  first hour with ≥ 100 primary runs; 216 that hour against 6–33 an hour on 06-18).
  The 334 runs on 06-18 are a trickle all day; 1,823 more v0.107.1 records start before 06-18 and
  are dropped as `before_release`. Changelog 1.2.1 says v0.107.1 was also on the beta
  channel, which would explain the trickle. [computed; the beta explanation is inferred]
- v0.103.3 runs fall from about 2,900 a day to 470 on 06-19, 83 on 06-20 and 23 by 06-22:
  the switch is almost complete within a day.
- Same check for the others: v0.103.2 (builds.csv 04-16) also went live at about **01:00 UTC
  on 04-17** (189 runs on 04-16, 3,905 on 04-17); v0.103.3 (05-29) at about 22:00 UTC on
  05-29, the same day.
- **Does week 0 start on the right day?** For v0.107.1 and v0.103.2, week 0 (from the
  builds.csv date, 00:00 UTC) starts about 25 hours before the stable population switched.
  Week 0 therefore holds one extra day of thin early (probably beta-channel) play, and
  "weeks 0–3" covers about 27 days of real stable play, not 28. The offset is the same for
  both patches, so it cannot produce a patch difference; the site's 2026-06-19 is the better
  UTC date for v0.107.1. The SlayTheStats tooltip release (2026-06-19 per SPIROMETRY.md)
  falls on the same day as the real switch, not the day after. [computed / inferred]

### G2. Representativeness: token runs against other runs [computed]

Script: `triage/scripts/g2_representativeness.py`. Within each stable build, primary runs
with a token against key-present runs without one (runs whose page predates the key are a
third, unknown group, shown in the script's output).

| Build | group | runs | mean asc. | A0 share | tagged share | win rate (finished) | abandoned | floors |
|---|---|---|---|---|---|---|---|---|
| v0.99.1 | token | 21,138 | 3.52 | 0.28 | **0.008** | **0.199** | 0.23 | 24.2 |
| | no token | 21,770 | 3.68 | 0.27 | **0.526** | **0.257** | 0.12 | 28.1 |
| v0.103.2 | token | 17,592 | 4.85 | 0.19 | 0.007 | 0.193 | 0.22 | 24.9 |
| | no token | 19,562 | 5.06 | 0.17 | 0.525 | 0.233 | 0.12 | 28.3 |
| v0.103.3 | token | 4,550 | 4.79 | 0.18 | 0.005 | 0.185 | 0.19 | 25.8 |
| | no token | 5,413 | 4.93 | 0.19 | 0.492 | 0.218 | 0.14 | 27.0 |
| v0.107.1 | token | 42,225 | 4.71 | 0.23 | 0.009 | 0.184 | 0.26 | 24.2 |
| | no token | 127,896 | 5.15 | 0.18 | 0.138 | 0.175 | 0.26 | 23.9 |

- **Token runs are almost never SlayTheStats-tagged (under 1%)**, while about half of the
  key-present runs without a token are tagged (14% on v0.107.1). The token and the `_sts` tag
  are two different upload routes that barely overlap. [computed; "upload route" inferred]
- Before June, token runs win less (0.19–0.20 against 0.22–0.26), are abandoned about twice
  as often (19–23% against 12–14%) and reach fewer floors; on v0.107.1 they look like the
  rest. Ascension is a little lower; character mix is within about 3 points of the others in
  every build. Runs per token: 19–41 (G1).
- Before-block pick rates of the 38 line cards: correlation token vs no token 0.98 (patch 1)
  and 0.96 (patch 2); median |difference| 1.1 pp (patch 1) and 3.4 pp (patch 2, where the token
  side has only about 300 offers per card); 8 of 24 and 2 of 14 differ by more than 2 binomial
  SEs (Collision Course +3.7 pp, Gather Light −3.8, Flick Flack +2.9, Skewer +2.6, Hemokinesis
  +3.8, ...).
- **Reading.** The token subset is a different set of uploaders (a non-SlayTheStats route,
  more abandoned and lost runs before June), but it ranks the cards almost the same way. It
  differs enough that its *levels* should not stand in for the population; it is usable for
  a within-subset replication of a *contrast* (patch 1 vs patch 2), with that caveat. [inferred]

### G2b. Power gate [computed]

Script: `triage/scripts/g2b_power_gate.py` (rule fixed before counting: estimable = ≥ 200
treated offers in each block on the subset, weeks 0–3 after block). Treated offers in the
token subset: patch 1 before 630–4,131 and after 395–2,605 per tweak; **patch 2 before
150–869** (v0.103.3) and after 267–1,652.

- Estimable: **35 of 38** at ≥ 200 per block (24 + 11; The Scythe, Juggernaut and Hyperbeam
  have 150–175 before-block offers); 38 of 38 at ≥ 50; 23 of 38 at ≥ 500.
- SE ratio subset / full, approximated as √((1/n_b + 1/n_a)_subset / (1/n_b + 1/n_a)_full)
  on treated offers (assumes the treated card's binomial noise dominates and similar pick
  rates): median **2.43 (patch 1), 3.56 (patch 2)**.
- `d_power.py --simulate-first --tau2 0.0517 --se-scale 3.56 --se-scale-first 2.43`:
  planted slope2 = 1.44 detected as nonzero in **96.7%** (honest) / 74.4% (placebo-inflated);
  a flat patch 2 against patch 1 detected in **86%** (honest) / 37% (placebo-inflated); slope2
  ≠ 0 at a planted 0: 7.2% (honest). Power to detect a patch-1 slope of 1.44 on the subset
  (expected SE of slope1 from the same design, analytically): SE 0.21, power ≈ 100% (honest);
  SE 0.37, 97% (placebo-inflated).
- **Gate passed** (power for patch 1 far above 50%; 35 ≥ 30 estimable). G3 goes ahead. The
  subset can tell "patch 2 flat" from "patch 2 like patch 1" with honest errors, but only
  weakly under placebo-scale errors (37%).

### G3. The dose-response on the token subset [computed]

Scripts: `triage/scripts/g3_token_subset.py` (fits; test on Parry, Uproar and Hyperbeam
first, 10 s; Phil approved the full run: 84 s, peak 4.0 GB, no errors) and
`triage/scripts/g3_analysis.py`. `did.fit_did` cannot restrict to a subset of runs, but the
loaded frame carries `uploader_hash`, so the subset is a row filter on it (treated and control
offers both from token runs), and the fit reuses `did._subset` / `did._fixed_effects` (same
model, weeks 0–3, same-color controls; nothing in `src/` edited). Each estimate gets SEs
clustered by `run_key` and by token; a second variant adds token fixed effects. Output:
`triage/out/g3_token_fits.csv`.

| Data | n | slope1 | slope2 | difference (z) | τ² |
|---|---|---|---|---|---|
| full (did_h3) | 24 + 14 | 1.41 ± 0.19 | +0.03 ± 0.31 | −1.39 ± 0.37 (−3.80) | 0.052 |
| **token subset** | 24 + 14 | **1.15 ± 0.23** | **−0.04 ± 0.41** | −1.19 ± 0.47 (**−2.55**) | 0.065 |
| subset, token-clustered SEs | 24 + 14 | 1.10 ± 0.23 | −0.07 ± 0.41 | (−2.46) | 0.058 |
| subset, 35 estimable | 24 + 11 | 1.15 ± 0.23 | +0.07 ± 0.42 | (−2.25) | 0.066 |
| subset + token fixed effects | 24 + 14 | 1.14 ± 0.23 | −0.05 ± 0.40 | (−2.56) | 0.065 |
| same, token-clustered, 35 | 24 + 11 | 1.10 ± 0.24 | +0.03 ± 0.43 | (−2.19) | 0.060 |

- **Patch 1's slope reappears on the subset** (1.15 ± 0.23, z 5): the subset is usable.
  Subset and full-data effects correlate 0.94 in patch 1 (17 of 24 toward the change).
- **Patch 2 stays flat** (−0.04 ± 0.41; 9 of 14 toward the change); its subset effects
  correlate only 0.47 with the full-data ones, as expected when the true effects are near
  zero and the subset SEs are 3.5× larger.
- The difference is z −2.2 to −2.6: smaller than on the full data, as the power gate
  predicted (G2b: about 86% power with honest SEs), and the same sign and size (−1.1 to −1.2
  log-odds per unit ln against −1.39).
- **Token fixed effects change nothing** (slopes move by < 0.01). Comparing each token with
  itself does not revive patch 2. [computed]
- What this does and does not test. [inferred] The subset fit holds the *upload route*
  fixed (a population with different habits from the SlayTheStats uploaders, G2), and the
  token FE remove differences in a player's overall pick propensity. The subset still
  includes tokens seen on only one side of a release; a stayers-only fit (tokens on both
  sides, 218 for v0.103.3 → v0.107.1, 397 for v0.99.1 → v0.103.2) was not run (≈ 1.5 minutes;
  listed in the wrap-up). Population change between blocks is therefore **weakened** as an
  explanation for patch 2's flatness: a population that excludes the SlayTheStats route
  shows the same pattern. It is not excluded for changes in *which players within* the
  token route played each block.

### G4. Clustering by token [computed]

`triage/out/g4_token_placebo.csv`: 5 unchanged cards per window (9 windows, 45 placebo
fits, seed 20261008, ≥ 200 subset offers per block), same model, weeks 0–3.

| | n | sd z (run / token clusters) | robust sd z | \|z\| > 2 | se_token / se_run |
|---|---|---|---|---|---|
| all | 45 | 2.13 / 1.58 | 2.10 / 1.64 | 33% / 22% | 1.32 |
| first patch | 20 | 2.48 / 1.82 | 2.65 / 2.01 | 40% / 25% | 1.28 |
| second patch | 25 | 1.84 / 1.39 | 1.82 / 1.17 | 28% / 20% | 1.35 |

Real tweaks: token-clustered SE / run-clustered SE median 1.32 (0.97–2.58; 1.43 first patch,
1.20 second).

- Token clustering widens SEs by about a third and moves the subset's placebo spread from
  about 2.1 to 1.6 (robust 2.1 → 1.6). **It does not bring it to 1.**
- The subset's run-clustered placebo spread is already about 2, not 4, because its SEs are
  2.5–3.5× larger while the card-level drift (in pp) is not: placebo β² = 0.0017 + 0.93 ×
  se² gives an additive sd of about 4.2 pp and no multiplicative excess on the subset (45
  points, noisy). That is C's picture: an **additive, card-level component that does not
  shrink with more data**, which no clustering can remove, plus (on the full data) a
  multiplicative part of ×1.5–2.4. A token-clustering factor of about 1.3 could explain only
  part of that multiplicative part, and only for the token runs: most runs have no token
  (G1), and for them uploader clustering is not possible. So token clustering is a partial
  fix of a minor part, not a solution to the calibration. [computed / inferred]

### G5. Selection caveats (stated, not computed)

- Token runs are one upload route (almost no SlayTheStats tags, G2), with more abandoned and
  lost runs before June than other uploads. They rank cards the same way as other uploads
  (pick-rate correlation 0.96–0.98) but are not a sample of all players.
- 93% of v0.103.3's tokens also appear on v0.107.1 (G1): a within-token comparison across
  that release is mostly people who kept playing.
- A within-player comparison removes changes in *who* is playing (for the players compared)
  and fixed skill. It does not remove skill that grows during the window, or learning
  specific to particular cards. It says what the patch did to stayers, not to everyone.
- The token key is absent on pages before about 950, so the subset leans toward runs
  uploaded later (September downloads), with whatever upload-lag selection that brings.

---

## H. What did the patches do? (pre-declared aggregates)

Script: `triage/scripts/h_patch_outcomes.py` (list, population and boundaries fixed in its
header before it ran; 11 s). Population: primary runs on stable-branch builds, by UTC start
date; per-week values for weeks −3 to −1 and 0 to 3 around each boundary, then the mean of
the weekly values per side. The "z" uses week-to-week variation only (3 and 4 weeks) and is
crude.

**Negative control (a)**, chosen by the rule from date ranges only: the longest stable build
is v0.107.1 (2026-06-18 to the data's end on 2026-09-22, 96 days; builds.csv has no later
stable), the middle of its range is day 48, the closest week boundary counted from its
release is day 49: **2026-08-06**. **Negative control (b)**: the v0.103.3 release (2026-05-29).
v0.103.3 was the current stable for only 3 weeks, so control (b)'s week 3 (06-19 to 06-25) is
v0.107.1's release week: contaminated by design; weeks 0–2 shown as well.

**Rarity mix of cards taken in wins vs losses: not computed.** Card rarities are only in
`reference/raw/cards.json` (off-limits; `card_changes.csv` has them for changed cards only).
[unverified]

Every outcome examined (post minus pre; pre = mean of weeks −3..−1, post = mean of weeks 0..3):

| Outcome | v0.103.2 release | v0.103.3 release (control b) | v0.107.1 release | within v0.107.1 (control a) |
|---|---|---|---|---|
| runs started per week | 23,144 → 20,432 (−12%, z −0.7) | 17,072 → 28,420 (+66%, z 2.0) | 23,413 → 31,508 (+35%, z 1.6) | 19,222 → 16,709 (−13%, z −3.1) |
| win rate (finished runs) | 0.227 → 0.225 (z −0.3) | 0.194 → 0.185 (z −0.9) | 0.183 → 0.184 (z 0.0) | 0.179 → 0.175 (z −1.1) |
| floors reached | 26.1 → 26.9 (z 2.4) | 25.3 → 24.7 (z −1.3) | 24.5 → 24.7 (z 0.5) | 24.1 → 23.5 (z −2.3) |
| mean ascension | 3.77 → 4.96 (+1.19, z 4.9) | 4.57 → 4.75 (z 0.4) | 4.40 → 5.42 (+1.01, z 4.6) | 4.88 → 5.02 (+0.14, z 5.7) |
| share at A0 | 0.255 → 0.175 (z −5.5) | 0.215 → 0.206 (z −0.4) | 0.225 → 0.182 (z −2.5) | 0.199 → 0.190 (z −3.0) |
| skip rate per reward screen | 0.235 → 0.217 (−1.8 pts, z −3.8) | 0.203 → 0.199 (z −1.3) | 0.197 → 0.202 (+0.6, z 1.5) | 0.191 → 0.201 (+1.1, z 2.7) |
| share Defect | 0.182 → 0.187 (z 0.8) | 0.183 → 0.185 (z 0.3) | 0.184 → 0.178 (z −1.3) | 0.189 → 0.188 (z −0.2) |
| share Ironclad | 0.227 → 0.226 (z −0.2) | 0.233 → 0.237 (z 0.5) | 0.239 → 0.224 (z −2.4) | 0.244 → 0.254 (z 4.1) |
| share Necrobinder | 0.187 → 0.175 (z −2.3) | 0.179 → 0.187 (z 1.5) | 0.187 → 0.196 (z 1.5) | 0.177 → 0.175 (z −0.5) |
| share Regent | 0.191 → 0.189 (z −0.3) | 0.169 → 0.166 (z −0.5) | 0.163 → 0.164 (z 0.2) | 0.159 → 0.153 (z −1.8) |
| share Silent | 0.213 → 0.223 (z 2.1) | 0.237 → 0.226 (z −2.3) | 0.227 → 0.237 (z 1.1) | 0.231 → 0.231 (z −0.1) |

Control (b), weeks 0–2 only (before v0.107.1): runs per week +37%, win rate −1.1 pts,
floors −0.8, mean ascension −0.18, A0 share +1.0 pt, skip rate −0.7 pt. [computed]

**Multiple comparisons.** 44 comparisons; 16 have |z| > 2, **including 5 of 11 at control (a),
where nothing was released**. The crude weekly z is badly overconfident (weeks share trends,
upload lag, beta releases). Read only differences that are large next to the controls'.
[computed / inferred]

What survives that bar [computed numbers; reading inferred]:
- **Ascension jumps at both balance releases**: mean +1.2 (v0.103.2) and +1.0 (v0.107.1)
  against +0.14 (control a) and +0.18 / −0.18 (control b). The A0 share falls 8 and 4 points
  (controls: about −1 and ±1). It peaks in weeks 0–1 (5.4–5.9) and eases in weeks 2–3.
  So the population in the first weeks after a major release plays at higher ascension:
  returning or more committed players, or ascension progress reset/re-climb. The DiD has
  ascension fixed effects, but this is a **population shift that coincides with weeks 0–1 of
  both patches** (same direction and similar size in both, so it cannot by itself explain a
  difference between them).
- **Runs started per week** rise 35% at v0.107.1 (and at control b, where week 3 is the
  v0.107.1 week), fall 12% at v0.103.2, and fall 13% at control a (upload lag makes recent
  weeks thin). No consistent release effect.
- **Win rate among finished runs does not move** at either release (±0.2 pts), against
  −0.4 to −1.1 pts at the controls. Neither patch changed how often runs are won.
- **Skip rate**: −1.8 pts at v0.103.2, +0.6 at v0.107.1, +1.1 at control a: within the range
  the control shows. Floors reached: +0.8 (v0.103.2), +0.1 (v0.107.1), −0.6 and −0.8 at the
  controls: same.
- Character shares move by ≤ 1.5 points everywhere, as much at control a (Ironclad +1.0) as at
  the releases.

**Reading.** [inferred] At the aggregate level neither patch changed win rate, skip rate,
floors or the character mix by more than calendar time does on its own. Both major releases
brought the same visible population change (higher ascension in the first two weeks). These
aggregates do not separate the two patches.

---
---

# Final synthesis (Parts 1 and 2)

Tags as above. Numbers are from the 2026-10-02 rebuild (1,873 pages, 1,871,830 records),
weeks 0–3 after release, ln ruler, unless stated.

## 1. The anomaly and what explains it

**The anomaly, in my words.** In the first balance patch (v0.103.2, April), bigger number
changes moved pick rates more: about +1.4 log-odds of pick rate per unit of ln(new/old).
In the second (v0.107.1, June), tweaks of the same sizes and kinds, measured just as
precisely, show no such relation: the slope is 0.03 ± 0.31, buffs were picked barely more
than nerfs (+0.06 against +0.01 log-odds), and only 7 of the 14 line tweaks moved in the
direction of their change. Two separate claims are involved and the evidence treats them
differently:

- **(A) "Patch 2 is flat."** Its own dose-response is near zero.
- **(B) "Patch 1 is inflated."** Its steep slope overstates what the changes did.

They predict different things (A is about patch 2's tweaks; B about patch 1's) and both could
hold. The patch *difference* is the gap between them.

### Claim A: patch 2 is flat

Evidence for A (each [computed]): slope2 near zero on all nine rulers (B), under every SE
inflation (C), every control scope (L), on the token subset with and without token fixed
effects (G3: −0.04 ± 0.41), with character intercepts (K1) and with the starting-point terms
(K3). A patch-1-sized slope would have been detected 99–100% of the time (D). Most telling:
**the real patch-2 effects are spread out exactly as much as the fake effects of a patch with
no card changes** (sd 0.131 log-odds for both, I), and as much as unchanged cards' placebo
effects (0.13 vs 0.12, C).

What weakens A: it rests on 14 points with one high-leverage nerf. Without Debilitate
v0.107.1 (which Phil calls "dose unknown"), slope2 is 0.20 ± 0.46; under all three of Phil's
review calls 0.23 ± 0.46 (ratio to patch 1 0.16 ± 0.32) (K2). So the honest statement is "patch
2's slope is small, best estimate 0 to 0.2 log-odds per unit ln, and we cannot rule out
about half of patch 1's", not "exactly zero". [computed / inferred]

### Claim B: patch 1 is inflated

- Regression to the mean (J): **weakened.** The pre-release movement predicts the effect with a
  *positive* sign (+0.80 ± 0.47, z 1.7; +1.44 ± 0.46 on the pre-slope version): cards that
  were falling kept falling relative to the change, the opposite of reversion. Adding it
  raises slope1 to 1.54–1.63. Part 1's note 8 (trends continuing, so patch 1 is if anything
  understated) is the reading the data favour. Not ruled out (z 1.7 on the declared model).
- Temporary bounce / novelty (J3): **weakened.** Patch 1's slope holds and slightly grows over
  weeks 0–5 (1.35 → 1.68).
- Substitution spillover or a character-level shock (L): **supported as a modest
  inflation.** With other characters' cards as controls, slope1 falls 12% (1.41 → 1.24),
  through an almost uniform per-character shift (Silent +1.3 pp, Regent and Ironclad −0.9 to
  −1.0) whose direction matches each character's net buff or nerf. This revises F: same-screen
  substitution is about 1% of each effect, but whole-run or pool-level substitution (or a
  character-wide shock; not separable) is about 1 pp per card in patch 1. Patch 2 is untouched.
- One character or between-character contrast (K1): **partly supported.** With character
  intercepts slope1 is 1.04 ± 0.25 (0.84 with character × patch intercepts); within Silent
  the first-patch slope is only 0.29 ± 0.18 (8 points). Part of patch 1's slope is "Silent
  was nerfed and fell, Regent was buffed and rose", which intercepts absorb along with real
  dose variation (dose and character are confounded there). No single character carries it
  (leave-one-out 1.29–1.77).
- Starting points (K3): patch 1 mostly buffed unpopular cards (17 of 24 below the controls'
  25th percentile). Low starters respond more per unit dose in log-odds and the same in pp,
  so this is a scale issue, not inflation.

Net for B: patch 1's slope is somewhere around **0.8 to 1.6 depending on specification, most
specifications 1.1–1.5**. It is not near zero under any reading tested. [computed range;
reading inferred]

### Each named explanation for the patch difference

| Explanation | Verdict | Main evidence | Change from Part 1's interim read |
|---|---|---|---|
| Ruler | **Partly supports; not the whole story** | Difference clear on 6 of 9 rulers; weak on per-kind, absent on absolute (B); under Phil's calls z −2.0 on absolute, −1.9 on the post-hoc hybrid (K2) | Phil's calls make the absolute ruler informative and narrow the ruler spread (−1.3 to −3.5 instead of −0.4 to −4.2) |
| Dose measurement error | **Open** | Points the right way; partial-coverage doses more common in patch 2 (B2); Crescent Spear's correction moves little (K2) | none |
| Power | **Weakened** | 99–100% detection (D); subset 96.7% (G2b) | none |
| Before-block drift | **Weakened** | Fake patch v0.103.2 → v0.103.3: slope +0.05 ± 0.18; large fake effects exactly as many as placebo predicts (I) | Was "open"; the fake patch is flat. New: v0.103.3 card levels are noisy (fake vs real corr −0.66) |
| Regression to the mean in patch 1 | **Weakened** | Positive pre-movement coefficient (J2) | Resolves Part 1's open reading toward continuation |
| One character carries a patch | **Partly supports, through one point** | Necrobinder out: z −1.6 (via Debilitate v0.107.1); character intercepts z −2.6 / −2.1 (K1) | New |
| Choice of controls | **Weakened as the cause of the difference; trims patch 1** | z −3.55 / −3.60 under "other" / "all"; slope1 −12% (L) | New |
| Threshold for low starters | **Contradicted** | Patch 1, not patch 2, has the floor cards; interaction has the wrong sign or is null (K3) | New (exploratory) |
| Miscalibrated errors | **Weakened for the difference; real for per-card claims** | z −3.2 to −3.9 under inflation (C); token clustering widens SEs ×1.3, placebo spread 2.1 → 1.6 on the subset, not to 1 (G4) | Token clustering is a partial fix of a minor part |
| Spillover | **Weakened as the cause; larger than thought for patch 1** | Away from zero; ~1% same-screen (F), ~12% of slope1 via character-level shift (L) | Size revised up for patch 1 |
| Novelty fade or slow uptake | **Novelty weakened; slow uptake possible in both** | Patch 1 steady or growing to week 5 (J3); patch 2 shows more at all weeks (0.24) than weeks 0–3 (B) | Patch-2 slow uptake still open: even all weeks, 0.24 ± 0.32 |
| Population change | **Weakened** | Token route (no SlayTheStats uploads) shows the same pattern; token FE change nothing (G3); both releases bring the same ascension jump (H) | Was "open". Within-token stayers-only not run |
| Patch really did less (or players responded less) | **Best supported** | Real patch-2 effects indistinguishable in spread from a no-change patch (I) and from placebos (C); H shows no aggregate change at either release beyond calendar noise | Strengthened |

**Bottom line.** [inferred] The data say the second patch's numeric tweaks moved pick rates
about as much as nothing at all, while the first patch's moved them in proportion to size.
The leading explanation is that the second patch did less to choices (or players responded
less). It is not a power problem, before-block drift, a population change visible with the
token, or the choice of controls. Patch 1's slope is somewhat overstated by between-character
substitution or shocks (about 12%) and by the between-character contrast, and is not
inflated by regression to the mean. The patch *difference* is robust on scale-preserving
rulers (z −2.2 to −4.2 across everything in Parts 1–2) but leans on one patch-2 card,
Debilitate v0.107.1: without it z is −2.4 and patch 2 could have up to roughly half of patch
1's slope. Why patch 2 did less is not answered by any of this: candidates are a settled meta
and more experienced players (June, ascension rising), tooltips (the SlayTheStats tooltips
arrived the same day as the real v0.107.1 switch, 2026-06-19 UTC, G1; but token runs, which
are almost never SlayTheStats uploads, show the same flatness, G3), and the kinds of change in
patch 2 (more partial-coverage doses).

## 2. Wrap-up list (ranked)

Effort is Phil's time unless marked CC. "Must" items total about 4.5 hours of Phil's time.

| # | Item | Who | Effort | What it changes | Label |
|---|---|---|---|---|---|
| 1 | Read this report; rerun `i_fake_patch.py`, `j_reversion.py`, `k_character_review.py`, `l_compare.py`, `g3_analysis.py` and look at the outputs | Phil (scripts run in ≤ 2 min each, except I and G3 at 1–2 min) | 1.5 h | Nothing is a result until Phil has checked it | **must** |
| 2 | Decide the status of the review calls, the mixed-tweak rule and the primary ruler (keep ln primary; report Phil's calls and the rulers as the sensitivity table) | Phil | 0.5 h | Fixes what the headline is; the K2 table shows the difference becomes z −2.4 on ln | **must** |
| 3 | Add two rows to the notebook 04 sensitivity table: without Debilitate v0.107.1, and control scope "other" (from `triage/out/did_h3_ctrl_other.csv`, or by `run_all(control_scope="other", max_week_after=3)` in a notebook, ≈ 10 min of compute) | Phil (notebook) | 0.5 h | The two most important new caveats appear where readers look | **must** |
| 4 | Doc edits (section 3 below) on a branch, PR | CC drafts; Phil reviews | CC 30 min; Phil 0.5 h | Docs match the rebuild and the triage | **must** |
| 5 | Write the conclusion paragraph (README results and SPIROMETRY "Phase 5 results"): patch 2 moved picks no more than drift; patch difference robust but leans on Debilitate v0.107.1; cause unknown | Phil | 1 h | The project's stated finding | **must** |
| 6 | Clear notebook 02's saved outputs that print hashed uploader IDs (cells 27, 41) | Phil | 15 min | Release checklist | **must** |
| 7 | Stayers-only token fit (tokens on both sides of each release) | CC (≈ 2 min compute, 20 min) | — | Closes the within-player question for the people compared | should |
| 8 | Pooled-before weeks 0–3 fit for patch 2 (E, run-level fit 2) | CC (≈ 2 min) | — | Replaces I's approximate v0.103.2-based slope (+0.09 ± 0.16) with a real fit | should |
| 9 | Per-character control trends across v0.99.1 → v0.103.2 (to tell substitution from a character shock in L) | CC (30 min) | — | Says whether patch 1's same-color estimates are overstated by ~1 pp | should |
| 10 | Rarity mix in wins vs losses (H's missing outcome) | CC, needs permission to read `reference/raw/cards.json` | 15 min | Completes H's declared list; unlikely to change anything | should |
| 11 | Detrended DiD (E, fit 3); full placebo with token clustering; more rulers; hierarchical Bayes; more threshold work | — | hours each | Little: the remaining questions are about why patch 2 did less, which these do not answer | skip |

## 3. Proposed edits to SPIROMETRY.md and PLAN.md (text only, not applied)

**SPIROMETRY.md, "Phase 5 results" heading and intro:** replace "(rerun 2026-09-29, 1,513-page
tables)" with "(rerun 2026-10-02, 1,873-page tables: parser 1.7.0, built 2026-10-02 22:32 UTC,
1,871,830 records)". Update the numbers to the rebuild (table in Part 1 A): clearly nonzero
22 / 8 (weeks 0–3: 21 / 8); toward the change 18 of 21 / 8 of 8 (weeks 0–3: 17 of 20 / 5 of 7);
median |β| 4.3 / 1.5; offers per stable build 4.01M / 4.33M / 2.24M / 9.48M; solo run_keys with
more than one record 149, dedup-removed rows 4,905; drop-top-10-uploaders median shift 0.17 SE;
tagged / untagged shifts 2.55 / 0.59 SE, correlation 0.75, χ² 101 on 43; largest effects Corrosive
Wave −15.8, Leading Strike +10.0, Untouchable −9.2, Pinpoint −8.9 (Parry +14.7);
upgrade-only placebos Royalties −2.6 ± 1.1 (2.4σ), Untouchable v0.107.1 −2.0 ± 0.44 (4.5σ),
Serpent Form −0.28 ± 1.05; anticipation 15 informative (3 + 12), 11 with a nonzero main effect.

**"Dose-response":** "(38 tweaks; mixed-direction and upgrade-only kept off the line: Leading
Strike and Serpent Form (first patch), Reflect, Royalties and Untouchable v0.107.1 (second
patch).)" Slopes: one slope 1.02 ± 0.18; by patch 1.41 ± 0.19 and 0.03 ± 0.31 (all weeks 1.50 ±
0.20 and 0.24 ± 0.32); τ² 0.059, Q 1,249 on 36; buff / nerf slopes 1.57 ± 0.37 / 0.44 ± 0.40;
median |β| on the line 4.1 / 1.9 points ("about half", not "a third"). Replace "So the flat
second-patch slope isn't a power problem or a smaller-changes problem" with: "Power is not
the issue: a patch-1-sized slope would be detected in 99–100% of simulations (triage D). The
second patch's real effects are spread out no more than unchanged cards' placebo effects, or
than a fake patch between two builds with no card changes (triage I)." Add: "The patch
difference is z −3.8 on ln and between −2.2 and −4.2 across rulers on which it exists,
control scopes, SE inflations and the token subset; it falls to −2.4 without Debilitate
v0.107.1 and to −1.6 without Necrobinder's tweaks (triage K)." In the candidates, replace
"(from 2026-06-19, the day after v0.107.1)" with "(from 2026-06-19, the same UTC day the
stable population switched to v0.107.1, about 01:00 UTC)".

**"Mixed-direction tweaks: dose rule":** replace "This assumes a Shiv deals 4 damage (from
Phil; **not yet verified** from the card text)" with "A Shiv deals 4 damage (upgraded 6),
verified from `notes/patch_history_samples/changelog_1.1.0.json`." Add the rule: "A tweak is
mixed only if the card's total printed output, in the unit of its main field, moves in a
different direction for the base and the upgraded card, or two changed numbers in different
units move in opposite directions. Direction = patch-note label; dose = ln(new total / old
total) for the un-upgraded card at Strength and Dexterity 0, counting generated cards at their
printed values; a dose of 0 or of the wrong sign keeps the tweak off the line (sign ruler only);
game-state ranges are sensitivity only. Under it Leading Strike stays off (11 → 11) and Reflect
(17 → 15, upgraded 21 → 20) is not mixed: on the line at −0.125 (z diff −4.08)." Status:
"run (triage B2)".

**"Placebo calibration":** heading "(2026-10-02, rebuilt tables)"; add the triage findings: placebo
spread is card-level (window means sd 0.34 vs within 3.85), with an additive part (1.6–2.8 pp)
and a multiplicative part (×1.5–2.4); a card's placebo z correlates +0.45 across patches;
random-effects τ² absorbs most of it, so the dose-response difference survives every
inflation (z −3.2 to −3.9); clustering by token widens SEs by about 1.3 and moves the
subset placebo spread from about 2.1 to 1.6, not to 1. Status line stays "NOT met".

**Spillover (wherever "toward zero" appears, and analysis idea 6):** "Same-offer substitution
biases the pick-rate DiD with same-color controls *away from* zero (controls rise after a nerf,
fall after a buff). Dropping shared screens removes about 0.8% of each effect. Controls from
other characters lower the first patch's slope by 12% (per-character shifts of about 1 pp,
in the direction of each character's net change), consistent with substitution across a
character's whole pool or with a character-wide shock; second patch unchanged."

**"Known data issues":** (1) Release timing: "v0.103.2 and v0.107.1 reached stable players at
about 01:00 UTC on 04-17 and 06-19, a day after their builds.csv dates (week 0 starts about 25
hours early for both; same offset in both patches); v0.103.3 at about 22:00 UTC on its
date." (2) Token coverage on the primary population: fill 19.4% / 14.5% / 6.8% / 14.6%
(v0.99.1 / v0.103.2 / v0.103.3 / v0.107.1), 543 / 500 / 234 / 1,035 tokens, 397 tokens on
both sides of v0.103.2 and 218 of v0.107.1; token runs are almost never SlayTheStats-tagged
(< 1%); key absent before about page 950. (3) About 170 mod cards whose ids have no "-"
reach `primary_offers` (≤ ~100 offers each); harmless for the fits (never controls under
`card_colors`) but worth a parser rule.

**"Open questions" 8, 9, 10:** 8: "partly answered (triage C, G4): card-level and persistent;
token clustering is a partial fix of a minor part." 9: "answered: the difference survives
calibrated errors (triage C); it depends on the ruler (B, K2) and leans on Debilitate v0.107.1
(K1)." 10: "done (triage Parts 1 and 2, 2026-10-07/08)."

**PLAN.md "Next up" 7:** mark (c) "rebuild: 1.41 ± 0.19 against 0.03 ± 0.31"; (f) "0.17 SE on the
rebuild"; (g) "token subset done (triage G3): same pattern; per uploader-group fits still open";
(n) "done in triage L: z −3.55 ('other'), −3.60 ('all'); slope1 −12%"; (o) "analysed in triage C".
Item 11: README results numbers to the rebuild. **Decision log** (new entries, 2026-10-08):
"Weeks 0–3 is the primary horizon for every dose-response; all weeks secondary." "Mixed-tweak
rule adopted (text above); Reflect on the line at −0.125." "Phil's card-review calls (Grand
Finale off, Debilitate v0.107.1 dose unknown, Crescent Spear at 0.223) reported as a
sensitivity variant, not the primary" (or as Phil decides, item 2). "Release week 0 stays at
the builds.csv date; the one-day offset is documented."

## 4. Open questions only Phil can answer

1. Do the review calls become the primary specification, or stay a sensitivity row? (Under
   them the headline z goes from −3.8 to −2.4.)
2. Is "patch 2 moved choices no more than drift; cause unknown" an acceptable final finding,
   or does the project need a cause before it is written up?
3. Is `player_token` opt-in, and which upload tool sets it? (Answers whether the token subset is
   a self-selected group; the maintainer message, PLAN item 4.)
4. Does anything in the game reset or reward ascension at a major update? Both releases show
   mean ascension +1.0 to +1.2 in weeks 0–1 (H).
5. Is the snapshot complete enough to quote the rebuild numbers as final, or will there be
   another rebuild?
6. May a future session read `reference/raw/cards.json` (card colors and rarities)? The triage
   reconstructed colors from the runs (checked exactly against saved fits); rarity could not
   be reconstructed.
7. Debilitate v0.107.1: is "dose unknown" a final call? It is the single most influential point
   for the patch difference.

## What I computed versus inferred (summary)

Computed here (scripts in `triage/scripts/`, outputs in `triage/out/`): every number in
sections I, J, K, L, G and H; the fits were checked by exactly reproducing five saved did_h3
estimates before any new fit. Inferred: every "reading" paragraph; the substitution
interpretation of L's per-character shifts; the beta-channel explanation of the 06-18 trickle;
the claims about selection in G5. Unverified: the rarity outcome (not computed), whether the
token is opt-in, and why the second patch did less.

---

# Part 3 (section M)

## M. Spillover and the placebo spread — EXPLORATORY

**EXPLORATORY.** Proposed by Phil after the placebo results were seen. Nothing in this section
changes the calibration factors, the numbers module, the guide or any headline result. Script:
`triage/scripts/m_spillover.py`; tables in `triage/out_final/m_*.csv`.

**Inputs.** Unlike Parts 1 and 2 (1,873 pages), this section uses the final tables and fits:
`data/runs/runs.duckdb` (read-only, 2,071 pages, parser 1.7.0) and
`data/analysis/placebo_h3.parquet` (weeks 0–3, same-color controls, one row per (window, pseudo
card); 463 pairs; `min_offers` 51; factors 4.10 / 2.67). So the C numbers (4.33 / 2.09) are not
the comparison here; the 4.10 is. Aggregates and card-level estimates only. Card colors come
from `db.use_derived_colors()`, since `reference/raw/` stays closed.

### Interpretation rule, written before running

Declared 2026-11-06, before any exposure or clean-placebo number was computed. Git writes are
blocked in this session, so no commit timestamps this order; the claim rests on this note.

Phil's rule for test 3, as given: **test 3 robust sd near the patch factor → spillover is not
the main cause; near 1–2 → contamination is a large part.** The patch factor is the first
patch's 4.10.

Added by me, also before running:
- The rule names two outcomes. A robust sd between 2 and the factor, or a confidence interval
  that spans both, counts as unresolved. No cutoff for "near" was declared, so the estimate is
  reported with its interval and not forced into either reading.
- Test 2 predictions: corr(z, signed exposure) < 0 and corr(z², exposure) > 0.

Known limits of test 3, seen in the reference tables before running:
- **"Zero changes" holds for numeric tweaks only.** `tweak_sizes.csv` lists numeric tweaks.
  `card_versions.csv` shows six Defect cards changed in v0.99.1 → v0.103.2: Hotfix (rework),
  Voltaic (cost 2 → 3), Rocket Punch (text-only, labeled `mechanic`: its cost reduction now
  lasts until played) and three `wording` changes (Flak Cannon, Iteration, Trash to Treasure).
  All six leave the pseudo cards and the controls, as `windows.csv` excludes them. Defect is
  the least changed window, not an unchanged one.
- It is one character in one window. A Defect result can't separate "no spillover" from
  "Defect drifted differently".
- Changes outside cards (relics, enemies, colorless cards) are in every window and are not
  removed by this test.

Choice forced by the data: `direction` is +1 on all 50 rows of `tweak_sizes.csv` (it means "a
bigger number is stronger"), and the sign of a change lives in `log_ratio`. So "direction ×
|log_ratio|" would be unsigned and would equal sum |log_ratio|. Signed dose here is direction ×
log_ratio, the `x` of the dose line (`common.all_tweaks`).

### Answer

**Spillover from changed cards is not shown to explain the placebo spread, and it is not
ruled out.** Test 3 is unresolved under the rule. Test 2 finds no signed spillover, and the
spread does not track exposure once the patch contrast is removed. [inferred]

### Checks before reading anything [computed]

- `placebo_h3` gives 463 pairs and first-patch robust sd 4.10; the script stops otherwise.
- `--check`: the script's sampling and fit, with derived colors, reproduce the saved placebo
  fits for Hemokinesis (first patch) and Uproar (second): same pseudo cards, same `n_eligible`,
  max |Δz| 1.1e-07.
- Exposures recomputed from `did.load_block_data` for 4 Ironclad cards: after block within
  0.002. Before block, the SQL is about 0.02 higher on screen exposure, because it also counts
  changed cards outside the color map. Grapple is the large one: 9,569 Ironclad offers before,
  9 after (removed), and it is a changed card. Not reconciled to the digit.

Added after the first run, so they are not part of the declared design: the `*_subst` exposures,
intervals on window spreads and within-window correlations, the partial correlations, and the
all-eligible Defect fit. The first run's results had been seen. The declared numbers did not
change.

### 1. Spread by character-window [computed]

Tables: `m_windows.csv`, `m_window_spearman.csv`. Dose is direction × log_ratio over the
window's numeric tweaks. "Changed" counts every kind of change in that color; "subst." leaves
out wording-only changes. Upgrade-only tweaks without a log_ratio count as tweaks with no dose.
Interval: 95%, resampling pairs.

| Patch | Color | Tweaks | Line | Changed | Subst. | Sum \|log_ratio\| | Net signed dose | Pairs | Robust sd z [95%] | Plain sd z | Mean z |
|---|---|---|---|---|---|---|---|---|---|---|---|
| first | Ironclad | 2 | 2 | 14 | 12 | 0.47 | +0.47 | 35 | 4.83 [3.32, 6.77] | 4.90 | −0.06 |
| first | Necrobinder | 3 | 3 | 10 | 10 | 0.76 | +0.76 | 44 | 3.15 [2.05, 4.40] | 3.70 | +0.03 |
| first | Regent | 12 | 11 | 25 | 24 | 2.56 | +2.56 | 56 | 4.26 [2.94, 5.88] | 4.63 | −0.12 |
| first | Silent | 10 | 8 | 15 | 14 | 2.78 | −1.91 | 82 | 3.79 [2.91, 4.93] | 4.60 | −0.26 |
| second | Defect | 3 | 3 | 6 | 6 | 0.41 | +0.41 | 44 | 2.13 [1.45, 3.58] | 2.98 | +0.43 |
| second | Ironclad | 2 | 2 | 6 | 6 | 0.34 | +0.34 | 34 | 3.37 [2.06, 4.49] | 3.27 | +0.63 |
| second | Necrobinder | 4 | 4 | 5 | 4 | 1.39 | +0.58 | 53 | 2.73 [1.72, 3.77] | 2.70 | +0.49 |
| second | Regent | 6 | 4 | 14 | 13 | 0.83 | +0.19 | 75 | 2.79 [2.00, 3.61] | 3.28 | +0.02 |
| second | Silent | 2 | 1 | 6 | 6 | 0.15 | +0.15 | 40 | 1.92 [1.18, 3.02] | 2.24 | +0.27 |

Spearman of robust sd z. **n = 9 windows pooled, 4 first patch, 5 second.** With n = 4 the
smallest possible two-sided p is 0.083, so the within-patch rows can't reach 0.05.

| Against | Pooled (9) | First (4) | Second (5) |
|---|---|---|---|
| n tweaks | +0.21 | −0.20 | +0.21 |
| n line tweaks | +0.31 | −0.20 | +0.36 |
| n changed, every kind | +0.72 | +0.40 | +0.22 |
| n changed, substantive | +0.68 | +0.40 | +0.22 |
| sum \|log_ratio\| | +0.45 | −0.40 | +0.30 |
| sum \|log_ratio\|, line tweaks | +0.48 | −0.20 | +0.30 |

Reading. [inferred] The pooled +0.72 mostly restates that the first patch changed more and
spread more; those are the same two groups as the factors. Within the first patch the size of
the change does not order the spread: Ironclad has 2 tweaks and the largest spread, Regent 12
and less. Nine points can't separate spillover from anything else that differs by patch.

### 2. Exposure of each placebo pair [computed]

Tables: `m_exposure_pairs.csv`, `m_exposure_corr.csv`. After block is weeks 0–3, before block is
as the fit keeps it. Screens are the fit's `screen_id`; lists that couldn't be split count as one
screen (about 1% of combat offers). "Took" means picked from a reward screen, so shop purchases
don't count. Exposure uses all of a window's changed cards, including the real treated cards the
placebo fit leaves out.

Pearson with 95% bootstrap intervals (2,000 draws, resampling pseudo cards), after block.
Before-block values are within 0.05 of these; all are in the CSV. 463 pairs, 312 cards pooled;
217 and 199 first; 246 and 222 second.

| Test (prediction) | Pooled | First | Second |
|---|---|---|---|
| z, signed exposure (< 0) | +0.01 [−0.13, +0.15] | +0.00 [−0.16, +0.17] | +0.05 [−0.07, +0.17] |
| z², screen exposure (> 0) | +0.22 [+0.13, +0.30] | +0.11 [−0.01, +0.23] | +0.01 [−0.13, +0.14] |
| z², run exposure (> 0) | +0.17 [+0.10, +0.23] | −0.05 [−0.18, +0.08] | +0.03 [−0.11, +0.16] |
| z², screen, substantive | +0.23 [+0.15, +0.31] | +0.12 [−0.01, +0.24] | +0.04 [−0.11, +0.17] |
| z², run, substantive | +0.16 [+0.10, +0.23] | −0.05 [−0.19, +0.08] | +0.04 [−0.10, +0.16] |

The same on deviations from each window's mean (post hoc), and then with log offers partialled
out as well:

| Test | Pooled | First | Second | Pooled, offers out | First, offers out | Second, offers out |
|---|---|---|---|---|---|---|
| z, signed exposure | −0.04 [−0.14, +0.07] | −0.05 [−0.18, +0.07] | +0.07 [−0.04, +0.17] | −0.04 | −0.05 | +0.08 |
| z², screen, substantive | +0.18 [+0.11, +0.25] | +0.25 [+0.17, +0.32] | −0.11 [−0.20, −0.02] | +0.12 | +0.07 | −0.05 |
| z², run, substantive | −0.22 [−0.27, −0.16] | −0.27 [−0.35, −0.19] | −0.19 [−0.28, −0.11] | −0.11 | −0.12 | −0.12 |

Mean exposure, after block (every change / substantive):

| Window | Screen | Run |
|---|---|---|
| First: Ironclad | 0.27 / 0.25 | 0.77 / 0.74 |
| First: Necrobinder | 0.25 / 0.25 | 0.80 / 0.80 |
| First: Regent | 0.64 / 0.62 | 0.97 / 0.97 |
| First: Silent | 0.40 / 0.40 | 0.90 / 0.90 |
| Second: Defect | 0.14 / 0.14 | 0.41 / 0.41 |
| Second: Ironclad | 0.11 / 0.11 | 0.38 / 0.38 |
| Second: Necrobinder | 0.09 / 0.07 | 0.35 / 0.28 |
| Second: Regent | 0.30 / 0.29 | 0.85 / 0.84 |
| Second: Silent | 0.16 / 0.16 | 0.51 / 0.51 |

Correlation of each exposure between the blocks: screen 0.995, run 0.990, signed 0.996.

Reading. [inferred]
- **Signed test: no support.** The sign spillover predicts does not appear in either patch, and
  the intervals exclude anything beyond about −0.17.
- **Variance test: the pooled positive is the patch contrast.** Within each patch the intervals
  include zero. Inside windows the first and second patches take opposite signs, and offer
  volume absorbs most of that. Run exposure inside windows has the wrong sign.
- **The before block is not a real contrast.** Exposure is almost the same in both blocks, so it
  behaves as a fixed property of a card (rarity, when it's offered), not as something the patch
  did. That is why the before-block correlations match, and it means test 2 can't tell exposure
  from anything else tied to those card properties.
- **Run exposure is saturated** in the first patch (0.74–0.97), so it has little range there.
- **L is not contradicted.** L's shift of about 1 pp is shared across a character's cards, and
  same-color controls cancel a shared shift. Test 2 looks for card-by-card spillover, which is
  what would widen z.

### 3. Clean placebo [computed]

Tables: `m_clean_placebo.csv`, `m_clean_summary.csv`, `m_clean_exposure.csv`. Across the ten
character-windows, one has no row in `tweak_sizes.csv`: Defect v0.99.1 → v0.103.2. It has enough
offers: all 74 unchanged Defect cards pass `min_offers` 51 in both blocks. Fits use `did.load_block_data`
and `did.placebo_fit` with the window row of a Defect card-patch, seed 0, weeks 0–3, same-color
controls, 73 controls per fit, all offers. Intervals resample cards.

| Design | Fits | Robust sd z [95%] | Plain sd z | Mean z | Share \|z\| > 2 | First-patch factor |
|---|---|---|---|---|---|---|
| **Declared: 20 cards** | 20 | **2.73 [0.81, 4.14]** | 3.35 | −0.24 | 0.50 | 4.10 |
| Secondary, post hoc: all eligible | 74 | 3.24 [2.09, 4.18] | 3.75 | −0.18 | 0.57 | 4.10 |

How clean the window is: pseudo cards' mean exposure to the three substantive changes (Hotfix,
Voltaic, Rocket Punch), after block: screen 0.08, run 0.40. That is 3 to 7 times below the other
first-patch windows on screens (0.25–0.62), and about half on runs (0.74–0.97). Exposure is
reduced, not zero, and the pool has no large card added or removed.

**Under the declared rule: unresolved.** The estimate sits between the two named outcomes, and
its interval spans both.

Reading. [inferred]
- The all-eligible fit leans away from "contamination is a large part": its interval only just
  excludes 2 and includes 4.10. It was not declared, its 20 declared cards are among the 74, and
  the estimate is still below 4.10, so it's a lean and not a verdict.
- Defect is more spread out in the first patch (3.24) than in the second (2.13 [1.45, 3.58])
  despite less exposure (0.08 against 0.14 on screens, 3 substantive changes against 6). The
  intervals overlap. The direction is the opposite of spillover and fits calendar-time drift,
  C's hypothesis 1.
- A first-patch-scale spread with few changed cards is what drift predicts, but one character
  in one window can't show that, and Defect may simply have drifted differently.

### What this does not settle

- Spillover through channels with no card-level exposure measure here: relic, enemy and
  colorless changes, and shop purchases.
- Whether C's hypothesis 1 (card trends) is the cause. These tests look for spillover and don't
  measure trends directly.
- The size of any spillover share of the spread. Nothing here gives a share.

---

## N. Card-level drift and the placebo spread — EXPLORATORY

**EXPLORATORY.** Proposed by Phil after the placebo results and section M were seen. Nothing in
this section changes the calibration factors, the numbers module, the guide or any headline
result. Script: `triage/scripts/n_drift.py`; tables in `triage/out_final/n_*.csv`. Inputs: the
final tables (2,071 pages, read-only) and `data/analysis/placebo_h3.parquet`.

### Predictions and rules, written before running

Written 2026-11-06, before any drift number was computed. The only run-data query made first
listed offers and dates per build, and ascension and act counts. Git writes are still blocked,
so no commit timestamps this order; the claim rests on this note and on the order of the diff.

**Population.** As the placebo fits: `offers_with_version`, known ascension, each card from its
own character's runs, own-color cards, all offers (`picked`), with no adjustment in tests 1 and
5's unstratified fit. Cards must be unchanged on both sides of the build: not in
`window_changes` for the windows entering or leaving it. A card changed at a release is
expected to settle, and the placebo pool leaves changed cards out anyway.

**Builds, chosen from the listing alone.** Stable branch; only offers from the weeks the build
was the current stable (from its release to the next stable's), counted in full weeks from
release; at least 4 full weeks.

| Build | Current stable | Full weeks | Use |
|---|---|---|---|
| v0.99.1 | 03-17 to 04-16 | 4 | yes |
| v0.103.2 | 04-16 to 05-29 | 6 | yes |
| v0.103.3 | 05-29 to 06-18 | 2 | no: too short for a slope |
| v0.107.1 | 06-18 to 10-04 (snapshot end) | 15 | yes |

Betas are out (a different population, and v0.111.0 is one despite its size). v0.98.x are out:
one week or less. Week 0 stays in test 1 and is skipped in test 2's blocks (release-week
transients). v0.107.1 is also reported on its first 6 weeks, so the builds compare at one
horizon: a 15-week slope and a 4-week slope aren't the same quantity under a random walk.

**Definitions fixed here.**
- Slope: weighted linear fit of weekly logit pick rate (empirical logit, +0.5) on week, weights
  n p(1−p); the pp version weights n / p(1−p). Each card needs at least 51 offers (`min_offers`)
  in every week it's fit on. Slopes are compared to the mean of the same build and character, so
  a shift shared by a character's cards doesn't count, as the DiD's controls remove it.
- sigma_g² = Var(g) − mean(SE²). SE is binomial. Weekly shocks that aren't a trend also inflate
  Var(g), so lack of fit (chi²/df around the line) is reported, with a version scaling SE² by it.
- Rarity is derived from offer counts and checked against the rarities on file. Card type exists
  only in `reference/raw/`, so the split stays blank here unless `TRIAGE_COLORS=reference` is set.
- Test 2 blocks are 1 week long. Gap = weeks from the start of one block to the start of the
  next, which is also center to center: gap 1 is adjacent blocks. The first block starts at week
  1. v0.107.1 also runs a second scan from week 8, to compare early and late. Possible gaps:
  v0.99.1 1, 2; v0.103.2 1, 2, 4; v0.107.1 1, 2, 4, 6 in each scan. Same 20 pseudo cards per
  character across a scan's gaps, seed 0. Controls: the character's unchanged cards.
- log(excess sd) on log(gap) has a free intercept per scan, so gap is not confounded with build.
  Excess variance = Var(β) − mean(SE²). The interval resamples pseudo cards.
- Test 3 uses each window's actual offer-time distribution (stragglers included) and each pair's
  SE. Trend: Δ² from the blocks' mean times. Other shapes: the variance of a fractional Brownian
  path, averaged over the two blocks, so block length is respected.
- Test 4: the slope is fit per card on before-block offers with week < 0 (stragglers played
  after the release would have extreme leverage), demeaned by card × upgraded. The line is
  removed from every offer of every card in the fit. One fit per pair, using the pair's first
  tweak, against that tweak's saved z. The projected slope has its own error, which the clustered
  SE doesn't know: Δ² Var(slope). So z is reported with both SEs, and the corrected SE is primary.
- Test 5 bands: A0, A1–4, A5–8, A9–10, about equal in offers. Fixed mix: each card's own
  band × act mix over the build, by direct standardization.

**Predictions and what each outcome means.** "Near" is defined here so nothing lands undefined,
as test 3 of section M did. An interval spanning two outcomes counts as unresolved.

| Test | If drift | Outcomes |
|---|---|---|
| 1. sigma_g | > 0 clearly; larger in earlier builds | Interval above 0: within-build drift exists. Includes 0: none detected. Order across builds v0.99.1 > v0.103.2 > v0.107.1 (6 weeks): supports early-access settling; any other order counts against it. |
| 2. Gap slope | Near 1 (steady) or 0.5 (random walk) | ≥ 0.75 steady trend; 0.25–0.75 random walk; < 0.25 not drift. |
| 3. Budget | Predicted sd z near 4.10 / 2.67 | Share = (predicted² − 1) / (actual² − 1). ≥ 0.7 drift is sufficient; 0.3–0.7 part of the spread; < 0.3 minor. Reported per patch. |
| 4. Detrended | Robust sd falls toward 1–1.5 | ≤ 1.5: linear trend explains it. 1.5 to 80% of the factor: part. Above 80%: linear pre-trends don't explain it. |
| 5. Mix | sigma_g about unchanged | Within 25% of the unstratified value: drift isn't player mix. Falls by more: mix is a large part. |

Limits known before running:
- **Test 4 can fail with drift present.** A random walk has no trend to project, so a pre-slope
  says nothing about what comes next. "No fall" rules out persistent linear trends, not drift.
  Read it with test 2.
- **Test 1 can't see steps.** A shift at a release (relics, enemies, a meta change, spillover)
  isn't within-build drift, so test 3's gap between predicted and actual holds any such step
  along with everything else. A shortfall doesn't identify a cause.
- Test 2's 1-week blocks are noisier than the real blocks, so excess variance may be small
  against SE² at short gaps and its log undefined. Such cells are reported, not dropped silently.
- Second-patch budget: v0.103.3 has no slope of its own, so its neighbors stand in.
- Weekly shocks that don't persist look like drift in test 1 and like slope 0 in test 2.

### Answer

**Drift accounts for part of the placebo spread, not all of it, and it isn't a steady trend.**
Unchanged cards do move within a build, by about 0.7 pp per week early on. That movement fades
later in a build, it doesn't carry across a release, and removing pre-trends removes nothing. The
budget puts drift at about a third to two thirds of the excess variance, with more left over in
the first patch. So the placebo factors stay as they are, and linear detrending is not a fix.
[inferred]

### Declared outcomes [computed]

| Test | Result | Declared outcome |
|---|---|---|
| 1. sigma_g | 0.69 pp/week [0.64, 0.73]; 0.035 logit [0.033, 0.037] | **Drift exists.** Build order tied, not as predicted (see test 1) |
| 2. Gap slope | **0.18 [0.02, 0.47]** | **Unresolved:** spans "not drift" and "random walk". Excludes steady trend |
| 3. Budget | Share 0.66 / 0.70 from test 1; 0.12 / 0.20 from test 2's shape | **Part** from test 1, **minor** from test 2 |
| 4. Detrended | Corrected robust sd 2.11 / 1.40 | Rule says **part** / **explains**. **Both readings are wrong; see test 4** |
| 5. Mix | sigma_g 0.030 against 0.035 (−13%) | **Not player mix**, overall |

### Checks and changes after the predictions [computed]

- `--check`: the model path returns saved placebo β and SE for 4 pairs across both patches, directly
  and through a fake window (|Δβ| ≤ 2e-13). `block_var` and `lines` pass known-answer checks.
- Rarity is derived from offers. My first attempt failed validation (27 of 35 Uncommons wrong: the
  cards on file are nearly all changed cards, and I had already dropped their changed builds).
  Counted before exclusions, offers are tri-modal and 95 of 97 cards on file match. This was fixed
  before any drift number was computed.
- **Card type: not computed.** It exists only in `reference/raw/`. Set `TRIAGE_COLORS=reference`
  and rerun `--part 1` to fill the split.
- Choice made while coding, not in the note: in test 4, stragglers' time is capped at week 4, so a
  line isn't projected months out.
- **Part 6 is post hoc, added after reading tests 1–5:** stretches of a build, scans one by one,
  test 4's noise-only benchmark, the direct budget. Everything marked post hoc below comes from it.

### Builds [computed]

Offers in the weeks each build was the current stable, own-color unchanged cards:

| Build | Weeks | Offers | Cards |
|---|---|---|---|
| v0.99.1 | 4 | 3,225,024 | 332 |
| v0.103.2 | 6 | 3,505,381 | 333 |
| v0.107.1 | 15 | 9,740,796 | 365 |

### 1. Within-build drift [computed]

Tables: `n_sigma.csv`, `n_sigma_pooled_character.csv`, `n_slopes.csv`. Slopes are relative to the
build × character mean. "Lack of fit" is chi²/df around the line (1 if binomial noise were all
there is). The last column scales SE² by it. v0.107.1 is at 6 weeks unless marked.

| Split | Level | Slopes | sigma_g pp/week [95%] | sigma_g logit/week [95%] | Lack of fit | sigma_g pp, lack-of-fit SE |
|---|---|---|---|---|---|---|
| Overall | all | 1,028 | 0.69 [0.64, 0.73] | 0.035 [0.033, 0.037] | 1.68 | 0.61 |
| Build | v0.99.1 | 332 | 0.72 [0.63, 0.80] | 0.037 [0.033, 0.041] | 1.52 | 0.62 |
| Build | v0.103.2 | 332 | 0.73 [0.66, 0.79] | 0.037 [0.034, 0.040] | 1.65 | 0.69 |
| Build | v0.107.1 | 364 | 0.62 [0.56, 0.67] | 0.031 [0.029, 0.034] | 1.80 | 0.56 |
| Build | v0.107.1, 15 weeks | 364 | 0.27 [0.25, 0.30] | 0.013 [0.012, 0.014] | 2.06 | 0.26 |
| Character | Defect | 222 | 0.57 [0.49, 0.64] | 0.029 [0.026, 0.033] | 1.64 | 0.48 |
| Character | Ironclad | 208 | 0.73 [0.63, 0.83] | 0.038 [0.032, 0.043] | 1.70 | 0.67 |
| Character | Necrobinder | 215 | 0.63 [0.53, 0.74] | 0.031 [0.026, 0.035] | 1.79 | 0.54 |
| Character | Regent | 179 | 0.74 [0.64, 0.86] | 0.039 [0.034, 0.043] | 1.52 | 0.69 |
| Character | Silent | 204 | 0.75 [0.64, 0.85] | 0.038 [0.033, 0.043] | 1.76 | 0.69 |
| Rarity | Common | 248 | 0.55 [0.49, 0.62] | 0.033 [0.030, 0.037] | 2.51 | 0.51 |
| Rarity | Uncommon | 457 | 0.73 [0.66, 0.79] | 0.037 [0.033, 0.040] | 1.48 | 0.69 |
| Rarity | Rare | 323 | 0.72 [0.62, 0.81] | 0.034 [0.029, 0.039] | 1.31 | 0.66 |
| Card type | — | | not computed | | | |

Partially pooled per character (pp; shrunk toward 0.69, between-character variance 0.007): Defect
0.60, Necrobinder 0.66, Ironclad 0.71, Regent 0.72, Silent 0.72. On the logit scale the
between-character variance is about zero, so most of the pp difference is base rates. Defect has
the lowest drift, which bears on section M's clean window.

Stretches of a build, post hoc (`n_posthoc_sigma.csv`, pp/week):

| Stretch | sigma_g [95%] | Lack-of-fit SE |
|---|---|---|
| v0.107.1 weeks 1–7 | 0.49 [0.44, 0.53] | 0.43 |
| v0.107.1 weeks 8–14 | 0.29 [0.23, 0.34] | 0.20 |
| All three builds, release week out | 0.70 [0.64, 0.75] | 0.51 |

Reading. [inferred]
- Drift exists: the interval is far from 0.
- **The predicted order failed as written.** v0.99.1 and v0.103.2 tie and v0.107.1 is a little
  lower. At a fixed mix the order does hold (test 5), but that view wasn't the declared one.
- **It fades within a build.** On equal 7-week stretches of v0.107.1, sigma_g falls from 0.49 to
  0.29, intervals clear of each other. The 15-week slope (0.27) against the 6-week one (0.62) has
  a ratio of 0.44, close to the 0.40 expected if movement stopped after week 6; a random walk would
  give 0.63. One build shows this, so "early in a build" and "early in the summer" can't be told
  apart.
- Lack of fit of 1.7 means there are also weekly shocks of about 1 pp that aren't a trend.

### 2. Gap scan [computed]

Tables: `n_gap_fits.csv`, `n_gap_summary.csv`, `n_gap_slope.csv`. 1-week blocks, 20 pseudo cards
per character, placebo model and clustering. Excess variance in pp².

| Scan | Gap | Fits | Robust sd z | Plain sd z | sd β (pp) | Mean SE (pp) | Excess var |
|---|---|---|---|---|---|---|---|
| v0.99.1 from week 1 | 1 | 100 | 1.43 | 1.24 | 1.84 | 1.51 | 0.86 |
| | 2 | 100 | 1.37 | 1.46 | 2.28 | 1.56 | 2.51 |
| v0.103.2 from week 1 | 1 | 100 | 1.29 | 1.22 | 2.32 | 1.81 | 1.73 |
| | 2 | 100 | 1.40 | 1.24 | 2.45 | 1.90 | 1.95 |
| | 4 | 100 | 1.66 | 1.81 | 2.94 | 1.77 | 5.12 |
| v0.107.1 from week 1 | 1 | 100 | 1.50 | 1.56 | 2.46 | 1.48 | 3.59 |
| | 2 | 100 | 1.81 | 1.85 | 2.76 | 1.57 | 4.85 |
| | 4 | 100 | 2.01 | 1.97 | 2.89 | 1.61 | 5.44 |
| | 6 | 100 | 1.91 | 1.85 | 3.01 | 1.71 | 5.76 |
| v0.107.1 from week 8 | 1 | 100 | 1.08 | 1.23 | 2.70 | 2.15 | 2.15 |
| | 2 | 100 | 0.95 | 1.01 | 2.27 | 2.18 | −0.18 |
| | 4 | 100 | 0.97 | 1.13 | 2.65 | 2.18 | 1.74 |
| | 6 | 100 | 1.24 | 1.30 | 2.86 | 2.18 | 2.89 |

**log(excess sd) on log(gap), free intercept per scan: 0.18 [0.02, 0.47]**, 12 of 13 cells (one has
negative excess, so no log). Excess sd at gap 1: 1.44 pp. Scan by scan, post hoc
(`n_posthoc_scans.csv`): v0.103.2 0.39 [0.11, 0.89]; v0.107.1 early 0.13 [−0.01, 0.29]; v0.107.1
late 0.04 [−0.31, 0.63]. v0.99.1 has two gaps, so no slope.

Reading. [inferred] Steady trend is out: the interval stops at 0.47. Random walk and "not drift"
are both inside it. The main feature is that excess is already large at gap 1 and grows slowly, as
weekly shocks would. Late in v0.107.1 robust sd z is about 1 and robust excess about 0, though plain
excess still reaches 2.9 pp², so a few cards do move. That is the clearest single result here:
**well after a release, most unchanged cards behave as the errors say they should.** Note that
1-week blocks have large SEs, so a z near 1 there is a weaker statement than it would be at the
real blocks' precision.

### 3. Budget [computed]

Tables: `n_budget.csv`, `n_budget_windows.csv`, `n_budget_posthoc.csv`, `n_budget_direct.csv`.
Mean distance between blocks, from the actual offers: 3.96 weeks (first), 3.00 (second). Each row
predicts robust sd z with each pair's own SE. Actual: 4.10 / 2.67. Share as declared.

| Drift assumed | First: predicted, share | Second: predicted, share |
|---|---|---|
| Steady trend, sigma_g pp | 3.37, 0.66 | 2.30, 0.70 |
| Same, upper end of sigma_g | 3.57, 0.74 | 2.41, 0.78 |
| Same, sigma_g logit × p(1−p) | 3.23, 0.60 | 2.23, 0.64 |
| Same, neighbouring builds' sigma_g | 3.53, 0.72 | 2.27, 0.67 |
| Same, lack-of-fit SE | 3.06, 0.53 | 2.12, 0.57 |
| Post hoc: release week out, lack-of-fit SE | 2.63, 0.37 | 1.88, 0.41 |
| Test 2's scale, random walk | 2.95, 0.49 | 2.25, 0.66 |
| **Test 2's scale and fitted exponent** | **1.70, 0.12** | **1.50, 0.20** |
| Test 2's scale, steady trend | 6.75, 2.81 | 4.30, 2.85 |

The last row overshoots because it treats gap 1's excess, mostly weekly shocks, as a weekly
trend. It is a bound, not an estimate.

Direct comparison, post hoc: real placebo excess variance is 11.8 pp² (first) and 6.7 (second).
The within-build scans at gap 4, the nearest to the real blocks' distance, give 4.07 pooled, 5.12
and 5.44 in early scans, and 1.74 late. So early-scan shares are 0.43–0.46 (first) and 0.76–0.81
(second), and the pooled ones 0.35 and 0.61. These flatter drift: 1-week blocks keep shocks that
the real multi-week blocks average out.

Reading. [inferred]
- Test 1's budget assumes the steady trend that test 2 rejects, so 0.66 / 0.70 is an upper
  reading. Test 2's 0.12 / 0.20 is low, because its fit mixes in the late scan and measures no
  release. The defensible range is about **0.35–0.7**: part, not all.
- **First patch has the larger shortfall:** at least 6 pp² isn't reached by anything within a
  build. Test 1 can't see a step at a release, so that's where any step would sit, along with
  spillover and everything else. A shortfall doesn't identify a cause, as declared.
- Block timing alone goes some way to the factors' difference: the same sigma_g gives 3.37 and 2.30
  (ratio 1.47; actual 1.53) because the first window's blocks are about a week further apart. That
  relies on the steady trend, so it's suggestive only. On test 2's shape the ratio is 1.14.

### 4. Detrended placebo [computed]

Tables: `n_detrended_pairs.csv`, `n_detrended.csv`, `n_detrended_bench.csv`. 463 fits, one per pair.

| | First | Second |
|---|---|---|
| Saved robust sd z (factor) | 4.10 | 2.67 |
| Detrended, clustered SE | 5.01 | 4.47 |
| **Detrended, corrected SE (declared primary)** | **2.11** | **1.40** |
| **Noise-only benchmark, post hoc** | **1.98** | **1.28** |
| sd β before → after detrending (pp) | 3.80 → 5.32 | 3.28 → 7.42 |
| Median SE before → corrected (pp) | 0.82 → 1.93 | 0.95 → 3.18 |

Would the pre-slope have predicted the placebo β, post hoc? All-offers pairs only: 197 first, 206
second. The 60 upgraded-offers pairs have so few offers that they swamp the noise term.

| | First | Second |
|---|---|---|
| Coefficient of β on the projection [95%] | +0.08 [−0.06, +0.23] | −0.02 [−0.12, +0.10] |
| Expected if pre-trends carried on (reliability of the pre-slope) | 0.68 | 0.20 |
| R² | 0.006 | 0.000 |

Reading. [inferred]
- **The declared rule gives the wrong answer here, and the fault is in the rule I wrote.** The
  corrected robust sd falls to 2.11 / 1.40, which reads as "part" and "explains". But detrending
  made β noisier, not tighter, and the fall comes entirely from the larger SE in the denominator.
  The benchmark shows it: pure noise in place of the pre-slope gives 1.98 / 1.28, as low as or
  lower than the real thing. **Detrending removed nothing.**
- **Linear pre-trends don't carry across a release.** In the first patch the pre-slope is well
  measured, and its coefficient is far below 0.68. The second patch's is less sharp, but its
  interval also stops short of 0.20.
- As declared, this doesn't rule out drift: a pre-slope says nothing about a random walk or about
  movement that starts at a release. It does fit the fading in tests 1 and 2.

### 5. Mix check [computed]

Table: `n_mix.csv`. sigma_g, logit per week, at matched horizons.

| View | sigma_g [95%] | Lack-of-fit SE |
|---|---|---|
| Unstratified | 0.035 [0.033, 0.037] | 0.031 |
| **Fixed band × act mix** | **0.030 [0.028, 0.033]** | 0.027 |
| Within A0 | 0.028 [0.023, 0.032] | 0.011 |
| Within A1–4 | 0.035 [0.032, 0.038] | 0.028 |
| Within A5–8 | 0.045 [0.040, 0.049] | 0.034 |
| Within A9–10 | 0.059 [0.053, 0.064] | 0.042 |

| Build | Unstratified | Fixed mix | Change |
|---|---|---|---|
| v0.99.1 | 0.037 | 0.040 | +9% |
| v0.103.2 | 0.037 | 0.028 | −24% |
| v0.107.1 | 0.031 | 0.020 | −35% |

Reading. [inferred]
- Overall −13%, within the declared 25%: drift isn't mostly player mix.
- **That average hides a pattern:** mix accounts for nothing in the earliest build and about a third
  of v0.107.1's. At a fixed mix the predicted order appears, 0.040 > 0.028 > 0.020, with clear
  intervals. So settling over early access may be real and partly masked by changes in who plays.
  This view is the mix check's, not test 1's declared one.
- Within-band sigma_g is not lower than the overall value, which also argues against mix. Don't read
  the rise with ascension as a finding: bands are smaller, SEs are binomial while weekly noise is
  over-dispersed, and the lack-of-fit column moves a lot (A0 0.028 → 0.011).

### What this does and doesn't settle

- **Settled, within limits:** unchanged cards drift within builds; it isn't a steady trend; linear
  pre-trends don't continue across a release. Detrending shouldn't be used for calibration.
- **Fits but not shown:** movement in the weeks after a release that settles by about week 8. Only
  v0.107.1 is long enough to show this. Section I's fake patch, on the 1,873-page tables, is
  consistent: spread of the placebo's size across a release that changed no cards.
- **Not settled:** what fills the rest of the spread, especially at least 6 pp² in the first patch.
  Section M didn't find spillover there, and nothing here measures a step at a release directly.
- The factors are unaffected: they measure the spread and don't depend on its cause.

---

## O. Forensics on the largest placebo misses — EXPLORATORY

**EXPLORATORY.** Proposed by Phil after sections M and N were seen. Nothing in this section
changes the calibration factors, the numbers module, the guide or any headline result. Script:
`triage/scripts/o_forensics.py`; tables in `triage/out_final/o_*.csv`. Inputs: the final tables
(`data/runs/runs.duckdb`, read-only), `data/analysis/placebo_h3.parquet` (weeks 0–3, 463 pairs,
one row per (window, pseudo card)), and the M and N tables (`m_exposure_pairs.csv`,
`n_slopes.csv`). Colors are derived (`db.py`); `reference/raw/` stays closed.

### Rules and what each outcome means, written before running

Written 2026-11-10, before any number of this section was computed. What I had looked at: M's
and N's saved tables and text, the count of runs by uploader tag and token, the number of pairs
per window, the week layout of one window's offers, and the time one fit takes. Git writes are
blocked in this session, so no commit timestamps this order; the claim rests on this note.

**1. Concentration.** Pairs sorted by z², largest first. Excess of a pair is z² − 1. The curve
is the cumulative share of total excess against the share of pairs, per patch and pooled. Then
the robust sd (1.4826 × MAD) and plain sd of z, per patch and pooled, after dropping the 5, 10,
20 and 46 pairs with the largest z² (pooled ranking; 46 is 10% of 463).

- Phil's rule, as given: **the top 10% of pairs carrying > 50% of the excess = tail-driven;
  < 25% = broad.** Between 25% and 50% the rule names no outcome, so that counts as mixed.
- Tail-driven means a minority of cards hold the miscalibration: the forensics of test 2 are
  the right tool, and a fix could target those cards. Broad means most unchanged cards miss by
  a few SEs: there is no handful to explain, and only a general cause (drift, a step at a
  release, an SE that is too small everywhere) would do.
- Added by me, before running, because the two cutoffs aren't symmetric around what "broad"
  produces. If every z were normal with one inflated sd s (as broad as it gets with honest
  shape), the top 10% would carry (0.439 s² − 0.1) / (s² − 1) of the excess: **0.46 at s = 4.10
  and 0.49 at s = 2.67.** Even a flat (uniform) z gives about 0.27. So "< 25%" can't
  happen, and a share just over 50% is close to what a plain normal gives. I report the share
  next to a simulated normal benchmark (same number of pairs, sd = the patch's plain sd, 10,000
  draws) with its 95% range. Above that range: heavier tails than a normal. Inside it: the
  spread is a normal's, scaled up, whatever side of 50% it falls.
- The drop table is the more direct reading, since the factors are robust sds, which a few
  pairs can't move. The same normal benchmark gives what each sd would be after the same drops.
  Robust sd still near the factor after dropping 46: broad. Plain sd falling to the robust sd:
  the tail explains the gap between the two, not the factor.

**2. Influence on the top 25.** The 25 pairs with the largest |z|, ranked over both patches
together (so most are expected from the first patch; each row says which). Each is refit with
its first tweak's window row and compared with that refit's own baseline, which must
reproduce the saved z. Slices, each removed from the whole fit (the card and its controls):

- Uploader: each of the 10 tokens with the most offers of that card in the fit. Tokens exist on
  about 16% of runs, so the rest are one slice, `no token`. Because "untagged" in this
  repository means "no SlayTheStats tag" (`group`), which is a different split, `untagged` and
  `tagged` are also removed, each as one slice. Uploaders are written as ranks, not hashes.
- Week: each week of the before block (offers of before builds played after the release
  pooled as one slice) and each of weeks 0–3 of the after block.
- Ascension band: A0, A1–4, A5–8, A9–10, as in N.

Reported per card: the largest single |Δz| and its slice, and every slice in a long table.
Also saved for plotting: weekly offers and pick rate of each top card, and its controls' pooled
rate and mean of card rates. No figures.

- Phil's rule, as given: **a slice whose removal alone takes |z| below 2 is a driver for that
  card.**
- Added by me, before running. Removing a slice also removes data, so the SE grows and |z|
  falls with β unchanged; `no token` and `untagged` are each about 80% of the offers. So each
  refit also reports z with the baseline β over the new SE. A driver under the rule is called
  **precision only** when that number is already below 2, and **a driver of β** when it isn't.
  Only the second says the slice produced the miss.
- Outcomes. Most top cards with a driver of β of one kind (one uploader, one week, one band):
  that mechanism (C's hypotheses 3, 4 or 5) is the lead for the tail. Few or none: the misses
  are spread across uploaders, weeks and bands, which is what a card-level shift between the
  blocks looks like, whatever caused it.
- Limit: about 30 slices per card and cards chosen for extreme z, so some shrinkage of |z|
  under any removal is expected.

**3. Predicting misses.** One row per pair (463). Targets z² and |z|. Features:

| Feature | Source |
|---|---|
| Character | pair's color, five indicators |
| Rarity | derived from offer tiers, as N (Common, Uncommon, Rare as 0, 1, 2) |
| Type | only in `reference/raw/`: blank in the sandbox and then left out of the model |
| Base pick rate | the pseudo card's rate before, from the saved fit |
| Offers before, after | from the saved fit, log |
| Within-build slope, lack of fit | `n_slopes.csv`, pp per week at the matched horizon, relative to the build × character mean, signed and absolute; chi²/df. From the build before the window: v0.99.1 for the first patch, v0.103.2 for the second (v0.103.3 has no slope). The after build's slope overlaps the outcome weeks, so it is not used. Blank when the card changed entering that build |
| Exposure | `m_exposure_pairs.csv`, after block: signed; screen and run (substantive) as unsigned |
| Behavior or bug-fix events | `window_changes`' flag for the card in the window, and the number of new behavior events |
| Top-uploader share | largest single token's share of the card's offers in the fit; also the top 10's |
| Untagged share | share of the card's offers without the SlayTheStats tag; also the share without a token |
| Upgraded-offers fit | added by me: 60 pairs are fit on upgraded offers only |

Patch is not a feature. XGBoost with fixed settings chosen here and not tuned (depth 3,
learning rate 0.05, 200 trees, subsample 0.8, column sample 0.8, min child weight 5, squared
error). Five folds holding out whole cards (a card in both patches stays together), repeated
over 20 splits. CV R² = 1 − SSE / SST out of fold, SST around each training fold's mean,
averaged over splits. SHAP values are XGBoost's own TreeSHAP on the model fit to all pairs,
reported as mean |SHAP|. Then one model trained on the first patch's pairs scores the second
patch's with no refit.

- Phil's rule, as given: **CV R² < 0.05, or no transfer to patch 2 = no predictive feature
  found.**
- Definitions added by me, before running:
  - Transfer is judged by rank: Spearman between the first-patch model's predictions and the
    second patch's actual target, 95% interval resampling cards. Interval above 0 = transfer.
    The level of z² differs by patch (factors 4.10 and 2.67), so raw R² on the second patch is
    expected to be negative from the level alone; it is reported but doesn't decide. Transfer
    is also reported on second-patch cards that are not in the first patch, since 95 cards are
    in both and C found their z correlated (+0.45).
  - The patch contrast: z² is larger in the first patch, so any feature that differs by patch
    (exposure, offers) earns pooled R² without saying anything about cards; M's test 2 hit
    this. So CV R² is also reported for a model whose only feature is the patch, and within
    each patch. A pooled R² that is ≥ 0.05 but not above the patch-only model restates the
    patch contrast and counts as no predictive feature. A permutation null (target shuffled
    within patch, 200 times) gives the R² expected from that alone.
  - A mechanical link: z = β / SE, and offers and base rate set the SE. C found the spread of
    β doesn't shrink with the SE, so more offers means a larger z² with no cause behind it. So
    the same model is also run on β² (pp²). If z² is predictable and β² isn't, the feature
    found is precision.
- SHAP is only read if the rule is passed; with CV R² near 0 it describes a fit to noise.

### Answer

**The misses are broad, and the largest ones are steps at the release that no uploader, week or
ascension band produces. Nothing in the feature list predicts which cards miss.** The top 10%
of pairs carry just over half the excess, which the rule calls tail-driven, but a normal with
the same sd gives nearly that, and the robust sd is still 3.4 and 2.5 after the top 10% are
gone. So there is no handful of cards to fix, and the factors stay as they are. [inferred]

### Declared outcomes [computed]

| Test | Result | Outcome under the rule | Reading |
|---|---|---|---|
| 1. Concentration | Top 10% carry 0.57 pooled, 0.53 first, 0.55 second | **Tail-driven** (> 0.50) | A normal gives 0.51, 0.46, 0.49. The first patch is just above the normal's range, the second inside it. Robust sd after dropping 46: 3.36 / 2.50. **Broad** |
| 2. Influence | 2 of 25 cards have a driver, both `no token`, both second patch | **No driver for 23 of 25** | No single uploader, week or band takes any card below \|z\| = 3.8. The 2 are weak (see test 2) |
| 3. Prediction | CV R² −0.05 (z²), 0.01 (\|z\|); transfer Spearman +0.28 [0.16, 0.40] | **No predictive feature found** (R² < 0.05) | Rank transfers weakly. The patch alone gives R² 0.05–0.06 |

### Checks and changes after the rules [computed]

- `--check`: this script's fit path returns the saved z for the largest pair of each patch
  (|Δz| ≤ 5e-08). Uploader shares from the SQL equal those counted in the fit data. `top_share`
  passes two known-answer checks, including the 0.46 at s = 4.10 quoted in the rules.
- `placebo_h3` gives 463 pairs and first-patch robust sd 4.10; the script stops otherwise.
- **Tolerance loosened during the run.** Part 2 stopped at Haunt: its refit z differed from the
  saved one by 9e-06, over my 1e-06. With derived colors that window has 69 control cards, not
  71; the two missing cards have 2 offers of 1.16 million. The tolerance is now 1e-04, and part 2
  was rerun from the start.
- **Card type: not in the model.** It exists only in `reference/raw/`. Set
  `TRIAGE_COLORS=reference` and rerun `--part 3` to include it.
- xgboost was not installed. It is now a `forensics` extra in `pyproject.toml`; here it ran from
  a temporary directory (`FORENSICS_PYLIB`), placed last on the path, so the environment's
  pandas and numpy were the ones used. SHAP values are XGBoost's own TreeSHAP (`pred_contribs`),
  not the `shap` package.
- 50 of 463 pairs have no slope (the card changed entering the earlier build), and 1 has no
  exposure row. XGBoost treats those as missing.
- **Part 4 is post hoc, added after reading tests 1–3:** the model on the features that set the
  SE and on the rest; a per-slice summary of test 2; the size of each top card's step against
  its weekly noise. Everything marked post hoc below comes from it.

### 1. Concentration [computed]

Tables: `o_concentration.csv`, `o_concentration_curve.csv` (the full curve, for plotting),
`o_drop_top.csv`. Plain sd z on these 463 pairs: 3.73 pooled, 4.46 first, 2.94 second. "Normal"
is the declared benchmark with its 95% range. The interval on the share resamples pairs.

| | Pooled | First | Second |
|---|---|---|---|
| Pairs | 463 | 217 | 246 |
| Share with \|z\| > 2 | 0.54 | 0.65 | 0.46 |
| Top 5% carry [95%] | 0.39 [0.35, 0.43] | 0.33 [0.28, 0.38] | 0.38 [0.31, 0.44] |
| Normal | 0.34 [0.30, 0.39] | 0.29 [0.24, 0.35] | 0.32 [0.27, 0.38] |
| **Top 10% carry [95%]** | **0.57 [0.52, 0.61]** | **0.53 [0.47, 0.58]** | **0.55 [0.47, 0.62]** |
| Normal | 0.51 [0.46, 0.56] | 0.46 [0.40, 0.52] | 0.49 [0.43, 0.55] |
| Top 20% carry [95%] | 0.76 [0.72, 0.80] | 0.73 [0.68, 0.77] | 0.78 [0.72, 0.83] |
| Normal | 0.72 [0.68, 0.76] | 0.68 [0.62, 0.73] | 0.71 [0.66, 0.77] |

After dropping the pairs with the largest z² (pooled ranking). Each cell is robust sd / plain
sd, with the normal benchmark's in brackets:

| Dropped | From first, second | Pooled | First | Second |
|---|---|---|---|---|
| 0 | 0, 0 | 3.31 / 3.73 [3.52 / 3.73] | 4.10 / 4.46 [4.45 / 4.45] | 2.68 / 2.94 [2.92 / 2.94] |
| 5 | 5, 0 | 3.27 / 3.55 [3.48 / 3.54] | 3.98 / 4.13 [4.33 / 4.14] | 2.68 / 2.94 [2.92 / 2.92] |
| 10 | 9, 1 | 3.19 / 3.38 [3.43 / 3.42] | 3.86 / 3.90 [4.23 / 3.94] | 2.64 / 2.87 [2.92 / 2.90] |
| 20 | 17, 3 | 3.10 / 3.13 [3.34 / 3.22] | 3.68 / 3.50 [4.03 / 3.64] | 2.64 / 2.78 [2.89 / 2.83] |
| 46 | 34, 12 | 2.86 / 2.70 [3.11 / 2.85] | 3.36 / 2.94 [3.59 / 3.11] | 2.50 / 2.49 [2.80 / 2.63] |

After the 46 are gone, 58% of the first patch's remaining pairs and 43% of the second's still
have |z| > 2.

Reading. [inferred]
- **Under the rule as given: tail-driven, in both patches.** I don't think that reading holds,
  for the reason declared: a plain normal lands at 0.46–0.51. The first patch is above the
  normal's range by 0.01 and the second is inside it, so the tails are a little heavier than a
  normal's and no more.
- **The drop table says broad.** The robust sd falls from 4.10 to 3.36 and from 2.68 to 2.50,
  about as a normal's would under the same trimming, and nowhere near 1. Removing the worst
  tenth of the cards leaves the factors at 80–95% of their size.
- The plain sd falls to the robust sd by the 20th drop. So the tail explains why the plain sd
  (4.46 / 2.94) sits above the factor (4.10 / 2.67), and not the factor.
- 34 of the 46 are first-patch pairs, where a normal mixture expects 37: the first patch
  holds most of the tail because its whole distribution is wider.

### 2. Influence on the top 25 [computed]

Tables: `o_top_pairs.csv` (one row per pair), `o_influence.csv` (667 refits, none failed),
`o_top_weekly.csv` (605 rows: offers and pick rate by block and week for each card, with its
controls' pooled rate and mean of card rates; before-build offers played after the release are
in it with their own weeks, and are thin). 21 of the 25 are first-patch pairs, 4 second; 10
Silent, 7 Regent, 5 Ironclad, 3 Necrobinder; 16 positive, 9 negative. Pillar of Creation is in
twice, rank 1 (first patch, z +13.6) and rank 9 (second, +10.5). All 25 are all-offers fits.

β in pp. "Largest" is the single slice with the largest |Δz|; "z, β held" is the baseline β
over the new SE, so it shows how much of the fall is lost precision.

| Rank | Patch | Card | z | β (SE) | Largest slice (share of the card's offers) | z without it | z, β held | Lowest \|z\| over all slices |
|---|---|---|---|---|---|---|---|---|
| 1 | first | Pillar of Creation | +13.6 | +9.7 (0.7) | no token (0.81) | +4.8 | +6.0 | 4.8 |
| 2 | first | Piercing Wail | +11.6 | +5.3 (0.5) | no token (0.82) | +2.7 | +4.9 | 2.7 |
| 3 | first | Setup Strike | −11.5 | −4.8 (0.4) | A9–10 (0.21) | −5.9 | −9.5 | 5.9 |
| 4 | first | Ricochet | −11.1 | −4.9 (0.4) | no token (0.82) | −2.4 | −4.5 | 2.4 |
| 5 | first | Bloodletting | +11.1 | +5.2 (0.5) | untagged (0.73) | +5.9 | +5.9 | 5.9 |
| 6 | first | Tactician | −11.1 | −9.2 (0.8) | no token (0.82) | −3.3 | −4.7 | 3.3 |
| 7 | first | Reflex | −11.0 | −9.7 (0.9) | no token (0.82) | −3.4 | −4.7 | 3.4 |
| 8 | first | Crescent Spear | −10.7 | −5.0 (0.5) | no token (0.81) | −4.6 | −4.6 | 4.6 |
| 9 | second | Pillar of Creation | +10.5 | +9.3 (0.9) | no token (0.91) | +2.6 | +3.1 | 2.6 |
| 10 | first | Know Thy Place | +10.2 | +4.8 (0.5) | no token (0.81) | +4.7 | +4.5 | 4.7 |
| 11 | first | Blood Wall | +9.9 | +4.8 (0.5) | no token (0.81) | +3.9 | +4.2 | 3.9 |
| 12 | first | Haunt | −9.9 | −8.7 (0.9) | no token (0.80) | −4.9 | −4.5 | 4.9 |
| 13 | first | Dodge and Roll | +9.7 | +3.4 (0.4) | no token (0.82) | +4.6 | +4.0 | 4.6 |
| 14 | first | Leg Sweep | +9.6 | +7.0 (0.7) | untagged (0.73) | +4.1 | +4.9 | 4.1 |
| 15 | first | Footwork | +9.4 | +7.8 (0.8) | no token (0.82) | +3.6 | +3.9 | 3.6 |
| 16 | first | Devastate | −8.8 | −6.3 (0.7) | no token (0.81) | −2.1 | −3.8 | 2.1 |
| 17 | first | Lethality | +8.6 | +7.9 (0.9) | untagged (0.73) | +4.4 | +4.5 | 4.4 |
| 18 | second | Second Wind | +8.6 | +5.6 (0.7) | no token (0.92) | **+0.8** | +2.4 | 0.8 |
| 19 | second | Begone | +8.6 | +5.0 (0.6) | no token (0.90) | **+0.1** | +2.4 | 0.1 |
| 20 | first | Breakthrough | +8.4 | +3.3 (0.4) | untagged (0.73) | +3.7 | +4.6 | 3.7 |
| 21 | first | Blur | +8.4 | +6.7 (0.8) | untagged (0.72) | +4.6 | +4.3 | 4.6 |
| 22 | first | Master Planner | −8.3 | −10.1 (1.2) | no token (0.82) | −2.7 | −3.5 | 2.7 |
| 23 | first | Backflip | +8.2 | +3.9 (0.5) | no token (0.82) | +3.0 | +3.5 | 3.0 |
| 24 | second | Wrought in War | −7.7 | −4.1 (0.5) | no token (0.91) | −2.5 | −2.4 | 2.5 |
| 25 | first | Enfeebling Touch | +7.7 | +7.0 (0.9) | A9–10 (0.17) | +4.7 | +7.0 | 4.7 |

By slice, post hoc (`o_posthoc_slices.csv`). "β kept" is the refit β over the baseline β.

| Slice removed | Median share of the card's offers | β kept, median (range) | Largest \|Δz\| | Lowest \|z\| left |
|---|---|---|---|---|
| Any one token (250 refits) | 0.002 (max 0.007) | 1.00 (0.95–1.04) | 0.39 | 7.5 |
| No token | 0.82 | 0.93 (0.03–1.52) | 8.92 | 0.1 |
| Untagged | 0.73 | 1.05 (0.75–2.43) | 6.58 | 2.6 |
| Tagged | 0.28 | 0.98 (0.77–1.09) | 4.03 | 5.3 |
| Any one before week | 0.02–0.17 | 0.98–1.02 (0.85–1.15) | 2.45 | 6.0 |
| After, week 0 | 0.15 | 0.99 (0.74–1.29) | 2.78 | 4.9 |
| After, weeks 1–3, each | 0.08–0.11 | 1.00–1.01 (0.82–1.13) | 2.04 | 6.5 |
| A0 | 0.21 | 1.01 (0.65–1.27) | 2.92 | 4.8 |
| A1–4 | 0.35 | 1.15 (0.86–1.42) | 3.42 | 6.8 |
| A5–8 | 0.22 | 1.03 (0.78–1.21) | 3.48 | 6.3 |
| A9–10 | 0.21 | **0.76** (0.52–1.01) | 5.52 | 3.8 |

Step against weekly noise, post hoc (`o_posthoc_step.csv`). For each top card: its gap to the
controls' pooled rate by week; the step is the mean gap after minus before. Over the 25 cards
the step is 2.1 to 22 times the sd of the weekly gap before (median 3.9), and in 23 of 25 more
than half of it is already there between the last week before and week 0 (median share 1.0).

Reading. [inferred]
- **No uploader is behind any of these.** The largest token holds at most 0.7% of a card's
  offers, and removing any one moves z by at most 0.4. C's hypothesis 3, as heavy uploaders,
  is out for the tail.
- **No week is behind them.** Removing any single week keeps 74–129% of β and leaves every
  card at |z| ≥ 4.9. A one-week shock (C's hypothesis 4) doesn't make these misses.
- **They look like steps at the release.** The shift is present in week 0 and holds through
  week 3, and for most cards the gap before is flat. These cards were chosen for a large after-minus-before
  difference, so a shift is guaranteed; that it arrives at once and not as a drift through the
  before block is the part that carries information. It matches N: pre-trends don't carry
  across a release, and the first patch's shortfall sits where a step would.
- **A9–10 players hold more of the shift than their share.** They are 21% of offers, and
  without them β falls by a median 24%; without A1–4 it rises 15%. No band alone takes a card
  below |z| = 3.8, so this is a gradient and not a driver. It fits N's rising drift with
  ascension, which N warned not to read as a finding; it is post hoc here too.
- **The 2 drivers under the rule are weak.** Begone and Second Wind, both second patch: on the
  8–10% of their offers with a token, β is +0.1 and +1.8 pp, against +5.0 and +5.6. Those
  subset fits have SEs of about 2.1 and 2.4 pp, so each is about 2 SEs from the full estimate,
  among 50 `no token` and `untagged` refits. They pass my own "driver of β" test only because
  that test compared against |z| = 2 and not against the subset's error. The other 23 cards'
  token subsets agree with the full fit (median β kept 0.93).
- Every other fall in |z| under `no token` or `untagged` is lost precision: "z, β held" is
  about what the refit gives.
- Pillar of Creation moves +9.7 pp and then +9.3 pp in two windows that list it as unchanged.
  Whether that is a change the tables don't record or players finding the card can't be told
  from here. [unverified]

### 3. Predicting misses [computed]

Tables: `o_features.csv` (463 rows), `o_cv.csv`, `o_transfer.csv`, `o_shap.csv`,
`o_posthoc_split.csv`. 22 features, 312 cards. CV R² is the mean over 20 splits, with the
range. "Null" is the same model with the target shuffled within patch.

| Target | Scope | CV R² (range) | Null mean, 95th pct | p |
|---|---|---|---|---|
| z² | Pooled | **−0.05** (−0.10, −0.01) | −0.11, −0.01 | 0.16 |
| z² | Patch only, pooled | 0.05 (0.04, 0.05) | | |
| z² | First | −0.13 (−0.24, −0.06) | −0.23, −0.10 | 0.10 |
| z² | Second | −0.05 (−0.20, 0.06) | −0.22, −0.09 | 0.02 |
| \|z\| | Pooled | **0.01** (−0.03, 0.06) | −0.09, −0.01 | 0.03 |
| \|z\| | Patch only, pooled | 0.06 (0.05, 0.07) | | |
| \|z\| | First | −0.10 (−0.23, −0.03) | −0.22, −0.10 | 0.06 |
| \|z\| | Second | −0.03 (−0.14, 0.06) | −0.22, −0.09 | 0.02 |
| β² (pp²) | Pooled | 0.05 (−0.12, 0.19) | −0.16, −0.09 | 0.005 |
| β² (pp²) | First | −0.05 (−0.17, 0.08) | −0.23, −0.08 | 0.03 |
| β² (pp²) | Second | 0.21 (−0.13, 0.32) | −0.19, −0.09 | 0.005 |

Trained on the first patch, scored on the second, no refit:

| Target | Scored on | Pairs | Spearman [95%] | R², no refit |
|---|---|---|---|---|
| z² | All second-patch pairs | 246 | +0.28 [0.16, 0.40] | −3.7 |
| z² | Cards not in the first patch | 118 | +0.28 [0.11, 0.44] | −3.9 |
| z² | Cards in both | 128 | +0.24 [0.06, 0.40] | −3.7 |
| \|z\| | All second-patch pairs | 246 | +0.25 [0.14, 0.36] | −2.1 |
| \|z\| | Cards not in the first patch | 118 | +0.18 [0.02, 0.34] | −2.1 |
| β² | All second-patch pairs | 246 | +0.24 [0.12, 0.35] | −0.2 |

Mean |SHAP| on the model fit to all pairs, top six, as a share of the total (the sign is the
rank correlation of the feature with its SHAP value):

| z² | \|z\| | β² |
|---|---|---|
| log offers before 0.23 (+) | log offers before 0.22 (+) | top-uploader share 0.15 (+) |
| lack of fit 0.13 (+) | screen exposure 0.14 (+) | screen exposure 0.11 (+) |
| log offers after 0.11 (+) | lack of fit 0.11 (+) | top-10 uploader share 0.11 (+) |
| screen exposure 0.10 (+) | log offers after 0.10 (+) | base rate 0.10 (+) |
| untagged share 0.10 (−) | untagged share 0.08 (−) | signed exposure 0.09 (−) |
| signed exposure 0.07 (+) | no-token share 0.06 (−) | log offers before 0.09 (−) |

Character, rarity, the behavior flag and the upgraded-offers flag are each under 0.01.

Feature groups, post hoc (pooled CV R²; transfer Spearman on all second-patch pairs):

| Features | z²: R², transfer | \|z\|: R², transfer | β²: R², transfer |
|---|---|---|---|
| Declared (22) | −0.05, +0.28 [0.16, 0.40] | 0.01, +0.25 [0.14, 0.36] | 0.05, +0.24 [0.12, 0.35] |
| Precision only: offers, base rate, upgraded fit (4) | −0.02, +0.17 [0.04, 0.29] | 0.00, +0.07 [−0.05, 0.20] | 0.05, +0.18 [0.05, 0.30] |
| Declared without those (18) | −0.05, +0.19 [0.06, 0.30] | 0.02, +0.23 [0.11, 0.35] | 0.05, +0.24 [0.10, 0.36] |

Reading. [inferred]
- **Under the rule: no predictive feature found.** CV R² is below 0.05 for z² and |z|, pooled
  and within each patch, and below what the patch label alone gives (0.05–0.06). The features
  don't even recover the patch contrast.
- **The rule's two halves disagree, and the first decides.** Transfer by rank is there (+0.28,
  interval above 0), including on cards the first-patch model never saw. So the features carry
  a weak ordering of cards by how much they miss, and it is too weak to predict a size: a
  Spearman of 0.28 is about 8% of rank variance.
- **My settings made R² a harsh test.** The untuned 200-tree model overfits: on shuffled
  targets it scores −0.11 to −0.23, where a model that learned nothing would score about 0.
  The real fits beat that null in most rows (p 0.02–0.16) while staying under 0. The threshold
  was applied as declared; a shallower or tuned model might clear 0, though probably not by
  much, given the rank correlation.
- **SHAP is not read as a finding**, as declared, since the rule wasn't passed. For the
  record, offers lead for z² and |z|, with a positive sign. That is the mechanical link
  declared beforehand: C found β's spread doesn't shrink with the SE, so more offers give a
  larger z.
- **The β² check didn't separate cause from precision, and I should have seen why.** β² holds
  the SE² too, so cards with few offers have a larger β² from noise alone, and its SHAP ranks
  the top uploader's share (largest when offers are few) and base rate first. Its pooled R² of
  0.05 swings from −0.12 to 0.19 across splits, and the second patch's 0.21 from −0.13 to
  0.32, so a few pairs set it.
- The post hoc split doesn't isolate precision either. The 18 other features still transfer
  (+0.19 to +0.23), but uploader shares and exposure both track how often a card is offered.
- Drift's lack of fit ranks second or third for z². It is the one feature tied to a mechanism
  (cards with noisy weeks earlier miss more later), and it fits N. With R² below 0 it is a
  lead and not a result.

### What this does and doesn't settle

- **Settled, within limits:** the placebo miss is broad and not the work of a few cards. For
  the 25 largest, it is not one uploader and not one week. The features on hand can't say
  which cards will miss.
- **Fits but not shown:** a step in an unchanged card's pick rate at a release, larger among
  high-ascension players. That is what M's and N's leftover looked like, and now the top
  cards show it directly, but only the top 25 were refit, and they were selected for it.
- **Not settled:** what the step is. Changes outside cards (relics, enemies), a shift in how a
  character is played after its changed cards move, and unrecorded card changes all remain,
  and nothing here separates them. Pillar of Creation is the place to start by hand.
- The factors are unaffected: they measure the spread and don't depend on its cause.

---

## P. Archetype (complement) spillover — EXPLORATORY

**EXPLORATORY.** The pattern was found post hoc by Phil on Regent, after sections M, N and O
were seen. Nothing in this section changes the calibration factors, the numbers module, the
guide or any headline result. Script: `triage/scripts/p_archetype.py`; tables in
`triage/out_final/p_*.csv`. Inputs: `data/analysis/placebo_h3.parquet` (weeks 0–3, 463 pairs),
`reference/change_events.csv`, `patch_notes_cards.csv`, `card_changes.csv`, and card text.

**The discovery (Phil, post hoc).** Among Regent placebo pairs (all offers, weeks 0–3), cards
whose text creates cards or pays off creating them had positive z in 7 of 7 (first patch) and
9 of 10 (second), against about a third of other Regent cards. The first window's changes to
that archetype were mostly reworks and cost changes (Arsenal, Begone, Charge, Bundle of Joy),
plus Collision Course and Heirloom Hammer tweaks. This section tests the idea on Defect,
Ironclad, Necrobinder and Silent.

### Rules, written before any placebo z of the four test characters was read for this section

Written 2026-11-10. Git writes are blocked in this session, so no commit timestamps this
order; the claim rests on this note and on the order of the section. Everything down to
"Results" was written, and `p_archetypes.csv`, `p_changes.csv` and `p_archetype_windows.csv`
were saved, before parts 3–5 of the script (the only ones that load a z) were run.

**What I had already seen, which the order can't undo.** Section O prints z for its 25 largest
pairs, and 18 of them are cards of the test characters: 10 Silent, 5 Ironclad, 3 Necrobinder.
I knew, when writing the rules, that four Silent cards with Sly (Ricochet, Tactician, Reflex,
Master Planner) were strongly negative in the first patch and that three Ironclad cards that
lose HP (Bloodletting, Blood Wall, Breakthrough) were strongly positive. Both sit in archetypes
below (`discard`, `hp_loss`). The rules are plain keyword rules that I would have written
anyway, but that can't be shown. So the test is also reported with every pair of O's top 25
left out, and that row should be read next to the declared one.

**Card text.** Full text exists only in `reference/raw/cards.json`, which this session's
sandbox does not open; Phil copied the file to the session's scratch folder for this task, and
the script reads it through `P_CARDS` (default: the file in `reference/raw/`). It is stable
v0.107.1's text. Text in force earlier is rebuilt in two steps: `card_changes.csv`'s old
descriptions, then old wordings quoted in the patch notes (`TEXT_AT` in the script, each with
its source). Limits:
- `card_changes.csv` cuts descriptions at about 80 characters, and for five reworks (Stoke,
  Dominate, Spite, Glow, Shatter) the earlier wording is in neither source. A card whose
  earlier text is cut or unknown keeps its later memberships too, so it can't be seen entering
  an archetype.
- Begone, Charge and Cinder's earlier wording is rebuilt from the notes and the changed
  fields, not quoted.
- A placebo card is unchanged in its window, so its text there is one text. Its archetypes
  come from that window's text, not from today's.

**Archetype rules.** One list of keyword rules, applied by regular expression to the text with
markup removed, plus a few structured fields. A card is in every archetype it matches. A card
is a member whether it makes the thing or pays off for it, since both are complements of the
other members. An archetype exists for a character in a window when at least 3 of its
reward-pool cards (Common, Uncommon, Rare) match. `create` is the discovery's archetype, in
the same words for every character. 96 of 439 cards match no archetype in each window.

| Archetype | Characters | Text matches (markup removed) | Also a member by |
|---|---|---|---|
| create | all | `\b[Aa]dds? (?:a ¦an ¦\d+ ¦X )?.*\b(?:into¦to) (?:your¦their) (?:Hand¦Draw Pile¦Discard Pile)¦Transform¦\bcop(?:y¦ies) of¦[Cc]reated?\b¦Fill your Hand` |  |
| exhaust | all | `Exhaust` |  |
| debuff | all | `\bWeak\b¦Vulnerable¦debuff` |  |
| strength | all | `[Gg]ain \d+ Strength` |  |
| attack_play | all | `\bAttacks?\b` |  |
| skill_play | all | `\bSkills?\b` |  |
| power_play | all | `\bPowers?\b` |  |
| block_payoff | all | `your Block\b¦gain Block\b¦Block is not removed¦Block from a card¦Block gain¦Gain Block equal` |  |
| draw | all | `[Dd]raw \d+ (?:additional )?cards?¦[Dd]raw cards¦[Ww]henever you draw¦draw an? ¦cards? drawn` |  |
| discard | all | `\b[Dd]iscard(?:ed)? (?!Pile)¦\bSly\b` | keywords:Sly |
| hp_loss | all | `(?<!nemy )(?<!nemies )\b[Ll]ose \d+ HP¦\blost HP¦you lose HP¦lose \d+ HP and` |  |
| zero_cost | all | `0 ?\[energy:1\] (?:cards?¦Attacks?¦copy)¦do not cost 0` |  |
| ethereal | all | `Ethereal` | keywords:Ethereal |
| dexterity | all | `Dexterity` |  |
| orb | defect | `Channel¦Evoke¦\bOrbs?\b` |  |
| lightning | defect | `Lightning` |  |
| frost | defect | `Frost` |  |
| dark | defect | `\bDark\b` |  |
| focus | defect | `Focus` |  |
| status | defect | `Status` | spawns:BURN, DAZED, SLIMED, VOID, WOUND |
| poison | silent | `Poison` |  |
| shiv | silent | `Shivs?\b` | spawns:SHIV |
| osty | necrobinder | `Osty¦Summon` | tags:OstyAttack |
| doom | necrobinder | `Doom` |  |
| soul | necrobinder | `\bSouls?\b` | spawns:SOUL |
| forge | regent | `Forge¦Sovereign Blade` |  |
| star | regent | `\[star:` | star_cost:True |

(`¦` stands for the regular expression's alternation bar.) Choices made here, before z:
- The Exhaust keyword alone doesn't make a card an `exhaust` member; the text must mention it.
- Sly cards are in `discard`: Sly is what a discard pays off. They are not a separate archetype.
- `strength` is gaining Strength, not taking it from an enemy. `hp_loss` is the player's own.
- `zero_cost` is cards that refer to 0-cost cards as a group, not cards that make one card free.
- `draw` holds both cards that draw and cards that pay off drawing, so it is broad.
- Only a character's own cards count. Colorless cards, relics and enemies are outside this.

**Card → archetype, text at v0.107.1** (`p_archetypes.csv` has every card in both windows,
with the text used and its source). Basic and Ancient cards are listed but aren't in the
reward pool.

| Character | Archetype | Cards | Members (text at v0.107.1) |
|---|---|---|---|
| Defect | create | 12 | Adaptive Strike, Boost Away, Compact, Creative AI, Fight Through, Gunk Up, Overclock, Rocket Punch, Smokestack, TURBO, Trash to Treasure, White Noise |
| Defect | dark | 5 | Consuming Shadow, Darkness, Null, Rainbow, Shadow Shield |
| Defect | debuff | 3 | Beam Cell, Go for the Eyes, Null |
| Defect | draw | 12 | Compile Driver, Coolheaded, FTL, Iteration, Machine Learning, Modded, Overclock, Reboot, Rocket Punch, Scrape, Skim, Sweeping Beam |
| Defect | focus | 6 | Biased Cognition, Defragment, Focused Strike, Hotfix, Hyperbeam, Synchronize |
| Defect | frost | 7 | Chill, Cold Snap, Coolheaded, Glacier, Hailstorm, Ice Lance, Rainbow |
| Defect | lightning | 9 | Ball Lightning, Lightning Rod, Rainbow, Storm, Tempest, Tesla Coil, Thunder, Voltaic, Zap |
| Defect | orb | 37 | Ball Lightning, Barrage, Bulk Up, Capacitor, Chaos, Chill, Cold Snap, Compile Driver, Consuming Shadow, Coolant, Coolheaded, Darkness, Dualcast, Fusion, Glacier, Glasswork, Ice Lance, Ignition, Lightning Rod, Loop, Meteor Strike, Modded, Multi-Cast, Null, Quadcast, Rainbow, Refract, Shadow Shield, Shatter, Spinner, Storm, Synchronize, Tempest, Thunder, Trash to Treasure, Voltaic, Zap |
| Defect | power_play | 6 | Creative AI, Signal Boost, Storm, Subroutine, Synthesis, White Noise |
| Defect | status | 11 | Boost Away, Compact, Fight Through, Flak Cannon, Gunk Up, Iteration, Overclock, Rocket Punch, Smokestack, TURBO, Trash to Treasure |
| Defect | zero_cost | 4 | Adaptive Strike, All for One, Feral, Scrape |
| Ironclad | attack_play | 13 | Aggression, Expect a Fight, Infernal Blade, Juggling, One-Two Punch, Pillage, Primal Force, Rage, Second Wind, Stampede, Stomp, Thrash, Unrelenting |
| Ironclad | block_payoff | 5 | Barricade, Body Slam, Demonic Shield, Juggernaut, Unmovable |
| Ironclad | create | 5 | Anger, Infernal Blade, Juggling, Primal Force, Stoke |
| Ironclad | debuff | 13 | Bash, Break, Bully, Colossus, Cruelty, Dismantle, Dominate, Molten Fist, Taunt, Thunderclap, Tremble, Uppercut, Vicious |
| Ironclad | draw | 10 | Battle Trance, Burning Pact, Dark Embrace, Drum of Battle, Hellraiser, Offering, Pillage, Pommel Strike, Shrug It Off, Vicious |
| Ironclad | exhaust | 18 | Ashen Strike, Brand, Burning Pact, Cinder, Corruption, Dark Embrace, Drum of Battle, Evil Eye, Feel No Pain, Fiend Fire, Forgotten Ritual, Havoc, Howl from Beyond, Pact's End, Second Wind, Stoke, Thrash, True Grit |
| Ironclad | hp_loss | 12 | Blood Wall, Bloodletting, Brand, Breakthrough, Crimson Mantle, Demonic Shield, Hemokinesis, Inferno, Offering, Rupture, Spite, Tear Asunder |
| Ironclad | strength | 7 | Brand, Demon Form, Dominate, Fight Me!, Inflame, Rupture, Setup Strike |
| Necrobinder | attack_play | 3 | Lethality, Reaper Form, Squeeze |
| Necrobinder | create | 10 | Call of the Void, Capture Spirit, Dirge, Glimpse Beyond, Grave Warden, Reave, Seance, Sentry Mode, Severance, Undeath |
| Necrobinder | debuff | 8 | Deathbringer, Debilitate, Defy, Fear, High Five, Misery, Putrefy, Sleight of Flesh |
| Necrobinder | doom | 13 | Blight Strike, Countdown, Death's Door, Deathbringer, End of Days, Negative Pulse, Neurosurge, No Escape, Oblivion, Reaper Form, Scourge, Shroud, Time's Up |
| Necrobinder | draw | 7 | Death March, Demesne, Fetch, Neurosurge, Pagestorm, Parse, Scourge |
| Necrobinder | ethereal | 15 | Banshee's Cry, Call of the Void, Defile, Defy, Demesne, Enfeebling Touch, Fear, Lethality, Pagestorm, Parse, Pull from Below, Sculpting Strike, Seance, Spirit of Ash, Veilpiercer |
| Necrobinder | exhaust | 3 | Cleanse, Eidolon, Soul Storm |
| Necrobinder | osty | 25 | Afterlife, Bodyguard, Bone Shards, Calcify, Cleanse, Devour Life, Dirge, Fetch, Flatten, High Five, Invoke, Legion of Bone, Necro Mastery, Poke, Protector, Pull Aggro, Rattle, Reanimate, Right Hand Hand, Sacrifice, Sic 'Em, Snap, Spur, Squeeze, Unleash |
| Necrobinder | soul | 10 | Capture Spirit, Devour Life, Dirge, Glimpse Beyond, Grave Warden, Haunt, Reave, Seance, Severance, Soul Storm |
| Regent | create | 14 | Arsenal, BEGONE!, Bundle of Joy, CHARGE!!, Collision Course, Crash Landing, GUARDS!!!, Heirloom Hammer, Largesse, Manifest Authority, Pillar of Creation, Quasar, Spectrum Shift, Supermassive |
| Regent | debuff | 5 | Comet, Falling Star, Gamma Blast, Know Thy Place, Meteor Shower |
| Regent | draw | 12 | Big Bang, Decisions, Decisions, Glimmer, Glow, Guiding Star, Kingly Kick, Kingly Punch, Pale Blue Dot, Photon Cut, Prophesize, Spoils of Battle, Tyranny |
| Regent | forge | 14 | Beat into Shape, Big Bang, Bulwark, Conqueror, Furnace, Hammer Time, Parry, Refine Blade, Seeking Edge, Spoils of Battle, Summon Forth, Sword Sage, The Smith, Wrought in War |
| Regent | skill_play | 3 | Decisions, Decisions, Lunar Blast, Make It So |
| Regent | star | 34 | Alignment, Astral Pulse, Big Bang, Black Hole, Child of the Stars, Cloak of Stars, Comet, Convergence, Crescent Spear, Decisions, Decisions, Devastate, Dying Star, Falling Star, Gamma Blast, Gather Light, Genesis, Glow, Guiding Star, Hidden Cache, Knockout Blow, Meteor Shower, Neutron Aegis, Particle Wall, Quasar, Radiate, Reflect, Resonance, Royal Gamble, Seven Stars, Shining Strike, Solar Strike, The Sealed Throne, The Smith, Venerate |
| Regent | strength | 3 | Arsenal, Monologue, Resonance |
| Silent | attack_play | 4 | Envenom, Finisher, Shadow Step, Tracking |
| Silent | block_payoff | 3 | Blur, Mirage, Shadowmeld |
| Silent | create | 10 | Blade Dance, Blade of Ink, Cloak and Dagger, Fan of Knives, Hidden Daggers, Infinite Blades, Leading Strike, Nightmare, Storm of Steel, Up My Sleeve |
| Silent | debuff | 9 | Assassinate, Expose, Leg Sweep, Malaise, Neutralize, Scare, Sucker Punch, Suppress, Tracking |
| Silent | dexterity | 4 | Abrasive, Anticipate, Footwork, Wraith Form |
| Silent | discard | 20 | Abrasive, Acrobatics, Calculated Gamble, Dagger Throw, Flick-Flack, Hand Trick, Haze, Hidden Daggers, Master Planner, Memento Mori, Prepared, Reflex, Ricochet, Shadow Step, Sneaky, Storm of Steel, Survivor, Tactician, Tools of the Trade, Untouchable |
| Silent | draw | 13 | Acrobatics, Adrenaline, Backflip, Corrosive Wave, Dagger Throw, Escape Plan, Expertise, Murder, Predator, Prepared, Reflex, Speedster, Tools of the Trade |
| Silent | poison | 12 | Accelerant, Bouncing Flask, Bubble Bubble, Corrosive Wave, Deadly Poison, Envenom, Haze, Mirage, Noxious Fumes, Outbreak, Poisoned Stab, Snakebite |
| Silent | shiv | 12 | Accuracy, Blade Dance, Blade of Ink, Cloak and Dagger, Fan of Knives, Hidden Daggers, Infinite Blades, Knife Trap, Leading Strike, Phantom Blades, Storm of Steel, Up My Sleeve |
| Silent | skill_play | 7 | Burst, Escape Plan, Flechettes, Hand Trick, Master Planner, Pinpoint, Pounce |

Cards whose archetypes differ between the two sides of a window:

| Window | Card | Before | After | Source of the earlier text |
|---|---|---|---|---|
| first | Arsenal | strength | create strength | patch notes v0.101.0, old text quoted |
| first | Blade of Ink | attack_play | create shiv | patch notes v0.102.0, old text quoted |
| first | Borrowed Time | doom | (none) | patch notes v0.102.0, old text quoted |
| first | Spoils of Battle | forge | draw forge | patch notes v0.100.0/v0.101.0: draw added in v0.101.0 |
| second | Conflagration | attack_play | (none) | patch notes v0.104.0, old text quoted |
| second | Scare | (not in the game) | debuff | cards.json |

**Changes and direction (step 2).** Every event of a member in the window, from
`change_events.csv`, with the patch notes' verbs from `patch_notes_cards.csv` for the same card
and version (`p_changes.csv`, with the field changes and note text).
- A card's direction: **buff** if every balance note on it in the window says Buffed, **nerf**
  if every one says Nerfed, **unclear** if the verbs are mixed or are Changed or Reworked, or
  the change has no balance note. **No balance change** for wording, art and bug-fix behavior
  events, and for a beta change reverted before stable (Capture Spirit).
- For an archetype, a card whose text enters it (or that is added to the game) counts as a
  buff, and one whose text leaves it counts as a nerf, whatever its verb: that is support
  gained or lost. The last column drops this and uses verbs only.
- Net direction of an archetype in a window: buff if more members count as buffs than nerfs,
  nerf if the reverse, unclear if tied with any substantive change, none otherwise.
- Many nets rest on one changed card. That is the rule as written; it makes the exposure
  coarse, not graded.

| Window | Character | Archetype | Changed members (how each counts) | Buff / nerf / unclear | Net | Net, verbs only |
|---|---|---|---|---|---|---|
| first | Defect | create | Rocket Punch (buff), Trash to Treasure (no balance change) | 1 / 0 / 0 | buff | buff |
| first | Defect | draw | Iteration (no balance change), Rocket Punch (buff) | 1 / 0 / 0 | buff | buff |
| first | Defect | focus | Hotfix (nerf) | 0 / 1 / 0 | nerf | nerf |
| first | Defect | lightning | Voltaic (nerf) | 0 / 1 / 0 | nerf | nerf |
| first | Defect | orb | Trash to Treasure (no balance change), Voltaic (nerf) | 0 / 1 / 0 | nerf | nerf |
| first | Defect | status | Flak Cannon (no balance change), Iteration (no balance change), Rocket Punch (buff), Trash to Treasure (no balance change) | 1 / 0 / 0 | buff | buff |
| first | Ironclad | attack_play | Expect a Fight (unclear) | 0 / 0 / 1 | unclear | unclear |
| first | Ironclad | create | Stoke (unclear) | 0 / 0 / 1 | unclear | unclear |
| first | Ironclad | debuff | Break (buff), Colossus (unclear), Dominate (unclear), Tremble (unclear) | 1 / 0 / 3 | buff | buff |
| first | Ironclad | exhaust | Cinder (buff), Forgotten Ritual (nerf), Howl from Beyond (no balance change), Stoke (unclear) | 1 / 1 / 1 | unclear | unclear |
| first | Ironclad | hp_loss | Hemokinesis (buff), Spite (unclear), Tear Asunder (no balance change) | 1 / 0 / 1 | buff | buff |
| first | Ironclad | strength | Dominate (unclear), Fight Me! (buff) | 1 / 0 / 1 | buff | buff |
| first | Necrobinder | create | Capture Spirit (no balance change), Dirge (nerf), Grave Warden (unclear), Seance (nerf) | 0 / 2 / 1 | nerf | nerf |
| first | Necrobinder | debuff | Debilitate (buff), Defy (unclear) | 1 / 0 / 1 | buff | buff |
| first | Necrobinder | doom | Borrowed Time (nerf; left) | 0 / 1 / 0 | nerf | unclear |
| first | Necrobinder | ethereal | Banshee's Cry (nerf), Defy (unclear), Sculpting Strike (buff), Seance (nerf) | 1 / 2 / 1 | nerf | nerf |
| first | Necrobinder | osty | Dirge (nerf) | 0 / 1 / 0 | nerf | nerf |
| first | Necrobinder | soul | Capture Spirit (no balance change), Dirge (nerf), Grave Warden (unclear), Seance (nerf) | 0 / 2 / 1 | nerf | nerf |
| first | Regent | create | Arsenal (buff; entered), BEGONE! (unclear), Bundle of Joy (buff), CHARGE!! (unclear), Collision Course (buff), Heirloom Hammer (buff) | 4 / 0 / 2 | buff | buff |
| first | Regent | debuff | Falling Star (buff) | 1 / 0 / 0 | buff | buff |
| first | Regent | draw | Glow (unclear), Guiding Star (buff), Kingly Kick (buff), Kingly Punch (buff), Spoils of Battle (buff; entered) | 4 / 0 / 1 | buff | buff |
| first | Regent | forge | Parry (buff), Refine Blade (buff), Spoils of Battle (unclear), Sword Sage (buff), Wrought in War (buff) | 4 / 0 / 1 | buff | buff |
| first | Regent | star | Alignment (nerf), Falling Star (buff), Gather Light (buff), Glow (unclear), Guiding Star (buff), Reflect (no balance change), Solar Strike (buff) | 4 / 1 / 1 | buff | buff |
| first | Regent | strength | Arsenal (unclear) | 0 / 0 / 1 | unclear | unclear |
| first | Silent | attack_play | Blade of Ink (nerf; left) | 0 / 1 / 0 | nerf | unclear |
| first | Silent | create | Blade of Ink (buff; entered), Leading Strike (buff) | 2 / 0 / 0 | buff | buff |
| first | Silent | dexterity | Anticipate (nerf) | 0 / 1 / 0 | nerf | nerf |
| first | Silent | discard | Acrobatics (unclear), Flick-Flack (nerf), Memento Mori (buff), Prepared (unclear), Untouchable (nerf) | 1 / 2 / 2 | nerf | nerf |
| first | Silent | draw | Acrobatics (unclear), Corrosive Wave (nerf), Prepared (unclear), Speedster (unclear) | 0 / 1 / 3 | nerf | nerf |
| first | Silent | poison | Corrosive Wave (nerf) | 0 / 1 / 0 | nerf | nerf |
| first | Silent | shiv | Blade of Ink (buff; entered), Leading Strike (buff) | 2 / 0 / 0 | buff | buff |
| first | Silent | skill_play | Pinpoint (nerf) | 0 / 1 / 0 | nerf | nerf |
| second | Defect | draw | Reboot (no balance change), Scrape (no balance change) | 0 / 0 / 0 | none | none |
| second | Defect | focus | Hyperbeam (buff) | 1 / 0 / 0 | buff | buff |
| second | Defect | lightning | Tesla Coil (buff) | 1 / 0 / 0 | buff | buff |
| second | Defect | orb | Fusion (unclear), Shatter (unclear) | 0 / 0 / 2 | unclear | unclear |
| second | Defect | power_play | Synthesis (buff) | 1 / 0 / 0 | buff | buff |
| second | Defect | zero_cost | Scrape (no balance change) | 0 / 0 / 0 | none | none |
| second | Ironclad | attack_play | Conflagration (nerf; left), Unrelenting (buff) | 1 / 1 / 0 | unclear | buff |
| second | Ironclad | block_payoff | Juggernaut (buff) | 1 / 0 / 0 | buff | buff |
| second | Ironclad | draw | Drum of Battle (unclear) | 0 / 0 / 1 | unclear | unclear |
| second | Ironclad | exhaust | Drum of Battle (unclear), Howl from Beyond (buff), Pact's End (unclear) | 1 / 0 / 2 | buff | buff |
| second | Necrobinder | attack_play | Reaper Form (no balance change) | 0 / 0 / 0 | none | none |
| second | Necrobinder | create | Reave (no balance change) | 0 / 0 / 0 | none | none |
| second | Necrobinder | debuff | Debilitate (nerf) | 0 / 1 / 0 | nerf | nerf |
| second | Necrobinder | doom | Reaper Form (no balance change) | 0 / 0 / 0 | none | none |
| second | Necrobinder | draw | Death March (buff) | 1 / 0 / 0 | buff | buff |
| second | Necrobinder | ethereal | Enfeebling Touch (no balance change) | 0 / 0 / 0 | none | none |
| second | Necrobinder | osty | Sic 'Em (buff) | 1 / 0 / 0 | buff | buff |
| second | Necrobinder | soul | Reave (no balance change) | 0 / 0 / 0 | none | none |
| second | Regent | create | Arsenal (no balance change), Pillar of Creation (no balance change), Supermassive (no balance change) | 0 / 0 / 0 | none | none |
| second | Regent | draw | Tyranny (unclear) | 0 / 0 / 1 | unclear | unclear |
| second | Regent | forge | Bulwark (nerf), Furnace (buff), Parry (unclear), Summon Forth (unclear), Sword Sage (unclear) | 1 / 1 / 3 | unclear | unclear |
| second | Regent | star | Astral Pulse (unclear), Crescent Spear (buff), Reflect (nerf), Seven Stars (no balance change), The Sealed Throne (unclear) | 1 / 1 / 2 | unclear | unclear |
| second | Regent | strength | Arsenal (no balance change) | 0 / 0 / 0 | none | none |
| second | Silent | create | Blade of Ink (nerf), Hidden Daggers (no balance change), Nightmare (unclear) | 0 / 1 / 1 | nerf | nerf |
| second | Silent | debuff | Scare (buff; entered) | 1 / 0 / 0 | buff | unclear |
| second | Silent | discard | Hidden Daggers (no balance change), Tools of the Trade (no balance change), Untouchable (buff) | 1 / 0 / 0 | buff | buff |
| second | Silent | draw | Predator (unclear), Tools of the Trade (no balance change) | 0 / 0 / 1 | unclear | unclear |
| second | Silent | shiv | Blade of Ink (nerf), Hidden Daggers (no balance change) | 0 / 1 / 0 | nerf | nerf |
| second | Silent | skill_play | Pounce (buff) | 1 / 0 / 0 | buff | buff |

Grapple (removed in the first window) has no color or text on file and is in no archetype.
Defect has no pairs in `placebo_h3` for the first window (no tweak there, section M), so its
first-window rows above are not tested.

**The test (step 3), as declared by Phil, with my definitions.**
- Pairs: all-offers placebo pairs of Defect, Ironclad, Necrobinder and Silent, as in the
  discovery. One pair per card and window.
- Each pair gets a predicted sign d from its archetypes' net directions in its window: +1 if
  at least one is a net buff and none a net nerf, −1 for the reverse, 0 (other) if neither.
  A pair with both is **conflicted** and is left out of both groups, and counted.
- Statistic: the mean over exposed pairs of d × (z − the mean z of the other pairs of the same
  character-window). Positive means shifted as predicted. Also reported: mean z by group and
  sign counts.
- Permutation: d shuffled across pairs within each character-window, 10,000 times. Per
  character and pooled over the four.
- **Rule, as given: a pooled shift in the predicted direction with p < 0.05 = replicates;
  otherwise not replicated.** The p that decides is two-sided; the one-sided p is reported
  too. If they fall on different sides of 0.05 I say so and call it not replicated.
- Sensitivities, named now: verbs only (no entry or exit); O's top-25 pairs left out;
  upgraded-offers pairs included. None of them decides.

**Budget (step 4).** All 463 pairs and all five characters, as the factors are computed.
Robust sd of z by patch, next to 4.10 / 2.67:
- with exposed pairs removed. Exposed, primary: in an archetype with any substantive change to
  a member in the window (net buff, nerf or unclear). Secondary: net buff or nerf only.
- with an archetype × window term absorbed: z regressed on one indicator per character-window
  and archetype (a card in several gets several) plus a character-window intercept, by least
  squares; robust sd of the residuals.
- Both lose pairs or degrees of freedom, which moves a robust sd by itself. So each is set
  next to the same computation with the pairs' archetype sets shuffled within character-window
  (1,000 times; mean and 95% range). Only a fall below that range counts as explained spread.

**Regent check (step 5).** Regent all-offers pairs split by `create` under each window's own
text and under the v0.107.1 text for both windows; cards whose class differs are listed.
Phil's own list of cards isn't on file, so the comparison is with his counts (7 of 7, 9 of 10).

### Results

Everything below was computed after the text above was written.

### Answer

**Under the declared rule the pattern replicates: pooled over the four test characters, pairs
in net-buffed archetypes sit above, and pairs in net-nerfed archetypes below, their
character's other placebo cards (shift +1.64 in z, two-sided p 0.001).** [computed]

**I don't think that shows what the rule was meant to show.** The shift comes from Ironclad
and Silent in the first window, and most of it from two archetypes whose direction I had
already seen in section O. Defect goes the other way, Necrobinder shows nothing, and the
second window shows nothing pooled. Counted by archetype, not by card, 17 of 29 go as
predicted. What the data do show is weaker and more general: **cards of one archetype move
together across a release, whether or not the archetype's members were buffed or nerfed.**
In the first patch that co-movement is a real part of the placebo spread. The factors stay as
they are. [inferred]

### Checks and changes after the rules [computed]

- `--check`: the rules pass their known-answer cases, the statistic recovers a planted shift,
  and the permutation test rejects a true null 4.5% of the time at 0.05.
- `placebo_h3` gives 463 pairs and first-patch robust sd 4.10; the script stops otherwise.
- **The Regent rule reproduces the discovery exactly**: 7 of 7 and 9 of 10 (step 5). So the
  `create` rule is at least the split Phil made.
- **Rules changed while building the tables, before any z.** `zero_cost` first matched any
  "costs 0" or "free to play" text and was narrowed to cards that name 0-cost cards as a
  group. `block_payoff` matched Expose ("Block from the enemy") and was narrowed. An event
  with no balance note first counted as unclear and now adds no verb (this made Rocket Punch a
  buff, as its note says). Cut or unknown earlier text first made Rocket Punch look as if it
  entered `zero_cost`; such text now keeps the later memberships. All four were found by
  reading the member and change tables.
- 5 of the 292 all-offers pairs are conflicted and left out: Hidden Daggers (both windows),
  Storm of Steel, High Five (both windows).
- **Part 6 is post hoc, added after reading the test:** archetypes as the unit.
- A fix after the first run of part 3, which stopped on a column type before printing
  anything: the flag for O's pairs. It also drops a flagged card's upgraded-offers pair.

### 3. The declared test [computed]

Tables: `p_test.csv`, `p_test_pairs.csv`. 287 pairs in the test: 59 in net-buffed archetypes,
70 in net-nerfed, 158 other. "Shift as predicted" is the declared statistic, in z; positive
means buffed archetypes up and nerfed archetypes down, against the same character-window's
other pairs. "Sign as predicted" counts exposed pairs with z on the predicted side of 0.

| Scope | Pairs: buff / nerf / other | Mean z: buff / nerf / other | Shift as predicted | Sign as predicted | Share z > 0: buff / nerf / other | p, two-sided | p, one-sided |
|---|---|---|---|---|---|---|---|
| Defect | 9 / 0 / 35 | -1.33 /  / +0.88 | **-2.21** | 1 of 9 | 0.11 /  / 0.54 | 0.045 | 0.980 |
| Ironclad | 19 / 0 / 50 | +3.11 /  / -0.79 | **+3.85** | 14 of 19 | 0.74 /  / 0.40 | < 0.001 | < 0.001 |
| Necrobinder | 14 / 36 / 45 | -0.20 / +0.20 / +0.46 | **-0.29** | 21 of 50 | 0.36 / 0.56 / 0.56 | 0.732 | 0.638 |
| Silent | 17 / 34 / 28 | +1.45 / -2.30 / +1.16 | **+3.38** | 37 of 51 | 0.65 / 0.24 / 0.57 | < 0.001 | < 0.001 |
| Pooled | 59 / 70 / 158 | +1.17 / -1.01 / +0.28 | **+1.64** | 73 of 129 | 0.53 / 0.40 / 0.51 | 0.001 | < 0.001 |

By character-window:

| Scope | Pairs: buff / nerf / other | Mean z: buff / nerf / other | Shift as predicted | Sign as predicted | Share z > 0: buff / nerf / other | p, two-sided | p, one-sided |
|---|---|---|---|---|---|---|---|
| Defect second | 9 / 0 / 35 | -1.33 /  / +0.88 | **-2.21** | 1 of 9 | 0.11 /  / 0.54 | 0.045 | 0.980 |
| Ironclad first | 9 / 0 / 26 | +3.32 /  / -1.23 | **+4.55** | 7 of 9 | 0.78 /  / 0.35 | 0.013 | 0.008 |
| Ironclad second | 10 / 0 / 24 | +2.91 /  / -0.32 | **+3.23** | 7 of 10 | 0.70 /  / 0.46 | 0.007 | 0.004 |
| Necrobinder first | 1 / 31 / 11 | +5.32 / -0.19 / +0.01 | **+0.36** | 15 of 32 | 1.00 / 0.55 / 0.55 | 0.775 | 0.398 |
| Necrobinder second | 13 / 5 / 34 | -0.62 / +2.65 / +0.60 | **-1.45** | 6 of 18 | 0.31 / 0.60 / 0.56 | 0.030 | 0.986 |
| Silent first | 8 / 32 / 20 | +1.46 / -2.44 / +2.37 | **+3.66** | 30 of 40 | 0.62 / 0.22 / 0.70 | < 0.001 | < 0.001 |
| Silent second | 9 / 2 / 8 | +1.43 / -0.05 / -1.85 | **+2.36** | 7 of 11 | 0.67 / 0.50 / 0.25 | 0.023 | 0.013 |
| Pooled first | 18 / 63 / 57 | +2.60 / -1.33 / +0.27 | **+2.46** | 52 of 81 | 0.72 / 0.38 / 0.51 | < 0.001 | < 0.001 |
| Pooled second | 41 / 7 / 101 | +0.54 / +1.88 / +0.29 | **+0.25** | 21 of 48 | 0.44 / 0.57 / 0.50 | 0.611 | 0.300 |

Pooled, under each version:

| Version | Exposed pairs | Shift as predicted | Sign as predicted | p, two-sided | p, one-sided | First / second shift |
|---|---|---|---|---|---|---|
| Declared | 129 | +1.64 | 73 of 129 | 0.001 | < 0.001 | +2.46 / +0.25 |
| Patch-note verbs only | 120 | +1.52 | 69 of 120 | < 0.001 | < 0.001 | +2.86 / -0.35 |
| Pairs shown in section o's top 25 left out | 115 | +0.99 | 64 of 115 | 0.011 | 0.006 | +1.63 / +0.07 |
| Upgraded-offers pairs included | 150 | +1.62 | 88 of 150 | < 0.001 | < 0.001 | +2.41 / +0.35 |

Reading. [inferred]
- **Rule: replicates.** The pooled two-sided p is 0.001 and the one-sided p is below it, so
  the two don't disagree. It also passes with O's pairs left out (+0.99, p 0.011).
- **It is two characters, and one window.** Ironclad (+3.85) and Silent (+3.38) carry it.
  Defect is −2.21, the wrong way, with 1 of 9 pairs as predicted. Necrobinder is −0.29.
  Pooled, the first window gives +2.46 and the second +0.25 (p 0.61).
- **Sign counts are weak.** 73 of 129 exposed pairs have z on the predicted side (57%). Pairs
  in buffed archetypes are positive 52% of the time, against 51% of other pairs; the
  difference is on the nerf side (40% positive). The shift is in sizes more than in signs.
- **Entry and exit add little.** With verbs only the pooled shift is +1.52. Ironclad's second
  window does depend on it (+3.23 with, +0.96 without): Conflagration leaving `attack_play`
  cancels Unrelenting's buff there.
- **The p is too small, for a reason I should have declared.** Shuffling labels across cards
  treats cards as exchangeable. If cards of an archetype move together for any reason, the
  number of independent units is nearer the 29 archetype-windows than the 129 pairs. The post
  hoc table below is the check on that.

### Archetypes as the unit, post hoc [computed]

Tables: `p_posthoc_archetypes.csv`, `p_posthoc_summary.csv`. One row per character-window and
archetype with at least 2 all-offers pairs: its pairs' mean z minus the mean z of the
character-window's other pairs. Test characters, archetypes with a net direction, largest
first:

| Character | Window | Archetype | Net | Pairs | Mean z | Rest of the character-window | Difference | z > 0 | As predicted |
|---|---|---|---|---|---|---|---|---|---|
| Ironclad | first | hp_loss | buff | 6 | +6.34 | -1.38 | +7.72 | 6 of 6 | yes |
| Silent | first | discard | nerf | 13 | -5.91 | +1.15 | -7.06 | 1 of 13 | yes |
| Necrobinder | first | soul | nerf | 3 | -6.04 | +0.48 | -6.52 | 0 of 3 | yes |
| Ironclad | first | strength | buff | 2 | -4.62 | +0.22 | -4.84 | 1 of 2 | no |
| Necrobinder | first | debuff | buff | 2 | +3.65 | -0.14 | +3.78 | 2 of 2 | yes |
| Defect | second | focus | buff | 2 | -3.06 | +0.59 | -3.65 | 0 of 2 | no |
| Ironclad | second | exhaust | buff | 9 | +3.28 | -0.32 | +3.60 | 7 of 9 | yes |
| Silent | first | dexterity | nerf | 2 | +3.10 | -0.45 | +3.55 | 1 of 2 | no |
| Silent | first | draw | nerf | 9 | -2.52 | +0.04 | -2.56 | 2 of 9 | yes |
| Necrobinder | first | ethereal | nerf | 8 | +2.04 | -0.41 | +2.45 | 6 of 8 | no |
| Silent | second | skill_play | buff | 3 | +1.96 | -0.47 | +2.43 | 3 of 3 | yes |
| Silent | second | debuff | buff | 2 | +1.82 | -0.32 | +2.14 | 1 of 2 | yes |
| Necrobinder | second | debuff | nerf | 6 | +2.21 | +0.26 | +1.95 | 4 of 6 | no |
| Silent | first | shiv | buff | 9 | +1.29 | -0.61 | +1.90 | 6 of 9 | yes |
| Ironclad | first | debuff | buff | 2 | +1.65 | -0.16 | +1.81 | 1 of 2 | yes |
| Silent | first | poison | nerf | 10 | -1.85 | -0.04 | -1.80 | 2 of 10 | yes |
| Necrobinder | first | create | nerf | 4 | -1.44 | +0.18 | -1.62 | 1 of 4 | yes |
| Defect | second | lightning | buff | 6 | -0.86 | +0.63 | -1.49 | 1 of 6 | no |
| Silent | first | skill_play | nerf | 6 | -1.54 | -0.21 | -1.33 | 2 of 6 | yes |
| Necrobinder | second | osty | buff | 11 | -0.54 | +0.75 | -1.29 | 4 of 11 | no |
| Defect | second | power_play | buff | 2 | -0.79 | +0.49 | -1.27 | 0 of 2 | no |
| Necrobinder | second | draw | buff | 3 | -0.71 | +0.56 | -1.26 | 1 of 3 | no |
| Necrobinder | first | osty | nerf | 10 | -0.88 | +0.30 | -1.18 | 4 of 10 | yes |
| Silent | first | attack_play | nerf | 4 | -1.23 | -0.27 | -0.95 | 1 of 4 | yes |
| Silent | second | discard | buff | 6 | +0.54 | -0.38 | +0.92 | 3 of 6 | yes |
| Necrobinder | first | doom | nerf | 9 | +0.46 | -0.08 | +0.54 | 7 of 9 | no |
| Silent | second | create | nerf | 2 | -0.49 | -0.06 | -0.42 | 0 of 2 | yes |
| Silent | first | create | buff | 7 | -0.46 | -0.32 | -0.14 | 3 of 7 | no |
| Silent | second | shiv | nerf | 3 | -0.09 | -0.11 | +0.01 | 1 of 3 | no |

- 17 of 29 as predicted (sign test p 0.46). Mean signed difference +0.87; flipping each
  archetype's sign at random gives p 0.14.
- Two rows hold 14.8 of the summed signed difference of 25.3: Silent `discard` in the first
  window (13 pairs, 1 positive) and Ironclad `hp_loss` in the first window (6 pairs, all
  positive). Those are the two archetypes I had seen in O. The other 27 average +0.39, with
  15 as predicted.
- Archetypes with no net direction sit almost as far from their character's other cards:
  mean |difference| 1.51 over 28, against 2.42 for the 29 with one. The largest of them, all
  five characters:

| Character | Window | Archetype | Net | Pairs | Mean z | Difference | z > 0 |
|---|---|---|---|---|---|---|---|
| Regent | second | create | none | 10 | +4.99 | +6.02 | 9 of 10 |
| Defect | second | status | none | 10 | +4.00 | +4.62 | 9 of 10 |
| Regent | first | strength | unclear | 2 | -4.45 | -4.50 | 0 of 2 |
| Ironclad | first | attack_play | unclear | 8 | -2.82 | -3.57 | 1 of 8 |
| Regent | second | forge | unclear | 7 | -2.89 | -3.39 | 1 of 7 |
| Silent | first | block_payoff | none | 3 | +2.88 | +3.38 | 2 of 3 |
| Defect | second | create | none | 9 | +3.08 | +3.34 | 7 of 9 |
| Silent | first | debuff | none | 6 | +2.32 | +2.93 | 5 of 6 |

Reading. [inferred]
- **At the archetype level the direction is not predicted beyond chance.** That is post hoc
  and has little power at 29 units, so it doesn't overturn the declared result; it says the
  declared p overstates it.
- **Archetypes cluster with or without a change.** Defect's `status` cards are +4.0 in the
  second window (9 of 10 positive) with no balance change to any member. Regent's `create`
  cards are +5.0 in the second window with only bug fixes to members.
- Silent's first window is the one place where the story fits in detail: `discard`, `draw`,
  `poison`, `skill_play` and `attack_play` were net-nerfed and are all below the rest; `shiv`
  was buffed and is above.

### 4. Budget [computed]

Table: `p_budget.csv`. All 463 pairs, five characters. Robust sd of z. "Sets shuffled" is the
same computation with the pairs' archetype sets dealt to other pairs of the same
character-window, 1,000 times: what removing that many pairs, or fitting that many terms,
does by itself.

| Exposure | Patch | Factor | Pairs exposed | Exposed removed | Same, sets shuffled [95%] | Archetype × window absorbed (terms) | Same, sets shuffled [95%] |
|---|---|---|---|---|---|---|---|
| Any substantive change to a member | first | 4.10 | 155 of 217 | **3.97** | 4.05 [3.18, 5.02] | **2.88** (46) | 3.84 [3.44, 4.24] |
| Any substantive change to a member | second | 2.67 | 122 of 246 | **3.17** | 2.71 [2.28, 3.16] | **2.55** (46) | 2.58 [2.33, 2.84] |
| Net buff or nerf only | first | 4.10 | 140 of 217 | **4.02** | 4.25 [3.47, 5.02] | **3.11** (35) | 3.93 [3.59, 4.30] |
| Net buff or nerf only | second | 2.67 | 60 of 246 | **2.85** | 2.72 [2.45, 2.98] | **2.63** (35) | 2.60 [2.38, 2.82] |

Plain sd, first patch: 4.46 before, 3.22 with the terms absorbed (primary exposure).

Reading. [inferred]
- **Removing exposed pairs changes nothing.** 3.97 against 4.10, and 3.17 against 2.67, both
  inside or at the edge of what removing random pairs gives. Cards outside every changed
  archetype miss as widely as cards inside one. Most first-patch pairs are exposed (155 of
  217), so this removal is also coarse.
- **Absorbing archetype × window terms takes the first patch from 4.10 to 2.88**, below the
  shuffled range (3.44–4.24). In variance, that is about 0.41 of the excess over 1 beyond
  what the same number of arbitrary terms absorbs ((3.84² − 2.88²) / (4.10² − 1)). **In the
  second patch it absorbs nothing** (2.55 against 2.58).
- So in the first patch, part of the spread is shared within archetypes. This fits M's and
  N's leftover: a step at the release that isn't within-build drift and that card-by-card
  exposure to changed cards didn't order. It does not say the changed cards caused it: the
  terms absorb an archetype's mean whatever its sign, and the sign test above is at chance.
- The terms were chosen by me from card text. Another grouping of the same cards would
  absorb a different amount; the shuffled benchmark guards against the number of terms, not
  against the choice of grouping.

### 5. Regent check [computed]

Tables: `p_regent.csv`, `p_regent_split.csv`. Regent all-offers pairs, `create` against the
rest.

| Window | Text used | Create pairs | z > 0 | Mean z | Other pairs | z > 0 | Mean z |
|---|---|---|---|---|---|---|---|
| first | the window's own | 7 | 7 | +6.50 | 49 | 17 (35%) | −1.06 |
| first | v0.107.1 | 7 | 7 | +6.50 | 49 | 17 (35%) | −1.06 |
| second | the window's own | 10 | 9 | +4.99 | 45 | 15 (33%) | −1.03 |
| second | v0.107.1 | 10 | 9 | +4.99 | 45 | 15 (33%) | −1.03 |

- **No card's classification changes.** The only Regent card whose `create` membership
  differs by window is Arsenal (not a member before v0.103.2), and it is a changed card in
  the first window, so it was never a placebo pair there.
- First window pairs: Manifest Authority, Crash Landing, Pillar of Creation, Quasar, Spectrum
  Shift, Guards, Supermassive. Second: those minus Manifest Authority, Spectrum Shift and
  Supermassive, plus Charge, Heirloom Hammer (the one negative), Arsenal, Begone, Bundle of
  Joy and Collision Course.
- **The second window's result has no change behind it under my rule.** `create`'s members
  had only bug fixes there (the Largesse fix to Arsenal, Pillar of Creation and Supermassive),
  so its net direction is none. Four cards are in both windows and positive in both. So
  Regent's second window reads as the same cards still rising, not as a response to that
  window's changes. Most Regent `create` cards make Colorless cards, and Colorless changes
  are outside this section. [inferred]
- Regent's other buffed archetypes in the first window don't all follow: `forge` +2.1 and
  `debuff` +3.3 above the rest, `draw` +0.2, and `star` (25 pairs, 4 buffs and 1 nerf among
  members) −3.6.

### What this does and doesn't settle

- **Settled, within limits:** under the rule as given, the pooled test passes. The Regent
  split is reproduced and doesn't depend on which build's text is used.
- **Fits but not shown:** that changes to an archetype's members move its unchanged members
  in the same direction. Silent's first window fits it well, Ironclad's `hp_loss` fits it,
  Defect and Necrobinder don't, and by archetype the direction is at chance.
- **Shown, post hoc:** placebo z clusters by archetype in the first patch, enough to take the
  robust sd from 4.10 to 2.88. Not in the second patch.
- **Not settled:** why archetypes move together when none of their cards changed (Defect
  `status`, Regent `create` in the second window). Changes outside a character's cards and
  players following a strategy as a whole both remain. A grouping from the data (which cards
  are picked into the same decks) would test the clustering without my reading of the text.
- The factors are unaffected: they measure the spread and don't depend on its cause.

---

## Q. The release nudge — EXPLORATORY

**EXPLORATORY.** Proposed by Phil after sections O and P were seen. Nothing in this section
changes the calibration factors, the numbers module, the guide or any headline result. Script:
`triage/scripts/q_nudge.py`; tables in `triage/out_final/q_*.csv`. Inputs: the final tables
(`data/runs/runs.duckdb`, read-only), `data/analysis/placebo_h3.parquet` (weeks 0–3, 463 pairs,
one row per (window, pseudo card)) and the reference tables. Colors are derived (`db.py`);
`reference/raw/` stays closed. No figures: tables for plotting are listed at the end.

**The hypothesis under test (Phil's working story, not a result).** Each new build gives every
card a fresh random offset in pick rate, unrelated to balance changes. If so, a DiD across a
build boundary carries extra variance 2σ_b² that the clustered SE doesn't include, and a DiD
inside one build doesn't.

### Rules and what each outcome means, written before running

Written 2026-11-11, before any number of this section was computed. What I had looked at:
sections C, I, N, O and P and their tables; offers, runs and first and last dates per build;
the number of cards `window_changes` reports across each pair of consecutive stable builds
(0, 0, 0, 88, 0, 50); the column names of the saved files and change tables. No fit, no z and
no offer-rate statistic was run. `.git` is not writable in this session (`git fetch` failed
with "cannot open .git/FETCH_HEAD: Operation not permitted"), so no commit timestamps this
order; the claim rests on this note and on the order of the section. The work is based on the
local `main` (41787cf), which equals `origin/main` as last fetched.

**Disclosure.** The rules marked (Phil) came from Phil's prompt, written before any Q number
existed. While part 3 was running, after parts 1 and 2 were done, Phil ran
`triage/scripts/q_z_vs_offers.py`, a quick look with no intervals: τ = 3.35 / 2.47 pp, median
SE 0.82 / 0.95 pp, and the width of z rising with offers in both patches except the second
patch's top offer bin (about 35k offers); it changed no rule and no computation here.

Rules marked **(Phil)** are as given. Everything marked **(mine)** is a choice the prompt left
open, made here.

**Two facts already on file that the hypothesis must live with** (mine, noted before running):
- C found the z of the same pseudo card in the two patches correlated at +0.45. The two real
  windows share no build, so independent offsets per build predict 0 there. A pure nudge
  can't be the whole story even if every test below goes its way.
- I found fake and real second-patch effects correlated at −0.66. Those two differences share
  the v0.103.3 block with opposite signs, and independent offsets of equal size predict −0.5
  before noise. That one fits.

#### Part 1. One nudge size, two patches?

Data: the 463 pairs. β in pp; SE the saved clustered SE (for a pair shared by several tweaks,
the mean over them, as `placebo_pairs` saves it).

- Model, per patch: β_i ~ Normal(μ, SE_i² + τ²). μ and τ by maximum likelihood, per patch and
  pooled (one τ, a μ per patch). 95% interval on τ from 2,000 resamples of pseudo cards; in the
  pooled fit a card in both patches stays together. Median SE per patch is reported.
- Prediction: with the pooled τ, simulate z_i = β_i / SE_i from each pair's own SE, 5,000
  draws, and take the 95% range of the robust sd (1.4826 × MAD) of z per patch.
- **Rule (Phil): the two per-patch τ intervals overlap AND each patch's observed robust sd
  (4.10, 2.67) falls inside the pooled-τ prediction's range = "one nudge size fits both; the
  factors differ because the patches' SEs differ." Otherwise = "the patches differ in nudge
  size."**
- Secondary (Phil): the same on the log-odds scale (`to_log_odds` with the pseudo card's rate
  before). Both reported; pp decides.
- The normal model is an approximation (Phil): O found tails a little heavier than a normal's.
  The robust-sd comparison is the check on it.
- Mine:
  - "Overlap" means the two 95% intervals share at least one value. That is a lenient test of
    equality, so the interval of τ_first − τ_second (cards resampled jointly) is reported
    next to it. It doesn't decide.
  - The simulation draws β_i ~ Normal(μ_patch, SE_i² + τ²) with the pooled fit's μ, and
    holds τ at its point estimate, as the rule says. The same range with τ drawn from its
    bootstrap is reported as a wider secondary range.
  - The observed robust sd is recomputed from the saved z and must give 4.10 and 2.67 (2.68 in
    O's table is the same number to one more rounding); the script stops otherwise.
  - τ is one number per patch, over all five characters and both kinds of fit (403 all-offers
    pairs, 60 upgraded-offers pairs). τ on the all-offers pairs alone is reported beside it.
  - If the hypothesis holds, σ_b = τ / √2.

#### Part 2. Negative-control outcome: offer rate

The game's RNG sets offers, so an unchanged card's share of offers should move only by chance.

- Data: the 43 windows, `load_window` as in the main analysis, after block cut to weeks 0–3.
  `offer_rate_check` per window; control rows kept; one row per (window, card) as
  `placebo_pairs` dedupes. Statistic: `z_binom_rarity`. Per patch: robust sd, plain sd, share
  |z| > 2, n.
- **Rules (Phil): robust sd ≤ 1.2 = the window construction gives honest z on a pure-chance
  quantity, so the pick-rate excess is behavior and not the data pipeline. Robust sd ≥ 1.5 =
  offer rate is inflated too; then report it per rarity, per window, and for windows whose
  card pool changed against those where it didn't. Between 1.2 and 1.5 = mixed.**
- **Limit (Phil): `z_binom` uses a binomial SE, which treats offers as independent. So this
  tests the windows and the data, not the clustering.**
- Secondary (Phil): a run-clustered bootstrap SE of the log share ratio, 200 draws, and the
  robust sd of z with that SE. Timed first; skipped with a note if over 1 h.
- Mine:
  - The rule is applied per patch. If the patches land in different bands, I report each and
    call the part mixed.
  - Dedupe key: color, before builds, after builds, card. Tweaks sharing a window differ only
    in which treated card is left out, so their z for one control card are near duplicates and
    are averaged. `fit_on` is not in the key: offer rate is computed on all offers whichever
    offers the tweak's DiD used.
  - Rows without a finite z (no offers in a block) are dropped and counted.
  - **Rarity is derived, not read.** `offer_rate_check` takes rarity from
    `reference/raw/cards.json`. Here it comes from `card_changes.csv` and
    `offer_rate.parquet` where they have the card, else from offer tiers as in N (95 of 97 on
    file matched there). A card in the wrong tier is measured against the wrong median, which
    can only add spread. With `TRIAGE_COLORS=reference` the file's rarities are used.
  - "Card pool changed": `card_changes.csv` has a row for a card of the window's color at the
    window's stable build whose kind includes added, removed or rarity_change.
  - Bootstrap: runs resampled with replacement within each block; each draw recomputes every
    control card's log share ratio and its rarity median, so the SE is of the deviation the z
    uses. That is cheap done by matrix, so it runs on every control row. The "fixed random 100
    rows" (seed 0) are reported too, as asked.
  - A limit to add: offers are RNG given the pool a run draws from, but who is playing, and
    what they have unlocked or reached, can still move shares between blocks. Whether this
    game gates cards behind unlocks is not known to me. [unverified] An inflated offer z
    therefore isn't proof of a pipeline fault. An honest one is clean evidence for the
    pipeline.

#### Part 3. Cut-point sweep (the main test)

Design, the same at every cut **(Phil)**: before = the 3 weeks before the cut, after = weeks
0–2 from the cut. Pseudo cards: each character's cards unchanged across the cut
(`window_changes`), up to 20 per character per cut, seed fixed, `min_offers` as in
`placebo_all` (51 in each block). Same model and clustering as `placebo_fit`. One row per
(cut, character, card).

- a. Real stable boundaries: v0.98.1 → v0.98.2 → v0.98.3 → v0.99.1 → v0.103.2 → v0.103.3 →
  v0.107.1, six cuts at the newer build's release date. Before is the older build's offers,
  after the newer build's.
- b. Interior cuts: inside one stable build, every 7 days from release + 3 weeks to (last day
  with play) − 3 weeks; both blocks are that build's offers, split by `start_time`.
- Gate (Phil): the date-split path, given a real boundary's build split, must reproduce the
  build-split z for 3 pairs to 1e-4.
- Anchors (Phil): the two real windows under this 3 + 3 design, next to 4.10 / 2.67.
- Per cut (Phil): robust sd and plain sd of z, share |z| > 2, n, weeks since that build's
  release, card changes across the cut, 95% interval on the robust sd from resampling cards
  within the cut; and the offer-rate z of part 2.
- Runtime (Phil): 10 fits timed first and the estimate reported. Over 2 h: interior cuts every
  14 days.

**Rules (Phil):**
- **Interior cuts pooled have robust sd ≤ 1.3 AND the real boundaries pooled have ≥ 2 = "the
  excess is tied to releases" (the nudge story is supported).**
- **Interior cuts pooled ≥ 2 = "the excess is not tied to releases": week-to-week variation
  the SEs miss, release or not.**
- **Otherwise mixed; described.**
- **Settling (N's lead): robust sd of interior cuts against weeks since release. Spearman < 0
  with its interval below 0 = the spread fades through a build.** Weeks since release and
  calendar date can't be separated in v0.107.1.
- **Boundaries with zero card changes against boundaries with changes: descriptive only, not a
  test; too few boundaries.**

Mine:
- **Blocks at a boundary.** Before = the older build's offers started in the 21 days before
  the newer build's release date (00:00 UTC, as `release_date`); its offers played after the
  release are left out, unlike the main design, because "the 3 weeks before the cut" excludes
  them. After = the newer build's offers in weeks 0–2 from its release. Three older builds
  lived under 3 weeks (v0.98.1 one day, v0.98.2 four, v0.98.3 seven) and v0.103.3 lived 20
  days, so those before blocks are shorter than 3 weeks. For v0.98.2 and v0.98.3 as the newer
  build, weeks 0–2 run past their replacement's release, so the after block holds play on a
  superseded build; the share of such offers is reported per cut.
- **"Last day with play"** is read as the last day the build was the current stable: the day
  before the next stable's release, or 2026-10-03 for v0.107.1 (the snapshot's last full day).
  Every build has stray play into October, so the literal reading would put cuts in periods
  with almost no data. That gives no interior cut in v0.98.x, v0.99.1 (30 days) or v0.103.3,
  one in v0.103.2 (2026-05-07) and ten in v0.107.1 (2026-07-09 to 2026-09-10, 3 to 12 weeks
  after release): 11 cuts. So the interior side is almost entirely one build.
- **Interior cuts overlap.** Blocks are 3 weeks and cuts are 7 days apart, so neighbouring
  cuts share two thirds of their data and the pooled rows are not independent. The pooled
  robust sd is still the declared statistic. Its interval resamples cards, keeping a card's
  rows from every cut together. The two cuts of v0.107.1 that share no data (weeks 3 and 9)
  are also reported alone.
- **Sampling.** Each character's cards are put in one fixed random order (seed 0 and the
  character), and a cut takes the first 20 in that order that are eligible there. So the same
  cards recur across cuts where they can, which the card-level resampling and the
  adjacent-boundary check below need.
- **Pseudo cards at interior cuts.** As given: unchanged across the cut, which inside a build
  is every card. A card changed on entering the build may still be settling, which N kept out.
  Each row is flagged, and the interior result is also given without the flagged rows. The
  flagged cards stay in the controls either way.
- **Gate.** Three saved pairs (first patch, second patch, and an upgraded-offers pair or a
  third character), refit through this script's loader and fake window with the block set by
  build and the after block cut at week 3, must return the saved z to 1e-4.
- **Anchors.** The prompt names "v0.99.1 → v0.103.2 and v0.103.2 → v0.107.1 (the real
  windows)". The second real window is v0.103.3 → v0.107.1 (`windows.csv`), and v0.103.2 had
  only stray play in the 3 weeks before v0.107.1, so I read it as v0.103.3 → v0.107.1. Two
  versions: (i) the 463 saved pairs refit under 3 + 3, same cards and same kind of fit, so
  only the design changes; (ii) the sweep's own rows for those two boundaries (new sample of
  cards, all offers). (i) is the one to set next to 4.10 / 2.67.
- **z depends on the SE, and the hypothesis is stated in pp.** A nudge of fixed size gives a
  smaller z where blocks hold fewer offers, and late v0.107.1 blocks do. So each cut also gets
  its excess variance in pp² (Var(β) − mean SE², and a robust version), its τ by part 1's
  likelihood, and its median SE. And one benchmark: the robust sd of z the interior cuts
  **would** show at their own SEs if they carried the τ of the real boundaries pooled (5,000
  draws, 95% range). The rules decide on z as given. If interior z is ≤ 1.3 but inside that
  benchmark's range, the interior cuts were too imprecise to tell, and I will say so.
- **Pooling the boundaries.** All six, as given. The three v0.98.x boundaries have short
  before blocks and so large SEs; the pooled figure is also given for the three later
  boundaries alone.
- **Settling.** Spearman over the 11 interior cuts' robust sds against weeks since release;
  interval by resampling cards (all of a card's cuts together) and recomputing. Also on τ.
- **Adjacent boundaries** (not asked; no rule). Independent offsets per build predict that a
  card's β across one boundary and across the next are negatively correlated (−0.5 before
  noise), since they share a block. Reported for each pair of consecutive boundaries on the
  cards sampled in both, with the value expected at those SEs. v0.103.2 → v0.103.3 → v0.107.1
  is the pair with usable data.
- **Offer-rate z at every cut.** `offer_rate_check` on the cut's two blocks, every unchanged
  card of the character, `z_binom_rarity`, with the bootstrap SE version if part 2 shows it is
  cheap. Same bands as part 2 (≤ 1.2, ≥ 1.5), read at the interior cuts first.
- **What the main rule can't separate.** A release also moves who is on the stable branch
  (beta players come back, others return to try the patch). A spread tied to releases
  supports "something happens at a release", of which a per-card offset is one form.
  Interior cuts of v0.107.1 are not quiet either: five beta builds came out during it.

### Results

Everything below was computed after the text above was written.

### Answer

**Mixed under the rule, and the substance is clearer than the label: most of the placebo
excess sits at releases, but not as a fresh offset at every build.** Across real boundaries the
robust sd of z is 2.14 [1.91, 2.37]; at cuts inside a build it is 1.38 [1.26, 1.48], just over
the 1.3 the rule needed. In pp² the excess is 5.0 at boundaries against 1.2 inside builds. Three
things don't fit the hypothesis as stated. The one boundary that changed no card and has full
blocks (v0.103.2 → v0.103.3) looks like an interior cut (1.69, τ 1.2 pp), not like the two
patches (2.80 and 2.33, τ 3.1 and 2.2 pp). The spread inside a build is highest in the weeks
right after a release and fades. And a card's moves across consecutive boundaries are not
negatively correlated where the blocks share no data, which fresh offsets would require.
What the tables fit is **a step at a release that changes cards, which then persists, plus a
few weeks of settling**. Offer rate, which players don't choose, is honest throughout. The
factors stay as they are. [inferred]

### Declared outcomes [computed]

| Part | Result | Outcome under the rule |
|---|---|---|
| 1. One nudge size | τ 3.35 [2.95, 3.72] and 2.44 [2.15, 2.71] pp, intervals apart; both robust sds inside the pooled-τ range | **The patches differ in nudge size** |
| 2. Offer rate | Robust sd 1.16 (first), 0.93 (second) | **Honest**: the excess is behavior, not the pipeline. Plain sd 2.44 in the first patch: a one-sided tail, unrelated to the placebo misses |
| 3. Sweep | Interior pooled 1.38 [1.26, 1.48]; boundaries pooled 2.14 [1.91, 2.37] | **Mixed**: the boundaries pass (≥ 2), the interior misses ≤ 1.3 by 0.08 and is far below 2 |
| 3. Settling | Spearman −0.66 [−0.90, −0.21] over 11 interior cuts | **The spread fades through a build.** v0.107.1 alone: −0.55 [−0.87, +0.04], not clear of 0 |

### Checks and changes after the rules [computed]

- `--check`: the likelihood recovers a planted τ and returns 0 when there is none. **Gate
  passed**: the date-split loader, given the real build split, returns the saved z for 3 pairs
  (Silent first patch, Ironclad second patch, one upgraded-offers pair), through the real
  window row and through the fake window: largest |Δz| 1e-09.
- `placebo_h3` gives 463 pairs and 4.10 / 2.67; the script stops otherwise.
- **Runtime estimate, made before the sweep:** 2.7 s per fit on the largest cut, so about 101
  minutes for up to 2,163 fits. Under 2 h, so interior cuts stayed at every 7 days. The sweep
  took about an hour: 1,603 cut fits and 463 anchor fits, none failed.
- **The sweep's summary step crashed once**, after every fit was saved: the settling
  correlation for "v0.107.1 only" was handed the empty v0.103.2 cut. Fixed, and the summaries
  were recomputed from the saved fits (`--part 3 --summary`). No fit was rerun and no rule or
  definition changed.
- v0.98.1 → v0.98.2 has 3 fits: its before block is one day, and few cards reach 51 offers. It
  is in the pooled boundary figure (503 rows = 500 + 3) and has no row of its own.
- Rarity is derived, as declared: the offer tier agrees with the rarity on file for 95 of 97
  cards.
- No new dependency: scipy is already in the `analysis` extra.
- **Part 4 is post hoc or asked for later:** the offer-rate tail and its link to the placebo
  z (mine, after reading part 2), and the two descriptive asides (Phil, while part 3 ran).
- Tests: `pytest tests` gives 266 passed, 4 skipped. The other 47 (27 failed, 20 errors) are
  all `PermissionError` on `reference/raw/`, which the sandbox closes. Collection from the
  repository root also stops on `.spirometry_salt` for the same reason, so the run names
  `tests` and ignores the closed paths. The triage scripts have no tests of their own;
  `--check` is this script's.
- **Git writes are blocked**, as in O and P: no branch `nudge`, no commit. Phil's
  `triage/scripts/q_z_vs_offers.py` is in the working tree, to go in the same commit.

### Part 1. One nudge size, two patches? [computed]

Tables: `q_tau.csv`, `q_tau_predict.csv`, `q_tau_pairs.csv` (the 463 pairs on both scales, for
plotting). τ and its interval in pp unless marked.

| Fit | Pairs (cards) | Median SE | μ | τ [95%] | σ_b = τ/√2 | τ, log-odds [95%] |
|---|---|---|---|---|---|---|
| First | 217 (199) | 0.82 | −0.13 | **3.35 [2.95, 3.72]** | 2.37 | 0.180 [0.155, 0.206] |
| Second | 246 (222) | 0.95 | +0.41 | **2.44 [2.15, 2.71]** | 1.73 | 0.133 [0.115, 0.151] |
| Pooled, one τ | 463 (312) | 0.88 | −0.13 / +0.42 | 2.92 [2.63, 3.16] | 2.06 | 0.158 [0.140, 0.176] |
| First − second | | | | 0.91 [0.47, 1.33] | | 0.047 [0.023, 0.068] |

On the 403 all-offers pairs: 3.25 [2.87, 3.60] and 2.44 [2.15, 2.69], difference 0.81
[0.41, 1.21].

Robust sd of z, observed against simulated from each pair's own SE:

| Patch | Observed | Pooled τ: median [95% range] | Inside | Same, τ drawn from its bootstrap | The patch's own τ: median [95% range] |
|---|---|---|---|---|---|
| First | 4.10 | 3.60 [3.05, 4.21] | yes | [2.95, 4.27] | 4.07 [3.45, 4.77] |
| Second | 2.67 | 3.05 [2.61, 3.54] | yes | [2.55, 3.58] | 2.64 [2.26, 3.05] |

The log-odds scale gives the same pattern: predicted 3.62 [3.06, 4.24] and 3.08 [2.64, 3.57],
both observed values inside.

Reading. [inferred]
- **Rule: "the patches differ in nudge size."** The second half of the rule passes: both
  observed robust sds are inside the pooled-τ range. The first half fails: the τ intervals
  don't overlap (2.95 against 2.71), on either scale, and the difference's own interval is
  clear of 0. The rule needs both.
- **The SEs explain part of the factors' gap, not most of it.** One τ of 2.92 pp predicts 3.60
  and 3.05. That is a ratio of 1.18 from the SEs alone, against the observed 1.53, or about
  0.4 of the gap between 4.10 and 2.67. The second patch sits at the bottom of its predicted
  range and the first near the top of its own, which is what two different τ look like.
- **The normal model is adequate for this purpose.** With each patch's own τ the simulation
  gives 4.07 and 2.64, against 4.10 and 2.67.
- In variance, τ² is 11.2 and 6.0 pp², which is N's direct figure (11.8 and 6.7) by another
  route. If the hypothesis holds, the offset a build gives a card has sd 2.4 pp at v0.103.2
  and 1.7 pp at v0.107.1. A nudge "unrelated to balance changes" has no reason to be larger
  at the release with more changes (88 cards against 50), though two releases can't show
  that it is related either.

### Part 2. Offer rate as a negative control [computed]

Tables: `q_offer_rows.csv` (622 rows, one per window and control card), `q_offer_summary.csv`
(every split below, also per window). No row lacked a finite z. Tweaks sharing a window gave
identical z for a control card, so the dedupe averaged nothing. Runtime 69 s, the bootstrap 9 s
of it, so it ran on every row.

| | n | Robust sd | Plain sd | Share \|z\| > 2 | Robust sd, bootstrap SE | Plain sd, bootstrap SE |
|---|---|---|---|---|---|---|
| **First** | 258 | **1.16** | 2.44 | 0.147 | 1.15 | 2.23 |
| **Second** | 364 | **0.93** | 1.32 | 0.074 | 0.94 | 1.26 |
| Both | 622 | 1.04 | 1.88 | 0.105 | 1.06 | 1.74 |
| Fixed 100 rows | 100 | 0.81 | 1.94 | 0.070 | 0.83 | 1.72 |

Per rarity, robust sd: first Common 0.84, Uncommon 1.45, Rare 0.93; second 0.77, 1.01, 1.01.
Per window it runs from 0.78 to 1.36 (Silent, first). Windows whose pool changed against the
rest: first 1.06 against 1.18, second 0.99 against 0.89. Without the rarity adjustment
(`z_binom`) the robust sd is 1.29 and 1.33, so the adjustment matters, as `offer_rate_check`
intends.

Reading. [inferred]
- **Rule: honest, in both patches (1.16 and 0.93, both ≤ 1.2).** The windows and the data give
  a z of about the right size on a quantity players don't choose. So the pick-rate excess of
  4.10 and 2.67 is not something the window construction makes by itself.
- **The clustering isn't the issue for offers.** The run-clustered bootstrap SE is 0.98–0.99
  of the binomial SE at the median, and the robust sds barely move. That was the declared
  limit of the binomial z, and here it turns out not to bind.
- **The body is honest and the tail is not.** The plain sd is 2.44 in the first patch, and
  14.7% of rows are beyond 2 where 4.6% is expected. First-patch Uncommons are at 1.45,
  which alone would read as mixed. The rule is on the robust sd and I apply it as written;
  the tail is taken up post hoc below.

**The offer-rate tail, post hoc** (`q_posthoc_offer_tail.csv`, `q_posthoc_offer_link.csv`;
part 4 of the script, added after reading the table above). 36 of 622 rows have |z| > 3, and
30 of those are positive: a card's share of offers **rose** against its rarity's median.

| Patch | Card | Share change against its rarity | Offer z | Placebo z of the same pair |
|---|---|---|---|---|
| first | Blood Wall | +21% | +17.5 | +9.9 |
| first | Inferno | +28% | +13.7 | not a pair |
| first | Lunar Blast | +32% | +13.5 | −4.6 |
| first | Afterlife | +14% | +11.1 | +0.2 |
| first | Phantom Blades | +18% | +9.1 | +5.8 |
| first | Veilpiercer | +19% | +8.4 | +0.8 |
| first | Heavenly Drill | +25% | +7.6 | −2.1 |
| second | Blood Wall | +9% | +7.6 | −0.2 |
| second | TURBO | +8% | +6.2 | +3.6 |
| second | Sculpting Strike | +8% | +6.0 | −1.4 |

- Six cards are in the tail in both patches (Blood Wall, Inferno, Lunar Blast, Heavenly Drill,
  Hidden Daggers, Supermassive), each time upward and by less in the second.
- **This is not the placebo excess.** Across the 403 all-offers pairs, the rank correlation
  between a card's offer z and its placebo z is +0.07 [−0.02, 0.16] signed and −0.07
  [−0.17, 0.03] in size. With every pair whose offer |z| exceeds 2 left out, the placebo
  robust sd is 4.30 and 3.06, against 4.23 and 2.95 on the same pairs before.
- What moves these cards' offers is not known. Offers are random given the pool a run draws
  from, so a one-sided, repeating rise looks like more runs having these cards in their pool
  over time, as unlocks through play would do. Whether the game works that way is not in any
  table here. [unverified] A rarity that the offer tiers got wrong doesn't explain it: that
  would set a card against the wrong median, and a window's medians differ by 0.06 at most,
  against rises of 0.07 to 0.28 in log share.

### Descriptive asides, no tests [computed]

Asked for by Phil while part 3 ran, after his `q_z_vs_offers.py` look. Tables:
`q_aside_offer_bins.csv`, `q_aside_second_top_bin.csv`, `q_aside_first_offer_tail.csv`. His τ
for the second patch (2.47) differs from part 1's (2.44) because his fit holds μ at 0.

**(a) The second patch's top offer bin.** Six bins per patch by the pseudo card's offers in
the fit, as in his script. The top bin is 41 pairs with 30,276 to 42,052 offers, and **every
one is a Common**, all-offers fits: Necrobinder 13, Defect 12, Ironclad 8, Regent 5, Silent 3.
30 of the 41 have z below 0.

| Patch | Bin | Pairs | Offers, median | Median SE (pp) | Robust sd z | Robust sd β (pp) | Share Common |
|---|---|---|---|---|---|---|---|
| first | 1 | 37 | 6,244 | 1.27 | 2.35 | 3.90 | 0.00 |
| first | 2 | 36 | 7,446 | 1.14 | 3.94 | 4.25 | 0.11 |
| first | 3 | 37 | 13,171 | 0.83 | 3.91 | 3.15 | 0.00 |
| first | 4 | 35 | 13,998 | 0.80 | 5.74 | 4.22 | 0.03 |
| first | 5 | 36 | 16,604 | 0.69 | 4.18 | 2.92 | 0.22 |
| first | 6 (top) | 36 | 43,157 | 0.43 | 5.53 | 2.17 | 1.00 |
| second | 1 | 41 | 1,638 | 2.32 | 1.35 | 3.92 | 0.12 |
| second | 2 | 41 | 5,391 | 1.36 | 2.03 | 2.77 | 0.05 |
| second | 3 | 41 | 10,657 | 0.98 | 2.80 | 2.68 | 0.02 |
| second | 4 | 41 | 11,847 | 0.93 | 3.21 | 2.94 | 0.00 |
| second | 5 | 41 | 15,081 | 0.73 | 4.22 | 3.09 | 0.32 |
| **second** | **6 (top)** | 41 | 33,257 | 0.50 | **2.71** | **1.55** | 1.00 |

The top bin's pairs, β in pp:

| Character | Card | Offers | β (SE) | z |
|---|---|---|---|---|
| Silent | Slice | 40,244 | −2.10 (0.40) | −5.2 |
| Ironclad | Iron Wave | 41,654 | −2.17 (0.42) | −5.2 |
| Ironclad | Setup Strike | 41,936 | −2.41 (0.47) | −5.1 |
| Defect | Hotfix | 33,341 | −2.64 (0.55) | −4.8 |
| Necrobinder | Drain Power | 33,007 | −1.85 (0.44) | −4.2 |
| Necrobinder | Blight Strike | 33,274 | −1.97 (0.48) | −4.1 |
| Necrobinder | Wisp | 33,118 | −2.40 (0.60) | −4.0 |
| Defect | Leap | 33,561 | −1.89 (0.50) | −3.8 |
| Regent | Refine Blade | 30,353 | −1.97 (0.59) | −3.3 |
| Regent | Photon Cut | 30,276 | −1.35 (0.42) | −3.2 |
| Necrobinder | Flatten | 32,736 | −1.82 (0.59) | −3.1 |
| Silent | Poisoned Stab | 40,346 | −1.46 (0.48) | −3.1 |
| Regent | Hidden Cache | 30,364 | −1.76 (0.59) | −3.0 |
| Defect | Sweeping Beam | 33,257 | −1.27 (0.44) | −2.9 |
| Necrobinder | Scourge | 31,887 | −1.48 (0.57) | −2.6 |
| Defect | Ball Lightning | 33,502 | −1.17 (0.56) | −2.1 |
| Ironclad | Molten Fist | 41,875 | −1.04 (0.53) | −2.0 |
| Defect | Beam Cell | 33,434 | −0.90 (0.53) | −1.7 |
| Necrobinder | Defile | 33,239 | −0.75 (0.46) | −1.6 |
| Ironclad | Armaments | 42,052 | −0.72 (0.45) | −1.6 |
| Defect | Charge Battery | 33,535 | −0.74 (0.59) | −1.3 |
| Silent | Ricochet | 40,503 | −0.43 (0.48) | −0.9 |
| Defect | Claw | 33,389 | −0.61 (0.77) | −0.8 |
| Necrobinder | Poke | 32,745 | −0.43 (0.58) | −0.7 |
| Regent | Crush Under | 30,286 | −0.28 (0.48) | −0.6 |
| Ironclad | Blood Wall | 32,534 | −0.10 (0.54) | −0.2 |
| Necrobinder | Fear | 33,074 | −0.08 (0.47) | −0.2 |
| Ironclad | Cinder | 37,449 | −0.04 (0.30) | −0.1 |
| Necrobinder | Pull Aggro | 32,841 | −0.06 (0.48) | −0.1 |
| Defect | Cold Snap | 33,239 | −0.04 (0.49) | −0.1 |
| Ironclad | Pommel Strike | 41,856 | +0.23 (0.58) | +0.4 |
| Defect | Lightning Rod | 33,292 | +0.38 (0.58) | +0.7 |
| Necrobinder | Reap | 32,816 | +0.33 (0.40) | +0.8 |
| Necrobinder | Grave Warden | 33,016 | +0.64 (0.61) | +1.1 |
| Necrobinder | Graveblast | 32,929 | +0.50 (0.46) | +1.1 |
| Defect | Gunk Up | 33,236 | +0.89 (0.47) | +1.9 |
| Ironclad | Tremble | 41,765 | +1.18 (0.51) | +2.3 |
| Regent | Glitterstream | 30,405 | +2.28 (0.50) | +4.6 |
| Defect | Hologram | 33,325 | +2.96 (0.58) | +5.1 |
| Defect | Boost Away | 33,423 | +3.97 (0.56) | +7.1 |
| Necrobinder | Defy | 33,070 | +4.52 (0.61) | +7.4 |

So the bin that breaks the rising pattern is a rarity, not an offer count: the offer bins and
rarity can't be separated at the top, in either patch. Commons' β is the tightest of any bin
in both patches (2.17 and 1.55 pp against 2.9–4.2 and 2.7–3.9), which is N's result too
(Commons drift least). In the first patch the SE there is small enough that z is still wide.
Rarity is the offer tier where the card isn't on file. [computed; the last sentence of
reading is inferred]

**(b) The first patch's one-sided offer-rate tail.** The 20 control cards with offer z above
+3 in the first window (4 are below −3). `window_changes` gives the set of changed cards and
not the kind of change, so the kind comes from `card_changes.csv` for cards in that set.

| Character | Card | Rarity | Share change against its rarity | Offer z | Pool change on file for that character and rarity |
|---|---|---|---|---|---|
| Ironclad | Blood Wall | Common | +21% | +17.5 | none |
| Ironclad | Inferno | Uncommon | +28% | +13.7 | Colossus joined (Rare → Uncommon) |
| Regent | Lunar Blast | Uncommon | +32% | +13.5 | none |
| Necrobinder | Afterlife | Common | +14% | +11.1 | none |
| Silent | Phantom Blades | Uncommon | +18% | +9.1 | Acrobatics joined (Common → Uncommon) |
| Necrobinder | Veilpiercer | Uncommon | +19% | +8.4 | none |
| Regent | Heavenly Drill | Rare | +25% | +7.6 | none |
| Silent | Hidden Daggers | Uncommon | +13% | +6.5 | Acrobatics joined |
| Silent | Reflex | Uncommon | +11% | +6.2 | Acrobatics joined |
| Ironclad | Drum of Battle | Uncommon | +11% | +6.2 | Colossus joined |
| Necrobinder | Calcify | Uncommon | +11% | +5.4 | none |
| Silent | Hand Trick | Uncommon | +10% | +5.4 | Acrobatics joined |
| Silent | Master Planner | Rare | +12% | +4.4 | none |
| Necrobinder | Sacrifice | Rare | +13% | +4.3 | none |
| Regent | Supermassive | Uncommon | +8% | +4.1 | none |
| Necrobinder | Sleight of Flesh | Uncommon | +7% | +3.8 | none |
| Necrobinder | Haunt | Uncommon | +7% | +3.7 | none |
| Ironclad | Feel No Pain | Uncommon | +5% | +3.4 | Colossus joined |
| Regent | Child of the Stars | Uncommon | +5% | +3.1 | none |
| Regent | Black Hole | Uncommon | +5% | +3.1 | none |

- 13 of the 20 have no pool change on file for their rarity. The other 7 are Ironclad and
  Silent Uncommons, where one card joined the rarity. A card joining a rarity lowers every
  other member's share by the same amount, which the rarity median already removes, and these
  shares rose.
- Not placed: Grapple (removed) and Follow Through (Uncommon → Common) changed at v0.103.2
  with no color on file, so they can't be assigned to a character. Left blank, not guessed.
- Rarity is the offer tier for cards not on file; Regent and Necrobinder have no recorded
  addition, removal or rarity change in this window.

### Part 3. Cut-point sweep [computed]

Tables: `q_cuts.csv` (the 17 cuts), `q_cut_fits.csv` (1,603 fits, one per cut, character and
card), `q_cut_info.csv` (offers and dates per cut and character), `q_cut_offer.csv` (offer-rate
z of every unchanged card at every cut), `q_cut_summary.csv`, `q_pooled.csv`,
`q_interior_benchmark.csv`, `q_settling.csv`, `q_anchor_pairs.csv`, `q_anchor.csv`,
`q_adjacent.csv`. 100 fits per cut (20 per character) except v0.98.1 → v0.98.2. Excess is
Var(β) − mean SE²; τ by part 1's likelihood. "Offer z" is the robust sd / plain sd of
`z_binom_rarity` over about 400 cards.

**Real boundaries.**

| Cut | Before block | Own-color cards changed | Robust sd z [95%] | Plain sd | \|z\| > 2 | Median SE (pp) | Excess (pp²) | τ (pp) [95%] | Offer z |
|---|---|---|---|---|---|---|---|---|---|
| v0.98.1 → v0.98.2 | 1 day | 0 | 3 fits | | | | | | |
| v0.98.2 → v0.98.3 | 4 days | 0 | 1.92 [1.52, 2.55] | 2.24 | 0.36 | 1.43 | 7.0 | 2.49 [1.96, 2.94] | 1.16 / 3.63 |
| v0.98.3 → v0.99.1 | 7 days | 0 | 2.13 [1.65, 2.41] | 1.86 | 0.29 | 1.05 | 2.3 | 1.43 [1.11, 1.66] | 1.14 / 2.35 |
| **v0.99.1 → v0.103.2** | 21 days | 70 | **2.80 [2.27, 3.67]** | 3.45 | 0.50 | 0.97 | 9.7 | 3.07 [2.47, 3.61] | 1.09 / 2.02 |
| v0.103.2 → v0.103.3 | 21 days | 0 | **1.69 [1.24, 2.11]** | 1.68 | 0.21 | 1.07 | 1.6 | 1.20 [0.90, 1.46] | 0.99 / 1.03 |
| **v0.103.3 → v0.107.1** | 20 days | 37 | **2.33 [1.59, 3.21]** | 2.87 | 0.46 | 0.95 | 5.1 | 2.22 [1.79, 2.59] | 1.04 / 1.39 |

After-block play on a superseded build: 12% of offers at v0.98.2 → v0.98.3, 4% at v0.103.2 →
v0.103.3, none elsewhere.

**Interior cuts.**

| Cut | Weeks since release | Robust sd z [95%] | Plain sd | \|z\| > 2 | Median SE (pp) | Excess (pp²) | τ (pp) [95%] | Offer z |
|---|---|---|---|---|---|---|---|---|
| v0.103.2 @ 05-07 | 3 | 2.14 [1.69, 2.56] | 2.36 | 0.31 | 1.05 | 3.9 | 1.94 [1.53, 2.36] | 0.94 / 1.28 |
| v0.107.1 @ 07-09 | 3 | 1.76 [1.37, 2.27] | 2.00 | 0.26 | 0.94 | 2.1 | 1.42 [1.05, 1.71] | 1.05 / 1.36 |
| v0.107.1 @ 07-16 | 4 | 1.50 [1.19, 1.88] | 1.73 | 0.21 | 0.99 | 1.4 | 1.17 [0.79, 1.50] | 1.15 / 1.15 |
| v0.107.1 @ 07-23 | 5 | 1.26 [0.87, 1.65] | 1.38 | 0.18 | 1.06 | 0.7 | 0.81 [0.52, 1.02] | 0.89 / 1.02 |
| v0.107.1 @ 07-30 | 6 | 1.28 [0.97, 1.59] | 1.34 | 0.15 | 1.10 | 0.8 | 0.84 [0.46, 1.09] | 0.97 / 1.03 |
| v0.107.1 @ 08-06 | 7 | 1.15 [0.82, 1.46] | 1.20 | 0.13 | 1.12 | 0.6 | 0.57 [0.00, 0.88] | 0.92 / 1.03 |
| v0.107.1 @ 08-13 | 8 | 1.31 [1.06, 1.59] | 1.28 | 0.14 | 1.15 | 0.5 | 0.75 [0.49, 0.97] | 1.03 / 1.00 |
| v0.107.1 @ 08-20 | 9 | 1.28 [0.97, 1.46] | 1.19 | 0.08 | 1.17 | 0.1 | 0.64 [0.34, 0.86] | 0.94 / 1.07 |
| v0.107.1 @ 08-27 | 10 | 1.45 [1.11, 1.73] | 1.37 | 0.11 | 1.17 | 1.1 | 0.87 [0.54, 1.14] | 0.95 / 1.13 |
| v0.107.1 @ 09-03 | 11 | 1.13 [0.79, 1.50] | 1.43 | 0.18 | 1.18 | 1.2 | 1.01 [0.53, 1.32] | 0.94 / 1.09 |
| v0.107.1 @ 09-10 | 12 | 1.16 [0.78, 1.43] | 1.32 | 0.14 | 1.18 | 1.0 | 0.82 [0.41, 1.07] | 0.90 / 0.98 |

**Pooled.** Intervals resample cards, a card's rows from every cut together.

| Rows | n | Robust sd z [95%] | Plain sd | \|z\| > 2 | Median SE (pp) | Excess (pp²) | τ (pp) [95%] |
|---|---|---|---|---|---|---|---|
| **Interior cuts [rule]** | 1,100 | **1.38 [1.26, 1.48]** | 1.55 | 0.17 | 1.12 | 1.2 | 1.08 [0.92, 1.20] |
| Interior, cards changed entering the build left out | 997 | 1.36 [1.25, 1.47] | 1.53 | 0.17 | 1.13 | 1.2 | 1.06 [0.90, 1.20] |
| Interior, v0.107.1 only | 1,000 | 1.31 [1.20, 1.42] | 1.44 | 0.16 | 1.13 | 0.9 | 0.94 [0.77, 1.07] |
| Interior, v0.107.1 weeks 3 and 9 (no shared data) | 200 | 1.39 [1.23, 1.62] | 1.64 | 0.17 | 1.07 | 1.1 | 1.13 [0.88, 1.34] |
| Interior, v0.107.1 weeks 3–7 | 500 | 1.31 [1.20, 1.55] | 1.56 | 0.19 | 1.07 | 1.1 | 1.04 [0.80, 1.22] |
| Interior, v0.107.1 weeks 8–12 | 500 | 1.22 [1.10, 1.39] | 1.32 | 0.13 | 1.17 | 0.8 | 0.81 [0.60, 0.97] |
| **Real boundaries [rule]** | 503 | **2.14 [1.91, 2.37]** | 2.49 | 0.36 | 1.06 | 5.0 | 2.19 [1.92, 2.42] |
| Boundaries, the three later ones | 300 | 2.27 [1.91, 2.55] | 2.76 | 0.39 | 0.99 | 5.5 | 2.31 [1.98, 2.63] |
| Boundaries, v0.98.x | 203 | 2.00 [1.65, 2.30] | 2.04 | 0.32 | 1.25 | 4.3 | 1.94 [1.56, 2.25] |
| Boundaries with zero card changes | 300 | 1.90 [1.65, 2.19] | 1.94 | 0.29 | 1.15 | 3.7 | 1.70 [1.40, 1.95] |
| Boundaries with card changes | 203 | 2.63 [2.13, 3.23] | 3.14 | 0.47 | 0.96 | 7.0 | 2.67 [2.27, 3.06] |

Offer-rate z, pooled: interior 0.96 robust (0.99 with the bootstrap SE), 1.11 plain, 6.5%
beyond 2, over 4,399 rows. Boundaries 1.05 robust, 2.17 plain, 9.6% beyond 2, over 2,248 rows.

**Benchmark: what the interior cuts would show at their own SEs with the boundaries' τ.**

| τ taken from | τ (pp) | Predicted interior robust sd [95% range] | Observed |
|---|---|---|---|
| Boundaries pooled | 2.19 | 2.29 [2.13, 2.45] | 1.38 |
| Same, lower end of its interval | 1.92 | 2.08 [1.93, 2.23] | 1.38 |
| The three later boundaries | 2.31 | 2.38 [2.22, 2.56] | 1.38 |
| v0.103.2 → v0.103.3 alone | 1.20 | 1.54 [1.44, 1.66] | 1.38 |

**Settling.** Spearman of each interior cut's spread against weeks since release:

| Statistic | Cuts | Spearman [95%] |
|---|---|---|
| Robust sd of z, all interior cuts [rule] | 11 | **−0.66 [−0.90, −0.21]** |
| Robust sd of z, v0.107.1 only | 10 | −0.55 [−0.87, +0.04] |
| τ, all interior cuts | 11 | −0.46 [−0.85, −0.14] |
| τ, v0.107.1 only | 10 | −0.29 [−0.81, +0.13] |

**Anchors: the 463 saved pairs refit under 3 + 3**, same cards and same kind of fit.

| Patch | Pairs | Saved robust sd (factor) | Under 3 + 3 [95%] | Ratio [95%] | Median SE: saved → 3 + 3 (pp) | τ: saved → 3 + 3 (pp) | Corr of β |
|---|---|---|---|---|---|---|---|
| First | 217 | 4.10 | 3.30 [2.87, 3.98] | 0.81 [0.74, 0.93] | 0.82 → 0.96 | 3.35 → 3.31 | 0.96 |
| Second | 246 | 2.67 | 2.75 [2.19, 3.23] | 1.03 [0.91, 1.12] | 0.95 → 1.00 | 2.44 → 2.68 | 0.98 |

The sweep's own rows for the same two boundaries (a new sample of 100 cards, all offers) are
2.80 and 2.33, in the boundary table above.

**Adjacent boundaries.** Correlation of a card's β across one boundary and the next, on cards
sampled in both, β centered within character. "Shared noise" is what the same offers in both
fits produce with no nudge (the middle build's two blocks are the same days when it lived
under 3 weeks); "fresh offsets" adds −τ₁τ₂/2.

| Boundaries | Middle build | Cards | Corr of β [95%] | Expected, shared noise only | Expected, fresh offsets |
|---|---|---|---|---|---|
| v0.98.2 → v0.98.3 → v0.99.1 | v0.98.3, 7 days, same offers | 100 | **+0.40 [0.24, 0.55]** | −0.13 | −0.44 |
| v0.98.3 → v0.99.1 → v0.103.2 | v0.99.1, 30 days, no shared offers | 87 | −0.07 [−0.27, 0.15] | 0 | −0.35 |
| v0.99.1 → v0.103.2 → v0.103.3 | v0.103.2, 43 days, no shared offers | 87 | **+0.02 [−0.22, 0.25]** | 0 | −0.30 |
| v0.103.2 → v0.103.3 → v0.107.1 | v0.103.3, 20 days, same offers | 91 | −0.32 [−0.51, −0.10] | −0.14 | −0.44 |

Reading. [inferred]
- **Rule: mixed.** The boundaries pooled reach 2 (2.14, interval 1.91–2.37, so not clear of
  2). The interior cuts pooled are 1.38, over the 1.3 needed for "tied to releases" and far
  from the 2 needed for "not tied to releases". The interior interval contains 1.3.
- **The interior cuts were precise enough to tell.** Their SEs (median 1.12 pp) are like the
  boundaries' (1.06). With the boundaries' τ they would have shown 2.29 [2.13, 2.45]; they
  show 1.38. So this is not the case I flagged in the rules, where a low interior z could
  come from large SEs. In pp² the excess is 5.0 across boundaries and 1.2 inside builds.
- **So most of the excess is tied to releases, and about a quarter of it is there without
  one.** The interior excess is not zero at any stretch: 17% of interior z are beyond 2
  where 4.6% is expected, and τ is 0.8 pp even in weeks 8–12.
- **It fades after a release, as N's lead said.** The two cuts 3 weeks after a release are
  the highest interior ones (2.14 and 1.76), and their before blocks are the release's first
  three weeks. From week 5 on the robust sd is 1.13–1.45. The declared Spearman is
  below 0 with its interval. Within v0.107.1 alone the interval reaches +0.04, and weeks
  since release can't be told from the calendar there, as declared. So a release is followed
  by about a month of extra movement, which a single offset at the release doesn't describe.
- **The boundary without card changes doesn't behave like a patch.** v0.103.2 → v0.103.3 has
  full blocks and no card change: 1.69, τ 1.20 pp. That is below the interior cut of v0.103.2
  three weeks after its release (2.14, τ 1.94) and level with v0.107.1's early interior cuts.
  The two boundaries with card changes are at 2.80 and 2.33, τ 3.07 and 2.22. Descriptive
  only, as declared: one clean boundary without changes, two with. The v0.98.x boundaries
  also changed no card and are at 1.9–2.1, but they are the game's first twelve days, with
  before blocks of 4 and 7 days, and can't stand for a quiet release.
- **Fresh offsets per build are not what the cards do.** If each build drew a new offset
  around a card's own level, a card's β across two consecutive boundaries would be negatively
  correlated, about −0.3 at these SEs. Where the middle build's blocks share no offers, the
  correlation is −0.07 and +0.02, and the intervals stop at −0.27 and −0.22, short of the
  −0.35 and −0.30 expected. A step that stays (each release moves a card and it keeps the new level) predicts 0
  and fits. The one negative value, −0.32 through v0.103.3, is where the two fits use the
  same 20 days of offers, which gives −0.14 with no nudge at all; its interval holds both
  −0.14 and −0.44. That is section I's −0.66, on 91 unchanged cards, and weaker.
  At launch the sign is the other way: cards that moved from v0.98.2 to v0.98.3 kept moving
  the same way into v0.99.1 (+0.40), a trend and not an offset.
- **Under a step that stays, the extra variance of a DiD across one boundary is the step's
  variance, not 2σ_b².** Part 1's σ_b = τ/√2 only applies under fresh offsets, so read τ
  itself as the size: 3.3 pp at v0.103.2, 2.4 pp at v0.107.1.
- **The design moves z, not τ.** For the first patch, 3 + 3 lowers the robust sd from 4.10 to
  3.30 because the shorter before block raises the SE (0.82 → 0.96 pp); τ is unchanged (3.35 →
  3.31). For the second patch both barely move, and τ rises a little (2.44 → 2.68). β under
  the two designs correlate at 0.96 and 0.98. So the sweep's boundary figures are a little
  lower than the factors for a reason that has nothing to do with the cards.
- **Offer rate is honest wherever it is cleanest.** At interior cuts, where the pool can't
  change, the robust sd is 0.96 and the plain sd 1.11. At boundaries the body is honest
  (1.05) and the plain sd is 2.17, with the tail largest at launch (3.63, 2.35) and smaller
  at each later boundary (2.02, 1.03, 1.39). That is the one-sided tail of part 2 again,
  shrinking with the game's age.

### What this does and doesn't settle

- **Settled, within limits:**
  - The pipeline is not the source. Offer rate gives z of the right size in both patches and
    at every interior cut.
  - The excess is much larger across a release than inside a build (5.0 against 1.2 pp²),
    measured with the same design, model and SE sizes on both sides.
  - It isn't one nudge size: τ differs between the two patches, and one release that changed
    no card is far below both.
  - It isn't a fresh offset per build: consecutive boundaries with separate data are
    uncorrelated.
  - Some excess remains inside a build and fades in the weeks after a release.
- **Fits but not shown:** a step in pick rate at releases that change cards, which stays, and
  about a month of settling after it. "Changes cards" rests on one clean boundary without
  changes against two with; and the two with changes are also the two major updates, so card
  changes can't be told from anything else those updates brought (relics, enemies, returning
  players).
- **Not settled:**
  - What the step is. Nothing here separates a per-card behavioral shift from a change in who
    is on the stable branch after a major update.
  - Whether the fading is "weeks since release" or the calendar. Ten of the eleven interior
    cuts are in one build.
  - Why some cards' offer share rises across releases (the one-sided tail). It is unrelated
    to the placebo misses, but it is unexplained.
  - Commons: they hold the top offer bin in both patches and have the tightest β, so "z grows
    with offers" and "Commons move less" can't be separated at the top.
- **A consequence for the dose-response, not acted on here:** if the step belongs to releases
  that change cards, an unchanged card's placebo spread is the right yardstick for a changed
  card only if the step is unrelated to the card's own change, which is what M and P looked
  at and didn't resolve.
- The factors are unaffected: they measure the spread and don't depend on its cause.

### Update to SPIROMETRY.md, open question 8 (applied 2026-11-11, with Phil's wording)

The line below is what this section proposed. Phil then supplied the text now in
SPIROMETRY.md. Two things from this line were merged into it: the rule's "mixed" label with
the excess variances (1.2 against 5.0 pp²), and the offer-rate robust sds (1.16 / 0.93). His
text also notes that the two boundaries with card changes are the two major updates.

> Release nudge, exploratory (triage Q, final tables): offer rate is honest (robust sd 1.16 /
> 0.93), so the excess is behavior and not the pipeline; under one 3 + 3 design the excess is
> 5.0 pp² across real stable boundaries against 1.2 pp² at cuts inside a build (robust sd 2.14
> against 1.38, "mixed" under the declared rule), fades in the weeks after a release, differs
> between the patches (τ 3.35 / 2.44 pp), is small at the one boundary that changed no card
> (1.69), and is uncorrelated across consecutive boundaries, so it reads as a lasting step at
> releases that change cards plus about a month of settling, not a fresh offset per build.

### Files, tables and runtime

- Changed: `triage/TRIAGE.md` (this section), `triage/scripts/q_nudge.py` (new),
  `README.md` (repository table), `PLAN.md` (status line and decision log), `SPIROMETRY.md`
  (open question 8). In the working
  tree and not mine: `triage/scripts/q_z_vs_offers.py` (Phil).
- Tables in `triage/out_final/`, for plotting:
  - Part 1: `q_tau.csv`, `q_tau_predict.csv`, `q_tau_pairs.csv`.
  - Part 2: `q_offer_rows.csv`, `q_offer_summary.csv`.
  - Part 3: `q_cuts.csv`, `q_cut_fits.csv`, `q_cut_info.csv`, `q_cut_offer.csv`,
    `q_cut_summary.csv`, `q_pooled.csv`, `q_interior_benchmark.csv`, `q_settling.csv`,
    `q_anchor_pairs.csv`, `q_anchor.csv`, `q_adjacent.csv`.
  - Post hoc and asides: `q_posthoc_offer_tail.csv`, `q_posthoc_offer_link.csv`,
    `q_aside_offer_bins.csv`, `q_aside_second_top_bin.csv`, `q_aside_first_offer_tail.csv`.
  - No figure was made.
- Runtime: `--check` 45 s; part 1 21 s; part 2 69 s; part 3 about an hour for the fits
  (five characters) and 18 s for the summaries; part 4 8 s. Peak memory
  2.9 GB for one character's v0.107.1 load; the sweep's own peak was not recorded, because
  the run that did the fits stopped in the summary step before printing it.

---

## R. Does the release shake scale with what changed, and is it within players? — EXPLORATORY

**EXPLORATORY.** Proposed by Phil after section Q was seen. Nothing in this section changes
the calibration factors, the numbers module, the guide or any headline result. Script:
`triage/scripts/r_dose.py`; tables in `triage/out_final/r_*.csv`. Inputs: the final tables
(`data/runs/runs.duckdb`, read-only), `data/analysis/placebo_h3.parquet` (weeks 0–3, 463
pairs) and the reference tables. Colors and rarities are derived as in Q; `reference/raw/`
stays closed. No figures: tables for plotting are listed at the end.

**The reading under test (Q's, inferred, not shown).** When a patch changes some of a
character's cards, players re-evaluate the character, so its unchanged cards shift by a
lasting few pp, then settle over about a month. R tests two predictions: the shift grows with
how much changed (part 1), and it happens within the same players (part 2).

### Rules and what each outcome means, written before running

Written 2026-11-11, before any number of this section was computed. What I had looked at:
sections C, G, N, O, P and Q and their tables; runs per build and character; the kinds of
change in `change_events.csv`; the number of cards `window_changes` reports across three beta
boundaries (43, 19, 14); the count of runs with a token (321,588 of 1,993,497, 1,957 tokens).
No fit and no τ of this section had been run. Git is not attempted, as instructed; the order
rests on this note. Rules marked **(Phil)** are as given; **(mine)** marks what the prompt
left open.

**Shared tool (Phil).** τ per unit by maximum likelihood, β_i ~ Normal(μ, SE_i² + τ²), β in
pp, as in Q part 1 (`q_nudge.mle`), with a 95% interval from 2,000 resamples of pseudo cards.
Mine: when rows from several units are pooled, each unit has its own μ and a card's rows stay
together in a resample.

#### Part 1. Dose: shake against number of changes

- **Boundaries (Phil):** every consecutive pair of builds on the beta branch in `builds.csv`,
  plus Q's stable boundaries. A unit is used only if both sides have ≥ 3,000 runs of the
  character. A hotfix (released ≤ 3 days after the previous build on its branch) is merged
  into the build before it.
- **Design (Phil):** before = the older build's offers, after = the newer build's, each capped
  at its first 3 weeks from its release. Pseudo cards: the character's cards unchanged across
  the boundary (`window_changes`), up to 20 per unit, seed fixed, 51 offers in each block.
  Model and clustering as `placebo_fit`.
- **Unit (Phil):** character × boundary. **Dose:** the number of that character's cards with a
  substantive change across the boundary. Text-only and behavior (bug-fix) changes are counted
  and reported separately.
- **Test a (Phil):** units with dose 0 pooled against units with dose ≥ 1 pooled, τ with
  intervals. **Intervals don't overlap and dose ≥ 1 is larger = "changes drive the shake."
  Overlap = not shown.**
- **Test b (Phil):** Spearman of unit τ against dose over units with ≥ 15 placebo pairs,
  interval by resampling units. **Interval above 0 = "the shake grows with the number of
  changes."**
- **Limits (Phil):** beta players are a different population from stable players. Beta builds
  are short, so they sit in the unsettled stretch Q found: comparable to weeks 0–3, not to
  Q's late cuts. A beta change can be reverted before stable; `window_changes` uses each
  build's own card versions, so a reverted change counts at the boundary where it appears and
  again where it leaves.
- Mine:
  - **Merges.** By the 3-day rule: v0.99.0 into v0.99.0-beta (same day), v0.105.1 into
    v0.105.0, v0.106.1 into v0.106.0, v0.110.1 into v0.110.0 on beta; v0.98.2 into v0.98.1 on
    stable. v0.103.1 (6 days after v0.103.0), v0.109.1 (9 days) and v0.98.3 (4 days) stay
    separate. A merged build's release is its first member's date, and its 3 weeks run from
    there. v0.98.0 has no branch on file and is left out, not guessed.
  - **"Consecutive" is taken literally**, also where a unit fails the run count: no boundary
    skips over a dropped build. From the run counts I expect the early betas (v0.100.0 to
    v0.103.1, 300–3,200 runs a character) and v0.109.1 to fail for most characters.
  - **The run count is applied to the data the fit uses:** distinct runs of the character in
    each capped block. Whole-build counts are reported too.
  - **Blocks.** Offers started in [release, release + 21 days) of each side's build. Older-build
    play after the newer build's release stays in if it is inside the older build's 3 weeks,
    as in the main design. For a stable boundary this is the older build's *first* 3 weeks,
    not its last 3 as in Q, so R's stable rows are not Q's rows. The gap between the blocks'
    mean start times is recorded per unit, and τ against that gap is reported as a check on
    drift standing in for dose.
  - **Kinds.** For a card `window_changes` marks as changed, the events that differ between
    the two sides are looked up in `change_events.csv`. Substantive = any such event that is
    not a wording-only or excluded text change; this includes reworks, tweaks, cost and rarity
    changes, additions, removals, mechanic changes carried by text, and reverts. Text-only =
    only wording or excluded text events differ. A card marked changed because a version is
    unknown or a row is missing is counted as "unknown" and is not dose. Behavior = the
    second set `window_changes` returns. Only the character's own cards count; colorless
    cards and cards with no color on file are outside the dose.
  - **Test a's intervals** resample pseudo cards, as the shared tool says. Units also differ
    for reasons a card resample doesn't see (population, season), so a second interval
    resampling units is reported. It doesn't decide.
  - **Test b** uses τ's point estimate per unit; a unit's τ can be 0. Ties get average ranks.
  - **Card changes against release size (not asked, declared now, secondary).** Dose varies
    between characters at one boundary, where the days, the build and the population are the
    same. So: (i) Spearman of τ against dose with both taken as deviations from their
    boundary's mean, over boundaries with at least 2 units, interval by resampling units;
    (ii) Spearman of τ against the boundary's total dose over all five characters. If (i) is
    above 0, a character's own changes matter beyond the size of the release. If only (ii)
    is, the shake follows the release and not the character. Neither changes a or b.
  - Tests a and b are also reported for beta and stable units apart, descriptively, because
    dose 0 could otherwise stand in for "hotfix on stable".

#### Part 2. Same players before and after

- **Windows (Phil):** the 463 pairs' windows, weeks 0–3, the main design.
- **Subset (Phil):** runs of uploader tokens with offers in both blocks of the window. Tokens
  and offers per window are reported. Each pair is fit twice on the subset: (i) the standard
  model; (ii) the standard model plus a token × card fixed effect. τ per patch for each.
- **Rule (Phil): τ(ii) ≥ 0.75 × τ(i), with intervals, = "the shift happens within the same
  players" (re-evaluation). τ(ii) ≤ 0.5 × τ(i) = "mostly a change in who plays." Between =
  mixed.** The singleton drop under (ii) is reported; if it removes over half the offers, that
  is said next to the result.
- Mine:
  - A window is a character and its builds. A token is in the subset when it has at least one
    offer of that character's cards in the before block and one in the after block's weeks
    0–3. All its runs in the window are kept.
  - The ratio τ(ii) / τ(i) per patch decides by its point value. Its interval comes from one
    resample of cards applied to both fits. If the interval crosses 0.75 or 0.5, I name both
    outcomes it reaches.
  - Every pair is refit, whatever its offers on the subset; a pair that can't be fit is
    counted. τ is also given on pairs with ≥ 51 subset offers of the pseudo card in each block.
  - Beside the two: τ from the saved full-data fits of the same pairs, so the reader sees
    what taking the subset does before any fixed effect.
  - Errors stay clustered by run, as in `placebo_fit`.
  - **What (i) already does.** The subset holds the set of players fixed, so (i) on the subset
    against the full data is the first cut at "who plays". (ii) then removes what is left of
    it: a player with many runs after and few before weighs differently in the two blocks.
  - **Limits.** About 16% of runs carry a token, the key is missing on the older half of the
    pages, and token holders play far more than others (G1: about 39 runs each). The second
    window has few tokens on both sides (G1: 218). So a pass says the shift is within these
    players, not that it is within all players. And "within players" covers anything that
    changes for a player across the release, not only re-evaluation: the game outside the
    cards changed too.

#### Part 3. Descriptive asides (no rules)

- **a. Commons on the log-odds scale (Phil).** τ by rarity × patch on the 463 pairs, in pp and
  in log-odds (`to_log_odds`), with intervals.
- **b. Rarity tide (Phil).** The 463 pairs refit with a block × rarity fixed effect added
  (rarity derived as in Q). Robust sd of z and τ per patch next to 4.10 / 2.67. A post hoc
  model variant, not a candidate fix.
- **c. Offer sources (Phil).** For Q's 20-card offer-rate tail in the first patch: offers by
  source before and after, as shares, for those cards and for all other same-character cards;
  which source carries their rise.
- Mine: in b, every card in the fit gets its rarity, and a card with none is its own level.
  In c, the after block is weeks 0–3 as in Q part 2, and a card's rise is split by source into
  the change of its share within each source and the change of the sources' mix.

#### Addition after the rules: within-boundary contrast (Phil; descriptive, not declared)

Added by Phil after the rules above were written and before he had seen any R result. On my
side, when it arrived part 1's fits were still running and I had read no part 1 number; I had
read part 2's table. It has no rule and decides nothing.

For each boundary with at least one dose-0 unit and at least one dose ≥ 1 unit, both passing
the run rule: τ of its dose ≥ 1 units pooled minus τ of its dose-0 units pooled. Reported per
boundary, and as the mean over boundaries with an interval from resampling boundaries. Same
release, different exposure: a positive difference points to card changes, about zero to the
release as a whole. Mine: each side pools its units with a μ per unit, and each boundary's
difference also gets an interval from resampling cards. From the plan table, only two
boundaries qualify (v0.104.0 → v0.105.0 and v0.106.0 → v0.107.0, both beta), so an interval
from resampling two boundaries can take only three values and says little.

#### Runtime and resuming

Ten fits are timed before each part's full run and the estimate is written below. A part over
2 h gets a thinner design proposed here and is not run. Fits are saved as each unit or window
finishes, and the script skips what is saved, so a restart redoes nothing.

### Results

Everything below in section R was computed after the text above was written.

### Answer

**Neither prediction's dose half holds, and the within-players half does.** The shake does
not grow with the number of a character's changed cards: units with no change have τ 2.14 pp
[1.80, 2.33] and units with changes 1.94 [1.67, 2.08], the rank correlation of τ with dose is
+0.02 [−0.30, 0.33], and inside one boundary characters with changes shake no more than
characters without (differences −0.10 and −0.60 pp). The shift does happen within the same
players: holding each token's own taste for each card fixed leaves τ at 0.95 [0.85, 1.06] of
its value in the first patch and 0.79 [0.53, 1.05] in the second, on pairs with enough
offers. So Q's reading survives in part. Players do pick unchanged cards differently after a
release, and it isn't a change in who plays. But what sets the size is not how many of the
character's cards changed. It follows the release as a whole and the time between the
blocks: beta builds shake by about 1.0–1.7 pp whatever they change, the two stable major
updates by 3.2 and 2.2 pp, and a stable boundary with no card change but 44 days between its
blocks by 2.7 pp. The factors stay as they are. [inferred]

### Declared outcomes [computed]

| Test | Result | Outcome under the rule |
|---|---|---|
| 1a. Dose 0 against dose ≥ 1 | τ 2.14 [1.80, 2.33] (19 units) against 1.94 [1.67, 2.08] (34 units) | **Not shown**: the intervals overlap, and dose ≥ 1 is not larger |
| 1b. τ against dose | Spearman +0.02 [−0.30, 0.33], 53 units | **Not shown**: the interval holds 0 |
| 2. Same players | τ(ii)/τ(i): first 2.21 [0.87, 3.69], second 0.81 [0.52, 1.08] | **Within the same players** in both, by the point value. The first patch's figure is one bad fit (see part 2); the second's interval reaches into "mixed" and stays above 0.5 |

### Checks and changes after the rules [computed]

- **Timing before each run.** Part 1: 2.7 s per fit on the largest unit, at most 54 minutes
  for 53 units. Part 2: 1.5 s per fit, about 24 minutes for 926 fits. Part 3b: 4.0 s per fit,
  about 32 minutes for 463. All under 2 h, so no design was thinned. The three ran at the
  same time and took 32, 8 and 24 minutes.
- **Saved fits and resuming.** Each part appends its fits to `r_dose_fits.csv`,
  `r_token_fits.csv` or `r_rarity_fits.csv` as a unit or window finishes, and a rerun skips
  what is there. Every table below was rebuilt from those files with `--analyze`, which is
  the same path a restart takes. The runs were not interrupted. To check the skip, parts 2
  and 3 were run again without flags after they had finished: they refit nothing (9 s and
  12 s), left the fit files at 926 and 463 rows, and returned the same tables. A restart in
  the middle of a unit or window redoes that one unit or window.
- The loader, fit and likelihood are Q's (`q_nudge.py`), which passed its gate there.
- Fits: 1,060 in part 1, none failed. Part 2: 926, of which 5 failed, all under model (ii) on
  upgraded-offers pairs where the token × card effects leave nothing to estimate; 458 of 463
  pairs are usable under both models. Part 3b: 463, none failed.
- **Two additions after the rules.** Phil's within-boundary contrast, recorded in the rules
  section with when it arrived. And one post hoc table of mine, τ per boundary beside its gap
  and dose, added after reading the tests.
- A slip to correct: my status note said "53 of 105 units". There are 20 boundaries and 100
  units; 53 are used.
- Tests: `pytest tests` gives 266 passed, 4 skipped. The other 47 (27 failed, 20 errors) are
  all `PermissionError` on `reference/raw/`, closed by the sandbox, the same 47 as before
  this section.
- Git was not attempted, as instructed.

### Part 1. Dose [computed]

Tables: `r_plan.csv` (all 100 units with run counts, dose, the other change counts, and why a
unit is dropped), `r_units.csv`, `r_dose_fits.csv` (1,060 fits), `r_unit_tau.csv` (τ per unit),
`r_dose_tests.csv`, `r_within_boundary.csv`, `r_posthoc_boundary.csv`.

**Units.** 15 beta boundaries and 5 stable ones after the merges, 100 character × boundary
units. 53 pass the run rule: 28 beta, 25 stable. Dropped, 47: every character at nine beta
boundaries (the early betas through v0.103.1 → v0.104.0, where one side has 0 to 3,145 runs,
and both boundaries of v0.109.1), and Necrobinder and Regent at v0.108.0 → v0.109.0 (2,949
and 2,869 runs). Of the 53, 19 have dose 0: fifteen stable (the two launch boundaries and
v0.103.2 → v0.103.3) and four beta. Text-only changes occur in 7 used units, 6 of them at the
two major updates. Every used unit gave 20 pairs.

**Tests.** τ in pp. For a, the first interval resamples cards and the second resamples units.

| Test | Scope | Group | Units | Estimate [95%] | Resampling units |
|---|---|---|---|---|---|
| a | **All units [rule]** | Dose 0 | 19 | **2.14 [1.80, 2.33]** | [1.75, 2.52] |
| a | **All units [rule]** | Dose ≥ 1 | 34 | **1.94 [1.67, 2.08]** | [1.57, 2.25] |
| b | **All units [rule]** | Spearman, τ against dose | 53 | **+0.02 [−0.30, 0.33]** | |
| a | Beta | Dose 0 | 4 | 1.61 [0.87, 2.08] | [0.95, 1.97] |
| a | Beta | Dose ≥ 1 | 24 | 1.28 [1.02, 1.39] | [1.08, 1.49] |
| b | Beta | Spearman, τ against dose | 28 | −0.05 [−0.42, 0.37] | |
| a | Stable | Dose 0 | 15 | 2.25 [1.87, 2.46] | [1.79, 2.66] |
| a | Stable | Dose ≥ 1 | 10 | 2.73 [2.27, 3.02] | [2.26, 3.16] |
| b | Stable | Spearman, τ against dose | 25 | +0.40 [0.01, 0.72] | |
| secondary | All | Spearman, τ against dose, both as deviations from the boundary's mean | 38 | +0.06 [−0.28, 0.38] | |
| secondary | All | Spearman, τ against the boundary's total dose | 53 | +0.05 [−0.27, 0.36] | |
| check | All | Spearman, τ against the gap between blocks | 53 | **+0.40 [0.11, 0.63]** | |
| check | All | Spearman, τ against text-only changes | 53 | +0.39 [0.20, 0.56] | |

**Within-boundary contrast (Phil's addition; descriptive).** Two boundaries qualify.

| Boundary | Dose-0 units | Dose ≥ 1 units (dose) | τ, dose 0 [95%] | τ, dose ≥ 1 [95%] | Difference [95%, cards] |
|---|---|---|---|---|---|
| v0.104.0 → v0.105.0 | Ironclad, Necrobinder | Defect (4), Regent (5), Silent (1) | 1.42 [0.00, 2.27] | 1.32 [0.74, 1.64] | −0.10 [−1.10, +1.32] |
| v0.106.0 → v0.107.0 | Defect, Silent | Ironclad (1), Necrobinder (2), Regent (2) | 1.76 [0.85, 2.27] | 1.15 [0.47, 1.55] | −0.60 [−1.45, +0.33] |
| Mean over the 2 | | | | | −0.35 [−0.60, −0.10] resampling boundaries |

The last interval can only take three values and isn't a measure of uncertainty; the two
card-resampling intervals are, and both hold 0.

**τ per boundary, post hoc** (units pooled, a μ per unit).

| Boundary | Branch | Units | Unit doses | Total dose | Gap (days) | τ [95%] | Robust sd z | Median SE |
|---|---|---|---|---|---|---|---|---|
| v0.104.0 → v0.105.0 | beta | 5 | 0 0 1 4 5 | 10 | 14 | 1.36 [0.84, 1.77] | 1.37 | 1.40 |
| v0.105.0 → v0.106.0 | beta | 5 | 2 3 3 3 3 | 14 | 14 | 1.18 [0.68, 1.51] | 1.47 | 1.25 |
| v0.106.0 → v0.107.0 | beta | 5 | 0 0 1 2 2 | 5 | 14 | 1.42 [0.87, 1.71] | 1.56 | 1.19 |
| v0.107.0 → v0.108.0 | beta | 5 | 3 5 5 5 5 | 23 | 28 | 1.75 [1.26, 2.06] | 1.60 | 1.41 |
| v0.108.0 → v0.109.0 | beta | 3 | 3 5 7 | 18 | 12 | 1.10 [0.00, 1.54] | 1.45 | 1.63 |
| v0.110.0 → v0.111.0 | beta | 5 | 2 2 3 4 4 | 15 | 17 | 1.00 [0.35, 1.28] | 1.32 | 1.35 |
| v0.98.1 → v0.98.3 | stable | 5 | all 0 | 0 | 6 | 2.57 [1.91, 3.05] | 2.37 | 1.22 |
| v0.98.3 → v0.99.1 | stable | 5 | all 0 | 0 | 13 | 1.27 [0.96, 1.45] | 2.01 | 1.01 |
| v0.99.1 → v0.103.2 | stable | 5 | 3 10 12 14 24 | 63 | 29 | 3.17 [2.50, 3.62] | 3.22 | 0.93 |
| v0.103.2 → v0.103.3 | stable | 5 | all 0 | 0 | 44 | 2.69 [2.14, 3.05] | 3.28 | 1.02 |
| v0.103.3 → v0.107.1 | stable | 5 | 4 6 6 6 13 | 35 | 19 | 2.20 [1.74, 2.51] | 2.26 | 0.94 |

Reading. [inferred]
- **Rule a: not shown. Rule b: not shown.** Units with changes don't shake more than units
  without, and τ doesn't rise with dose. The same holds inside a boundary, by the declared
  secondary (+0.06) and by Phil's contrast (both differences below 0, both intervals holding
  0). Same release, different exposure, no difference: that points to the release as a whole.
- **The dose-0 group is not a quiet group, and that limits rule a.** Fifteen of its 19 units
  are stable: ten from the game's first twelve days, and five from v0.103.2 → v0.103.3, whose
  blocks under this design are v0.103.2's first three weeks and v0.103.3's, 44 days apart.
  The four beta dose-0 units are the clean ones and they are few. So a is weaker evidence
  than b and the within-boundary contrasts, which don't lean on that group.
- **Beta builds barely shake, whatever they change.** Six beta boundaries with 5 to 23 changed
  cards give τ of 1.0 to 1.75 pp, about what Q found at cuts *inside* a stable build three to
  four weeks after a release (1.2 to 1.9). Among beta units the correlation with dose is
  −0.05. The highest beta boundary is also the one with the longest gap (28 days).
- **Time between the blocks matters as much as anything measured here.** τ rises with the
  gap (+0.40, interval clear of 0). The boundary with no card change and a 44-day gap is at
  2.69 pp; Q measured the same boundary with v0.103.2's *last* three weeks as the before
  block and got 1.2. The difference is where the before block sits: R's is the three weeks
  right after a major update. So cards kept moving for weeks after v0.103.2 came out, by an
  amount comparable to the step at its release (3.17). That is Q's settling, larger than Q's
  "about a month, then flat" suggested. One build shows it.
- **The stable-only correlation (+0.40) is the two major updates against the rest**, and R
  still can't separate "many cards changed" from "major update": every unit with a dose
  above 7 is in v0.99.1 → v0.103.2 or v0.103.3 → v0.107.1. Inside v0.99.1 → v0.103.2 the five
  characters do line up (doses 3, 10, 12, 14, 24 with τ 1.9, 3.4, 3.0, 3.5, 3.7); inside
  v0.103.3 → v0.107.1 they don't (4, 6, 6, 6, 13 with 1.7, 2.0, 2.9, 1.5, 2.5). That is
  post hoc and five units each.
- The correlation with text-only changes (+0.39) is the same thing by another name: 6 of the
  7 units with a text-only change are at the two major updates.
- As declared: beta players are another population, and a beta change that ships later on
  stable has already been seen by them. So "beta changes don't shake beta players" does not
  show that the same changes wouldn't shake stable players arriving at a major update.

### Part 2. Same players before and after [computed]

Tables: `r_token_windows.csv`, `r_token_fits.csv` (926 fits), `r_token_tau.csv`.

**Subset.** Tokens with offers in both blocks of the window:

| Window | Tokens with any offer | Tokens on both sides | Runs in the subset | Offers in the subset | Share of the window's offers |
|---|---|---|---|---|---|
| Silent, first | 625 | 262 | 5,300 | 195,939 | 12.4% |
| Regent, first | 584 | 240 | 5,087 | 177,146 | 12.8% |
| Necrobinder, first | 606 | 254 | 5,137 | 183,065 | 13.8% |
| Ironclad, first | 601 | 261 | 5,869 | 214,879 | 13.0% |
| Regent, second | 344 | 97 | 1,608 | 58,948 | 5.4% |
| Necrobinder, second | 367 | 100 | 1,874 | 66,466 | 5.6% |
| Defect, second | 324 | 87 | 1,545 | 61,168 | 5.0% |
| Ironclad, second | 358 | 105 | 1,692 | 62,957 | 4.1% |
| Silent, second | 368 | 110 | 2,000 | 72,524 | 4.9% |

**τ per patch**, pp. "Saved" is the full-data fit of the same pairs.

| Pairs | Patch | n | τ saved [95%] | τ (i), subset [95%] | τ (ii), + token × card [95%] | τ(ii)/τ(i) [95%] | Median SE: saved, (i), (ii) | Singleton drop, (ii) |
|---|---|---|---|---|---|---|---|---|
| **All fit under both [rule]** | first | 216 | 3.35 [2.95, 3.72] | 3.60 [3.10, 4.06] | 7.95 [3.00, 12.62] | **2.21 [0.87, 3.69]** | 0.82, 2.30, 2.62 | 1.4% |
| **All fit under both [rule]** | second | 242 | 2.44 [2.15, 2.72] | 3.09 [2.33, 3.73] | 2.49 [1.41, 3.41] | **0.81 [0.52, 1.08]** | 0.94, 4.01, 4.33 | 1.9% |
| ≥ 51 subset offers in each block | first | 209 | 3.35 [2.93, 3.71] | 3.60 [3.08, 4.02] | 3.41 [2.86, 3.94] | 0.95 [0.85, 1.06] | 0.81, 2.28, 2.57 | 1.3% |
| ≥ 51 subset offers in each block | second | 214 | 2.45 [2.15, 2.71] | 3.03 [2.27, 3.64] | 2.40 [1.43, 3.24] | 0.79 [0.53, 1.05] | 0.90, 3.84, 4.21 | 1.6% |

β under (i) and (ii) correlate at 0.79 (first) and 0.67 (second) on the ≥ 51 pairs.

Reading. [inferred]
- **Rule: within the same players, in both patches.** The singleton drop is under 2% of
  offers, nowhere near half.
- **The first patch's 2.21 is not a real ratio.** One upgraded-offers pair with 17 and 8
  subset offers returns β = +99 pp with an SE of 2.4 pp under (ii), a z of 42, and the normal
  likelihood stretches τ to cover it. With pairs under 51 subset offers set aside (7 in the
  first patch, 28 in the second, all upgraded-offers fits), the ratio is 0.95 [0.85, 1.06].
  That subset was declared before running, and it is the figure to read.
- **The second patch passes by the point value and not by its interval.** 0.79 [0.53, 1.05]
  reaches into "mixed". It has under half the tokens of the first patch and SEs of 4 pp
  against a τ of 2.4 to 3.0, so it is imprecise. It stays above 0.5, so "mostly a change in
  who plays" is out for it too.
- **Fixing who plays removes nothing.** τ on the both-sides subset is no smaller than on the
  full data (3.60 against 3.35; 3.09 against 2.44), and fixing each player's taste for each
  card takes off 5% in the first patch. A change in the population can't be what moves the
  unchanged cards, among players with a token.
- As declared, these are token holders, about one run in eight in the first window and one
  in twenty in the second, and heavy players. And "within players" doesn't say what changed
  for them: their view of the character, or the game around the cards.

### Part 3. Descriptive asides [computed]

Tables: `r_rarity_tau.csv`, `r_rarity_fits.csv` (463 refits), `r_rarity_tide.csv`,
`r_offer_sources.csv` (per character, source and group, and per tail card).

**a. τ by rarity and patch.**

| Patch | Rarity | Pairs | Median rate before | τ, pp [95%] | τ, log-odds [95%] | Robust sd z |
|---|---|---|---|---|---|---|
| first | Common | 49 | 0.20 | 2.84 [2.04, 3.39] | 0.176 [0.128, 0.210] | 5.80 |
| first | Uncommon | 102 | 0.28 | 3.70 [3.09, 4.31] | 0.196 [0.160, 0.236] | 4.64 |
| first | Rare | 66 | 0.37 | 2.96 [2.40, 3.47] | 0.142 [0.116, 0.167] | 2.91 |
| second | Common | 62 | 0.23 | 1.91 [1.41, 2.29] | 0.111 [0.085, 0.132] | 3.02 |
| second | Uncommon | 111 | 0.28 | 2.62 [2.20, 3.01] | 0.142 [0.116, 0.171] | 3.21 |
| second | Rare | 73 | 0.35 | 2.55 [1.98, 3.04] | 0.131 [0.099, 0.159] | 1.94 |

In pp Commons have the smallest τ in both patches, as Q found. **On log-odds that holds only
in the second patch, and not clearly.** In the first patch Rares are lowest (0.142) and
Commons sit between Rares and Uncommons; in the second Commons are lowest (0.111 against
0.131 and 0.142) with overlapping intervals. Commons are picked least often, so part of
their tight pp spread is a low base rate. Rarity is the offer tier where not on file.

**b. Rarity tide.** The 463 pairs refit with a block × rarity fixed effect.

| Patch | Factor | Robust sd, saved | With block × rarity [95%] | τ saved | τ with block × rarity [95%] | Mean z of Commons: saved → with |
|---|---|---|---|---|---|---|
| First | 4.10 | 4.10 | 4.16 [3.46, 4.74] | 3.35 | 3.38 [2.96, 3.76] | −0.14 → −0.22 |
| Second | 2.67 | 2.67 | 2.85 [2.31, 3.19] | 2.44 | 2.47 [2.15, 2.76] | −0.55 → +0.20 |

A shift shared by a rarity is not part of the spread: nothing is absorbed. The second
patch's downward lean of Commons (Q's aside) goes away, as it should, and the width stays.
A post hoc model variant, not a candidate fix.

**c. Offer sources for the first patch's 20-card offer-rate tail.** The cards' share of their
character's offers, v0.99.1 against v0.103.2 weeks 0–3, split by source. "Within source" is
the log ratio of the cards' share of that source's offers.

| Character | Tail cards' share of offers: before → after | Combat: within source, part of the rise | Elite: within source, part of the rise | Boss: within source, part of the rise | Sources' mix |
|---|---|---|---|---|---|
| Ironclad (4 cards) | 4.4% → 5.0% | +0.14, 72% | +0.12, 27% | no offers before | about 0 |
| Necrobinder (6) | 5.9% → 6.6% | +0.10, 69% | +0.10, 26% | +0.11, 5% | about 0 |
| Regent (5) | 3.7% → 4.1% | +0.10, 56% | +0.07, 29% | +0.23, 15% | about 0 |
| Silent (5) | 3.4% → 3.9% | +0.15, 70% | +0.09, 22% | +0.11, 8% | about 0 |

**No one source carries the rise.** The cards' share goes up within combat, elite and boss
rewards alike, and the mix of sources barely moves. Combat holds most of the rise because it
holds most of the offers (70–77% of these cards'). Event-combat offers are under 1% and
change nothing. So the tail isn't one kind of reward screen changing; these cards became
more likely to be offered everywhere. [computed; the last sentence is inferred]

### What this does and doesn't settle

- **Settled, within limits:**
  - Among players with a token, the shift in unchanged cards happens within the same
    players. It is not a change in who plays.
  - The shake does not scale with the number of a character's changed cards, across units or
    inside a boundary, over the range R can see (0 to 7 on beta, where it can be separated
    from release size).
  - A rarity-wide shift is not part of the spread.
  - The offer-rate tail is not tied to a reward source.
- **Fits but not shown:** the shake belongs to major stable updates and to the weeks that
  follow them. Beta builds with up to 23 changed cards shake about as little as a quiet week
  inside a stable build; the two major updates shake most; and v0.103.2's cards moved as
  much over its first six weeks as at its release. Two major updates, and one build with a
  long gap.
- **Not settled:**
  - Card changes against release size at the scale of a major update. All units with more
    than 7 changed cards are in the two major updates, so R leaves this where Q did. The
    line added to SPIROMETRY.md, "(triage R tests this)", is answered only for small doses.
  - Whether beta players' calm is about beta players or about beta builds. They are a
    different population and have often seen a change before it counts as new.
  - What changes for a player at a major update: the character's cards, the rest of the game,
    or simply returning after a break. Part 2 can't tell these apart.
  - Why the second patch's within-player ratio is lower (0.79). It is within its own noise.
- The factors are unaffected: they measure the spread and don't depend on its cause.

### Update to SPIROMETRY.md, open question 8 (applied 2026-11-11, at Phil's direction)

This section proposed replacing "(triage R tests this)" with "(triage R: not separated at
that scale)" and adding the line below before "Not yet verified." Phil had the line applied
and asked for more: Q's passage there now says the v0.103.3 boundary's 1.2 pp was measured
late in v0.103.2 and that this section gets 2.69 pp from its first three weeks, so it no
longer supports "releases that change cards"; the clause is replaced by what this section
found; Q's leading reading gives way to the one in the line below; and a sentence marked
inferred is added, that the pattern is consistent with each card's pick rate wandering like
a random walk relative to its character, faster for about a month after a major update.

> Dose and same players, exploratory (triage R, final tables): the shift is within the same
> players (token × card effects keep 0.95 [0.85, 1.06] and 0.79 [0.53, 1.05] of τ), but it
> does not grow with the number of a character's changed cards (dose 0: τ 2.14 pp, dose ≥ 1:
> 1.94; Spearman +0.02 [−0.30, 0.33]; no difference inside a boundary); beta builds shake by
> 1.0–1.7 pp whatever they change, and τ rises with the time between blocks, so the leading
> reading becomes: players pick differently after a major update as a whole and keep
> adjusting for weeks, rather than re-evaluating a character in proportion to its changes.

### Privacy check, files and runtime

- **Privacy check, clean.** All 14 `triage/out_final/r_*.csv` tables: no column name matches
  uploader, player, run_key, run_hash, screen_id, hash, steam or start_time. The 1,450
  distinct non-numeric values were scanned for hex strings of 12 or more characters,
  pipe-joined keys and long strings; the one long value is a pyfixest error message
  ("All variables are collinear…") in `r_token_fits.csv`, which holds no identifier. Text
  columns hold card ids, card-patch ids, characters, rarities, build and boundary labels,
  dates, sources and summary labels. Uploaders appear only as counts (`n_tokens_any`,
  `n_tokens_both`, `pseudo_tokens`, `median_pseudo_tokens`). `r_dose.py` uses
  `uploader_hash` and `run_key` in memory, for the subset, the fixed effect and distinct
  counts, and prints or writes neither.
- **Files to commit:** `triage/TRIAGE.md`, `triage/scripts/r_dose.py`, `README.md`,
  `PLAN.md`, and `triage/out_final/`: `r_plan.csv`, `r_units.csv`, `r_dose_fits.csv`,
  `r_unit_tau.csv`, `r_dose_tests.csv`, `r_within_boundary.csv`, `r_posthoc_boundary.csv`,
  `r_token_windows.csv`, `r_token_fits.csv`, `r_token_tau.csv`, `r_rarity_tau.csv`,
  `r_rarity_fits.csv`, `r_rarity_tide.csv`, `r_offer_sources.csv`. These are also the
  tables for plotting; no figure was made. `SPIROMETRY.md` (open question 8) was updated
  afterwards, so it belongs in the commit too.
- **Runtime:** part 1 32 minutes (peak memory 5.0 GB), part 2 8 minutes (2.2 GB), part 3 24
  minutes (3.1 GB), run at the same time; rebuilding part 1's tables from saved fits 1
  minute; the three timing runs about 1, 0.5 and 1 minute.
