"""The field guide's numbers table: every number the write-up prints, by key, from the saved
final-rerun outputs.

    python -m spirometry.numbers --analysis data/analysis --results results \
        --out writeup/numbers.json [--snapshot-log snapshot.log] [--allow-sample]

Writes writeup/numbers.json (read by the Typst source: #n("key")) and writeup/numbers.csv
beside it (the same rows, for reading). One row per number:

    key        dotted lower-case name, e.g. dose.primary.h3.slope_first
    value      the number as computed (JSON number or string)
    text       the number as printed: decimals, ±, signs, thousands separators. Formatting
               happens here and nowhere else; negatives use the minus sign (U+2212).
    source     the file it came from
    column     the column and filter that produced it
    horizon    "weeks 0-3", "all weeks" or "" (not a fit)
    spec       which tweaks are on the dose line ("triage" = the notebooks' 38, "primary" =
               the 2026-10-09 spec; spirometry.sensitivity.SPECS), or ""
    build      the build stamp: tables built at, pages, parser version
    appendix   true for the rows the reproducibility appendix lists

Inputs (nothing else is read; the run database is never opened):

    results/meta.json                            build stamp and play-date range (written
                                                 by spirometry.export with --db), pages
    results/pick_rate_did.csv                    per-tweak DiD, both horizons
    results/dose_response.csv                    the notebooks' meta-regressions (triage spec)
    <analysis>/writeup/rulers.csv                spirometry.sensitivity: slopes per spec
    <analysis>/writeup/se_inflation.csv          same, SEs scaled by the placebo spread
    <analysis>/writeup/calibrated_counts.csv     same: clearly nonzero on placebo-scaled z
    <analysis>/placebo_diagnostics_summary.csv   placebo calibration, z spread
    snapshot.log                                 the download log (scripts/snapshot_export.py):
                                                 last page and --count-only's records total.
                                                 Only three kinds of line are read (page
                                                 lines, "reached end of export", "total").
                                                 It predates the tables, so it is exempt from
                                                 the staleness check.

Guards (each stops the run and writes nothing):
- Build stamp: results/meta.json must carry tables_built_at_utc, snapshot_pages,
  parser_version, snapshot_start_date and snapshot_end_date. A sample export (meta.json
  "sample": true) is refused unless --allow-sample.
- Snapshot log: it must say "reached end of export" and have a "total" line, and its last
  page (numbered from 1) must equal meta.json's snapshot_pages.
- Calibrated counts: calibrated_counts.csv's uncalibrated rows (spread "none") must equal
  the counts from pick_rate_did.csv, so both use the same tweaks and rule.
- Staleness: an input file last modified before tables_built_at_utc was not made from these
  tables; the run names it.
- Privacy: every input table and the output pass spirometry.export.check_output
  (identifier columns, hashed-id-looking strings). Aggregates only.
- A value that is missing in its source stops the run (no blank numbers in the text).

Counting rules (as the export and SPIROMETRY.md define them):
- uncalibrated clearly nonzero (did.<h>.<patch>.uncalibrated.*) = |beta| > 2 clustered SE
  (export's clearly_nonzero / clearly_nonzero_h).
- calibrated clearly nonzero (did.<h>.<patch>.calibrated.*, the lead count by the decision
  log): |z / factor| > 2, factor = the patch's robust placebo sd at the same horizon;
  calibrated_plain_sd.* is the same with the plain placebo sd (sensitivity). Computed by
  spirometry.sensitivity.calibrated_counts; formatted here. A horizon without placebo fits
  has no keys and is listed under "missing" in numbers.json's build header.
- toward the change = export.toward_change (sign(beta) = sign(direction x ln ratio), for
  tweaks with one direction: not mixed, not upgrade-only), on beta for all weeks and on
  beta_h for weeks 0-3 (the export has no weeks 0-3 column for it).
- median |beta| in percentage points (beta x 100), all solo-estimable tweaks of the patch.
- Placebo spreads are all-weeks fits (the placebo calibration ran on all weeks).
"""
import argparse, datetime, json, math, pathlib, re, sys

import numpy as np
import pandas as pd

from spirometry.export import ExportError, check_output, toward_change

MINUS = "−"
KEY = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)*$")
HORIZONS = {"h3": "weeks 0-3", "all": "all weeks"}
HORIZON_KEY = {v: k for k, v in HORIZONS.items()}
SPREAD_KEY = {"robust sd": "calibrated", "sd": "calibrated_plain_sd"}
PATCHES = ["first", "second"]
COLUMNS = ["key", "value", "text", "source", "column", "horizon", "spec", "build",
           "appendix"]


class NumbersError(RuntimeError):
    pass


# -------------------------------------------------------------------------- formatting

def fmt_int(n):
    """2071 -> '2,071'."""
    return f"{int(n):,}".replace("-", MINUS)


def fmt_num(x, decimals=2, sign=False):
    """Fixed decimals, minus sign for negatives, '+' for positives when sign=True. A value
    that rounds to zero prints without a sign."""
    s = f"{abs(x):.{decimals}f}"
    if float(s) == 0:
        return s
    if x < 0:
        return MINUS + s
    return ("+" + s) if sign else s


def fmt_pm(x, se, decimals=2, sign=False):
    return f"{fmt_num(x, decimals, sign)} ± {fmt_num(se, decimals)}"


def fmt_pct(share, decimals=0):
    """0.715 -> '72%'."""
    return f"{fmt_num(100 * share, decimals)}%"


def fmt_time(iso):
    """'2026-10-09T21:18:20+00:00' -> '2026-10-09 21:18 UTC'."""
    t = datetime.datetime.fromisoformat(iso).astimezone(datetime.timezone.utc)
    return t.strftime("%Y-%m-%d %H:%M UTC")


# -------------------------------------------------------------------------------- rows

class Table:
    """Collects rows; refuses a bad key, a repeat or a missing value."""

    def __init__(self, build):
        self.build, self.rows = build, []

    def add(self, key, value, text, source, column, horizon="", spec="", appendix=False):
        if not KEY.match(key):
            raise NumbersError(f"bad key {key!r}: lower-case words joined by dots")
        if any(r["key"] == key for r in self.rows):
            raise NumbersError(f"key {key} defined twice")
        if value is None or (isinstance(value, float) and not math.isfinite(value)):
            raise NumbersError(f"{key}: value missing in {source} ({column})")
        if isinstance(value, (np.integer,)):
            value = int(value)
        elif isinstance(value, (np.floating,)):
            value = float(value)
        self.rows.append(dict(key=key, value=value, text=text, source=source, column=column,
                              horizon=horizon, spec=spec, build=self.build,
                              appendix=bool(appendix)))

    def estimate(self, key, est, se, decimals, source, column, sign=False, **kw):
        """Three keys: <key> (estimate), <key>_se, <key>_pm ('1.40 ± 0.19')."""
        self.add(key, est, fmt_num(est, decimals, sign), source, column, **kw)
        self.add(f"{key}_se", se, fmt_num(se, decimals), source, f"{column} (se)", **kw)
        self.add(f"{key}_pm", [float(est), float(se)], fmt_pm(est, se, decimals, sign),
                 source, f"{column} (estimate ± se)", **kw)

    def count(self, key, n, source, column, **kw):
        self.add(key, int(n), fmt_int(n), source, column, **kw)

    def frame(self):
        return pd.DataFrame(self.rows, columns=COLUMNS)


# ------------------------------------------------------------------------------ inputs

def _paths(analysis, results):
    a, r = pathlib.Path(analysis), pathlib.Path(results)
    return {"meta": r / "meta.json",
            "pick_rate": r / "pick_rate_did.csv",
            "dose": r / "dose_response.csv",
            "rulers": a / "writeup" / "rulers.csv",
            "se_inflation": a / "writeup" / "se_inflation.csv",
            "calibrated": a / "writeup" / "calibrated_counts.csv",
            "placebo": a / "placebo_diagnostics_summary.csv"}


def read_stamp(meta, allow_sample=False):
    """The build stamp from results/meta.json; refuses a blank stamp or a sample export."""
    if meta.get("sample") and not allow_sample:
        raise NumbersError("results/meta.json is a sample export (sample: true); "
                           "pass --allow-sample to build from it")
    need = ["tables_built_at_utc", "snapshot_pages", "parser_version",
            "snapshot_start_date", "snapshot_end_date"]
    blank = [k for k in need if not str(meta.get(k, "")).strip()]
    if blank:
        raise NumbersError(f"results/meta.json has no build stamp or play dates "
                           f"({', '.join(blank)} blank): rerun spirometry.export with --db")
    built = datetime.datetime.fromisoformat(meta["tables_built_at_utc"])
    if built.tzinfo is None:
        raise NumbersError("tables_built_at_utc has no time zone")
    return built


def check_fresh(paths, built):
    """Every input must be at least as new as the tables it was computed from."""
    old = []
    for p in paths:
        t = datetime.datetime.fromtimestamp(p.stat().st_mtime, datetime.timezone.utc)
        if t < built:
            old.append(f"{p} (modified {t.isoformat(timespec='seconds')})")
    if old:
        raise NumbersError(f"input(s) older than the run tables (built "
                           f"{built.isoformat(timespec='seconds')}): {'; '.join(old)}")


PAGE_LINE = re.compile(r"\bpage (\d+): \d+ runs\b")
TOTAL_LINE = re.compile(r"^total\s+(\d+)\s+(\d+)\s*$")


def read_snapshot_log(path):
    """(last page, records) from the download log: the last "page N: ... runs" line (the
    log numbers pages from 1, so N is the page count; files are 0 .. N-1) and the first
    column of --count-only's "total" line (records, repeats included; the second column,
    distinct runs, is not used). Refuses a log without "reached end of export"."""
    last = records = None
    end = False
    for line in pathlib.Path(path).read_text().splitlines():
        m = PAGE_LINE.search(line)
        if m:
            last = int(m.group(1))
        elif "reached end of export" in line:
            end = True
        else:
            m = TOTAL_LINE.match(line.strip())
            if m:
                records = int(m.group(1))
    if not end:
        raise NumbersError(f"{path}: no 'reached end of export' line (snapshot unfinished)")
    if last is None or records is None:
        raise NumbersError(f"{path}: no page lines or no 'total' line")
    return last, records


def private(name, df):
    """spirometry.export's privacy check, as a NumbersError."""
    try:
        check_output(name, df)
    except ExportError as e:
        raise NumbersError(f"privacy check: {e}") from None


def load(analysis="data/analysis", results="results", allow_sample=False,
         snapshot_log="snapshot.log"):
    """Read and check every input. Returns (meta, built, tables, paths, log)."""
    paths = _paths(analysis, results)
    missing = [str(p) for p in [*paths.values(), pathlib.Path(snapshot_log)]
               if not p.exists()]
    if missing:
        raise NumbersError(f"missing input(s): {', '.join(missing)}")
    meta = json.loads(paths["meta"].read_text())
    built = read_stamp(meta, allow_sample)
    check_fresh(paths.values(), built)
    tables = {}
    for name, p in paths.items():
        if name == "meta":
            continue
        df = pd.read_csv(p)
        private(str(p), df)
        tables[name] = df
    last, records = read_snapshot_log(snapshot_log)
    if str(last) != str(meta["snapshot_pages"]).strip():
        raise NumbersError(f"{snapshot_log} ends at page {last}, results/meta.json says "
                           f"{meta['snapshot_pages']} pages")
    return meta, built, tables, paths, dict(last_page=last, records=records)


# ------------------------------------------------------------------------------- keys

def _one(df, source, **where):
    """The single row of `df` matching `where`; refuses none or several."""
    m = pd.Series(True, index=df.index)
    for c, v in where.items():
        m &= df[c].astype(str) == str(v)
    if m.sum() != 1:
        raise NumbersError(f"{source}: {int(m.sum())} rows match {where}, expected 1")
    return df[m].iloc[0]


def _filter(where):
    return ", ".join(f"{c} = {v}" for c, v in where.items())


def provenance_keys(T, meta, src, log, src_log):
    T.add("build.tables_built_at", meta["tables_built_at_utc"],
          fmt_time(meta["tables_built_at_utc"]), src, "tables_built_at_utc", appendix=True)
    T.add("build.parser_version", str(meta["parser_version"]), str(meta["parser_version"]),
          src, "parser_version", appendix=True)
    T.count("snapshot.pages", int(meta["snapshot_pages"]), src, "snapshot_pages",
            appendix=True)
    T.count("snapshot.last_page", log["last_page"], src_log,
            "last 'page N: ... runs' line (pages numbered from 1; files 0 to N-1)",
            appendix=True)
    T.count("snapshot.records", log["records"], src_log,
            "'total' line, first column (records read, repeats included)", appendix=True)
    for k in ["start", "end"]:
        T.add(f"snapshot.{k}_date", meta[f"snapshot_{k}_date"], meta[f"snapshot_{k}_date"],
              src, f"snapshot_{k}_date ({meta.get('snapshot_dates_source', '')})",
              appendix=True)
    if str(meta.get("exported_at_utc", "")).strip():
        T.add("build.results_exported_at", meta["exported_at_utc"],
              fmt_time(meta["exported_at_utc"]), src, "exported_at_utc", appendix=True)


def did_keys(T, p, src):
    """Tweak counts, uncalibrated clearly nonzero (clustered SE), toward the change and
    median |beta|, per patch and horizon. Returns the counts, for the check against
    calibrated_counts.csv's uncalibrated rows."""
    counts = {}
    T.count("tweaks.solo_estimable", len(p), src, "rows")
    for pt in PATCHES:
        T.count(f"tweaks.{pt}", (p.patch == pt).sum(), src, f"rows, patch = {pt}")
    single = (p.mixed_direction != "yes") & (p.upgrade_only != "yes")
    for hz, (b, s, cn) in {"all": ("beta", "se", "clearly_nonzero"),
                           "h3": ("beta_h", "se_h", "clearly_nonzero_h")}.items():
        horizon = HORIZONS[hz]
        toward = pd.Series(toward_change(p[b], p.dose_x, single), index=p.index)
        for pt in PATCHES:
            g = p.patch == pt
            clear = g & (p[cn] == "yes")
            n = dict(n_clearly_nonzero=int(clear.sum()),
                     n_clearly_nonzero_with_direction=int((clear & (toward != "")).sum()),
                     n_toward=int((clear & (toward == "yes")).sum()))
            counts[(horizon, pt)] = n
            pre = f"did.{hz}.{pt}.uncalibrated"
            what = f"uncalibrated: {cn} = yes (|{b}| > 2 clustered {s}), patch = {pt}"
            T.count(f"{pre}.clearly_nonzero", n["n_clearly_nonzero"], src, what,
                    horizon=horizon)
            T.count(f"{pre}.clearly_nonzero_with_direction",
                    n["n_clearly_nonzero_with_direction"], src,
                    f"{what}; not mixed, not upgrade-only", horizon=horizon)
            T.count(f"{pre}.clearly_nonzero_toward", n["n_toward"], src,
                    f"{what}; export.toward_change({b}) = yes", horizon=horizon)
            med = 100 * p.loc[g, b].abs().median()
            T.add(f"did.{hz}.{pt}.median_abs_beta_pp", med, fmt_num(med, 1), src,
                  f"median |{b}| x 100, patch = {pt}", horizon=horizon)
    return counts


def calibrated_keys(T, c, src, uncalibrated):
    """Clearly nonzero on placebo-scaled z (calibrated_counts.csv), per patch, horizon and
    spread. Checks the file's uncalibrated rows against pick_rate_did.csv's counts. Returns
    the keys left out (no placebo fits at that horizon), with the reason."""
    missing = []
    for r in c.itertuples():
        hz = HORIZON_KEY.get(r.horizon)
        if hz is None:
            raise NumbersError(f"{src}: unknown horizon {r.horizon!r}")
        if r.spread == "none":
            mine = uncalibrated.get((r.horizon, r.patch))
            theirs = dict(n_clearly_nonzero=r.n_clearly_nonzero,
                          n_clearly_nonzero_with_direction=r.n_clearly_nonzero_with_direction,
                          n_toward=r.n_toward)
            if mine is None or any(int(theirs[k]) != v for k, v in mine.items()):
                raise NumbersError(f"{src}: uncalibrated counts ({r.horizon}, {r.patch}) "
                                   f"{theirs} differ from pick_rate_did.csv's {mine}")
            continue
        pre = f"did.{hz}.{r.patch}.{SPREAD_KEY[r.spread]}"
        if r.status != "ok":
            missing.append(dict(keys=f"{pre}.*", reason=str(r.status)))
            continue
        w = f"horizon = {r.horizon}, patch = {r.patch}, spread = {r.spread}"
        kw = dict(horizon=r.horizon)
        T.add(f"{pre}.factor", float(r.factor), fmt_num(r.factor, 2), src, f"factor, {w}",
              **kw)
        T.count(f"{pre}.n_placebo", r.n_placebo, src, f"n_placebo (window, pseudo card "
                f"pairs), {w}", **kw)
        T.count(f"{pre}.n_tweaks", r.n_tweaks, src, f"n_tweaks, {w}", **kw)
        T.count(f"{pre}.clearly_nonzero", r.n_clearly_nonzero, src,
                f"n_clearly_nonzero (|z / factor| > 2), {w}", **kw)
        T.count(f"{pre}.clearly_nonzero_with_direction", r.n_clearly_nonzero_with_direction,
                src, f"n_clearly_nonzero_with_direction, {w}", **kw)
        T.count(f"{pre}.clearly_nonzero_toward", r.n_toward, src, f"n_toward, {w}", **kw)
    return missing


def dose_keys(T, dose, rulers, se_inf, src_dose, src_rulers, src_se):
    """Dose-response slopes: the notebooks' 38 (triage spec) from the export, the primary
    spec from spirometry.sensitivity, and the primary spec with placebo-scaled SEs."""
    for hz, label in [("h3", "weeks 0-3"), ("all", "all weeks")]:
        for term, name in [("slope_first", "slope_first"), ("slope_second", "slope_second")]:
            w = dict(horizon=label, model="slope per patch", term=term)
            r = _one(dose, src_dose, **w)
            T.estimate(f"dose.triage.{hz}.{name}", r.coef, r.se, 2, src_dose,
                       f"coef, {_filter(w)}", horizon=label, spec="triage")
        w = dict(horizon=label, model="one slope", term="slope")
        r = _one(dose, src_dose, **w)
        T.estimate(f"dose.triage.{hz}.one_slope", r.coef, r.se, 2, src_dose,
                   f"coef, {_filter(w)}", horizon=label, spec="triage")
        T.count(f"dose.triage.{hz}.n_tweaks", r.n_tweaks, src_dose,
                f"n_tweaks, {_filter(w)}", horizon=label, spec="triage")

    for spec in ["triage", "primary"]:
        w = dict(fits="did_h3", spec=spec, ruler="ln(new/old)")
        r = _one(rulers, src_rulers, **w)
        kw = dict(horizon="weeks 0-3", spec=spec)
        if spec == "primary":
            T.estimate("dose.primary.h3.slope_first", r.slope1, r.se1, 2, src_rulers,
                       f"slope1, {_filter(w)}", **kw)
            T.estimate("dose.primary.h3.slope_second", r.slope2, r.se2, 2, src_rulers,
                       f"slope2, {_filter(w)}", **kw)
            T.count("dose.primary.h3.n_first", r.n1, src_rulers, f"n1, {_filter(w)}", **kw)
            T.count("dose.primary.h3.n_second", r.n2, src_rulers, f"n2, {_filter(w)}", **kw)
        T.add(f"dose.{spec}.h3.z_diff", float(r.z_diff), fmt_num(r.z_diff, 2), src_rulers,
              f"z_diff, {_filter(w)}", **kw)

    for setting, name in [("robust sd by patch", "placebo_robust_sd"),
                          ("sd by patch", "placebo_sd")]:
        w = dict(label="primary, weeks 0-3 (did_h3)", setting=setting)
        r = _one(se_inf, src_se, **w)
        kw = dict(horizon="weeks 0-3", spec="primary")
        T.estimate(f"dose.primary.h3.{name}.slope_first", r.slope1, r.se1, 2, src_se,
                   f"slope1, {_filter(w)}", **kw)
        T.estimate(f"dose.primary.h3.{name}.slope_second", r.slope2, r.se2, 2, src_se,
                   f"slope2, {_filter(w)}", **kw)
        T.add(f"dose.primary.h3.{name}.z_diff", float(r.z_diff), fmt_num(r.z_diff, 2),
              src_se, f"z_diff, {_filter(w)}", **kw)
        for i, pt in [(1, "first"), (2, "second")]:
            f = float(r[f"factor{i}"])
            T.add(f"dose.primary.h3.{name}.factor_{pt}", f, fmt_num(f, 2), src_se,
                  f"factor{i}, {_filter(w)}", **kw)


def placebo_keys(T, pl, src):
    """Spread of placebo z (honest errors: sd 1), every fit and one row per (window,
    pseudo card) pair."""
    kw = dict(horizon="all weeks")
    for dedupe, tag in [(False, "fits"), (True, "pairs")]:
        d = pl[pl.dedupe.astype(str).str.lower() == str(dedupe).lower()]
        for split, level in [("all", "all"), ("patch", "first"), ("patch", "second")]:
            w = dict(dedupe=dedupe, split=split, level=level)
            r = _one(d, src, split=split, level=level)
            name = "all" if level == "all" else level
            T.add(f"placebo.{tag}.{name}.sd_z", float(r.sd_z), fmt_num(r.sd_z, 2), src,
                  f"sd_z, {_filter(w)}", **kw)
            T.add(f"placebo.{tag}.{name}.robust_sd_z", float(r.robust_sd_z),
                  fmt_num(r.robust_sd_z, 2), src, f"robust_sd_z, {_filter(w)}", **kw)
            T.add(f"placebo.{tag}.{name}.share_abs_z_gt2", float(r.share_abs_z_gt2),
                  fmt_pct(r.share_abs_z_gt2), src, f"share_abs_z_gt2, {_filter(w)}", **kw)
            T.count(f"placebo.{tag}.{name}.n", r.n_fits, src, f"n_fits, {_filter(w)}", **kw)


# ------------------------------------------------------------------------------- build

def build(analysis="data/analysis", results="results", allow_sample=False,
          snapshot_log="snapshot.log"):
    """Every key, checked. Returns (rows DataFrame, header dict)."""
    meta, built, t, paths, log = load(analysis, results, allow_sample, snapshot_log)
    stamp = (f"tables built {meta['tables_built_at_utc']}; {meta['snapshot_pages']} pages; "
             f"parser {meta['parser_version']}")
    T = Table(stamp)
    provenance_keys(T, meta, str(paths["meta"]), log, str(snapshot_log))
    unc = did_keys(T, t["pick_rate"], str(paths["pick_rate"]))
    missing = calibrated_keys(T, t["calibrated"], str(paths["calibrated"]), unc)
    dose_keys(T, t["dose"], t["rulers"], t["se_inflation"], str(paths["dose"]),
              str(paths["rulers"]), str(paths["se_inflation"]))
    placebo_keys(T, t["placebo"], str(paths["placebo"]))
    df = T.frame()
    # numeric values aren't text: 16 digits of a float would read as a hashed id
    private("numbers", df.assign(value=df.value.map(lambda v: v if isinstance(v, str)
                                                    else "")))
    header = dict(sample=bool(meta.get("sample")),
                  generated_at_utc=datetime.datetime.now(datetime.timezone.utc)
                  .isoformat(timespec="seconds"),
                  tables_built_at_utc=meta["tables_built_at_utc"],
                  snapshot_pages=str(meta["snapshot_pages"]),
                  parser_version=str(meta["parser_version"]),
                  missing=missing,
                  inputs={str(p): datetime.datetime.fromtimestamp(
                      p.stat().st_mtime, datetime.timezone.utc).isoformat(timespec="seconds")
                      for p in [*paths.values(), pathlib.Path(snapshot_log)]})
    return df, header


def write(df, header, out):
    """numbers.json ({build: header, numbers: {key: row}}) and numbers.csv beside it."""
    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = {r["key"]: {k: v for k, v in r.items() if k != "key"}
            for r in df.to_dict("records")}
    out.write_text(json.dumps(dict(build=header, numbers=rows), indent=2,
                              ensure_ascii=False) + "\n")
    df.to_csv(out.with_suffix(".csv"), index=False)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--analysis", default="data/analysis")
    p.add_argument("--results", default="results")
    p.add_argument("--out", default="writeup/numbers.json")
    p.add_argument("--snapshot-log", default="snapshot.log")
    p.add_argument("--allow-sample", action="store_true",
                   help="build from a sample export (results/meta.json sample: true)")
    a = p.parse_args(argv)
    try:
        df, header = build(a.analysis, a.results, a.allow_sample, a.snapshot_log)
    except NumbersError as e:
        sys.exit(f"numbers stopped: {e}")
    write(df, header, a.out)
    print(f"{len(df)} numbers ({int(df.appendix.sum())} for the appendix), tables built "
          f"{header['tables_built_at_utc']}, {header['snapshot_pages']} pages")
    for m in header["missing"]:
        print(f"missing: {m['keys']} ({m['reason']})")
    print(f"-> {a.out}, {pathlib.Path(a.out).with_suffix('.csv')}")


if __name__ == "__main__":
    main()
