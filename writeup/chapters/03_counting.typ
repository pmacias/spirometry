#import "../style.typ": *

= Counting: rates, averages and percentage points <ch-counting>

#lead[The small vocabulary every later chapter uses, and the spread of a single yes-or-no
  offer.]

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
  - *Bernoulli trial*: one yes-or-no outcome that is yes with some fixed probability. One
    offer is a Bernoulli trial: picked with probability $p$, not picked otherwise.
  - *Estimator*: a recipe that turns data into a guess at an unknown number. The pick rate is
    the estimator of $p$.
]

Write $p$ for the true chance that an offer of a card is picked, $p = P("picked" | "offered")$:
the share of picks you would see over endlessly many offers of that card, to the same kind of
players, in the same build. You never see $p$. You see $n$ offers, with outcomes $y_i$ (one for
a pick, zero otherwise, @eq-offer), of which $k$ were picks. The pick rate is

$ hat(p) = k / n = 1 / n sum_(i = 1)^n y_i $ <eq-phat>

In words: the estimated pick rate is the number of picks divided by the number of offers,
which is the same as the average of the offers' zeros and ones. Each offer is a Bernoulli
trial with $P(y_i = 1) = p$, so its expected value is

$ "E"[y_i] = 1 dot p + 0 dot (1 - p) = p $ <eq-bern-mean>

In words: the long-run average of one offer's outcome is the pick probability itself, because
a one turns up a share $p$ of the time and a zero the rest. Averaging $n$ offers keeps that
centre, $"E"[hat(p)] = p$, so the pick rate is aimed at the right number; @ch-noise works out
how far it scatters around it.

Each offer is a zero or a one, so the pick rate is an average, and everything that is true of
averages is true of pick rates: they wobble less as the number of offers grows (@ch-noise),
and they can be compared across groups. The "given offered" part matters: a card that is
rarely offered can still have a high pick rate. Offers and picks are counted separately, and
the offer count itself is checked in @ch-checks.

#project[
  *Your data.* Parry was offered #n("tweak.parry.v0_103_2.n_treated_offers") times across the
  first patch's before and after blocks. Its pick rate was #n("tweak.parry.v0_103_2.treated_rate_before")
  before the patch and #n("tweak.parry.v0_103_2.treated_rate_after") after. Picked at random,
  an after-patch offer of Parry had about that chance of being taken: $hat(p)$ for the after
  block is #n("tweak.parry.v0_103_2.treated_rate_after"), an estimate of the unknown $p$.
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
    average of those ones and zeros (@eq-phat).]),
  ([What does P(picked | offered) mean in words?],
   [The probability that a card is taken, given that it was offered.]),
  ([What is the difference between $p$ and $hat(p)$?],
   [$p$ is the true pick probability, which you never see; $hat(p)$ is the pick rate computed
    from the offers you have, an estimate of $p$.]),
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

For a rate that moves from $p_0$ to $p_1$:

$ "change in points" = p_1 - p_0, quad "relative change" = (p_1 - p_0) / p_0 $ <eq-points-percent>

In words: the change in points is the new rate minus the old one (printed as points by
multiplying by a hundred); the relative change is that difference divided by where the rate
started. The same change in points is a large relative change for a card that started low and a
small one for a card that started high.

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

There is a third scale, used when cards with very different starting rates are lined up
against each other: log-odds, $ln(p slash (1 - p))$. It behaves like an astronomer's magnitude
scale, where the same factor of brightness is the same number of magnitudes for a bright star
or a faint one. @ch-regression defines it (@eq-logit) and shows why the same push in log-odds
is many points for a card picked half the time and few for a card picked rarely.

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
  - *Variance* and *standard deviation (SD)*: how spread out individual values are. The SD is
    the square root of the variance and is in the same units as the values.
  - For a yes-or-no outcome with rate p, the variance is p(1 − p). It is largest when p is a half
    and small when p is near zero or one.
]

For values $x_1, dots, x_n$ with mean $overline(x)$:

$ overline(x) = 1 / n sum_i x_i, quad s^2 = 1 / n sum_i (x_i - overline(x))^2, quad
  s = sqrt(s^2) $ <eq-mean-var>

In words: the mean is the sum divided by the count; the variance $s^2$ is the average squared
distance from the mean; the SD $s$ is its square root, back in the units of the values. (Many
formulas divide by $n - 1$ instead of $n$ for the variance; the difference matters only for
small samples, and @ch-regression meets it as a small-sample factor.) The median is the value
with half the $x_i$ below it and half above.

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

#watch[
  A spread (SD) describes individual values; an error bar (@ch-noise) describes an estimate.
  A card's offers can be very spread out (each is a zero or a one) while its pick rate is known very
  precisely.
]

#skill[
  *Summarising many numbers robustly.* Report a median when a few values could be extreme,
  and check how much the mean and median disagree.
]

#check(
  ([Why do summaries over many tweaks in this guide use the median?],
   [A few cards with extreme effects would pull the mean; the median describes the typical
    tweak.]),
  ([In @eq-mean-var, why is the variance in squared units while the SD is in the values'
    units?],
   [The variance averages squared distances, so its units are squared; the square root undoes
    that.]),
  ([What is the difference between the SD of a card's offers and the error bar on its pick
    rate?],
   [The SD describes how individual offers vary (each is a zero or a one). The error bar describes how
    much the pick rate, an average of many offers, would move on a fresh sample, and it shrinks
    as offers grow.]),
)

== The spread of one offer, and why we square

@ch-noise builds the error bar of a pick rate from "the spread of one offer". That phrase needs
unpacking, because one offer is a yes or a no, and spread sounds like something only a
continuous measurement has.

#words[
  - *Signed distance*: a value minus the mean, with its sign. *Absolute distance*: the same
    without the sign.
  - *Root-mean-square (RMS)*: square each distance, average the squares, take the square
    root. The SD is the RMS distance from the mean.
  - *Mean absolute deviation (MAD)*: the average absolute distance from the mean. A real
    measure of spread, but a different one.
  - *Plug-in estimate*: using $hat(p)$ wherever a formula needs the unknown $p$.
]

#picture[
  A seesaw: put a weight of $1 - p$ at zero and a weight of $p$ at one, on a weightless plank.
  The plank balances at $p$, the mean. How hard it is to spin the plank about that balance
  point is its moment of inertia, which is the variance; the SD is the radius of gyration, the
  distance from the balance point at which all the weight could sit and spin the same way.
  For two weights, that picture works where a bell curve doesn't.
]

One offer's histogram is two bars: height $1 - p$ at zero and height $p$ at one. Its mean is
$p$ (@eq-bern-mean). The distances from the mean are $1 - p$ for a pick and $-p$ for a skip.
First try averaging them with their signs:

$ "E"[y - p] = p (1 - p) + (1 - p)(-p) = 0 $ <eq-signed>

In words: the average signed distance from the mean is always zero, for any $p$, because the
mean is the balance point: the picks' distance above it, weighted by how often they happen,
exactly cancels the skips' distance below. Signed distances can't measure spread. Squaring
makes every distance positive, so nothing cancels:

$ "Var"(y) = "E"[(y - p)^2] = p (1 - p)^2 + (1 - p) p^2 = p (1 - p) $ <eq-bern-var>

In words: the variance of one offer is the probability-weighted average of the squared
distances, which simplifies to $p(1 - p)$. Its square root is the SD of one offer:

$ "SD"(y) = sqrt(p (1 - p)) $ <eq-bern-sd>

In words: the spread of a single yes-or-no offer is the square root of the pick probability
times the skip probability. It is largest at a coin flip, where it is a half, and shrinks to
zero as $p$ approaches zero or one, where every offer goes the same way.

#mathfull[
  Two shortcuts to @eq-bern-var. First, factor: $p(1 - p)^2 + (1 - p)p^2 = p(1 - p)[(1 - p)
  + p] = p(1 - p)$. Second, use $"Var"(y) = "E"[y^2] - "E"[y]^2$. A zero or one squared is
  itself, so $y^2 = y$ and $"E"[y^2] = p$; then $"Var"(y) = p - p^2 = p(1 - p)$.

  The mean absolute deviation is the same average without squares:
  $"MAD" = p(1 - p) + (1 - p)p = 2p(1 - p)$. Compare it with the SD:
  $2p(1 - p) <= sqrt(p(1 - p))$ is the same as $2 sqrt(p(1 - p)) <= 1$, which holds because
  $p(1 - p)$ is never more than a quarter. So the MAD is at most the SD, equal only at a coin
  flip. That is general: for any distribution the RMS of the distances is at least their plain
  average, because squaring gives extra weight to the large ones.
]

*Why squares and not plain distances?* Not because squares are the only sensible measure, but
because squared spreads add. For independent pieces, the variance of a sum is the sum of the
variances (@ch-noise derives it); absolute deviations have no such rule. That one property is
what makes the error bar of an average shrink with the square root of the number of offers, and
what lets errors be combined "in quadrature". The order of operations matters for the same
reason: RMS means square, then average, then root. Root each squared distance before averaging
and you are back to the MAD.

#fig("fig_toy_bernoulli_sd", width: medium, [A worked example, not your data: the SD of one
  yes-or-no offer, $sqrt(p(1 - p))$, at every pick probability. Largest at a coin flip, zero
  at the ends.])

#project[
  *A worked example, not your data.* The three quantities at three pick probabilities:

  #align(center, ftable(
    columns: (auto, auto, auto, auto, auto),
    [$p$], [*Signed average*], [*Variance* $p(1 - p)$], [*SD (RMS)*], [*MAD*],
    [#n("toy.bernoulli_spread.p50.p")], [#n("toy.bernoulli_spread.p50.signed")],
      [#n("toy.bernoulli_spread.p50.var")], [#n("toy.bernoulli_spread.p50.sd")],
      [#n("toy.bernoulli_spread.p50.mad")],
    [#n("toy.bernoulli_spread.p20.p")], [#n("toy.bernoulli_spread.p20.signed")],
      [#n("toy.bernoulli_spread.p20.var")], [#n("toy.bernoulli_spread.p20.sd")],
      [#n("toy.bernoulli_spread.p20.mad")],
    [#n("toy.bernoulli_spread.p05.p")], [#n("toy.bernoulli_spread.p05.signed")],
      [#n("toy.bernoulli_spread.p05.var")], [#n("toy.bernoulli_spread.p05.sd")],
      [#n("toy.bernoulli_spread.p05.mad")],
  ))

  The signed average is zero every time; the variance matches $p(1 - p)$; the SD is never
  below the MAD, and the two agree only at a coin flip.

  *Your data.* Parry's before-patch pick rate was #n("tweak.parry.v0_103_2.treated_rate_before"),
  so a single before-patch offer of Parry was fairly predictable (mostly not picked), and its
  SD sat well below the coin-flip maximum. After the patch the rate was close to its controls',
  #n("tweak.parry.v0_103_2.treated_rate_after"), and each offer was less predictable. In
  practice $p$ is unknown, so formulas use the plug-in $hat(p)$. That is fine with thousands of
  offers; @ch-noise shows where it breaks.
]

#incode("teaching_sims.bernoulli_spread", [One offer's signed average distance, variance, SD
  and MAD, at a few pick probabilities.])[
  *What goes in:* a few values of $p$. *What comes out:* the table above and the curve of the
  figure. The lines that matter: `d_pick, d_skip = 1 - p, 0 - p` are the two distances from
  the mean. `signed` is @eq-signed, always zero. `var` is @eq-bern-var, written as "square,
  then average"; `sd = np.sqrt(var)` takes the root last, @eq-bern-sd. `mad` averages the plain
  distances instead. Swap the order (root each square first, then average) and `sd` turns
  into `mad`.
]

#mixup[
  You might read "the spread of one offer" as meaningless, because one offer is a yes or a no,
  not a measurement with a width. The spread is not of one observed offer but of the
  _process_ that produces offers: a two-bar histogram with weight $1 - p$ at zero and $p$ at
  one. That histogram has a mean and a variance like any other (@eq-bern-var), and it is what
  @ch-noise divides by the square root of the number of offers.
]

#mixup[
  You might work the spread at a coin flip and get the right-looking numbers by the wrong
  route: average the plain distances (a half), then square or root that and call it the
  variance or the SD. At $p$ of a half every quantity is a half or a quarter, so the mistake
  can't show. Try $p$ of #n("toy.bernoulli_spread.p20.p") instead: the plain distances average
  #n("toy.bernoulli_spread.p20.mad") (the MAD), but the SD is #n("toy.bernoulli_spread.p20.sd"),
  the root of the average squared distance, #n("toy.bernoulli_spread.p20.var"). The order is
  square, average, root.
]

#mixup[
  You might reach for "about two-thirds of values lie within one SD of the mean". That reading
  belongs to the bell curve (@ch-noise). For one offer at $p$ of #n("toy.bernoulli_spread.p20.p"),
  one SD either side of the mean runs from below zero to well short of one: it contains the bar
  at zero and misses the bar at one, and no offer ever sits at the mean. For two bars, use the
  seesaw picture instead.
]

#watch[
  The SD of one offer is fixed by $p$; more data doesn't shrink it. What shrinks with more data
  is the error bar on the pick rate (@ch-noise). Keeping the two apart is half of reading any
  error bar correctly.
]

#skill[
  *Knowing what a summary does to the data.* Before using a spread measure, know what it
  weights heavily (squares weight large distances), what it ignores (signs), and which rules it
  obeys (variances add; absolute deviations don't).
]

#check(
  ([Work $p$ of #n("toy.bernoulli_spread.p20.p") by hand: the two distances from the mean, the
    variance and the SD.],
   [A pick sits one minus #n("toy.bernoulli_spread.p20.p") above the mean, a skip
    #n("toy.bernoulli_spread.p20.p") below it. The variance is the probability-weighted average
    of their squares, #n("toy.bernoulli_spread.p20.var"), which is $p(1 - p)$; the SD is its
    root, #n("toy.bernoulli_spread.p20.sd").]),
  ([Why can't the average signed distance from the mean measure spread?],
   [It is always zero: the mean is the balance point, so the weighted distances above and below
    it cancel (@eq-signed).]),
  ([Why does a card picked half the time give noisier offers than one picked a twentieth of
    the time?],
   [The variance of a yes-or-no outcome is p(1 − p), which is largest at one half: each offer is
    then most uncertain.]),
  ([Why is "about two-thirds within one SD" wrong for one offer?],
   [It is a property of the bell curve. One offer has two bars; one SD either side of the mean
    contains the bar at zero and misses the bar at one, and no offer sits at the mean.]),
  ([Why does the guide use squared distances rather than absolute ones?],
   [Squared spreads add: the variance of a sum of independent pieces is the sum of their
    variances. That rule gives the square-root law for error bars and lets errors combine in
    quadrature.]),
)
