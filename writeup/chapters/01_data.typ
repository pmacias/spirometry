#import "../style.typ": *

= The data: run files, offers, and which runs count <ch-data>

#lead[What a run file records, how the download was cleaned, and which runs the analysis uses.]

Every number in this guide starts from run files that players uploaded. Before any method,
you need to know what is in those files, what can go wrong with them, and which ones the
analysis keeps. An interviewer will ask about this first, and many of the project's
decisions are here.

== What a run file records

#picture[
  A run file is a flight recorder for one game. It does not explain why the pilot did
  anything, but it logs every event in order: which floor, which fight, which cards were
  dealt, which one was kept. A reward screen is a hand of cards dealt to you; each card in
  the hand is either kept or passed.
]

#words[
  - *Run file (record)*: the uploaded log of one run. It holds the character, the ascension
    level (a difficulty setting), the game version, whether the run was won, and every floor
    with what happened on it.
  - *Reward screen*: the choice of cards the game shows after a fight. Usually three cards;
    the player takes one or none.
  - *Offer*: one card shown on a reward screen. An offer is *picked* (taken) or not.
]

The key fact about offers is that *the game's random number generator decides which cards
appear*. The player decides only which one to take. So the run file records both what was
available and what was chosen, for every reward screen of every run. That is what makes a
pick rate measurable at all, and it is the starting point of every design in this guide.

Not every list of cards in a run file is a clean reward screen. Shops, events and some
relics also write card lists, and a few relics put two screens into one list. The analysis
uses card rewards after fights (normal fights, elites, bosses, and fights that start from
an event), and splits merged lists into screens where the relic that caused them can be
identified.

In symbols, which the rest of the guide uses: an offer is indexed by $i$, belongs to run
$r(i)$, shows card $c(i)$, and has the outcome

$ y_i = cases(1 & "if the card was picked,", 0 & "if it was not.") $ <eq-offer>

In words: each offer becomes a single number, one for a pick and zero for anything else (a
different card taken, or nothing). Everything later in the guide is built from these zeros
and ones: a pick rate is their average (@ch-counting), an effect is a difference of such
averages (@ch-did), and a regression is a machine for computing those differences
(@ch-regression).

#project[
  *Your data.* The unit of analysis is the *card offer*: one row per card shown on a reward
  screen, with whether it was picked. Shops are kept in a separate table and are not part of
  the main analysis. The stable builds the two patches compare hold
  #n("audit.offers_0_99_1") offers (v0.99.1), #n("audit.offers_0_103_2") (v0.103.2),
  #n("audit.offers_0_103_3") (v0.103.3) and #n("audit.offers_0_107_1") (v0.107.1). One run
  produces many offers, which matters for the error bars (@ch-regression).
]

#watch[
  "Picked" is a choice among the cards on that screen, and the alternative is often to take
  nothing. A card's pick rate can move because players value it differently, or because
  they skip more screens altogether. The design in @ch-did compares each card with others
  on the same kind of screens, which takes out a general change in skipping.
]

#skill[
  *Learning the data's generating process before modelling it.* Knowing that the game, not
  the player, decides the offers is what tells you which comparisons are fair. Ask "who or
  what decided each column?" for every dataset you meet.
]

#check(
  ([What is an offer, and what two outcomes can it have?],
   [One card shown on a reward screen. It is either picked (taken) or not.]),
  ([Who decides which cards appear on a reward screen, and why does that matter for the
    analysis?],
   [The game's random number generator. Because the player does not choose what is offered,
    the set of offers is not shaped by who the player is, which makes pick rates and later
    the offer-as-instrument design possible.]),
  ([In @eq-offer, what is $y_i$ for an offer of Parry on a screen where the player took a
    different card? And on a screen where they skipped?],
   [Zero both times. $y_i$ is one only when this offer's card was the one taken.]),
  ([Why are shop lists left out of the main analysis?],
   [A shop is a different choice (paying gold, from a shelf with different rules), and solo
    shop logs list only the unsold cards, so they are not comparable with reward screens.
    They sit in a separate table.]),
)

== Builds, branches and patch windows

#picture[
  The game has a main road and a test track. New changes go to the test track first, where
  players who opted in try them, and reach the main road a few weeks later. To see what a
  change did on the main road, you compare traffic on the main road just before and just
  after the change arrived there.
]

#words[
  - *Build*: one game version, such as v0.103.2. Every run file says which build it was
    played on.
  - *Stable and beta branch*: the main release that most players get, and the opt-in test
    release that gets changes earlier.
  - *Patch window*: the builds compared around one change. The *before block* is the build
    (or pooled builds) just before the change reached stable; the *after block* is the first
    build carrying it.
]

The branch of a build comes from the project's reference table of builds, never from the
run file: the export's records have no branch field. Write $B(r)$ for the build run $r$ was
played on. A window is a pair of sets of builds, before and after:

$ W = (cal(B)^-, cal(B)^+), quad "block"(r) = cases("before" & "if" B(r) in cal(B)^-, "after" & "if" B(r) in cal(B)^+) $ <eq-window>

In words: a window names the builds on each side of a change, and a run's block is decided
by its build alone, never by its date. The first patch's window is
$({"v0.99.1"}, {"v0.103.2"})$ and the second's $({"v0.103.3"}, {"v0.107.1"})$; a run on any
other build is in neither block of that window. The two stable windows are
v0.99.1 → v0.103.2 (the first patch, April 2026) and v0.103.3 → v0.107.1 (the second,
June 2026). v0.103.3 was a stable hotfix that changed no card's numbers (it carried a few
bug fixes, flagged for a check in @ch-checks), and it is the second patch's before block on
its own.

#project[
  *Your data.* The first patch's window compares #n("tweaks.first") numeric tweaks, the
  second's #n("tweaks.second"). Each changed card is compared against unchanged cards of the
  same character in the same window (@ch-did). Beta builds carry many of the same changes
  earlier; the comparison uses stable builds only, and beta play comes back as a check in
  @ch-checks (anticipation).
]

#fig("fig_runs_per_build", [Primary runs (and all distinct runs) per build, stable and beta.])

#watch[
  A run's build tells you which card versions it had, not the date it was played. Old builds
  keep being played for months after they are replaced, and the analysis always assigns card
  versions from the build, never from the date.
]

#skill[
  *Defining the comparison window.* Before-and-after studies live or die on what "before"
  and "after" mean. Write them down as specific units (here, builds), not as vague periods.
]

#check(
  ([What is a patch window, and what are its before and after blocks?],
   [The builds compared around one change: the before block is the stable build (or pooled
    builds) just before the change reached stable, the after block the first stable build
    carrying it.]),
  ([Why is the branch taken from the reference table rather than from the run file?],
   [The run files have no branch field. The reference table of builds says which branch each
    build was released on.]),
  ([Name the two stable windows the project compares.],
   [v0.99.1 → v0.103.2 (first patch) and v0.103.3 → v0.107.1 (second patch).]),
  ([A run on v0.103.2 is played in June, after v0.103.3 was released. Which block of the
    second patch's window is it in?],
   [Neither. By @eq-window a run's block depends on its build, and v0.103.2 is in neither
    set of that window. (It is the first patch's after block.)]),
)

== The snapshot and the backfill

#picture[
  Think of a shared holiday album. Some people upload their photos the same evening, others
  months later in one big batch. If you count photos per day on a given date, recent days
  look thin, and they keep filling in long after. Two groups uploading in different ways can
  also look different for reasons that have nothing to do with the holiday.
]

#words[
  - *Snapshot*: the downloaded copy of the export, as it stood when the download finished.
  - *Backfill (upload lag)*: runs uploaded long after they were played. The lag is the time
    from playing to uploading.
  - *Uploader group*: runs uploaded through the SlayTheStats mod carry a stamp (*tagged*);
    runs uploaded any other way do not (*untagged*). The mod uploads a player's whole local
    history at once, oldest first.
]

#project[
  *Your data.* The snapshot is complete: #n("snapshot.pages") pages, #n("snapshot.records")
  records, played from #n("snapshot.start_date") to #n("snapshot.end_date"). Upload lag on
  primary runs is long: median #n("audit.lag_median_days") days; #n("audit.lag_share_over_7d")
  of runs arrive more than a week after being played, #n("audit.lag_share_over_30d") more
  than a month after and #n("audit.lag_share_over_90d") more than three months after. Tagged
  runs lag far more (median #n("audit.lag_median_days_tagged") days, untagged
  #n("audit.lag_median_days_untagged")). The snapshot's start date in the download log was
  not in the part of the log checked, so it is left blank there; the play dates above come
  from the runs themselves.
]

#fig("fig_upload_lag", [Share of primary runs uploaded more than a given number of days after
  being played, all runs and by uploader group.])

#watch[
  Because of backfill, runs played in the last weeks before the snapshot ended are
  under-counted, tagged runs most of all. And the tagged share by play date measures upload
  timing, not who was playing; the analysis never uses it as a population measure.
]

#skill[
  *Knowing how your data arrived.* The time a record was created and the time it reached you
  are different clocks. Checking the gap between them tells you which periods are complete.
]

#check(
  ([What is backfill, and why does it make the last weeks of the snapshot thin?],
   [Runs uploaded long after they were played. Runs played shortly before the download ended
    had less time to be uploaded, so many of them were not yet in the export.]),
  ([Why do tagged runs lag so much more than untagged ones?],
   [The SlayTheStats mod uploads each user's whole local history at once, oldest first, so
    many tagged runs reach the export months after they were played.]),
  ([What would go wrong if you read the tagged share of runs by play date as "the share of
    players using the mod"?],
   [The share depends on when histories were uploaded and where the snapshot ends, not on how
    many people played with the mod at the time. It would show drops and rises that are
    upload timing.]),
)

== Duplicates and retries

#picture[
  A guest who signs the guest book twice is one guest. A player who replays a level from a
  save and writes down both attempts has played one level, but has two different endings on
  record. The first is a duplicate to drop; the second needs a rule, because keeping the
  better attempt would flatter the player.
]

#words[
  - *Duplicate record*: the same run uploaded more than once.
  - *Run key*: the label that identifies one run across records (a hash of the game's seed,
    start time, the characters and the ascension).
  - *Retried run*: copies of one run whose endings differ (in win, floors reached or
    abandonment), most likely a restored save.
]

There were two layers of duplicates. A block of export pages was downloaded twice; those
records are identical apart from one token field and are dropped as exact repeats. Then
some runs were uploaded more than once under different records; the run key finds them and
keeps one copy. For pick rates one copy is enough, because the copies share their early
reward screens. For win analyses (@ch-wins) a retried run is dropped altogether: keeping the
most complete copy would keep the attempt that went better.

*The keys in symbols.* Two different labels do the work. A record's *run hash* comes with the
export and is identical for identical records, so it finds the re-downloaded pages. The *run
key* is computed by the parser from four fields of the record:

$ "key"(r) = "trunc"("hash"("seed"_r || "start"_r || "sort"("chars"_r) || "asc"_r)) $ <eq-run-key>

In words: the run key is a hash, $"hash"$ (SHA-256), of the seed, the start time, the characters
sorted into a fixed order and the ascension, joined end to end ($||$), cut to its first
sixteen hex characters. Sorting matters for co-op copies, which can list the same players in
different orders. Two records with the same key are copies of one run. Among the copies
$C_q = {r : "key"(r) = q}$ of a key $q$ the tables keep the first by page and line, and mark the run as
retried if the copies disagree on how it ended:

$ "retried"(q) = exists r, r' in C_q : ("win"_r, "floors"_r, "abandoned"_r) != ("win"_(r'), "floors"_(r'), "abandoned"_(r')) $ <eq-retried>

In words: a run key is retried when any two of its copies differ in whether the run was won,
how many floors it reached or whether it was abandoned.

*Hashing player identifiers.* Co-op records carry each player's Steam ID, and newer records an
uploader token. Neither is needed for any result, but both are useful for checks (the
stayers of @ch-explanations). The parser replaces each with a *keyed* hash:

$ "id"' = "trunc"("HMAC"_"salt" ("id")) $ <eq-player-hash>

In words: the stored identifier is a keyed hash (HMAC-SHA256) of the original, using a secret
key, the $"salt"$, that lives only on Phil's machine, cut to sixteen hex characters. The same player
always gets the same hashed value, so checks that follow a player still work, but without
the salt nobody can tell which player it is. Solo runs use the player id one and keep it.

#mathfull[
  *Why a plain hash is not enough for a Steam ID.* A hash function can't be run backwards, but
  it can be run forwards on every candidate. Steam IDs are numbers in a known, limited range,
  so an attacker could hash every plausible ID and look up which one gives the stored value
  (a dictionary attack). A keyed hash mixes the secret salt into every evaluation; without it
  the forward computation can't be done, so the dictionary can't be built. The run key, by
  contrast, is a plain hash: it is built from game fields (seed, start time, characters,
  ascension), not from anything that identifies a person.

  *How likely is a collision?* Cutting a hash to $L$ bits (here $L$ is sixty-four: sixteen hex
  characters of four bits each) means two different runs could share a key by chance. For $N$
  runs and a well-mixed hash, the chance that any two collide is about
  $ P("collision") approx N^2 / 2^(L + 1) $
  In words: the chance of any shared key grows with the square of the number of runs and
  halves with every extra bit, because there are about $N^2 slash 2$ pairs of runs and each
  pair collides with probability $2^(-L)$. With sixty-four bits and a snapshot of a few million records, that is vanishingly small. The
  real risk to the run key was never chance: in early versions of the parser the key was only
  seed and start time, and different runs that shared both were merged. Adding the characters and ascension
  split them.
]

#incode("runs.keys", [The run key and the two identifier hashes, as the parser computes
  them.])[
  *What goes in:* a record's fields, and for the player hash the secret key. *What comes out:*
  sixteen hex characters. The lines that matter: `hmac.new(key, ..., hashlib.sha256)` is
  @eq-player-hash, and the slice at the end of the line keeps the first sixteen characters. `player_hash` leaves the solo player id one as it is,
  because it is the same placeholder in every solo record. In `run_key`,
  `sorted(str(c) for c in characters)` is the $"sort"("chars"_r)$ of @eq-run-key, and the
  plain `hashlib.sha256` (no key) is enough because nothing in it identifies a person.
]

#incode("runs.dedup_views", [Retried runs and the deduplicated views, in SQL inside the
  parser's source.])[
  *What goes in:* the `runs` and `card_offers` tables, one row per record. *What comes out:*
  `runs_dedup` (one record per run key) and `primary_offers` (the offers the analysis uses).
  The lines that matter: `RETRIED_SQL` is @eq-retried, written as "the smallest and largest
  value of each ending field over the key's copies differ" (`OVER k` is the window of one run
  key). In `runs_dedup`, `row_number() OVER w ... WHERE rn = 1` keeps the first copy by page
  and line. `primary_offers` joins offers to `runs_dedup`, so a run uploaded twice
  contributes its offers once, and applies the population filter of the next section.
]

#project[
  *Your data.* Of #n("dedup.records_read") records read, #n("dedup.exact_repeats_dropped")
  were exact repeats from the re-downloaded pages and were dropped. Among solo runs,
  #n("dedup.solo_run_keys_multi_record") run keys have more than one record, and
  #n("dedup.solo_run_keys_retried") of those copies disagree on how the run ended
  (#n("dedup.primary_run_keys_retried") in the primary population). Deduplicating by run key
  removed #n("dedup.primary_offers_dedup_removed") offer rows. Counting each run once across
  builds gives #n("snapshot.distinct_runs") distinct runs; the download script's own total,
  #n("snapshot.distinct_runs_per_build_sum"), counts the #n("snapshot.runs_in_several_builds")
  runs recorded under two build ids twice.
]

#watch[
  "Keep the best copy" sounds harmless and is not. Whenever copies of a record differ in the
  outcome, choosing one by its outcome builds a bias into the data before any analysis runs.
]

#skill[
  *Deduplicating with a stated rule.* Define what makes two records the same unit, count how
  many collapse, and decide separately what to do when copies disagree.
]

#check(
  ([What is the difference between a duplicate record and a retried run?],
   [A duplicate is the same run uploaded twice with the same content (or the same ending). A
    retried run has copies with different endings, most likely from a restored save.]),
  ([Why are retried runs fine for pick rates but dropped from win analyses?],
   [Their copies share the early reward screens, so one copy gives the right picks. But they
    have different endings, and keeping any one copy by its ending (or the most complete
    one) would favour the attempt that went better.]),
  ([Why does the run key sort the characters before hashing?],
   [Co-op copies of one run can list the same players in different orders. Sorting gives
    every copy the same input, so they get the same key.]),
  ([Why are Steam IDs hashed with a secret key rather than a plain hash?],
   [Steam IDs come from a limited, known range, so anyone could hash every candidate and look
    the stored value up. With a secret key mixed in, that forward computation is impossible
    without the key.]),
  ([Two counts of distinct runs differ slightly. Why?],
   [The audit counts each run once over all builds. The download script counts distinct runs
    within each build and sums, so runs recorded under two build ids are counted twice.]),
)

== The primary population

#picture[
  A study has a guest list. Before the party you decide who counts as a guest, write the
  rule down, and apply it to everyone the same way. You don't decide after seeing who
  danced.
]

#words[
  - *Sample and population*: the runs you have, and all the runs the question is about. You
    use the first to learn about the second.
  - *Primary population*: the runs the main analysis uses, defined by fixed filters.
]

The primary population is: solo runs (co-op runs mix several players' choices); no custom
modifiers; no sign of mods (a mod card, character, act, enchantment, event or encounter, or a
mod save key); a released build; a start date on or after that build's release date (an
earlier start means the run began on an older build); and a run that starts at the Neow
event, as the standard game does. Abandoned runs stay in for pick rates (their choices are
real choices) and leave the win analyses. Possible cheats (very fast wins) are flagged, not
filtered.

The same rule as a predicate, one test per condition. For a run $r$ on build $B(r)$:

$ cal(P) = {r : "solo"(r) and not "custom"(r) and not "modded"(r) and "released"(B(r))
  and "start"_r >= "release"(B(r)) and "neow"(r)} $ <eq-primary>

In words: the primary population is the set of runs that are solo, have no custom modifiers,
carry no mod marker, were played on a released build, started on or after that build's
release date and began at Neow. The offers the pick-rate analysis uses are then

$ cal(O) = {i : r(i) in cal(P)_"dedup" and "source"(i) in cal(S) and not "modcard"(i)} $ <eq-offers>

In words: an offer counts if its run is in the deduplicated primary population, it came from
one of the card-reward sources $cal(S)$ (normal fights, elites, bosses and fights that start
from an event), and its card is not a mod's card.

#incode("runs.primary_filter", [@eq-primary and @eq-offers as the parser writes them, in
  SQL.])[
  *What goes in:* nothing at run time: these are strings that the views of the previous
  section paste into their `WHERE` clauses. The lines that matter: each `AND` of
  `PRIMARY_RUN_FILTER` is one condition of @eq-primary (`r.n_players = 1` is solo,
  `NOT r.before_release` is the start-date rule, `r.neow_start` the Neow rule).
  `PRIMARY_FILTER` adds the two offer conditions of @eq-offers; `COMBAT_SOURCES` is
  $cal(S)$, defined at the top of the module. Keeping the rule in one string means the
  pick-rate tables and the win analyses can't drift apart: the win analyses start from the
  same run-level part.
]

#project[
  *Your data.* The primary population is #n("audit.primary_runs") runs,
  #n("audit.primary_share") of distinct runs. Solo runs alone are #n("audit.solo_runs")
  (#n("audit.solo_share")). Runs started before their build's release:
  #n("audit.before_release_runs") (#n("audit.before_release_share")). Not abandoned (the win
  population): #n("audit.primary_finished") (#n("audit.primary_finished_share") of distinct
  runs). Of #n("audit.primary_wins") primary wins, #n("audit.fast_wins") took under a quarter
  of an hour; they stay in, flagged. Two wins that looked impossible on an earlier audit
  (a huge gold total, an empty deck) were #unverified[not rechecked on the final tables].
]

#watch[
  Filters chosen after looking at results are a way to find whatever you want. Every filter
  here was decided during the data audit, before any pick-rate model was fitted, and written
  into SPIROMETRY.md.
]

#skill[
  *Defining the population before the analysis.* Say who is in, who is out and why, in a
  form a program can apply. Then report how many records each rule removes.
]

#check(
  ([List four filters that define the primary population.],
   [Any four of: solo runs; no custom modifiers; no mod markers; a released build; started on
    or after the build's release date; starts at Neow.]),
  ([In @eq-primary, which condition removes a run that began on an older build and was
    finished on the new one?],
   [$"start"_r >= "release"(B(r))$: a run that started before its build's release date began
    on an older build.]),
  ([Why do abandoned runs stay in for pick rates but leave the win analyses?],
   [A pick made in an abandoned run is still a real choice about an offer. But an abandoned
    run has no honest win or loss, so it can't be an outcome for winning.]),
  ([What would go wrong if a run that started on the old build and finished on the new one
    were kept?],
   [Its early floors may have been played with the old card versions, so it would mix the
    two versions inside one "after" run.]),
)

== Thin builds

#picture[
  A shop that opens for one day has too few customers to say much about its prices on its
  own. If its prices were the same as the shop next door's, you can count the two together.
  If they were different, you leave the one-day shop out.
]

#words[
  - *Thin build*: a build with too few primary runs to stand alone in a comparison.
  - *Pooling*: counting a thin build together with its neighbour on the same branch, allowed
    only when no card change falls between them.
]

Stated precisely. Let $N(B)$ be the number of primary runs on build $B$ and $N_"min"$ the
threshold. A build is thin when

$ "thin"(B) <==> N(B) < N_"min", quad N_"min" = #n("audit.min_runs") $ <eq-thin>

In words: a build is thin when it has fewer primary runs than the threshold. A thin build $B$
may be pooled with a neighbour $B'$ only when

$ "pool"(B, B') <==> "thin"(B) and "branch"(B) = "branch"(B') and "adjacent"(B, B')
  and Delta_"cards"(B, B') = emptyset $ <eq-pool>

In words: pooling needs a thin build, a neighbour on the same branch, and an empty set of card
changes between the two ($Delta_"cards"$, read from the card-change tables). If any condition
fails, the thin build stands alone or is left out.

#project[
  *Your data.* The working threshold is #n("audit.min_runs") primary runs, chosen by hand
  rather than from a power calculation (it changes no result, because the windows are fixed).
  The builds below it (#n("audit.thin_builds")) are #n("audit.thin_builds_list"). v0.103.1
  (#n("audit.thin_primary_0_103_1") primary runs) pools with v0.103.0. v0.99.0
  (#n("audit.thin_primary_0_99_0") runs) is left out: its neighbour v0.99.1 is on another
  branch. v0.110.0 (#n("audit.thin_primary_0_110_0") runs) would pool with v0.110.1 by the
  rule; that call is #unverified[not checked against the patch notes], and both builds come
  after the last stable window, so it only matters for designs that use beta builds.
]

#mixup[
  You might read "that call is not checked against the patch notes" as a doubt about the
  results. It isn't one. Two sources say whether a card changed between builds: the card-change
  tables built from the game data (the project's own record, compared field by field) and the
  official patch notes (the developers' announcement). The pooling rule, @eq-pool, reads only
  the first. For the earlier builds the two were cross-checked; for v0.110.0 and v0.110.1 they
  haven't been. That matters only for a design that uses those builds, and none of the results
  in this guide does: the two windows were fixed in advance and contain no thin build.
]

#mixup[
  You might call v0.103.3, the second patch's before block, a thin build because it is the
  smaller side of that window. It isn't: it holds #n("audit.offers_0_103_3") offers, against
  #n("audit.offers_0_103_2") on v0.103.2, so it is about half the size of the other before
  blocks, far above the threshold. The accurate description is a *short, smaller* before
  block: about three weeks live. It still limits precision, for two reasons @ch-noise makes
  exact: what counts for one card's estimate is that card's offers, a small slice of the
  build's total, and the error of a before-and-after difference is dominated by its smaller
  side.
]

#watch[
  Pooling two builds assumes they are the same treatment. If a card changed between them,
  the pooled block mixes two versions and the comparison is blurred. That is why the rule
  checks every card-change table before pooling. And "no card changed" is necessary, not
  sufficient: @ch-checks shows that pick rates can drift between two builds with identical
  cards.
]

#skill[
  *Setting a minimum sample size, and saying how it was set.* A threshold chosen by hand is
  fine if it is labelled as such and shown not to drive the results.
]

#check(
  ([When may a thin build be pooled with its neighbour?],
   [When it is on the same branch and no card change falls between the two builds.]),
  ([Why is v0.99.0 left out rather than pooled?],
   [Its neighbour v0.99.1 was released on the stable branch while v0.99.0 was a beta, so
    pooling would cross branches.]),
  ([If v0.110.1 had buffed one card, what would go wrong if v0.110.0 and v0.110.1 were
    pooled anyway?],
   [The pooled block would mix two versions of that card, so any comparison using it would
    blur the old and new versions together. @eq-pool forbids it, because
    $Delta_"cards"$ would not be empty.]),
  ([Is v0.103.3 a thin build? How should you describe it?],
   [No: it has millions of offers, far above the threshold. It is a short, smaller before
    block, about half the size of the others and about three weeks long.]),
  ([What does "not checked against the patch notes" mean for v0.110.0?],
   [The pooling call used only the card-change tables; the official notes for v0.110.1 were
    not read to confirm no card changed. It affects only designs that use those builds.]),
  ([The threshold for a thin build was chosen by hand. Why does that not threaten the
    results?],
   [The patch windows are fixed builds, and none of them depends on the threshold. Changing
    it would change which beta builds stand alone, not any estimate in the guide.]),
)
