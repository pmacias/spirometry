"""Tests for spirometry.treatment on small synthetic patch histories."""
import filecmp, shutil

from spirometry import treatment as t

BUILDS = [  # (build, branch, date): a stable line with a hotfix, and a beta line
    ("v0.99.1", "stable", "2026-03-17"),
    ("v0.100.0", "beta", "2026-03-19"),
    ("v0.101.0", "beta", "2026-03-26"),
    ("v0.102.0", "beta", "2026-04-02"),
    ("v0.103.2", "stable", "2026-04-16"),
    ("v0.104.0", "beta", "2026-04-23"),
    ("v0.103.3", "stable", "2026-05-29"),
    ("v0.107.1", "stable", "2026-06-18"),
    ("v0.108.0", "beta", "2026-07-02"),
]
COLORS = {"PARRY": "regent", "CAPTURE_SPIRIT": "necrobinder", "SKEWER": "silent",
          "STRIKE": "regent", "REFLECT": "regent", "GLOW": "regent", "KINGLY_KICK": "regent"}


def builds():
    return [{"build_id": b, "branch": br, "release_date": d, "source": "", "notes": ""}
            for b, br, d in BUILDS]


def cc(card, field, old, new, beta, stable, kind="tweak", also=""):
    src = "changelog; beta: update-history field match" + (
        f"; field also changed in {also}" if also else "")
    return {"card_id": card, "field": field, "old": old, "new": new, "beta_build": beta,
            "stable_build": stable, "change_kind": kind, "source": src,
            "color": COLORS.get(card, "")}


def note(card, version, q="", b0="", u0="", b1="", u1="", verb="Buffed", text="x"):
    return {"version": version, "section": "balance", "role": "subject", "card_id": card,
            "verb": verb, "quantity": q, "before_base": b0, "before_upg": u0,
            "after_base": b1, "after_upg": u1, "raw_text": text}


def bcc(card, version, status, **kw):
    r = {"card_id": card, "version": version, "status": status, "change_kind": "",
         "verb": "Nerfed", "quantity": "", "before_base": "", "before_upg": "",
         "after_base": "", "after_upg": "", "source": "patch notes", "text": "x"}
    r.update(kw)
    return r


def history():
    """Parry 6 -> 8 (v0.100.0) -> 10 (v0.101.0), stable at v0.103.2; Skewer a one-step
    tweak; Capture Spirit nerfed on v0.100.0 and reverted on v0.101.0; Reflect changed on
    v0.104.0 (stable v0.107.1); a Strike behavior fix on v0.104.0 with a v0.103.3 copy;
    Glow changed on v0.108.0 only."""
    changes = [
        cc("PARRY", "vars.Parry", "6", "10", "v0.100.0", "v0.103.2", also="v0.101.0"),
        cc("PARRY", "upgrade.parrypower", "+3", "+4", "v0.101.0", "v0.103.2"),
        cc("SKEWER", "damage", "7", "8", "v0.102.0", "v0.103.2"),
        cc("KINGLY_KICK", "damage", "24", "22", "v0.101.0", "v0.103.2"),
        cc("REFLECT", "block", "17", "16", "v0.104.0", "v0.107.1"),
    ]
    notes = [
        note("PARRY", "v0.100.0", "block", "6", "9", "8", "11"),
        note("PARRY", "v0.101.0", "block gain", "8", "11", "10", "14"),
        note("CAPTURE_SPIRIT", "v0.100.0", "hp loss", "3", "4", "2", "3", verb="Nerfed"),
        note("CAPTURE_SPIRIT", "v0.101.0", verb="Reverted (Buffed)"),
    ]
    beta = [
        bcc("CAPTURE_SPIRIT", "v0.100.0", "reverted", quantity="hp loss", before_base="3",
            before_upg="4", after_base="2", after_upg="3"),
        bcc("CAPTURE_SPIRIT", "v0.101.0", "reverted", verb="Reverted (Buffed)"),
        bcc("GLOW", "v0.108.0", "after_last_stable", verb="Buffed", quantity="damage",
            before_base="3", after_base="4"),
    ]
    behavior = [
        {"card_id": "STRIKE", "version": "v0.104.0", "kind": "timing", "text": "fix"},
        {"card_id": "STRIKE", "version": "v0.103.3", "kind": "timing", "text": "fix"},
    ]
    return dict(builds=builds(), changes=changes, beta_changes=beta, behavior=behavior,
                notes=notes, labels=[], attrs={c: {"color": col} for c, col in COLORS.items()})


def tables(h=None):
    events, versions, wins, mismatches = t.build_tables(**(h or history()))
    ver = {(r["card_id"], r["build_id"]): r for r in versions}
    win = {(r["event_id"], r["branch"]): r for r in wins}
    return {e["event_id"]: e for e in events}, ver, win, mismatches


def test_accumulation_across_branches():
    ev, ver, win, mismatches = tables()
    assert mismatches == []
    assert set(ev) >= {"PARRY@v0.100.0", "PARRY@v0.101.0", "SKEWER@v0.102.0"}
    # the net 6 -> 10 is split by the notes; the upgrade moved only on v0.101.0
    f = {x["field"]: (x["old"], x["new"]) for x in ev["PARRY@v0.100.0"]["fields"]}
    assert f["vars.Parry"] == ("6", "8") and "upgrade.parrypower" not in f
    f = {x["field"]: (x["old"], x["new"]) for x in ev["PARRY@v0.101.0"]["fields"]}
    assert f["vars.Parry"] == ("8", "10") and f["upgrade.parrypower"] == ("+3", "+4")
    assert ev["PARRY@v0.100.0"]["stable_build"] == "v0.103.2"
    expect = {"v0.99.1": "", "v0.100.0": "PARRY@v0.100.0",
              "v0.101.0": "PARRY@v0.100.0 PARRY@v0.101.0",
              "v0.102.0": "PARRY@v0.100.0 PARRY@v0.101.0",
              "v0.103.2": "PARRY@v0.100.0 PARRY@v0.101.0",     # stable = every beta before it
              "v0.104.0": "PARRY@v0.100.0 PARRY@v0.101.0",     # beta after the stable
              "v0.108.0": "PARRY@v0.100.0 PARRY@v0.101.0"}
    for b, ids in expect.items():
        assert ver[("PARRY", b)]["event_ids"] == ids, b
    assert [ver[("PARRY", b)]["version"] for b in ("v0.99.1", "v0.100.0", "v0.101.0",
                                                   "v0.103.2")] == [0, 1, 2, 2]
    # Reflect's v0.104.0 change reaches stable only at v0.107.1
    assert ver[("REFLECT", "v0.103.3")]["event_ids"] == ""
    assert ver[("REFLECT", "v0.107.1")]["event_ids"] == "REFLECT@v0.104.0"
    # Glow's post-stable beta change: betas only
    assert ver[("GLOW", "v0.108.0")]["event_ids"] == "GLOW@v0.108.0"
    assert ver[("GLOW", "v0.107.1")]["event_ids"] == ""
    assert ev["GLOW@v0.108.0"]["change_kind"] == "tweak"


def test_windows_clean_and_not():
    ev, ver, win, _ = tables()
    # v0.101.0's step is clean on beta; on stable both steps arrive together
    w = win[("PARRY@v0.101.0", "beta")]
    assert (w["before_builds"], w["after_builds"], w["clean"]) == ("v0.100.0", "v0.101.0", "yes")
    w = win[("PARRY@v0.100.0", "stable")]
    assert w["clean"] == "no" and "PARRY@v0.101.0" in w["reason"]
    w = win[("SKEWER@v0.102.0", "stable")]
    assert (w["before_builds"], w["after_builds"], w["clean"]) == ("v0.99.1", "v0.103.2", "yes")
    # same-character cards changed in the same step leave the control group
    assert win[("PARRY@v0.101.0", "beta")]["control_exclusions"] == "KINGLY_KICK"
    assert win[("PARRY@v0.100.0", "beta")].get("control_exclusions", "") == ""   # no before
    assert win[("PARRY@v0.100.0", "stable")]["control_exclusions"] == "KINGLY_KICK"
    assert win[("SKEWER@v0.102.0", "stable")]["control_exclusions"] == ""        # other colour
    assert win[("REFLECT@v0.104.0", "beta")]["control_exclusions"] == ""
    # Strike's bug fix falls in Reflect's windows: a flag for regent controls
    assert win[("REFLECT@v0.104.0", "beta")]["control_behavior_flags"] == "STRIKE"


def test_beta_revert():
    ev, ver, win, mismatches = tables()
    nerf, revert = ev["CAPTURE_SPIRIT@v0.100.0"], ev["CAPTURE_SPIRIT@v0.101.0"]
    assert nerf["change_kind"] == "tweak" and revert["change_kind"] == "revert"
    assert nerf["stable_build"] == revert["stable_build"] == ""        # never reached stable
    assert ver[("CAPTURE_SPIRIT", "v0.100.0")]["version"] == 1
    assert ver[("CAPTURE_SPIRIT", "v0.101.0")]["version"] == 2
    # the stable build carries both (they net out); no card_changes row, no mismatch
    assert ver[("CAPTURE_SPIRIT", "v0.103.2")]["event_ids"] == \
        "CAPTURE_SPIRIT@v0.100.0 CAPTURE_SPIRIT@v0.101.0"
    assert win[("CAPTURE_SPIRIT@v0.101.0", "beta")]["clean"] == "yes"
    assert win[("CAPTURE_SPIRIT@v0.101.0", "stable")]["clean"] == "no"
    assert mismatches == []


def test_stable_hotfix_carries_no_card_events():
    ev, ver, win, _ = tables()
    for card in ("PARRY", "SKEWER", "CAPTURE_SPIRIT", "REFLECT"):
        a, b = ver[(card, "v0.103.2")], ver[(card, "v0.103.3")]
        assert (a["version"], a["event_ids"]) == (b["version"], b["event_ids"])
    # its bug-fix copy is a behavior event only, on stable; betas carry the beta row
    assert ver[("STRIKE", "v0.103.3")]["behavior_event_ids"] == "STRIKE@v0.103.3/fix1"
    assert ver[("STRIKE", "v0.103.3")]["version"] == 0
    assert ver[("STRIKE", "v0.108.0")]["behavior_event_ids"] == "STRIKE@v0.104.0/fix1"
    assert ev["STRIKE@v0.104.0/fix1"]["sensitivity_only"] == "yes"
    # v0.107.1's window starts at the hotfix
    assert win[("REFLECT@v0.104.0", "stable")]["before_builds"] == "v0.103.3"


def test_stable_check_fails_on_purpose():
    h = history()
    # card_changes says 6 -> 11, but the events only get to 10
    h["changes"][0] = cc("PARRY", "vars.Parry", "6", "11", "v0.100.0", "v0.103.2",
                         also="v0.101.0")
    h["notes"][1] = note("PARRY", "v0.101.0", "block gain", "8", "11", "11", "14")
    events, _, _, _ = t.build_tables(**h)
    ok = t.stable_check(events, h["builds"], h["changes"])
    assert ok == []
    wrong = [dict(r) for r in h["changes"]]
    wrong[0]["new"] = "12"
    bad = t.stable_check(events, h["builds"], wrong)
    assert len(bad) == 1 and "PARRY vars.Parry" in bad[0] and "6 -> 11" in bad[0]
    # an event dropped from the history: card_changes has a field no event carries
    missing = [e for e in events if e["event_id"] != "SKEWER@v0.102.0"]
    bad = t.stable_check(missing, h["builds"], h["changes"])
    assert any("SKEWER damage" in m and "no event carries it" in m for m in bad)


def test_unresolved_field_is_spread_not_guessed():
    h = history()
    h["notes"] = [n for n in h["notes"] if n["card_id"] != "PARRY"]
    ev, ver, win, mismatches = tables(h)
    f = {x["field"]: (x["old"], x["new"]) for x in ev["PARRY@v0.100.0"]["fields"]}
    assert f["vars.Parry"] == ("6", t.UNRESOLVED)
    f = {x["field"]: (x["old"], x["new"]) for x in ev["PARRY@v0.101.0"]["fields"]}
    assert f["vars.Parry"] == (t.UNRESOLVED, "10")
    assert mismatches == []


def test_card_patch_windows():
    ev, ver, win, _ = tables()
    # Parry's two beta steps are one card-patch on stable: clean at that level
    w = win[("PARRY@v0.103.2/patch", "stable")]
    assert w["level"] == "card_patch" and w["members"] == "PARRY@v0.100.0 PARRY@v0.101.0"
    assert (w["before_builds"], w["after_builds"], w["clean"]) == ("v0.99.1", "v0.103.2", "yes")
    assert w["control_exclusions"] == "KINGLY_KICK"
    assert ("PARRY@v0.103.2/patch", "beta") not in win          # stable windows only
    assert win[("REFLECT@v0.107.1/patch", "stable")]["before_builds"] == "v0.103.3"
    # a card-patch with no card_changes row (Capture Spirit's nerf + revert) gets none
    assert ("CAPTURE_SPIRIT@v0.103.2/patch", "stable") not in win
    # net fields come from card_changes
    h = history()
    events, _, _, _ = t.build_tables(**h)
    rows = {(r["card_patch_id"], r["field"]): r for r in t.patch_field_rows(h["changes"], events)}
    r = rows[("PARRY@v0.103.2/patch", "vars.Parry")]
    assert (r["old"], r["new"], r["rel_change"]) == ("6", "10", "0.6667")
    assert r["events"] == "PARRY@v0.100.0 PARRY@v0.101.0"


def test_card_patch_not_clean_when_card_differs_by_more():
    h = history()
    events, _, _, _ = t.build_tables(**h)
    cards = set(h["attrs"]) | {e["card_id"] for e in events}
    _, state = t.card_versions(events, h["builds"], cards)
    units = t.card_patches(events, h["changes"])
    parry = next(u for u in units if u["id"] == "PARRY@v0.103.2/patch")
    parry["members"] = ["PARRY@v0.101.0"]                          # drop one step on purpose
    parry["events"] = [e for e in parry["events"] if e["event_id"] == "PARRY@v0.101.0"]
    colors = {c: a["color"] for c, a in h["attrs"].items()}
    w = next(r for r in t.windows([parry], h["builds"], state, cards, colors))
    assert w["clean"] == "no" and "PARRY@v0.100.0" in w["reason"]


def test_kind_source():
    ev, _, _, _ = tables()
    assert ev["PARRY@v0.100.0"]["kind_source"] == "card_changes"
    assert ev["CAPTURE_SPIRIT@v0.100.0"]["kind_source"] == "text rule"
    assert ev["GLOW@v0.108.0"]["kind_source"] == "text rule"
    assert ev["STRIKE@v0.104.0/fix1"]["kind_source"] == "behavior"
    h = history()
    h["changes"].append({**history()["changes"][0], "card_id": "TAG_TEAM", "field": "(patch notes)",
                         "old": "", "new": "", "change_kind": "mechanic", "beta_build": "v0.101.0",
                         "source": "patch notes"})
    h["beta_changes"].append(bcc("FUEL", "v0.108.0", "after_last_stable", change_kind="rework"))
    ev, _, _, _ = tables(h)
    assert ev["TAG_TEAM@v0.101.0"]["kind_source"] == "notes-only"
    assert ev["FUEL@v0.108.0"]["kind_source"] == "beta_card_changes"


def test_rel_change():
    assert t.rel_change("6", "8") == "0.3333"
    assert t.rel_change("+3", "+4") == "0.3333"
    assert t.rel_change("0", "1") == "" and t.rel_change("none", "2") == ""


def test_real_reference_rebuilds_identically(tmp_path):
    """The committed reference data: the stable check passes and two builds are identical."""
    ref = tmp_path / "reference"
    (ref / "raw").mkdir(parents=True)
    for name in ("builds", "card_changes", "beta_card_changes", "behavior_changes",
                 "patch_notes_cards", "text_only_labels"):
        shutil.copy(t.REF / f"{name}.csv", ref)
    shutil.copy(t.REF / "raw" / "cards.json", ref / "raw")
    assert t.build(ref) == []
    outs = ["change_events", "change_event_fields", "card_versions", "windows",
            "card_patch_fields"]
    first = tmp_path / "first"
    first.mkdir()
    for o in outs:
        shutil.copy(ref / f"{o}.csv", first)
    t.build(ref)
    for o in outs:
        assert filecmp.cmp(first / f"{o}.csv", ref / f"{o}.csv", shallow=False), o
        assert filecmp.cmp(t.REF / f"{o}.csv", ref / f"{o}.csv", shallow=False), \
            f"committed {o}.csv is stale: rerun python -m spirometry.treatment"
