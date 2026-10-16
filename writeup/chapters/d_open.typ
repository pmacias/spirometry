#import "../style.typ": *

= Still open, or not yet verified <app-open>

Everything SPIROMETRY.md and PLAN.md mark as open, unverified or not run, with the chapter
where it matters. Nothing here changes a number in the guide; each item limits how far one
of them can be pushed.

== Not yet verified

- *Why the placebo spread of the DiD z's is so large* (SPIROMETRY.md, open question). Card by
  card and persistent; clustering by player token narrows it but not to honest size. The
  calibration in @ch-placebo corrects for it on average without explaining it.
- *Whether the player token is opt-in* (SPIROMETRY.md, known issues). Matters for how far the
  token runs of @ch-explanations represent their upload route.
- *Two wins that looked impossible* on an earlier audit (a huge gold total, an empty deck):
  not rechecked on the final tables (@ch-data). Wins are flagged, not filtered, and win
  analyses are future work.
- *v0.110.0’s pooling with v0.110.1* (@ch-data): by the rule it pools, but the patch notes were
  not checked. Both builds come after the last stable window.
- *When in the run cards are picked*: measured on early tables only, not used (@ch-checks).
- *The snapshot's start date in the download log*: not in the part of the log checked, left
  blank. The play-date range comes from the runs.

== Open

- *Why the second patch moved choices so much less than the first* (@ch-dose, @ch-explanations,
  @ch-open). The project's main open question.
- *Why Patter and Sculpting Strike were offered more after the first patch* (@ch-checks). Not a
  rarity pool change.
- *The negative upgrade-only placebos* on Royalties and Untouchable v0.107.1 (@ch-checks).
  Drift in the second patch's before block is the first candidate.
- *Measurement error in partial-coverage doses* (@ch-rulers): points the right way to explain
  part of the flatness; no better measurement exists to test it.
- *Ascension as one baseline per level, or in bands* (PLAN item 14; @ch-regression).
- *How many heavy uploaders the robustness check should drop* (ten now; PLAN item 14).
- *The shape of each informative tweak's weekly gap at its first-beta date* (step, ramp or
  drift): not yet recorded (PLAN item 14; @ch-checks).
- *Whether the win fits should include the mix of early screen types* (an early elite offers
  rarer cards): off by default, undecided (@ch-wins).
- *The real-data balance check for the offer instrument*: not run (@ch-wins).

== Not run, or future work

- *Real win effects*: the power check (PLAN item 15, task 9), the per-card win effects, the
  strength change across patches (step 5) and perception against strength (step 6)
  (@ch-wins).
- *Partial pooling* (step 7), *the staggered rollout* (step 8) and *reworks* (step 9)
  (@ch-open).
- *The stayers-only token fit* and *the pre-declared aggregates on the final tables*
  (@ch-explanations; the aggregates were measured on the earlier
  #n("const.earlier_tables.pages")-page tables only).
- *Where the flagged cards' extra offers come from* (by act and floor type): not planned; a
  caveat.
- *Card-by-act baselines*: not planned; offer timing balanced between blocks (@ch-checks).
- *The minimum-runs threshold from a power calculation*: not planned; the windows are fixed.
- *The dashboard, the release checklist and publishing* (@ch-open).
- *Per-build lists for the mod-content rule*, needed when new official content ships.
