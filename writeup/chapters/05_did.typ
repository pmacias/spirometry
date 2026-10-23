#import "../style.typ": *

= Difference-in-differences <ch-did>

#lead[How to separate what the patch did from everything else that changed at the same time.]

A patch is not the only thing that happens between two builds. Players get better, a new
strategy spreads, the mix of players shifts, other cards change. A card's pick rate before
and after the patch moves for all of those reasons together. This chapter explains the
method that takes out the shared part, difference-in-differences; writes down exactly what it
estimates and what it assumes; and goes through the ways that assumption can fail in a game
where cards compete for the same picks.

== Two plants on a windowsill

#picture[
  Two plants sit on the same windowsill. You give one fertilizer and not the other. A month
  later the fertilized plant has grown ten centimetres. Was it the fertilizer? Partly: it
  was also a sunny month. The other plant grew six. Both had the same sun, so the
  fertilizer's share is the difference of the two growths: four centimetres. You subtract
  one change from another, which is where the name comes from.
]

#words[
  - *Difference-in-differences (DiD)*: the treated group's change minus the control group's
    change over the same period.
  - *Treated card*: the card the patch changed.
  - *Control cards*: unchanged cards of the same character (the same *color*), seen in the
    same builds. They play the plant without fertilizer.
]

The treated card and its controls are offered in the same runs, by the same players, in the
same weeks. Whatever happened to the game as a whole between the two builds (players
improving, the meta moving, a change in who uploads) moves the controls too, and the
subtraction removes it.

#skill[
  *Choosing a comparison group.* The control group should share everything with the treated
  group except the treatment. Ask what else could have changed, and whether the controls
  felt it too.
]

#check(
  ([In the windowsill picture, what plays the role of the patch, the treated card and the
    control cards?],
   [The fertilizer is the patch; the fertilized plant is the treated card; the unfertilized
    plant is the control cards.]),
  ([Why does DiD subtract the controls' change rather than compare the treated card with the
    controls after the patch?],
   [The treated card and the controls may start at different levels (different pick rates).
    Comparing changes removes that fixed difference; comparing levels after the patch would
    mix it in.]),
  ([Name two things other than the patch that could move a card's pick rate between two
    builds.],
   [Any two of: players getting better; the meta (popular strategies) moving; a change in who
    plays or uploads; other cards changing.]),
)

== Parry by hand

The simplest DiD needs only four numbers: the treated card's pick rate before and after,
and the controls' before and after. These four numbers make a 2×2 table. In symbols, give each
offer two yes-or-no labels: $T_i = 1$ if it is an offer of the treated card (zero for a
control), and $A_i = 1$ if it is in the after block (zero for before). Write
$overline(y)_(t, s)$ for the pick rate of the cell with $T = t$ and $A = s$: the average of
@eq-phat over the offers in that cell. The DiD is

$ hat(tau)_"DiD" = (overline(y)_(1, 1) - overline(y)_(1, 0)) - (overline(y)_(0, 1) - overline(y)_(0, 0)) $ <eq-did>

In words: the estimated effect is the treated card's change in pick rate (after minus before)
minus the controls' change over the same builds. Its error bar follows from @eq-se-diff: the
four cell averages come from different offers, so their squared SEs add.

#ftable(
  columns: (auto, auto, auto, auto),
  [], [*Before (v0.99.1)*], [*After (v0.103.2)*], [*Change (points)*],
  [Parry], [#n("tweak.parry.v0_103_2.treated_rate_before")],
    [#n("tweak.parry.v0_103_2.treated_rate_after")],
    [#n("tweak.parry.v0_103_2.treated_change_pp")],
  [Controls], [#n("tweak.parry.v0_103_2.control_rate_before")],
    [#n("tweak.parry.v0_103_2.control_rate_after")],
    [#n("tweak.parry.v0_103_2.control_change_pp")],
  [*Difference*], [], [], [*#n("tweak.parry.v0_103_2.did_raw_pp")*],
)

#project[
  *Your data.* Parry's controls are #n("tweak.parry.v0_103_2.n_control_cards") unchanged cards
  of its character. They barely moved; Parry's own change
  was #n("tweak.parry.v0_103_2.treated_change_pp") points, so the hand calculation of
  @eq-did gives #n("tweak.parry.v0_103_2.did_raw_pp"). The regression of @ch-regression, which
  compares like with like within each run's group, gives
  #n("tweak.parry.v0_103_2.all.beta_pp_pm") over all after-weeks and
  #n("tweak.parry.v0_103_2.h3.beta_pp_pm") over weeks 0–3. The hand calculation and the model
  agree, which is the first thing to check whenever a model reports a DiD.
]

#fig("fig_parry_did", [Parry and its controls before and after. The dashed line is the
  counterfactual: where Parry would have ended if it had moved like its controls.])

#watch[
  The dashed line in the figure is not data. It is the counterfactual the method assumes,
  and the next sections are about when that assumption is safe.
]

#skill[
  *Checking a model against a hand calculation.* Before trusting a regression, compute the
  simplest version of the same quantity by hand. If they disagree badly, find out why before
  going on.
]

#check(
  ([Compute Parry's DiD from the 2×2 table in words: what do you subtract from what?],
   [Parry's change (after minus before) minus the controls' change (after minus before),
    @eq-did.]),
  ([The controls' pick rate barely moved. Why is the DiD still worth computing for Parry?],
   [You only know the controls barely moved because you measured them. For other cards and
    windows the controls move by a point or two, as large as many effects.]),
  ([What does the dashed line in the Parry figure represent?],
   [The counterfactual: Parry's pick rate after the patch had it moved like its controls.]),
  ([How would you get the SE of @eq-did from the four cells' SEs?],
   [Square each cell's SE, add the four, and take the root: the cells come from different
    offers, so their errors add in quadrature (@eq-se-diff).]),
)

== Why both differences

There are two simpler comparisons, and each fails in its own way. The potential outcomes of
@ch-confounding say exactly how. For a cell, write $mu_(t, s)$ for the pick rate it would have
had _without_ the patch: the average untreated outcome $"E"[Y(0)]$ over that cell's offers.
Only the treated card after the patch is actually treated, so three of the four observed cells
are untreated outcomes, and the fourth is the untreated outcome plus the effect $tau$ (the
effect on the treated card, $tau_"ATT"$ of @eq-ate-att). Ignoring sampling noise:

$ overline(y)_(0, 0) = mu_(0, 0), quad overline(y)_(0, 1) = mu_(0, 1), quad
  overline(y)_(1, 0) = mu_(1, 0), quad overline(y)_(1, 1) = mu_(1, 1) + tau $ <eq-did-cells-po>

In words: every cell shows its untreated pick rate, except the treated card after the patch,
which shows its untreated pick rate plus the effect.

*Treated against controls, after only.* This takes the bottom-right cell minus the
top-right one:

$ overline(y)_(1, 1) - overline(y)_(0, 1) = tau + underbrace((mu_(1, 1) - mu_(0, 1)), "baseline gap") $ <eq-after-only>

In words: the after-only comparison is the effect plus however differently the treated card
and its controls would have been picked anyway. That second term is the selection bias of
@eq-naive. After the patch Parry was picked at about the same rate as its controls; before,
it was picked at about half their rate. The after-only comparison would call the patch's
effect zero.

*Before against after, treated card only.* This takes the treated row's change:

$ overline(y)_(1, 1) - overline(y)_(1, 0) = tau + underbrace((mu_(1, 1) - mu_(1, 0)), "time change") $ <eq-before-after>

In words: the before-and-after comparison is the effect plus whatever would have happened to
the treated card's pick rate over the same time anyway: players improving, the meta moving.
Corrosive Wave shows the difference it makes: its own pick rate changed by
#n("tweak.corrosive_wave.v0_103_2.treated_change_pp") points, but its controls' changed by
#n("tweak.corrosive_wave.v0_103_2.control_change_pp") over the same builds, so the DiD is
#n("tweak.corrosive_wave.v0_103_2.did_raw_pp").

*Both differences.* Subtract the controls' change from the treated card's change, as @eq-did
does, and the fixed baseline gap cancels within each row while the shared time change cancels
between the rows. What is left is the effect plus one term, which the next section is about.

#picture[
  A runner's time improves after new shoes. Before-after alone credits the shoes with the
  cool weather; comparing her with other runners on race day alone credits the shoes with
  her talent. Comparing her improvement with theirs, on the same course on the same days,
  credits the shoes with what is left.
]

#project[
  *A worked example, not your data.* Four 2×2 tables of pick rates in percent, and what each
  comparison says:

  #align(center, small-table(
    columns: (auto, auto, auto, auto, auto, auto),
    [*Case*], [*Treated before, after*], [*Controls before, after*], [*After only*],
      [*Before/after*], [*DiD*],
    [A buff closes a gap],
      [#n("toy.four_ways.parry_like.t_before"), #n("toy.four_ways.parry_like.t_after")],
      [#n("toy.four_ways.parry_like.c_before"), #n("toy.four_ways.parry_like.c_after")],
      [#n("toy.four_ways.parry_like.after_only")], [#n("toy.four_ways.parry_like.before_after")],
      [#n("toy.four_ways.parry_like.did")],
    [The same, plus a meta shift],
      [#n("toy.four_ways.meta_shift.t_before"), #n("toy.four_ways.meta_shift.t_after")],
      [#n("toy.four_ways.meta_shift.c_before"), #n("toy.four_ways.meta_shift.c_after")],
      [#n("toy.four_ways.meta_shift.after_only")], [#n("toy.four_ways.meta_shift.before_after")],
      [#n("toy.four_ways.meta_shift.did")],
    [A popular card, small buff],
      [#n("toy.four_ways.popular.t_before"), #n("toy.four_ways.popular.t_after")],
      [#n("toy.four_ways.popular.c_before"), #n("toy.four_ways.popular.c_after")],
      [#n("toy.four_ways.popular.after_only")], [#n("toy.four_ways.popular.before_after")],
      [#n("toy.four_ways.popular.did")],
  ))

  The DiD gets the effect in every case. After-only says nothing happened in the first two and
  credits the third card's popularity to the patch. Before/after is fooled by the meta shift.
]

#incode("teaching_sims.four_ways", [The three comparisons on a 2×2 table.])[
  *What goes in:* four pick rates per case. *What comes out:* after-only, before/after and DiD.
  The lines that matter: `after_only` is @eq-after-only, `before_after` is @eq-before-after
  and `did` is @eq-did. Each is one subtraction; the point is which cells each one uses.
]

#mixup[
  You might read "the after-only comparison would call the effect zero" as if leaving out the
  before period means subtracting zero, so the answer is trivially zero. It isn't trivial.
  After-only is a real number, the treated card's rate minus its controls' rate after the
  patch, and for Parry it _happens_ to come out near zero because two things cancel: a negative
  baseline gap (Parry was always picked less than its controls) and a positive effect (the buff
  closed that gap). @eq-after-only measures the sum. For another card the same mistake could
  give a large number in either direction. The problem isn't zero; it's that one snapshot
  mixes two things you can't separate.
]

*Why after-only is exactly right in an A/B test.* In a randomized experiment, users are
assigned to treatment or control by a coin flip, so the two groups have the same $Y(0)$ on
average: the baseline gap of @eq-after-only is zero, and the after-only comparison _is_ the
effect. That is the standard A/B readout. It fails here because cards are not assigned to
patches by a coin. Designers buff weak cards and nerf strong ones; Parry was buffed _because_
it was picked less. The before period is how the starting gap is measured and removed.

Note what the control is in an A/B test: the _same_ thing, without the change, at the _same_
time. The game's version would be the developers randomly giving half of all runs the buffed
Parry and half the old Parry, during the same weeks: same card, same weeks, same kind of
players, only the version differs. That never happened, because every player got the patch at
once, so the only "without the change" data for Parry is _earlier_, which brings in everything
else that changed over time. The other cards stand in for "what time did to everything". Two
different kinds of comparison: same unit, two groups, one time (A/B); and one unit over time
against other units over time (DiD).

#project[
  *Your data.* The closest thing to two versions at once is the beta branch, which had the new
  card weeks before stable did. But players chose to play beta, so it is a staggered rollout,
  not a randomized test; @ch-open lists it as future work. A different randomization, not to be
  mixed up with this one: the game randomly _offers_ cards. That is an experiment on runs
  (offered against not offered), and it is what @ch-wins uses for the strength question. It
  doesn't answer "did the patch change picks".
]

#watch[
  "It went up after the patch" is a before-after claim, and it is the one people make most.
  Ask what the unchanged cards did over the same builds. And even true A/B tests use the
  before period: it doesn't remove bias there, but it cuts noise (the industry name is CUPED).
]

#skill[
  *Ruling out the boring explanations.* Each simpler comparison fails for a specific reason
  (time trends, fixed differences). Writing each as "the effect plus a named term" tells you
  which design removes which term.
]

#check(
  ([What does a before-and-after comparison of the treated card alone count as the patch's
    effect that it shouldn't?],
   [Everything else that changed between the builds: players improving, meta drift,
    changes in who plays. The time-change term of @eq-before-after.]),
  ([Why would an after-only comparison have called Parry's effect zero?],
   [After the patch Parry was picked at about its controls' rate. The comparison ignores that
    before the patch it was picked far less: the negative baseline gap and the positive effect
    cancel in @eq-after-only.]),
  ([A card is picked #n("toy.four_ways.held_still.t_before")% before and
    #n("toy.four_ways.held_still.t_after")% after; its controls
    #n("toy.four_ways.held_still.c_before")% before and #n("toy.four_ways.held_still.c_after")%
    after. What do after-only, before/after and DiD say?],
   [After-only #n("toy.four_ways.held_still.after_only"), before/after
    #n("toy.four_ways.held_still.before_after"), DiD #n("toy.four_ways.held_still.did") points.
    The card held still while everything around it rose: relative to its controls, it lost
    ground.]),
  ([Why is the after-only comparison exactly right in a randomized A/B test but not here?],
   [Random assignment makes the treated and control groups alike before the change, so the
    baseline gap is zero. Patches are not random: designers change cards because of their pick
    rates, so the gap is large.]),
  ([In an A/B test of Parry's buff, what would the control be?],
   [Runs with the old Parry, in the same weeks, randomly chosen: the same card without the
    change, at the same time.]),
  ([For Corrosive Wave, which is larger in size: the raw before-after change or the DiD? Why?],
   [The DiD: the controls rose over the same builds, so subtracting their change makes the
    fall larger.]),
)

== The one assumption: parallel trends

#words[
  - *Parallel trends*: without the patch, the treated card would have moved like its
    controls. DiD needs this and nothing else.
  - *Fixed horizon (weeks 0–3)*: only the first four weeks after the after-build's release
    count, so both patches are compared over the same length of time. *All weeks* uses every
    week the after-build was played.
]

#picture[
  Two plants on the same windowsill get the same sun, so their growth is a fair comparison.
  Put one on a shadier shelf and the comparison breaks: it would have grown less anyway.
  Parallel trends is the claim that the treated card and its controls sat on the same
  windowsill.
]

Put @eq-did-cells-po into @eq-did. The effect $tau$ comes out once, and so does a combination
of untreated pick rates:

$ hat(tau)_"DiD" = tau + underbrace([(mu_(1, 1) - mu_(1, 0)) - (mu_(0, 1) - mu_(0, 0))], "difference in untreated trends") $ <eq-did-bias>

In words: the DiD equals the effect plus the difference between how the treated card and how
the controls would have moved without the patch. The baseline gap is gone (each row is a
change), and so is any shift common to both rows. The assumption that makes the leftover term
zero is parallel trends:

$ mu_(1, 1) - mu_(1, 0) = mu_(0, 1) - mu_(0, 0) $ <eq-parallel>

In words: had the patch not happened, the treated card's pick rate would have changed by the
same amount as its controls' between the two blocks. The treated card may sit higher or lower
than its controls; it just has to move in step with them.

Parallel trends can't be proved, because it is about the counterfactual. It can be made
plausible: the controls are offered in the same runs, and @ch-checks looks at the weeks
before the patch to see whether the treated card was already drifting away from its
controls.

The horizon is a decision of the same kind. The first patch's after-build was played for
many more weeks than the second's, and effects can grow or fade. Comparing both over
weeks 0–3 holds the length fixed; all weeks is the secondary version. The weeks are counted from
each build's listed release date. Both stable releases reached most players about a day
after that date, the same offset in both patches, so it can't make a difference between
them.

#project[
  *Your data.* Most of each effect arrives in the first month. Parry: #n("tweak.parry.v0_103_2.h3.beta_pp_pm")
  over weeks 0–3 against #n("tweak.parry.v0_103_2.all.beta_pp_pm") over all weeks. Over
  weeks 0–3, the median effect size is #n("did.h3.first.median_abs_beta_pp") points in the first
  patch and #n("did.h3.second.median_abs_beta_pp") in the second; over all weeks,
  #n("did.all.first.median_abs_beta_pp") and #n("did.all.second.median_abs_beta_pp"). The
  horizon is not why the patches differ.
]

#fig("fig_parry_weekly", [Parry's weekly gap to its controls, before and after the patch.
  Flat before, a step at release, flat after: what parallel trends looks like when it holds.])

#watch[
  "The trends were parallel before the patch" supports the assumption; it doesn't prove it.
  Something could start at the same time as the patch and affect only the treated card.
]

#skill[
  *Stating the identifying assumption.* Every causal design rests on one assumption you
  can't test directly. Say it in one sentence, then say what evidence makes it plausible.
]

#check(
  ([State the parallel-trends assumption in one sentence for Parry.],
   [Had the patch not changed Parry, its pick rate would have moved like its controls' pick
    rate between v0.99.1 and v0.103.2.]),
  ([In @eq-did-bias, which two terms of the simpler comparisons have cancelled, and which term
    is left?],
   [The baseline gap (cancelled within each row) and the shared time change (cancelled between
    rows). What is left is the difference between the treated card's and the controls'
    untreated trends, zero under parallel trends.]),
  ([Does parallel trends require the treated card and its controls to have the same pick rate
    before the patch?],
   [No. They can sit at any distance apart; they only have to move in step without the
    patch.]),
  ([Why use a fixed horizon of weeks 0–3 for the main comparison?],
   [The two patches' after-builds were played for different lengths of time. A fixed horizon
    compares both over the same weeks, so a difference between patches can't come from
    effects growing or fading over time.]),
  ([What would go wrong if a card was already becoming more popular before the patch, and its
    controls weren't?],
   [Parallel trends would fail: the DiD would count the existing drift as part of the patch's
    effect.]),
)

== Can pick rates trend if cards compete?

Every reward screen is a contest between cards: if one card is taken, the others on that
screen aren't. So it is tempting to think the total of all pick rates is fixed, and that
nothing can trend. The intuition is right about a conserved total in one narrow case, and it
still doesn't protect parallel trends.

#words[
  - *Skip rate*: the share of reward screens on which the player takes nothing.
  - *Drift*: a slow change in a card's pick rate, or in its gap to the controls, that has
    nothing to do with the patch (players discovering a card, a strategy spreading).
  - *Event study*: the gap between the treated card and its controls, week by week, instead
    of collapsed into a before and an after average.
]

On one screen with cards $j$, every card is picked or not, and exactly one card is picked or
the screen is skipped. With $"skip" = 1$ for a skipped screen and zero otherwise:

$ sum_(j in "screen") y_j = 1 - "skip" $ <eq-screen-total>

In words: the picks on a screen add up to one minus the skip indicator. Three things stop that
from fixing pick rates in place. First, the skip rate can drift: as players learn that thin
decks win, they skip more, and every card's pick rate falls together, so "all cards" can
trend. Second, the controls are not all cards: picks can flow between them and the changed
cards (spillover, below), so their average isn't conserved even when the screen total is.
Third, parallel trends is about one card against the controls, not about the total. A fixed
total still lets one card rise while the others fall a little each.

Collapsing turns a drift into a step. Suppose the treated card's gap to its controls grows by
$kappa$ every week $u$ with no patch at all, $g_u = g_0 + kappa u$. DiD averages the gap over
the before weeks and the after weeks and subtracts:

$ hat(tau)_"DiD" = overline(g)_"after" - overline(g)_"before" = kappa (overline(u)_"after" - overline(u)_"before") $ <eq-drift-step>

In words: a steady drift in the gap shows up in the DiD as an "effect" equal to the drift per
week times the distance between the two blocks' average weeks. Shared drift cancels (it
doesn't move the gap); only drift _relative to the controls_ fools the DiD. It needn't be
steady, and longer windows let more of it pile up, which is one reason the main horizon is
fixed at weeks 0–3.

#fig("fig_toy_drift", [A simulation with known truth, with no patch at all. Left: the skip
  rate rises from #n("toy.drift.skip_first") to #n("toy.drift.skip_last") and the controls'
  pick rate falls with it, so the total of pick rates isn't fixed. Right: card zero, being
  discovered, gains on its controls every week; a "patch" placed at week
  #n("toy.drift.fake_patch_week") would be credited with that climb.])

#project[
  *A simulation with known truth.* Screens of three cards from one character plus a skip,
  played for ten weeks, with a skip option that grows a little more appealing every week and
  one card that players are slowly discovering. No patch at all. A DiD with a fake patch date at
  week #n("toy.drift.fake_patch_week") reports #n("toy.drift.did_pp") points: @eq-drift-step
  in action. The rising gap before the fake date is exactly what the weekly event-study plot of
  @ch-checks is built to catch.

  *Your data.* The closest the fits come to a conserved total is the sensitivity option that
  keeps only screens where something was picked (@ch-checks): it removes the choice to take
  nothing, so the shares on each screen sum to one. Even then a single card can trend against
  the rest, so parallel trends is still checked week by week.
]

#incode("teaching_sims.drift", [Weekly pick rates with a drifting skip rate and one card being
  discovered.])[
  *What goes in:* the number of cards, weeks and screens per week, and the two drifts. *What
  comes out:* each week's skip rate, card zero's pick rate and the controls', and a DiD at a
  fake patch date. The lines that matter: `a[0] += discovery * w` makes card zero more
  appealing each week; the last column of `u`, `skip_drift * w`, makes skipping more appealing.
  `prob` is a logit choice among the three cards and the skip, so @eq-screen-total holds on
  every screen. The last two lines are @eq-did on weekly averages, which turns the drift into
  a step (@eq-drift-step).
]

#mixup[
  You might reason that because every card competes with the others for picks, one card's
  gain is another's loss, so the pick rate of "all cards" can't move and there is nothing to
  trend. The screen total in @eq-screen-total is fixed only once skips are counted, and the
  skip rate can drift. More importantly, parallel trends is about one card against its
  controls, not the total: a fixed total still allows one card to rise while the rest fall a
  little each. If Parry had been gaining a point a week before any patch, conservation would
  only say that the rise was paid for by tiny losses spread over everyone else, and the DiD
  would still credit the rise to the patch.
]

The weeks _after_ release matter too. A gap that is still rising after release (slow
adoption) means weeks 0–3 understates the eventual effect; a gap that jumps and then fades
(novelty from reading the patch notes) means it overstates the lasting one. A flat after period
is one clean step that stuck. If the gap is still rising, the pre-specified weeks 0–3 number
stays the headline (switching horizons after seeing the results is a forking path), labelled
as a likely lower bound, with all weeks as the secondary horizon.

#watch[
  An event study's flat pre-period supports parallel trends; it doesn't prove it. With few
  before-weeks (the second patch's short before block gives two or three), a slow drift can
  hide inside the error bars.
]

#skill[
  *Not collapsing too early.* Before averaging a time series into "before" and "after", plot
  it at the finest grain that is still readable. A trend that averaging would turn into a step
  is easy to see week by week.
]

#check(
  ([Name two reasons the controls' average pick rate can trend even though cards compete.],
   [The skip rate can change, moving every card's pick rate together; and picks can flow
    between the controls and the changed cards (spillover). Changes in which cards are offered
    together can also move it.]),
  ([If the picks per screen were truly fixed, could parallel trends still fail? How?],
   [Yes. One card can rise while the others fall slightly, for instance because players are
    discovering it. Its gap to the controls trends before the patch, and the DiD counts that as
    part of the effect.]),
  ([By @eq-drift-step, what happens to a drift's false "effect" if the before and after blocks
    are made longer?],
   [It grows: the distance between the two blocks' average weeks grows, so more drift piles up
    between them.]),
  ([The gap is still rising at the end of weeks 0–3. What does that say about the weeks 0–3
    estimate, and should you switch to all weeks?],
   [It is probably a lower bound on the eventual effect. Keep the pre-specified horizon as the
    headline, say so, and show all weeks as the secondary number.]),
)

== Choosing the controls

#words[
  - *Control exclusions*: same-color cards that changed in the same window are left out of
    the controls, since they had their own treatment.
  - *Bug-fix flags*: cards whose behaviour changed through a bug fix, with no change in their
    numbers. They stay in the controls; dropping them is a check.
]

The controls for each tweak are the other cards of the same character that the patch did
not change, seen in both blocks. Every card changed in the window, the treated card's
neighbours included, is out. Colorless cards are never controls: they are offered to every
character from other sources and rarely appear on the reward screens the fit uses.

The second patch's before block is v0.103.3 alone. Pooling the earlier stable build
v0.103.2 into it would give more data, but the treated cards drifted between those two
builds, and pooling moves several estimates; @ch-checks shows how much. The first patch's
cards are not excluded from the second patch's controls; dropping them is also a check and
changes nothing.

#project[
  *Your data.* Each tweak has a few dozen controls (Parry has
  #n("tweak.parry.v0_103_2.n_control_cards"), Corrosive Wave
  #n("tweak.corrosive_wave.v0_103_2.n_control_cards")). Dropping the bug-fix-flagged cards
  from the controls moves the estimates by a median #n("robustness.h3_drop_behavior_flags.median_shift_se")
  SEs (weeks 0–3).
]

#watch[
  Same-color controls share the treated card's screens, so a change to one card can move its
  controls' picks too (players take a buffed card instead of a control). The next section
  shows which way that pushes the estimates, and @ch-explanations checks it with other
  characters' cards as controls.
]

#skill[
  *Writing down the control rule before seeing results.* Who counts as a control, and who is
  excluded, should follow from the design, not from which choice gives the nicest answer.
]

#check(
  ([Why are cards of the same character used as controls?],
   [They are offered in the same runs, to the same players, in the same weeks, so whatever
    else changed for that character between builds affects them too.]),
  ([Why is a same-color card that changed in the same window left out of the controls?],
   [It had its own treatment, so its change would contaminate the control group's change.]),
  ([Why is the second patch's before block v0.103.3 alone and not pooled with v0.103.2?],
   [The treated cards drifted between the two builds; pooling would mix that drift into the
    before block and move several estimates.]),
)

== When the controls are partly treated: spillover

DiD assumes the controls show what would have happened without the patch. But a nerf pushes
players away from the treated card and toward other cards, the controls among them. Then the
controls are not untouched: they are partly treated.

#words[
  - *Spillover (substitution)*: the treatment of one unit changes another unit's outcome. Here,
    a change to one card moves the picks of the cards it competes with.
  - *SUTVA* (the stable unit treatment value assumption): each unit's potential outcomes depend
    only on its own treatment, not on anyone else's. Spillover is a violation of it, also called
    *interference*.
  - *Control scope*: which unchanged cards serve as controls: the same character's (the main
    choice) or other characters' (a check).
  - *Estimand*: the exact quantity an estimate is meant to measure.
]

#picture[
  Discount one brand of cereal and its rival's sales fall. Measure the discount's effect against
  the rival and you count the rival's loss as part of the gain: the comparison group was moved
  by the very thing you are measuring.
]

Say the controls' change has two parts: the common trend everyone shares, and a spillover
$psi$ caused by the patch itself. The treated card's change is the trend plus $tau$. Then

$ hat(tau)_"DiD" = (tau + "trend") - ("trend" + psi) = tau - psi $ <eq-spillover>

In words: with spillover, the DiD is the effect minus the patch's push on the controls.
Substitution makes $psi$ the opposite sign to $tau$: a nerf sends picks to the controls
($tau < 0$, $psi > 0$), a buff takes picks from them ($tau > 0$, $psi < 0$). Either way
$tau - psi$ is further from zero than $tau$. Spillover makes effects look too big; it can't
hide them.

Why one card's spillover is small and a patch's can be large: one nerfed card's lost picks are
spread over dozens of controls, so each moves a little. A patch that buffs many cards of the
same character at once pulls picks away from every control together, and then the controls move
noticeably.

#fig("fig_toy_spillover", [A simulation with known truth: the DiD for card zero with three
  choices of controls, against the truth (dashed). A: only card zero nerfed. B:
  #n("toy.spillover.n_buffed") of the #n("toy.spillover.k") cards buffed at once, card zero
  among them.])

#project[
  *A simulation with known truth.* Reward screens of three cards drawn from
  #n("toy.spillover.k") cards of one character, plus a skip, with a logit choice on each card's
  appeal. No other shocks, so card zero's own change is the truth, and other characters'
  controls (whose change is zero) recover it exactly.

  #align(center, small-table(
    columns: (auto, auto, auto),
    [*Points*], [*A: one card nerfed*], [*B: several buffed at once*],
    [Truth: card zero's own change], [#n("toy.spillover.a.truth_pp")], [#n("toy.spillover.b.truth_pp")],
    [Same-character controls' change], [#n("toy.spillover.a.ctrl_change_pp")], [#n("toy.spillover.b.ctrl_change_pp")],
    [DiD, same-character controls], [#n("toy.spillover.a.did_same_pp")], [#n("toy.spillover.b.did_same_pp")],
    [DiD, same character, card zero's screens dropped], [#n("toy.spillover.a.did_drop_screens_pp")], [#n("toy.spillover.b.did_drop_screens_pp")],
    [DiD, other characters' controls], [#n("toy.spillover.a.did_other_pp")], [#n("toy.spillover.b.did_other_pp")],
  ))

  In A the controls barely move and same-character DiD overstates the nerf a little; dropping
  the screens that held card zero removes it, because in this toy all of A's spillover happens
  on shared screens. In B the controls fall by a sizeable share of card zero's own change, and
  dropping card zero's screens barely helps: the other buffed cards still pull picks from the
  controls on every other screen.

  *Your data.* Dropping the screens that held the treated card moves the real estimates by a
  median of only #n("robustness.h3_drop_shared_screens.median_shift_se") SEs (weeks 0–3). That
  looks more like B than A: if there is spillover, it isn't players choosing between the two
  cards on one screen, but something at the level of the run or the character. The refit with
  other characters' cards as controls is in @ch-explanations. One reading, not tested: the
  first patch changed many cards of the same characters at once and moved picks a lot, so it
  had much more to spill than the second patch, whose cards barely moved picks.
]

#incode("teaching_sims.spillover_all", [Reward screens with a logit choice, and the two
  spillover scenarios.])[
  *What goes in:* the number of cards and screens. *What comes out:* for each scenario, card
  zero's own change and the DiD with each choice of controls. The lines that matter: in
  `simulate_screens`, `np.argsort(rng.random(...))[:, :3]` draws three distinct cards per
  screen, and `prob = np.exp(u) / np.exp(u).sum(...)` is the logit choice among them and the
  skip, so a more appealing card takes picks from the others on its screen (the substitution).
  `pick_rate(..., drop_screens_with=[0])` drops every screen that showed card zero. In
  `scenario`, `d_treated - d_ctrl` is @eq-did with same-character controls, and
  subtracting zero in the last line uses controls that never share a screen.
]

Other characters' cards can't be substitutes, because they are never offered in the same runs.
The cost is that they don't share the treated character's own shocks (a boss change that hits
one character, a strategy that spreads for one character), which is the problem of the next
section in reverse. Neither control group is perfect, so the conclusion is checked against
both.

There is also a question of what is being estimated. When many cards change together, "the
effect of the buff" can mean the card's change _in that patch_, competing with the other buffs,
or its effect _if it had been buffed alone_. Other characters' controls estimate the first.
Worth saying which you mean.

#watch[
  Spillover can't be fixed by adding data: like any bias, it is a property of the comparison
  (@eq-mse). It is tested by changing the controls, not by tightening the error bars.
]

#skill[
  *Asking whether the control group was touched.* Before trusting any comparison group, ask
  whether the treatment could have reached it: through competition, through shared users,
  through the same budget. If it could, find a control group it can't reach and compare.
]

#check(
  ([Does substitution make a nerf look too big or too small with same-character controls? A
    buff?],
   [Too big in both cases: the controls move opposite to the treated card, so $tau - psi$
    in @eq-spillover is further from zero than $tau$.]),
  ([Why not just switch to other characters' controls for everything?],
   [They can't be substitutes, but they don't share the treated character's own shocks, so
    they swap one bias for another. They are a check: a conclusion that survives both is what's
    convincing.]),
  ([Why would spillover be much bigger in a patch that buffed many cards of one character
    than for a single nerf?],
   [One card's lost or gained picks are spread thinly over many controls. Many changed cards
    pull on every control at once, so the controls move together and noticeably.]),
  ([Dropping the treated card's screens barely moved the real estimates. What does that rule
    out, and what doesn't it?],
   [It rules out spillover living mainly on shared screens (players choosing between the two
    cards on one screen). It doesn't rule out spillover at the level of the run or the
    character.]),
)

== Shocks to one kind of card

A patch rarely changes only cards. The same update can change a boss, an enemy or a relic, and
some of those changes hit one kind of card harder than another.

#words[
  - *Confounder (for a DiD)*: something that, first, changes at the same time as the treatment
    and, second, affects the treated card differently from its controls. Both are needed: anything that
    hits treated and controls equally cancels in @eq-did.
  - *Card type*: attack, skill or power. Same-character controls are a mix of types.
  - *Type-level placebo*: a comparison of unchanged cards of one type against unchanged cards
    of another across a patch. With no type-wide shock, it should show nothing.
]

#picture[
  A shop discounts one umbrella in the week it starts raining. Compared with the whole shop,
  the rain looks like the discount's effect. Compared with the other umbrellas, it cancels.
]

Say a nerfed skill is treated, and the same patch adds a boss that pushes every skill's pick
rate down by $h$. A share $w$ of its controls are skills; the rest are attacks the boss doesn't
touch. The treated card's change is $tau + h$; the controls' average change is $w h$. Then

$ hat(tau)_"mixed" = (tau + h) - w h = tau + (1 - w) h $ <eq-type-shock>

In words: with controls that are only partly of the treated card's type, the DiD picks up the
type-wide shock in proportion to the share of the controls that _don't_ share the treated
card's type. Same-character controls protect against shocks that hit the whole character
($w$ would be one for such a shock); they don't protect against shocks that hit one kind of
card.

#fig("fig_toy_type_shock", width: medium, [A simulation with known truth: a skill nerfed
  in the same patch as a change that hits every skill, estimated four ways. Mixed controls
  absorb only part of the shock; skill-only controls recover the truth.])

#project[
  *A simulation with known truth.* A skill is nerfed by #n("toy.type_shock.truth_pp")
  points in a patch that also pushes every skill down by #n("toy.type_shock.boss_hit_pp").
  Its controls are #n("toy.type_shock.n_ctrl_skill") skills and #n("toy.type_shock.n_ctrl_attack")
  attacks. Before/after alone gives #n("toy.type_shock.naive_pp")\; DiD with all the
  character's controls gives #n("toy.type_shock.did_mixed_pp"), as @eq-type-shock predicts;
  DiD with skill-only controls gives #n("toy.type_shock.did_skill_only_pp"), the truth. In real
  data the cost of type-matched controls is a smaller, noisier control group.

  *Your data.* Whether non-card changes (bosses, enemies, relics) in the two windows hit one
  card type unevenly is #unverified[not checked]. The offer-rate check of @ch-checks covers
  offers by rarity, not picks by type. The cheapest test is a type-level placebo: unchanged
  skills against unchanged attacks across each patch. It is listed as an open question in
  @ch-open. The dose-response slope (@ch-dose) is less exposed than any single card: a
  type-wide shock bends it only if the big tweaks are mostly of one type.
]

#incode("teaching_sims.type_shock", [A shock to one card type and three ways to estimate the
  nerf.])[
  *What goes in:* the numbers of skill and attack controls, the true nerf and the shock.
  *What comes out:* before/after, DiD with mixed controls and DiD with skill-only controls. The
  lines that matter: `after_t = before_t + true_nerf + boss_hit_on_skills` is the treated
  skill's change; `after_s` moves by the shock, `after_a` doesn't. `change_t - all_ctrl` is
  @eq-type-shock with $w$ the share of skills among the controls; `change_t - skill_ctrl` uses
  $w$ of one, so the shock cancels.
]

#watch[
  A design that removes shared shocks is only as good as its definition of "shared". Ask which
  shocks the controls share with the treated card (the character's) and which they don't (its
  type, its rarity, its role in a deck).
]

#skill[
  *Listing what else changed.* For any before-and-after design, list every change that landed
  in the same window, not only the one you are studying, and ask which of them could hit the
  treated unit and its controls unequally.
]

#check(
  ([Why do same-character controls protect you from a boss that got harder for Ironclad
    overall, but not from one that punishes multi-attacks?],
   [The Ironclad-wide shock hits treated and controls equally and cancels; the multi-attack
    shock hits the treated card more than its mixed controls (@eq-type-shock).]),
  ([A multi-attack card is buffed, and the same patch adds a boss that punishes multi-attacks.
    Is the estimated effect too big or too small?],
   [Too small: the boss pushes the card's picks down, hiding part of the buff, and the mixed
    controls absorb only part of that push.]),
  ([What are the two conditions for something to confound a DiD?],
   [It changes at the same time as the treatment, and it affects the treated card differently
    from its controls.]),
)
