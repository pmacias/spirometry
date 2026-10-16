"""spirometry.writeup: the whole build on synthetic outputs (sample_results -> numbers ->
lint -> privacy -> figures -> typst), the digit lint, a missing key failing the compile, figure
placeholders and staleness. No run data. Compile tests need the "writeup" extra (typst)."""
import base64
import importlib.util
import json
import os
import pathlib
import re
import shutil

import pytest

from spirometry import numbers as N, sample_results, writeup as W

REPO_WRITEUP = pathlib.Path(__file__).resolve().parents[1] / "writeup"
FIGURE_SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "writeup" / "figures.py"
# A 1x1 PNG, for a figure file that exists.
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8Dw"
                       "HwAFBQIAX8jx0gAAAABJRU5ErkJggg==")

EXAMPLE = '''#import "../style.typ": *

= Example chapter

== A section

Parry moved by #n("dose.triage.h3.slope_first_pm") over weeks 0–3 on v0.103.2.

#picture[An everyday picture.]
#project[In your project: #n("snapshot.pages") pages.]
#skill[Choosing a comparison group.]
#unverified[A claim not yet checked.]

#fig("fig_example", [An example figure.])

#check(
  ([What is a pick rate?], [Picks divided by offers.]),
  ([Why cluster by run?], [Offers from one run are related.]),
)
'''


def _stub(text):
    """A chapter reduced to its title line (label kept, so cross-references resolve)."""
    title = re.search(r"^= .*$", text, re.M).group(0)
    return f'#import "../style.typ": *\n\n{title}\n'


@pytest.fixture()
def wu(tmp_path):
    """A copy of writeup/ (typ files only) with a synthetic numbers.json, every chapter cut to
    its title (the written chapters name real cards the synthetic outputs don't have), and
    one example chapter that uses every helper."""
    w = tmp_path / "writeup"
    shutil.copytree(REPO_WRITEUP, w, ignore=shutil.ignore_patterns(
        "numbers.json", "numbers.csv", "build", "figures", "OUTLINE.md", "REVIEW.md"))
    for f in (w / "chapters").glob("*.typ"):
        if f.name != "a_answers.typ":
            f.write_text(_stub(f.read_text()))
    a, r = tmp_path / "analysis", tmp_path / "results"
    sample_results.write_numbers_inputs(a, r, tmp_path / "ref", seed=4)
    df, header = N.build(a, r, allow_sample=True, snapshot_log=tmp_path / "snapshot.log")
    N.write(df, header, w / "numbers.json")
    (w / "chapters" / "00_project.typ").write_text(EXAMPLE)
    return w


def test_lint_catches_a_stray_digit():
    bad = W.lint_text("= Title\n\nPicks rose by 12 points.\n", "ch.typ")
    assert bad == [("ch.typ", 3, "Picks rose by 12 points.")]


def test_lint_allows_keys_comments_and_fixed_terms():
    ok = ('#import "../style.typ": *\n'
          '// a comment with 3 digits 42\n'
          '/* block\n comment 7 */\n'
          'It moved #n("did.h3.first.uncalibrated.clearly_nonzero") over weeks 0–3.\n'
          'On v0.103.2 against v0.99.1, in 2026; variance p(1 − p); |z| > 2; a 95% interval.\n'
          '#fig("fig_dose_2", [A caption.])\n'
          'Notebook section 7 of 02_pick_rate_did; weak if F < 10.\n')
    assert W.lint_text(ok) == []


def test_lint_reads_captions_and_check_text():
    bad = W.lint_text('#fig("fig_a", [Slope 1.4 here.])\n#check(([Q with 3?], [A.]))\n')
    assert [i for _, i, _ in bad] == [1, 2]


def test_repo_chapters_pass_the_lint():
    assert W.lint(REPO_WRITEUP) == []


def test_repo_figures_are_drawn_by_the_figure_script():
    spec = importlib.util.spec_from_file_location("figures", FIGURE_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    drawn = {f.__name__ for f in mod.FIGURES}
    names = W.figure_names(REPO_WRITEUP)
    assert names and set(names) <= drawn


def test_repo_keys_exist_in_the_real_numbers_table():
    """Every #n key in the chapters is in writeup/numbers.json (git-ignored: skipped where it
    is missing or built from sample outputs)."""
    path = REPO_WRITEUP / "numbers.json"
    if not path.exists():
        pytest.skip("writeup/numbers.json not built here")
    table = json.loads(path.read_text())
    if table["build"].get("sample"):
        pytest.skip("writeup/numbers.json is from sample outputs")
    used = set()
    for f in W.chapter_files(REPO_WRITEUP):
        used |= set(re.findall(r'#n\(\s*"([^"]+)"\s*\)', f.read_text()))
    assert used and not used - set(table["numbers"])


def test_build_on_synthetic_outputs(wu):
    pytest.importorskip("typst")
    r = W.build(wu, allow_sample=True)
    pdf = pathlib.Path(r["pdf"])
    assert pdf.exists() and pdf.parent == wu / "build"
    assert r["pages"] >= 19 and r["sample"]
    assert r["figures_missing"] == ["fig_example"]     # placeholder, not an error


def test_answers_collected_for_the_answer_key(wu):
    typst = pytest.importorskip("typst")
    out = typst.query(str(wu / "main.typ"), "<answer>", field="value", root=str(wu))
    import json
    answers = json.loads(out)
    assert [a["num"] for a in answers] == ["0.1", "0.2"]   # chapter 0, questions 1 and 2


def test_sample_numbers_refused_without_flag(wu):
    with pytest.raises(W.WriteupError, match="sample"):
        W.build(wu)


def test_stray_digit_stops_the_build(wu):
    p = wu / "chapters" / "03_counting.typ"
    p.write_text(p.read_text() + "\nParry rose 14 points.\n")
    with pytest.raises(W.WriteupError, match=r"03_counting.typ:\d+: Parry rose 14 points"):
        W.build(wu, allow_sample=True)


def test_missing_key_fails_the_compile(wu):
    pytest.importorskip("typst")
    p = wu / "chapters" / "05_did.typ"
    p.write_text(p.read_text() + '\nThe slope is #n("dose.no_such.key").\n')
    with pytest.raises(W.WriteupError, match="no key 'dose.no_such.key'"):
        W.build(wu, allow_sample=True)


def test_present_figure_is_used_and_stale_one_stops(wu):
    pytest.importorskip("typst")
    f = wu / "figures" / "fig_example.png"
    f.parent.mkdir()
    f.write_bytes(PNG)
    r = W.build(wu, allow_sample=True)
    assert r["figures_present"] == ["fig_example"] and r["figures_missing"] == []
    old = 1_700_000_000                                # 2023: before the synthetic stamp
    os.utime(f, (old, old))
    with pytest.raises(W.WriteupError, match="older than the run tables.*fig_example"):
        W.build(wu, allow_sample=True)


def test_privacy_check(wu):
    p = wu / "chapters" / "07_checks.typ"
    p.write_text(p.read_text() + "\n// uploader 0123456789abcdef\n")
    with pytest.raises(W.WriteupError, match="privacy"):
        W.build(wu, allow_sample=True)


def test_refresh_numbers(wu, tmp_path):
    pytest.importorskip("typst")
    (wu / "numbers.json").unlink()
    with pytest.raises(W.WriteupError, match="not found"):
        W.build(wu, allow_sample=True)
    r = W.build(wu, refresh_numbers=True, analysis=tmp_path / "analysis",
                results=tmp_path / "results", snapshot_log=tmp_path / "snapshot.log",
                allow_sample=True)
    assert (wu / "numbers.json").exists() and r["pages"] >= 19


def test_cli(wu, capsys):
    pytest.importorskip("typst")
    W.main(["build", "--writeup", str(wu), "--allow-sample"])
    out = capsys.readouterr().out
    assert "pages" in out and "SAMPLE" in out and "fig_example" in out
