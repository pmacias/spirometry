#import "../style.typ": *

= Why "just compare" doesn't work <ch-confounding>

#lead[Confounding: when the group that got the treatment was different to start with.]

The obvious way to ask whether a card is good is to compare runs that took it with runs that
didn't. This chapter explains why that comparison measures the wrong thing, writes the problem
down exactly (the notation the rest of the guide uses for causal effects), shows the same
problem in your uploader groups, and explains why more data does not fix it.

== Vitamins and card picks

#picture[
  People who take vitamins are healthier than people who don't. Do vitamins make you
  healthy? Maybe a little. But people who already look after themselves are the ones who
  buy vitamins. Their health and their vitamin habit share a cause: how much they care about
  their health. Comparing vitamin takers with non-takers mixes the vitamins' effect with the
  effect of being the kind of person who takes them.
]

Your game has the same shape. Players who take a strong-looking card are, on average,
better players, and better players win more anyway. So "runs that took card X win more
often" partly measures skill, not the card.

#fig("fig_confounding_dag", [Skill pushes both arrows: good players pick the card more and
  win more anyway. The arrow from picking to winning is the effect you want, hidden behind
  the other two.])

#project[
  *Simulation.* The IV primer builds a made-up game where the truth is known: taking the
  card raises the chance of winning by #n("iv.single.truth"). In that game, runs that took
  the card won #n("iv.single.win_pickers") of the time against #n("iv.single.win_non_pickers")
  for runs that didn't. The naive comparison (took against didn't take) gives
  #n("iv.single.naive_pm"), well above the truth, because skill raises both picking and
  winning. @ch-wins shows how the game's random offers recover the truth.
]

#skill[
  *Asking "compared with what?"* Every effect is a comparison. Before trusting one, name the
  two groups being compared and ask how they differed before the treatment.
]

#check(
  ([In your own words, why is "win rate of runs that took card X minus win rate of runs that
    didn't" not the effect of card X?],
   [Players who take card X differ from those who don't, especially in skill, and skill also
    raises the chance of winning. The difference mixes the card's effect with the effect of
    being the kind of player who takes it.]),
  ([In the simulated game, the naive estimate is larger than the truth. Which way would it be
    off if weak players were the ones who took the card?],
   [Below the truth: the takers would win less for reasons unrelated to the card, which pulls
    the comparison down.]),
  ([What does the arrow from skill to "picks the card" represent?],
   [That a player's skill changes how likely they are to take the card, which is the
    selection that lets skill into the comparison.]),
)

== The words, and the notation

#words[
  - *Outcome*: the thing you measure. Here, whether a card was picked (@ch-did) or whether
    the run was won (@ch-wins).
  - *Treatment*: the thing whose effect you want. Here, the patch (the card's new version
    being live), or taking a card. It doesn't have to be medical.
  - *Confounder*: something that affects both who gets the treatment and the outcome. Skill
    is the big one.
  - *Selection*: the treated and untreated groups differ because of who chose, or was
    chosen, to be treated. Selection is how confounders get in.
  - *Causal effect*: what would change for the same run if you flipped the treatment and
    nothing else.
  - *Counterfactual*: the world where the treatment was flipped: the same run, with the card
    not taken; the same weeks, without the patch.
  - *Potential outcomes*: the two outcomes a unit would have, one with the treatment and one
    without. Only one of them is ever seen.
]

#picture[
  The counterfactual is the road not taken. You took the motorway and arrived in an hour;
  would the back road have been faster? You can never drive both roads with the same
  traffic on the same day. Every method in this guide is a way of estimating the road not
  taken from roads other people drove.
]

The words have an exact version, and the rest of the guide uses it. Take a unit $i$ (a run, or
a card in a window) and a treatment indicator $D_i$, one if the unit is treated and zero if
not. Give the unit two *potential outcomes*: $Y_i (1)$, what its outcome would be with the
treatment, and $Y_i (0)$, what it would be without. What you observe is whichever one the
treatment switched on:

$ Y_i = D_i Y_i (1) + (1 - D_i) Y_i (0) $ <eq-po-observed>

In words: the observed outcome is the treated potential outcome if the unit was treated, and
the untreated one if it wasn't. The other one, the counterfactual, is never recorded. The
causal effect for one unit is the difference between its two potential outcomes:

$ tau_i = Y_i (1) - Y_i (0) $ <eq-tau-unit>

In words: the effect of the treatment on unit $i$ is what its outcome would be with the
treatment minus what it would be without. @eq-po-observed says exactly one of the two terms is
ever seen, so $tau_i$ can never be computed for any single unit. This is sometimes called the
fundamental problem of causal inference. What can be estimated are averages over many units.
Write $"E"[dot]$ for an average over the units (an expectation) and $"E"[dot | D = 1]$ for an
average over the treated units only. Two averages matter:

$ tau_"ATE" = "E"[Y(1) - Y(0)], quad tau_"ATT" = "E"[Y(1) - Y(0) | D = 1] $ <eq-ate-att>

In words: the average treatment effect, $tau_"ATE"$, averages the effect over every unit; the
average treatment effect on the treated, $tau_"ATT"$, averages it over the units that were
actually treated. They are equal when every unit has the same effect, and can differ when
the units that got the treatment respond differently from those that didn't.

#project[
  *Your data, in this notation.* For the pick-rate question the unit is a changed card in its
  window, $D = 1$ means the patch changed it, and the outcome is its pick rate after the
  patch. Parry's $Y(1)$ is the after-patch pick rate you observed; its $Y(0)$ is the pick rate
  Parry would have had in the same weeks, with the same players, had the patch left it alone.
  The effect the project reports for each tweak is an estimate of $tau_"ATT"$ for that card:
  the effect of the patch on the cards the patch actually changed. For the strength question
  the unit is a run and $D = 1$ means the run took the card.
]

You can never see both versions of the same unit. That is why the rest of the guide exists:
each design builds a stand-in for the missing $Y(0)$. In @ch-did the stand-in is unchanged
cards; in @ch-wins it is the game's own random offers.

#watch[
  "Causal" is not a stronger word for "correlated". A correlation is a fact about the data
  you have. A causal effect is a claim about a counterfactual you can't observe, and it is
  only as good as the argument for the stand-in.
]

#skill[
  *Naming the counterfactual.* For any claimed effect, say out loud what the comparison
  group stands in for, and why it is a fair stand-in.
]

#check(
  ([What is a confounder? Name one in your data.],
   [Something that affects both who gets the treatment and the outcome. Player skill: it
    affects which cards are taken and whether the run is won.]),
  ([What is the counterfactual for "the effect of the patch on Parry's pick rate"?],
   [Parry's pick rate in the same weeks, with the same players, had the patch not changed
    Parry: its $Y(0)$.]),
  ([Why can't the causal effect for one run be observed directly?],
   [Each run happens once, with the treatment either on or off. By @eq-po-observed only one
    potential outcome is recorded; the other, the counterfactual, never happens.]),
  ([What is the difference between $tau_"ATE"$ and $tau_"ATT"$?],
   [$tau_"ATE"$ averages the effect over every unit, $tau_"ATT"$ over the treated units only.
    They differ when the treated units respond differently from the rest.]),
)

== Selection bias, written out

The naive comparison is the average outcome of the treated minus the average outcome of the
untreated. With the notation above it can be taken apart exactly. Add and subtract the
treated units' average untreated outcome, $"E"[Y(0) | D = 1]$ (a number you can't observe, but
can write down):

$ underbrace("E"[Y | D = 1] - "E"[Y | D = 0], "naive comparison")
  &= underbrace("E"[Y(1) - Y(0) | D = 1], tau_"ATT") \
  &+ underbrace("E"[Y(0) | D = 1] - "E"[Y(0) | D = 0], "selection bias") $ <eq-naive>

In words: the naive comparison equals the effect on the treated plus a second term, the
*selection bias*: how differently the treated and untreated units would have done if nobody
had been treated. The naive number is the causal effect only when that second term is zero.

#mathfull[
  The derivation is two lines. By @eq-po-observed, a treated unit's observed outcome is its
  $Y(1)$ and an untreated unit's is its $Y(0)$, so the naive comparison is
  $"E"[Y(1) | D = 1] - "E"[Y(0) | D = 0]$. Subtract and add $"E"[Y(0) | D = 1]$:

  $ "E"[Y(1) | D = 1] - "E"[Y(0) | D = 1] + "E"[Y(0) | D = 1] - "E"[Y(0) | D = 0] $

  In words: nothing has changed, because the same term was taken away and put back. The
  first pair is $tau_"ATT"$ (the difference of averages over the same group is the average of
  the differences) and the second pair is the selection bias. Nothing is assumed: the
  decomposition holds for any data. The assumptions come in when you argue the second pair
  is zero.

  When is it zero? When the treatment is assigned at random, by a coin flip that knows
  nothing about the units. Then $D$ is independent of $(Y(0), Y(1))$, the treated and
  untreated groups have the same average $Y(0)$, the selection term vanishes, and also
  $tau_"ATT" = tau_"ATE"$. That is why a randomized experiment can read its effect off a
  plain difference of averages, and why @ch-did needs more than that.
]

#project[
  *Simulation.* In the IV primer's game the naive comparison is #n("iv.single.naive") and the
  true effect is #n("iv.single.truth"). Every unit in that game has the same effect, so
  $tau_"ATT"$ is the truth, and the gap between the two numbers is the selection-bias term of
  @eq-naive: skilled players take the card more often and would have won more often without
  it, so $"E"[Y(0) | D = 1] > "E"[Y(0) | D = 0]$.

  *Your data.* The same decomposition applies to the patches. Designers don't change cards at
  random: they buff cards that are picked too little and nerf cards that are picked too much.
  So the changed cards' $Y(0)$, their pick rate without the change, differs from the unchanged
  cards' before anything happens. Parry was picked at #n("tweak.parry.v0_103_2.treated_rate_before")
  before the patch against #n("tweak.parry.v0_103_2.control_rate_before") for its unchanged
  neighbours. Comparing changed and unchanged cards after a patch carries that selection-bias
  term in full; @ch-did shows how a before period removes it.
]

#mixup[
  You might think player skill threatens every analysis in this project the same way. It
  doesn't. In the strength question ("does taking card X help you win?") the player chooses
  the treatment, and skill drives both the choice and the win: a direct confounder, present
  even with no patch at all. In the pick-rate question ("did the patch change how often X is
  picked?") the calendar chooses the treatment: every player got the patch on the same day.
  Skill can then only bias the answer if the mix of skill _changed_ across the patch _and_
  skilled players treat X differently from its controls. That is possible (more experienced
  players by June is one candidate explanation in @ch-explanations), but it is a narrower
  threat, and the model's ascension and uploader-group terms guard against part of it.
]

#watch[
  The decomposition in @eq-naive is exact, but the selection-bias term can't be computed from
  the data, because it needs $Y(0)$ for the treated units. A design never measures the bias
  away; it argues, from how the treatment was assigned, that the bias is zero or has been
  removed.
]

#skill[
  *Writing an estimate as the target plus a bias.* For any comparison, write what it equals in
  potential outcomes: the effect you want plus whatever else it picks up. The extra term tells
  you which assumption the comparison needs.
]

#check(
  ([Write the naive comparison as the sum of two terms, and name them.],
   [The effect on the treated, $"E"[Y(1) - Y(0) | D = 1]$, plus the selection bias,
    $"E"[Y(0) | D = 1] - "E"[Y(0) | D = 0]$ (@eq-naive).]),
  ([Why does random assignment make the naive comparison unbiased?],
   [A coin flip knows nothing about the units, so the treated and untreated groups have the
    same average untreated outcome; the selection-bias term is zero.]),
  ([Designers buff cards that are picked too little. Which sign does the selection-bias term
    have for an after-only comparison of buffed cards against unchanged ones?],
   [Negative: the buffed cards' untreated pick rate is below the unchanged cards', so the
    comparison understates the buff.]),
  ([Why is skill a direct confounder for "does taking X help you win?" but only a possible one
    for "did the patch change X's picks?"],
   [Players choose to take X, and skilled players both take certain cards and win more. The
    patch date isn't chosen by players, so skill matters only if the skill mix shifted across
    the patch in a way that treats X differently from its controls.]),
)

== The uploader groups as a live example

Your data has a visible version of selection. Runs uploaded through the SlayTheStats mod
(the tagged group) come from players who installed a mod to track their stats. They are not
a random slice of players, and it shows.

#project[
  *Your data.* On finished primary runs of v0.103.2, tagged runs won
  #n("audit.win_rate_v0_103_2_tagged_pct") of the time and untagged runs
  #n("audit.win_rate_v0_103_2_untagged_pct") (#n("audit.win_runs_v0_103_2_tagged") and
  #n("audit.win_runs_v0_103_2_untagged") runs); over all builds,
  #n("audit.win_rate_all_tagged_pct") against #n("audit.win_rate_all_untagged_pct"). The
  groups also rank cards differently. Over #n("audit.groups_0_103_2_cards") cards on
  v0.103.2, the rank correlation of their pick rates is #n("audit.groups_0_103_2_spearman"),
  and a card's pick rate typically differs by #n("audit.groups_0_103_2_gap_pct") between the
  groups (an absolute gap; @ch-counting explains the difference between this and a relative
  one). On v0.107.1: #n("audit.groups_0_107_1_spearman") and
  #n("audit.groups_0_107_1_gap_pct").
]

The groups already differed on v0.103.2, which was played before the mod showed any
community statistics, so the gap is mainly about who the players are. A gap of that size is
as large as many patch effects. So every pick-rate estimate in this guide is made with the
uploader group in the model (each group gets its own baseline), and the pooled version is a
check (@ch-checks).

#watch[
  The tagged group's higher win rate does not mean the mod makes people better. It is the
  vitamin picture again: the people who install a stats mod are a different crowd.
]

#skill[
  *Spotting selection in who contributes data.* Any dataset built from volunteers, users of
  one app, or people who opted in, carries the reasons they opted in. Look for a subgroup
  you can compare, as the tag allows here.
]

#check(
  ([Why do the uploader groups differ in win rate and in card rankings?],
   [They are different players: people who install a stats mod are likely more dedicated
    and more skilled. The difference was there before the mod showed community statistics,
    so it is mainly selection.]),
  ([How does the analysis protect the pick-rate estimates from the uploader-group
    difference?],
   [The model gives each uploader group its own baseline, so a change in the mix of groups
    can't look like a patch effect; the pooled model is run as a check.]),
  ([Why was v0.103.2 a useful build for this comparison?],
   [It was played before the mod showed community statistics, so a difference there can't be
    caused by the mod's tooltips.]),
)

== Why more data doesn't fix it

#picture[
  Survey a million vitamin takers and a million non-takers and you get a very precise answer
  to the wrong question. The difference between the groups will be known to many decimal
  places; it will still mix the vitamins with the people.
]

More data shrinks random scatter (@ch-noise), not unfairness. Selection is a property of how
the groups were formed, and it stays the same however many runs you add. In the notation of
@eq-naive: as the number of units grows, the naive comparison settles ever more tightly on
$tau_"ATT"$ plus the selection-bias term, not on $tau_"ATT"$. Its standard error shrinks
toward zero; its bias doesn't move. Larger data only makes the wrong number look more
certain. @ch-noise gives this a formula: an estimate's typical squared error is its bias
squared plus its variance, and only the variance falls with more data.

#project[
  *Simulation.* In the IV primer's game, the naive estimate's bias grows with how strongly
  skill drives picking: with no skill effect it is #n("iv.confounding.skill_0.naive_bias"),
  and at the strongest setting it is #n("iv.confounding.skill_0_12.naive_bias"), while the
  instrument's bias stays at #n("iv.confounding.skill_0_12.iv_bias").
  Over many repeated draws of the game, the naive estimate's 95% intervals (@ch-noise)
  contain the truth only #n("iv.draws.naive.coverage") of the time, against
  #n("iv.draws.iv.coverage") for the instrument's. The naive intervals are not wide and
  careless: their typical SE is #n("iv.draws.naive.mean_se"), smaller than the instrument's
  #n("iv.draws.iv.mean_se"). They are narrow and in the wrong place.
]

#watch[
  A tight error bar means a precise estimate, not an accurate one. Error bars measure random
  scatter only; they say nothing about whether the comparison is biased. With a million runs,
  even a small bias comes out precise and "significant".
]

#skill[
  *Separating bias from noise.* Noise shrinks with more data; bias doesn't. When someone
  offers more data as the fix, ask which of the two the problem is.
]

#check(
  ([Would ten times as many runs remove the confounding? Why or why not?],
   [No. Confounding comes from how the groups were formed; more runs give a more precise
    estimate of the same mixed-up comparison. In @eq-naive the selection-bias term doesn't
    depend on the number of units.]),
  ([In the simulation, what happens to the naive estimate's bias as skill drives picking
    more strongly?],
   [It grows, from zero when skill doesn't affect picking to a large overestimate at the
    strongest setting; the instrument's estimate stays close to the truth.]),
  ([What would go wrong if you reported the naive estimate with a very narrow interval?],
   [The interval would almost never contain the truth: it would state a wrong number with
    false confidence.]),
  ([The naive estimate in the simulation has a smaller SE than the instrument's, yet its
    intervals miss the truth far more often. How can both be true?],
   [The SE measures scatter around the estimate's own centre. The naive estimate scatters
    little, but its centre is off by the selection bias, so its narrow intervals sit in the
    wrong place.]),
)
