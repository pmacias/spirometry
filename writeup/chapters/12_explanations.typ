#import "../style.typ": *

= Is it the design? Power, drift, controls and players <ch-explanations>

#lead[Could low power, a drifting before block, the choice of controls, or a change in who
  plays explain the flat second patch?]

@ch-rulers asked whether the second patch looks flat because of how doses were measured, and
found that the difference holds on every reasonable proportional ruler. This chapter asks the
same question of the design: each section names one explanation that would make the second
patch's flatness an artefact, and tests it.

Most of these tests come from the triage, an investigation run in October 2026 on the earlier
#n("const.earlier_tables.pages")-page run tables. The fake patch, the regression-to-the-mean
checks, the token subset, the control-scope fits and the per-group lines were rerun on the
final tables, and every number below from those checks is a final-table number. Between the
earlier tables and the final ones, no main estimate (no tweak's effect and no dose-response
coefficient) moved by more than one standard error. Two parts of the triage were not rerun,
and are labelled where they appear.

== Power by simulation

#words[
  - *Statistical power*: the chance that a study detects an effect of a given size if it is
    really there.
  - *Simulation*: answering a question by generating fake data many times from a known truth
    and running the real analysis on each copy.
]

#picture[
  A metal detector's sensitivity. If it beeps for a coin at arm's length only one time in
  three, silence over a patch of beach doesn't mean the beach is empty. Before reading
  "nothing found" as "nothing there", you check how often the detector finds a coin that you
  buried yourself.
]

The power simulation keeps the first patch's points as they are, replaces each second-patch
point with a fake one drawn from a line with a planted slope (using that tweak's real dose,
real SE and the real scatter between cards), refits the same model, and counts how often the
second slope is detected. It does this a thousand times for each planted slope, with fixed
settings chosen before it ran.

#project[
  *Your data* (primary spec, honest SEs as the model reports them). A second-patch slope as
  large as the first patch's is detected
  #n("power.primary.honest.planted_1_44.power_slope_second") of the time. Half that size:
  #n("power.primary.honest.planted_0_7.power_slope_second"). A fifth of it:
  #n("power.primary.honest.planted_0_3.power_slope_second"). With no slope planted, a false
  detection happens #n("power.primary.honest.planted_0.power_slope_second") of the time, and
  the difference from the first patch is detected #n("power.primary.honest.planted_0.power_diff")
  of the time. With placebo-inflated SEs the detection shares are
  #n("power.primary.placebo_inflated.planted_1_44.power_slope_second"),
  #n("power.primary.placebo_inflated.planted_0_7.power_slope_second") and
  #n("power.primary.placebo_inflated.planted_0_3.power_slope_second").
]

#fig("fig_power", [Share of simulations in which the second patch's slope is detected,
  against the planted slope (primary spec).])

So a second patch that responded like the first would almost certainly have been seen. A
second patch that responded half as much would often have been missed. "No dose-response in
the second patch" means "much less than the first", not "none".

#watch[
  "Not significant" is not "no effect". Without a power check, a null result is only as
  informative as the study's ability to see something. Here the check says the study could
  see a first-patch-sized slope, and not a half-sized one reliably.
]

#skill[
  *Checking power before reading a null.* Plant the effect you care about in simulated data
  that matches yours, and count how often your own analysis finds it.
]

#check(
  ([What does a power simulation plant, and what does it count?],
   [It plants a known second-patch slope in fake data built from the real doses, SEs and
    scatter, refits the real model, and counts how often the slope is detected.]),
  ([What does the power result allow you to say about the second patch?],
   [A slope as large as the first patch's would almost always have been seen, so the second
    patch's response was much smaller; a slope half as large could easily have been missed,
    so "none" is too strong.]),
  ([What would go wrong if you reported the flat second slope without the power check?],
   [A reader couldn't tell whether "no slope" means the patch did little or the study
    couldn't see anything; the claim would be uninterpretable.]),
)

== A fake patch

#words[
  - *Fake patch*: the same analysis across two builds where no card changed. Any "effects"
    it finds are the design's own noise and drift.
]

#picture[
  A rehearsal where nothing on stage changes. If the audience still gasps at the same moments,
  the gasps in the real show can't all be about the new scene.
]

v0.103.2 and v0.103.3 are consecutive stable builds with identical card versions. Running
the second patch's analysis across them, with each second-patch card treated as if it had
been changed and given its eventual dose, shows what the second patch's design produces when
nothing happened.

#project[
  *Your data* (final tables). The fake patch's dose-response slope is
  #n("checks.fake_patch.h3.slope_pm") on #n("checks.fake_patch.h3.n") tweaks, flat as it
  should be. #n("checks.fake_patch.h3.n_abs_z_gt2") of the fake effects are beyond two
  clustered SEs, against #n("checks.fake_patch.h3.expected_abs_z_gt2") expected from the
  placebo spread, and #n("checks.fake_patch.h3.n_abs_z_gt2_calibrated") after calibration. The
  striking number is the spread. The fake effects spread with an sd of
  #n("checks.fake_patch.h3.sd_fake") log-odds; the second patch's real effects with
  #n("checks.fake_patch.h3.sd_real"). The real second patch moved picks about as much as a
  patch that changed nothing. Fake and real effects correlate at
  #n("checks.fake_patch.h3.corr_real"), because both use v0.103.3 (one as the after block, one
  as the before block): noise in v0.103.3’s card levels enters them with opposite signs.
]

#fig("fig_fake_patch", [Fake-patch effects (v0.103.2 → v0.103.3, no card changes) against the
  real second-patch effects of the same cards.])

#watch[
  The negative correlation is a warning about v0.103.3, not a finding about the cards: a
  noisy shared baseline makes the two comparisons that use it move against each other.
]

#skill[
  *Running the analysis where nothing happened.* A fake treatment date or a fake treated
  group shows the size of effects your design produces by itself. Compare real effects with
  that, not with zero.
]

#check(
  ([What is a fake patch, and what should its dose-response slope be?],
   [The same analysis across two builds with no card changes, using the cards' eventual
    doses; its slope should be zero.]),
  ([What does it mean that the fake effects spread as much as the real second-patch effects?],
   [The second patch's real effects are no larger, as a group, than what the design produces
    when nothing changed.]),
  ([Why are fake and real effects negatively correlated?],
   [Both use v0.103.3, as the after block in one and the before block in the other, so noise
    in that build's card levels pushes them in opposite directions.]),
)

== Regression to the mean

#words[
  - *Regression to the mean*: extreme values tend to be followed by more ordinary ones. A card
    picked unusually little just before a buff could rise afterwards without the buff.
]

#picture[
  A student's best-ever exam is usually followed by an ordinary one. Not because they got
  worse, but because the best-ever score included some luck. If the school had changed
  teachers right after that exam, the next exam would wrongly blame the new teacher.
]

The worry is about the first patch, not the second: if designers buffed cards that were
temporarily unpopular and nerfed cards that were temporarily popular, the bounce-back would
look like a patch effect and make the first patch's slope too steep. The test is whether the
cards' movement before release predicts their effect.

#project[
  *Your data* (final tables, first patch's #n("checks.reversion.j1.n") line tweaks).
  #n("checks.reversion.j1.n_opposes") of them moved against their coming change in the weeks
  before release. But the movement predicts the effect with a positive coefficient
  (#n("checks.reversion.j2.declared.pre_coef_pm")\; #n("checks.reversion.j2.pre_slope.pre_coef_pm")
  on the pre-release slope version): cards kept going the way they were going, the opposite of
  a bounce-back. With it in the model the first slope gets steeper, not flatter
  (#n("checks.reversion.j2.declared.slope_x_pm")). Nor does the first slope fade over time:
  week by week after release it runs from #n("checks.reversion.j3.week0.slope") to
  #n("checks.reversion.j3.week5.slope") through the sixth week. In the second patch,
  pre-release movement doesn't change the flat slope (#n("checks.reversion.j4.model.slope_x_pm")).
]

#fig("fig_slope_by_week", [The first patch's dose-response slope estimated week by week after
  release.])

#watch[
  Regression to the mean only inflates an effect if treatment was chosen because of an
  extreme value. Checking whether the pre-treatment movement predicts the effect is the
  direct test; arguing about designers' intentions is not.
]

#skill[
  *Testing for regression to the mean.* Put the pre-treatment movement into the model. A
  bounce-back shows up as a negative coefficient; continuation as a positive one.
]

#check(
  ([How could regression to the mean inflate the first patch's slope?],
   [If buffed cards were temporarily unpopular and nerfed cards temporarily popular, they
    would drift back afterwards, adding a fake rise or fall in the patch's direction.]),
  ([What did the data show instead?],
   [The pre-release movement predicts the effect with a positive sign (continuation), and
    including it makes the first slope steeper. The slope also holds steady week by week.]),
  ([Why would a slope that faded quickly after release be suspicious?],
   [It would suggest a temporary bounce or novelty, not a lasting change in how players value
    the cards.]),
)

== Spillover and the choice of controls

#words[
  - *Spillover (substitution)*: a change to one card moves the picks of others. A buffed card
    is taken instead of something else, so the others' pick rates fall.
  - *Control scope*: which unchanged cards are the controls: the same character's ("color",
    the main design), other characters' only ("other"), or every character's ("all").
]

#picture[
  A discount on one brand of cereal lifts its sales and lowers its rival's. If you measured
  the discount by comparing the brand with its rival, you would count the rival's loss as
  part of the gain.
]

Same-color controls share the treated card's reward screens and runs, so substitution makes
them move opposite to the treated card, and the DiD comes out too large (away from zero), not
too small. The fix is to use other characters' cards, which can't be substitutes: they are
never offered to the same character. The cost is that they don't share the character's own
shocks.

#project[
  *Your data* (final tables, weeks 0–3). With other characters' cards as controls, the first
  patch's slope falls from #n("checks.control_scope.color.primary.slope_first_pm") to
  #n("checks.control_scope.other.primary.slope_first_pm") (all characters:
  #n("checks.control_scope.all.primary.slope_first_pm")); the second patch stays flat
  (#n("checks.control_scope.other.primary.slope_second_pm")). The patch difference stays:
  z diff #n("checks.control_scope.other.primary.z_diff") with other characters' controls,
  #n("checks.control_scope.all.primary.z_diff") with all. Card by card, first-patch estimates
  move by a median #n("checks.control_scope.other.first.median_abs_shift_se") SEs
  (#n("checks.control_scope.other.first.n_moved_1se") of #n("checks.control_scope.other.first.n")
  by more than one), second-patch ones by #n("checks.control_scope.other.second.median_abs_shift_se").
  Dropping screens that held the treated card barely moves anything
  (#n("robustness.h3_drop_shared_screens.median_shift_se") SEs), so the spillover is not on the
  screen itself but at the level of the run or the character.
]

#watch[
  Moving to other characters' controls trades one problem for another: no substitution, but
  no protection against a shock to the treated card's own character. That is why it is a
  check, and why its smaller first slope is read as a modest trim rather than the true value.
]

#skill[
  *Testing the control group itself.* Refit with a different, defensible control group. If
  the conclusion survives both, neither group's weakness explains it.
]

#check(
  ([Which way does substitution bias a DiD with same-color controls, and why?],
   [Away from zero: a buffed card is taken instead of its controls, so the controls fall and
    the difference grows (the reverse for a nerf).]),
  ([What happened to the first and second slopes with other characters' cards as controls?],
   [The first slope fell modestly; the second stayed flat; the difference between them
    stayed at nearly three SEs.]),
  ([Why are other characters' cards not simply the better controls?],
   [They can't be substitutes, but they don't share shocks specific to the treated card's
    character, which same-color controls absorb.]),
)

== Who was playing

#words[
  - *Player token*: a hashed identifier carried by runs uploaded through one route (not the
    SlayTheStats mod). Runs with the same token come from the same player.
  - *Stayers*: players seen on both sides of a release. Comparing only them would hold the
    population fixed.
]

If the second patch's flatness came from a change in who was playing (more experienced
players in June, or the SlayTheStats mod's community-statistics tooltips, which arrived the
same day as the v0.107.1 release), then a group of players untouched by that change should
show a first-patch-like response.

#project[
  *Your data* (final tables, weeks 0–3, primary spec). Fitting each uploader group alone,
  tagged runs give #n("checks.group_lines.tagged.h3.primary.slope_first_pm") and
  #n("checks.group_lines.tagged.h3.primary.slope_second_pm") (z diff
  #n("checks.group_lines.tagged.h3.primary.z_diff")); untagged runs
  #n("checks.group_lines.untagged.h3.primary.slope_first_pm") and
  #n("checks.group_lines.untagged.h3.primary.slope_second_pm")
  (#n("checks.group_lines.untagged.h3.primary.z_diff")). The runs with a player token, almost
  never mod uploads, give #n("checks.token.subset.run_clustered.slope_first_pm") and
  #n("checks.token.subset.run_clustered.slope_second_pm") (the notebooks' set of tweaks; z diff
  #n("checks.token.subset.run_clustered.z_diff")), and the same with each player as their own
  baseline (#n("checks.token.subset_token_fe.run_clustered.z_diff")) or with errors clustered by
  player (#n("checks.token.subset.token_clustered.z_diff")). Every group shows the same
  pattern. The stayers-only fit was not run, and whether the token is opt-in is
  #unverified[not yet verified].
]

#watch[
  The tooltip story is plausible and was the first candidate. But untagged runs and token runs
  (which almost never come through the mod) show the same flat second patch, so tooltips can
  be at most part of the explanation.
]

#skill[
  *Checking for a population change.* Find a subgroup the suspected change didn't touch, or a
  way to follow the same people, and see whether the pattern holds there.
]

#check(
  ([Why do the token runs make a good test of the tooltip explanation?],
   [They come through a different upload route and are almost never mod uploads, so they
    weren't shown the mod's tooltips.]),
  ([What does it mean that the per-player baseline (token fixed effects) changed nothing?],
   [Differences between the players in the subset don't drive the pattern; the flatness holds
    within players.]),
  ([What would a stayers-only fit add, and why is it still open?],
   [It would compare the same players before and after each release, holding the population
    fixed. It was planned but not run.]),
)

== Pre-declared aggregates

#words[
  - *Pre-declared analysis*: the outcomes, population and comparisons written down before
    the analysis runs, so the results can't steer what is reported.
  - *Negative control*: a comparison where nothing should happen (here, a date with no
    release), to show how much calendar time alone moves the outcomes.
]

#picture[
  Writing the bet down before the race. Afterwards nobody can say you picked the horse that
  won.
]

The triage wrote down a list of game-wide outcomes (runs started per week, win rate, floors
reached, ascension, skip rate, character mix) and compared the weeks before and after each
release, with two negative-control dates. This part was measured on the earlier
#n("const.earlier_tables.pages")-page tables only and was #unverified[not rerun] on the final
tables; it is described here without numbers.

#project[
  *Your data* (measured on the earlier #n("const.earlier_tables.pages")-page tables). Neither
  patch changed win rate, skip rate, floors reached or the character mix by more than calendar
  time does on its own. Both releases brought the same visible change in who was playing:
  higher ascension levels in the first two weeks, about equally in both patches. A shift that
  is the same in both patches can't by itself explain a difference between them. One
  declared outcome (the rarity mix of cards in wins and losses) was not computed.
]

#watch[
  Many aggregate comparisons with crude error bars produce "significant" results at the
  negative controls too. Read only differences that are large next to what the controls show.
]

#skill[
  *Declaring the analysis in advance.* Fix the outcomes and comparisons first, include a
  negative control, and report everything you declared.
]

#check(
  ([What is a negative control in the pre-declared aggregates?],
   [A date with no release, compared the same way, to show how much the outcomes move with
    calendar time alone.]),
  ([Both releases brought higher ascension in their first weeks. Why can't that explain the
    patch difference?],
   [It happened about equally in both patches, so it can't make one patch different from the
    other.]),
  ([Why are these aggregates described without numbers?],
   [They were measured only on the earlier tables and were not rerun on the final ones, and
    no saved output carries them into the numbers table.]),
)

== What was found

*What the numbers show.* None of the design explanations tested here accounts for the second
patch's flat response. The design had the power to see a first-patch-sized slope. A fake
patch with no card changes produces effects as spread out as the real second patch's. The
first patch's slope is not a bounce-back and does not fade. Other characters' cards as
controls trim the first patch's slope somewhat and leave the difference in place. Every
group of players examined (tagged, untagged, token runs, and token runs within players)
shows the same pattern.

*How much to trust it, and why.* These checks rule out the explanations they test, as far
as their own power allows; they don't explain why the second patch did less. The best
supported reading is that the second patch's tweaks moved choices much less than the first
patch's: in the data they are indistinguishable, as a group, from no change at all. That is a
statement about pick rates, not about how strong the cards became. Candidates for why
(a settled meta and more experienced players by June, the kinds of numbers the second patch
changed, measurement error in its harder-to-size doses) are not tested here, and the
difference itself still leans on the ruler and on a few tweaks (@ch-rulers). The first
patch's slope is overstated by some amount through spillover between same-character cards,
and the size of that overstatement depends on which controls are right.

#skill[
  *Ruling out alternative explanations, and saying what is left.* After each test, say which
  explanation it removes and how firmly. End with the explanations no test has reached.
]

#check(
  ([List four design explanations for the flat second patch that this chapter tests, and
    the verdict on each.],
   [Any four: low power (ruled out for a first-patch-sized slope); before-block drift (the
    fake patch is flat, though v0.103.3 is noisy); regression to the mean in the first patch
    (no: continuation, steady slope); choice of controls (trims the first slope, difference
    stays); population change and tooltips (every group shows the pattern).]),
  ([Explain to a friend what "the second patch is indistinguishable from no change" means and
    doesn't mean.],
   [Its tweaks moved pick rates no more, as a group, than a comparison where nothing changed.
    It doesn't mean the cards' strength didn't change, or that players ignored the patch
    entirely; a smaller response could be hiding in the noise.]),
  ([What remains unexplained?],
   [Why the second patch moved choices so much less than the first.]),
)
