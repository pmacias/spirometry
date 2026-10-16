#import "../style.typ": *

= Is it the measuring stick? Rulers and doses <ch-rulers>

#lead[Whether the second patch looks flat only because of how the size of a change was
  measured.]

A dose-response line has two axes, and either can mislead. @ch-placebo tested the vertical
one (the error bars on the effects). This chapter tests the horizontal one: the dose. If a
different, equally reasonable way of measuring "how big was this change" made the second
patch look like the first, the puzzle would be about measurement, not about players.

== Many rulers and a post-hoc one

#picture[
  Measure the rooms of a house in metres, in footsteps, or by ranking them from smallest to
  largest. If "the kitchen is bigger than the bathroom" holds on every method, it is about
  the rooms. If it holds only in footsteps, it may be about your feet.
]

#words[
  - *Sign ruler*: only the direction counts (a buff counts plus one, a nerf minus one). It ignores size entirely.
  - *Absolute ruler*: new minus old, in the card's own units (three more damage).
  - *Rank ruler*: tweaks ranked by their ln dose, so only the order matters.
  - *Per-kind rulers*: doses divided by the typical dose for that kind of number (damage,
    block, power amount), so kinds are comparable.
  - *Post hoc*: chosen after seeing the results. A post-hoc ruler can be tuned, knowingly or
    not, to tell a story, so it is marked and given less weight.
]

#ftable(
  columns: (auto, auto, auto, auto),
  [*Ruler (primary spec, weeks 0–3)*], [*First slope*], [*Second slope*], [*z diff*],
  [ln(new/old), primary], [#n("rulers.primary.ln.slope_first_pm")], [#n("rulers.primary.ln.slope_second_pm")], [#n("rulers.primary.ln.z_diff")],
  [ln dose, effect in points], [#n("rulers.primary.pp_ln.slope_first_pm")], [#n("rulers.primary.pp_ln.slope_second_pm")], [#n("rulers.primary.pp_ln.z_diff")],
  [Percent change], [#n("rulers.primary.percent.slope_first_pm")], [#n("rulers.primary.percent.slope_second_pm")], [#n("rulers.primary.percent.z_diff")],
  [Mean of base and upgraded ln], [#n("rulers.primary.base_upgraded.slope_first_pm")], [#n("rulers.primary.base_upgraded.slope_second_pm")], [#n("rulers.primary.base_upgraded.z_diff")],
  [Rank], [#n("rulers.primary.rank.slope_first_pm")], [#n("rulers.primary.rank.slope_second_pm")], [#n("rulers.primary.rank.z_diff")],
  [Sign only], [#n("rulers.primary.sign.slope_first_pm")], [#n("rulers.primary.sign.slope_second_pm")], [#n("rulers.primary.sign.z_diff")],
  [ln, per kind], [#n("rulers.primary.ln_kind.slope_first_pm")], [#n("rulers.primary.ln_kind.slope_second_pm")], [#n("rulers.primary.ln_kind.z_diff")],
  [Absolute, per kind], [#n("rulers.primary.absolute_kind.slope_first_pm")], [#n("rulers.primary.absolute_kind.slope_second_pm")], [#n("rulers.primary.absolute_kind.z_diff")],
  [Absolute (new − old)], [#n("rulers.primary.absolute.slope_first_pm")], [#n("rulers.primary.absolute.slope_second_pm")], [#n("rulers.primary.absolute.z_diff")],
  [Hybrid (post hoc)], [#n("rulers.primary.hybrid.slope_first_pm")], [#n("rulers.primary.hybrid.slope_second_pm")], [#n("rulers.primary.hybrid.z_diff")],
)

#project[
  *Your data.* The slopes are in different units on different rulers, so compare the z diff
  column. On every ruler that preserves proportions (ln, percent, the ln of base and
  upgraded, rank, sign) the patches differ by about three SEs or more. On the per-kind rulers
  the difference shrinks to around two, and on the absolute ruler it disappears
  (#n("rulers.primary.absolute.z_diff")). The absolute ruler treats three more damage on a
  fifty-damage card the same as three more on a six-damage card, which is hard to defend for
  picks, and its first-patch slope is itself weak. The hybrid ruler (absolute for damage and
  block, ln for everything else) was proposed after the results were known; it gives
  #n("rulers.primary.hybrid.z_diff") and is marked post hoc.
]

#fig("fig_rulers", [Patch difference (z diff) by ruler and by which tweaks are on the line.
  The hybrid ruler is post hoc.])

#watch[
  A ruler chosen after seeing the results is not evidence for or against anything; it is a
  hypothesis for the next patch. That is why ln(new/old) was fixed as the primary ruler and
  the others are reported as a table, not picked from.
]

#skill[
  *Checking whether a conclusion depends on how you measured.* Re-run the key comparison on
  every defensible measurement, report them all, and mark the ones chosen after looking.
]

#check(
  ([On which rulers does the patch difference hold, and on which does it shrink or vanish?],
   [It holds (about three SEs or more) on the proportional rulers: ln, percent, the base and
    upgraded ln, rank and sign. It shrinks on the per-kind rulers and vanishes on the
    absolute ruler.]),
  ([Why is the absolute ruler a weak test for pick rates?],
   [It treats the same number of extra points as the same change whatever the card's size,
    although three more damage matters much more on a small card than on a large one.]),
  ([What does "post hoc" mean, and why is the hybrid ruler marked that way?],
   [Chosen after seeing the results. The hybrid ruler was proposed after notebook 04’s
    results were known, so it could fit the data by construction.]),
)

== Mixed tweaks

#words[
  - *Mixed tweak* (the dose rule's sense): a tweak whose card's total printed output moves in
    different directions for the base and upgraded card, or whose changed numbers in
    different units move opposite ways. Its direction is the patch-note label; its dose is
    ln(new total / old total) for the un-upgraded card, counting generated cards at their
    printed values. A dose of zero or of the wrong sign keeps it off the line.
]

The rule was written down from the card texts without looking at effects, and adopted in
October 2026. It settles the two tweaks that the export flags as mixed. Leading Strike (less
damage, one more Shiv; patch notes "buffed") totals the same damage before and after, so its
dose is zero: off the ln line, on the sign ruler as a buff. Reflect (less block on both the
base and the upgraded card) is not mixed under the rule: on the line as a nerf.

#project[
  *Your data.* Other ways of handling the two give the same picture on the ln ruler. Both off
  (the notebooks' set): z diff #n("mixed.ln.both_off.z_diff"). Leading Strike at its damage
  equivalent with Strength from zero to three: between #n("mixed.ln.leading_strike_damage_equivalent_s_0.z_diff")
  and #n("mixed.ln.leading_strike_damage_equivalent_s_3.z_diff"). Reflect on at its base block:
  #n("mixed.ln.reflect_base_block.z_diff"). Only one variant breaks it: Leading Strike at its
  naive main-field dose (damage only, a big nerf), #n("mixed.ln.leading_strike_naive_main_field.z_diff"),
  which treats a card the patch notes called a buff, and players picked far more, as the
  largest nerf in the patch.
]

#watch[
  Measuring a tweak by one field when the card changed in several is the most common way a
  dose goes wrong. Leading Strike's naive dose is a large nerf; its real change was close to
  neutral in damage and players read it as a buff.
]

#skill[
  *Writing a measurement rule before applying it.* For hard cases, write the rule from the
  definitions (here, the card text), apply it mechanically, and show what the alternatives
  would have given.
]

#check(
  ([Why is Leading Strike off the ln line?],
   [Under the mixed-tweak rule its total printed damage is the same before and after (less
    damage, one more Shiv), so its dose is zero; it enters only the sign ruler, as a buff.]),
  ([Which single variant removes the patch difference, and why is it not credible?],
   [Leading Strike at its naive main-field dose. It counts a card the notes called a buff, and
    that players picked far more, as a large nerf.]),
  ([Why was the mixed-tweak rule written from the card text without looking at the effects?],
   [So that the rule can't be tuned to produce a preferred answer.]),
)

== Hard-to-measure doses: Debilitate and Reflect

#words[
  - *Measurement error in the dose*: if doses are measured with noise, the fitted slope is
    pulled toward zero (*attenuation*). A blurry ruler makes any relation look flatter.
]

Debilitate's second-patch nerf shortened a debuff by one turn. How much that weakens the card
depends on the deck, the length of fights and other sources of the same debuffs: there is no
single size. The decision (October 2026) was to keep it off the ln line, on the sign ruler as
a nerf, and to show the line with it at its table dose as a sensitivity row.

#project[
  *Your data.* The choices about Debilitate and Reflect move the second slope more than
  anything else on the ln ruler. Primary (Reflect on, Debilitate off): z diff
  #n("rulers.primary.ln.z_diff"). Debilitate added at its table dose:
  #n("rulers.primary_debilitate_table_dose.ln.z_diff"), with the second slope
  #n("rulers.primary_debilitate_table_dose.ln.slope_second_pm"). Both off: second slope
  #n("rulers.reflect_off_debilitate_off.ln.slope_second_pm"), z diff
  #n("rulers.reflect_off_debilitate_off.ln.z_diff"). Each of these two nerfs was followed by
  slightly more picks, so each one on the line flattens the second patch further.
]

#plain[
  Partial-coverage doses (a change whose effect depends on the game state, like a debuff
  length) are more common among the second patch's tweaks. Measurement error points the right
  way to explain part of the flatness. Whether it does is #unverified[open]: there is no
  better measurement of those doses to test it with.
]

#watch[
  "These are judgement calls" is not a weakness to hide. State each call, its reason, and
  what the result is under the other choice. Here the range is z diff
  #n("rulers.reflect_off_debilitate_off.ln.z_diff") to
  #n("rulers.primary_debilitate_table_dose.ln.z_diff"), and the primary sits between.
]

#skill[
  *Treating uncertain inputs as part of the uncertainty.* When an input can't be measured,
  say so, keep it out of the main estimate, and show the estimate with it in.
]

#check(
  ([Why can't Debilitate's second-patch nerf be given a size?],
   [A shorter debuff weakens the card by an amount that depends on the deck, fight length and
    other sources of the same debuffs; there is no single number.]),
  ([Which way does measurement error in the doses push a slope?],
   [Toward zero: noise in the dose blurs the relation and flattens the fitted line.]),
  ([What range of patch differences do the Debilitate and Reflect calls span on the ln
    ruler?],
   [From #n("rulers.reflect_off_debilitate_off.ln.z_diff") (both off) to
    #n("rulers.primary_debilitate_table_dose.ln.z_diff") (both on), with the primary spec at
    #n("rulers.primary.ln.z_diff").]),
)

== Leave one out

#words[
  - *Leave-one-out*: refit without each point in turn, and see how far the answer moves.
  - *Influential point*: a point whose removal moves the answer a lot.
]

#picture[
  A jury's verdict should not change when one juror goes home. If it does, the verdict rests
  on that juror, and you want to know what they said.
]

#project[
  *Your data.* Under the primary spec the most influential second-patch tweak is Patter's
  nerf. Without it the second slope moves by #n("leave_out.primary.max_abs_d_slope_second_se")
  of its SEs, to #n("leave_out.primary.patter.v0_107_1.slope_second_pm") (z diff
  #n("leave_out.primary.patter.v0_107_1.z_diff")): no single tweak makes the second patch
  flat. Leaving out a whole character is a bigger test. Without Regent's cards (the character
  with the most tweaks on the line), the second slope is #n("leave_out.primary.regent.slope_second_pm")
  and the z diff falls to #n("leave_out.primary.regent.z_diff"), mostly because the second
  slope's SE doubles. Without Necrobinder's: #n("leave_out.primary.necrobinder.z_diff").
  Without Silent's, the first slope rises to #n("leave_out.primary.silent.slope_first_pm").
]

#fig("fig_leave_out", [The second patch's slope with each tweak left out, primary spec.])

#plain[
  Giving each character its own intercept (so the line is estimated from differences within a
  character) gives a first slope of #n("character.primary.character_intercepts.slope_first_pm")
  and a z diff of #n("character.primary.character_intercepts.z_diff")\; with a separate intercept
  per character and patch, #n("character.primary.character_x_patch_intercepts.z_diff"). Part
  of the first patch's slope is a contrast between characters (one character's cards were
  mostly nerfed and fell, another's mostly buffed and rose), which intercepts absorb together
  with real dose variation, because there the two are tangled. Within Regent alone, the first
  slope is #n("character.primary.within.regent.first.slope_pm") on
  #n("character.primary.within.regent.first.n") tweaks and the second
  #n("character.primary.within.regent.second.slope_pm") on
  #n("character.primary.within.regent.second.n").
]

#watch[
  Fourteen points can't carry many splits. Every extra term (a character intercept, a
  character left out) costs precision, and a z diff that falls because its SE grew is not the
  same as one that falls because the slopes converged.
]

#skill[
  *Finding the points a result rests on.* Refit without each point and each group. Report the
  largest moves, and say whether they came from the estimate shifting or from its error
  growing.
]

#check(
  ([Which second-patch tweak is most influential, and does removing it make the second
    patch steep?],
   [Patter's nerf. No: removing it moves the second slope by well under one SE and the
    difference remains.]),
  ([Leaving out Regent's cards shrinks the z diff. Why is that weaker evidence against the
    result than it looks?],
   [Mostly the second slope's SE grows (fewer points), rather than the two slopes moving
    together.]),
  ([Why can character intercepts reduce the first patch's slope even if the dose effect is
    real?],
   [In the first patch the dose and the character are tangled: one character's cards were
    mostly nerfed and another's buffed. Intercepts absorb that between-character contrast
    along with part of the real dose effect.]),
)

== The review calls

Your own review of the card texts made three calls that a strict table can't: Grand
Finale off the line, Crescent Spear at a corrected dose (its effective damage rather than its
listed number), and Debilitate's second-patch nerf off (as above). The decision of October
2026 keeps them as a sensitivity variant, not the primary spec.

#project[
  *Your data.* With all the review calls: z diff #n("review.primary.review_calls.ln.z_diff").
  One call at a time: Grand Finale off #n("review.primary.one_call_grand_finale_off.ln.z_diff"),
  Crescent Spear corrected #n("review.primary.one_call_crescent_spear_at_ln_10_8.ln.z_diff").
  Under the review calls the absolute ruler gives #n("review.primary.review_calls.absolute.z_diff")
  and the hybrid #n("review.primary.review_calls.hybrid.z_diff"): Grand Finale's change (from
  #n("tweak.grand_finale.v0_103_2.old") to #n("tweak.grand_finale.v0_103_2.new") damage) is by
  far the largest in absolute terms, and without it the absolute ruler starts to see the first
  patch's slope.
]

#watch[
  An analyst's judgement about inputs is legitimate if it is made before seeing how it moves
  the result, written down with its reason, and shown as a variant beside the rule-based
  version.
]

#skill[
  *Separating rules from judgement.* Keep a mechanical primary spec, record expert calls as a
  named variant, and show both.
]

#check(
  ([What are the three review calls?],
   [Grand Finale off the line, Crescent Spear at a corrected dose (its effective damage),
    Debilitate's second-patch nerf off the line.]),
  ([Do the review calls change the conclusion on the ln ruler?],
   [No: the patch difference stays at about three SEs.]),
  ([Why are the review calls a variant rather than the primary spec?],
   [They are judgement about individual cards; the primary spec is a rule applied
    mechanically, and judgement is shown beside it so readers can see how much it matters.]),
)
