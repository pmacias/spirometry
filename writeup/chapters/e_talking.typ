#import "../style.typ": *

= Talking about it <app-talking>

How to explain the project out loud: a version for one minute, one for five, and the
questions an interviewer is most likely to ask. Every number is the same one the chapters
use; say fewer of them rather than different ones.

== The sixty-second version

I studied what balance patches in Slay the Spire 2 did to players' choices. Players upload
logs of their games, and each log records every card the game offered and whether the player
took it, so every patch is a natural experiment. I built the pipeline from
#n("snapshot.records") uploaded run records, cleaned it down to #n("audit.primary_runs") solo runs,
and measured, for #n("tweaks.solo_estimable") cards whose numbers changed, how their pick rate
moved compared with unchanged cards of the same character (a difference-in-differences). In
the first patch, picks moved the way the change pointed and in proportion to its size. In the
second, with changes of the same sizes, picks barely moved, about as much as in a comparison
where nothing changed. Along the way I found that the model's error bars were several times
too small, measured by how often it finds "effects" on cards that didn't change, and I
corrected the counts for that. Why the second patch did less is still open.

== The five-minute version

*The question.* A game patch changes card numbers: more damage here, less block there. Did
players respond, and in proportion? The game decides at random which cards to offer after a
fight, and the uploaded logs record every offer and pick, so the pick rate of each card is
measurable before and after each patch.

*The data.* #n("snapshot.pages") pages of a public export, #n("snapshot.records") records. I
removed re-downloaded pages and duplicate uploads, dropped co-op, modded and custom runs and
runs from before their build's release, and kept #n("audit.primary_runs") solo runs. Two
things in the data shaped the design: players upload in bulk, months late, so recent weeks are
thin; and players who upload through a stats mod differ from the rest (they win
#n("audit.win_rate_v0_103_2_tagged_pct") against #n("audit.win_rate_v0_103_2_untagged_pct")
and rank cards differently), so every estimate keeps the two groups apart.

*The method.* For each changed card I compared its pick rate before and after the patch with
the same change for the same character's unchanged cards, which removes whatever moved the
whole game between builds. The model is a regression with a baseline for each card, block,
uploader group, act and ascension, and errors clustered by run. I checked offer rates, trends
before the patch, reactions to the beta notes, placebos built into upgrade-only changes, and
a table of robustness checks.

*The surprise.* I ran the same method on cards that didn't change. With honest error bars,
#n("const.honest.share_abs_z_gt2") should look "clearly nonzero"; #n("placebo.pairs.all.share_abs_z_gt2")
did. So I rescaled each patch's errors by that placebo spread and lead with the corrected
counts.

*The result.* First patch: #n("did.h3.first.calibrated.clearly_nonzero") of
#n("tweaks.first") tweaks moved picks clearly, all those with a direction toward the change, and the
slope of effect against change size was #n("dose.primary.h3.slope_first_pm"). Second patch:
#n("did.h3.second.calibrated.clearly_nonzero") of #n("tweaks.second"), slope
#n("dose.primary.h3.slope_second_pm"). The difference has a z of #n("dose.primary.h3.z_diff") and
survives the corrected errors, other control groups, each uploader group and a subset of
identified players. It weakens on some ways of measuring change size and leans on a few cards.
A simulation shows a first-patch-sized response would have been detected, and a fake patch
with no changes looks just like the real second patch.

*What's next.* Fix the cause of the too-small error bars, pool the per-card estimates, and run
the win-effect design (the random offer as an instrument for taking a card), which is built
and tested in simulation but not run on real data.

== Ten questions you are likely to be asked

#qa[What was the question?][
  What balance patches did to players' card choices: after a patch, was a changed card picked
  more or less often when offered, and did bigger changes move picks more? The second half,
  whether taking a card helps you win, has a design and tooling but no real-data results.
]

#qa[Why not just compare pick rates before and after the patch?][
  Everything else changes between builds too: players improve, strategies spread, the mix of
  uploaders shifts. Comparing each changed card with unchanged cards of the same character,
  over the same builds, removes what they share. For Corrosive Wave the plain before-and-after
  drop was #n("tweak.corrosive_wave.v0_103_2.treated_change_pp") points; net of its controls it
  was #n("tweak.corrosive_wave.v0_103_2.did_raw_pp").
]

#qa[How do you know the comparison is fair?][
  I can't prove the key assumption (that the changed card would have moved like its controls),
  but I checked what it implies: the patch didn't change how often cards were offered (with two
  exceptions, flagged), most cards weren't drifting before the patch, upgrade-only changes show
  little effect on un-upgraded copies, players mostly didn't react to the beta notes early, and
  the estimates barely move when I drop heavy uploaders, shared screens or flagged controls.
]

#qa[How did you handle uncertainty?][
  Clustered standard errors by run, then a placebo test of those errors: the same model on
  unchanged cards. The errors were too small by a factor of about
  #n("did.h3.first.calibrated.factor") in the first patch and
  #n("did.h3.second.calibrated.factor") in the second, so I divide each z by that factor
  before calling anything clearly nonzero, and I show both counts.
]

#qa[What's the main result?][
  The first patch moved picks in the direction of each change and in proportion to its size;
  the second, with changes of the same sizes, barely moved them. The slopes are
  #n("dose.primary.h3.slope_first_pm") and #n("dose.primary.h3.slope_second_pm") log-odds per
  unit of log change; their difference has a z of #n("dose.primary.h3.z_diff").
]

#qa[Couldn't the second patch just be underpowered?][
  A simulation that plants a first-patch-sized slope in data like the second patch's detects it
  #n("power.primary.honest.planted_1_44.power_slope_second") of the time. A slope half that size
  would be detected only #n("power.primary.honest.planted_0_7.power_slope_second") of the time,
  so the honest claim is "much less than the first patch", not "zero".
]

#qa[What is the weakest part of the analysis?][
  Three things. The error bars needed a correction whose cause I haven't verified. The patch
  difference depends on how change size is measured: on raw differences (three more damage
  counts the same on any card) it disappears. And it leans on a few cards: dropping one
  character's cards or changing the call on two hard-to-measure changes moves its z between
  #n("leave_out.primary.regent.z_diff") and #n("rulers.primary_debilitate_table_dose.ln.z_diff").
]

#qa[Why does the second patch look different?][
  I don't know. I ruled out low power, a drifting comparison build (a fake patch looks the
  same), a bounce-back in the first patch, the choice of control cards, and a change in who
  uploads (every subgroup shows it, including players who never used the stats mod). What's
  left: a settled meta and more experienced players by June, the kinds of numbers the second
  patch changed, and noise in measuring those changes.
]

#qa[What would you do differently?][
  Test the error bars with placebos from the start, not after the first results, and build the
  model so that each card's popularity can drift week to week, which is the likely cause of
  the too-small errors. Fix the rules for measuring change sizes before looking at any
  effects; most were, but a few calls came later and are reported as sensitivity variants.
  And run the win-effect power check early, so the second question gets a yes or no.
]

#qa[What would you do next?][
  Model the card-level drift and redo the placebo calibration with it; pool the per-card
  estimates so rarely offered cards don't get extreme values; run the win-effect power check
  and, if it passes, estimate whether patched cards became stronger and whether players'
  reactions matched. The beta branch, which gets changes weeks earlier, offers a second
  experiment for every patch.
]
