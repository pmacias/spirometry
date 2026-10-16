#import "../style.typ": *

= What the patches did to picks: the tweaks one by one <ch-results>

#lead[How pick rates moved for each changed card, counted honestly.]

This chapter puts the method to work on all #n("tweaks.solo_estimable") tweaks. Every number
is a DiD (@ch-did: the treated card's change minus its unchanged same-character controls'
change), from the regression of @ch-regression, over weeks 0–3 after release unless it says
otherwise, in percentage points. "Clearly nonzero" means the calibrated version of
@ch-placebo: the z divided by its patch's placebo factor is beyond two.

== The counts

#words[
  - *Buff* and *nerf*: a change that makes a card stronger or weaker, by the patch notes'
    label.
  - *Toward the change*: the effect has the sign the change predicts (picks up after a buff,
    down after a nerf).
  - *Mixed-direction tweak*: a tweak whose numbers moved both ways. *Upgrade-only tweak*: a
    tweak to the upgraded card only (@ch-checks). Neither has a single predicted direction,
    so neither enters the "toward the change" count.
]

#ftable(
  columns: (auto, auto, auto),
  [*Over weeks 0–3*], [*First patch*], [*Second patch*],
  [Tweaks], [#n("tweaks.first")], [#n("tweaks.second")],
  [Clearly nonzero, calibrated], [#n("did.h3.first.calibrated.clearly_nonzero")],
    [#n("did.h3.second.calibrated.clearly_nonzero")],
  [... of those with a direction, toward the change],
    [#n("did.h3.first.calibrated.clearly_nonzero_toward") of #n("did.h3.first.calibrated.clearly_nonzero_with_direction")],
    [#n("did.h3.second.calibrated.clearly_nonzero_toward") of #n("did.h3.second.calibrated.clearly_nonzero_with_direction")],
  [Clearly nonzero, uncalibrated], [#n("did.h3.first.uncalibrated.clearly_nonzero")],
    [#n("did.h3.second.uncalibrated.clearly_nonzero")],
  [... toward the change],
    [#n("did.h3.first.uncalibrated.clearly_nonzero_toward") of #n("did.h3.first.uncalibrated.clearly_nonzero_with_direction")],
    [#n("did.h3.second.uncalibrated.clearly_nonzero_toward") of #n("did.h3.second.uncalibrated.clearly_nonzero_with_direction")],
  [Median effect size (points)], [#n("did.h3.first.median_abs_beta_pp")],
    [#n("did.h3.second.median_abs_beta_pp")],
)

#project[
  *Your data.* Over all weeks the calibrated counts are #n("did.all.first.calibrated.clearly_nonzero")
  and #n("did.all.second.calibrated.clearly_nonzero"), and the uncalibrated ones
  #n("did.all.first.uncalibrated.clearly_nonzero") and #n("did.all.second.uncalibrated.clearly_nonzero").
  With honest errors and no real effects, about #n("did.expected_false_alarms.first") first-patch
  and #n("did.expected_false_alarms.second") second-patch tweaks would be clearly nonzero by
  luck.
]

The direction counts follow the export's rule for what has a direction: a tweak whose
changed numbers don't all move the same way has none. Two tweaks fall out that way: Leading
Strike in the first patch and Reflect in the second. (Reflect's base and upgraded totals both
fall, so the dose rule of @ch-dose puts it on the line as a nerf; the direction count still
leaves it out. Both choices are stated where they apply.)

#watch[
  #n("did.h3.first.calibrated.clearly_nonzero") of #n("tweaks.first") and #n("did.h3.second.calibrated.clearly_nonzero") of #n("tweaks.second") are not the same kind of evidence even after
  calibration. The first is many times what luck gives; the second is close to it.
]

#skill[
  *Summarising many estimates without overclaiming.* Lead with a count built on honest error
  bars, show the uncorrected count beside it, and compare both with what chance alone would
  produce.
]

#check(
  ([How many first-patch and second-patch tweaks are clearly nonzero after calibration,
    weeks 0–3?],
   [#n("did.h3.first.calibrated.clearly_nonzero") of #n("tweaks.first") in the first patch and #n("did.h3.second.calibrated.clearly_nonzero") of #n("tweaks.second") in the second.]),
  ([Why do mixed-direction and upgrade-only tweaks not count toward "toward the change"?],
   [Neither has a single predicted direction: a mixed tweak moved numbers both ways, and an
    upgrade-only tweak changed only the upgraded card, measured on very few offers.]),
  ([About how many clearly nonzero tweaks would chance alone give in the second patch, and
    what does that say about its calibrated count?],
   [About #n("did.expected_false_alarms.second"). The calibrated count is
    #n("did.h3.second.calibrated.clearly_nonzero"), barely above what luck alone would give.]),
)

== The forest plot

#words[
  - *Forest plot*: every estimate drawn as a point with its interval, one row per item, so
    many results can be read at once.
]

#picture[
  A row of thermometers, each with its own error printed on the side. You read the row for
  the pattern (are most of them above zero?) and each thermometer for its own reading, but
  you don't treat one shaky thermometer's reading as news.
]

#fig("fig_forest", [Every tweak's weeks 0–3 effect, by patch, with the clustered 95% interval
  (thick) and the wider placebo-scaled interval (thin). Colour follows the main field's
  direction, so mixed Leading Strike and Reflect are drawn as nerfs.])

#project[
  *Your data.* The first patch's rows sit well away from zero on both sides, buffs up and
  nerfs down; many stay clear of zero even with the wide, placebo-scaled interval. The second
  patch's rows cluster near zero; their wide intervals almost all cross it.
]

#watch[
  A forest plot sorted by effect size makes the extreme rows look like a story. Read the
  intervals first, then the order.
]

#skill[
  *Showing uncertainty for many estimates at once.* Draw each estimate with its interval, and
  when the error bars are known to be off, show the corrected interval too.
]

#check(
  ([What does each row of the forest plot show?],
   [One tweak's estimated effect with its intervals: the clustered one and the wider
    placebo-scaled one.]),
  ([Why draw two intervals for each tweak?],
   [The clustered interval is what the model reports; the placebo-scaled one corrects it for
    the error bars being too small. Showing both shows how much the correction matters.]),
  ([What is the visible difference between the two patches in the plot?],
   [First-patch rows sit far from zero in the direction of each change; second-patch rows sit
    near zero and their corrected intervals mostly cross it.]),
)

== The largest movers

#ftable(
  columns: (auto, auto, auto, auto, auto),
  [*Tweak*], [*Change*], [*Pick rate before → after*], [*Effect (points)*], [*Calibrated z*],
  [Corrosive Wave], [nerf], [#n("tweak.corrosive_wave.v0_103_2.treated_rate_before") → #n("tweak.corrosive_wave.v0_103_2.treated_rate_after")],
    [#n("tweak.corrosive_wave.v0_103_2.h3.beta_pp_pm")], [#n("tweak.corrosive_wave.v0_103_2.h3.z_calibrated")],
  [Parry], [buff], [#n("tweak.parry.v0_103_2.treated_rate_before") → #n("tweak.parry.v0_103_2.treated_rate_after")],
    [#n("tweak.parry.v0_103_2.h3.beta_pp_pm")], [#n("tweak.parry.v0_103_2.h3.z_calibrated")],
  [Leading Strike], [mixed], [#n("tweak.leading_strike.v0_103_2.treated_rate_before") → #n("tweak.leading_strike.v0_103_2.treated_rate_after")],
    [#n("tweak.leading_strike.v0_103_2.h3.beta_pp_pm")], [#n("tweak.leading_strike.v0_103_2.h3.z_calibrated")],
  [Untouchable (v0.103.2)], [nerf], [#n("tweak.untouchable.v0_103_2.treated_rate_before") → #n("tweak.untouchable.v0_103_2.treated_rate_after")],
    [#n("tweak.untouchable.v0_103_2.h3.beta_pp_pm")], [#n("tweak.untouchable.v0_103_2.h3.z_calibrated")],
  [Danse Macabre], [buff], [#n("tweak.danse_macabre.v0_103_2.treated_rate_before") → #n("tweak.danse_macabre.v0_103_2.treated_rate_after")],
    [#n("tweak.danse_macabre.v0_103_2.h3.beta_pp_pm")], [#n("tweak.danse_macabre.v0_103_2.h3.z_calibrated")],
  [Fight Me], [buff], [#n("tweak.fight_me.v0_103_2.treated_rate_before") → #n("tweak.fight_me.v0_103_2.treated_rate_after")],
    [#n("tweak.fight_me.v0_103_2.h3.beta_pp_pm")], [#n("tweak.fight_me.v0_103_2.h3.z_calibrated")],
  [Pinpoint], [nerf], [#n("tweak.pinpoint.v0_103_2.treated_rate_before") → #n("tweak.pinpoint.v0_103_2.treated_rate_after")],
    [#n("tweak.pinpoint.v0_103_2.h3.beta_pp_pm")], [#n("tweak.pinpoint.v0_103_2.h3.z_calibrated")],
  [Flick Flack], [nerf], [#n("tweak.flick_flack.v0_103_2.treated_rate_before") → #n("tweak.flick_flack.v0_103_2.treated_rate_after")],
    [#n("tweak.flick_flack.v0_103_2.h3.beta_pp_pm")], [#n("tweak.flick_flack.v0_103_2.h3.z_calibrated")],
  [Collision Course], [buff], [#n("tweak.collision_course.v0_103_2.treated_rate_before") → #n("tweak.collision_course.v0_103_2.treated_rate_after")],
    [#n("tweak.collision_course.v0_103_2.h3.beta_pp_pm")], [#n("tweak.collision_course.v0_103_2.h3.z_calibrated")],
)

#project[
  *Your data.* All of the largest movers are first-patch tweaks. Corrosive Wave's nerf (its
  main number from #n("tweak.corrosive_wave.v0_103_2.old") to #n("tweak.corrosive_wave.v0_103_2.new"))
  took it from one of its character's most-picked cards to an ordinary one; Parry's buff (from
  #n("tweak.parry.v0_103_2.old") to #n("tweak.parry.v0_103_2.new")) roughly doubled its pick
  rate. Leading Strike is mixed: its damage went from #n("tweak.leading_strike.v0_103_2.old")
  to #n("tweak.leading_strike.v0_103_2.new") while the number of Shivs it creates went from one
  to two, and the patch notes called it a buff. Its picks rose sharply, so players read it as
  a buff. The second patch's largest calibrated movers are Unrelenting
  (#n("tweak.unrelenting.v0_107_1.h3.beta_pp_pm"), calibrated z
  #n("tweak.unrelenting.v0_107_1.h3.z_calibrated")), Uproar
  (#n("tweak.uproar.v0_107_1.h3.beta_pp_pm"), #n("tweak.uproar.v0_107_1.h3.z_calibrated")) and
  Patter's nerf (#n("tweak.patter.v0_107_1.h3.beta_pp_pm"),
  #n("tweak.patter.v0_107_1.h3.z_calibrated"), just short of the line). Most effects arrive in
  the first month: Leading Strike's is #n("tweak.leading_strike.v0_103_2.h3.beta_pp_pm") over
  weeks 0–3 and #n("tweak.leading_strike.v0_103_2.all.beta_pp_pm") over all weeks.
]

Two first-patch movers carry caveats from @ch-checks. Patter
(#n("tweak.patter.v0_103_2.h3.beta_pp_pm"), calibrated z #n("tweak.patter.v0_103_2.h3.z_calibrated"))
was offered more often after the patch and was already drifting up before it, so part of its
estimate may not be the patch. Fight Me was drifting the other way (down) before release,
which, if anything, works against its estimated rise.

#watch[
  "Largest" depends on the scale. In points, popular cards can move more; in log-odds
  (@ch-regression), rarely picked cards can. Danse Macabre's effect is moderate in points but
  roughly doubles its pick rate.
]

#skill[
  *Picking examples honestly.* Show the largest effects with their uncertainty and their
  caveats, and say how they were chosen, so a reader doesn't mistake the extremes for the
  typical case.
]

#check(
  ([Why is Leading Strike called mixed, and what did its pick rate do?],
   [Its damage went down while the number of Shivs it creates went up, and the patch notes
    called it a buff. Its pick rate rose sharply.]),
  ([Patter's first-patch estimate is clearly nonzero. What two caveats go with it?],
   [It was offered more often after the patch (it fails the offer-rate check), and it was
    already drifting up before release (a pre-trend).]),
  ([Why are the largest movers all from the first patch?],
   [The first patch's effects were larger across the board; the second patch's typical effect
    was well under half the size for tweaks of similar size (@ch-dose).]),
)

== Against the change

Some tweaks moved against the direction of their change. Without calibration there are
several: in the first patch, buffs to Memento Mori
(#n("tweak.memento_mori.v0_103_2.h3.beta_pp_pm")), Grand Finale
(#n("tweak.grand_finale.v0_103_2.h3.beta_pp_pm")) and Solar Strike
(#n("tweak.solar_strike.v0_103_2.h3.beta_pp_pm")) were followed by fewer picks; in the second,
nerfs to Bulwark (#n("tweak.bulwark.v0_107_1.h3.beta_pp_pm")) and Debilitate
(#n("tweak.debilitate.v0_107_1.h3.beta_pp_pm")) by more.

#project[
  *Your data.* After calibration none of them is past the line: calibrated z
  #n("tweak.memento_mori.v0_103_2.h3.z_calibrated") (Memento Mori),
  #n("tweak.grand_finale.v0_103_2.h3.z_calibrated") (Grand Finale),
  #n("tweak.solar_strike.v0_103_2.h3.z_calibrated") (Solar Strike),
  #n("tweak.bulwark.v0_107_1.h3.z_calibrated") (Bulwark) and
  #n("tweak.debilitate.v0_107_1.h3.z_calibrated") (Debilitate). Each is within what unchanged
  cards do on their own. The upgrade-only tweaks' estimates rest on a few hundred upgraded
  offers and are uninformative: Serpent Form #n("tweak.serpent_form.v0_103_2.h3.beta_pp_pm"),
  Royalties #n("tweak.royalties.v0_107_1.h3.beta_pp_pm"), Untouchable (v0.107.1)
  #n("tweak.untouchable.v0_107_1.h3.beta_pp_pm").
]

#watch[
  An effect against the change is not automatically an error. Players can misread a patch, a
  buff can come with a change to the card's role, or another card can become a better
  choice. But an effect against the change that disappears under honest error bars is best
  read as noise.
]

#skill[
  *Treating surprising results as tests, not stories.* Before explaining an odd result, check
  whether it survives the corrected error bars. Most surprises in a large table don't.
]

#check(
  ([Name two tweaks that moved against their change before calibration.],
   [Any two of: Memento Mori, Grand Finale, Solar Strike (buffs, fewer picks); Bulwark,
    Debilitate in the second patch (nerfs, more picks).]),
  ([Why does calibration change how these results are read?],
   [Their calibrated z's are all within two, so they are within what unchanged cards produce
    by themselves; they can't be distinguished from noise.]),
  ([What would go wrong if you wrote a story about why players picked Memento Mori less after
    its buff?],
   [You would be explaining a result that is consistent with noise, and the story would be
    unfalsifiable by this data.]),
)

== What was found

*What the numbers show.* In the first balance patch (v0.103.2), pick rates moved the way the
changes pointed. #n("did.h3.first.calibrated.clearly_nonzero") of #n("tweaks.first") tweaks
are clearly nonzero with calibrated errors over the first four weeks, and every one of them
with a single direction moved toward its change. The typical tweak moved picks by
#n("did.h3.first.median_abs_beta_pp") points, and the largest by more than ten (Corrosive Wave
#n("tweak.corrosive_wave.v0_103_2.h3.beta_pp"), Parry #n("tweak.parry.v0_103_2.h3.beta_pp")).
In the second patch (v0.107.1), #n("did.h3.second.calibrated.clearly_nonzero") of
#n("tweaks.second") tweaks are clearly nonzero, both toward their change, and the typical
tweak moved picks by #n("did.h3.second.median_abs_beta_pp") points.

*How much to trust it, and why.* The first patch's result is strong. It survives the
correction of @ch-placebo, which widened its error bars by a factor of
#n("did.h3.first.calibrated.factor")\; the
robustness checks of @ch-checks move the estimates little; and the only sign problems are
two cards with caveats (Patter's offer rate and pre-trend, Fight Me's pre-trend). For any one
first-patch card, the calibrated z is the honest guide, and cards near the line are
uncertain. The second patch's result is weaker in a specific way: it is a near-absence of
clear effects, and an absence is only as convincing as the power to see something.
@ch-explanations shows that a first-patch-sized response would have been seen. Two things
limit the second patch's individual estimates: its before block is short and drifts
(@ch-checks), and its real effects are only a little larger than its placebos (@ch-placebo).
The count could be a little higher or lower on another sample; the conclusion that the second
patch moved picks far less than the first does not hang on it.

#skill[
  *Keeping the finding and the confidence apart.* State what the numbers show first, then
  say how much to trust it and why. Mixing the two ("the patch probably sort of worked")
  makes both unclear.
]

#check(
  ([State the first patch's pick-rate finding in two sentences, with numbers.],
   [#n("did.h3.first.calibrated.clearly_nonzero") of #n("tweaks.first") tweaks moved picks clearly, with calibrated errors over weeks 0–3, and all of those
    with a direction moved toward their change. The typical tweak moved picks by
    #n("did.h3.first.median_abs_beta_pp") points\; the largest, Corrosive Wave, by
    #n("tweak.corrosive_wave.v0_103_2.h3.beta_pp").]),
  ([Why is the second patch's result "weaker in a specific way"?],
   [It is mostly an absence of clear effects, and an absence needs a power argument (would a
    real effect have been seen?) plus a stable comparison, and its before block drifts.]),
  ([What would you say if asked whether the second patch's count of two is exact?],
   [No: on another sample it could easily be one more or one fewer. The conclusion rests on the pattern
    (small effects, no dose-response), not on that count.]),
)
