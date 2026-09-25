"""Cross-check the official patch notes against the card patch dataset.

Reads reference/patch_notes_cards.csv (from spirometry.patch_notes), card_changes.csv,
text_only_labels.csv and builds.csv, and writes:

    reference/crosscheck.csv        one row per (card, stable window): notes vs card_changes
    reference/behavior_changes.csv  bug-fix-only mentions that change how a card plays
    reference/beta_card_changes.csv card changes that never reached stable as written

text_only_labels.csv is hand-labeled and only read, never written.

Usage (from the repo root; run after `python -m spirometry.patch_notes build`):
    python -m spirometry.notes_crosscheck
"""
import collections, csv, pathlib, re

REF = pathlib.Path("reference")

# Stable windows: a change first seen on a beta after `lo` reaches stable at `stable`.
# Versions up to v0.99.1 are launch hotfixes; v0.103.3 is a stable bug-fix patch; versions
# after v0.107.1 have not reached stable (as of the notes cached here).
WINDOWS = [((0, 99, 1), (0, 103, 2), "v0.103.2"),
           ((0, 103, 2), (0, 107, 1), "v0.107.1")]
MAJOR_UPDATES = {"v0.103.2", "v0.107.1"}
CHANGE_SECTIONS = {"content", "balance", "content+balance"}
NOTE_SECTIONS = CHANGE_SECTIONS | {"writing"}

CC_FIELDS = ["card_id", "version", "stable_build", "notes_versions", "notes_sections",
             "notes_verbs", "in_notes", "in_card_changes", "change_kind", "text_only_label",
             "agreement", "detail"]
BEHAVIOR_FIELDS = ["card_id", "version", "branch", "date", "kind", "also_in_notes_as",
                   "in_card_changes", "text"]
BETA_FIELDS = ["card_id", "version", "branch", "date", "status", "verb", "quantity",
               "before_base", "before_upg", "after_base", "after_upg", "reached_stable_as",
               "source", "text"]


def vt(v):
    return tuple(int(x) for x in v.lstrip("v").split("-")[0].split("."))


def window_of(version):
    """Stable build a note's version rolls into, or '' (hotfix, stable patch, or beta-only)."""
    t = vt(version)
    for lo, hi, stable in WINDOWS:
        if lo < t <= hi and version != "v0.103.3":
            return stable
    return ""


def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {path} ({len(rows)} rows)")


def num(s):
    s = str(s).strip().lstrip("+").rstrip("%")
    if s in ("", "none"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def canon(q):
    """Quantity as written -> a key for chaining ('Energy cost' and 'cost' are the same)."""
    q = re.sub(r"\b(gain|base|upgraded|the|of|self-|but|and|while)\b", " ", q.lower())
    q = re.sub(r"\s+", " ", q).strip()
    if "star cost" in q:
        return "star cost"
    if "cost" in q:
        return "cost"
    return q


def net_changes(clauses):
    """Chain numeric clauses (in version order) per quantity: [(q, b0, u0, b1, u1)]."""
    chains = collections.OrderedDict()
    for c in clauses:
        key = canon(c["quantity"])
        b0, u0, b1, u1 = c["before_base"], c["before_upg"], c["after_base"], c["after_upg"]
        if key in chains and num(chains[key][2]) == num(b0):
            chains[key] = (chains[key][0], chains[key][1], b1, u1)
        else:
            chains[key if key not in chains else f"{key}#{len(chains)}"] = (b0, u0, b1, u1)
    return [(k.split("#")[0],) + v for k, v in chains.items()]


def upgraded_totals(card, cc_rows):
    """{field: (old total, new total)} for upgrade.X deltas, using the card's current base X
    from the card list (for notes that quote the upgraded card, e.g. 'Tesla Coil+ card')."""
    out = {}
    base = CARD_BASE.get(card, {})
    for r in cc_rows:
        if r["field"].startswith("upgrade."):
            x = r["field"].split(".", 1)[1].lower()
            b = base.get(x)
            if b is not None and num(r["old"]) is not None and num(r["new"]) is not None:
                out[r["field"]] = (b + num(r["old"]), b + num(r["new"]))
    return out


def compare_numbers(nets, cc_rows, card=""):
    """(verdict, detail) for the notes' net numeric changes against card_changes rows."""
    base = [(r["field"], num(r["old"]), num(r["new"])) for r in cc_rows
            if not r["field"].startswith("upgrade.") and r["field"] != "(card)"]
    upg = [(r["field"], r["old"], r["new"]) for r in cc_rows if r["field"].startswith("upgrade.")]
    totals = upgraded_totals(card, cc_rows)
    verdicts, details = [], []
    for q, b0, u0, b1, u1 in nets:
        nb0, nb1 = num(b0), num(b1)
        label = f"{q} {b0}{f'({u0})' if u0 else ''} -> {b1}{f'({u1})' if u1 else ''}"
        if nb0 is None or nb1 is None:
            continue
        if b0.startswith("+") or b1.startswith("+"):
            # an upgrade delta as written ("upgraded Block gain +2 -> +3")
            got = [f for f, o, n in upg if (num(o) or 0) == nb0 and (num(n) or 0) == nb1]
            verdicts.append("match" if got else "missing")
            details.append(f"{label}: " + (f"matches {got[0]}" if got else
                                           "no upgrade field in card_changes moves this way"))
            continue
        if nb0 == nb1:
            verdicts.append("match")
            details.append(f"{label}: base unchanged")
        else:
            exact = [f for f, o, n in base if o == nb0 and n == nb1]
            same = [f for f, o, n in base if o is not None and n is not None
                    and (n - o) * (nb1 - nb0) > 0]
            opp = [f for f, o, n in base if o is not None and n is not None
                   and (n - o) * (nb1 - nb0) < 0]
            upg_exact = [f for f, (o, n) in totals.items() if (o, n) == (nb0, nb1)]
            if "upgrade" in q:
                # "now upgrades from 2 -> 3": the upgrade's increment moved by the difference
                upg_exact += [f for f, o, n in upg if (num(n) or 0) - (num(o) or 0) == nb1 - nb0]
            if exact:
                verdicts.append("match")
                details.append(f"{label}: matches {exact[0]}")
            elif upg_exact:
                verdicts.append("match")
                details.append(f"{label}: matches the upgraded card via {upg_exact[0]} "
                               f"(current base from the card list)")
            elif same:
                f = same[0]
                o, n = next((o, n) for g, o, n in base if g == f)
                verdicts.append("size")
                details.append(f"{label}: same direction as {f} {o:g} -> {n:g}, size differs")
            elif opp:
                f = opp[0]
                o, n = next((o, n) for g, o, n in base if g == f)
                verdicts.append("direction")
                details.append(f"{label}: opposite direction to {f} {o:g} -> {n:g}")
            else:
                verdicts.append("missing")
                details.append(f"{label}: no card_changes field moves this way")
        # Upgraded value: notes give totals, card_changes gives upgrade deltas (costs absolute).
        if u0 and u1:
            if q in ("cost", "star cost"):
                want = (num(u0), num(u1))
                got = [f for f, o, n in upg if (num(o), num(n)) == want]
                changed = num(u0) != num(u1) or num(u0) != nb0
            else:
                d0, d1 = num(u0) - nb0, num(u1) - nb1
                changed = d0 != d1
                got = [f for f, o, n in upg if (num(o) or 0) == d0 and (num(n) or 0) == d1]
            if changed and not got:
                verdicts.append("upgrade")
                details.append(f"{label}: upgraded value change not in card_changes")
    if not verdicts:
        return "", ""
    order = ["direction", "missing", "size", "upgrade", "match"]
    worst = min(verdicts, key=order.index)
    return worst, "; ".join(details)


VERDICT_TEXT = {
    "match": "agree: numbers match",
    "size": "disagree: size",
    "direction": "disagree: direction",
    "missing": "disagree: notes number not in card_changes",
    "upgrade": "disagree: upgrade value",
}


NON_NUMERIC_CUE = re.compile(r"\b(now|no longer|instead|twice|once|innate|ethereal|exhausts?|"
                             r"retain|evokes?|triggers?|draws? cards immediately)\b", re.I)


def non_numeric_clauses(note_row):
    """Clauses of a note that describe a change without numbers ("now Exhausts",
    "Lightning triggers once -> twice"), or the whole note if its verb is Reworked."""
    from spirometry.patch_notes import CHANGE_RE
    text = note_row["raw_text"]
    if note_row["verb"].startswith("Reworked"):
        return [f"{note_row['version']} Reworked"]
    body = text.split(":", 1)[1] if ":" in text else text
    out = []
    for clause in re.split(r"\s\*\s|;|, but |\. | and (?=no longer|now)", body):
        clause = clause.strip(" *.")
        if clause and not CHANGE_RE.search(clause) and NON_NUMERIC_CUE.search(clause):
            out.append(f"{note_row['version']} '{clause}'")
    return out


def crosscheck(notes, changes, labels):
    bugfix = collections.defaultdict(list)
    for r in notes:
        if r["role"] == "subject" and r["section"] == "bug fix" and window_of(r["version"]):
            bugfix[(r["card_id"], window_of(r["version"]))].append(r)
    notes = [r for r in notes if r["role"] == "subject" and r["section"] in NOTE_SECTIONS]
    by_card_window = collections.defaultdict(list)
    for r in notes:
        w = window_of(r["version"])
        if w:
            by_card_window[(r["card_id"], w)].append(r)
    cc = collections.defaultdict(list)
    for r in changes:
        cc[(r["card_id"], r["stable_build"])].append(r)
    lab = {(r["card_id"], r["stable_build"]): r["label"] for r in labels}

    out = []
    for key in sorted(set(by_card_window) | set(cc), key=lambda k: (k[1], k[0])):
        card, stable = key
        nrows = sorted(by_card_window.get(key, []), key=lambda r: vt(r["version"]))
        crows = cc.get(key, [])
        kind = crows[0]["change_kind"] if crows else ""
        label = lab.get(key, "")
        versions = list(dict.fromkeys(r["version"] for r in nrows))
        sections = sorted({r["section"] for r in nrows})
        verbs = list(dict.fromkeys(r["verb"] for r in nrows if r["verb"]))
        change_notes = [r for r in nrows if r["section"] in CHANGE_SECTIONS]
        betas = sorted({r["beta_build"] for r in crows if r["beta_build"]}, key=vt)
        version = (betas or [v for v in versions if v not in MAJOR_UPDATES] or versions
                   or [""])[0]
        row = {"card_id": card, "version": version, "stable_build": stable,
               "notes_versions": " ".join(versions), "notes_sections": " ".join(sections),
               "notes_verbs": " ".join(verbs), "in_notes": "yes" if nrows else "no",
               "in_card_changes": "yes" if crows else "no", "change_kind": kind,
               "text_only_label": label}
        if any(r["wiki_only"] for r in nrows):
            row["in_notes"] = "wiki only"
        # Numbers from before a rework or revert in this window don't describe what reached
        # stable; compare only what comes after the last one.
        resets = [vt(r["version"]) for r in change_notes if r["version"] not in MAJOR_UPDATES
                  and re.match(r"(Reworked|Reverted)", r["verb"])]
        numbered = [r for r in change_notes if r["before_base"] and
                    (r["version"] in MAJOR_UPDATES or not resets or vt(r["version"]) >= max(resets))]
        # Prefer the major update's summary numbers (net over the window) when it has them.
        summary = [r for r in numbered if r["version"] in MAJOR_UPDATES]
        clauses = summary or [r for r in numbered if r["version"] not in MAJOR_UPDATES]
        nets = net_changes(clauses)

        if nrows and not crows:
            reverted = (any(r["verb"].startswith("Reverted") for r in nrows) or
                        (nets and all(num(b0) == num(b1) and (u0 or "") == (u1 or "")
                                      for _, b0, u0, b1, u1 in nets)))
            if not change_notes:
                agreement, detail = "notes only: writing", "wording change the tables don't have"
            elif reverted:
                agreement, detail = "notes only: reverted within beta", "net change is zero"
            else:
                agreement = "notes only: missing from card_changes"
                detail = "; ".join(f"{canon(q)} {b0}({u0}) -> {b1}({u1})"
                                   for q, b0, u0, b1, u1 in nets) or "no numbers in the notes"
        elif crows and not nrows:
            agreement, detail = "table only", "no mention in the patch notes for this window"
            fixes = sorted({r["version"] for r in bugfix.get(key, [])}, key=vt)
            if fixes:
                detail = "mentioned only in bug fixes: " + " ".join(fixes)
        else:
            verdict, detail = compare_numbers(nets, crows, card)
            if verdict:
                agreement = VERDICT_TEXT[verdict]
            elif change_notes:
                agreement, detail = "agree: no numbers to compare", "; ".join(verbs)
            else:
                agreement, detail = "agree: writing note", "only in the writing section"
        # A numeric tweak in the table, but the notes also describe a non-numeric change
        # (a rework, a new keyword, a changed trigger): the tweak label may be wrong.
        if kind in ("tweak", "tweak+cost_change") and change_notes:
            extra = [c for r in change_notes for c in non_numeric_clauses(r)]
            if extra:
                agreement = "disagree: kind; " + agreement
                detail = (f"table says {kind}, notes also say: " + " | ".join(
                    dict.fromkeys(extra)) + "; " + detail).strip("; ")
        # text_only hand labels vs where the notes put the change
        if label and nrows:
            expect = "wording" if not change_notes else "mechanic"
            if label != "exclude" and label != expect:
                agreement += f"; label {label} but notes list it under " + \
                             ("writing" if expect == "wording" else "/".join(
                                 sorted({r['section'] for r in change_notes})))
        row.update(agreement=agreement, detail=detail)
        out.append(row)
    return out


# ------------------------------------------------------------------ behavior changes

NOT_BEHAVIOR = re.compile(r"crash|softlock|hovertip|tooltip|visual|animation|vfx|sfx|"
                          r"\bart\b|translation|localiz|wording|typo|description|text|"
                          r"preview|display|showing|shown|icon|controller|state divergence|"
                          r"desync|error|log\b|portrait|inspection|hotkey|screen|sound|"
                          r"music|audio|blackscreen|\bui\b", re.I)


def behavior_changes(notes, changes):
    """Bug-fix mentions of a card that read as a gameplay change (timing, generation,
    interactions), not a crash, UI or text fix. A keyword heuristic, so a candidate list:
    'kind' says what the fix touches; check the text before using a row."""
    change_mentions = {(r["card_id"], r["version"]) for r in notes
                       if r["section"] in CHANGE_SECTIONS and r["role"] == "subject"}
    cc_cards = {(r["card_id"], r["stable_build"]) for r in changes}
    out, seen = [], set()
    for r in notes:
        if r["section"] != "bug fix" or r["role"] != "subject":
            continue
        text = r["raw_text"]
        if NOT_BEHAVIOR.search(text):
            continue
        if not re.search(r"\bno longer\b|\bnow\b|\bproperly\b|\bcorrectly\b|\balways\b|"
                         r"\bnever\b|\binstead\b|\bbefore\b|\bafter\b", text, re.I):
            continue
        if re.search(r"\bgenerated\b", text, re.I):
            kind = "generation"          # which effects can create the card mid-combat
        elif re.search(r"\bplayers?\b|\bmultiplayer\b|\brecipient\b", text, re.I):
            kind = "multiplayer"
        elif re.search(r"\b(relic|enchant\w*|event|potion|affliction|curse|quest)\b", text, re.I):
            kind = "interaction"         # with a relic, enchantment, event, ...
        elif re.search(r"\b(before|after|until|immediately|timing|order)\b", text, re.I):
            kind = "timing"
        else:
            kind = "rule"
        key = (r["card_id"], r["version"], text)
        if key in seen:
            continue
        seen.add(key)
        w = window_of(r["version"])
        out.append({"card_id": r["card_id"], "version": r["version"], "branch": r["branch"],
                    "date": r["date"], "kind": kind,
                    "also_in_notes_as": "content/balance" if (r["card_id"], r["version"])
                    in change_mentions else "",
                    "in_card_changes": "yes" if (r["card_id"], w) in cc_cards else "no",
                    "text": text})
    return sorted(out, key=lambda r: (vt(r["version"]), r["card_id"]))


# ------------------------------------------------------------------ beta-only changes

def beta_card_changes(notes, crosscheck_rows):
    """Card changes in beta notes that never reached stable as written:

    - after_last_stable: any content/balance change on a beta after v0.107.1;
    - reverted: a change later reverted within the same window (net zero or 'Reverted');
    - revised: a change whose numbers were changed again before stable (the stable value
      differs from this beta's 'after');
    - beta_only_card: cards that existed only on beta (e.g. Prepare in v0.100.0).
    """
    rows = [r for r in notes if r["section"] in CHANGE_SECTIONS and r["role"] == "subject"
            and r["version"] not in MAJOR_UPDATES and r["branch"] == "beta"]
    status_of = {(r["card_id"], r["stable_build"]): r["agreement"] for r in crosscheck_rows}
    by_card_window = collections.defaultdict(list)
    for r in rows:
        by_card_window[(r["card_id"], window_of(r["version"]))].append(r)
    out = []
    for (card, w), rs in by_card_window.items():
        rs.sort(key=lambda r: vt(r["version"]))
        versions = list(dict.fromkeys(r["version"] for r in rs))
        for r in rs:
            status, stable_as = "", ""
            if not w:
                status = "after_last_stable"
            elif r["in_card_list"] == "no":
                status = "beta_only_card"
            elif status_of.get((card, w), "").startswith("notes only: reverted"):
                status = "reverted"
            elif r["verb"].startswith("Reverted"):
                status = "reverts_earlier_beta"
            elif len(versions) > 1 and r["version"] != versions[-1]:
                later = [x for x in rs if vt(x["version"]) > vt(r["version"])]
                if r["before_base"] and any(canon(x["quantity"]) == canon(r["quantity"])
                                            and x["before_base"] for x in later):
                    status = "revised"
                    last = [x for x in later if canon(x["quantity"]) == canon(r["quantity"])][-1]
                    stable_as = f"{last['after_base']}({last['after_upg']})" if last[
                        "after_upg"] else last["after_base"]
                elif any(x["verb"].startswith("Reverted") for x in later):
                    status = "reverted"
            if not status:
                continue
            if status == "after_last_stable":
                later = [x for x in rs if vt(x["version"]) > vt(r["version"])
                         and re.search(r"\brevert", x["raw_text"], re.I)]
                if later:
                    status += f"; reverted in {later[0]['version']}"
            out.append({"card_id": card, "version": r["version"], "branch": r["branch"],
                        "date": r["date"], "status": status, "verb": r["verb"],
                        "quantity": r["quantity"], "before_base": r["before_base"],
                        "before_upg": r["before_upg"], "after_base": r["after_base"],
                        "after_upg": r["after_upg"], "reached_stable_as": stable_as,
                        "source": "patch notes", "text": r["raw_text"]})
    return sorted(out, key=lambda r: (vt(r["version"]), r["card_id"], r["quantity"]))


# update-history labels that aren't gameplay (text, parser fields, images)
HISTORY_NOISE = re.compile(r"^(description|upgrade description|can be generated in combat|"
                           r"type variants|image url|rarity key|type key|keywords key|"
                           r"powers applied\[\d+\]\.power key|compendium order)", re.I)


def history_beta_rows(histories, unmatched, notes_rows):
    """Beta card changes from Spire Codex update-history that the notes rows don't cover:
    every gameplay entry after v0.107.1, and history_unmatched entries within a window
    (changes no stable changelog explains: reverted before stable, or parser changes)."""
    have = {(r["card_id"], r["version"]) for r in notes_rows}
    out = []
    last = vt(WINDOWS[-1][2])
    for card, entries in histories.items():
        for e in entries:
            v = e["version"].lower()
            if "-" in v or vt(v) <= last or (card, v) in have:
                continue
            changes = [c for c in e["changes"] if not HISTORY_NOISE.match(c)]
            if changes:
                out.append({"card_id": card, "version": v, "branch": "beta", "date": e["date"],
                            "status": "after_last_stable", "source": "update-history",
                            "text": "; ".join(changes)})
    for u in unmatched:
        v = u["version"]
        fields = [f for f in u["fields"].split("|") if not HISTORY_NOISE.match(f)]
        if "-" in v or not fields or (u["card_id"], v) in have:
            continue
        entry = next((e for e in histories.get(u["card_id"], [])
                      if e["version"].lower() == v), {})
        text = "; ".join(c for c in entry.get("changes", []) if not HISTORY_NOISE.match(c))
        out.append({"card_id": u["card_id"], "version": v, "branch": "", "date": u["date"],
                    "status": "not in a stable changelog (reverted before stable, or parser)",
                    "source": "update-history (history_unmatched.csv)", "text": text})
    return out


def load_histories(ref=REF):
    import json
    out = {}
    for p in sorted((ref / "raw" / "update_history" / "cards").glob("*.json")):
        h = json.loads(p.read_bytes())
        out[p.stem] = h if isinstance(h, list) else []
    return out


def load_card_base(ref=REF):
    """card_id -> {lowercased value name: current base value} from the cached card list."""
    import json
    out = {}
    for c in json.loads((ref / "raw" / "cards.json").read_bytes()):
        vals = {k: c[k] for k in ("damage", "block") if isinstance(c.get(k), (int, float))}
        for k, v in (c.get("vars") or {}).items():
            if isinstance(v, (int, float)):
                vals.setdefault(k.lower(), v)
        out[c["id"]] = vals
    return out


CARD_BASE = {}


def build():
    CARD_BASE.update(load_card_base())
    notes = read_csv(REF / "patch_notes_cards.csv")
    changes = read_csv(REF / "card_changes.csv")
    labels = read_csv(REF / "text_only_labels.csv")
    rows = crosscheck(notes, changes, labels)
    write_csv(REF / "crosscheck.csv", rows, CC_FIELDS)
    write_csv(REF / "behavior_changes.csv", behavior_changes(notes, changes), BEHAVIOR_FIELDS)
    beta = beta_card_changes(notes, rows)
    beta += history_beta_rows(load_histories(), read_csv(REF / "history_unmatched.csv"),
                              [r for r in notes if r["role"] == "subject"])
    beta.sort(key=lambda r: (vt(r["version"]), r["card_id"], r.get("quantity", "")))
    write_csv(REF / "beta_card_changes.csv", beta, BETA_FIELDS)


if __name__ == "__main__":
    build()
