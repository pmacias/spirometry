#import "../style.typ": *

= Difference-in-differences <ch-did>

#lead[How to separate what the patch did from everything else that changed at the same time.]

A patch is not the only thing that happens between two builds. Players get better, a new
strategy spreads, the mix of players shifts, other cards change. A card's pick rate before
and after the patch moves for all of those reasons together. This chapter explains the
method that takes out the shared part: difference-in-differences.

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
and the controls' before and after. These four numbers make a 2×2 table.

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
  was #n("tweak.parry.v0_103_2.treated_change_pp") points, so the hand calculation gives
  #n("tweak.parry.v0_103_2.did_raw_pp"). The regression of @ch-regression, which compares like
  with like within each run's group, gives #n("tweak.parry.v0_103_2.all.beta_pp_pm") over all
  after-weeks and #n("tweak.parry.v0_103_2.h3.beta_pp_pm") over weeks 0–3. The hand
  calculation and the model agree, which is the first thing to check whenever a model
  reports a DiD.
]

#fig("fig_parry_did", [Parry and its controls before and after. The dashed line is the
  counterfactual: where Parry would have ended if it had moved like its controls.])

#watch[
  The dashed line in the figure is not data. It is the counterfactual the method assumes,
  and the next two sections are about when that assumption is safe.
]

#skill[
  *Checking a model against a hand calculation.* Before trusting a regression, compute the
  simplest version of the same quantity by hand. If they disagree badly, find out why before
  going on.
]

#check(
  ([Compute Parry's DiD from the 2×2 table in words: what do you subtract from what?],
   [Parry's change (after minus before) minus the controls' change (after minus before).]),
  ([The controls' pick rate barely moved. Why is the DiD still worth computing for Parry?],
   [You only know the controls barely moved because you measured them. For other cards and
    windows the controls move by a point or two, as large as many effects.]),
  ([What does the dashed line in the Parry figure represent?],
   [The counterfactual: Parry's pick rate after the patch had it moved like its controls.]),
)

== Why not the simpler comparisons

There are two simpler comparisons, and each fails in its own way.

*Before against after, treated card only.* This counts everything that changed between the
builds as the patch's effect. Corrosive Wave shows the difference it makes: its own pick
rate changed by #n("tweak.corrosive_wave.v0_103_2.treated_change_pp") points, but its controls'
changed by #n("tweak.corrosive_wave.v0_103_2.control_change_pp") over the same builds, so the DiD is
#n("tweak.corrosive_wave.v0_103_2.did_raw_pp").

*Treated against controls, after only.* This mixes the patch with how differently the
cards were valued all along. After the patch Parry was picked at about the same rate as its
controls; before, it was picked at about half their rate. The after-only comparison would
call the patch's effect zero.

#picture[
  A runner's time improves after new shoes. Before-after alone credits the shoes with the
  cool weather; comparing her with other runners on race day alone credits the shoes with
  her talent. Comparing her improvement with theirs, on the same course on the same days,
  credits the shoes with what is left.
]

#watch[
  "It went up after the patch" is a before-after claim, and it is the one people make most.
  Ask what the unchanged cards did over the same builds.
]

#skill[
  *Ruling out the boring explanations.* Each simpler comparison fails for a specific reason
  (time trends, fixed differences). Naming the reason tells you which design fixes it.
]

#check(
  ([What does a before-and-after comparison of the treated card alone count as the patch's
    effect that it shouldn't?],
   [Everything else that changed between the builds: players improving, meta drift,
    changes in who plays.]),
  ([Why would an after-only comparison have called Parry's effect zero?],
   [After the patch Parry was picked at about its controls' rate. The comparison ignores that
    before the patch it was picked far less, so the rise disappears.]),
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
  ([Why use a fixed horizon of weeks 0–3 for the main comparison?],
   [The two patches' after-builds were played for different lengths of time. A fixed horizon
    compares both over the same weeks, so a difference between patches can't come from
    effects growing or fading over time.]),
  ([What would go wrong if a card was already becoming more popular before the patch, and its
    controls weren't?],
   [Parallel trends would fail: the DiD would count the existing drift as part of the patch's
    effect.]),
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
  controls' picks too (players take a buffed card instead of a control). @ch-explanations
  shows which way that pushes the estimates and checks it with other characters' cards as
  controls.
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
  ([What could go wrong with same-color controls if players take a buffed card instead of a
    control card?],
   [The controls' pick rate would fall because of the patch, so the subtraction would make the
    buff's effect look larger than it was (substitution, or spillover).]),
)
