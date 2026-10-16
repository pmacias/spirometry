#import "../style.typ": *

= Why "just compare" doesn't work <ch-confounding>

#lead[Confounding: when the group that got the treatment was different to start with.]

The obvious way to ask whether a card is good is to compare runs that took it with runs that
didn't. This chapter explains why that comparison measures the wrong thing, shows the same
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

== The words

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
]

#picture[
  The counterfactual is the road not taken. You took the motorway and arrived in an hour;
  would the back road have been faster? You can never drive both roads with the same
  traffic on the same day. Every method in this guide is a way of estimating the road not
  taken from roads other people drove.
]

You can never see both versions of the same run. That is why the rest of the guide exists:
each design builds a stand-in for the counterfactual. In @ch-did the stand-in is unchanged
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
    Parry.]),
  ([Why can't the causal effect for one run be observed directly?],
   [Each run happens once, with the treatment either on or off. The other version, the
    counterfactual, never happens.]),
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

More data shrinks luck (@ch-noise), not unfairness. Selection is a property of how the
groups were formed, and it stays the same however many runs you add. Larger data only makes
the wrong number look more certain.

#project[
  *Simulation.* In the IV primer's game, the naive estimate's bias grows with how strongly
  skill drives picking: with no skill effect it is #n("iv.confounding.skill_0.naive_bias"),
  and at the strongest setting it is #n("iv.confounding.skill_0_12.naive_bias"), while the
  instrument's bias stays at #n("iv.confounding.skill_0_12.iv_bias").
  Over many repeated draws of the game, the naive estimate's 95% intervals (@ch-noise)
  contain the truth only #n("iv.draws.naive.coverage") of the time, against
  #n("iv.draws.iv.coverage") for the instrument's.
]

#watch[
  A tight error bar is not evidence that a comparison is fair. Error bars measure luck only.
]

#skill[
  *Separating bias from noise.* Noise shrinks with more data; bias doesn't. When someone
  offers more data as the fix, ask which of the two the problem is.
]

#check(
  ([Would ten times as many runs remove the confounding? Why or why not?],
   [No. Confounding comes from how the groups were formed; more runs give a more precise
    estimate of the same mixed-up comparison.]),
  ([In the simulation, what happens to the naive estimate's bias as skill drives picking
    more strongly?],
   [It grows, from zero when skill doesn't affect picking to a large overestimate at the
    strongest setting; the instrument's estimate stays close to the truth.]),
  ([What would go wrong if you reported the naive estimate with a very narrow interval?],
   [The interval would almost never contain the truth: it would state a wrong number with
    false confidence.]),
)
