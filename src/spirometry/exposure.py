"""Beta exposure of each numeric tweak: when did the change first appear on a beta build,
and how long before its stable release? One row per solo-estimable numeric tweak
card-patch. Reference tables only, no run data.

Reads reference/tweak_sizes.csv, windows.csv (level = card_patch, `members` = the card's
change events that make up the card-patch), change_events.csv, change_event_fields.csv
and builds.csv; writes reference/beta_exposure.csv.

first_beta_build / first_beta_date: the earliest `first_beta` among the card-patch's member
events (for a change revised on a later beta, Parry, Untouchable v0.103.2, Reflect, the
first step). beta_steps: the member events' changes of the step field (the main field;
the upgrade field for upgrade-only tweaks), `build:date:old>new` in release order.
beta_timing_note: the member events' field rows whose beta attribution the treatment
tables mark as uncertain ("which beta unresolved", "no beta timing", "spread over the
card's betas"), so a date there is the tables' best placement, not a fact. Blank where a
source doesn't say.

Usage (from the repo root):
    python -m spirometry.exposure        # write reference/beta_exposure.csv and print it
"""
import datetime, pathlib

from spirometry.treatment import read_csv, write_csv

REF = pathlib.Path("reference")
COLS = ["card_patch_id", "card_id", "color", "stable_build", "stable_date",
        "first_beta_build", "first_beta_date", "lead_days", "step_field", "n_beta_steps",
        "beta_steps", "member_events", "revised_or_reverted",
        "other_events_after_first_beta", "other_event_ids", "beta_timing_note",
        "upgrade_only"]
UNCERTAIN = ("unresolved", "no beta timing", "spread over")


def _date(s):
    return datetime.date.fromisoformat(s) if s else None


def build_rows(tweaks, windows, events, fields, builds):
    date = {b["build_id"]: b["release_date"] for b in builds}
    members = {w["event_id"]: w["members"].split() for w in windows
               if w["level"] == "card_patch"}
    ev = {e["event_id"]: e for e in events}
    by_card = {}
    for e in events:
        by_card.setdefault(e["card_id"], []).append(e)
    fld = {}
    for f in fields:
        fld.setdefault(f["event_id"], {})[f["field"]] = f
    out = []
    for t in tweaks:
        if t["solo_estimable"] != "yes":
            continue
        cpid, card = t["card_patch_id"], t["card_id"]
        up_only = t["upgrade_only"] == "yes"
        step_field = t["upgrade_field"] if up_only else t["main_field"]
        mem = [m for m in members.get(cpid, []) if m in ev]
        firsts = sorted({ev[m]["first_beta"] for m in mem if ev[m]["first_beta"]},
                        key=lambda b: date.get(b) or "9999")
        first = firsts[0] if firsts else ""
        fdate, sdate = date.get(first, ""), date.get(t["stable_build"], "")
        lead = (_date(sdate) - _date(fdate)).days if fdate and sdate else ""
        steps, notes = [], []
        for m in sorted(mem, key=lambda m: date.get(ev[m]["event_build"]) or "9999"):
            f = fld.get(m, {}).get(step_field)
            if f and ev[m]["timing"] == "beta":
                b = ev[m]["event_build"]
                steps.append(f"{b}:{date.get(b, '')}:{f['old']}>{f['new']}")
            for g in fld.get(m, {}).values():
                if any(u in g["via"] for u in UNCERTAIN):
                    notes.append(f"{m} {g['field']}: {g['via']}")
        rr = [f"{m} {ev[m]['status']}" for m in mem
              if "revised" in ev[m]["status"] or "reverted" in ev[m]["status"]]
        others = []
        if fdate and sdate:
            for e in by_card.get(card, []):
                d = date.get(e["event_build"], "")
                if e["event_id"] not in mem and d and fdate <= d < sdate:
                    others.append(e["event_id"])
        out.append(dict(
            card_patch_id=cpid, card_id=card, color=t["color"],
            stable_build=t["stable_build"], stable_date=sdate, first_beta_build=first,
            first_beta_date=fdate, lead_days=lead, step_field=step_field,
            n_beta_steps=len(steps), beta_steps="; ".join(steps),
            member_events=" ".join(mem),
            revised_or_reverted=("yes: " + "; ".join(rr)) if rr else "no",
            other_events_after_first_beta=len(others) if fdate and sdate else "",
            other_event_ids=" ".join(sorted(others)), beta_timing_note="; ".join(notes),
            upgrade_only=t["upgrade_only"]))
    return out


def build(ref=REF, quiet=False):
    ref = pathlib.Path(ref)
    rows = build_rows(read_csv(ref / "tweak_sizes.csv"), read_csv(ref / "windows.csv"),
                      read_csv(ref / "change_events.csv"),
                      read_csv(ref / "change_event_fields.csv"),
                      read_csv(ref / "builds.csv"))
    write_csv(ref / "beta_exposure.csv", rows, COLS)
    if not quiet:
        for r in rows:
            print(f"  {r['card_patch_id']:32s} {r['first_beta_build']:9s} "
                  f"{r['first_beta_date']:10s} {str(r['lead_days']):>3s}d  "
                  f"{r['beta_steps']}{'  U' if r['upgrade_only'] == 'yes' else ''}"
                  f"{'  R' if r['revised_or_reverted'] != 'no' else ''}"
                  f"{'  +' + str(n) if (n := r['other_events_after_first_beta']) else ''}")
    return rows


if __name__ == "__main__":
    build()
