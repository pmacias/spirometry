"""The field guide's numbers table: every number the write-up prints, by key, from the saved
final-rerun outputs.

    python -m spirometry.numbers --analysis data/analysis --results results \
        --out writeup/numbers.json [--allow-sample]

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

    results/meta.json                            build stamp (written by spirometry.export
                                                 with --db), snapshot pages
    results/pick_rate_did.csv                    per-tweak DiD, both horizons
    results/dose_response.csv                    the notebooks' meta-regressions (triage spec)
    <analysis>/writeup/rulers.csv                spirometry.sensitivity: slopes per spec
    <analysis>/writeup/se_inflation.csv          same, SEs scaled by the placebo spread
    <analysis>/placebo_diagnostics_summary.csv   placebo calibration, z spread

Guards (each stops the run and writes nothing):
- Build stamp: results/meta.json must carry tables_built_at_utc, snapshot_pages and
  parser_version. A sample export (meta.json "sample": true) is refused unless
  --allow-sample.
- Staleness: an input file last modified before tables_built_at_utc was not made from these
  tables; the run names it.
- Privacy: every input table and the output pass spirometry.export.check_output
  (identifier columns, hashed-id-looking strings). Aggregates only.
- A value that is missing in its source stops the run (no blank numbers in the text).

Counting rules (as the export and SPIROMETRY.md define them):
- clearly nonzero = |beta| > 2 clustered SE (export's clearly_nonzero / clearly_nonzero_h).
- toward the change = sign(beta) = sign(direction x ln ratio), for tweaks with one
  direction (not mixed, not upgrade-only): the export's toward_change for all weeks; the
  same rule on beta_h for weeks 0-3 (the export has no weeks 0-3 column for it).
- median |beta| in percentage points (beta x 100), all solo-estimable tweaks of the patch.
- Placebo spreads are all-weeks fits (the placebo calibration ran on all weeks).
"""
import argparse, datetime, json, math, pathlib, re, sys

import numpy as np
import pandas as pd

from spirometry.export import ExportError, check_output

MINUS = "−"
KEY = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)*$")
HORIZONS = {"h3": "weeks 0-3", "all": "all weeks"}
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
            "placebo": a / "placebo_diagnostics_summary.csv"}


def read_stamp(meta, allow_sample=False):
    """The build stamp from results/meta.json; refuses a blank stamp or a sample export."""
    if meta.get("sample") and not allow_sample:
        raise NumbersError("results/meta.json is a sample export (sample: true); "
                           "pass --allow-sample to build from it")
    need = ["tables_built_at_utc", "snapshot_pages", "parser_version"]
    blank = [k for k in need if not str(meta.get(k, "")).strip()]
    if blank:
        raise NumbersError(f"results/meta.json has no build stamp ({', '.join(blank)} "
                           f"blank): rerun spirometry.export with --db")
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


def private(name, df):
    """spirometry.export's privacy check, as a NumbersError."""
    try:
        check_output(name, df)
    except ExportError as e:
        raise NumbersError(f"privacy check: {e}") from None


def load(analysis="data/analysis", results="results", allow_sample=False):
    """Read and check every input. Returns (meta, built, tables, paths)."""
    paths = _paths(analysis, results)
    missing = [str(p) for p in paths.values() if not p.exists()]
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
    return meta, built, tables, paths


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


def provenance_keys(T, meta, src):
    T.add("build.tables_built_at", meta["tables_built_at_utc"],
          fmt_time(meta["tables_built_at_utc"]), src, "tables_built_at_utc", appendix=True)
    T.add("build.parser_version", str(meta["parser_version"]), str(meta["parser_version"]),
          src, "parser_version", appendix=True)
    T.count("snapshot.pages", int(meta["snapshot_pages"]), src, "snapshot_pages",
            appendix=True)
    if str(meta.get("snapshot_last_page", "")).strip():
        T.count("snapshot.last_page", int(meta["snapshot_last_page"]), src,
                "snapshot_last_page", appendix=True)
    if str(meta.get("exported_at_utc", "")).strip():
        T.add("build.results_exported_at", meta["exported_at_utc"],
              fmt_time(meta["exported_at_utc"]), src, "exported_at_utc", appendix=True)


def did_keys(T, p, src):
    """Tweak counts, clearly nonzero, toward the change and median |beta|, per patch and
    horizon."""
    T.count("tweaks.solo_estimable", len(p), src, "rows")
    for pt in PATCHES:
        T.count(f"tweaks.{pt}", (p.patch == pt).sum(), src, f"rows, patch = {pt}")
    single = (p.mixed_direction != "yes") & (p.upgrade_only != "yes") & p.dose_x.notna()
    for hz, (b, s, cn) in {"all": ("beta", "se", "clearly_nonzero"),
                           "h3": ("beta_h", "se_h", "clearly_nonzero_h")}.items():
        horizon = HORIZONS[hz]
        toward = np.sign(p[b]) == np.sign(p.dose_x)
        for pt in PATCHES:
            g = p.patch == pt
            clear = g & (p[cn] == "yes")
            T.count(f"did.{hz}.{pt}.clearly_nonzero", clear.sum(), src,
                    f"{cn} = yes (|{b}| > 2 {s}), patch = {pt}", horizon=horizon)
            T.count(f"did.{hz}.{pt}.clearly_nonzero_with_direction", (clear & single).sum(),
                    src, f"{cn} = yes, not mixed, not upgrade-only, patch = {pt}",
                    horizon=horizon)
            T.count(f"did.{hz}.{pt}.clearly_nonzero_toward", (clear & single & toward).sum(),
                    src, f"{cn} = yes, one direction, sign({b}) = sign(dose_x), "
                         f"patch = {pt}", horizon=horizon)
            med = 100 * p.loc[g, b].abs().median()
            T.add(f"did.{hz}.{pt}.median_abs_beta_pp", med, fmt_num(med, 1), src,
                  f"median |{b}| x 100, patch = {pt}", horizon=horizon)


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

def build(analysis="data/analysis", results="results", allow_sample=False):
    """Every key, checked. Returns (rows DataFrame, header dict)."""
    meta, built, t, paths = load(analysis, results, allow_sample)
    stamp = (f"tables built {meta['tables_built_at_utc']}; {meta['snapshot_pages']} pages; "
             f"parser {meta['parser_version']}")
    T = Table(stamp)
    provenance_keys(T, meta, str(paths["meta"]))
    did_keys(T, t["pick_rate"], str(paths["pick_rate"]))
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
                  inputs={str(p): datetime.datetime.fromtimestamp(
                      p.stat().st_mtime, datetime.timezone.utc).isoformat(timespec="seconds")
                      for p in paths.values()})
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
    p.add_argument("--allow-sample", action="store_true",
                   help="build from a sample export (results/meta.json sample: true)")
    a = p.parse_args(argv)
    try:
        df, header = build(a.analysis, a.results, a.allow_sample)
    except NumbersError as e:
        sys.exit(f"numbers stopped: {e}")
    write(df, header, a.out)
    print(f"{len(df)} numbers ({int(df.appendix.sum())} for the appendix), tables built "
          f"{header['tables_built_at_utc']}, {header['snapshot_pages']} pages")
    print(f"-> {a.out}, {pathlib.Path(a.out).with_suffix('.csv')}")


if __name__ == "__main__":
    main()
