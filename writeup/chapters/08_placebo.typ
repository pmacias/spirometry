#import "../style.typ": *

= Are the error bars honest? The placebo calibration <ch-placebo>

#lead[If the same method is run on cards that did not change, does it find "no effect" as
  often as its error bars promise?]

Everything in @ch-noise assumed the SEs are honest: that an estimate's real wobble is the
size the model reports. This chapter tests that assumption directly, finds that it fails,
and builds the corrected count of "clearly nonzero" tweaks that the results in @ch-results
lead with.

== A smoke alarm tested without fire

#picture[
  You test a smoke alarm by making a little smoke when there is no fire. If it goes off a
  little more often than it should, you can live with it. If it goes off half the time you
  open the oven, its alarms in a real fire are hard to read. The fix is not to throw the
  alarm away but to learn how often it cries wolf and read its alarms against that.
]

#words[
  - *Placebo test* (from @ch-checks): a test where the true effect is known to be zero.
  - *Pseudo-treated card*: an unchanged card analysed as if the patch had changed it. Its
    true effect is zero.
  - *Standard normal*: the bell curve that z = estimate ÷ SE should follow when the true
    effect is zero and the SE is honest: centred on zero, with a spread (sd) of one, and
    beyond two only about one time in twenty.
]

If the SEs are honest, the z's of many pseudo-treated cards should look like draws from the
standard normal. If their spread is much wider than one, the SEs are too small, and every
"clearly nonzero" count built on them is too large.

#project[
  *Your data.* This was prompted by an earlier check: the tweaks' effects fitted separately
  on early- and late-uploaded runs disagreed by more than their SEs allowed. The placebo test
  asks the question for the whole method at once.
]

#watch[
  A placebo test checks the method, not one result. It can tell you the error bars are too
  small on average; it can't tell you which particular estimate is wrong.
]

#skill[
  *Checking your error bars are honest.* Run the full method where the answer is known to be
  zero, many times, and compare the spread of results with what the error bars promise.
]

#check(
  ([What should the z's of pseudo-treated cards look like if the SEs are honest?],
   [Like the standard normal: centred on zero, sd of one, beyond two in about one fit in
    twenty.]),
  ([In the smoke-alarm picture, what does "learning how often it cries wolf" correspond to?],
   [Measuring the spread of placebo z's, the calibration factor, and reading real estimates
    against it.]),
  ([Why can't a placebo test say which individual tweak's estimate is wrong?],
   [It measures how the method behaves on average across many fits with a true effect of
    zero; it says how wide the error bars should be, not which estimate missed.]),
)

== The placebo design

The placebo fits are the real fits with one change. For each tweak, an unchanged card of the
same character takes the treated card's place; the real treated card is dropped from the
data, and the pseudo card is removed from the controls. Everything else (the windows, the
model, the fixed effects, the clustering) is the same as in the real fit.

#words[
  - *Minimum offers*: a pseudo card needs at least as many offers in each block as the
    least-offered real tweak, so placebos are no thinner than real tweaks.
  - *Window–card pair*: tweaks that share a window draw the same pseudo cards, and those fits
    differ only in which real card was left out. Counting each (window, pseudo card) pair
    once removes near-duplicate rows.
  - *Robust sd*: a spread measured from the median distance to the median (the MAD), scaled
    to match the ordinary sd for a bell curve. A few extreme values can't drag it.
]

#project[
  *Your data.* Up to twenty pseudo cards per tweak, drawn with a fixed seed:
  #n("placebo.fits.all.n") fits on #n("tweaks.solo_estimable") tweaks, which are
  #n("placebo.pairs.all.n") distinct window–card pairs. The minimum-offers rule came out at
  #n("placebo.min_offers") offers per block, set by an upgrade-only tweak, so it barely binds
  for ordinary tweaks. The fits were run at both horizons, all weeks and weeks 0–3.
]

#watch[
  Counting near-duplicate rows as independent would make a placebo summary look more
  certain than it is. Deduplicate before summarising.
]

#skill[
  *Designing a placebo that matches the real analysis.* A placebo only calibrates the method
  if it goes through exactly the same pipeline, with the same data rules, as the real fits.
]

#check(
  ([How is a placebo fit built from a real fit?],
   [An unchanged same-character card replaces the treated card; the real treated card is
    dropped and the pseudo card removed from the controls; everything else is the same.]),
  ([Why are the results summarised over window–card pairs rather than over all fits?],
   [Tweaks sharing a window draw the same pseudo cards, so their fits are near copies;
    counting each pair once avoids treating copies as independent evidence.]),
  ([Why use a robust sd alongside the ordinary sd?],
   [A few extreme placebo fits can inflate the ordinary sd; the robust sd describes the
    typical spread and isn't dragged by them.]),
)

== What came out

#ftable(
  columns: (auto, auto, auto, auto, auto),
  [*Window–card pairs*], [*Pairs*], [*sd of z*], [*Robust sd of z*], [*Share beyond two*],
  [Honest errors], [], [#n("const.honest.sd_z")], [#n("const.honest.sd_z")],
    [#n("const.honest.share_abs_z_gt2")],
  [First patch, all weeks], [#n("placebo.pairs.first.n")], [#n("placebo.pairs.first.sd_z")],
    [#n("placebo.pairs.first.robust_sd_z")], [#n("placebo.pairs.first.share_abs_z_gt2")],
  [First patch, weeks 0–3], [#n("placebo.h3.pairs.first.n")], [#n("placebo.h3.pairs.first.sd_z")],
    [#n("placebo.h3.pairs.first.robust_sd_z")], [#n("placebo.h3.pairs.first.share_abs_z_gt2")],
  [Second patch, all weeks], [#n("placebo.pairs.second.n")], [#n("placebo.pairs.second.sd_z")],
    [#n("placebo.pairs.second.robust_sd_z")], [#n("placebo.pairs.second.share_abs_z_gt2")],
  [Second patch, weeks 0–3], [#n("placebo.h3.pairs.second.n")], [#n("placebo.h3.pairs.second.sd_z")],
    [#n("placebo.h3.pairs.second.robust_sd_z")], [#n("placebo.h3.pairs.second.share_abs_z_gt2")],
)

#project[
  *Your data.* The placebo z's are far too spread out. With honest errors their sd would be
  #n("const.honest.sd_z")\; it is #n("placebo.pairs.all.sd_z") over all pairs (robust sd
  #n("placebo.pairs.all.robust_sd_z")), and #n("placebo.pairs.all.share_abs_z_gt2") of
  unchanged cards come out "clearly nonzero" against #n("const.honest.share_abs_z_gt2")
  expected. The clustered SEs are several times too small, and by different amounts in the
  two patches: about four times in the first, two to three times in the second. The spread is
  larger for rarely picked pseudo cards (robust sd
  #n("placebo.spread.treated_rate_before.low.robust_sd_z") in the lowest third by pick rate,
  #n("placebo.spread.treated_rate_before.high.robust_sd_z") in the highest).
]

#fig("fig_placebo_z", [Placebo z by patch (all-weeks fits) against the standard normal that
  honest errors would give.])

#watch[
  The real tweaks' z's are just as inflated as the placebos'. A tweak whose z is four is not four honest
  SEs from zero; in the first patch it is about one.
]

#skill[
  *Comparing a distribution with what it should be.* Plot what you got against the
  distribution your assumptions promise. A spread four times too wide is obvious in a
  picture and easy to miss in a table of p-values.
]

#check(
  ([With honest errors, what share of placebo fits should be beyond two SEs? What share is?],
   [About one in twenty (under five percent). About half of window–card pairs, and about two
    thirds in the first patch.]),
  ([What does a robust sd of about four for the first patch's placebo z's mean for its real
    estimates?],
   [Their true uncertainty is about four times what the clustered SEs say, so their z's
    should be divided by about four before reading them.]),
  ([Explain to a friend why "clearly nonzero" counts made with the model's SEs are too high.],
   [The model's error bars are too narrow, so luck alone pushes many estimates past the
    two-SE line: even cards that didn't change cross it most of the time.]),
)

== Calibrated "clearly nonzero"

#words[
  - *Calibration factor*: the placebo robust sd for a patch and horizon. It says how many
    times too small the clustered SEs are, on average.
  - *Calibrated z*: a tweak's z divided by its patch's factor. *Calibrated "clearly
    nonzero"*: a calibrated z beyond two in size.
  - *Empirical p*: the share of a tweak's own window's placebos whose effect is at least as
    large as the real one. It doesn't assume any bell curve.
]

#picture[
  A bathroom scale checked with known weights. If a two-kilo weight reads eight kilos, you
  divide every reading by four. The calibration factor is that divisor, measured on cards
  whose weight is known to be zero.
]

The calibrated count is the lead count in this guide, at the primary horizon, weeks 0–3. The
rule was set before the counts were seen (decision log, October 2026): one factor per patch,
from placebo fits at the estimate's own horizon. The plain sd is a sensitivity version, and
the uncalibrated counts are kept, labelled as such.

#ftable(
  columns: (auto, auto, auto, auto),
  [*Over weeks 0–3*], [*Factor*], [*Clearly nonzero*], [*Toward the change*],
  [First patch, calibrated], [#n("did.h3.first.calibrated.factor")],
    [#n("did.h3.first.calibrated.clearly_nonzero") of #n("tweaks.first")],
    [#n("did.h3.first.calibrated.clearly_nonzero_toward") of #n("did.h3.first.calibrated.clearly_nonzero_with_direction")],
  [First patch, plain sd], [#n("did.h3.first.calibrated_plain_sd.factor")],
    [#n("did.h3.first.calibrated_plain_sd.clearly_nonzero")],
    [#n("did.h3.first.calibrated_plain_sd.clearly_nonzero_toward") of #n("did.h3.first.calibrated_plain_sd.clearly_nonzero_with_direction")],
  [First patch, uncalibrated], [],
    [#n("did.h3.first.uncalibrated.clearly_nonzero")],
    [#n("did.h3.first.uncalibrated.clearly_nonzero_toward") of #n("did.h3.first.uncalibrated.clearly_nonzero_with_direction")],
  [Second patch, calibrated], [#n("did.h3.second.calibrated.factor")],
    [#n("did.h3.second.calibrated.clearly_nonzero") of #n("tweaks.second")],
    [#n("did.h3.second.calibrated.clearly_nonzero_toward") of #n("did.h3.second.calibrated.clearly_nonzero_with_direction")],
  [Second patch, plain sd], [#n("did.h3.second.calibrated_plain_sd.factor")],
    [#n("did.h3.second.calibrated_plain_sd.clearly_nonzero")],
    [#n("did.h3.second.calibrated_plain_sd.clearly_nonzero_toward") of #n("did.h3.second.calibrated_plain_sd.clearly_nonzero_with_direction")],
  [Second patch, uncalibrated], [],
    [#n("did.h3.second.uncalibrated.clearly_nonzero")],
    [#n("did.h3.second.uncalibrated.clearly_nonzero_toward") of #n("did.h3.second.uncalibrated.clearly_nonzero_with_direction")],
)

#project[
  *Your data.* Calibration cuts the first patch's count from
  #n("did.h3.first.uncalibrated.clearly_nonzero") to #n("did.h3.first.calibrated.clearly_nonzero")
  and the second patch's from #n("did.h3.second.uncalibrated.clearly_nonzero") to
  #n("did.h3.second.calibrated.clearly_nonzero") (#n("did.h3.second.calibrated_plain_sd.clearly_nonzero") under the plain sd). In the first patch
  every calibrated clearly-nonzero tweak with a single direction moved toward its change;
  the tweaks that moved against their change are no longer past the line. The all-weeks
  version agrees for the first patch (#n("did.all.first.calibrated.clearly_nonzero") of
  #n("tweaks.first")) and gives #n("did.all.second.calibrated.clearly_nonzero") for the second.
  Against their own window's placebos, #n("placebo.vs_real.first.n_empirical_p_lt_05") of
  #n("tweaks.first") first-patch tweaks and #n("placebo.vs_real.second.n_empirical_p_lt_05") of
  #n("tweaks.second") second-patch tweaks are larger than all but a twentieth of the
  placebos (empirical p below five hundredths, all weeks).
]

#watch[
  One factor per patch is an average. Some cards' true uncertainty is larger than the factor
  says and some smaller, so a calibrated z near two is still a coin-toss call.
]

#skill[
  *Correcting a test with a measured error rate.* When the error bars are known to be off,
  rescale them by what a placebo shows, state the rule before you count, and keep the
  uncorrected numbers beside the corrected ones.
]

#check(
  ([How is a calibrated z computed?],
   [The tweak's z divided by its patch's placebo robust sd at the same horizon.]),
  ([Why is the calibrated count the lead number rather than the uncalibrated one?],
   [The placebo test shows the uncalibrated errors are several times too small, so the
    uncalibrated count includes many tweaks that unchanged cards would match.]),
  ([What does it mean that, after calibration, all first-patch tweaks past the line moved
    toward their change?],
   [The tweaks that seemed to move against their change were within what unchanged cards do;
    the clear first-patch effects all go the way the patch notes pointed.]),
  ([What would go wrong if the factor were chosen after seeing which counts it produced?],
   [It could be tuned to give a preferred answer; fixing the rule first keeps the count
    honest.]),
)

== What it does and doesn't explain

The calibration tells you how much to discount the error bars. It doesn't tell you why they
are too small, and that matters for what else might be wrong.

#project[
  *Your data.* The real effects are not much larger than the placebos in the second patch:
  the median size of an effect is #n("placebo.vs_real.second.real.median_abs_beta_pp") points
  for the real tweaks against #n("placebo.vs_real.second.placebo.median_abs_beta_pp") for
  their window's placebos (first patch: #n("placebo.vs_real.first.real.median_abs_beta_pp")
  against #n("placebo.vs_real.first.placebo.median_abs_beta_pp")). The spread is card by card
  and persists across the two patches (measured on the earlier
  #n("const.earlier_tables.pages")-page tables). Clustering by player token instead of by run, on the
  runs that have a token, narrows the placebo spread (sd of z
  #n("checks.token.placebo.all.sd_z_run") clustered by run, #n("checks.token.placebo.all.sd_z_token")
  clustered by token) but doesn't bring it to one. #unverified[Why the spread is so large is
  not yet verified.] The status line in SPIROMETRY.md reads: "the clustered standard errors
  are calibrated" is *not met*.
]

#fig("fig_real_vs_placebo", [Size of each real tweak's effect against the spread of its own
  window's placebos.])

The most likely shape of the problem is that each card has its own slow wobble in how it is
valued from week to week, shared across runs and players, which clustering by run cannot
see. A model that let each card's pick rate drift would be the direct fix; it is not built.
The dose-response in @ch-dose is checked with placebo-scaled errors too, and its main
conclusion survives.

#watch[
  "We corrected the error bars" is not "we know why they were wrong". Say both halves: the
  correction and the open question.
]

#skill[
  *Stating limits honestly.* When a check fails, report the failure, the correction you
  applied, how the conclusions changed, and what is still unexplained.
]

#check(
  ([In the second patch, how do the real effects compare in size with the placebos'?],
   [Only a little larger: the typical real effect is close to the typical placebo effect,
    which is part of why so few second-patch tweaks pass the calibrated line.]),
  ([Clustering by player token narrows the placebo spread but not to one. What does that
    suggest?],
   [Players' repeated runs are part of the problem but not all of it; something else, likely
    card-level drift shared across players, remains.]),
  ([What is still unknown after the calibration?],
   [Why the clustered errors are too small: the cause of the large placebo spread is not
    verified.]),
)
