"""Tweak sizes for the dose-response plot: one row per numeric tweak card-patch.

Reads reference/card_patch_fields.csv, reference/windows.csv (level = card_patch) and
reference/card_changes.csv, and writes reference/tweak_sizes.csv. No run data.

Main field: the first changed field among MAIN_FIELDS, else the single changed vars.*
field; blank (with a note) if neither fits. log_ratio = ln(new / old) on it. The
upgrade.* delta that changed goes in upgrade_field / upgrade_old / upgrade_new, and
upgraded_log_ratio = ln((new + upgrade_new) / (old + upgrade_old)) when both are known.

Usage (from the repo root):
    python -m spirometry.tweaks          # write reference/tweak_sizes.csv and print it
"""
import collections, math, pathlib

from spirometry.patch_history import tweak_report, vkey
from spirometry.treatment import read_csv, write_csv

REF = pathlib.Path("reference")
MAIN_FIELDS = ["damage", "block", "energy_gain", "powers_applied[0].amount"]
COLS = ["card_patch_id", "card_id", "color", "stable_build", "before_builds", "after_builds",
        "main_field", "old", "new", "log_ratio", "upgrade_field", "upgrade_old",
        "upgrade_new", "upgraded_log_ratio", "upgrade_only", "mixed_direction",
        "solo_estimable", "direction", "note"]

# direction = +1 when a bigger number makes the card stronger (the default). A card-patch
# whose main number works the other way (a drawback, a cost-like count) gets -1 here, with
# a comment saying why. None found among the 50 numeric tweaks (Phil to review):
# every main field is damage, block, a power amount, Forge, gold or a card-generating count.
DIRECTION = {}

# Hand notes for cases the rules can't see (Phil to review).
NOTES = {
    "DEATH_MARCH@v0.107.1/patch": "mostly an upgrade change, but base vars.ExtraDamage "
                                  "changes too (3 -> 4): not upgrade-only, and its "
                                  "un-upgraded offers are no placebo",
}


def num(s):
    try:
        return float(str(s).replace("+", ""))
    except ValueError:
        return None


def log_ratio(old, new):
    return f"{math.log(new / old):.4f}" if old and new and old > 0 and new > 0 else ""


def fmt(x):
    return "" if x is None else f"{x:g}"


def earlier_value(patches, card, stable, field):
    """The field's value after the card's latest card-patch before `stable` that changed it
    (so the value the card carried into this window), or None."""
    best = None
    for (c, s), fields in patches.items():
        if c == card and vkey(s) < vkey(stable) and field in fields:
            if best is None or vkey(s) > vkey(best[0]):
                best = (s, fields[field]["new"])
    return (best[0], num(best[1])) if best else None


def build_rows(patch_fields, windows, changes):
    tweaks = collections.OrderedDict()
    patches = collections.defaultdict(dict)               # (card, stable) -> field -> row
    for r in patch_fields:
        patches[(r["card_id"], r["stable_build"])][r["field"]] = r
        if r["change_kind"] == "tweak":
            tweaks.setdefault(r["card_patch_id"], []).append(r)
    win = {w["event_id"]: w for w in windows if w["level"] == "card_patch"}
    color = {(r["card_id"], r["stable_build"]): r.get("color", "") for r in changes}
    not_solo = {(c, s): why for c, s, why in tweak_report(changes) if why}

    out = []
    for cpid, rows in tweaks.items():
        card, stable = rows[0]["card_id"], rows[0]["stable_build"]
        f = {r["field"]: r for r in rows}
        notes = []
        vars_ = [k for k in f if k.startswith("vars.")]
        upg = [k for k in f if k.startswith("upgrade.")]
        upgrade_only = len(upg) == len(f)
        main = next((k for k in MAIN_FIELDS if k in f), None)
        if main is None and len(vars_) == 1:
            main = vars_[0]
        if main is None:
            notes.append("upgrade-only: no base field changed" if upgrade_only else
                         f"no main field: {len(vars_)} vars.* fields changed")
        old = num(f[main]["old"]) if main else None
        new = num(f[main]["new"]) if main else None

        uf = upg[0] if len(upg) == 1 else None
        if len(upg) > 1:
            notes.append(f"{len(upg)} upgrade fields changed: " + " ".join(upg))
        uo = num(f[uf]["old"]) if uf else None
        un = num(f[uf]["new"]) if uf else None
        base_o, base_n = old, new
        if uf and main is None and upgrade_only:
            # The base value didn't change in this window: take it from the card's earlier
            # card-patch of the matching field, if there is one (upgrade.block -> block).
            prev = earlier_value(patches, card, stable, uf.split(".", 1)[1])
            if prev:
                base_o = base_n = prev[1]
                notes.append(f"upgraded ratio uses base {uf.split('.', 1)[1]} {prev[1]:g} "
                             f"(set by the {prev[0]} card-patch, unchanged since)")
            else:
                notes.append("base value not in the change tables: no upgraded ratio")
        up_lr = (log_ratio(base_o + uo, base_n + un)
                 if None not in (base_o, base_n, uo, un) else "")

        signs = {math.copysign(1, num(r["new"]) - num(r["old"])) for r in rows
                 if num(r["new"]) is not None and num(r["old"]) is not None
                 and num(r["new"]) != num(r["old"])}
        if cpid in NOTES:
            notes.append(NOTES[cpid])
        why = not_solo.get((card, stable))
        if why:
            notes.append("not solo-estimable: " + ", ".join(why))
        w = win.get(cpid, {})
        out.append(dict(
            card_patch_id=cpid, card_id=card, color=color.get((card, stable), ""),
            stable_build=stable, before_builds=w.get("before_builds", ""),
            after_builds=w.get("after_builds", ""), main_field=main or "",
            old=fmt(old), new=fmt(new), log_ratio=log_ratio(old, new),
            upgrade_field=uf or "", upgrade_old=f[uf]["old"] if uf else "",
            upgrade_new=f[uf]["new"] if uf else "", upgraded_log_ratio=up_lr,
            upgrade_only="yes" if upgrade_only else "no",
            mixed_direction="yes" if len(signs) > 1 else "no",
            solo_estimable="no" if why else "yes",
            direction=DIRECTION.get(cpid, 1), note="; ".join(notes)))
    out.sort(key=lambda r: (vkey(r["stable_build"]), r["card_id"]))
    return out


def build(ref=REF, quiet=False):
    rows = build_rows(read_csv(ref / "card_patch_fields.csv"), read_csv(ref / "windows.csv"),
                      read_csv(ref / "card_changes.csv"))
    write_csv(ref / "tweak_sizes.csv", rows, COLS)
    if not quiet:
        for r in rows:
            print(f"  {r['card_patch_id']:32s} {r['main_field'] or '-':26s} "
                  f"{r['old'] or '':>3s} -> {r['new'] or '':<3s} {r['log_ratio'] or '':>8s}  "
                  f"up {r['upgrade_old'] or '':>3s} -> {r['upgrade_new'] or '':<3s} "
                  f"{r['upgraded_log_ratio'] or '':>8s}  "
                  f"{'U' if r['upgrade_only'] == 'yes' else ' '}"
                  f"{'M' if r['mixed_direction'] == 'yes' else ' '}"
                  f"{' ' if r['solo_estimable'] == 'yes' else 'X'}")
    return rows


if __name__ == "__main__":
    build()
