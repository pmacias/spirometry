#import "../style.typ": *

= Checking the design <ch-checks>

#lead[How the analysis tries to break its own result.]

A DiD estimate is only as good as its assumptions: that the patch changed nothing about the
offers, that the treated card wasn't already drifting, that players hadn't reacted earlier,
and that small choices in the model don't drive the answer. Each section below is a test
the design could fail. The results are reported whether they help or not.

== The offer-rate check

#picture[
  If you are testing whether a new card is more popular, first check that the dealer didn't
  change the deck. If the card started turning up twice as often, more picks could come from
  more chances, and something else about the game changed with the patch.
]

#words[
  - *Offer-rate check*: a patch should change how often a card is picked when offered, not
    how often it is offered. The check compares each card's share of its character's offers
    before and after, against the controls' shares.
  - *Rarity*: cards are common, uncommon or rare, and the game offers rarer cards less often.
    A change in the rarity pools would move offer shares for a whole rarity, so the check is
    also run against controls of the card's own rarity.
]

#project[
  *Your data.* #n("flags.offer_rate.all.n_flagged") of #n("tweaks.solo_estimable") tweaks are
  flagged against all controls, and #n("flags.offer_rate.all.n_flagged_rarity") against
  controls of their own rarity. Sculpting Strike's offer share moved by
  #n("tweak.sculpting_strike.v0_103_2.offer_share_vs_controls") on a log scale relative to the
  controls (z = #n("tweak.sculpting_strike.v0_103_2.offer_rate_z")); Patter's first-patch
  share by #n("tweak.patter.v0_103_2.offer_share_vs_controls") (z =
  #n("tweak.patter.v0_103_2.offer_rate_z")). Patter's second-patch tweak flags against its own
  rarity only. Because the flags hold against cards of the same rarity, a change to the
  rarity pools is ruled out: something specific to these cards changed how often they are
  offered. #unverified[Why is open], and their pick-rate estimates carry that caveat.
]

#fig("fig_offer_rate", [Each tweak's change in offer share against its controls (log ratio,
  minus the controls' median), with the flagged tweaks labelled.])

#watch[
  A flagged offer rate doesn't make a pick-rate estimate wrong; it means the comparison may
  include something besides the patch. Report it beside the estimate, don't silently drop the
  card.
]

#skill[
  *Testing a design's built-in prediction.* A good design predicts things besides the main
  result (here: offer rates shouldn't move). Checking those predictions is cheap and catches
  broken assumptions.
]

#check(
  ([Why should a patch not change how often a card is offered?],
   [Offers are decided by the game's random generator from the card pools; a change to a
    card's numbers doesn't change the pool, so only something else (a pool or rarity change,
    a bug) would move offer rates.]),
  ([Why is the check also run against controls of the card's own rarity?],
   [A change to a whole rarity's pool would move every card of that rarity. Comparing within
    the rarity separates a pool change from something specific to the card.]),
  ([What would go wrong if a flagged card's pick-rate estimate were reported without the
    caveat?],
   [Readers would take the whole change as the patch's effect on choices, when part of the
    comparison may come from whatever changed the card's offers.]),
)

== Pre-trends and the event study

#words[
  - *Pre-trend*: the treated card drifting away from its controls in the weeks before the
    patch. It is the visible warning that parallel trends (@ch-did) may fail.
  - *Event study*: the DiD estimated week by week, before and after the release, each week
    against a reference week just before it.
]

#picture[
  A time-lapse of the gap. Instead of one before photo and one after photo, you take one a
  week. If the gap was already widening before the patch, the single before-and-after
  comparison would have credited the patch with the drift.
]

#project[
  *Your data.* Pre-trends are judged by the weekly slope of the gap before release. In the
  first patch, #n("flags.pretrend.first.n_beyond_2se") tweaks drift by more than two SEs:
  Patter (#n("tweak.patter.v0_103_2.pretrend_slope_pp_pm") points a week) and Fight Me
  (#n("tweak.fight_me.v0_103_2.pretrend_slope_pp_pm")). In the second patch the
  count is #n("flags.pretrend.second.n_beyond_2se"), but it has only two before-weeks per card
  (against four in the first), so the check is weaker there. A drift of a point a week is
  comparable to many effects over a month, so these two estimates carry a caveat. The shape
  of each informative tweak's weekly gap around its first beta date (a step, a ramp or a
  straight drift) is #unverified[not yet recorded] card by card (PLAN item 14).
]

#fig("fig_event_study", [Weekly gaps to the controls for Parry and for the tweak with the
  steepest pre-trend.])

#watch[
  Testing each before-week separately against zero and counting the odd ones out ignores that
  neighbouring weeks are related; the notebook prints such a test but uses the slope to
  decide.
]

#skill[
  *Looking at the data over time before trusting a before-after number.* Plot the weekly
  series. Most broken assumptions in time comparisons are visible in a plot.
]

#check(
  ([What is a pre-trend, and why does it threaten a DiD?],
   [The treated card drifting relative to its controls before the patch. If the drift
    continued, the DiD would count it as part of the patch's effect.]),
  ([Why is the pre-trend check weaker for the second patch?],
   [Its before block (v0.103.3) was stable for only a few weeks, so each card has only two
    before-weeks to estimate a slope from.]),
  ([What does an event study show that a single DiD number doesn't?],
   [How the gap moved week by week: whether it was flat before, when it changed, and whether
    the change grew, held or faded.]),
)

== Upgrade-only tweaks: a built-in placebo

#words[
  - *Placebo test*: a test where the true effect is known to be zero. If the method finds an
    effect there, something besides the treatment is moving the numbers.
  - *Upgrade-only tweak*: a change to the upgraded card only. The un-upgraded card didn't
    change, so its offers are a natural placebo.
]

#picture[
  A sugar pill should do nothing. If patients on the sugar pill improve, the improvement in
  the real treatment group can't all be the drug.
]

#project[
  *Your data.* Three tweaks changed only the upgraded card. On their un-upgraded offers the
  DiD should be zero. Serpent Form: #n("tweak.serpent_form.v0_103_2.placebo_beta_pp_pm")
  points, as expected. Royalties: #n("tweak.royalties.v0_107_1.placebo_beta_pp_pm"). Untouchable
  (v0.107.1): #n("tweak.untouchable.v0_107_1.placebo_beta_pp_pm"), several SEs below zero. Both
  failures are second-patch cards, whose before block is thin and whose treated cards drift
  (the last section of this chapter), so drift is the first candidate; an attention effect
  from appearing in the patch notes would more likely push picks up after a buff, not down.
  #unverified[The cause is open.] On the placebo scale of @ch-placebo these values are within
  or at the edge of what unchanged cards show (measured on the earlier
  #n("const.earlier_tables.pages")-page tables). The upgraded-offer estimates themselves rest
  on very few offers (Serpent Form #n("tweak.serpent_form.v0_103_2.n_treated_offers"),
  Royalties #n("tweak.royalties.v0_107_1.n_treated_offers")) and are uninformative.
]

#watch[
  A failed placebo is evidence, not noise to explain away. Here it is one of the signs that
  the second patch's before block is not as stable as one would like.
]

#skill[
  *Using a placebo the data hands you.* Look for parts of the data that went through the same
  pipeline but could not have been affected by the treatment. They test the pipeline for
  free.
]

#check(
  ([Why are the un-upgraded offers of an upgrade-only tweak a placebo?],
   [The un-upgraded card did not change, so the true effect on its offers is zero.]),
  ([Two of the three placebos came out below zero. What is the first candidate explanation,
    and why?],
   [Drift in the second patch's thin before block: both are second-patch cards, and the
    treated cards are known to drift between the stable builds.]),
  ([Why are the upgrade-only tweaks' own estimates uninformative?],
   [They are measured on upgraded offers only, of which there were a few hundred, so their
    SEs are huge.]),
)

== Anticipation: reacting to the beta

#words[
  - *Anticipation*: players changing their picks when the beta patch notes appear, before the
    change reaches stable. It would put part of the effect into the before block and shrink
    the main estimate.
  - *First-beta date*: when the change first appeared on the beta branch. *Lead time*: from
    then to the stable release.
  - *Informative tweak*: one with enough old-card play on both sides of the first-beta date
    to test (at least two thousand treated offers on each side, and at least three days
    before it).
]

#picture[
  Umbrella sales rise when the forecast says rain, before a drop falls. If you measured the
  effect of rain from the day it started, you would miss the part that happened at the
  forecast.
]

The check runs on stable builds where players still had the old card, and asks whether the
treated card's gap to its controls moved at the first-beta date. It splits by date, never by
build.

#project[
  *Your data.* Lead times run from #n("anticipation.lead_days.min") to
  #n("anticipation.lead_days.max") days (median #n("anticipation.lead_days.median")).
  #n("anticipation.all.n_informative") of #n("anticipation.all.n_tweaks") tweaks are
  informative: #n("anticipation.first.n_informative") from the first patch and
  #n("anticipation.second.n_informative") from the second. The first patch mostly can't be
  tested: its old-card stable build had too few days before the first beta date. Of the
  #n("anticipation.all.n_informative_clear") informative tweaks with a clearly nonzero main
  effect, the post-beta gap divided by the main effect has a median of
  #n("anticipation.all.median_ratio_to_main"): small, or on the other side of zero. Two have a
  post-beta gap on the same side and larger than the main effect: Crescent Spear (ratio
  #n("tweak.crescent_spear.v0_107_1.anticipation.ratio_to_main")) and Furnace
  (#n("tweak.furnace.v0_107_1.anticipation.ratio_to_main")).
]

#fig("fig_anticipation", [Post-beta gap against the main effect for the informative tweaks.
  Points near the horizontal axis show no anticipation.])

#watch[
  "No anticipation found" holds only for the tweaks the check can test. For most of the first
  patch the check is silent, not reassuring.
]

#skill[
  *Checking timing assumptions.* When a treatment is announced before it starts, ask whether
  people could react to the announcement, and test the date you assumed against the earlier
  one.
]

#check(
  ([What is anticipation, and which way would it bias the main estimate?],
   [Players reacting to the beta patch notes before the stable release. It moves part of the
    effect into the before block, so the main estimate would be too small.]),
  ([Why can't most first-patch tweaks be tested for anticipation?],
   [Their old-card stable build had only a couple of days of play before the first beta date,
    too few offers to measure a change.]),
  ([Name the two tweaks whose post-beta gaps are larger than their main effects, and say
    what that could mean.],
   [Crescent Spear and Furnace. For them part of the effect may have arrived before stable,
    so their main estimates could understate it (or their cards were drifting anyway).]),
)

== The robustness table

#words[
  - *Robustness check*: change one choice in the analysis, refit, and see how far the answer
    moves. Moves are measured in the main estimate's SEs.
  - *Sensitivity analysis*: the same idea applied to a decision whose right answer is unclear
    (a ruler, a dose, a control group), to show how much the conclusion depends on it.
]

#picture[
  Weigh yourself again on another scale. If the number barely moves, the first scale was
  fine. If it jumps, you need to know why before you trust either.
]

#ftable(
  columns: (auto, auto, auto, auto),
  [*Check (weeks 0–3)*], [*Median shift (SEs)*], [*Beyond two SEs*], [*Sign flips*],
  [No uploader-group terms], [#n("robustness.h3_pooled_groups.median_shift_se")],
    [#n("robustness.h3_pooled_groups.share_beyond_2se")],
    [#n("robustness.h3_pooled_groups.sign_flips")],
  [Drop screens shared with the treated card], [#n("robustness.h3_drop_shared_screens.median_shift_se")],
    [#n("robustness.h3_drop_shared_screens.share_beyond_2se")],
    [#n("robustness.h3_drop_shared_screens.sign_flips")],
  [Drop bug-fix-flagged controls], [#n("robustness.h3_drop_behavior_flags.median_shift_se")],
    [#n("robustness.h3_drop_behavior_flags.share_beyond_2se")],
    [#n("robustness.h3_drop_behavior_flags.sign_flips")],
  [Drop the ten heaviest uploaders], [#n("robustness.h3_drop_top_uploaders.median_shift_se")],
    [#n("robustness.h3_drop_top_uploaders.share_beyond_2se")],
    [#n("robustness.h3_drop_top_uploaders.sign_flips")],
  [Screens where something was picked], [#n("robustness.h3_picked_screens_only.median_shift_se")],
    [#n("robustness.h3_picked_screens_only.share_beyond_2se")],
    [#n("robustness.h3_picked_screens_only.sign_flips")],
  [Untagged uploaders only], [#n("robustness.h3_untagged.median_shift_se")],
    [#n("robustness.h3_untagged.share_beyond_2se")], [#n("robustness.h3_untagged.sign_flips")],
  [Tagged uploaders only], [#n("robustness.h3_tagged.median_shift_se")],
    [#n("robustness.h3_tagged.share_beyond_2se")], [#n("robustness.h3_tagged.sign_flips")],
)

#project[
  *Your data.* The first four checks barely move anything. "Screens where something was
  picked" asks a slightly different question (the choice among cards, with "take nothing"
  removed) and moves estimates more, without changing any sign. The tagged-only fits use about
  a quarter of the data, so their SEs are about twice as large and a median shift near one SE
  would be expected from that alone; the observed #n("robustness.h3_tagged.median_shift_se")
  means the two uploader groups responded differently to some changes. Their estimates still
  correlate at #n("robustness.tagged_untagged.h3.corr") across the
  #n("robustness.tagged_untagged.h3.n") tweaks. The same checks over all weeks tell the same
  story (tagged only: #n("robustness.tagged.median_shift_se") SEs, with
  #n("robustness.tagged.sign_flips") sign flips).
]

#fig("fig_robustness", [Each check's shift from the main estimate, in the main estimate's SEs,
  for both horizons.])

A few planned checks were not run. Card-by-act baselines (each card's own profile through the
run) were dropped, because the timing of offers balanced between blocks. The analysis of when
in the run cards are picked was done on early tables only and is #unverified[not rechecked
on the final tables], so it isn't used here.

#watch[
  A check that moves nothing is not proof that the estimate is right; it shows that this one
  choice doesn't matter. The checks that matter most are the ones that could have moved the
  answer and didn't, and the ones that did move it (here, the uploader groups).
]

#skill[
  *Stress-testing a result.* List the choices you made, vary each one, and report the moves
  in units of the estimate's own uncertainty, including the ones that moved.
]

#check(
  ([Why are robustness shifts measured in SEs rather than in points?],
   [A move is only meaningful next to the estimate's uncertainty: a one-point move is large
    for a card with an SE of a few tenths and small for one with an SE of several points.]),
  ([The tagged-only check moves estimates a lot. Give two reasons, one expected and one
    informative.],
   [Expected: tagged runs are about a quarter of the data, so their estimates are noisier.
    Informative: the shift is larger than noise alone would give, so the two groups responded
    differently to some changes.]),
  ([What does "screens where something was picked" change about the question?],
   [It removes the choice to take nothing, so the estimate is about which card players choose
    among the offered ones.]),
)

== The second patch's before block

The second patch is compared against v0.103.3 alone, a stable build that ran for only about
three weeks. Two checks ask whether that choice matters.

#project[
  *Your data.* Dropping first-patch cards from the second patch's controls moves estimates by
  a median #n("second_patch.h3.no_first_patch_controls.median_shift_se") SEs (largest
  #n("second_patch.h3.no_first_patch_controls.max_shift_se")): the controls are fine. Pooling
  the earlier stable build v0.103.2 into the before block moves them by a median
  #n("second_patch.h3.pooled_before.median_shift_se") SEs, largest
  #n("second_patch.h3.pooled_before.max_shift_se"). Furnace, for example, goes from
  #n("tweak.furnace.v0_107_1.h3.beta_pp_pm") to #n("tweak.furnace.v0_107_1.h3.pooled_before_beta_pp_pm").
  Since the controls aren't the cause, the treated cards themselves drifted between the two
  builds. v0.103.3 alone stays the main design; the drift is a caveat on the second patch's
  individual estimates.
]

#watch[
  Pooling more data into a block is only a gain if the block is one treatment. Here it would
  mix in weeks when the treated cards stood at a different level.
]

#skill[
  *Testing a pooling decision both ways.* When a choice trades sample size against
  homogeneity, fit both and look at which estimates move and why.
]

#check(
  ([Dropping first-patch cards from the controls changed nothing, but pooling v0.103.2
    changed several estimates. What does that tell you?],
   [The controls are not the problem; the treated cards moved between v0.103.2 and v0.103.3,
    so pooling mixes in their earlier levels.]),
  ([Why not simply pool v0.103.2 to get a larger before block?],
   [It would mix the treated cards' drift into the before block, biasing their estimates;
    more data around a moving baseline is not better data.]),
  ([Which other check in this chapter points to the same weakness in the second patch's
    before block?],
   [The upgrade-only placebos: the two that came out below zero are both second-patch cards.]),
)
