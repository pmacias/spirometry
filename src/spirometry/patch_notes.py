"""Card mentions in Mega Crit's official patch notes, as mirrored on the Slay the Spire wiki.

Fetches the wiki's patch-note index and every early-access patch page (V0.98.1-V0.111.0)
as raw wikitext, caching them under reference/raw/wiki/ (reruns read the cache), then
builds from the cache alone:

    reference/patch_notes_cards.csv   one row per card mention (and per numeric change in it)
    reference/builds.csv              reconciled in place with the wiki's version list
    crosscheck / behavior_changes / beta_card_changes CSVs, via spirometry.notes_crosscheck

The wiki text is CC BY-SA 4.0 (see reference/raw/wiki/README.md).

Usage (from the repo root):
    python -m spirometry.patch_notes            # fetch what's missing, then build
    python -m spirometry.patch_notes fetch      # only fetch into the cache
    python -m spirometry.patch_notes build      # only build from the cache
"""
import argparse, collections, csv, json, pathlib, re, time
import requests

WIKI = "https://slaythespire.wiki.gg/wiki"
INDEX_TITLE = "Slay_the_Spire_2:Patch_Notes"
REF = pathlib.Path("reference")
WIKI_RAW = REF / "raw" / "wiki"
MIN_INTERVAL = 6.0          # seconds between requests: at most 10 per minute
HEADERS = {"User-Agent": "spirometry-research/0.1 (github.com/pmacias/spirometry)"}
# Early-access pages only: V0.98.1 (first post-launch hotfix) through V0.111.0.
FIRST, LAST = (0, 98, 1), (0, 111, 0)

# Verbs recorded as written when an item starts with one. The first six are the patch
# notes' usual ones; Removed / Reverted / Adjusted also occur and carry direction.
VERBS = ["Buffed", "Nerfed", "Changed", "Reworked", "Added", "Deprecated", "Removed",
         "Reverted", "Adjusted"]
# Level-2 headings -> section. Anything else keeps its own (lowercased) name.
SECTIONS = {"content": "content", "balance": "balance", "content & balance": "content+balance",
            "content and balance": "content+balance",
            "writing": "writing", "bug fixes": "bug fix"}
# Subsections where a plain (unmarked) card name counts as a card mention.
CARD_SUBSECTIONS = {"ironclad", "silent", "regent", "necrobinder", "defect", "colorless",
                    "colorless cards", "multiplayer", "characters", "reworks and reverts"}
CHARACTERS = {"ironclad", "silent", "regent", "necrobinder", "defect"}
# Words after a name that say it's not the card (relic, power, ... of the same name).
NOT_CARD_AFTER = re.compile(r"\s*(relic|relics|potion|potions|power|powers|event|events|"
                            r"enchantment|encounter|affliction|blessing|orb|orbs|badge|"
                            r"modifier|move|buff|debuff|status effect|keyword|monster|"
                            r"enemy|boss|ascension)\b", re.I)
# "X card" / "X cards", but not "X card view screen" (Pandora's Box relic UI).
SAYS_CARD = re.compile(r"\s*(?:status\s+|curse\s+)?cards?\b(?!\s+(view|screen|selection|preview|inspection))", re.I)
# Names in the notes that differ from the card list, with the evidence.
ALIASES = {
    # v0.101.0 "Spoils of War ... Forge decreased from 12(17)": Spoils of Battle's Forge was
    # 12(17) after v0.100.0, and no card is called Spoils of War.
    "Spoils of War": "SPOILS_OF_BATTLE",
    # v0.107.0 writes "Sealed Throne", v0.108.0 links {{C2|The Sealed Throne}}; same change.
    "Sealed Throne": "THE_SEALED_THRONE",
}

NUM = r"(\+?\d+(?:\.\d+)?%?)(?:\((\+?\d+(?:\.\d+)?%?)\))?(?:x\d+)?"
# A unit word may sit between a value and the arrow if it repeats after the new value
# ("8(10) Block -> 8(11) Block"), but not "+2 damage -> 1 additional hit".
CHANGE_RE = re.compile(r"(?<![\w.)\-–(])" + NUM + r"(?:\s+(?P<unit>[A-Za-z]+))?\s*"
                       r"(?:->|→|=>|\bto\b)\s*" + NUM + r"(?(unit)\s+(?P=unit)\b|(?![\w(\-–]))")
FILLER = re.compile(r"\b(increased|decreased|lowered|raised|reduced|changed|moved|goes|went|"
                    r"from|is|are|now|by|at|all|base values?)\b", re.I)

_last_request = 0.0


# ------------------------------------------------------------------------------ fetch

def page_path(title):
    return WIKI_RAW / f"{title.replace(':', '__')}.wikitext"


def get_raw(title):
    """Raw wikitext of a wiki page, from the cache if present, else fetched and saved."""
    global _last_request
    path = page_path(title)
    if path.exists():
        return path.read_text()
    while True:
        wait = _last_request + MIN_INTERVAL - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _last_request = time.monotonic()
        r = requests.get(f"{WIKI}/{title}", params={"action": "raw"}, headers=HEADERS,
                         timeout=60)
        if r.status_code == 429:
            time.sleep(int(r.headers.get("Retry-After", 60)))
            continue
        r.raise_for_status()
        break
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(r.text)
    return r.text


def version_tuple(v):
    return tuple(int(x) for x in v.lstrip("vV").split("-")[0].split("."))


def index_entries(index_text):
    """[(version, label, page title)] from the index's early-access list, newest first."""
    section = index_text.split("== During Early Access ==", 1)[1].split("==", 1)[0]
    out = []
    for name in re.findall(r"\{\{2\|([^}]+)\}\}", section):
        v, label = (s.strip() for s in name.split(" - ", 1))
        out.append((v.lower(), label, "Slay_the_Spire_2:" + name.strip().replace(" ", "_")))
    return out


def early_access_pages():
    entries = index_entries(get_raw(INDEX_TITLE))
    return [e for e in entries if FIRST <= version_tuple(e[0]) <= LAST]


def fetch():
    pages = early_access_pages()
    for v, label, title in pages:
        get_raw(title)
    print(f"{len(pages)} patch pages cached in {WIKI_RAW}")


# ------------------------------------------------------------------------------ parse

def card_id_for(name):
    """Spire Codex-style id from a display name: "Neow's Fury" -> NEOWS_FURY."""
    return re.sub(r"[^A-Z0-9]+", "_", name.upper().replace("'", "")).strip("_")


class CardNames:
    """Display name -> card ids, from the card list plus cards only changelogs know."""

    def __init__(self, cards, extra=()):
        self.ids = collections.defaultdict(list)
        for c in list(cards) + list(extra):
            if c["id"] not in self.ids[c["name"].lower()]:
                self.ids[c["name"].lower()].append(c["id"])
        self.known = {i for ids in self.ids.values() for i in ids}
        names = sorted(self.ids, key=len, reverse=True)
        self.pattern = re.compile(r"(?<![\w'])(" + "|".join(re.escape(n) for n in names) +
                                  r")(?![\w'])", re.I)

    def resolve(self, name, subsection=""):
        """(card_id, in_card_list) for a name as written; '' if it can't be one card."""
        base = name.rstrip("+").strip()
        if base in ALIASES:
            return ALIASES[base], True
        ids = self.ids.get(base.lower())
        if not ids and base.lower().endswith("s"):          # "Sovereign Blades"
            ids = self.ids.get(base.lower()[:-1])
        if not ids:
            cid = card_id_for(base)
            return cid, cid in self.known
        if len(ids) == 1:
            return ids[0], True
        # Strike / Defend: pick the character's version from the subsection.
        for i in ids:
            if subsection in CHARACTERS and i.endswith("_" + subsection.upper()):
                return i, True
        return "|".join(ids), True


def page_header(text):
    fields = dict(re.findall(r"^\|\s*(\w+)\s*=\s*(.*?)\s*$", text.split("}}", 1)[0], re.M))
    return fields.get("Version", "").lower(), fields.get("Type", ""), fields.get("ReleaseDate", "")


def branch_of(page_type):
    """Branch from the page's Type: 'Beta ...' is beta; Patch, Hotfix, Major Update are stable."""
    if not page_type:
        return ""
    return "beta" if page_type.lower().startswith("beta") else "stable"


def mark_up(line):
    """Wikitext -> plain text with card links as ⟪name⟫, bold as «text», other links as ⟦text⟧."""
    line = re.sub(r"\{\{C2\|([^|}]+)(?:\|[^}]*)?\}\}", r"⟪\1⟫", line)
    line = re.sub(r"\{\{\w+\|(?:[^|}]+\|)?([^|}]+)\}\}", r"⟦\1⟧", line)
    line = re.sub(r"\[\[(?:[^|\]]+\|)?([^\]]+)\]\]", r"\1", line)
    line = re.sub(r"'''((?:(?!''')[^|])+?)(?:\|(?:(?!''').)*)?'''", r"«\1»", line)
    return line.replace("''", "")


def plain(text):
    return re.sub(r"[⟪⟫«»⟦⟧]", "", text).strip()


def items(text):
    """Yield (section, subsection, top line, [sub lines]) for every bullet item on a page."""
    section, subsection, item = "intro", "", None
    for raw in text.splitlines():
        line = raw.strip()
        h = re.match(r"^(=+)\s*(.*?)\s*=+$", line)
        bold_head = re.match(r"^'''([^']+?):?'''$", line)
        if h or bold_head or not line.startswith("*"):
            if item:
                yield item
                item = None
            if h:
                name = h.group(2).rstrip(":").strip().lower()
                if len(h.group(1)) == 2 or name in SECTIONS:
                    section, subsection = SECTIONS.get(name, name), ""
                else:
                    subsection = name
            elif bold_head:
                subsection = bold_head.group(1).rstrip(":").strip().lower()
            continue
        depth = len(line) - len(line.lstrip("*"))
        body = line.lstrip("*").strip()
        if depth == 1 or item is None:
            if item:
                yield item
            item = (section, subsection, body, [])
        else:
            item[3].append(body)
    if item:
        yield item


def mentions(line, subsection, names):
    """[(name as written, start, end, strong)] card mentions in one marked-up line."""
    found, taken = [], []

    def free(a, b):
        return all(b <= s or a >= e for s, e in taken)

    for m in re.finditer(r"⟪([^⟫]+)⟫", line):
        found.append((m.group(1), m.start(), m.end(), True))
        taken.append(m.span())
    for m in re.finditer(r"⟦[^⟧]*⟧", line):
        taken.append(m.span())
    for m in re.finditer(r"«([^»]+)»", line):
        inner = m.group(1).strip()
        after = line[m.end():]
        says_card = SAYS_CARD.match(after) is not None
        if NOT_CARD_AFTER.match(after) and not says_card:
            taken.append(m.span())
            continue
        exact = names.pattern.fullmatch(inner.rstrip("+")) or inner.rstrip("+") in ALIASES
        listy = re.search(r"\b(the following|cards)\b", inner, re.I)
        # An unknown bold name counts if the text calls it a card, or if it's the object of
        # a verb in a character's section ("Reworked Prepared card into Prepare").
        verb_object = (subsection in CHARACTERS and
                       re.search(r"(\b(" + "|".join(VERBS) + r")|\binto|\band)\s*$",
                                 line[:m.start()]) is not None)
        if exact or (not listy and (says_card or verb_object)):
            found.append((inner, m.start(), m.end(), True))
            taken.append(m.span())
    for m in names.pattern.finditer(line):
        if not free(*m.span()) or not m.group(0)[0].isupper():
            continue
        after = line[m.end():].lstrip("+")
        if NOT_CARD_AFTER.match(after):
            continue
        if SAYS_CARD.match(after) or subsection in CARD_SUBSECTIONS:
            found.append((m.group(0), m.start(), m.end(), False))
            taken.append(m.span())
    for alias in ALIASES:
        for m in re.finditer(re.escape(alias), line):
            if free(*m.span()):
                found.append((alias, m.start(), m.end(), False))
                taken.append(m.span())
    return sorted(found, key=lambda t: t[1])


def subjects(line, found):
    """Which mentions are what the item is about: the first card named, plus any cards
    listed right after it ('X, Y, and Z cards'). Later ones are context ('... by Havoc')."""
    if not found:
        return []
    subj = [True] + [False] * (len(found) - 1)
    for k in range(1, len(found)):
        gap = plain(line[found[k - 1][2]:found[k][1]])
        if subj[k - 1] and re.fullmatch(r"\+?\s*(cards?)?\s*(,|and|, and|&|or|/)?\s*", gap):
            subj[k] = True
    return subj


def numeric_changes(text):
    """[(quantity, before_base, before_upg, after_base, after_upg)] from 'X from 7(9) -> 10(12)'."""
    text = re.sub(r'"[^"]*"', '""', plain(text))
    out, prev_end = [], 0
    for m in CHANGE_RE.finditer(text):
        seg = text[prev_end:m.start()]
        seg = re.split(r"[:;*•]|\. |, (?=[A-Za-z])", seg)[-1]
        quantity = re.sub(r"\s+", " ", FILLER.sub(" ", seg)).strip(" ,-").lower()
        out.append((quantity, m.group(1), m.group(2) or "", m.group(4), m.group(5) or ""))
        prev_end = m.end()
    return out


def verb_of(top):
    m = re.match(r"^(?:\(not mentioned in patch notes\)\s*)?(" + "|".join(VERBS) +
                 r")\b(\s*\((?:Buffed|Nerfed|Changed)\))?", plain(top))
    return (m.group(1) + (m.group(2) or "")).strip() if m else ""


PNC_FIELDS = ["version", "page_type", "branch", "date", "section", "subsection", "verb",
              "card_name", "card_id", "in_card_list", "role", "wiki_only", "change_n",
              "quantity", "before_base", "before_upg", "after_base", "after_upg", "raw_text"]


def parse_page(text, names):
    version, page_type, date = page_header(text)
    rows = []
    for section, subsection, top, subs in items(text):
        top_m = mark_up(top)
        found = mentions(top_m, subsection, names)
        line_for_subjects = top_m
        if not found:
            # e.g. "Added portrait art for the following cards:" with the cards as sub-bullets
            for s in subs:
                sm = mark_up(s)
                f = mentions(sm, subsection, names)
                found += [(n, 0, 0, strong) for n, _, _, strong in f]
            subj = [True] * len(found)
        else:
            subj = subjects(line_for_subjects, found)
        if not found:
            continue
        full = plain(mark_up(" ".join([top] + ["* " + s for s in subs])))
        changes = numeric_changes(" ; ".join([mark_up(top)] + [mark_up(s) for s in subs]))
        wiki_only = "not mentioned in patch notes" in top.lower()
        verb = verb_of(top_m)
        seen = set()
        for (name, _, _, _), is_subj in zip(found, subj):
            cid, in_list = names.resolve(name, subsection)
            if (cid, is_subj) in seen:
                continue
            seen.add((cid, is_subj))
            base = {"version": version, "page_type": page_type, "branch": branch_of(page_type),
                    "date": date, "section": section, "subsection": subsection, "verb": verb,
                    "card_name": name.rstrip("+").strip(), "card_id": cid,
                    "in_card_list": "yes" if in_list else "no",
                    "role": "subject" if is_subj else "context",
                    "wiki_only": "yes" if wiki_only else "", "change_n": "", "quantity": "",
                    "before_base": "", "before_upg": "", "after_base": "", "after_upg": "",
                    "raw_text": full}
            if is_subj and changes:
                for n, (q, bb, bu, ab, au) in enumerate(changes, 1):
                    rows.append({**base, "change_n": n, "quantity": q, "before_base": bb,
                                 "before_upg": bu, "after_base": ab, "after_upg": au})
            else:
                rows.append(base)
    return rows


def load_names(ref=REF):
    cards = json.loads((ref / "raw" / "cards.json").read_bytes())
    extra = []
    for p in sorted((ref / "raw" / "changelogs").glob("*.json")):
        for cat in json.loads(p.read_bytes()).get("categories", []):
            if cat["id"] == "cards":
                extra += [e for e in cat.get("removed", []) + cat.get("added", []) if "name" in e]
    return CardNames(cards, extra)


def cached_pages():
    """[(version, label, title, text)] for every cached early-access page, oldest first."""
    pages = early_access_pages()
    out = [(v, label, title, page_path(title).read_text()) for v, label, title in pages
           if page_path(title).exists()]
    missing = [t for _, _, t in pages if not page_path(t).exists()]
    assert not missing, f"not cached: {missing}; run fetch first"
    return sorted(out, key=lambda p: (version_tuple(p[0]), p[1]))


def build_mentions(pages, names):
    rows = []
    for v, label, title, text in pages:
        rows += parse_page(text, names)
    return rows


# ------------------------------------------------------------------------------ builds.csv

WIKI_SOURCE = "wiki patch notes"


def reconcile_builds(builds, pages):
    """Merge the wiki's version list into builds.csv rows (list of dicts), in place.

    Adds versions builds.csv lacks; fills blank branch / release_date from the wiki page
    header; records the wiki as a source; notes conflicts instead of overwriting. Earlier
    wiki additions are stripped first so rebuilding is idempotent.
    """
    rows = {}
    for r in builds:
        src = [s for s in r["source"].split("; ") if s and s != WIKI_SOURCE]
        notes = [n for n in r["notes"].split("; ") if n and not n.startswith("wiki:")]
        if not src:
            continue                               # a row the wiki alone added last time
        rows[r["build_id"]] = dict(r, source="; ".join(src), notes="; ".join(notes))
    # Fields the wiki filled last time are marked in notes as 'wiki: filled ...'; they were
    # stripped above together with the note, so blank them again before re-filling.
    for r in builds:
        for n in r["notes"].split("; "):
            m = re.match(r"wiki: filled (branch|release_date)", n)
            if m and r["build_id"] in rows:
                rows[r["build_id"]][m.group(1)] = ""

    by_version = collections.defaultdict(list)
    for v, label, title, text in pages:
        version, page_type, date = page_header(text)
        by_version[v].append((label, page_type, date, title))

    for v, entries in by_version.items():
        r = rows.setdefault(v, {"build_id": v, "branch": "", "release_date": "", "source": "",
                                "notes": ""})
        notes = [n for n in r["notes"].split("; ") if n]
        branches = {branch_of(pt) for _, pt, _, _ in entries}
        labels = " and ".join(f"'{lab}' (Type {pt or '?'}, {d or 'no date'})"
                              for lab, pt, d, _ in entries)
        new = []
        # Branch: one page -> its branch. Two pages (beta hotfix, then stable patch) -> stable,
        # with the beta date noted.
        wiki_branch = "stable" if "stable" in branches else branches.pop()
        stable_dates = [d for _, pt, d, _ in entries if branch_of(pt) == "stable" and d]
        wiki_date = (stable_dates or [d for _, _, d, _ in entries if d] or [""])[0]
        if len(entries) > 1:
            new.append(f"wiki: {len(entries)} pages: {labels}, released on beta first "
                       f"and then on stable")
        else:
            new.append(f"wiki: page {labels}")
        for lab, pt, d, _ in entries:
            if "hotfix" in lab.lower() and "hotfix" not in pt.lower():
                new.append(f"wiki: page title says '{lab}' but its Type field says '{pt}'")
        if f"{v}-beta" in rows:
            new.append(f"wiki: update-history's {v}-beta is probably this version")
        if not r["branch"]:
            r["branch"] = wiki_branch
            new.append("wiki: filled branch")
            notes = [n for n in notes if not n.startswith("branch unknown")]
        elif r["branch"] != wiki_branch:
            new.append(f"wiki: conflict: wiki says {wiki_branch}, kept {r['branch']}")
        if not r["release_date"] and wiki_date:
            r["release_date"] = wiki_date
            new.append("wiki: filled release_date")
            notes = [n for n in notes if not n.startswith("date unknown")]
        elif wiki_date and r["release_date"] != wiki_date:
            new.append(f"wiki: conflict: wiki date {wiki_date}, kept {r['release_date']}")
        r["source"] = "; ".join(s for s in [r["source"], WIKI_SOURCE] if s)
        r["notes"] = "; ".join(notes + new)
    return sorted(rows.values(), key=lambda r: build_key(r["build_id"]))


def build_key(v):
    m = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)(-.+)?", v.lower())
    return (tuple(map(int, m.groups()[:3])), 0 if m.group(4) else 1)


# ------------------------------------------------------------------------------ main

def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {path} ({len(rows)} rows)")


def build():
    pages = cached_pages()
    names = load_names()
    rows = build_mentions(pages, names)
    write_csv(REF / "patch_notes_cards.csv", rows, PNC_FIELDS)
    builds = read_csv(REF / "builds.csv")
    write_csv(REF / "builds.csv", reconcile_builds(builds, pages),
              ["build_id", "branch", "release_date", "source", "notes"])
    from spirometry import notes_crosscheck
    notes_crosscheck.build()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("step", nargs="?", choices=["fetch", "build", "all"], default="all")
    a = ap.parse_args()
    if a.step in ("fetch", "all"):
        fetch()
    if a.step in ("build", "all"):
        build()


if __name__ == "__main__":
    main()
