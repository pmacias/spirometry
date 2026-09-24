"""Card patch-change dataset from Spire Codex's changelogs and update history.

Fetches the card list, every changelog, and every card's update history, caching
raw responses under reference/raw/ (reruns read the cache instead of refetching),
then builds the reference CSVs from the cache alone:

    reference/builds.csv             one row per game version: branch, release date, source
    reference/card_changes.csv       one row per (card, field, stable patch), with beta timing
    reference/text_only_changes.csv  card-patches where only description text changed
    reference/excluded_fields.csv    card fields left out of card_changes, with counts
    reference/history_unmatched.csv  update-history entries no changelog row accounts for

What changed (old/new) comes from the changelogs' structured {field, old, new}; when it
first reached beta comes from update-history, matched on field labels only (its values are
preformatted, truncated strings and are never parsed).

Usage (from the repo root):
    python -m spirometry.patch_history            # fetch what's missing, then build
    python -m spirometry.patch_history fetch      # only fetch into the cache
    python -m spirometry.patch_history build      # only build CSVs from the cache
"""
import argparse, collections, csv, json, pathlib, re, time
import requests

API = "https://spire-codex.com/api"
REF = pathlib.Path("reference")
RAW = REF / "raw"
MIN_INTERVAL = 6.0          # seconds between requests: at most 10 per minute

# Versions seen in the run export so far (first 5 pages); all is_beta = false there.
RUN_DATA_VERSIONS = ["v0.98.0", "v0.98.1", "v0.98.2", "v0.98.3", "v0.99.1", "v0.100.0",
                     "v0.101.0", "v0.102.0", "v0.103.0", "v0.103.1", "v0.103.2"]

# Changelogs whose card diffs are a game release reaching the main (stable) site, with the
# text that says so. Every other changelog is a site/parser release: its card diffs are
# extraction fixes, not patches. Each quote is checked against the cached changelog.
GAME_CHANGELOGS = {
    "1.1.0": ("v0.103.2", "Data update for Mega Crit's Major Update #1 (game v0.103.2)"),
    "1.2.0": ("v0.107.1", "Slay the Spire 2 v0.107.1"),
}

# Branch facts stated in changelog text: (versions, branch, changelog tag, quote, note).
# A (lo, hi) tuple covers every known version in that inclusive range.
BRANCH_FACTS = [
    (["v0.103.2"], "stable", "1.1.0", "full rollup of beta content from v0.100.0 through "
     "v0.103.1 landing on stable", "stable release date = Spire Codex changelog date"),
    (("v0.100.0", "v0.103.1"), "beta", "1.1.0", "full rollup of beta content from v0.100.0 "
     "through v0.103.1 landing on stable", ""),
    (["v0.107.1"], "stable", "1.2.0", "Slay the Spire 2 v0.107.1",
     "main-site game-data release (Steam build_id 23811903); stable release date = Spire Codex "
     "changelog date. Changelog 1.2.1 also lists v0.107.1 among versions ingested on the beta "
     "channel, so it was on beta too"),
    (["v0.107.0", "v0.108.0"], "beta", "1.2.1", "the beta channel ingested game versions "
     "v0.107.0, v0.107.1, and v0.108.0", ""),
    (["v0.109.0", "v0.109.1", "v0.110.0", "v0.111.0"], "beta", "1.3.0",
     "Beta channel: ingested v0.109.0, v0.109.1, v0.110.0, and v0.111.0", ""),
]

# Card fields, after collapsing list indices to [i]. Gameplay whitelist, by role:
TEXT_FIELDS = {"description", "description_raw", "upgrade_description"}
COST_FIELDS = {"cost", "star_cost", "is_x_cost", "is_x_star_cost", "upgrade.cost"}
REWORK_FIELDS = {"type", "hit_count", "keywords[i]", "powers_applied[i].power", "target",
                 "spawns_cards", "spawns_cards[i]"}
NUMERIC_FIELDS = {"damage", "block", "energy_gain", "cards_draw", "hp_loss",
                  "powers_applied[i].amount"}
NUMERIC_PREFIXES = ("vars.", "upgrade.")          # every card variable and upgrade value
OTHER_FIELDS = {"rarity", "can_be_generated_in_combat"}
# Not whitelisted, with the reason written to excluded_fields.csv.
EXCLUDED_REASONS = {
    "compendium_order": "display order in the compendium",
    "type_key": "mirror of type", "rarity_key": "mirror of rarity",
    "keywords_key[i]": "mirror of keywords", "powers_applied[i].power_key": "mirror of power",
    "vars": "whole-dict summary ('N fields'), no values",
    "upgrade": "whole-dict summary ('N fields'), no values",
    "type_variants": "whole-dict summary ('N fields'), no values",
    "upgrade.description_changed": "flag that the upgrade text differs, not a value",
}

_last_request = 0.0


def get_cached(path, url, ok_404=False):
    """Return parsed JSON for url, from the cache file if present, else fetch and save raw bytes.

    With ok_404, a 404 body is cached and returned like any other response (update-history
    answers 404 {"detail": "No update history for ..."} for entities never changed).
    """
    global _last_request
    if path.exists():
        return json.loads(path.read_bytes())
    while True:
        wait = _last_request + MIN_INTERVAL - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _last_request = time.monotonic()
        r = requests.get(url, timeout=60)
        if r.status_code == 429:
            wait = int(r.headers.get("Retry-After", 60))
            print(f"rate limited, sleeping {wait}s")
            time.sleep(wait)
            continue
        if not (ok_404 and r.status_code == 404):
            r.raise_for_status()
        break
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(r.content)
    return r.json()


def cards_path():
    return RAW / "cards.json"


def changelog_index_path():
    return RAW / "changelogs.json"


def changelog_path(tag):
    return RAW / "changelogs" / f"{tag}.json"


def history_path(card_id):
    return RAW / "update_history" / "cards" / f"{card_id}.json"


def changelog_card_ids(changelog):
    """Card ids that appear anywhere in a changelog's cards category."""
    ids = set()
    for cat in changelog.get("categories", []):
        if cat["id"] == "cards":
            for kind in ("added", "removed", "changed"):
                ids.update(e["id"] for e in cat.get(kind, []))
    return ids


def fetch():
    cards = get_cached(cards_path(), f"{API}/cards")
    index = get_cached(changelog_index_path(), f"{API}/changelogs")
    changelogs = [get_cached(changelog_path(e["tag"]), f"{API}/changelogs/{e['tag']}")
                  for e in index]
    # Current cards plus any card a changelog mentions (removed cards are not in the list).
    ids = {c["id"] for c in cards}
    for cl in changelogs:
        ids |= changelog_card_ids(cl)
    todo = sorted(i for i in ids if not history_path(i).exists())
    print(f"{len(ids)} cards, {len(todo)} histories to fetch "
          f"(~{len(todo) * MIN_INTERVAL / 60:.0f} min)")
    for k, card_id in enumerate(todo, 1):
        get_cached(history_path(card_id), f"{API}/update-history/cards/{card_id}", ok_404=True)
        if k % 50 == 0:
            print(f"  {k}/{len(todo)}")
    print("fetch done")


# ---------------------------------------------------------------- build (cache only)

def vkey(v):
    """Sort key for 'v0.103.2' / 'V0.98.0-beta'; a '-suffix' sorts before the plain version."""
    m = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)(-.+)?", v.lower())
    return (tuple(map(int, m.groups()[:3])), 0 if m.group(4) else 1)


def norm_field(f):
    return re.sub(r"\[[^\]]*\]", "[i]", f)


def history_label(f):
    """Changelog field name -> update-history label ('powers_applied[0].amount' ->
    'powers applied[0].amount'), lowercased. Only labels are compared, never values."""
    return f.replace("_", " ").lower()


def is_num(v):
    try:
        float(str(v).lstrip("+"))
        return True
    except ValueError:
        return False


def field_role(f):
    n = norm_field(f)
    if n in TEXT_FIELDS:
        return "text"
    if n in COST_FIELDS:
        return "cost"
    if n in REWORK_FIELDS:
        return "rework"
    if n in NUMERIC_FIELDS or (n.startswith(NUMERIC_PREFIXES) and n not in EXCLUDED_REASONS):
        return "numeric"
    if n in OTHER_FIELDS:
        return "other"
    return None


def classify(changes):
    """change_kind for one card-patch from its whitelisted structured fields only.

    rework: a field added/removed (to or from 'none'), or type, hit count, keywords, power,
    target or spawned cards changed. tweak: only numeric values on existing fields.
    cost_change is appended whenever cost changed; rarity_change likewise.
    text_only: only description fields changed. Description text never decides anything else.
    """
    labels, structured = set(), False
    for c in changes:
        role = field_role(c["field"])
        if role in (None, "text"):
            continue
        structured = True
        old, new = str(c["old"]), str(c["new"])
        if role == "cost":
            labels.add("cost_change")
        elif norm_field(c["field"]) == "rarity":
            labels.add("rarity_change")
        elif role == "rework" or "none" in (old, new):
            labels.add("rework")
        elif role == "numeric" and is_num(old) and is_num(new):
            labels.add("tweak")
        else:
            labels.add("other")
    if not structured:
        return "text_only" if any(field_role(c["field"]) == "text" for c in changes) else None
    if "rework" in labels:
        labels -= {"tweak", "other"}
    order = ["rework", "tweak", "other", "cost_change", "rarity_change"]
    return "+".join(k for k in order if k in labels)


def load_cache():
    cards = json.loads(cards_path().read_bytes())
    index = json.loads(changelog_index_path().read_bytes())
    changelogs = {e["tag"]: json.loads(changelog_path(e["tag"]).read_bytes()) for e in index}
    histories = {}
    for p in sorted(history_path("x").parent.glob("*.json")):
        h = json.loads(p.read_bytes())
        if isinstance(h, dict):          # cached 404
            assert h.get("detail", "").startswith("No update history"), (p, h)
            h = []
        histories[p.stem] = h
    return cards, changelogs, histories


def changelog_text(cl):
    parts = [cl.get("title", "")]
    for k in ("features", "fixes", "api_changes"):
        parts += cl.get(k, [])
    return "\n".join(parts)


def build_builds(changelogs, histories):
    rows = {}

    def row(v):
        return rows.setdefault(v, {"build_id": v, "branch": "", "release_date": "",
                                   "source": [], "notes": []})

    # update-history: every version it lists, with its date and type.
    seen = collections.defaultdict(lambda: collections.defaultdict(set))
    for card, entries in histories.items():
        for e in entries:
            seen[e["version"].lower()]["date"].add(e["date"])
            seen[e["version"].lower()]["type"].add(e["type"])
            seen[e["version"].lower()]["cards"].add(card)
    for v, s in seen.items():
        r = row(v)
        r["source"].append("update-history")
        types = sorted(s["type"])
        if len(s["date"]) == 1:
            r["release_date"] = next(iter(s["date"]))
        else:
            r["notes"].append(f"update-history gives several dates: {sorted(s['date'])}")
        if types == ["Beta Patch"]:
            r["branch"] = "beta"
        n = len(s["cards"])
        r["notes"].append(f"update-history type {'/'.join(types)} ({n} card{'s' * (n != 1)})")

    # Branch facts from changelog text (checked against the cached text).
    known = set(rows) | set(RUN_DATA_VERSIONS)
    for versions, branch, tag, quote, note in BRANCH_FACTS:
        assert quote in changelog_text(changelogs[tag]), (tag, quote)
        if isinstance(versions, tuple):
            lo, hi = map(vkey, versions)
            versions = sorted((v for v in known if lo <= vkey(v) <= hi), key=vkey)
        for v in versions:
            r = row(v)
            if r["branch"] and r["branch"] != branch:
                r["notes"].append(f"update-history calls it {r['branch']}; changelog {tag} "
                                  f"says {branch}")
            r["branch"] = branch
            r["source"].append(f"changelog {tag} text")
            if note:
                r["notes"].append(note)
            if branch == "stable":
                beta_date = r["release_date"]
                r["release_date"] = changelogs[tag]["date"]
                if beta_date and beta_date != r["release_date"]:
                    r["notes"].append(f"update-history (beta) date {beta_date}")

    # Any other version mentioned in changelog text.
    for tag, cl in changelogs.items():
        for v in sorted(set(re.findall(r"\bv0\.\d+\.\d+\b", changelog_text(cl)))):
            r = row(v)
            if not any(s.startswith(f"changelog {tag}") for s in r["source"]):
                r["source"].append(f"changelog {tag} text (mention)")

    for v in RUN_DATA_VERSIONS:
        row(v)["source"].append("run data")

    for r in rows.values():
        why = []
        if not r["branch"]:
            why.append("branch unknown: no endpoint states it")
        if not r["release_date"]:
            why.append("date unknown: not in update-history and no changelog dates it")
        if "run data" in r["source"]:
            why.append("run files (first 5 export pages) report is_beta=false for every "
                       "version, including v0.100.0-v0.103.1, which changelog 1.1.0 calls beta; "
                       "is_beta is not used for branch")
        if v_suffix := re.search(r"-\w+$", r["build_id"]):
            why.append(f"'{v_suffix.group(0)}' version; relation to the plain version unknown")
        r["notes"] += why
    out = sorted(rows.values(), key=lambda r: vkey(r["build_id"]))
    for r in out:
        r["source"] = "; ".join(dict.fromkeys(r["source"]))
        r["notes"] = "; ".join(dict.fromkeys(r["notes"]))
    return out


def history_index(histories):
    """card -> [(vkey, version, date, {labels})], labels = text before ': ' in each change."""
    idx = {}
    for card, entries in histories.items():
        idx[card] = sorted(((vkey(e["version"]), e["version"].lower(), e["date"],
                             {s.split(": ", 1)[0].strip().lower() for s in e["changes"]})
                            for e in entries), key=lambda t: t[0])
    return idx


def build_changes(changelogs, histories, card_ids):
    hist = history_index(histories)
    rows, text_rows, matched = [], [], set()
    excluded = collections.defaultdict(lambda: {"count": 0, "changelogs": set(), "cards": []})
    non_card_types = collections.Counter()

    def exclude(field, reason, tag, card):
        e = excluded[(norm_field(field), reason)]
        e["count"] += 1
        e["changelogs"].add(tag)
        if card not in e["cards"]:
            e["cards"].append(card)

    prev = None
    for tag, (stable, quote) in sorted(GAME_CHANGELOGS.items(), key=lambda t: vkey(t[1][0])):
        cl = changelogs[tag]
        assert quote in changelog_text(cl), (tag, quote)
        lo, hi = (vkey(prev) if prev else None), vkey(stable)
        prev = stable
        for cat in cl["categories"]:
            if cat["id"] != "cards":
                non_card_types[cat["id"]] += sum(len(cat.get(k, [])) for k in
                                                 ("added", "removed", "changed"))
                continue
            entities = ([(e["id"], "added") for e in cat.get("added", [])] +
                        [(e["id"], "removed") for e in cat.get("removed", [])] +
                        [(e["id"], e["changes"]) for e in cat.get("changed", [])])
            for card, changes in entities:
                assert card in card_ids, f"{card} in changelog {tag} cards but not a known card"
                # '-beta' entries (V0.98.0-beta, V0.99.0-beta) are skipped: on every card they
                # are a change and its exact reversal, netting to zero.
                window = [h for h in hist.get(card, []) if (lo is None or h[0] > lo)
                          and h[0] <= hi and h[0][1]]
                if isinstance(changes, str):             # whole card added / removed
                    kind = changes
                    changes = [{"field": "(card)", "old": "none" if kind == "added" else "present",
                                "new": "present" if kind == "added" else "none"}]
                else:
                    kind = classify(changes)
                changed_fields = "|".join(c["field"] for c in changes)
                for c in changes:
                    role = field_role(c["field"]) if c["field"] != "(card)" else "card"
                    if role is None:
                        exclude(c["field"], EXCLUDED_REASONS.get(norm_field(c["field"]),
                                                                 "not in whitelist"), tag, card)
                        continue
                    if role == "text" and kind != "text_only":
                        continue
                    label = (history_label(c["field"]) if c["field"] != "(card)"
                             else "added." if kind == "added" else "removed.")
                    parent = re.split(r"[.\[]", label)[0]      # 'vars', 'upgrade', 'powers applied'
                    hits = [h for h in window if label in h[3]]
                    via = "field match"
                    if not hits and parent != label:
                        # update-history sometimes lists only the whole dict ('Vars: 3 fields → ...')
                        hits = [h for h in window if parent in h[3]]
                        via = f"match on whole '{parent}'"
                    if hits:
                        beta, src = hits[0], f"update-history {via}"
                        if len(hits) > 1:
                            src += "; field also changed in " + ", ".join(h[1] for h in hits[1:])
                    elif len(window) == 1:
                        beta, src = window[0], "update-history card match (only entry in window)"
                    else:
                        beta = None
                        src = (f"no update-history field match ({len(window)} entries in window)")
                    matched.update((card, h[1]) for h in (hits or ([beta] if beta else [])))
                    r = {"card_id": card, "field": c["field"], "old": c["old"], "new": c["new"],
                         "beta_build": beta[1] if beta else "", "beta_date": beta[2] if beta else "",
                         "stable_build": stable, "stable_date": cl["date"], "change_kind": kind,
                         "changed_fields": changed_fields,
                         "source": f"changelog {tag}; beta: {src}"}
                    rows.append(r)
                    if kind == "text_only":
                        text_rows.append(r)

    # Non-game changelogs: everything in their cards category is excluded, by field.
    for tag, cl in changelogs.items():
        if tag in GAME_CHANGELOGS:
            continue
        for cat in cl["categories"]:
            if cat["id"] == "cards":
                for e in cat.get("changed", []):
                    for c in e["changes"]:
                        exclude(c["field"], "site/parser changelog, not a game release", tag, e["id"])

    # update-history entries (up to the last stable build) that no changelog row explains.
    last = vkey(prev)
    unmatched = [{"card_id": card, "version": v, "date": d, "fields": "|".join(sorted(labels))}
                 for card, entries in hist.items() for k, v, d, labels in entries
                 if k <= last and (card, v) not in matched]
    excl = [{"field": f, "reason": reason, "count": e["count"],
             "changelogs": " ".join(sorted(e["changelogs"], key=lambda t: tuple(map(int, t.split("."))))),
             "example_cards": " ".join(e["cards"][:5])}
            for (f, reason), e in sorted(excluded.items(), key=lambda t: -t[1]["count"])]
    return rows, text_rows, excl, unmatched, non_card_types


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {path} ({len(rows)} rows)")


def build():
    cards, changelogs, histories = load_cache()
    card_ids = {c["id"] for c in cards}
    for cl in changelogs.values():
        card_ids |= changelog_card_ids(cl)
    missing = card_ids - set(histories)
    assert not missing, f"no cached history for {len(missing)} cards; run fetch first"

    write_csv(REF / "builds.csv", build_builds(changelogs, histories),
              ["build_id", "branch", "release_date", "source", "notes"])
    rows, text_rows, excl, unmatched, non_card = build_changes(changelogs, histories, card_ids)
    change_cols = ["card_id", "field", "old", "new", "beta_build", "beta_date", "stable_build",
                   "stable_date", "change_kind", "changed_fields", "source"]
    write_csv(REF / "card_changes.csv", rows, change_cols)
    write_csv(REF / "text_only_changes.csv", text_rows, change_cols)
    write_csv(REF / "excluded_fields.csv", excl,
              ["field", "reason", "count", "changelogs", "example_cards"])
    write_csv(REF / "history_unmatched.csv", unmatched, ["card_id", "version", "date", "fields"])
    print("non-card entity types skipped in game changelogs:", dict(non_card))


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
