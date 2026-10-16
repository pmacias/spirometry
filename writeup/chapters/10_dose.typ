#import "../style.typ": *

= Dose-response: do bigger changes move picks more? <ch-dose>

#lead[Whether the effect on picks is in proportion to the size of the number change.]

@ch-results looked at each tweak on its own. This chapter lines them up by how big each
change was and asks whether bigger changes moved picks more. It is the project's sharpest
result, and the source of its main puzzle.

== The dose and the ruler

#picture[
  A medicine works in doses. If a double dose helps more than a single dose, and a half dose
  less, you have good evidence that the medicine is doing the work and not something else that
  happened to the patients. A clean dose-response is one of the strongest signs that an effect
  is real.
]

#words[
  - *Dose*: the size of a numeric tweak.
  - *Ruler*: how the dose is measured. The primary ruler is *ln(new/old)*: the natural log of
    the new value divided by the old one, with the sign set by the change's direction. It
    treats going from four to five the same as going from eight to ten (both a quarter more),
    and a buff and a nerf of the same proportion as equal and opposite.
]

The ruler is applied to each tweak's *main field*, the number the change is about (damage,
block, the amount of a power). Tweaks without a single dose stay off the line: reworks,
cost changes, upgrade-only tweaks and mixed tweaks whose total doesn't move one way.

#project[
  *Your data.* Parry's main number went from #n("tweak.parry.v0_103_2.old") to
  #n("tweak.parry.v0_103_2.new"): a dose of #n("tweak.parry.v0_103_2.dose_x"). Corrosive Wave's
  went from #n("tweak.corrosive_wave.v0_103_2.old") to #n("tweak.corrosive_wave.v0_103_2.new"):
  #n("tweak.corrosive_wave.v0_103_2.dose_x"), negative because it was a nerf. A one-point
  damage buff on a card that dealt seven is a dose of #n("dose.example.ln_8_7").
]

#watch[
  The ruler is a choice, not a fact about the game. A card that goes from one to two of
  something doubles; whether that is "bigger" than ten more damage on a card that dealt fifty
  depends on how you measure. @ch-rulers tests whether the result depends on the ruler.
]

#skill[
  *Defining a continuous treatment.* When the treatment comes in amounts, choose and justify
  one scale before fitting, and plan to test others.
]

#check(
  ([What is the dose of a tweak, and what is the primary ruler?],
   [The size of the number change; the primary ruler is ln(new/old) of the main field, signed
    by the change's direction.]),
  ([Why does ln(new/old) treat going from four to five the same as eight to ten?],
   [Both are the same proportional change (a quarter more), and the log of a ratio depends
    only on the proportion.]),
  ([Why are reworks and upgrade-only tweaks kept off the dose-response line?],
   [A rework has no single number that measures its size; an upgrade-only tweak changes only
    the upgraded card, measured on very few offers, with no base value for some.]),
)

== Meta-regression

#picture[
  Combine readings from many thermometers, some precise and some shaky. You trust each one
  in proportion to its accuracy. And if they disagree by more than their errors allow, you
  admit that the rooms really are at different temperatures, not just that the thermometers
  are noisy.
]

#words[
  - *Meta-regression*: a regression across estimates. Each point is one tweak: its effect (in
    log-odds, @ch-regression) against its dose.
  - *Weighting by precision*: points with small SEs count more.
  - *Between-card scatter (τ)*: real differences between cards' effects beyond what their SEs
    explain. Same-sized changes can do different things to different cards.
  - *Random effects*: the model that allows for τ. Each card's true effect is the line plus
    its own deviation, and τ is estimated from the data.
  - *Intercept*: the line's value at a dose of zero, the effect of merely being in the patch
    notes.
]

Effects are in log-odds here, not points, so that cards with very different starting pick
rates are comparable (@ch-regression). The heterogeneity statistic Q measures how much the
points scatter around the line compared with their SEs; a Q far above its degrees of freedom
means τ is real.

#project[
  *Your data.* With one line for both patches (the notebooks' set of
  #n("dose.triage.h3.one_slope.n") tweaks, weeks 0–3): slope
  #n("dose.triage.h3.one_slope.slope_pm") log-odds per unit of ln(new/old), intercept
  #n("dose.triage.h3.one_slope.intercept_pm"), τ = #n("dose.triage.h3.one_slope.tau"), and Q =
  #n("dose.triage.h3.one_slope.q") on #n("dose.triage.h3.one_slope.df") degrees of freedom.
  The intercept is close to zero: no sign that appearing in the patch notes moves picks by
  itself. The one-point damage buff above (dose #n("dose.example.ln_8_7")) predicts
  #n("dose.example.log_odds") log-odds, about #n("dose.example.pp_at_20") points for a card
  picked one time in five.
]

#watch[
  τ is large: different cards respond very differently to same-sized changes. The line
  describes the average card, and any single card can sit far from it.
]

#skill[
  *Combining many noisy estimates.* Weight each by its precision, allow for real differences
  between them, and report how large those differences are.
]

#check(
  ([In a meta-regression, what is each data point?],
   [One tweak: its estimated effect (in log-odds) plotted against its dose, with its SE as
    the weight.]),
  ([What does τ measure, and what does a large τ tell you?],
   [Real differences between cards' effects beyond their SEs. A large τ means same-sized
    changes did quite different things to different cards.]),
  ([What would a large positive intercept have meant?],
   [That being in the patch notes raised picks by itself, even with a dose of zero, for
    example from attention.]),
)

== One slope, then one per patch

#words[
  - *Slope per patch*: a separate line for each patch, so each patch gets its own
    dose-response.
  - *Patch difference (z diff)*: the difference between the two slopes divided by its SE.
]

#fig("fig_dose", [Effect (log-odds) against dose for each tweak on the line, by patch, with
  each patch's fitted line (primary spec, weeks 0–3).])

#ftable(
  columns: (auto, auto, auto, auto),
  [*Weeks 0–3*], [*First patch slope*], [*Second patch slope*], [*z diff*],
  [Primary spec], [#n("dose.primary.h3.slope_first_pm")], [#n("dose.primary.h3.slope_second_pm")],
    [#n("dose.primary.h3.z_diff")],
  [Primary spec, placebo-scaled SEs], [#n("dose.primary.h3.placebo_robust_sd.slope_first_pm")],
    [#n("dose.primary.h3.placebo_robust_sd.slope_second_pm")],
    [#n("dose.primary.h3.placebo_robust_sd.z_diff")],
  [The notebooks' set], [#n("dose.triage.h3.slope_first_pm")], [#n("dose.triage.h3.slope_second_pm")],
    [#n("dose.triage.h3.z_diff")],
)

#project[
  *Your data.* The primary spec has #n("dose.primary.h3.n_first") first-patch and
  #n("dose.primary.h3.n_second") second-patch tweaks on the line. It differs from the
  notebooks' set of #n("dose.triage.h3.n_tweaks") in two tweaks, by decisions of October 2026:
  Reflect is on the line as a nerf (its base and upgraded totals both fall), and Debilitate's
  second-patch nerf is off (a shorter debuff whose size can't be measured; @ch-rulers). The
  first patch has a steep line. The second patch's line is flat: its slope is
  #n("rulers.primary.ln.ratio_pm") times the first patch's. A level shift for the second
  patch alone (#n("dose.triage.h3.patch_shift.second_pm")) does not capture the difference; the
  slope does. The placebo-scaled version multiplies each patch's SEs by its all-weeks placebo
  factor (#n("dose.primary.h3.placebo_robust_sd.factor_first") and
  #n("dose.primary.h3.placebo_robust_sd.factor_second")); the slopes move a little and the
  difference stays. All weeks, the notebooks' set: #n("dose.triage.all.slope_first_pm") and
  #n("dose.triage.all.slope_second_pm").
]

The placebo-scaled SEs barely widen the slopes' error bars, which looks odd after
@ch-placebo. The reason is τ. The slope's uncertainty comes mostly from how much cards
scatter around the line, not from each card's own SE; when the SEs grow, the model
attributes less of the scatter to τ, and the total barely changes.

#plain[
  Buffs and nerfs separately (notebooks' set, with a patch term): buff slope
  #n("dose.triage.h3.buff_nerf.slope_buff_pm"), nerf slope
  #n("dose.triage.h3.buff_nerf.slope_nerf_pm"). There are few nerfs on the line, and the two
  slopes can't be told apart.
]

#watch[
  A z diff near three says the two slopes differ by more than chance would usually give. It
  doesn't say why, and it is only as solid as the ruler and the points behind it
  (@ch-rulers).
]

#skill[
  *Modelling an effect against a continuous dose, and letting the slope vary by group.* Fit
  the shared line first, then ask whether groups need their own; compare slopes with their
  joint uncertainty, not by eye.
]

#check(
  ([Give the two patches' slopes under the primary spec, with SEs.],
   [First #n("dose.primary.h3.slope_first_pm"), second #n("dose.primary.h3.slope_second_pm")
    log-odds per unit of ln(new/old), weeks 0–3.]),
  ([Why did placebo-scaling the SEs barely change the slopes' error bars?],
   [The slopes' uncertainty is dominated by the real scatter between cards (τ); as the SEs
    grow, less of the scatter is attributed to τ, so the total uncertainty barely moves.]),
  ([Which two tweaks distinguish the primary spec from the notebooks' set, and how?],
   [Reflect is on the line in the primary spec (both its totals fall), and Debilitate's
    second-patch nerf is off (its size can't be measured).]),
)

== Same size, same precision, different effect

The obvious objections to a flat second patch are that its tweaks were smaller, or measured
less precisely. Neither holds.

#ftable(
  columns: (auto, auto, auto, auto, auto),
  [*Primary spec, weeks 0–3*], [*Tweaks*], [*Median dose*], [*Median effect (points)*],
    [*Median SE (log-odds)*],
  [First patch], [#n("dose.same_size.first.n")], [#n("dose.same_size.first.median_abs_dose")],
    [#n("dose.same_size.first.median_abs_beta_pp")], [#n("dose.same_size.first.median_se_lo")],
  [Second patch], [#n("dose.same_size.second.n")], [#n("dose.same_size.second.median_abs_dose")],
    [#n("dose.same_size.second.median_abs_beta_pp")], [#n("dose.same_size.second.median_se_lo")],
)

#project[
  *Your data.* The two patches' tweaks on the line are the same size (median dose
  #n("dose.same_size.first.median_abs_dose") against #n("dose.same_size.second.median_abs_dose"))
  and measured about equally well (median SE #n("dose.same_size.first.median_se_lo") against
  #n("dose.same_size.second.median_se_lo") log-odds). The second patch's moved picks by
  #n("dose.same_size.second.median_abs_beta_pp") points against
  #n("dose.same_size.first.median_abs_beta_pp"): about half as much, with no relation to size.
]

#watch[
  "Measured about equally well" uses the clustered SEs, which @ch-placebo found too small by
  different factors in the two patches. Equal precision is therefore not established; the
  placebo factors suggest the second patch's estimates are, if anything, somewhat less
  distorted.
]

#skill[
  *Ruling out the boring explanations for a difference.* Before explaining why two groups
  differ, check that they are comparable on the things that would trivially produce the
  difference (here, size and precision).
]

#check(
  ([What two simple explanations does the same-size table rule out?],
   [That the second patch's tweaks were smaller, and that they were measured less precisely.]),
  ([Why is "equal precision" stated with a caveat?],
   [It uses the clustered SEs, which the placebo test showed are too small by different
    factors in the two patches.]),
  ([If the second patch's tweaks had been half the size, would a flat line be surprising?],
   [Less so: smaller doses give smaller effects and less leverage for a slope, so a flat line
    would be harder to tell from a shallow one.]),
)

== What was found

*What the numbers show.* In the first patch, bigger number changes moved picks more, in
proportion: about #n("dose.primary.h3.slope_first") log-odds per unit of ln(new/old), so a
tweak's effect in log-odds was roughly its dose times that slope. In the second patch there is no such relation: the slope is
#n("dose.primary.h3.slope_second_pm"), close to zero, for tweaks of the same sizes measured about
as precisely. The two slopes differ by #n("dose.primary.h3.z_diff") SEs, or
#n("dose.primary.h3.placebo_robust_sd.z_diff") with placebo-scaled errors. Across both patches
the intercept is near zero, and cards scatter widely around any line (τ =
#n("dose.triage.h3.one_slope.tau")).

*How much to trust it, and why.* The first patch's slope is solid: it is far from zero under
every error bar and every check so far, though @ch-explanations shows that the choice of
controls trims it somewhat. The second patch's flatness is the result to be careful with.
Its slope's interval is wide: it can't rule out a slope of about half the first patch's,
only one of the same size. And the difference between the patches depends on how the dose is
measured and on a few influential tweaks, which is what @ch-rulers tests. Why the second
patch did less is not answered by this chapter.

#skill[
  *Stating a slope in words someone can use.* Translate a coefficient into a concrete example
  (a one-point buff on a seven-damage card) and say what range of slopes the data allow, not
  only the best estimate.
]

#check(
  ([Explain the first patch's dose-response to a friend with one concrete example.],
   [A one-point damage buff on a card that dealt seven is a dose of #n("dose.example.ln_8_7").
    The shared line predicts #n("dose.example.log_odds") log-odds from it, about
    #n("dose.example.pp_at_20") points of pick rate for a card picked one time in five; the
    first patch's own, steeper line predicts somewhat more.]),
  ([What can and can't the second patch's slope rule out?],
   [It rules out a slope as large as the first patch's. Its wide interval can't rule out a
    slope of about half the first patch's.]),
  ([What would go wrong if you reported only "the second patch has no dose-response"?],
   [It would hide the uncertainty (a moderate slope is still possible) and the dependence on
    the ruler and on a few tweaks, which @ch-rulers shows.]),
)
