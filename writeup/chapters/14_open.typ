#import "../style.typ": *

= What is settled, what is open, what could come next <ch-open>

#lead[What the project concludes, how far to trust it, and what is still unknown.]

== Conclusion

*What the numbers show.*

+ *The first balance patch moved pick rates the way it meant to, and in proportion.* Over the
  first four weeks, #n("did.h3.first.calibrated.clearly_nonzero") of #n("tweaks.first") numeric
  tweaks moved picks clearly once the error bars are corrected (@ch-placebo), and every one of
  them with a single direction moved toward its change. The typical effect was
  #n("did.h3.first.median_abs_beta_pp") percentage points, the largest more than ten. Bigger
  changes moved picks more: #n("dose.primary.h3.slope_first_pm") log-odds per unit of
  ln(new/old).
+ *The second balance patch, with tweaks of the same sizes, did not.* #n("did.h3.second.calibrated.clearly_nonzero")
  of #n("tweaks.second") tweaks moved picks clearly; the typical effect was
  #n("did.h3.second.median_abs_beta_pp") points; the dose-response slope was
  #n("dose.primary.h3.slope_second_pm"). As a group, its effects were as spread out as those of a
  fake patch in which nothing changed (sd #n("checks.fake_patch.h3.sd_real") log-odds for the
  real effects, #n("checks.fake_patch.h3.sd_fake") for the fake ones).
+ *The two patches differ.* The slopes differ by #n("dose.primary.h3.z_diff") SEs, or
  #n("dose.primary.h3.placebo_robust_sd.z_diff") with placebo-scaled errors. The difference
  holds with other characters' cards as controls, in each uploader group, and among token runs
  within players.
+ *The model's error bars are too small.* Unchanged cards come out "clearly nonzero" in
  #n("placebo.pairs.all.share_abs_z_gt2") of placebo fits instead of
  #n("const.honest.share_abs_z_gt2"), so the clustered SEs need widening by a factor of
  #n("did.h3.first.calibrated.factor") in the first patch and
  #n("did.h3.second.calibrated.factor") in the second (weeks 0–3).

*How much to trust it, and why.*

- The first patch's results are the most solid part of the project. They survive the
  corrected error bars, the design checks, the regression-to-the-mean test and every
  sensitivity variant. Its slope is somewhat overstated by spillover between same-character
  cards: with other characters' controls it is #n("checks.control_scope.other.primary.slope_first_pm").
- The second patch's flatness is real in the sense that a first-patch-sized response would
  almost always have been seen (#n("power.primary.honest.planted_1_44.power_slope_second") in the
  power simulation). It is not proof of no response: a slope half as large would be seen only
  #n("power.primary.honest.planted_0_7.power_slope_second") of the time.
- The difference between the patches depends on two measurement choices. On the absolute ruler
  it disappears (z diff #n("rulers.primary.absolute.z_diff")), and the calls on two
  hard-to-measure tweaks move it between #n("rulers.reflect_off_debilitate_off.ln.z_diff") and
  #n("rulers.primary_debilitate_table_dose.ln.z_diff"). It also leans on the character with the
  most tweaks: without Regent's cards it is #n("leave_out.primary.regent.z_diff").
- For any single card, the honest guide is its calibrated z. The calibration is an average
  correction for an error whose cause is #unverified[not yet verified].
- None of this says anything about whether the cards became stronger. Win effects are future
  work.

The short version: in April, players followed the patch notes in proportion to the size of
each change; in June, with changes of the same sizes, they barely moved, and why is open.

#skill[
  *Stating a conclusion at the strength the evidence allows.* Lead with what was measured,
  then say what each caveat does to it, using the same numbers. Don't round a "much less" up
  to "nothing" or down to "the same".
]

#check(
  ([State the project's conclusion in two sentences, with one number each.],
   [In the first patch, pick rates moved toward each change and in proportion to its size
    (slope #n("dose.primary.h3.slope_first_pm")). In the second patch, tweaks of the same sizes
    moved picks about as much as no change (slope #n("dose.primary.h3.slope_second_pm")).]),
  ([Name two things the patch difference depends on.],
   [The ruler (it disappears on the absolute ruler) and the calls on Debilitate and Reflect; it
    also leans on Regent's cards.]),
  ([What can't the project say about card strength, and why?],
   [Whether the patched cards became stronger or weaker for winning: the win-effect estimates
    on real data were not run.]),
)

== Still open

These are the questions the project raised and did not answer. Appendix D lists every open or
unverified item with where it comes from.

- *Why the second patch moved choices so much less.* Candidates, none tested: a settled meta
  and more experienced players by June; the kinds of number the second patch changed (several
  are power amounts or Forge, and more of its doses depend on the game state, like a debuff's
  length); measurement error in those doses; players responding less to patch notes.
- *Why the clustered error bars are too small.* The placebo spread is card by card and
  persists across patches; clustering by player helps only a little. A card-level drift
  shared across players is the leading candidate, #unverified[not verified].
- *Why Patter and Sculpting Strike were offered more after the first patch.* Not a rarity
  pool change; something specific to the two cards.
- *The negative upgrade-only placebos* (Royalties, Untouchable v0.107.1). Drift in the second
  patch's thin before block is the first candidate.
- *Which informative tweaks show a step, a ramp or a drift at their first-beta date.* Not yet
  recorded.
- *Ascension as one baseline per level or in bands*, and whether any estimate depends on it.

#skill[
  *Keeping an honest list of open questions.* Write each one with its best candidate answer
  and the test that would settle it, so that the list is a plan, not a confession.
]

#check(
  ([Name three questions this project leaves open.],
   [Any three of: why the second patch did less; why the error bars are too small; why Patter
    and Sculpting Strike were offered more; the negative upgrade-only placebos; the
    first-beta-date shapes; ascension banding.]),
  ([For the error-bar question, what is the leading candidate and how would you test it?],
   [Card-level drift shared across players; a model that lets each card's level drift from
    week to week, refit on the placebos, would show whether the spread falls to honest
    size.]),
  ([Why list candidate answers beside open questions?],
   [It turns the list into next steps and shows the questions were thought through, not
    abandoned.]),
)

== Future work

#words[
  - *Partial pooling (hierarchical Bayes)*: estimating all cards together so that each
    card's noisy estimate is pulled toward the group, more for cards with little data.
  - *Staggered rollout*: changes reach the beta branch weeks before stable, so the same
    change starts at two different dates for two populations, a second experiment.
  - *Perception against strength*: comparing how much a patch moved picks with how much it
    moved a card's effect on winning, to see whether players over- or under-react.
]

#picture[
  Early in a baseball season a player who has batted ten times might be hitting at a
  ridiculous rate. Nobody believes it; you mentally pull it toward the league average,
  less so as the season goes on. Partial pooling does that pulling, by an amount the data
  decide.
]

The project ends with this guide (decision of October 2026). In order of what would teach the
most:

+ *Model the card-level drift* that makes the error bars too small, and refit the placebos
  with it. It is the one fix that would sharpen every per-card number.
+ *Partial pooling* of the per-card effects, the planned answer to many comparisons (@ch-noise)
  and to rarely offered cards.
+ *The win-effect power check*, then real win effects (@ch-wins), then the strength change
  across patches and perception against strength, if the power check passes.
+ *The staggered rollout*: beta players got each change weeks earlier, and every stable build
  ran beside betas with tens of thousands of runs, so the design is feasible on volume.
+ *A stayers-only fit* (players seen on both sides of each release), the cleanest test of a
  population change.
+ *Reworks*, with before-and-after estimates reported apart from the dose-response.
+ *The dashboard and publishing*, after the release checklist (aggregates only, attribution of
  the cached reference data, a message to the data's maintainer).

#watch[
  "Future work" is honest only if the current results don't depend on it. Here they don't:
  every number in this guide stands without the items above, with the caveats stated.
]

#skill[
  *Ranking next steps by what they would change.* Order future work by how many conclusions it
  would sharpen, not by how interesting it is.
]

#check(
  ([What is partial pooling, and which problem in this project would it address?],
   [Estimating all cards together and pulling each noisy estimate toward the group; it
    addresses many comparisons and extreme estimates for rarely offered cards.]),
  ([Why is the staggered rollout a second experiment?],
   [The same change reached beta players weeks before stable players, so it starts at two
    dates for two populations, and each can serve as a comparison for the other.]),
  ([Which future step would you do first, and why?],
   [Modelling the card-level drift behind the too-small error bars, because it would sharpen
    every per-card result; or the win-effect power check, because it decides whether the
    strength question can be answered at all.]),
)
