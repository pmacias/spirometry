#import "../style.typ": *

= The project on one page <ch-project>

#lead[Two questions about every balance patch, the data that answers them, and how this guide is built.]

#plain[
  *How the numbers in this guide are marked.* Numbers labelled *your data* come from the
  final rerun: the run tables built on #n("build.tables_built_at") from all
  #n("snapshot.pages") export pages (parser #n("build.parser_version")), through your
  notebooks, the export and the sensitivity tables. Numbers labelled *simulation* come from
  the IV primer's made-up game, where the true answer is known. A few checks were only ever
  run on the earlier #n("const.earlier_tables.pages")-page tables; they say so where they
  appear. Anything SPIROMETRY.md or PLAN.md marks as open is printed in red with a small label
  after it, #unverified[like this], and parts of the project that were never run are called
  *future work*. No number in this guide was typed by hand: each one is generated from the
  saved outputs, so a rebuild cannot leave a stale number behind.
]

Slay the Spire 2 has been in early access since March 2026. Every few weeks a patch changes
some cards: a block value goes down, a power applies one more stack, a card becomes
something else entirely. Players upload the log of each game they play to a public
service, and that log records every card the game offered them and whether they took it.
So every patch is a natural experiment: a known change, on a known date, with hundreds of
thousands of games on each side of it.

This project asks what those patches did. This chapter says what that means, what was
measured, and how the rest of the guide teaches it.

== Two questions about every patch

#picture[
  A restaurant chain changes a recipe: the same dish, a little more salt. Thousands of
  plates go out every day and come back to the kitchen, some empty and some barely touched.
  The chain wants to know two things. Did diners order the dish more often after the change?
  And did the change make the dish better, meaning that people who ate it enjoyed the meal
  more? The first is about what people chose. The second is about what the choice did for
  them. They need different evidence, because the people who order a dish are not a random
  sample of diners.
]

#words[
  - *Balance patch*: a game update that changes cards' numbers or rules.
  - *Card change*: one card's difference between two versions of the game.
  - *Run*: one game, from the first floor to a win or a death.
]

The project has two main questions about each card change.

#ftable(
  columns: (auto, rest, auto),
  [*Question*], [*In words*], [*Tool*],
  [Behaviour], [After the patch, do players pick this card more or less often when the game
    offers it?], [Difference-in-differences (@ch-did)],
  [Strength], [Does taking this card make a run more likely to win, and did that change with
    the patch?], [Instruments (@ch-wins)],
)

Two more questions build on these. *Dose-response* (@ch-dose) asks whether bigger number
changes move picks more than small ones. *Perception against strength* asks whether pick
rates follow real strength, or whether players over- or under-react to patch notes.

The behaviour question is answered for every numeric tweak the solo design can estimate,
with error bars, checks and a dose-response line: that was the project's minimum result,
and it is done. The strength question is answered only in a simulation (@ch-wins): the
real-data version, and with it perception against strength, is future work.

#project[
  *Your data.* The snapshot holds #n("snapshot.records") run records from
  #n("snapshot.pages") export pages, played between #n("snapshot.start_date") and
  #n("snapshot.end_date"). After removing repeats and counting each run once, that is
  #n("snapshot.distinct_runs") distinct runs. The behaviour question is answered for
  #n("tweaks.solo_estimable") numeric tweaks: #n("tweaks.first") in the first stable
  balance patch (v0.103.2, April 2026) and #n("tweaks.second") in the second (v0.107.1,
  June 2026).
]

#skill[
  *Turning a vague question into ones data can answer.* "What did the patch do?" is not
  measurable as it stands. "Did the share of offers on which players took this card change,
  compared with cards that did not change?" is. Most of the work in a data project is this
  translation, done before any model is fitted.
]

#check(
  ([In one sentence each, state the project's two main questions.],
   [Behaviour: after a patch, do players pick a changed card more or less often when it is
    offered? Strength: does taking the card make a run more likely to win, and did the patch
    change that?]),
  ([Why do the two questions need different tools?],
   [Picking is a choice the player makes about an offer the game decides, so the offer gives
    a clean starting point for a before-and-after comparison. Winning after taking a card
    mixes the card's effect with the kind of player who takes it, so it needs a design that
    removes that selection (instruments, @ch-wins).]),
  ([Which of the two questions does this project answer on real data, and which only in a
    simulation?],
   [Behaviour is answered on real data for every solo-estimable numeric tweak. Strength is
    answered only in the IV primer's simulation; the real-data version is future work.]),
)

== What a patch changes

Patches change cards in different ways, and the analysis treats them differently.

#picture[
  Back to the restaurant. Adding a little salt is a change of amount: the same dish, more
  or less of one ingredient. Replacing the fish with chicken under the same menu name is a
  different dish. You can ask "does more salt mean more orders?" of the first kind, and you
  can line up all the salt changes by how much salt was added. The second kind has no
  "how much": it can only be compared before and after.
]

#words[
  - *Numeric tweak*: a change to a number on a card, such as damage, block or the amount of a
    power, with the card's rules unchanged.
  - *Rework*: a change to what a card does. It gets a before-and-after comparison but no
    place on a dose-response line, because there is no single number that says how big the
    change was.
  - *Dose*: the size of a numeric tweak, measured on a fixed ruler (@ch-dose).
]

The card changes were classified from the game data's structured fields, not from the
patch-note text, and then cross-checked against the official patch notes. Only two game
updates count as balance releases for this project, the ones that reached stable players
as v0.103.2 and v0.107.1; other changelog differences turned out to be fixes to the data,
not to the game.

#project[
  *Your data.* The reference tables list #n("changes.card_patches") card changes between
  stable builds. Of these, #n("changes.tweak_only") are pure numeric tweaks,
  #n("changes.rework") are reworks, #n("changes.cost_change") change an energy cost and
  #n("changes.text_only") change only the card text (hand-labelled: some change a mechanic,
  some only the wording). Of the #n("tweaks.numeric") numeric tweaks,
  #n("tweaks.not_solo_estimable") can't be estimated from solo card rewards (colorless,
  basic or token cards, or a multiplayer-only card), which leaves
  #n("tweaks.solo_estimable"). Parry, for example, went from
  #n("tweak.parry.v0_103_2.old") to #n("tweak.parry.v0_103_2.new") on its main number in
  the first patch.
]

#fig("fig_timeline", [Game builds on a calendar, stable and beta, with the two stable
  balance patches and the builds their comparisons use.])

#watch[
  A "buff" in the patch notes does not always make every number go up. Some tweaks move
  one number up and another down; some change only the upgraded version of the card. The
  guide calls these *mixed-direction* and *upgrade-only* tweaks (@ch-results), and they get
  special handling wherever a direction or a size matters.
]

#skill[
  *Classifying the treatment before measuring it.* An effect estimate is only as clear as
  the definition of what changed. Separating amount changes from rule changes, and writing
  the rule down before looking at results, keeps the later comparisons honest.
]

#check(
  ([What is the difference between a numeric tweak and a rework, and why does only one of
    them get a place on a dose-response line?],
   [A numeric tweak changes a number and keeps the card's rules; a rework changes what the
    card does. A tweak has a size (a dose) that can be measured on one ruler; a rework has no
    such size, so it can only be compared before and after.]),
  ([Why were the card changes classified from structured fields rather than from the patch
    notes?],
   [The structured fields give exact old and new values for every card in a form a program
    can compare. The notes are prose, incomplete and sometimes vague; they were used as a
    cross-check.]),
  ([Some numeric tweaks can't be estimated from solo card rewards. Give one reason.],
   [The card is never offered on a solo character's reward screen: colorless, basic and
    token cards come from other sources, and one card is multiplayer-only.]),
)

== How this guide is built

Each chapter takes one idea the analysis relies on. It starts with an everyday picture,
then gives the words a statistician would use, then shows the same idea in your numbers.
A *skill* box names the general data-science skill each section exercises, the part you
would carry to any other project. *Watch out* boxes name the common mistake. Every section
ends with questions to answer out loud; the answers are in Appendix A.

#ftable(
  columns: (auto, rest),
  [*Part*], [*What it covers*],
  [Foundations], [The data (@ch-data), why simple comparisons mislead (@ch-confounding),
    counting (@ch-counting), noise (@ch-noise)],
  [The method], [Difference-in-differences (@ch-did), regression (@ch-regression),
    checking the design (@ch-checks), checking the error bars (@ch-placebo)],
  [The results], [Tweak by tweak (@ch-results), dose-response (@ch-dose)],
  [The puzzle], [Is it the ruler (@ch-rulers)? Is it the design (@ch-explanations)?],
  [Beyond picks], [Instruments, in a simulation (@ch-wins); what is settled and open
    (@ch-open)],
  [Back matter], [Answers, glossary, your numbers on one page, what is still open, and how
    to talk about the project],
)

One thread runs through the whole guide. The first patch moved pick rates in the
direction of each change and in proportion to its size. The second patch, with tweaks of
the same sizes, did not show that pattern. @ch-dose, @ch-rulers and @ch-explanations are
about that difference; @ch-open says how far it can be trusted and what remains
unexplained.

Three terms appear in this chapter only as names. *Difference-in-differences* is defined in
@ch-did, *instruments* in @ch-wins and *dose-response* in @ch-dose. Everywhere else, a term
is defined before it is used.

#skill[
  *Writing for the reader you will be later.* This guide is meant to let you explain each
  step without the code open. The same discipline (one idea at a time, each with a concrete
  example from the data) makes a good README, a good notebook and a good interview answer.
]

#check(
  ([What three things does each new idea in this guide come with, and in what order?],
   [An everyday picture, then the words (the term and its meaning), then the project's own
    example with the real number.]),
  ([Why is no number in this guide typed by hand?],
   [Every number is generated from the saved outputs and inserted by key, so rebuilding the
    guide after a rerun updates every number, and none can be stale or mistyped.]),
  ([State the thread that runs through the guide in two sentences.],
   [In the first patch, pick rates moved in the direction of each change and in proportion to
    its size. In the second patch, tweaks of the same sizes showed no such pattern, and why is
    still open.]),
)
