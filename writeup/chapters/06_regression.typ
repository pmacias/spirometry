#import "../style.typ": *

= Regression: comparing like with like <ch-regression>

#lead[What the model in notebook 02 adds to the hand calculation, and how its error bars are
  built.]

The 2×2 table of @ch-did gives the right idea and nearly the right number. Your notebook, notebook 02, fits a
regression instead. It gives the same kind of answer, but it compares like with like (same
uploader group, same act, same ascension) and it comes with error bars that match how the
data were collected. This chapter explains what the model line means and why there are
several kinds of standard error.

== A line through points, or a difference of averages

#picture[
  Plot height against age for children and draw the best straight line through the points.
  The line's slope says how much taller a child is, on average, for each extra year. If the
  "age" axis has only two values, say before and after a birthday, the best line simply joins
  the two averages. A regression with yes-or-no inputs is a machine for computing
  differences of averages, adjusted for whatever else you put in.
]

#words[
  - *Regression*: a fitted relation between an outcome and one or more inputs.
  - *Coefficient (β)*: the fitted effect of one input on the outcome, holding the other
    inputs fixed.
  - *Linear probability model*: a regression whose outcome is zero or one (here, picked).
    Its coefficients are in pick-rate units: a coefficient of five hundredths means five
    more picks per hundred offers.
]

#project[
  *Your data.* In notebook 02 the outcome is "picked" for each offer of the treated card and
  its controls, and the input of interest is "this is the treated card, in the after block".
  Its coefficient is the DiD. For Parry the model gives #n("tweak.parry.v0_103_2.all.beta_pp_pm")
  points, the hand calculation #n("tweak.parry.v0_103_2.did_raw_pp").
]

#watch[
  A coefficient "holding the others fixed" is only as good as the list of others. A
  regression adjusts for what you put in, never for what you left out.
]

#skill[
  *Seeing a regression as a comparison.* Before reading coefficients, ask which two groups of
  observations the key coefficient compares, and what is held equal between them.
]

#check(
  ([In a regression with one yes-or-no input, what does the best-fitting line do?],
   [It joins the two group averages, so the slope is the difference between them.]),
  ([What does β mean in a linear probability model?],
   [The change in the probability of the outcome (here, the pick rate) associated with the
    input, holding the other inputs fixed.]),
  ([Why do the hand calculation and the model for Parry differ slightly?],
   [The model compares offers within the same uploader group, act and ascension and weights
    them by how much data each comparison has; the hand calculation pools everything.]),
)

== Reading the model line

#words[
  - *Fixed effects*: a separate baseline for each group, so comparisons happen within the
    group. A fixed effect for each card means each card has its own usual pick rate.
  - *Singleton*: a fixed-effect group with a single observation. It can't be compared with
    anything, so it is dropped.
]

#picture[
  Grading students within their own class: a teacher who marks hard and a teacher who marks
  easy both produce fair rankings within their class. Fixed effects do the same: each card
  (and each uploader group, block, act and ascension level) gets its own baseline, and the
  effect is read from the differences within those baselines.
]

The model in words. Whether an offer was picked depends on:
- which card it is, with upgraded and un-upgraded versions as separate cards, and a separate
  baseline in each uploader group;
- the block (before or after) in each uploader group, which captures everything that moved
  all of the character's cards between builds;
- the act of the run in which the card was offered;
- the ascension level, one baseline per level;
- and the treated card in the after block. This term's coefficient is the effect.

#project[
  *Your data.* The block term is where the controls do their work: they pin down how much every
  card moved between the blocks, and the treated card's coefficient is what is left. Dropping
  the uploader-group terms moves the estimates by a median
  #n("robustness.h3_pooled_groups.median_shift_se") SEs, so they changed little; they stay in
  because the groups differ (@ch-confounding). Singletons: #n("did.singletons_dropped.total")
  offers dropped across #n("did.singletons_dropped.n_tweaks") tweaks, at most
  #n("did.singletons_dropped.max") in any one. Offers with no recorded ascension are dropped.
  Whether each ascension level should be its own baseline or levels should be grouped in bands
  is #unverified[an open choice] (PLAN item 14).
]

#watch[
  A fixed effect for ascension is not a study of ascension. It removes differences between
  ascension levels from the comparison and nothing more; its own coefficients are not
  results.
]

#skill[
  *Reading a model specification.* Turn each term of a formula into a sentence about what
  is held fixed. If you can't say what a term absorbs, you can't say what the coefficient
  means.
]

#check(
  ([What does a fixed effect for each card do?],
   [It gives each card its own baseline pick rate, so the model compares a card's offers
    with that card's usual rate rather than with other cards' rates.]),
  ([Which term in the model absorbs "everything that moved all of the character's cards
    between builds"?],
   [The block term (before or after, in each uploader group), estimated mostly from the
    control cards.]),
  ([Why is a singleton dropped?],
   [It is the only observation in its group, so its group's baseline fits it exactly and it
    carries no information about the effect.]),
)

== Why several kinds of standard error

#words[
  - *iid SE*: assumes every offer is independent and equally noisy.
  - *Robust (heteroskedasticity-robust) SE*: allows offers to be unequally noisy (a card
    picked half the time is noisier per offer than one picked rarely, @ch-counting). Your
    notebooks use the most common small-sample version of it.
  - *Clustered SE*: also allows offers in the same run to be related. The main errors in
    this guide are clustered by run.
]

#picture[
  Ask ten strangers whether they like a film and you have ten opinions. Ask ten members of
  one family and you have something closer to one opinion said ten times: they watched it
  together and talked about it. Clustering admits that offers from one run are a family: the
  same player, the same deck, the same run going well or badly.
]

#project[
  *Your data.* Clustered SEs are larger than robust ones by a median factor of
  #n("se.clustered_over_robust.median") over the #n("tweaks.solo_estimable") tweaks (range
  #n("se.clustered_over_robust.min") to #n("se.clustered_over_robust.max")); Parry's is
  #n("tweak.parry.v0_103_2.se_over_robust"). The largest factors belong to common cards offered
  many times per run (Crescent Spear #n("tweak.crescent_spear.v0_107_1.se_over_robust")).
  Against iid SEs the ratio ranges from #n("se.clustered_over_iid.min") to
  #n("se.clustered_over_iid.max"), median #n("se.clustered_over_iid.median"), but that ratio
  mostly measures unequal noise between cards, which is why clustering is judged against the
  robust SE, not the iid one.
]

#fig("fig_se_ratio", [Clustered SE divided by robust SE for each tweak, against the treated
  card's number of offers.])

#watch[
  Clustering by run handles offers within a run. It does not handle other ways offers could
  be related, such as one player's many runs, or a card being valued differently by
  different groups week after week. @ch-placebo finds that something like that is going on,
  and that the clustered errors are much too small.
]

#skill[
  *Matching the error bars to the data's structure.* Ask what makes observations related
  (people, sessions, places, time) and cluster at that level. Then check, as @ch-placebo
  does, whether that was enough.
]

#check(
  ([Explain to a friend why offers from one run shouldn't count as independent.],
   [They come from the same player, deck and run: if the run is going badly, or the player
    has a style, several offers are affected together, like a family answering a survey.]),
  ([Why is clustering judged against robust SEs and not iid ones?],
   [The iid ratio mixes two things: unequal noise between cards and relatedness within runs.
    The robust SE already allows unequal noise, so the clustered-to-robust ratio isolates the
    effect of relatedness.]),
  ([Clustering widened the error bars by only a few percent. Does that prove the errors are
    honest?],
   [No. It shows that relatedness within a run matters little. Other sources of relatedness
    could make the errors too small, and the placebo test in @ch-placebo shows that they do.]),
)

== Log-odds, briefly

#words[
  - *Odds*: picks divided by passes. A pick rate of one in four is odds of one to three.
  - *Log-odds*: the natural logarithm of the odds. It stretches the scale near zero and one.
  - *Delta method*: a standard way to convert an estimate and its SE from one scale to
    another, using the slope of the conversion at the starting point.
]

#picture[
  Betting odds. Moving a long shot from a hundred to one to fifty to one is a big change in
  how good the horse is thought to be, even though its chance of winning moved by only half a
  point. Log-odds measure changes the way a bookmaker would: a few points matter more for a
  card nobody picks than for a card everyone picks.
]

Effects in this guide are reported in percentage points, which are easy to say. The
dose-response chapter (@ch-dose) converts each effect to log-odds first, so that cards with
very different starting pick rates are on a common scale. The conversion uses the treated
card's pick rate before the patch and the delta method.

#project[
  *Your data.* Parry's weeks 0–3 effect is #n("tweak.parry.v0_103_2.h3.beta_pp_pm") points, or
  #n("tweak.parry.v0_103_2.h3.beta_lo_pm") in log-odds, starting from a pick rate of
  #n("tweak.parry.v0_103_2.treated_rate_before").
]

#watch[
  A log-odds effect can't be read as points without knowing the starting rate. Always say
  which scale an effect is on.
]

#skill[
  *Choosing a scale.* Use the scale on which effects are comparable for the question (log-odds
  across cards with different baselines) and report on the scale people understand (points).
]

#check(
  ([A card is picked one time in four. What are its odds?],
   [One pick for every three passes: odds of one to three.]),
  ([Why convert effects to log-odds before comparing cards with very different pick rates?],
   [A few points is a big change for a rarely picked card and a small one for a popular card.
    Log-odds put the changes on a common scale.]),
  ([What does the delta method do?],
   [It converts an estimate and its SE from one scale to another (here points to log-odds)
    using the slope of the conversion at the starting value.]),
)
