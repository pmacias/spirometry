"""Field guide v2 build: one command from the numbers table to the PDF.

    python -m spirometry.writeup build [--writeup writeup] [--refresh-numbers]
        [--analysis data/analysis] [--results results] [--snapshot-log snapshot.log]
        [--allow-sample]
    python -m spirometry.writeup listings [--writeup writeup]

Steps, each stopping the build on failure:

1. numbers: reuse writeup/numbers.json, or with --refresh-numbers rebuild it with
   spirometry.numbers (same inputs and guards). A sample numbers.json (build.sample: true) is
   refused unless --allow-sample; the title page then says SAMPLE DATA.
2. digit lint: every chapter (writeup/chapters/*.typ) is read with comments, #n("...")
   calls, #fig("...") / #listing("...") / #incode("...") names and the fixed terms in ALLOW
   removed; any digit left is an error naming file, line and text. Numbers go through
   #n("key") so they come from numbers.json and can't go stale. Math ($...$, display
   equations over several lines included) and inline code (`...`) follow a looser rule:
   single-digit integers are structure (coefficients, exponents, the 0/1 coding), but any
   multi-digit integer or decimal is an error unless ALLOW names it; a #n("key") inside
   math is fine. Errors give the line the offending token is on.
3. listings (also `python -m spirometry.writeup listings`): every #listing("name", ...) and
   #incode("name", ...) in the chapters is extracted from the package source with ast into
   writeup/listings/<name>.py (git-ignored), with writeup/listings/index.json (source file,
   function, line numbers). A name is a LISTINGS entry or "<module>.<function>" under
   spirometry (e.g. "teaching_sims.se_layers"). A name that doesn't resolve, a start/end
   pattern that no longer matches, or an excerpt over MAX_LISTING_LINES stops the build.
   Chapter files never hold code text; the digit lint doesn't see listings, only captions.
4. privacy: no chapter and no numbers.json value may hold a string that looks like a hashed
   id (spirometry.export.HASH_VALUE). Aggregates only.
5. figures: every #fig("name", ...) in the chapters is looked up as
   writeup/figures/<name>.png. A missing file prints a labelled placeholder (listed in the
   report); a file older than the run tables in numbers.json's build stamp was drawn from
   older tables and stops the build.
6. compile: typst (PyPI, the "writeup" extra) compiles writeup/main.typ with the writeup
   folder as root to writeup/build/field_guide_v2.pdf. A key missing from numbers.json fails
   the compile (style.typ's n()), as does a listing missing from the index.

The Typst side (writeup/style.typ): n(key) prints a key's formatted text; v1's boxes
(picture, words, project, plain, watch) plus skill; the rework's mixup (COMMON MIX-UP),
mathfull (THE MATH, IN FULL) and incode (IN CODE: a listing and its walk-through);
listing(name, caption); check(...) for stop-and-check boxes, whose answers #answer-key()
collects in Appendix A; fig(name, caption); ftable(...). Display equations are numbered by
chapter, (6.3).
"""
import argparse, ast, datetime, importlib, inspect, json, pathlib, re, sys

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
    (r"\b1\.96\b", "the normal quantile of a 95% interval, a constant (rework, 2026-10-22)"),
    (r"\b1\.4826\b", "MAD to SD under a normal distribution, 1 / Phi^-1(3/4), a constant"),
    (r"\b(HC|CR|CRV)1\b", "names of variance estimators (HC1, CR1, pyfixest's CRV1)"),
]
_ALLOW = [re.compile(p) for p, _ in ALLOW]
_N_CALL = re.compile(r'#n\(\s*"[^"]*"\s*\)')
_FIG = re.compile(r'#fig\(\s*"([^"]+)"')
_LISTING = re.compile(r'#(?:listing|incode)\(\s*"([^"]+)"')
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)
# Math ($...$, unescaped dollars) and code (```...``` or `...`), found in one pass so a
# dollar inside code doesn't open math.
_SPAN = re.compile(r"```.*?```|`[^`]*`|(?<!\\)\$.*?(?<!\\)\$", re.S)
# Inside math and code: a decimal or a multi-digit integer is data-like.
_SPAN_BAD = re.compile(r"\d*\.\d+|\d{2,}")


class WriteupError(RuntimeError):
    pass


# ----------------------------------------------------------------------------------- lint

def _strip(text):
    """Chapter source with block comments blanked (line numbers kept)."""
    return _BLOCK_COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def _allow(s):
    for p in _ALLOW:
        s = p.sub("", s)
    return s


def lint_text(text, name="<text>"):
    """[(name, line number, line)] for every line with a digit outside #n(...), comments,
    #fig / #listing / #incode names, #import/#include lines and the ALLOW terms. Inside
    math and inline code only multi-digit integers and decimals count (see the module
    docstring); the line reported is the one the offending token is on."""
    lines = _strip(text).splitlines()
    original = text.splitlines()
    kept = []
    for line in lines:
        s = line.split("//", 1)[0]
        if re.match(r"\s*#(import|include)\b", s):
            s = ""
        s = _N_CALL.sub("", s)
        s = _FIG.sub("#fig(", s)
        s = _LISTING.sub("#listing(", s)
        kept.append(s)
    body = "\n".join(kept)
    bad = set()

    def span(m):
        inner = _allow(m.group(0))
        for t in _SPAN_BAD.finditer(inner):
            bad.add(body.count("\n", 0, m.start()) + inner.count("\n", 0, t.start()) + 1)
        return "\n" * m.group(0).count("\n")          # keep line numbers

    body = _SPAN.sub(span, body)
    for i, s in enumerate(body.split("\n"), 1):
        if re.search(r"\d", _allow(s)):
            bad.add(i)
    return [(name, i, original[i - 1].strip()) for i in sorted(bad)]


def chapter_files(writeup):
    return sorted((pathlib.Path(writeup) / "chapters").glob("*.typ"))


def lint(writeup):
    bad = []
    for f in chapter_files(writeup):
        bad += lint_text(f.read_text(), str(f))
    return bad


# ------------------------------------------------------------------------------- listings

MAX_LISTING_LINES = 60      # a listing must fit a page; show the core of a longer function

# Listings that need more than "<module>.<function>": several functions in one listing, an
# excerpt (start / end: patterns for the first and last body lines kept, "# ..." marks the
# cut) or a shortened docstring (doc: "full", "first" paragraph, or "none").
LISTINGS = {
    "did.fit_did": dict(source=["did:_fixed_effects", "did:_feols", "did:_fit_did"]),
    "did.subset_columns": dict(source="did:_subset", start=r'd\["is_treated"\] =',
                               end=r'd\["asc"\] =', doc="first"),
}


def listing_names(writeup):
    names = []
    for f in chapter_files(writeup):
        names += _LISTING.findall(_strip(f.read_text()))
    return sorted(set(names))


def _find(module, qualname):
    """(display path, source lines, ast node) of a function or class under spirometry."""
    try:
        mod = importlib.import_module(f"spirometry.{module}")
    except ImportError:
        raise WriteupError(f"listing: no module spirometry.{module}") from None
    path = pathlib.Path(inspect.getsourcefile(mod))
    src = path.read_text().splitlines()
    node = ast.parse("\n".join(src))
    for part in qualname.split("."):
        node = next((n for n in ast.iter_child_nodes(node) if n.__class__.__name__ in
                     ("FunctionDef", "AsyncFunctionDef", "ClassDef") and n.name == part), None)
        if node is None:
            raise WriteupError(f"listing: spirometry.{module} has no {qualname}")
    return f"spirometry/{module}.py", src, node


def _excerpt(module, qualname, start=None, end=None, doc="full"):
    """[(source line number or None, text)] for one function, trimmed as asked."""
    path, src, node = _find(module, qualname)
    line = lambda i: (i, src[i - 1])
    first = min([node.lineno] + [d.lineno for d in node.decorator_list])
    out = [line(i) for i in range(first, node.body[0].lineno)]           # def and signature
    body = node.body
    ds = body[0] if (isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant)
                     and isinstance(body[0].value.value, str)) else None
    indent = re.match(r"\s*", src[body[0].lineno - 1]).group(0)
    if ds is not None:
        doc_lines = [line(i) for i in range(ds.lineno, ds.end_lineno + 1)]
        if doc == "first":
            short = []
            for n, t in doc_lines:
                if not t.strip():
                    break
                short.append((n, t))
            out += short if len(short) == len(doc_lines) else short + [(None, indent + '..."""')]
        elif doc == "full":
            out += doc_lines
        body = body[1:]
    if not body:
        return path, out
    rest = [line(i) for i in range(body[0].lineno, node.end_lineno + 1)]
    if start or end:
        texts = [t for _, t in rest]
        lo = next((k for k, t in enumerate(texts) if re.search(start, t)), None) if start else 0
        if lo is None:
            raise WriteupError(f"listing: start pattern {start!r} not in {module}.{qualname}")
        hi = (next((k for k in range(lo, len(texts)) if re.search(end, texts[k])), None)
              if end else len(texts) - 1)
        if hi is None:
            raise WriteupError(f"listing: end pattern {end!r} not in {module}.{qualname}")
        cut = rest[lo:hi + 1]
        if lo > 0:
            cut = [(None, indent + "# ...")] + cut
        if hi < len(rest) - 1:
            cut = cut + [(None, indent + "# ...")]
        rest = cut
    return path, out + rest


def extract_listing(name):
    """(code text, index entry) for a listing name."""
    spec = LISTINGS.get(name)
    if spec is None:
        module, _, qual = name.partition(".")
        if not qual:
            raise WriteupError(f"listing: {name!r} is neither in LISTINGS nor <module>.<function>")
        spec = dict(source=f"{module}:{qual}")
    sources = spec["source"] if isinstance(spec["source"], list) else [spec["source"]]
    opts = {k: v for k, v in spec.items() if k != "source"}
    lines, paths, quals = [], [], []
    for s in sources:
        module, qual = s.split(":")
        path, part = _excerpt(module, qual, **opts)
        lines += ([(None, "")] if lines else []) + part
        paths.append(path)
        quals.append(qual)
    if len(lines) > MAX_LISTING_LINES:
        raise WriteupError(f"listing {name}: {len(lines)} lines (> {MAX_LISTING_LINES}); "
                           "show the core with start/end in LISTINGS")
    nums = [n for n, _ in lines if n is not None]
    entry = dict(path=", ".join(sorted(set(paths))), functions=", ".join(quals),
                 first=min(nums), last=max(nums),
                 numbers=["" if n is None else str(n) for n, _ in lines])
    return "\n".join(t for _, t in lines) + "\n", entry


def write_listings(writeup):
    """Extract every listing the chapters use into writeup/listings/ (old files removed).
    Returns the index {name: entry}."""
    d = pathlib.Path(writeup) / "listings"
    d.mkdir(parents=True, exist_ok=True)
    for old in d.glob("*.py"):
        old.unlink()
    index = {}
    for name in listing_names(writeup):
        code, entry = extract_listing(name)
        (d / f"{name}.py").write_text(code)
        index[name] = entry
    (d / "index.json").write_text(json.dumps(index, indent=1) + "\n")
    return index


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
    listings = write_listings(writeup)
    hits = privacy(writeup, numbers_path)
    if hits:
        raise WriteupError(f"privacy: hashed-id-looking strings in {', '.join(hits)}")
    built_at = datetime.datetime.fromisoformat(stamp["tables_built_at_utc"])
    present, missing, stale = figures(writeup, built_at)
    if stale:
        raise WriteupError(f"figures older than the run tables ({built_at.isoformat()}): "
                           f"{', '.join(stale)}; rerun scripts/writeup/figures.py")
    pdf = compile_pdf(writeup, {"figures": ",".join(present),
                                "listings": json.dumps(listings)},
                      writeup / "build" / PDF_NAME)
    return dict(pdf=str(pdf), pages=page_count(pdf), figures_present=present,
                figures_missing=missing, listings=sorted(listings),
                sample=bool(stamp.get("sample")))


def page_count(pdf):
    """Pages in a PDF typst wrote (counts /Type /Page objects)."""
    return len(re.findall(rb"/Type\s*/Page(?![s\w])", pathlib.Path(pdf).read_bytes()))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="numbers -> lint -> listings -> privacy -> figures -> PDF")
    b.add_argument("--writeup", default="writeup")
    b.add_argument("--refresh-numbers", action="store_true",
                   help="rebuild writeup/numbers.json with spirometry.numbers first")
    b.add_argument("--analysis", default="data/analysis")
    b.add_argument("--results", default="results")
    b.add_argument("--snapshot-log", default="snapshot.log")
    b.add_argument("--allow-sample", action="store_true")
    li = sub.add_parser("listings", help="extract the chapters' code listings only")
    li.add_argument("--writeup", default="writeup")
    a = p.parse_args(argv)
    if a.cmd == "listings":
        try:
            index = write_listings(a.writeup)
        except WriteupError as e:
            sys.exit(f"listings stopped: {e}")
        for name, e in index.items():
            print(f"{name}: {e['path']} {e['functions']}, lines {e['first']}-{e['last']}")
        print(f"{len(index)} listings -> {pathlib.Path(a.writeup) / 'listings'}/")
        return
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
