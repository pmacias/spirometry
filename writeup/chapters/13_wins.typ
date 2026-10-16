#import "../style.typ": *

= From picks to wins: instruments <ch-wins>

#lead[Does taking a card make a run more likely to win, and how can you tell when the players
  who take it are different?]

Pick rates say what players chose. The second question of @ch-project is whether the choice
was good: does taking a card raise the chance of winning? @ch-confounding showed why
comparing takers with non-takers fails. This chapter shows the fix the project built, an
*instrument*, using the IV primer's simulated game, where the true answer is known. The
real-data version is future work; the last section says what exists and what would come
next.

== The lottery for free gym passes

#picture[
  A city gives out free gym passes by lottery. Some winners never go; some losers buy a
  membership anyway. You want the effect of going to the gym on health. Comparing gym-goers
  with non-goers fails (healthy people go to the gym). But the lottery is random: winners and
  losers are alike in every way except the pass. So the health difference between winners
  and losers is caused by the pass, through the extra gym visits it caused. Divide that health
  difference by how much the pass raised gym-going, and you have the effect of going.
]

#words[
  - *Instrument*: a random push on the treatment that affects the outcome only through the
    treatment. Here, whether card X was offered.
  - *Intent-to-treat (ITT)*: the effect of being offered on winning: the lottery winners'
    health minus the losers'.
  - *First stage*: how much being offered raises taking the card: how much winning the
    lottery raised gym-going.
  - *IV estimate (Wald)*: ITT divided by the first stage. With more instruments or controls it
    is computed by two-stage least squares, the same idea.
]

In the game, the offer is the lottery: the random number generator decides whether card X
appears, regardless of who is playing. Runs that were offered X and runs that weren't are
alike before the offer, so their difference in winning is caused by the offer, and the offer
can only affect winning through the card being taken.

#skill[
  *Using randomness the system already has.* Look for something random that pushes the
  treatment: a lottery, a random assignment, a game's dice. It can stand in for an experiment
  you couldn't run.
]

#check(
  ([In the gym-pass picture, what are the instrument, the treatment, the ITT and the first
    stage?],
   [The lottery is the instrument; going to the gym is the treatment; the health difference
    between winners and losers is the ITT; how much winning raised gym-going is the first
    stage.]),
  ([Why is being offered a card a candidate instrument?],
   [The game's random generator decides it, so it doesn't depend on who the player is, and it
    plausibly affects winning only by letting the card be taken.]),
  ([How is the IV estimate computed from the ITT and the first stage?],
   [ITT divided by the first stage.]),
)

== Why it works, in a simulation

The IV primer builds a game where the truth is set by hand. A hidden skill raises both
picking card X and winning, as in @ch-confounding. Card X is offered at random. Taking X raises
the chance of winning by #n("iv.single.truth").

#project[
  *Simulation.* In one game of #n("iv.single.n_runs") runs, #n("iv.single.share_offered") were
  offered X and #n("iv.single.share_picked") took it. The naive comparison of takers and
  non-takers gives #n("iv.single.naive_pm"): too high, because of skill. The ITT is
  #n("iv.single.itt_pm"): small, because most runs never take X even when offered. The first
  stage is #n("iv.single.first_stage_pm"). Their ratio, the IV estimate, is
  #n("iv.single.iv_pm"), within its SE of the truth. Repeated over many draws of the game, the
  naive estimate averages #n("iv.draws.naive.mean") and its 95% interval contains the truth
  #n("iv.draws.naive.coverage") of the time; the IV estimate averages #n("iv.draws.iv.mean")
  and covers the truth #n("iv.draws.iv.coverage") of the time.
]

#fig("fig_iv_three", [The simulated game: the naive estimate, the ITT, the first stage and the
  IV estimate, against the true effect.])

#fig("fig_iv_draws", [Naive and IV estimates over many simulated draws of the game. The naive
  estimates cluster tightly around the wrong value; the IV estimates spread more widely around
  the truth.])

#watch[
  The IV estimate is noisier than the naive one: its SE here is about twice the naive SE. You
  trade precision for being right. A tight wrong answer is not better than a wide right one.
]

#skill[
  *Testing a method where you know the answer.* Before trusting a method on real data, build a
  small simulated world with a known truth, including the problem the method is meant to fix,
  and check that it recovers the truth.
]

#check(
  ([In the simulation, why is the ITT so much smaller than the true effect?],
   [Being offered only matters for runs that then take the card, and most offered runs don't;
    the ITT is the true effect diluted by the first stage.]),
  ([What does "covers the truth" mean for the naive and IV estimates over many draws?],
   [The share of draws whose 95% interval contains the true effect. The IV's is close to the
    promised rate; the naive's is far below it, because the naive estimate is biased.]),
  ([Why is the IV estimate noisier than the naive one?],
   [It divides a small, noisy ITT by the first stage, which magnifies the noise; it uses only
    the variation in taking the card that the random offer caused.]),
)

== Three assumptions

#words[
  - *Relevance*: the instrument really moves the treatment (being offered raises taking).
  - *Independence*: the instrument is as good as random (being offered doesn't depend on
    skill or anything else that affects winning).
  - *Exclusion*: the instrument affects the outcome only through the treatment (being offered
    a card you don't take doesn't change your chance of winning).
]

Relevance can be checked directly: the first stage is measured. Independence is plausible
because the game's random generator makes the offer, and it can be checked with a *balance
check*: runs offered X and runs not offered X should look alike on everything recorded before
the offer. Exclusion can't be checked from the data; it is an argument about the game.

#project[
  *Simulation.* The primer breaks each assumption on purpose. If the offer depends on skill
  (independence fails), the IV estimate becomes #n("iv.broken.offer_depends_on_skill.iv")
  against a truth of #n("iv.single.truth"). If being offered acts on winning directly
  (exclusion fails), it becomes #n("iv.broken.offer_acts_on_winning_directly.iv"). With all
  three holding, it is #n("iv.broken.clean.iv").
]

#watch[
  Exclusion is the assumption people forget. In the game, simply seeing a card might change
  how a player builds their deck even if they pass it. That would be a direct effect of the
  offer, and IV would credit it to taking the card.
]

#skill[
  *Stating which assumptions are testable.* For each assumption of a design, say whether the
  data can check it, and if not, what argument supports it.
]

#check(
  ([Name the three IV assumptions and say which one can't be checked from the data.],
   [Relevance, independence, exclusion. Exclusion can't be checked: it is an argument that
    the offer affects winning only through taking the card.]),
  ([What is a balance check, and which assumption does it support?],
   [A comparison of offered and not-offered runs on things recorded before the offer; it
    supports independence.]),
  ([Give an example of how exclusion could fail in the game.],
   [Seeing a card on a reward screen could change a player's plan for their deck even if they
    don't take it, which would affect winning directly.]),
)

== Why only the first reward screens

#words[
  - *First K screens*: the treatment is "took X on one of the run's first few reward
    screens", and the instrument is "was offered X on one of them". Later rewards, shops and
    events don't count.
  - *Survival bias*: later screens are reached only by runs that survived, so being offered a
    card late is already a sign of a strong run.
]

#picture[
  If the gym lottery were drawn only among people who had already kept up a month of
  exercise, winners would be fitter than the general public for reasons unrelated to the
  pass. Draw it on day one, among everyone, and the comparison is fair.
]

Every run reaches its first screens, so an offer there is not yet tied to how the run is
going. The tooling also drops runs that don't reach the K-th screen, because counting
unreached screens as "not offered" makes every card look as if being offered helps; the check
for that choice is K equal to one, where every offered run reached its screen. Retried runs
(@ch-data) are dropped, since their endings were chosen.

#project[
  *Your data.* This is how the real-data tooling (`spirometry.wins`) is built: the first three
  reward screens of each run, one row per run, with each build's week and the ascension level
  as baselines, and heteroskedasticity-robust errors. It has been tested on synthetic runs and
  on two fetched export pages. It has not been run on the full tables: that is future work.
]

#watch[
  "Ever offered the card in the run" is the tempting instrument and the wrong one: long runs
  see more cards, and long runs are winning runs.
]

#skill[
  *Defining the treatment window to avoid survival bias.* Measure exposure at a point every
  unit reaches, before the outcome starts to shape who is still observed.
]

#check(
  ([Why does the instrument use only the first few reward screens?],
   [Every run reaches them, so being offered there isn't a sign the run is going well; later
    screens are reached only by runs that survived.]),
  ([Why are runs that don't reach the K-th screen dropped, and what checks that choice?],
   [Counting their unreached screens as "not offered" would make offers look helpful (those
    runs lost early). The check is K equal to one, which every offered run reached.]),
  ([Why are retried runs dropped from win analyses?],
   [Their copies have different endings, and any rule for choosing one copy depends on the
    ending.]),
)

== Who the estimate is about

#words[
  - *Compliers*: runs that take the card when it is offered and don't when it isn't. The
    lottery winners who go to the gym only because they won.
  - *Non-compliance*: some offered runs don't take the card (and a few not-offered runs get it
    another way). IV handles it by dividing by the first stage.
  - *Complier shift*: after a patch, the set of runs that take a card changes, so an IV
    estimate can change because the takers changed.
]

IV estimates the effect for compliers, not for every run. If the card helps some decks more
than others, and the runs that take it are the ones it helps, the IV estimate is larger than
the average effect over all runs.

#project[
  *Simulation.* In the primer's version where the effect differs between runs, the IV
  estimate is #n("iv.het.iv_estimate"). The true effect among the runs that take the card is
  #n("iv.het.true_among_pickers")\; over all runs it is #n("iv.het.true_all"). IV recovers the
  first, not the second.
]

#watch[
  "Taking this card raises win rate by this much" should end with "for the runs that take it
  when offered". After a buff, more runs take the card, and a falling IV estimate could mean
  the new takers benefit less, not that the card got weaker.
]

#skill[
  *Saying whom an estimate is about.* Every causal estimate averages over some group. Name
  the group, and ask whether it changed between the things you compare.
]

#check(
  ([Who are the compliers in the card game?],
   [Runs that take card X when it is offered and wouldn't have it otherwise.]),
  ([In the simulation, why is the IV estimate above the all-runs effect?],
   [The runs that take the card are the ones it helps most, and IV estimates the effect for
    them.]),
  ([Why does the complier shift matter when comparing IV estimates before and after a
    patch?],
   [The patch changes who takes the card, so a change in the IV estimate could be a change in
    who complies rather than in the card's strength.]),
)

== When the instrument is weak or broken

#words[
  - *Weak instrument*: a first stage so small that dividing by it blows up the noise. The
    usual rule of thumb is a first-stage F < 10 (F measures how clearly the first stage is
    nonzero).
]

#picture[
  A lottery that almost nobody uses: a pass that is rarely redeemed. The difference between
  winners and losers is tiny and noisy, and dividing it by an almost-zero redemption rate
  gives a wild answer.
]

#project[
  *Simulation.* The primer shrinks the first stage step by step. With a first stage of
  #n("iv.weak.intercept_minus_1.first_stage") (F about #n("iv.weak.intercept_minus_1.f")), the
  middle eighty percent of IV estimates runs from #n("iv.weak.intercept_minus_1.iv_p10") to
  #n("iv.weak.intercept_minus_1.iv_p90"). With #n("iv.weak.intercept_minus_4.first_stage")
  (F about #n("iv.weak.intercept_minus_4.f")): #n("iv.weak.intercept_minus_4.iv_p10") to
  #n("iv.weak.intercept_minus_4.iv_p90"). With #n("iv.weak.intercept_minus_6.first_stage")
  (F about #n("iv.weak.intercept_minus_6.f"), below the rule of thumb in
  #n("iv.weak.intercept_minus_6.share_f_below_10") of draws):
  #n("iv.weak.intercept_minus_6.iv_p10") to #n("iv.weak.intercept_minus_6.iv_p90"), useless for a
  true effect of #n("iv.single.truth").
]

#fig("fig_iv_weak", [Spread of IV estimates as the first stage weakens, against the first
  stage's F.])

For real cards this matters twice. Rarely picked cards have weak first stages, and a single
card is a small part of a run, so its effect on winning is small. The planned power check
was meant to measure, on a few cards of one build, whether per-card IV errors are small
enough to be useful before running all cards.

#watch[
  A weak instrument doesn't announce itself in the IV estimate, which can look perfectly
  ordinary on any one draw. Only the first stage tells you. A strong first stage is the price
  of admission, not a detail.
]

#skill[
  *Checking the strength of an instrument first.* Report the first stage and its F before the
  IV estimate. If F is small, stop.
]

#check(
  ([What makes an instrument weak, and what happens to the IV estimate?],
   [A first stage near zero (F < 10 as a rule of thumb). The estimate's spread blows up
    because a noisy ITT is divided by a tiny number.]),
  ([Why are rarely picked cards a problem for IV?],
   [Being offered barely raises taking them, so their first stage is weak.]),
  ([What would go wrong if you reported an IV estimate without its first stage?],
   [A reader couldn't tell whether the estimate is meaningful or a division by almost
    nothing.]),
)

== Real runs: what is built and what is future work

The real-data side has tooling and no results. `spirometry.wins` computes the ITT, first
stage, IV and naive comparisons per card within a build, and balance checks for the offer;
`spirometry.strength` takes the IV before and after a patch, net of unchanged cards, which is
the strength question. The decisions they encode are in the decision log: the first three
screens; short runs dropped with the one-screen check; retried and abandoned runs out; week
and build baselines because win rates drift within a build (@ch-data); and a term for which
kinds of screens came first (an early elite offers rarer cards), off by default and
#unverified[undecided].

#project[
  *Your data.* No real win effect is reported in this guide. The power check on a few cards of
  one build, which would decide whether per-card win effects are precise enough to be worth
  running, was not run: real win effects, the strength change across patches and the
  comparison of perception against strength are future work (decision of October 2026). The
  real-data balance check has #unverified[not been run] either.
]

#watch[
  Having tooling is not having results. In an interview, say clearly that the win-effect
  design is built and tested in simulation, and that real-data estimates are future work.
]

#skill[
  *Knowing when to stop.* A design that is likely too noisy for its question should be tested
  for power on a small slice before the full run, with a rule for stopping written down in
  advance.
]

#check(
  ([What exists on the real-data side of the win-effect question, and what doesn't?],
   [Tooling for ITT, first stage, IV, balance checks and the before-and-after strength
    change, tested on synthetic runs and two fetched pages. No real results: the power check
    and the full runs are future work.]),
  ([Why was a power check planned before running every card?],
   [A single card is a small part of a run and some cards have weak first stages, so per-card
    IV errors might be too large to say anything; a small check would show that cheaply.]),
  ([Why do the win fits include week and build baselines?],
   [Win rates drift within a build over calendar time, so comparing runs from different weeks
    would mix in that drift.]),
)
