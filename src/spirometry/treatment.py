"""Per-build card versions and treatment windows for the pick-rate DiD (Phase 4).

Reads the committed reference tables (builds.csv, card_changes.csv, beta_card_changes.csv,
behavior_changes.csv, patch_notes_cards.csv, text_only_labels.csv, and the cached card list
for colors) and writes:

    reference/change_events.csv       one row per card change event (a card changing on one
                                      build), behavior (bug-fix) events included, marked
                                      sensitivity-only
    reference/change_event_fields.csv one row per (event, field): old -> new, relative change
    reference/card_versions.csv       one row per (card, build): version index and the events
                                      applied so far
    reference/windows.csv             one row per (event, branch): the builds just before and
                                      after, whether they differ only by this event, control
                                      exclusions and behavior flags

Version rules (PLAN.md phase 4 and decision log):
- An event is a card changing on one build. Within a stable window, card_changes.csv gives
  the net change and the first beta per field; the other betas that touched the field
  ("field also changed in ..."), the patch notes and beta_card_changes.csv add the
  intermediate steps, so beta revisions and reverts are separate events.
- A beta build carries every event first seen on a beta at or before it (version order);
  a stable build carries every event of its window and of earlier windows, reverted ones
  included (they net out). Stable-only events (dated to the stable build itself) are
  carried by later stables and by betas that are both later in version and released on or
  after that date. Hotfixes carry nothing beyond their window unless the notes say so
  (behavior_changes rows dated to them).
- v0.98.0 (branch unknown) and update-history's '-beta' pseudo-versions get no version.

Usage (from the repo root):
    python -m spirometry.treatment            # build the four CSVs and print the checks
"""
import collections, csv, json, pathlib, re

from spirometry.notes_crosscheck import (CHANGE_SECTIONS, MAJOR_UPDATES, NON_NUMERIC_CUE,
                                         canon, num, window_of)
from spirometry.patch_history import card_attrs, classify, vkey

REF = pathlib.Path("reference")

# Thin builds from the audit (SPIROMETRY.md, "Thin builds"): pooled with a same-branch
# neighbour when no card change event falls between them. v0.99.0 is thin too but is left
# out of all windows (decision log).
THIN_BUILDS = {"v0.103.1", "v0.105.0", "v0.109.1"}
NO_WINDOW_BUILDS = {"v0.99.0"}
UNRESOLVED = "?"                  # field value between two betas that update-history can't split

EVENT_COLS = ["event_id", "card_id", "color", "event_build", "first_beta", "stable_build",
              "window_stable", "timing", "change_kind", "kind_source", "text_only_label",
              "status", "sensitivity_only", "source", "field_changes", "note"]
FIELD_COLS = ["event_id", "card_id", "field", "old", "new", "rel_change", "via"]
VERSION_COLS = ["card_id", "build_id", "branch", "release_date", "version", "event_ids",
                "behavior_event_ids", "note"]
PATCH_FIELD_COLS = ["card_patch_id", "card_id", "stable_build", "change_kind", "field", "old",
                    "new", "rel_change", "events"]
WINDOW_COLS = ["level", "event_id", "card_id", "change_kind", "members", "branch",
               "before_builds", "after_builds",
               "clean", "reason", "control_exclusions", "behavior_in_window",
               "behavior_event_ids", "control_behavior_flags"]


def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {path} ({len(rows)} rows)")


def vk(v):
    return vkey(v)[0]


def fmt(x, like=""):
    """Number -> string, '+' kept when the value it replaces had one ('+3' upgrade deltas)."""
    s = f"{x:g}"
    return ("+" + s) if str(like).startswith("+") and x >= 0 else s


def rel_change(old, new):
    o, n = num(old), num(new)
    if o is None or n is None or o == 0:
        return ""
    return f"{(n - o) / abs(o):.4f}"


# ------------------------------------------------------------------------------ events

class Event(dict):
    """A card change event. Keys follow EVENT_COLS; `fields` is a list of
    {field, old, new, via} and `order` sorts events of one card on one build."""


def new_event(card, build, **kw):
    e = Event(event_id=f"{card}@{build}", card_id=card, event_build=build, first_beta="",
              stable_build="", window_stable="", timing="", change_kind="", kind_source="",
              text_only_label="", status="", sensitivity_only="no", source="", note="",
              fields=[])
    e.update(kw)
    return e


def notes_steps(rows):
    """Numeric patch-note clauses -> chains per quantity: [[(version, b0, u0, b1, u1)]],
    a step joining a chain when its 'before' equals the chain's last 'after'."""
    chains = []
    for r in sorted(rows, key=lambda r: vk(r["version"])):
        if num(r["before_base"]) is None or num(r["after_base"]) is None:
            continue
        step = (r["version"], r["before_base"], r["before_upg"], r["after_base"], r["after_upg"])
        q = canon(r["quantity"])
        for c in chains:
            if c[0] == q and num(c[1][-1][3]) == num(step[1]) and c[1][-1][0] != step[0]:
                c[1].append(step)
                break
        else:
            chains.append((q, [step]))
    return [c for _, c in chains]


def resolve_field(field, old, new, betas, chains):
    """Split a field's net old -> new over the betas update-history says touched it, using
    a patch-note chain that starts at `old` and ends at `new`. Returns [(beta, old, new)] or
    None if no single chain does it."""
    found = set()
    for c in chains:
        if not all(s[0] in betas for s in c):
            continue
        if field.startswith("upgrade."):
            if not all(num(s[2]) is not None and num(s[4]) is not None for s in c):
                continue
            deltas = [num(c[0][2]) - num(c[0][1])] + [num(s[4]) - num(s[3]) for s in c]
            if deltas[0] != (num(old) or 0) or deltas[-1] != (num(new) or 0):
                continue
            steps, prev = [], old
            for s, d0, d1 in zip(c, deltas, deltas[1:]):
                if d0 != d1:
                    nxt = new if d1 == (num(new) or 0) and s is c[-1] else fmt(d1, old)
                    steps.append((s[0], prev, nxt))
                    prev = nxt
        else:
            if num(c[0][1]) != num(old) or num(c[-1][3]) != num(new):
                continue
            steps, prev = [], old
            for s in c:
                nxt = new if s is c[-1] else fmt(num(s[3]), old)
                steps.append((s[0], prev, nxt))
                prev = nxt
        found.add(tuple(steps))
    if len(found) == 1:
        steps = list(found.pop())
        return steps if steps else None
    return None


RARITY_WORDS = re.compile(r"\b(Common|Uncommon|Rare)\b|\brarit(?:y|ies)\b")
ARROW = re.compile(r"->|→")


def notes_kind(rows, texts):
    """change_kind for a beta event known only from patch notes (or update-history text),
    by rule: Added -> added; Reworked/Deprecated -> rework; numbers -> tweak (cost_change
    for a cost); 'rarity' or two different rarities named -> rarity_change; a clause
    without a numeric change that says 'now', 'no longer', ... or has its own before ->
    after ('this turn -> next turn') -> mechanic. A tweak with a mechanic clause is a
    rework (as Glow, Shatter). An item whose verb is Reverted is `revert`; a change that
    reverts part of a card and changes something else is a rework."""
    from spirometry.patch_notes import CHANGE_RE
    labels, revert = set(), False
    for r in rows:
        verb, text = r.get("verb", ""), r.get("text", "")
        if verb == "Added":
            labels.add("added")
        elif verb.startswith(("Reworked", "Deprecated")):
            labels.add("rework")
        if verb.startswith("Reverted"):
            revert = True
            continue
        if re.search(r"\breverted\b", text, re.I):
            labels.add("rework")
        if re.search(r"\brarit(y|ies)\b", text, re.I) or \
                len(set(RARITY_WORDS.findall(text)) - {""}) > 1:
            labels.add("rarity_change")
        if num(r.get("before_base")) is not None and num(r.get("after_base")) is not None:
            labels.add("cost_change" if canon(r["quantity"]) in ("cost", "star cost")
                       else "tweak")
            if NON_NUMERIC_CUE.search(r["quantity"]):   # 'now Exhausts ... instead of cost'
                labels.add("mechanic")
        body = text.split(":", 1)[1] if ":" in text else text
        for clause in re.split(r"\s\*\s|;|, but |\. ", body):
            clause = clause.strip(" *.")
            if not clause or CHANGE_RE.search(clause) or re.search(r"\brevert", clause, re.I):
                continue
            if not RARITY_WORDS.search(clause) and (NON_NUMERIC_CUE.search(clause)
                                                    or ARROW.search(clause)):
                labels.add("mechanic")
    for t in texts:                      # update-history "Label: old → new" pairs
        k = classify([{"field": f, "old": o, "new": n} for f, o, n in t])
        labels |= set((k or "").split("+")) - {""}
    if revert and not labels:
        return "revert"
    if "added" in labels:
        return "added"
    if not labels:
        labels.add("mechanic")
    if "tweak" in labels and "mechanic" in labels:
        labels.add("rework")
    if "rework" in labels:
        labels -= {"tweak", "mechanic", "other"}
    order = ["rework", "tweak", "mechanic", "other", "cost_change", "rarity_change"]
    return "+".join(k for k in order if k in labels)


def history_pairs(text):
    """update-history text 'Block: 8 → 7; Vars.block: 8 → 7' -> [(field, old, new)]."""
    out = []
    for part in text.split("; "):
        m = re.fullmatch(r"(.+?): (.*) → (.*)", part.strip())
        if m:
            out.append((m.group(1).lower().replace(" ", "_"), m.group(2), m.group(3)))
    return out


def notes_fields(rows, via="patch notes"):
    out = []
    for r in rows:
        if num(r.get("before_base")) is None or num(r.get("after_base")) is None:
            continue
        q = r["quantity"]
        out.append({"field": f"notes:{q}", "old": r["before_base"], "new": r["after_base"],
                    "via": via})
        if r.get("before_upg") and r.get("after_upg"):
            out.append({"field": f"notes:{q} (upgraded)", "old": r["before_upg"],
                        "new": r["after_upg"], "via": via})
    return out


def build_events(builds, changes, beta_changes, behavior, notes, labels):
    """All card change events and behavior events, sorted by (event build, card)."""
    branch = {b["build_id"]: b["branch"] for b in builds}
    stables = sorted((b for b in branch if branch[b] == "stable"), key=vk)
    label = {(r["card_id"], r["stable_build"]): r["label"] for r in labels}
    note_rows = collections.defaultdict(list)
    for r in notes:
        if (r["role"] == "subject" and r["section"] in CHANGE_SECTIONS
                and r["version"] not in MAJOR_UPDATES):
            note_rows[(r["card_id"], r["version"])].append(r)
    bcc = collections.defaultdict(list)
    for r in beta_changes:
        if r["change_kind"] != "artifact":
            bcc[(r["card_id"], r["version"])].append(r)

    events = []
    # --- stable windows: card_changes groups, plus in-window notes and beta_card_changes
    groups = collections.defaultdict(list)
    for r in changes:
        if r["change_kind"] != "artifact":
            groups[(r["card_id"], r["stable_build"])].append(r)
    for card, v in list(bcc) + list(note_rows):
        w = window_of(v)
        after = any(x["status"].startswith("after_last_stable") for x in bcc.get((card, v), []))
        if w and not after:
            groups.setdefault((card, w), [])
    for (card, stable), rows in sorted(groups.items(), key=lambda t: (vk(t[0][1]), t[0][0])):
        kind = rows[0]["change_kind"] if rows else ""
        assert all(r["change_kind"] == kind for r in rows), (card, stable)
        in_window = lambda v: window_of(v) == stable
        nvs = {v for (c, v) in note_rows if c == card and in_window(v)}
        bvs = {v for (c, v) in bcc if c == card and in_window(v)
               and not bcc[(c, v)][0]["status"].startswith("after_last_stable")}
        field_betas = {}
        for r in rows:
            bs = [r["beta_build"]] if r["beta_build"] else []
            m = re.search(r"also changed in ([v0-9., ]+)", r["source"])
            if m:
                bs += [x.strip() for x in m.group(1).split(",") if x.strip()]
            field_betas[r["field"]] = sorted(set(bs), key=vk)
        versions = set(nvs) | set(bvs)
        for bs in field_betas.values():
            versions |= set(bs)
        betas = sorted((v for v in versions if branch.get(v) == "beta"), key=vk)
        chains = notes_steps([x for v in nvs for x in note_rows[(card, v)]])
        per_version = collections.defaultdict(list)
        for r in rows:
            f, bs = r["field"], field_betas[r["field"]]
            if not bs:
                if not betas:
                    per_version[""].append({"field": f, "old": r["old"], "new": r["new"],
                                            "via": "card_changes; no beta timing"})
                    continue
                bs = betas
                via0 = "card_changes; no update-history match, spread over the card's betas"
            else:
                via0 = "card_changes"
            if len(bs) == 1:
                per_version[bs[0]].append({"field": f, "old": r["old"], "new": r["new"],
                                           "via": via0})
                continue
            steps = resolve_field(f, r["old"], r["new"], bs, chains)
            if steps:
                for v, o, n in steps:
                    per_version[v].append({"field": f, "old": o, "new": n,
                                           "via": "card_changes net, split by patch-note numbers"})
                continue
            for i, v in enumerate(bs):
                o = r["old"] if i == 0 else UNRESOLVED
                n = r["new"] if i == len(bs) - 1 else UNRESOLVED
                per_version[v].append({"field": f, "old": o, "new": n,
                                       "via": via0 + "; which beta unresolved"})
        steps_at = set(per_version) | set(betas) | ({stable} & versions)
        for v in sorted(steps_at, key=lambda x: vk(x) if x else (0,)):
            if v == "":
                e = new_event(card, stable, timing="unknown", stable_build=stable,
                              window_stable=stable,
                              note="card_changes gives no beta for this change and the card "
                                   "has no other event in the window: beta timing unknown")
            elif v == stable:
                e = new_event(card, stable, timing="stable_only", stable_build=stable,
                              window_stable=stable,
                              note="update-history dates this change to the stable build")
            else:
                e = new_event(card, v, first_beta=v, timing="beta", stable_build=stable,
                              window_stable=stable)
            fields = per_version.get(v, [])
            bx = bcc.get((card, v), [])
            nx = note_rows.get((card, v), [])
            e["fields"] = fields + notes_fields(nx)
            e["text_only_label"] = label.get((card, stable), "") if "text_only" in kind else ""
            curated = [x["change_kind"] for x in bx if x["change_kind"]]
            if fields:
                notes_only = all(f["field"] == "(patch notes)" for f in fields)
                e["change_kind"] = kind
                e["kind_source"] = "notes-only" if notes_only else "card_changes"
            elif curated:
                e["change_kind"], e["kind_source"] = curated[0], "beta_card_changes"
            else:
                hist = [history_pairs(x["text"]) for x in bx
                        if x["source"].startswith("update-history")]
                e["change_kind"] = notes_kind(bx or nx, hist)
                e["kind_source"] = "text rule"
            srcs = (["card_changes"] if fields else []) + (["patch notes"] if nx else []) + \
                   (["beta_card_changes"] if bx else [])
            e["source"] = "; ".join(srcs)
            status = bx[0]["status"] if bx else ""
            if status in ("reverted", "reverts_earlier_beta"):
                e["stable_build"] = ""
            if status.startswith("not in a stable changelog"):
                status = "update-history only"
                e["fields"] += [{"field": f"history:{f}", "old": o, "new": n,
                                 "via": "update-history (beta_card_changes)"}
                                for x in bx for f, o, n in history_pairs(x["text"])]
            e["status"] = status
            if not rows:
                e["note"] = (e["note"] + "; " if e["note"] else "") + \
                    "no card_changes row (net zero over the window)"
            events.append(e)
    # --- betas after the last stable: beta_card_changes rows, one event per (card, version)
    for (card, v), bx in sorted(bcc.items(), key=lambda t: (vk(t[0][1]), t[0][0])):
        if not bx[0]["status"].startswith("after_last_stable"):
            continue
        hist = [history_pairs(x["text"]) for x in bx if x["source"] == "update-history"]
        curated = [x["change_kind"] for x in bx if x["change_kind"]]
        e = new_event(card, v, first_beta=v, timing="beta", status=bx[0]["status"],
                      change_kind=curated[0] if curated else notes_kind(bx, hist),
                      kind_source="beta_card_changes" if curated else "text rule",
                      source="beta_card_changes (" + ", ".join(sorted({x["source"] for x in bx}))
                             + ")")
        e["fields"] = notes_fields(bx) + [{"field": f"history:{f}", "old": o, "new": n,
                                           "via": "update-history (beta_card_changes)"}
                                          for t in hist for f, o, n in t]
        events.append(e)
    # --- behavior (bug-fix) events: sensitivity only, one per behavior_changes row
    seen = collections.Counter()
    for r in behavior:
        card, v = r["card_id"], r["version"]
        seen[(card, v)] += 1
        eid = f"{card}@{v}/fix{seen[(card, v)]}"
        if branch.get(v) == "stable":
            e = new_event(card, v, event_id=eid, timing="stable_only", stable_build=v,
                          window_stable=v)
        else:
            nxt = [s for s in stables if vk(s) > vk(v)]
            w = window_of(v) or ""
            e = new_event(card, v, event_id=eid, first_beta=v, timing="beta",
                          stable_build=w if w in nxt else "", window_stable=w)
        e.update(change_kind="behavior", kind_source="behavior", sensitivity_only="yes",
                 status=r["kind"], source="behavior_changes", note=r["text"])
        events.append(e)
    # A stable row with an earlier beta row of the same card that hadn't reached stable yet
    # is that fix's stable copy (e.g. Summon Forth: beta v0.104.0, stable v0.103.3 and
    # v0.107.1): betas already carry the beta row, so they don't carry the copy.
    date = {b["build_id"]: b["release_date"] for b in builds}
    beh = [e for e in events if e["change_kind"] == "behavior"]
    for e in beh:
        if e["timing"] != "stable_only":
            continue
        src = [x for x in beh if x["card_id"] == e["card_id"] and x["timing"] == "beta"
               and date[x["first_beta"]] <= date[e["event_build"]]
               and (not x["window_stable"] or vk(x["window_stable"]) >= vk(e["event_build"]))]
        if src:
            e["beta_copy_of"] = " ".join(x["event_id"] for x in src)
            e["note"] = f"stable copy of {e['beta_copy_of']}: " + e["note"]
            for x in src:
                x["note"] = f"stable copy {e['event_id']}; " + x["note"]
    events.sort(key=lambda e: (vk(e["event_build"]), e["card_id"], e["event_id"]))
    ids = [e["event_id"] for e in events]
    assert len(ids) == len(set(ids)), [i for i, n in collections.Counter(ids).items() if n > 1]
    return events


# ------------------------------------------------------------------------ carrying

def carries(e, build, info):
    """True / False / None (unknown) for whether `build` carries event `e`.
    info: build_id -> (branch, release_date)."""
    br, date = info[build]
    if not br or build.endswith("-beta"):
        return None
    if e["timing"] == "beta":
        if br == "beta":
            return vk(build) >= vk(e["first_beta"])
        return bool(e["window_stable"]) and vk(build) >= vk(e["window_stable"])
    s = e["window_stable"]
    if br == "stable":
        return vk(build) >= vk(s)
    if e.get("beta_copy_of"):
        return False                  # betas carry the beta row this copies
    if vk(build) > vk(s) and date >= info[s][1]:
        return True
    if e["timing"] == "stable_only":
        # stable-only: betas before the stable in version never had it; a later version
        # released before the stable date is unknown
        return False if vk(build) < vk(s) else None
    # timing unknown: any beta of the window may or may not have carried it
    prev = [b for b, (bb, _) in info.items() if bb == "stable" and vk(b) < vk(s)]
    lo = max((vk(b) for b in prev), default=(0, 0, 0))
    return False if vk(build) <= lo else None


def build_info(builds):
    return {b["build_id"]: (b["branch"], b["release_date"]) for b in builds}


def card_versions(events, builds, cards):
    """Rows of card_versions.csv and {(card, build): (set of card events or None,
    set of behavior events, set of unknown behavior events)}."""
    info = build_info(builds)
    by_card = collections.defaultdict(list)
    for e in events:
        by_card[e["card_id"]].append(e)
    chron = sorted((b for b, (br, _) in info.items() if br and not b.endswith("-beta")),
                   key=lambda b: (info[b][1] or "9999", vk(b)))
    order = {b: i for i, b in enumerate(chron)}
    all_builds = sorted(info, key=lambda b: vkey(b))
    rows, state = [], {}
    for card in sorted(set(cards) | set(by_card)):
        evs = by_card.get(card, [])
        index = {}
        per_build = {}
        for b in chron:
            card_set, beh, unknown, beh_unknown = [], [], [], []
            for e in evs:
                c = carries(e, b, info)
                sens = e["sensitivity_only"] == "yes"
                if c is None:
                    (beh_unknown if sens else unknown).append(e["event_id"])
                elif c:
                    (beh if sens else card_set).append(e["event_id"])
            per_build[b] = (card_set, beh, unknown, beh_unknown)
            if not unknown:
                index.setdefault(frozenset(card_set), len(index))
        for b in all_builds:
            br, date = info[b]
            note = ""
            if b not in order:
                note = ("update-history pseudo-version, not a run build (decision log)"
                        if b.endswith("-beta") else "branch unknown")
                rows.append({"card_id": card, "build_id": b, "branch": br, "release_date": date,
                             "version": "", "event_ids": "", "behavior_event_ids": "",
                             "note": note})
                state[(card, b)] = (None, set(), set())
                continue
            card_set, beh, unknown, beh_unknown = per_build[b]
            if unknown:
                note = "version unknown: may carry " + " ".join(unknown)
            if beh_unknown:
                note += ("; " if note else "") + "may carry behavior " + " ".join(beh_unknown)
            rows.append({"card_id": card, "build_id": b, "branch": br, "release_date": date,
                         "version": "" if unknown else index[frozenset(card_set)],
                         "event_ids": " ".join(card_set), "behavior_event_ids": " ".join(beh),
                         "note": note})
            state[(card, b)] = (None if unknown else set(card_set), set(beh), set(beh_unknown))
    return rows, state


# ---------------------------------------------------------------------------- checks

def compose(evs):
    """Net {field: (old, new)} over events in order, plus continuity problems."""
    net, problems = {}, []
    for e in evs:
        for f in e["fields"]:
            name = f["field"]
            if name.startswith(("notes:", "history:")):
                continue
            if name in net:
                cur = net[name][1]
                if UNRESOLVED not in (cur, f["old"]) and cur != f["old"]:
                    problems.append(f"{e['event_id']} {name}: starts at {f['old']} but the "
                                    f"previous event left {cur}")
                net[name] = (net[name][0], f["new"])
            else:
                net[name] = (f["old"], f["new"])
    return net, problems


def stable_check(events, builds, changes):
    """For each stable build whose changelog is a game release: the card events it carries
    beyond the previous stable, composed in order, must give card_changes' old -> new for
    every field. Returns a list of mismatch strings (empty = pass)."""
    info = build_info(builds)
    stables = sorted({r["stable_build"] for r in changes}, key=vk)
    all_stables = sorted((b for b, (br, _) in info.items() if br == "stable"), key=vk)
    want = collections.defaultdict(dict)
    for r in changes:
        if r["change_kind"] != "artifact":
            want[(r["card_id"], r["stable_build"])][r["field"]] = (r["old"], r["new"])
    card_events = [e for e in events if e["sensitivity_only"] != "yes"]
    out = []
    for s in stables:
        prev = [b for b in all_stables if vk(b) < vk(s)]
        p = prev[-1] if prev else None
        by_card = collections.defaultdict(list)
        for e in card_events:
            if carries(e, s, info) and not (p and carries(e, p, info)):
                by_card[e["card_id"]].append(e)
        cards = set(by_card) | {c for c, st in want if st == s}
        for card in sorted(cards):
            evs = sorted(by_card.get(card, []), key=lambda e: vk(e["event_build"]))
            net, problems = compose(evs)
            out += [f"{s} {card}: {x}" for x in problems]
            got = {f: on for f, on in net.items() if on[0] != on[1]}
            exp = want.get((card, s), {})
            for f in sorted(set(got) | set(exp)):
                if f not in exp:
                    out.append(f"{s} {card} {f}: events give {got[f][0]} -> {got[f][1]}, "
                               "not in card_changes")
                elif f not in net:
                    out.append(f"{s} {card} {f}: card_changes {exp[f][0]} -> {exp[f][1]}, "
                               "no event carries it")
                elif net[f] != exp[f]:
                    out.append(f"{s} {card} {f}: events give {net[f][0]} -> {net[f][1]}, "
                               f"card_changes {exp[f][0]} -> {exp[f][1]}")
    return out


# --------------------------------------------------------------------------- windows

def blocks(branch_builds, state, cards):
    """Consecutive same-branch builds -> blocks: a thin build joins a neighbour (the earlier
    one first) when every card's card-event set is the same on both."""
    def same(a, b):
        return all(state[(c, a)][0] == state[(c, b)][0] for c in cards)
    out = [[b] for b in branch_builds]
    for t in THIN_BUILDS:
        i = next((i for i, blk in enumerate(out) if t in blk), None)
        if i is None or len(out[i]) > 1:
            continue
        if i > 0 and not NO_WINDOW_BUILDS & set(out[i - 1]) and same(out[i - 1][-1], t):
            out[i - 1] += out.pop(i)
        elif i + 1 < len(out) and same(t, out[i + 1][0]):
            out[i] += out.pop(i + 1)
    return out


def card_patches(events, changes):
    """One unit per card_changes card-patch (card, stable build; artifacts left out): its
    member events are the card's card change events in that stable window."""
    kinds = {}
    for r in changes:
        if r["change_kind"] != "artifact":
            kinds[(r["card_id"], r["stable_build"])] = r["change_kind"]
    out = []
    for (card, stable), kind in sorted(kinds.items(), key=lambda t: (vk(t[0][1]), t[0][0])):
        members = [e for e in events if e["card_id"] == card and e["window_stable"] == stable
                   and e["sensitivity_only"] != "yes"]
        out.append({"id": f"{card}@{stable}/patch", "card": card, "change_kind": kind,
                    "level": "card_patch", "sens": False, "sort": stable, "branches": ("stable",),
                    "members": [e["event_id"] for e in members], "events": members})
    return out


def window_units(events, changes):
    units = [{"id": e["event_id"], "card": e["card_id"], "change_kind": e["change_kind"],
              "level": "event", "sens": e["sensitivity_only"] == "yes",
              "sort": e["event_build"], "branches": ("stable", "beta"),
              "members": [e["event_id"]], "events": [e]} for e in events]
    return units + card_patches(events, changes)


def windows(units, builds, state, cards, colors):
    """One row per (unit, branch) where the branch carries the unit: an event, or (stable
    branch only) a card-patch, i.e. all of a card's events in one stable window."""
    info = build_info(builds)
    card_list = sorted(cards)
    rows = []
    for br in ("stable", "beta"):
        seq = sorted((b for b, (x, _) in info.items() if x == br and not b.endswith("-beta")),
                     key=vk)
        blks = blocks(seq, state, card_list)

        def sets(card, blk, which):
            vals = [state[(card, b)][which] for b in blk]
            if which == 0 and any(v is None for v in vals):
                return None
            return set().union(*vals) if vals else set()

        for u in units:
            if br not in u["branches"]:
                continue
            card, members = u["card"], set(u["members"])

            def carried_by(b):
                cs = [carries(e, b, info) for e in u["events"]]
                return True if all(cs) else (False if not any(cs) else None)
            carried = [[carried_by(b) for b in blk] for blk in blks]
            first = next((i for i, cs in enumerate(carried) if any(cs)), None)
            if first is None:
                continue
            after = blks[first]
            before = blks[first - 1] if first > 0 else None
            row = {"level": u["level"], "event_id": u["id"], "card_id": card,
                   "change_kind": u["change_kind"],
                   "members": " ".join(u["members"]) if u["level"] == "card_patch" else "",
                   "branch": br, "before_builds": " ".join(before or []),
                   "after_builds": " ".join(after), "clean": "no", "reason": ""}
            if not all(carried[first]):
                row["reason"] = "not every build of the after block carries it"
            elif before is None:
                row["reason"] = "no earlier build on this branch"
            elif NO_WINDOW_BUILDS & set(before):
                excluded = " ".join(sorted(NO_WINDOW_BUILDS & set(before)))
                row["reason"] = f"before build {excluded} is in no window (decision log)"
            else:
                sb, sa = sets(card, before, 0), sets(card, after, 0)
                if sb is None or sa is None:
                    row["reason"] = "card version unknown on a build of the window"
                else:
                    if u["sens"]:
                        sb |= sets(card, before, 1)
                        sa |= sets(card, after, 1)
                    diff = (sa - sb) | (sb - sa)
                    if diff == members:
                        row["clean"], row["reason"] = "yes", ""
                    else:
                        others = sorted(diff - members)
                        row["reason"] = "the card also differs by " + " ".join(others)
            window_builds = (before or []) + after

            def fell(card_):
                """behavior events of a card that fall in the window"""
                if not before:
                    return set()
                start = state[(card_, window_builds[0])][1]
                out_ = set()
                for b in window_builds[1:]:
                    out_ |= state[(card_, b)][1] - start
                    out_ |= state[(card_, b)][2]
                return out_ - members
            beh = fell(card)
            row["behavior_in_window"] = "yes" if beh else "no"
            row["behavior_event_ids"] = " ".join(sorted(beh))
            if before:
                color = colors.get(card, "")
                excl, flags = [], []
                for c in card_list:
                    if c == card or colors.get(c, "") != color:
                        continue
                    sb, sa = sets(c, before, 0), sets(c, after, 0)
                    if sb is None or sa is None or sb != sa:
                        excl.append(c)
                    if fell(c):
                        flags.append(c)
                row["control_exclusions"] = " ".join(excl)
                row["control_behavior_flags"] = " ".join(flags)
            row["_sort"] = (vk(u["sort"]), card, u["level"] != "card_patch", u["id"],
                            br != "stable")
            rows.append(row)
    rows.sort(key=lambda r: r["_sort"])
    for r in rows:
        del r["_sort"]
    return rows


def patch_field_rows(changes, events):
    """Net old -> new per field for each card-patch, straight from card_changes.csv (the
    stable-window check verifies the events compose to these values)."""
    members = collections.defaultdict(list)
    for e in events:
        if e["sensitivity_only"] != "yes" and e["window_stable"]:
            members[(e["card_id"], e["window_stable"])].append(e["event_id"])
    out = []
    rows = [r for r in changes if r["change_kind"] != "artifact"]
    rows.sort(key=lambda r: (vk(r["stable_build"]), r["card_id"], r["field"]))
    for r in rows:
        key = (r["card_id"], r["stable_build"])
        out.append({"card_patch_id": f"{key[0]}@{key[1]}/patch", "card_id": key[0],
                    "stable_build": key[1], "change_kind": r["change_kind"],
                    "field": r["field"], "old": r["old"], "new": r["new"],
                    "rel_change": rel_change(r["old"], r["new"]),
                    "events": " ".join(members.get(key, []))})
    return out


# ----------------------------------------------------------------------------- build

def field_rows(events):
    out = []
    for e in events:
        for f in e["fields"]:
            out.append({"event_id": e["event_id"], "card_id": e["card_id"], "field": f["field"],
                        "old": f["old"], "new": f["new"],
                        "rel_change": rel_change(f["old"], f["new"]),
                        "via": f["via"]})
    return out


def summarize_fields(e):
    parts = []
    for f in e["fields"]:
        if f["field"] in ("description", "description_raw", "upgrade_description"):
            parts.append(f"{f['field']} (text)")
            continue
        rc = rel_change(f["old"], f["new"])
        parts.append(f"{f['field']} {f['old']} -> {f['new']}"
                     + (f" ({float(rc):+.1%})" if rc else ""))
    return "; ".join(parts)


def load_inputs(ref=REF):
    cards = json.loads((ref / "raw" / "cards.json").read_bytes())
    return dict(builds=read_csv(ref / "builds.csv"),
                changes=read_csv(ref / "card_changes.csv"),
                beta_changes=read_csv(ref / "beta_card_changes.csv"),
                behavior=read_csv(ref / "behavior_changes.csv"),
                notes=read_csv(ref / "patch_notes_cards.csv"),
                labels=read_csv(ref / "text_only_labels.csv"),
                attrs=card_attrs(cards))


def build_tables(builds, changes, beta_changes, behavior, notes, labels, attrs):
    events = build_events(builds, changes, beta_changes, behavior, notes, labels)
    colors = {c: a["color"] for c, a in attrs.items()}
    for r in changes:
        colors.setdefault(r["card_id"], r.get("color", ""))
    for e in events:
        e["color"] = colors.get(e["card_id"], "")
        e["field_changes"] = summarize_fields(e)
    cards = set(attrs) | {e["card_id"] for e in events}
    versions, state = card_versions(events, builds, cards)
    wins = windows(window_units(events, changes), builds, state, cards, colors)
    mismatches = stable_check(events, builds, changes)
    return events, versions, wins, mismatches


def report(events, wins, mismatches):
    print(f"\nstable-window check: {len(mismatches)} mismatch(es)")
    for m in mismatches:
        print("  " + m)
    clean = collections.defaultdict(dict)
    for w in wins:
        if w["level"] == "event":
            clean[w["event_id"]][w["branch"]] = w["clean"] == "yes"
    patches = [w for w in wins if w["level"] == "card_patch"]
    tweaks = [w for w in patches if w["change_kind"] == "tweak"]
    print(f"\ncard-patch stable windows: {sum(w['clean'] == 'yes' for w in patches)} of "
          f"{len(patches)} clean; numeric tweaks: "
          f"{sum(w['clean'] == 'yes' for w in tweaks)} of {len(tweaks)} clean")
    for w in patches:
        if w["clean"] != "yes":
            print(f"  not clean: {w['event_id']} ({w['change_kind']}): {w['reason']}")
    print("\nevents by kind: total | clean stable window | clean beta window | both | neither")
    by_kind = collections.defaultdict(list)
    for e in events:
        by_kind[e["change_kind"]].append(e["event_id"])
    for k in sorted(by_kind):
        ids = by_kind[k]
        s = sum(clean[i].get("stable", False) for i in ids)
        b = sum(clean[i].get("beta", False) for i in ids)
        both = sum(clean[i].get("stable", False) and clean[i].get("beta", False) for i in ids)
        none_ = sum(not any(clean[i].values()) for i in ids)
        print(f"  {k:28s} {len(ids):4d} | {s:4d} | {b:4d} | {both:4d} | {none_:4d}")
    unresolved = sorted({e["event_id"] for e in events for f in e["fields"]
                         if UNRESOLVED in (f["old"], f["new"])})
    unknown = [e["event_id"] for e in events if e["timing"] == "unknown"]
    print(f"\nfields split over betas without a resolving note ({len(unresolved)} events): "
          + " ".join(unresolved))
    print(f"events with unknown beta timing ({len(unknown)}): " + " ".join(unknown))


def build(ref=REF):
    inputs = load_inputs(ref)
    events, versions, wins, mismatches = build_tables(**inputs)
    write_csv(ref / "change_events.csv", events, EVENT_COLS)
    write_csv(ref / "change_event_fields.csv", field_rows(events), FIELD_COLS)
    write_csv(ref / "card_versions.csv", versions, VERSION_COLS)
    write_csv(ref / "windows.csv", wins, WINDOW_COLS)
    write_csv(ref / "card_patch_fields.csv", patch_field_rows(inputs["changes"], events),
              PATCH_FIELD_COLS)
    report(events, wins, mismatches)
    return mismatches


if __name__ == "__main__":
    build()
