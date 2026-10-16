#import "../style.typ": *

= Counting: rates, averages and percentage points <ch-counting>

#lead[The small vocabulary every later chapter uses.]

== Pick rate is an average of ones and zeros

#picture[
  A basketball player's free-throw percentage is made shots divided by attempts. Write
  each attempt as a one (made) or a zero (missed) and the percentage is just the average of those
  ones and zeros. It also works as a chance: pick one of the player's attempts at random,
  and the percentage is the chance it went in.
]

#words[
  - *Pick rate*: picks divided by offers for one card, over some set of offers.
  - *Conditional probability* P(picked | offered): "the probability of picked, given
    offered". The vertical bar reads "given". The pick rate estimates it.
]

Each offer is a zero or a one, so the pick rate is the average of those numbers, and everything
that is true of averages is true of pick rates: they wobble less as the number of offers
grows (@ch-noise), and they can be compared across groups. The "given offered" part matters:
a card that is rarely offered can still have a high pick rate. Offers and picks are counted
separately, and the offer count itself is checked in @ch-checks.

#project[
  *Your data.* Parry was offered #n("tweak.parry.v0_103_2.n_treated_offers") times across the
  first patch's before and after blocks. Its pick rate was #n("tweak.parry.v0_103_2.treated_rate_before")
  before the patch and #n("tweak.parry.v0_103_2.treated_rate_after") after. Picked at random,
  an after-patch offer of Parry had about that chance of being taken.
]

#fig("fig_before_after", [Two first-patch tweaks' pick rates before and after (all
  after-weeks), with the same character's unchanged cards beside them.])

#watch[
  A pick rate is not a popularity count. A card can be taken more often in total simply
  because it is offered more often, with no change in how players value it. Always divide by
  offers.
]

#skill[
  *Choosing the unit and the denominator.* "Per what?" decides what a rate means. Here the
  unit is the offer, and the denominator is offers of that card, not runs or screens.
]

#check(
  ([Why is a pick rate the same thing as an average?],
   [Each offer is recorded as one if picked and zero if not; picks divided by offers is the
    average of those ones and zeros.]),
  ([What does P(picked | offered) mean in words?],
   [The probability that a card is taken, given that it was offered.]),
  ([A card's total number of picks rises after a patch. Why is that not enough to say
    players value it more?],
   [It might simply be offered more often. Only picks divided by offers, compared with
    similar cards, says whether players take it more when they see it.]),
)

== Percentage points against percent

#picture[
  An interest rate goes from two percent to three percent. It rose by one percentage point,
  and by fifty percent. Both are true; they answer different questions. Points subtract the
  two rates; percent divides them.
]

#words[
  - *Percentage point (pp, "points")*: the difference between two rates, by subtraction.
  - *Percent change (relative change)*: the difference divided by the starting rate.
]

Your notebooks and this guide report effects in percentage points. A relative change makes
a small card look dramatic and a popular card look calm, so it is shown only beside the
points.

#ftable(
  columns: (auto, auto, auto, auto, auto),
  [], [*Before*], [*After*], [*Change (points)*], [*Relative change*],
  [Parry], [#n("tweak.parry.v0_103_2.treated_rate_before")],
    [#n("tweak.parry.v0_103_2.treated_rate_after")], [#n("tweak.parry.v0_103_2.treated_change_pp")],
    [#n("tweak.parry.v0_103_2.treated_relative_change")],
  [Corrosive Wave], [#n("tweak.corrosive_wave.v0_103_2.treated_rate_before")],
    [#n("tweak.corrosive_wave.v0_103_2.treated_rate_after")],
    [#n("tweak.corrosive_wave.v0_103_2.treated_change_pp")],
    [#n("tweak.corrosive_wave.v0_103_2.treated_relative_change")],
)

#project[
  *Your data.* These are raw before and after rates. The headline figure for Corrosive Wave
  is #n("tweak.corrosive_wave.v0_103_2.all.beta_pp") points, not
  #n("tweak.corrosive_wave.v0_103_2.treated_change_pp"), because the method of @ch-did also
  subtracts what the unchanged cards did over the same builds: their pick rate went from
  #n("tweak.corrosive_wave.v0_103_2.control_rate_before") to
  #n("tweak.corrosive_wave.v0_103_2.control_rate_after").
]

#watch[
  Mixing up points and percent is one of the most common ways to misstate a result in an
  interview. "Parry's pick rate rose #n("tweak.parry.v0_103_2.treated_relative_change")" and
  "changed by #n("tweak.parry.v0_103_2.treated_change_pp") points" describe the same data; say
  which one you mean.
]

#skill[
  *Stating a change without ambiguity.* Give the unit (points or percent), the baseline and
  the comparison, every time.
]

#check(
  ([A card goes from one pick in five to one pick in four. Give the change in points and as
    a relative change.],
   [Five percentage points (twenty percent to twenty-five), and a relative change of a quarter.]),
  ([A notebook prints a pick-rate effect of three hundredths, on the scale where a pick
    rate runs from zero to one. What is that in words?],
   [About three percentage points more picks per offer than the comparison predicts.]),
  ([Why does this guide report effects in points rather than percent?],
   [Points don't depend on the starting rate, so effects on rare and popular cards are on the
    same footing; percent would exaggerate changes on rarely picked cards.]),
)

== Average, middle and spread

#words[
  - *Mean*: the ordinary average. *Median*: the middle value when the values are sorted.
    A few extreme values pull the mean but barely move the median.
  - *Variance* and *standard deviation (sd)*: how spread out individual values are. The sd is
    the square root of the variance and is in the same units as the values.
  - For a yes-or-no outcome with rate p, the variance is p(1 − p). It is largest when p is a half
    and small when p is near zero or one.
]

#picture[
  Ten people in a room earn ordinary salaries; then a billionaire walks in. The mean salary
  jumps; the median barely moves. That is why summaries of many cards in this project use the
  median: one wild card shouldn't decide the summary.
]

#project[
  *Your data.* Over weeks 0–3 after release, the median size of a tweak's effect (ignoring
  its sign) was #n("did.h3.first.median_abs_beta_pp") points in the first patch and
  #n("did.h3.second.median_abs_beta_pp") in the second. That gap is the first sign of the
  puzzle this guide keeps returning to.
]

The formula p(1 − p) explains something you will meet again. A card picked about half the
time is noisier per offer than a card picked rarely, because each offer could go either way.
Cards differ in how noisy their offers are, so their error bars differ for that reason alone
(@ch-regression).

#watch[
  A spread (sd) describes individual values; an error bar (@ch-noise) describes an estimate.
  A card's offers can be very spread out (each is a zero or a one) while its pick rate is known very
  precisely.
]

#skill[
  *Summarising many numbers robustly.* Report a median when a few values could be extreme,
  and check how much the mean and median disagree.
]

#check(
  ([Why does a card picked half the time give noisier offers than one picked a twentieth of
    the time?],
   [The variance of a yes-or-no outcome is p(1 − p), which is largest at one half: each offer is
    then most uncertain.]),
  ([Why do summaries over many tweaks in this guide use the median?],
   [A few cards with extreme effects would pull the mean; the median describes the typical
    tweak.]),
  ([What is the difference between the sd of a card's offers and the error bar on its pick
    rate?],
   [The sd describes how individual offers vary (each is a zero or a one). The error bar describes how
    much the pick rate, an average of many offers, would move on a fresh sample, and it shrinks
    as offers grow.]),
)
