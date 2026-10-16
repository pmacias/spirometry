#import "../style.typ": *

= Your numbers on one page <app-numbers>

A study aid: the numbers worth knowing by heart, each from the final rerun (weeks 0–3 and the
primary spec unless the row says otherwise).

#small-table(
  columns: (rest, auto, auto),
  [*What*], [*Number*], [*Where*],
  [Export pages; run records], [#n("snapshot.pages")\; #n("snapshot.records")], [@ch-data],
  [Distinct runs; primary runs], [#n("snapshot.distinct_runs")\; #n("audit.primary_runs") (#n("audit.primary_share"))], [@ch-data],
  [Play dates], [#n("snapshot.start_date") to #n("snapshot.end_date")], [@ch-data],
  [Median upload lag (all; tagged; untagged), days], [#n("audit.lag_median_days")\; #n("audit.lag_median_days_tagged")\; #n("audit.lag_median_days_untagged")], [@ch-data],
  [Numeric tweaks; solo-estimable; first and second patch], [#n("tweaks.numeric")\; #n("tweaks.solo_estimable")\; #n("tweaks.first") and #n("tweaks.second")], [@ch-project],
  [Tagged against untagged win rate, v0.103.2], [#n("audit.win_rate_v0_103_2_tagged_pct") against #n("audit.win_rate_v0_103_2_untagged_pct")], [@ch-confounding],
  [Parry: pick rate before → after], [#n("tweak.parry.v0_103_2.treated_rate_before") → #n("tweak.parry.v0_103_2.treated_rate_after")], [@ch-counting],
  [Parry: DiD by hand; model], [#n("tweak.parry.v0_103_2.did_raw_pp")\; #n("tweak.parry.v0_103_2.h3.beta_pp_pm") points], [@ch-did],
  [Corrosive Wave: model], [#n("tweak.corrosive_wave.v0_103_2.h3.beta_pp_pm") points], [@ch-results],
  [Clustered ÷ robust SE, median (range)], [#n("se.clustered_over_robust.median") (#n("se.clustered_over_robust.min") to #n("se.clustered_over_robust.max"))], [@ch-regression],
  [Offer-rate flags (all controls; own rarity)], [#n("flags.offer_rate.all.n_flagged")\; #n("flags.offer_rate.all.n_flagged_rarity")], [@ch-checks],
  [Anticipation: informative tweaks; median ratio to main], [#n("anticipation.all.n_informative") of #n("anticipation.all.n_tweaks")\; #n("anticipation.all.median_ratio_to_main")], [@ch-checks],
  [Placebo: share beyond two SEs (honest: #n("const.honest.share_abs_z_gt2"))], [#n("placebo.pairs.all.share_abs_z_gt2")], [@ch-placebo],
  [Calibration factors, first; second], [#n("did.h3.first.calibrated.factor")\; #n("did.h3.second.calibrated.factor")], [@ch-placebo],
  [Clearly nonzero, calibrated: first; second], [#n("did.h3.first.calibrated.clearly_nonzero") of #n("tweaks.first")\; #n("did.h3.second.calibrated.clearly_nonzero") of #n("tweaks.second")], [@ch-results],
  [Clearly nonzero, uncalibrated: first; second], [#n("did.h3.first.uncalibrated.clearly_nonzero")\; #n("did.h3.second.uncalibrated.clearly_nonzero")], [@ch-noise],
  [Median effect size, points: first; second], [#n("did.h3.first.median_abs_beta_pp")\; #n("did.h3.second.median_abs_beta_pp")], [@ch-results],
  [One shared slope (notebooks' set); intercept; τ], [#n("dose.triage.h3.one_slope.slope_pm")\; #n("dose.triage.h3.one_slope.intercept_pm")\; #n("dose.triage.h3.one_slope.tau")], [@ch-dose],
  [Slope, first patch; second patch], [#n("dose.primary.h3.slope_first_pm")\; #n("dose.primary.h3.slope_second_pm")], [@ch-dose],
  [Patch difference z: clustered; placebo-scaled], [#n("dose.primary.h3.z_diff")\; #n("dose.primary.h3.placebo_robust_sd.z_diff")], [@ch-dose],
  [Median dose, first; second], [#n("dose.same_size.first.median_abs_dose")\; #n("dose.same_size.second.median_abs_dose")], [@ch-dose],
  [z diff, absolute ruler; hybrid (post hoc)], [#n("rulers.primary.absolute.z_diff")\; #n("rulers.primary.hybrid.z_diff")], [@ch-rulers],
  [z diff range over the Debilitate and Reflect calls], [#n("rulers.reflect_off_debilitate_off.ln.z_diff") to #n("rulers.primary_debilitate_table_dose.ln.z_diff")], [@ch-rulers],
  [z diff without Regent's cards], [#n("leave_out.primary.regent.z_diff")], [@ch-rulers],
  [Power: first-patch-sized slope; half that], [#n("power.primary.honest.planted_1_44.power_slope_second")\; #n("power.primary.honest.planted_0_7.power_slope_second")], [@ch-explanations],
  [Fake patch: slope; spread fake against real], [#n("checks.fake_patch.h3.slope_pm")\; #n("checks.fake_patch.h3.sd_fake") against #n("checks.fake_patch.h3.sd_real")], [@ch-explanations],
  [First slope with other characters' controls; z diff], [#n("checks.control_scope.other.primary.slope_first_pm")\; #n("checks.control_scope.other.primary.z_diff")], [@ch-explanations],
  [Token runs: z diff], [#n("checks.token.subset.run_clustered.z_diff")], [@ch-explanations],
  [Simulation: truth; naive; IV], [#n("iv.single.truth")\; #n("iv.single.naive_pm")\; #n("iv.single.iv_pm")], [@ch-wins],
)
