#import "../style.typ": *

= Noise: standard errors, intervals, and "clearly nonzero" <ch-noise>

#lead[How much a number could move by luck alone, and when an estimate is clearly different
  from zero.]

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
  - *Square-root rule*: the SE shrinks with the square root of the number of observations n.
    Four times the data halves the SE.
  - For a rate p measured on n offers, SE = √(p(1 − p) / n): the spread of one offer
    (@ch-counting) divided by the square root of the number of offers.
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
  tiny SE even though each offer is a coin-like zero or one.
]

#skill[
  *Quantifying uncertainty.* Every estimate you report should come with a statement of how
  much it could move by chance, and you should be able to say roughly how that shrinks with
  more data.
]

#check(
  ([You double the number of offers. By what factor does the SE of a pick rate shrink?],
   [By the square root of two: it becomes about seven tenths of what it was.]),
  ([Why is Royalties' SE so much larger than Parry's?],
   [Royalties' change was to the upgraded card only, so it is measured on upgraded offers,
    of which there were only a few hundred; Parry had many thousands of offers.]),
  ([In the soup picture, what plays the role of "a well-stirred pot"?],
   [Offers that are like a random draw from the population, so that each spoonful (sample)
    represents the whole.]),
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
)

== Two things a standard error does not cover

#words[
  - *Bias*: a systematic error that more data doesn't fix (@ch-confounding). A bathroom scale
    that always reads two kilos heavy.
  - *Multiple comparisons*: test enough things and some pass by luck. With honest errors,
    about one estimate in twenty lands beyond two SEs when nothing is going on.
]

#picture[
  Buy one lottery ticket and winning is a surprise. Buy a hundred and one small win is
  expected. Testing many cards is buying many tickets: a few "clearly nonzero" results are
  expected even if no card changed at all.
]

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
  *Separating luck from systematic error.* An SE measures luck under assumptions. Bias and
  many looks are the two classic ways a small SE misleads; name both when you present a
  result.
]

#check(
  ([With honest errors and no real effects, how many of the tweaks would you expect to be
    clearly nonzero?],
   [About one in twenty: around two of them.]),
  ([Someone says "the interval is very narrow, so the answer must be right". What is wrong
    with that?],
   [The interval covers luck only. A biased comparison can have a narrow interval around the
    wrong number, and if the SEs are not honest the interval is not even right about luck.]),
  ([Why is the second patch's count of clearly nonzero tweaks read with more care than the
    first patch's?],
   [It is closer to what chance alone would give, so a larger share of it could be false
    alarms.]),
)
