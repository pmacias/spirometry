#import "../style.typ": *

= Noise: standard errors, intervals, and "clearly nonzero" <ch-noise>

#lead[How much a number could move by luck alone, where the bell curve comes from, and when an
  estimate is clearly different from zero.]

== The soup and the coin

#picture[
  To check whether soup is salty enough you taste one spoonful. Another spoonful would taste
  a little different. If the pot is well stirred, a spoonful is a good guide; if you only
  taste three drops, you are guessing. A coin flipped ten times can easily land heads seven
  times. Flipped ten thousand times it lands very close to half. The rule of thumb: a hundred
  times more data gives ten times less wobble.
]

#words[
  - *Standard error (SE)*: the typical size of the wobble in an estimate: roughly how far it
    would move if you could redraw the sample.
  - *Independent*: two outcomes are independent when knowing one tells you nothing about the
    other. Offers from different runs are close to independent; offers from the same run
    are not quite (@ch-regression).
  - *Square-root rule*: the SE shrinks with the square root of the number of observations n.
    Four times the data halves the SE.
  - For a rate p measured on n offers, SE = √(p(1 − p) / n): the spread of one offer
    (@ch-counting) divided by the square root of the number of offers.
]

The formula comes from one rule about variances. For independent quantities, variances add:

$ "Var"(sum_(i = 1)^n y_i) = sum_(i = 1)^n "Var"(y_i) quad "(independent" y_i ")" $ <eq-var-sum>

In words: the variance of a sum of independent pieces is the sum of their variances. The
pick rate $hat(p)$ is that sum divided by $n$, and dividing by $n$ divides a variance by
$n^2$. Each offer has variance $p(1 - p)$ (@eq-bern-var), so

$ "Var"(hat(p)) = 1 / n^2 dot n p (1 - p) = (p (1 - p)) / n $ <eq-var-phat>

In words: the variance of a pick rate is one offer's variance divided by the number of offers.
Its square root is the standard error:

$ "SE"(hat(p)) = sqrt((p (1 - p)) / n) = "SD"(y) / sqrt(n) $ <eq-se>

In words: the standard error of a pick rate is the spread of one offer, $sqrt(p(1 - p))$,
divided by the square root of the number of offers. This is the square-root rule: four times
the offers, half the SE. In practice $p$ is unknown and the plug-in version
$hat("SE") = sqrt(hat(p)(1 - hat(p)) slash n)$ is used.

#mathfull[
  @eq-var-sum is a special case of the general rule for the variance of a sum,
  $ "Var"(sum_i y_i) = sum_i "Var"(y_i) + sum_(i != j) "Cov"(y_i, y_j) $
  In words: the variance of a sum is the sum of the variances plus every pair's covariance
  (how much the two move together). Independent pieces have zero covariance, which leaves
  @eq-var-sum. Two more facts give @eq-var-phat: a constant comes out of a variance squared,
  $"Var"(a X) = a^2 "Var"(X)$, so dividing by $n$ divides by $n^2$; and the $n$ offers each
  contribute $p(1 - p)$. The covariance terms are exactly what @ch-regression puts back when
  offers in one run are related: the design effect there is this sum of covariances, measured.
]

#project[
  *Your data.* Parry had #n("tweak.parry.v0_103_2.n_treated_offers") offers across its two
  blocks, and its effect is estimated with an SE of #n("tweak.parry.v0_103_2.all.beta_pp_se")
  points. Royalties, an upgrade-only tweak measured on upgraded offers only, had
  #n("tweak.royalties.v0_107_1.n_treated_offers") such offers, and its SE is
  #n("tweak.royalties.v0_107_1.all.beta_pp_se") points: far fewer offers, far more wobble.
]

#fig("fig_se_curve", [Standard error of a single pick rate as the number of offers grows,
  from the formula, with one tweak's offer count marked.])

#watch[
  The SE is about the estimate, not the individual offers. A card with many offers can have a
  tiny SE even though each offer is a coin-like zero or one. And @eq-se assumes independent
  offers; the error bars in this guide are built so as not to assume it (@ch-regression), and
  checked against reality in @ch-placebo.
]

#skill[
  *Quantifying uncertainty.* Every estimate you report should come with a statement of how
  much it could move by chance, and you should be able to say roughly how that shrinks with
  more data.
]

#check(
  ([You double the number of offers. By what factor does the SE of a pick rate shrink?],
   [By the square root of two: it becomes about seven tenths of what it was.]),
  ([Walk through @eq-var-phat in words: where does the $n^2$ come from, and where does one of
    the $n$'s go?],
   [Dividing the sum by $n$ divides its variance by $n^2$. The sum's variance is $n$ times one
    offer's variance, which cancels one $n$, leaving $p(1 - p) slash n$.]),
  ([Why is Royalties' SE so much larger than Parry's?],
   [Royalties' change was to the upgraded card only, so it is measured on upgraded offers,
    of which there were only a few hundred; Parry had many thousands of offers.]),
  ([In the soup picture, what plays the role of "a well-stirred pot"?],
   [Offers that are like a random draw from the population, so that each spoonful (sample)
    represents the whole.]),
)

== The spread of the data against the spread of the estimate

Two different spreads have now appeared, and they are easy to confuse because both are
called something-deviation and both are drawn as histograms.

#words[
  - *SD (of the data)*: how spread out the individual values are. For offers, the two bars of
    @ch-counting. More data doesn't shrink it.
  - *SE (of the estimate)*: how spread out the estimate would be over many imagined reruns of
    the whole study. More data shrinks it.
  - *Sampling distribution*: the histogram of an estimate over those imagined reruns. Its
    width is the SE.
]

#picture[
  A star observed with a photon counter. The counts in single short exposures scatter a lot:
  that is the SD, and it is set by the star and the detector. The uncertainty on the star's
  mean flux after a long night is small: that is the SE, and it shrinks as the photons pile up.
  More photons never change the first; they shrink the second.
]

You can't rerun a patch: there is one v0.103.2, played once. So the SE is computed from the
one dataset you have, as @eq-se does: the scatter you can see between offers stands in for the
reruns you can't do. Another way to see it is to split the data in two, estimate on each half
and watch how far the halves disagree (*split-sample* or, resampling with replacement, the
*bootstrap*). Each half has half the offers, so its SE is about $sqrt(2)$ times larger.

#fig("fig_toy_sd_vs_se", [A simulation with known truth. Left: one dataset of
  #n("toy.sd_vs_se.n") offers, its two bars, and their SD. Right: the pick rate over
  #n("toy.sd_vs_se.n_reruns") simulated reruns of the same study; its width is the SE, and the
  curve is the bell that @eq-se and the next section predict.])

#project[
  *A simulation with known truth.* A card with a true pick rate of #n("toy.sd_vs_se.p_true"),
  #n("toy.sd_vs_se.n") offers per dataset. In one dataset the SD of the offers is
  #n("toy.sd_vs_se.sd_data"). Over #n("toy.sd_vs_se.n_reruns") reruns the pick rate scatters
  with an SD of #n("toy.sd_vs_se.sd_reruns"), and @eq-se predicts #n("toy.sd_vs_se.se_formula").
  The two widths differ by a factor of #n("toy.sd_vs_se.sqrt_n"), the square root of the number
  of offers. Only the second is an error bar.
]

#incode("teaching_sims.sd_vs_se", [One dataset against many imagined reruns, in a
  simulation.])[
  *What goes in:* a true pick rate, offers per dataset and a number of reruns. *What comes
  out:* the SD of one dataset's offers, the spread of the pick rate over the reruns, and the
  formula's SE. The lines that matter: `one_dataset = rng.random(n) < p_true` draws one
  dataset of zeros and ones (the SD world); `rng.binomial(n, p_true, size=n_reruns) / n`
  draws a whole study's pick count at once, for every rerun (the SE world); `se` is @eq-se.
  Comparing `sd_reruns` with `se_formula` is the check that @eq-se is right.
]

#mixup[
  You might picture the error bar as the width of a histogram of the data: take each card's
  pick rates, measure the middle two-thirds of that spread, and take the median width over
  cards. That describes the data, so it is an SD, not an SE. An SE belongs to one estimate:
  imagine rerunning the whole patch with fresh players and fresh offers, compute the estimate
  each time, and histogram those estimates. The half-width of that imaginary histogram is the
  SE. A sentence like "the median SE over the second patch's tweaks" means: each tweak has one
  estimate and one SE; take the median of those SEs.
]

#watch[
  When someone quotes a spread, ask "of what?". The spread of picks across offers and the
  spread of an effect estimate across imagined reruns can differ by a factor of a hundred, and
  only the second tells you how far to trust the number.
]

#skill[
  *Telling a property of the data from a property of an estimate.* Means, SDs and histograms
  of observations describe the data; SEs and intervals describe how well a number computed
  from the data is pinned down.
]

#check(
  ([If the second patch had twice as many runs, which would shrink: the SD of picks or the SE
    of each effect? By how much?],
   [The SE, by about the square root of two (to about seven tenths of its size). The SD of a
    single offer is set by $p$ and doesn't change.]),
  ([You can't rerun a patch. Where does its SE come from, then?],
   [From the scatter inside the one dataset: @eq-se divides the spread of one offer by the
    square root of the number of offers. Splitting the data or resampling it (the bootstrap)
    is another way to get the same thing.]),
  ([Split a dataset in half and estimate on each half. Roughly how much larger is each half's
    SE than the full data's?],
   [About $sqrt(2)$ times larger, because each half has half the offers.]),
)

== Why the bell: two theorems about averages

Why is the histogram of estimates over reruns a bell, and why is it centred on the truth? Two
theorems answer different halves of that question, and they are often blended.

#words[
  - *Law of large numbers (LLN)*: as the number of offers grows, the pick rate homes in on the
    true $p$. It is about _where the estimate goes_.
  - *Central limit theorem (CLT)*: at a given number of offers, the pick rate's scatter over
    imagined reruns is close to a bell (Gaussian, or normal) curve with width $"SE"$. It is
    about _the size and shape of the error_.
  - *Normal distribution*, $cal(N)(mu, sigma^2)$: the bell curve with centre $mu$ and SD
    $sigma$. The *standard normal*, $cal(N)(0, 1)$, has centre zero and SD one; $Phi$ is its
    cumulative probability.
]

Write $hat(p)_n$ for the pick rate after $n$ offers. The law of large numbers says

$ hat(p)_n -> p quad "as" quad n -> infinity $ <eq-lln>

In words: the pick rate converges to the true pick probability as offers pile up. Precisely:
for any fixed distance, however small, the chance that $hat(p)_n$ is further than that from
$p$ shrinks to zero. It says the estimate converges, and nothing about how
fast or in what shape. The central limit theorem says how:

$ (hat(p)_n - p) / "SE"(hat(p)_n) quad "is approximately" quad cal(N)(0, 1) "for large" n $ <eq-clt>

In words: measured in units of its own standard error, the pick rate's error follows the
standard bell curve once there are enough offers. Equivalently, $hat(p)_n$ is approximately
normal with centre $p$ and SD $"SE" = sqrt(p(1 - p) slash n)$.

#picture[
  A zoom lens on a shrinking cloud. The law of large numbers says the cloud of possible
  estimates collapses onto the truth as data come in. The central limit theorem says that if
  you zoom in by $sqrt(n)$ as it collapses, it always looks like the same bell. A Galton board
  shows why it is a bell at all: each offer nudges the average up or down, landing at an
  extreme needs every nudge to go the same way, which is rare, and most paths mix and land near
  the middle.
]

#fig("fig_toy_lln_clt", [A simulation with known truth, true pick rate
  #n("toy.lln_clt.p"). Top: the pick rate over #n("toy.lln_clt.n_reruns") reruns at a fixed
  number of offers $n$ (the central limit theorem's picture): two bars, three lumpy bars, a
  lopsided hump, then a bell that the black curve matches. Bottom: one dataset growing (the law
  of large numbers' picture), with a band of one SE either side of the truth that narrows as
  $1 slash sqrt(n)$.])

#project[
  *A simulation with known truth.* At each number of offers the spread of the pick rate over
  #n("toy.lln_clt.n_reruns") reruns, against @eq-se:

  #align(center, ftable(
    columns: (auto, auto, auto, auto, auto, auto),
    [*Offers* $n$], [#n("toy.lln_clt.n1.n")], [#n("toy.lln_clt.n2.n")], [#n("toy.lln_clt.n10.n")],
      [#n("toy.lln_clt.n100.n")], [#n("toy.lln_clt.n1600.n")],
    [*Spread over reruns*], [#n("toy.lln_clt.n1.sd_estimates")], [#n("toy.lln_clt.n2.sd_estimates")],
      [#n("toy.lln_clt.n10.sd_estimates")], [#n("toy.lln_clt.n100.sd_estimates")],
      [#n("toy.lln_clt.n1600.sd_estimates")],
    [*SE formula*], [#n("toy.lln_clt.n1.se")], [#n("toy.lln_clt.n2.se")], [#n("toy.lln_clt.n10.se")],
      [#n("toy.lln_clt.n100.se")], [#n("toy.lln_clt.n1600.se")],
  ))

  The width matches @eq-se at every $n$, even one: the formula for the width is exact. What
  takes many offers is the _shape_. At one or two offers the histogram is two or three bars, at
  ten it is a lopsided hump, and only by a hundred does it look like the bell of @eq-clt.
]

#incode("teaching_sims.lln_clt", [The two theorems' pictures, in a simulation.])[
  *What goes in:* a true pick rate, several numbers of offers, a number of reruns and the
  length of one long dataset. *What comes out:* the reruns' estimates at each $n$ and one
  running estimate. The lines that matter: `clt` draws `n_reruns` whole studies at each fixed
  `n` (the top row of the figure, @eq-clt); `running = np.cumsum(offers) / np.arange(...)` is
  the pick rate after each new offer of one long dataset (the bottom panel, @eq-lln). Change
  `n_reruns` and the histograms get smoother or more ragged, but their widths don't move.
]

#mixup[
  You might read the central limit theorem as "as the data grow, the estimate turns into a
  Gaussian", and blend it with "the estimate converges to the truth". They are different
  claims. Convergence (the law of large numbers) is about one dataset growing. The bell (the
  central limit theorem) is about many imagined datasets of a fixed size: it is the shape of
  the cloud of estimates you would get from reruns, and your real dataset is one draw from it.
]

#mixup[
  You might mix up the two numbers in a simulation like the one above: the offers per dataset
  ($n$) and the number of reruns. Only $n$ sets the bell's width. The number of reruns only sets
  how smoothly the histogram is filled in; more reruns make the simulation's own picture less
  ragged and change nothing else. In real life you have one rerun. And if you pooled all $R$
  reruns of $n$ offers into one big dataset, you wouldn't escape the picture: you would move to
  a new one at $R n$ offers, with a bell narrower by $sqrt(R)$.
]

#watch[
  The "more than two SEs from zero" rule below assumes the bell. For a rare card with few
  offers the cloud is lopsided, and two SEs is less trustworthy. A rough rule: expect at least
  about ten picks and ten skips before reading a pick rate's error bar as a bell.
]

#skill[
  *Knowing which approximation a method leans on.* Many standard error bars are the central
  limit theorem in disguise. Know when it is safe (many independent pieces, none dominant) and
  when it isn't (few offers, rare outcomes, strongly related observations).
]

#check(
  ([A study of #n("toy.lln_clt.n1600.n") offers at a pick rate of #n("toy.lln_clt.p") is rerun
    #n("toy.lln_clt.n_reruns") times. Describe the histogram of the estimates: shape, centre and
    width.],
   [Roughly a bell, centred on #n("toy.lln_clt.p"), with width (SD) about
    #n("toy.lln_clt.n1600.se"), from @eq-se. About two-thirds of the reruns land within one SE
    of the truth.]),
  ([What is the difference between "the estimate converges to the true pick rate" and "the
    estimate is Gaussian"? Which theorem is each?],
   [Converging is the law of large numbers: where the estimate goes as data grow. Gaussian is
    the central limit theorem: the shape and size of the scatter over reruns at a given
    size.]),
  ([A card has a quarter as many offers before a patch as after, with a similar pick rate.
    Which side's pick rate is less certain, and by what factor?],
   [The before side: a quarter of the offers means an SE twice as large, by the square-root
    rule.]),
  ([In the simulation, which setting would you change to make the histograms narrower: the
    number of offers or the number of reruns?],
   [The number of offers. The number of reruns only makes the histograms smoother.]),
)

== Confidence intervals and "clearly nonzero"

#words[
  - *95% confidence interval*: the estimate plus or minus about two SEs (a little under two,
    to be exact). If the whole study were repeated many times, intervals built this way would
    contain the true value about 95% of the time.
  - *z*: the estimate divided by its SE. It says how many SEs the estimate is from zero.
  - *Clearly nonzero*: the working rule |z| > 2, the same as "the 95% interval excludes
    zero". It is a label for reading many rows, not a verdict on any one card.
]

Because the estimate is close to a bell around the truth (@eq-clt), the chance that it lands
within $z^*$ standard errors of the truth is the area of the standard bell between $-z^*$ and
$z^*$. The 95% interval takes the $z^*$ that leaves two and a half percent in each tail, which
is 1.96:

$ hat(theta) plus.minus 1.96 dot "SE"(hat(theta)) $ <eq-ci>

In words: the interval runs from 1.96 standard errors below the estimate $hat(theta)$ to 1.96
above it, where $hat(theta)$ is any estimate whose error is close to a bell (a pick rate, an
effect $hat(beta)$). How far an estimate sits from zero, in its own SEs, is

$ z = hat(theta) / "SE"(hat(theta)) $ <eq-z>

In words: $z$ is the estimate divided by its standard error, its distance from zero in units
of its own wobble. If the true value is zero and the SE is honest, $z$ follows the standard
bell, so the share of estimates past two SEs by luck alone is

$ P(abs(Z) > 2) = 2 (1 - Phi(2)) = #n("const.honest.share_abs_z_gt2") $ <eq-false-share>

In words: with no real effect and honest error bars, the chance that an estimate lands more
than two SEs from zero is twice the area of the bell's tail beyond two, about one in twenty.
That is the false-alarm rate of the clearly-nonzero rule.

#project[
  *Your data.* Parry's effect, all after-weeks: #n("tweak.parry.v0_103_2.all.beta_pp_pm")
  points, interval #n("tweak.parry.v0_103_2.all.ci_lo_pp") to
  #n("tweak.parry.v0_103_2.all.ci_hi_pp"), z = #n("tweak.parry.v0_103_2.all.z"). Far from
  zero. Bulwark's second-patch nerf, over weeks 0–3, is
  #n("tweak.bulwark.v0_107_1.h3.beta_pp_pm") points, z = #n("tweak.bulwark.v0_107_1.h3.z"):
  just past the line, in the opposite direction to the change, and worth much less weight
  than Parry.
]

#plain[
  A 95% interval is *not* "a 95% chance the true value is in this interval" for one study,
  although people say that loosely. It is a property of the method: the method catches the
  truth 95% of the time over many repetitions, provided the SE is honest. @ch-placebo tests
  that proviso, and it fails.
]

#watch[
  An estimate just past two SEs and an estimate twenty SEs out are both "clearly nonzero", but
  they are not equally convincing. Report the estimate and its SE, not only the label.
]

#skill[
  *Reading an interval.* Translate "β ± SE" into "somewhere between these two values,
  probably", and check whether zero, or another interesting value, is inside.
]

#check(
  ([An estimate is four points with an SE of one point. Is it clearly nonzero? Give the
    approximate 95% interval.],
   [Yes: z is four. The interval is about two to six points.]),
  ([What is z, and what does |z| > 2 mean?],
   [The estimate divided by its SE. |z| > 2 means the estimate is more than two SEs from
    zero, so its 95% interval excludes zero.]),
  ([Explain to a friend what a 95% confidence interval promises, without saying "95% chance
    the true value is inside".],
   [If you ran the same study many times, building the interval the same way each time,
    about nineteen in every twenty intervals would contain the true value, as long as the error
    bars are honest.]),
  ([What would go wrong if the SEs were too small by a factor of four?],
   [The intervals would be four times too narrow, and many estimates would be called clearly
    nonzero when they are within what luck can produce.]),
  ([Where does the 1.96 in @eq-ci come from?],
   [It is the point of the standard bell curve that leaves two and a half percent in each
    tail, so that the middle holds 95%.]),
)

== The error of a difference

Every effect in this guide is a difference: after minus before, treated minus controls. Its
error bar comes from the errors of the pieces, by the same rule as @eq-var-sum.

#words[
  - *In quadrature*: combining errors by adding their squares and taking the root, as
    independent errors combine.
  - *Limiting side*: the piece of a difference with the larger SE, which sets a floor on the
    difference's SE.
]

For two independent estimates $hat(A)$ and $hat(B)$,

$ "SE"(hat(A) - hat(B)) = sqrt("SE"(hat(A))^2 + "SE"(hat(B))^2) $ <eq-se-diff>

In words: the SE of a difference is the square root of the sum of the two squared SEs. The
minus sign doesn't matter, because $"Var"(-hat(B)) = (-1)^2 "Var"(hat(B))$: subtracting a noisy
number adds its noise just as adding it would. A consequence: a difference can never be more
precise than its less precise side. If $hat(B)$ has many more offers than $hat(A)$, its SE
shrinks toward zero and the difference's SE shrinks only to $"SE"(hat(A))$.

#picture[
  Subtracting a background exposure from a science exposure in astronomy. A long science
  exposure can't rescue a short background: the noise of the short one sets the floor of the
  subtraction. Before-and-after differences work the same way.
]

#fig("fig_toy_se_difference", width: medium, [A worked example, not your data: the SE of an
  after-minus-before difference as the after block grows, with the before block fixed at
  #n("toy.se_difference.n_before") offers and a pick rate of #n("toy.se_difference.p"). The
  curve flattens onto the before block's SE alone.])

#project[
  *A worked example, not your data.* A card picked at #n("toy.se_difference.p") with
  #n("toy.se_difference.n_before") offers before the patch has a before-block SE of
  #n("toy.se_difference.se_before_pp") points. With the same number of offers after, the
  difference's SE is #n("toy.se_difference.se_diff_equal_pp") points; with ten times as many
  after, #n("toy.se_difference.se_diff_10x_pp")\; with a hundred times as many,
  #n("toy.se_difference.se_diff_100x_pp"). Past a few times the before block's size, extra
  after-block offers buy almost nothing.

  *Your data.* The second patch's after block, v0.107.1, holds #n("audit.offers_0_107_1")
  offers; its before block, v0.103.3, holds #n("audit.offers_0_103_3"). Every second-patch
  effect is a difference across those two blocks, so the smaller v0.103.3 side sets the floor
  of its error, and the large after block can't make up for it. What counts for a single card
  is that card's offers in each block, a small slice of these totals, and fewer still for rare
  cards.
]

#incode("teaching_sims.se_difference", [The SE of a difference with one side fixed.])[
  *What goes in:* a pick rate, the before block's offers and a range of after-block sizes.
  *What comes out:* the difference's SE along that range. The lines that matter: `se_b` and
  `se_a` are @eq-se for each block; `se_diff = np.sqrt(se_b**2 + se_a**2)` is @eq-se-diff. As
  `n_after` grows, `se_a` goes to zero and `se_diff` to `se_b`.
]

#mixup[
  You might gauge a before block's precision by the build's total: v0.103.3 has tens of
  thousands of runs, so how can it limit anything? The sample that counts is per card: that
  card's offers in each block, and a few million offers spread over five characters and
  hundreds of cards leaves a few thousand for a typical card and fewer for a rare one. Then
  @eq-se-diff makes the smaller block the floor. And offers aren't independent (offers in one
  run share a player and a deck), so the effective sample sits somewhere between the card's
  offers and its runs; @ch-regression makes that exact. The one-line version: _the card's
  offers in the smaller block, discounted for clustering_.
]

#watch[
  @eq-se-diff needs the two estimates to be independent. Before and after blocks are different
  runs, so that holds for them. Two estimates that share a block do not: the fake patch of
  @ch-explanations and the real second patch share v0.103.3, and their errors move together.
]

#skill[
  *Finding the limiting term.* When an uncertainty is built from several pieces, find the
  largest one first. Improving any other piece buys little.
]

#check(
  ([To know how precise one card's estimate is, do you look up the build's runs or the card's
    offers?],
   [The card's offers, in the smaller of the two blocks, discounted for clustering (offers in
    one run are related).]),
  ([Why does subtracting one estimate from another add to the error rather than cancel it?],
   [Variances add for independent pieces, whatever the sign: $"Var"(-hat(B)) = "Var"(hat(B))$.]),
  ([Two blocks have SEs of three points and four points for a card. What is the SE of their
    difference?],
   [Five points: the square root of nine plus sixteen.]),
  ([Doubling the after block's size barely changed a tweak's SE. Why?],
   [The before block was the limiting side; its SE sets the floor of @eq-se-diff, and the
    after block's SE was already small next to it.]),
)

== Very small samples: when the plug-in formula breaks

The plug-in SE, $sqrt(hat(p)(1 - hat(p)) slash n)$, puts the estimate where the truth should
be. With thousands of offers that is harmless. With a handful it fails exactly where an honest
error bar matters most.

#words[
  - *Wilson interval*: an interval for a rate that stays sensible at small counts; the usual
    recommendation for a few offers.
  - *Prior and posterior*: in Bayesian updating, what you believe about $p$ before the data,
    and after.
  - *Beta distribution*, $"Beta"(a, b)$: a family of curves on zero to one, the natural shape
    for beliefs about a rate. $"Beta"(1, 1)$ is flat.
  - *Partial pooling*: letting each card's estimate borrow strength from the other cards, so
    thin cards are pulled toward the group.
]

Offer a card once and see a skip. Then $hat(p) = 0$, the plug-in spread is $sqrt(0 dot 1) =
0$, and the SE is zero: the method claims certainty from one offer. The same happens to a rare
card never picked in fifty offers. Two fixes keep the estimate off the walls. The first adds
pretend data. The *Wilson* interval, with $z = 1.96$, has centre and half-width

$ tilde(p) = (hat(p) + z^2 slash (2 n)) / (1 + z^2 slash n), quad
  "hw" = z / (1 + z^2 slash n) sqrt((hat(p) (1 - hat(p))) / n + z^2 / (4 n^2)) $ <eq-wilson>

In words: the Wilson centre $tilde(p)$ is the pick rate pulled toward a half by an amount that
fades as offers grow, and its half-width $"hw"$ has an extra term that keeps it above zero even
when $hat(p)$ is zero or one. A simpler cousin (Agresti–Coull) just adds two pretend picks and
two pretend skips, $(k + 2) slash (n + 4)$.

The second fix is Bayesian updating, the formal version of "update as the data come in". Start
from a flat prior, every $p$ equally plausible, $"Beta"(1, 1)$, which acts like one pretend
pick and one pretend skip. After $k$ picks in $n$ offers the belief about $p$ is

$ p | k, n quad tilde.op quad "Beta"(1 + k, 1 + n - k), quad "E"[p | k, n] = (k + 1) / (n + 2) $ <eq-posterior>

In words: the posterior belief about the pick rate is a Beta curve with the picks added to the
first number and the skips to the second, and its mean is the picks plus one over the offers
plus two. It is never a spike after one offer. Updating one offer at a time or all at once, in
any order, gives the same curve.

#mathfull[
  Bayes' rule: posterior is proportional to likelihood times prior. The likelihood of $k$
  picks in $n$ independent offers is proportional to $p^k (1 - p)^(n - k)$; the flat prior is
  a constant. So the posterior is proportional to $p^k (1 - p)^(n - k)$, which is the shape of
  a $"Beta"(1 + k, 1 + n - k)$ curve, whose density is proportional to $p^(a - 1)(1 - p)^(b -
  1)$ with $a = 1 + k$ and $b = 1 + n - k$. A Beta's mean is $a slash (a + b)$, which gives
  $(k + 1) slash (n + 2)$.

  Updating one offer at a time multiplies in one factor of $p$ or $(1 - p)$ at each step;
  multiplication doesn't care about order, so the end result is the same. To predict the next
  offer, average the chance of a pick over every plausible $p$, weighted by the posterior: that
  is "marginalizing", and for the flat prior it gives $(k + 1) slash (n + 2)$ again, Laplace's
  rule of succession. With lots of data the pretend pick and skip are swamped and all three
  methods agree.
]

#fig("fig_toy_posterior", width: medium, [A simulation with known truth: a flat prior
  updated offer by offer for a card with a true pick rate of #n("toy.small_samples.p_true").
  Flat at no offers, a ramp after one, a lopsided hump by five to twenty, and a narrow peak by
  the last checkpoint (cut off at the top).])

#project[
  *A worked example, not your data.* Three 95% intervals for a pick rate, each given as
  centre, then lower to upper end:

  #align(center, small-table(
    columns: (auto, auto, auto, auto),
    [*Picks / offers*], [*Plug-in*], [*Wilson*], [*Bayes (flat prior)*],
    [#n("toy.small_samples.k0_n1.k") / #n("toy.small_samples.k0_n1.n")],
      [#n("toy.small_samples.k0_n1.plugin.centre"), #n("toy.small_samples.k0_n1.plugin.lo") to #n("toy.small_samples.k0_n1.plugin.hi")],
      [#n("toy.small_samples.k0_n1.wilson.centre"), #n("toy.small_samples.k0_n1.wilson.lo") to #n("toy.small_samples.k0_n1.wilson.hi")],
      [#n("toy.small_samples.k0_n1.bayes.centre"), #n("toy.small_samples.k0_n1.bayes.lo") to #n("toy.small_samples.k0_n1.bayes.hi")],
    [#n("toy.small_samples.k1_n1.k") / #n("toy.small_samples.k1_n1.n")],
      [#n("toy.small_samples.k1_n1.plugin.centre"), #n("toy.small_samples.k1_n1.plugin.lo") to #n("toy.small_samples.k1_n1.plugin.hi")],
      [#n("toy.small_samples.k1_n1.wilson.centre"), #n("toy.small_samples.k1_n1.wilson.lo") to #n("toy.small_samples.k1_n1.wilson.hi")],
      [#n("toy.small_samples.k1_n1.bayes.centre"), #n("toy.small_samples.k1_n1.bayes.lo") to #n("toy.small_samples.k1_n1.bayes.hi")],
    [#n("toy.small_samples.k0_n3.k") / #n("toy.small_samples.k0_n3.n")],
      [#n("toy.small_samples.k0_n3.plugin.centre"), #n("toy.small_samples.k0_n3.plugin.lo") to #n("toy.small_samples.k0_n3.plugin.hi")],
      [#n("toy.small_samples.k0_n3.wilson.centre"), #n("toy.small_samples.k0_n3.wilson.lo") to #n("toy.small_samples.k0_n3.wilson.hi")],
      [#n("toy.small_samples.k0_n3.bayes.centre"), #n("toy.small_samples.k0_n3.bayes.lo") to #n("toy.small_samples.k0_n3.bayes.hi")],
    [#n("toy.small_samples.k1_n5.k") / #n("toy.small_samples.k1_n5.n")],
      [#n("toy.small_samples.k1_n5.plugin.centre"), #n("toy.small_samples.k1_n5.plugin.lo") to #n("toy.small_samples.k1_n5.plugin.hi")],
      [#n("toy.small_samples.k1_n5.wilson.centre"), #n("toy.small_samples.k1_n5.wilson.lo") to #n("toy.small_samples.k1_n5.wilson.hi")],
      [#n("toy.small_samples.k1_n5.bayes.centre"), #n("toy.small_samples.k1_n5.bayes.lo") to #n("toy.small_samples.k1_n5.bayes.hi")],
    [#n("toy.small_samples.k30_n600.k") / #n("toy.small_samples.k30_n600.n")],
      [#n("toy.small_samples.k30_n600.plugin.centre"), #n("toy.small_samples.k30_n600.plugin.lo") to #n("toy.small_samples.k30_n600.plugin.hi")],
      [#n("toy.small_samples.k30_n600.wilson.centre"), #n("toy.small_samples.k30_n600.wilson.lo") to #n("toy.small_samples.k30_n600.wilson.hi")],
      [#n("toy.small_samples.k30_n600.bayes.centre"), #n("toy.small_samples.k30_n600.bayes.lo") to #n("toy.small_samples.k30_n600.bayes.hi")],
    [#n("toy.small_samples.k320_n1600.k") / #n("toy.small_samples.k320_n1600.n")],
      [#n("toy.small_samples.k320_n1600.plugin.centre"), #n("toy.small_samples.k320_n1600.plugin.lo") to #n("toy.small_samples.k320_n1600.plugin.hi")],
      [#n("toy.small_samples.k320_n1600.wilson.centre"), #n("toy.small_samples.k320_n1600.wilson.lo") to #n("toy.small_samples.k320_n1600.wilson.hi")],
      [#n("toy.small_samples.k320_n1600.bayes.centre"), #n("toy.small_samples.k320_n1600.bayes.lo") to #n("toy.small_samples.k320_n1600.bayes.hi")],
  ))

  At one offer the plug-in interval has no width at all; Wilson and Bayes stay wide, as one
  offer deserves. By the last two rows the three methods agree: the differences live in the
  small-sample corner.

  *Your data.* No pick rate in the main analysis is estimated from a handful of offers: the
  smallest treated count is Royalties' #n("tweak.royalties.v0_107_1.n_treated_offers")
  upgraded offers. Where the guide's plan reaches for small-sample help, it is partial pooling
  across cards (@ch-open), the grown-up version of the prior here, and that is future work.
]

#incode("teaching_sims.intervals", [Three ways to put a 95% interval on a pick rate.])[
  *What goes in:* picks $k$ and offers $n$. *What comes out:* centre, lower and upper end.
  The lines that matter: `plugin` is @eq-se around $hat(p)$, with 1.96 from @eq-ci; when
  `ph` is zero or one, `se` is zero. `wilson` is @eq-wilson line by line (`centre` and `half`).
  `bayes` builds the posterior of @eq-posterior with `beta(1 + k, 1 + n - k)` and reads its
  mean and the points that leave two and a half percent in each tail.
]

#mixup[
  You might ask, after one offer that was skipped, whether to plug in zero or one, and want to
  "marginalize" over both possibilities. That instinct is the Bayesian answer, formalized:
  hold a belief over every plausible $p$ (the prior), update it with each offer (the
  posterior, @eq-posterior), and average over it when you need a prediction. The flat prior
  after one skip gives a mean of a third, not zero, and a wide curve that admits it doesn't know
  much yet.
]

#watch[
  An interval of zero width is a symptom, not a result. Whenever a rate is zero or one, or
  rests on a few offers, use an interval built for small counts.
]

#skill[
  *Checking a formula at the edges.* Try a method on the smallest and most extreme cases (one
  observation, all zeros) before trusting it. Formulas that work in the middle often fail at
  the walls.
]

#check(
  ([A card is offered three times and never picked. What are the plug-in estimate and SE, and
    the flat-prior posterior mean? Which do you trust?],
   [Plug-in: zero, with an SE of zero, which claims certainty. The posterior is
    $"Beta"(1, 4)$, with mean one fifth, and wide. Trust the posterior: three offers can't
    rule out a moderate pick rate.]),
  ([A card is picked #n("toy.small_samples.k30_n600.k") times in
    #n("toy.small_samples.k30_n600.n") offers. Roughly what are $hat(p)$ and its SE, and is the
    bell reading reasonable?],
   [$hat(p)$ is #n("toy.small_samples.k30_n600.plugin.centre"), and the SE is about a
    hundredth: the square root of $hat(p)(1 - hat(p))$ divided by the square root of the
    offers. With well over ten picks and ten skips, the bell reading is reasonable.]),
  ([Why do the three methods disagree at one offer and agree at a few hundred?],
   [The pretend data (Wilson's pull toward a half, the prior's pick and skip) matter only when
    there is little real data; they are swamped as offers grow.]),
)

== Precision, accuracy, and what a standard error does not cover

An SE answers one question: how far would this estimate move on a fresh sample? Two common
problems are outside that question.

#words[
  - *Precision*: how little the estimate would wobble over reruns. Measured by the variance,
    reported as the SE. Shrinks with more data.
  - *Accuracy*: how close the estimate's centre is to the truth. Its failure is *bias*, a
    systematic error, set by the design; more data doesn't touch it. A bathroom scale that
    always reads two kilos heavy is precise and inaccurate.
  - *Mean squared error (MSE)*: the average squared distance between the estimate and the
    truth; it counts both failures.
  - *Multiple comparisons*: test enough things and some pass by luck. With honest errors,
    about one estimate in twenty lands beyond two SEs when nothing is going on.
]

#picture[
  A bathroom scale reads five pounds heavy. Weigh yourself a hundred times and the readings
  agree to a tenth of a pound; every one of them is wrong by five. Averaging more readings
  makes the wrong answer look more certain. Physicists say statistical error and systematic
  error; statisticians say variance and bias.
]

For an estimator $hat(theta)$ of a true value $theta$, the bias is
$"bias"(hat(theta)) = "E"[hat(theta)] - theta$, and

$ "MSE"(hat(theta)) = "E"[(hat(theta) - theta)^2] = "bias"(hat(theta))^2 + "Var"(hat(theta)) $ <eq-mse>

In words: the typical squared error of an estimate is its bias squared plus its variance. More
data shrinks the variance term; only a better design shrinks the bias term. This is the source
of the phrase "bias–variance tradeoff": a choice that buys precision (more data, a wider
window, pooling blocks) can cost accuracy, and the reverse.

#mathfull[
  Add and subtract the estimator's own centre:
  $hat(theta) - theta = (hat(theta) - "E"[hat(theta)]) + "bias"$. Square and average:
  $"E"[(hat(theta) - theta)^2] = "E"[(hat(theta) - "E"[hat(theta)])^2] + 2 dot "bias" dot
  "E"[hat(theta) - "E"[hat(theta)]] + "bias"^2$. The middle term is zero, because an estimate's average distance from
  its own centre is zero (the same cancellation as @eq-signed). What is left is
  $"Var"(hat(theta)) + "bias"^2$.
]

A fixed bias does worse than stay put as data grow: it becomes _significant_. If an estimate is
off by a fixed bias and its SE is $sigma slash sqrt(n)$, with $sigma$ the SD of one
observation, its distance from the truth in SEs is

$ "bias" / "SE" = ("bias" dot sqrt(n)) / sigma $ <eq-bias-z>

In words: the bias measured in standard errors grows with the square root of the sample size.
With a small sample a bias hides in the noise; with a huge one, even a tiny bias is many SEs
from the truth, and every interval misses it.

#fig("fig_toy_fixed_bias", [A simulation with known truth: a pick-rate estimate that reads
  #n("toy.fixed_bias.bias_pp") point too high (true rate #n("toy.fixed_bias.p_true")), rerun many
  times at four sample sizes. The histogram narrows around the wrong centre until it excludes
  the truth entirely.])

#project[
  *A simulation with known truth.* The share of 95% intervals that contain the truth, for an
  estimate #n("toy.fixed_bias.bias_pp") point too high:

  #align(center, ftable(
    columns: (auto, auto, auto, auto),
    [*Offers*], [*SE (points)*], [*Bias in SEs*], [*Intervals covering the truth*],
    [#n("toy.fixed_bias.n1000.n")], [#n("toy.fixed_bias.n1000.se_pp")],
      [#n("toy.fixed_bias.n1000.bias_over_se")], [#n("toy.fixed_bias.n1000.share_covers")],
    [#n("toy.fixed_bias.n10000.n")], [#n("toy.fixed_bias.n10000.se_pp")],
      [#n("toy.fixed_bias.n10000.bias_over_se")], [#n("toy.fixed_bias.n10000.share_covers")],
    [#n("toy.fixed_bias.n100000.n")], [#n("toy.fixed_bias.n100000.se_pp")],
      [#n("toy.fixed_bias.n100000.bias_over_se")], [#n("toy.fixed_bias.n100000.share_covers")],
    [#n("toy.fixed_bias.n1000000.n")], [#n("toy.fixed_bias.n1000000.se_pp")],
      [#n("toy.fixed_bias.n1000000.bias_over_se")], [#n("toy.fixed_bias.n1000000.share_covers")],
  ))

  More data made it worse, not better: precise and wrong. That is roughly what the placebo
  calibration of @ch-placebo caught in your data, for a different reason (error bars too
  small rather than a bias), and why the choice not to pool v0.103.2 into the second patch's
  before block (@ch-checks) traded precision for accuracy.
]

#incode("teaching_sims.fixed_bias", [A fixed bias at growing sample size.])[
  *What goes in:* the true rate, a bias and a few sample sizes. *What comes out:* each size's
  SE, the bias in SEs, and the share of intervals that cover the truth. The lines that matter:
  `rng.binomial(n, p_true + bias, ...)` draws estimates centred on the wrong value;
  `bias / se` is @eq-bias-z; `covers` checks @eq-ci's interval against `p_true`.
]

The second problem is many looks. Test $N$ estimates whose true values are all zero, with
honest SEs, and the expected number past two SEs is

$ "E"["false alarms"] = N dot P(abs(Z) > 2) $ <eq-expected-false>

In words: the expected count of clearly-nonzero results from luck alone is the number of
estimates times the false-alarm share of @eq-false-share.

#project[
  *Your data.* With honest errors, the share of estimates beyond two SEs when nothing is
  going on is #n("const.honest.share_abs_z_gt2"). Over #n("tweaks.solo_estimable") tweaks
  that is about #n("did.expected_false_alarms.all") false alarms
  (#n("did.expected_false_alarms.first") in the first patch,
  #n("did.expected_false_alarms.second") in the second). Using the error bars the model
  reports (*uncalibrated*: @ch-placebo explains why that word is needed), weeks 0–3, the first
  patch has #n("did.h3.first.uncalibrated.clearly_nonzero") of #n("tweaks.first") tweaks
  clearly nonzero and the second #n("did.h3.second.uncalibrated.clearly_nonzero") of
  #n("tweaks.second"). The second count is the one to read with more care.
]

#picture[
  Buy one lottery ticket and winning is a surprise. Buy a hundred and one small win is
  expected. Testing many cards is buying many tickets: a few "clearly nonzero" results are
  expected even if no card changed at all.
]

The plan's answer to multiple comparisons on a card-by-card scale is partial pooling
(@ch-open), which pulls noisy estimates toward the group. It is future work. In this guide
the main defence is to read counts against what chance alone would give, and to put more
weight on the patterns across many cards (@ch-dose) than on any single card.

#watch[
  A narrow interval says the estimate would barely move on a fresh sample. It says nothing
  about whether the comparison was fair. Fairness is what the design (@ch-did to @ch-checks)
  is for, and honesty of the error bars is what @ch-placebo checks.
]

#skill[
  *Separating random error from systematic error.* An SE measures random scatter under
  assumptions. Bias and many looks are the two classic ways a small SE misleads; name both
  when you present a result.
]

#check(
  ([With honest errors and no real effects, how many of the tweaks would you expect to be
    clearly nonzero?],
   [About one in twenty: around two of them (@eq-expected-false).]),
  ([Someone says "the interval is very narrow, so the answer must be right". What is wrong
    with that?],
   [The interval covers random scatter only. A biased comparison can have a narrow interval
    around the wrong number, and if the SEs are not honest the interval is not even right
    about the scatter.]),
  ([A boss change in the same patch confounds one card's estimate. Is that a statistical or a
    systematic error? What happens to it if you double the runs?],
   [Systematic. Doubling the runs leaves it unchanged and makes it look more significant
    (@eq-bias-z).]),
  ([Card A: three points, SE a third of a point, with a known confounder in its window. Card
    B: three points, SE one and a half points, with none. Which do you trust more?],
   [Usually B: its error bar is honest about what it doesn't know. A's tight bar says nothing
    about the confounder.]),
  ([Write the MSE as two terms. Which one does more data shrink?],
   [Bias squared plus variance (@eq-mse). More data shrinks the variance; the bias stays.]),
  ([Why is the second patch's count of clearly nonzero tweaks read with more care than the
    first patch's?],
   [It is closer to what chance alone would give, so a larger share of it could be false
    alarms.]),
)
