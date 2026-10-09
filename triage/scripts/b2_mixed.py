"""Section B2: mixed tweaks and dose measurement.

Part 1. Leading Strike and Reflect as SENSITIVITY variants (the primary fit keeps them off the
line). Doses are fixed below, before any fit; their measured effects are not used to choose.
  Leading Strike (label "Buffed", patch_notes_cards.csv v0.102.0): 7 dmg + 1 Shiv -> 3 dmg +
    2 Shivs; a Shiv deals 4 (changelog 1.1.0 text in notes/patch_history_samples/: "Deal 4
    damage."). Damage at Strength S: old 7+S + (4+S) = 11+2S, new 3+S + 2(4+S) = 11+3S.
    Doses: ln((11+3S)/(11+2S)) for S = 0..3; sign-only +1 (on the sign ruler); naive -0.847.
  Reflect (label "Nerfed", v0.104.0, v0.107.0 and v0.107.1 notes): base Block 17 -> 15,
    upgraded 21 -> 20 (upgrade delta +4 -> +5; changelog 1.2.0 text). Doses: base -0.125,
    upgraded total ln(20/21) = -0.049, their mean -0.087; sign-only -1.
Part 2. Dose coverage: a hand classification of each line tweak from its card text (does the
  changed number make up the card's whole effect, or one component of it?). Made by the
  triage author from the changelog/patch-note text, AFTER notebook 05's effects had been
  seen, so it is not blind. Sensitivity only.
Part 3. Attenuation arithmetic for measurement error in the dose.

Read-only; runs in about a second.   python triage/scripts/b2_mixed.py [h3|main]
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "triage/scripts")
from common import add_rulers, all_tweaks, fit, on_line, slopes_by_patch  # noqa: E402

FITS = sys.argv[1] if len(sys.argv) > 1 else "h3"
LS, RF = "LEADING_STRIKE@v0.103.2/patch", "REFLECT@v0.107.1/patch"

LS_DOSES = {f"damage-equivalent S={s}": float(np.log((11 + 3 * s) / (11 + 2 * s)))
            for s in range(4)}
LS_DOSES["naive main field (-0.847)"] = float(np.log(3 / 7))
RF_DOSES = {"base block (-0.125)": float(np.log(15 / 17)),
            "upgraded total (-0.049)": float(np.log(20 / 21)),
            "mean of the two (-0.087)": float((np.log(15 / 17) + np.log(20 / 21)) / 2)}

D = all_tweaks(FITS)
base_line = on_line(D)
print(f"fits: did_{FITS}.parquet")
for c in [LS, RF]:
    r = D.loc[c]
    print(f"  {r.card_id}: beta {100 * r.beta:+.2f} pp, beta_lo {r.beta_lo:+.3f} ± {r.se_lo:.3f} "
          f"(shown for the record; not used to choose doses)")
print("Leading Strike doses:", {k: round(v, 4) for k, v in LS_DOSES.items()})
print("Reflect doses:", {k: round(v, 4) for k, v in RF_DOSES.items()})


def with_points(extra):
    """The 38-tweak line plus mixed tweaks at given ln doses {card_patch_id: x}."""
    L = base_line.copy()
    for cpid, x in extra.items():
        row = D.loc[[cpid]].copy()
        row["x"] = x
        L = pd.concat([L, row])
    return L


def summarize(label, L, x="x"):
    r = slopes_by_patch(L, x)
    return dict(variant=label, n1=r["n1"], n2=r["n2"], slope1=r["slope1"], se1=r["se1"],
                slope2=r["slope2"], se2=r["se2"], diff=r["diff"], se_diff=r["se_diff"],
                z_diff=r["z_diff"], tau2=r["tau2"])


rows = [summarize("PRIMARY: both off the line", base_line)]
for k, v in LS_DOSES.items():
    rows.append(summarize(f"LS {k}", with_points({LS: v})))
for k, v in RF_DOSES.items():
    rows.append(summarize(f"Reflect {k}", with_points({RF: v})))
for kl, vl in LS_DOSES.items():
    for kr, vr in RF_DOSES.items():
        rows.append(summarize(f"LS {kl} + Reflect {kr}", with_points({LS: vl, RF: vr})))
T = pd.DataFrame(rows).set_index("variant")
pd.set_option("display.width", 220, "display.max_rows", 100)
print("\n== Part 1a. ln ruler")
print(T.round(3).to_string())
p = T.iloc[0]
o = T.iloc[1:]
print(f"\nAcross all {len(o)} variants: slope1 {o.slope1.min():.3f}..{o.slope1.max():.3f} "
      f"(primary {p.slope1:.3f}); slope2 {o.slope2.min():.3f}..{o.slope2.max():.3f} "
      f"(primary {p.slope2:.3f}); diff {o['diff'].min():.3f}..{o['diff'].max():.3f} "
      f"(primary {p['diff']:.3f}); z_diff {o.z_diff.min():.2f}..{o.z_diff.max():.2f} "
      f"(primary {p.z_diff:.2f})")
no_naive = o[~o.index.str.contains("naive")]
print(f"Without the naive LS dose: z_diff {no_naive.z_diff.min():.2f}..{no_naive.z_diff.max():.2f}")

print("\n== Part 1b. sign ruler (LS +1 from its 'Buffed' label, Reflect -1 from 'Nerfed')")
srows = []
for label, extra in [("primary", {}), ("LS +1", {LS: 1.0}), ("Reflect -1", {RF: -1.0}),
                     ("both", {LS: 1.0, RF: -1.0})]:
    L = with_points({k: np.sign(v) for k, v in extra.items()})
    L = add_rulers(L)
    srows.append(summarize(label, L, "x_sign"))
print(pd.DataFrame(srows).set_index("variant").round(3).to_string())

# Part 2 -------------------------------------------------------------------------------
# whole: the changed number is the card's whole effect, or the effect is proportional to it
#        (per-trigger amounts), so ln(new/old) is the card-level change at fixed game state.
# component: the card has other value it keeps unchanged (extra damage/block, a generated
#        card, a free next card, Forge, Vigor, stars, a debuff), so ln of the changed number
#        overstates the card-level change.
# scaling: the changed number is a base or a per-event increment of a total that also depends
#        on game state (discards, draws, star cards, plays).
COVERAGE = {
    # first patch
    "ANTICIPATE": "whole", "COLLISION_COURSE": "component", "CORROSIVE_WAVE": "whole",
    "DANSE_MACABRE": "whole", "DEBILITATE@v0.103.2/patch": "component", "FIGHT_ME": "component",
    "FLICK_FLACK": "whole", "GATHER_LIGHT": "component", "GLITTERSTREAM": "component",
    "GRAND_FINALE": "whole", "HEIRLOOM_HAMMER": "component", "HEMOKINESIS": "whole",
    "I_AM_INVINCIBLE": "component", "KINGLY_KICK": "whole", "MEMENTO_MORI": "scaling",
    "PARRY": "whole", "PATTER@v0.103.2/patch": "component", "PINPOINT": "whole",
    "REFINE_BLADE": "component", "SCULPTING_STRIKE": "component", "SKEWER": "whole",
    "SOLAR_STRIKE": "component", "UNTOUCHABLE@v0.103.2/patch": "whole",
    "WROUGHT_IN_WAR": "component",
    # second patch
    "BULWARK": "component", "CRESCENT_SPEAR": "scaling", "DEATH_MARCH": "scaling",
    "DEBILITATE@v0.107.1/patch": "component", "FURNACE": "whole", "HYPERBEAM": "whole",
    "JUGGERNAUT": "whole", "PATTER@v0.107.1/patch": "component", "POUNCE": "component",
    "SIC_EM": "component", "SYNTHESIS": "component", "THE_SCYTHE": "scaling",
    "UNRELENTING": "component", "UPROAR": "component",
}
L = base_line.copy()
L["coverage"] = [COVERAGE.get(i, COVERAGE.get(c)) for i, c in zip(L.index, L.card_id)]
assert L.coverage.notna().all(), L[L.coverage.isna()].card_id.tolist()
print("\n== Part 2. Dose coverage by patch (hand classification from card text; not blind)")
print(pd.crosstab(L.coverage, L.patch, margins=True).to_string())
print("\nKind by patch:")
print(pd.crosstab(L.kind, L.patch, margins=True).to_string())

L["partial"] = (L.coverage != "whole").astype(float)
sec = L.second.to_numpy()
for label, cols in [
        ("slope per patch + x*partial", [L.x * L.partial]),
        ("slope per patch + x*partial + x*partial*second", [L.x * L.partial, L.x * L.partial * sec])]:
    X = np.column_stack([np.ones(len(L)), sec, L.x * (1 - sec), L.x * sec] + [c.to_numpy() for c in cols])
    b, cov, tau2, Q, dof = fit(L.beta_lo, L.se_lo, X)
    se = np.sqrt(np.diag(cov))
    c = np.zeros(len(b)); c[2], c[3] = -1, 1
    print(f"  {label}: slope1(whole) {b[2]:+.3f} ± {se[2]:.3f}, slope2(whole) {b[3]:+.3f} ± {se[3]:.3f}, "
          f"x*partial {b[4]:+.3f} ± {se[4]:.3f}"
          + (f", x*partial*second {b[5]:+.3f} ± {se[5]:.3f}" if len(b) > 5 else "")
          + f"; z(slope2-slope1 for whole) {(c @ b) / np.sqrt(c @ cov @ c):+.2f}; tau2 {tau2:.4f}")
for lab, keep in [("whole only", L.coverage == "whole"), ("drop scaling", L.coverage != "scaling")]:
    r = slopes_by_patch(L[keep])
    print(f"  {lab}: n {r['n1']}+{r['n2']}, slope1 {r['slope1']:+.3f} ± {r['se1']:.3f}, slope2 "
          f"{r['slope2']:+.3f} ± {r['se2']:.3f}, z_diff {r['z_diff']:+.2f}")

# Part 3 -------------------------------------------------------------------------------
print("\n== Part 3. Attenuation arithmetic")
r = slopes_by_patch(base_line)
lam_hi = (r["slope2"] + 1.96 * r["se2"]) / r["slope1"]
print(f"  slope2/slope1 = {r['slope2'] / r['slope1']:.3f}; upper 95% slope2 / slope1 = {lam_hi:.2f}")
print("  Classical error in x (noise independent of the true dose) multiplies a patch's slope by")
print("  lambda = var(true x) / var(observed x). A flat patch 2 from patch-2-only measurement error")
for v in [lam_hi, 0.25, 0.1]:
    print(f"    lambda = {v:.2f}: error variance = {(1 / v - 1):.1f} x the true-dose variance "
          f"(observed x sd {np.sqrt(1 / v):.1f} x the true sd)")
for pt in ["first", "second"]:
    s = base_line[base_line.patch == pt].x
    print(f"  observed x, {pt}: sd {s.std():.3f}, mean |x| {s.abs().mean():.3f}")
