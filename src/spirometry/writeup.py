"""Field guide v2 build: one command from the numbers table to the PDF.

    python -m spirometry.writeup build [--writeup writeup] [--refresh-numbers]
        [--analysis data/analysis] [--results results] [--snapshot-log snapshot.log]
        [--allow-sample]

Steps, each stopping the build on failure:

1. numbers: reuse writeup/numbers.json, or with --refresh-numbers rebuild it with
   spirometry.numbers (same inputs and guards). A sample numbers.json (build.sample: true) is
   refused unless --allow-sample; the title page then says SAMPLE DATA.
2. digit lint: every chapter (writeup/chapters/*.typ) is read with comments, #n("...")
   calls, #fig("...") names and the fixed terms in ALLOW removed; any digit left is an
   error naming file, line and text. Numbers go through #n("key") so they come from
   numbers.json and can't go stale.
3. privacy: no chapter and no numbers.json value may hold a string that looks like a hashed
   id (spirometry.export.HASH_VALUE). Aggregates only.
4. figures: every #fig("name", ...) in the chapters is looked up as
   writeup/figures/<name>.png. A missing file prints a labelled placeholder (listed in the
   report); a file older than the run tables in numbers.json's build stamp was drawn from
   older tables and stops the build.
5. compile: typst (PyPI, the "writeup" extra) compiles writeup/main.typ with the writeup
   folder as root to writeup/build/field_guide_v2.pdf. A key missing from numbers.json fails
   the compile (style.typ's n()).

The Typst side (writeup/style.typ): n(key) prints a key's formatted text; v1's boxes
(picture, words, project, plain, watch) plus skill; check(...) for stop-and-check boxes, whose
answers #answer-key() collects in Appendix A; fig(name, caption); ftable(...).
"""
import argparse, datetime, json, pathlib, re, sys

from spirometry.export import HASH_VALUE

PDF_NAME = "field_guide_v2.pdf"

# Fixed terms whose digits are part of a name, not a measured number. Keep this short: a
# number that comes from data goes through #n("key").
ALLOW = [
    (r"[Ww]eeks? 0[–-]3", "the fixed horizon's name (decision log 2026-10-09)"),
    (r"\bv\d+\.\d+\.\d+\b", "build names (v0.103.2)"),
    (r"\b(19|20)\d\d\b", "years"),
    (r"p ?\( ?1 ?[−-] ?p ?\)", "the variance of a 0/1 outcome, p(1 - p)"),
    (r"\|z\| ?> ?2\b", "the clearly-nonzero rule"),
    (r"\b95 ?%", "the confidence level's name"),
    (r"\bF ?< ?10\b", "the weak-instrument rule of thumb"),
    (r"\b2 ?× ?2\b", "the 2x2 table"),
    (r"\b(step|task|item|notebook|section) \d+[a-z]?\b", "PLAN.md / notebook numbering"),
    (r"\b0\d_[a-z_]+\b", "notebook and chapter file names (02_pick_rate_did)"),
    (r"Slay the Spire 2\b", "the game's name"),
]
_ALLOW = [re.compile(p) for p, _ in ALLOW]
_N_CALL = re.compile(r'#n\(\s*"[^"]*"\s*\)')
_FIG = re.compile(r'#fig\(\s*"([^"]+)"')
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)


class WriteupError(RuntimeError):
    pass


# ----------------------------------------------------------------------------------- lint

def _strip(text):
    """Chapter source with block comments blanked (line numbers kept)."""
    return _BLOCK_COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def lint_text(text, name="<text>"):
    """[(name, line number, line)] for every line with a digit outside #n(...), comments,
    #fig names, #import/#include lines and the ALLOW terms."""
    bad = []
    for i, line in enumerate(_strip(text).splitlines(), 1):
        s = line.split("//", 1)[0]
        if re.match(r"\s*#(import|include)\b", s):
            continue
        s = _N_CALL.sub("", s)
        s = _FIG.sub("#fig(", s)
        for p in _ALLOW:
            s = p.sub("", s)
        if re.search(r"\d", s):
            bad.append((name, i, line.strip()))
    return bad


def chapter_files(writeup):
    return sorted((pathlib.Path(writeup) / "chapters").glob("*.typ"))


def lint(writeup):
    bad = []
    for f in chapter_files(writeup):
        bad += lint_text(f.read_text(), str(f))
    return bad


# -------------------------------------------------------------------------------- privacy

def privacy(writeup, numbers_path):
    """Hashed-id-looking strings in the chapters or in numbers.json's text values."""
    hits = []
    for f in [*chapter_files(writeup), pathlib.Path(writeup) / "main.typ"]:
        if f.exists() and HASH_VALUE.search(f.read_text()):
            hits.append(str(f))
    nums = json.loads(pathlib.Path(numbers_path).read_text())["numbers"]
    for k, row in nums.items():
        for v in (row.get("text"), row.get("value") if isinstance(row.get("value"), str)
                  else None):
            if isinstance(v, str) and HASH_VALUE.search(v):
                hits.append(f"numbers.json {k}")
    return hits


# -------------------------------------------------------------------------------- figures

def figure_names(writeup):
    names = []
    for f in chapter_files(writeup):
        names += _FIG.findall(_strip(f.read_text()))
    return sorted(set(names))


def figures(writeup, built_at):
    """(present, missing, stale) figure names. Stale = the PNG is older than the run tables
    in the build stamp."""
    present, missing, stale = [], [], []
    for name in figure_names(writeup):
        p = pathlib.Path(writeup) / "figures" / f"{name}.png"
        if not p.exists():
            missing.append(name)
            continue
        t = datetime.datetime.fromtimestamp(p.stat().st_mtime, datetime.timezone.utc)
        (stale if t < built_at else present).append(name)
    return present, missing, stale


# ---------------------------------------------------------------------------------- build

def _numbers(writeup, refresh, analysis, results, snapshot_log, allow_sample):
    path = pathlib.Path(writeup) / "numbers.json"
    if refresh:
        from spirometry import numbers as N
        try:
            df, header = N.build(analysis, results, allow_sample, snapshot_log)
        except N.NumbersError as e:
            raise WriteupError(f"numbers: {e}") from None
        N.write(df, header, path)
    if not path.exists():
        raise WriteupError(f"{path} not found: run python -m spirometry.numbers, or build "
                           f"with --refresh-numbers")
    build = json.loads(path.read_text())["build"]
    if build.get("sample") and not allow_sample:
        raise WriteupError(f"{path} is from sample outputs; pass --allow-sample")
    return path, build


def compile_pdf(writeup, sys_inputs, out):
    try:
        import typst
    except ImportError:
        raise WriteupError("typst is not installed: pip install -e '.[writeup]'") from None
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        typst.compile(str(pathlib.Path(writeup) / "main.typ"), output=str(out),
                      root=str(writeup), sys_inputs=sys_inputs)
    except Exception as e:                      # typst.TypstError carries the message
        raise WriteupError(f"typst compile failed: {e}") from None
    return out


def build(writeup="writeup", refresh_numbers=False, analysis="data/analysis",
          results="results", snapshot_log="snapshot.log", allow_sample=False):
    """Every step. Returns a report dict: pdf, pages, figures missing (placeholders)."""
    writeup = pathlib.Path(writeup)
    numbers_path, stamp = _numbers(writeup, refresh_numbers, analysis, results,
                                   snapshot_log, allow_sample)
    bad = lint(writeup)
    if bad:
        raise WriteupError("digit lint: hand-typed digits (use #n(\"key\")):\n" + "\n".join(
            f"  {f}:{i}: {line}" for f, i, line in bad))
    hits = privacy(writeup, numbers_path)
    if hits:
        raise WriteupError(f"privacy: hashed-id-looking strings in {', '.join(hits)}")
    built_at = datetime.datetime.fromisoformat(stamp["tables_built_at_utc"])
    present, missing, stale = figures(writeup, built_at)
    if stale:
        raise WriteupError(f"figures older than the run tables ({built_at.isoformat()}): "
                           f"{', '.join(stale)}; rerun scripts/writeup/figures.py")
    pdf = compile_pdf(writeup, {"figures": ",".join(present)},
                      writeup / "build" / PDF_NAME)
    return dict(pdf=str(pdf), pages=page_count(pdf), figures_present=present,
                figures_missing=missing, sample=bool(stamp.get("sample")))


def page_count(pdf):
    """Pages in a PDF typst wrote (counts /Type /Page objects)."""
    return len(re.findall(rb"/Type\s*/Page(?![s\w])", pathlib.Path(pdf).read_bytes()))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="numbers -> lint -> privacy -> figures -> PDF")
    b.add_argument("--writeup", default="writeup")
    b.add_argument("--refresh-numbers", action="store_true",
                   help="rebuild writeup/numbers.json with spirometry.numbers first")
    b.add_argument("--analysis", default="data/analysis")
    b.add_argument("--results", default="results")
    b.add_argument("--snapshot-log", default="snapshot.log")
    b.add_argument("--allow-sample", action="store_true")
    a = p.parse_args(argv)
    try:
        r = build(a.writeup, a.refresh_numbers, a.analysis, a.results, a.snapshot_log,
                  a.allow_sample)
    except WriteupError as e:
        sys.exit(f"writeup build stopped: {e}")
    print(f"{r['pdf']}: {r['pages']} pages" + (" (SAMPLE DATA)" if r["sample"] else ""))
    if r["figures_missing"]:
        print("placeholders (figure not drawn yet): " + ", ".join(r["figures_missing"]))


if __name__ == "__main__":
    main()
