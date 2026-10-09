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
build (commit 09aa195 "Rebuild pipeline and re-run notebooks"). SPIROMETRY.md "Phase 5
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
