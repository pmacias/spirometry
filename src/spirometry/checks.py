"""Chapter 12's design checks ("is it the design?"), summarised for the numbers table.

    python -m spirometry.checks --triage triage --analysis data/analysis \
        --results results --out data/analysis/writeup

The five checks the scope decision of 2026-10-16 names, each read from what the triage
scripts saved (no run data; card-level estimates only):

    fake patch            i_fake_patch.csv          (triage/scripts/i_fake_patch.py)
    regression to mean    j_premove.csv, j_models.csv, j_weekly.csv (j_reversion.py)
    token subset          g3_token_fits.csv, g4_token_placebo.csv (g3_token_subset.py)
    control scope         did_h3_ctrl_other.csv, did_h3_ctrl_all.csv (l_control_scope.py)
    per-group dose lines  <analysis>/writeup/group_lines.csv (spirometry.sensitivity, from
                          notebook 02's saved tagged / untagged fits)

Which tables: a triage file is read from triage/out_final/ (the rerun on the current tables,
scripts/writeup/phil_runs.sh) when it is there, else from triage/out/ (the triage itself, on
the 1,873-page tables). Every row carries `pages` (the tables' page count) and `tables`
("2,071-page tables" or "1,873-page tables") so the text can label it. A file in
triage/out_final/ older than the current tables' build stamp (results/meta.json) is refused.
Comparisons inside a check use fits from the same tables: the control-scope shifts compare
with the same tables' did_h3 ("color" scope), which for triage/out/ is
data/analysis_p1873/did_h3.parquet (left blank if that copy is missing).

Output: design_checks.csv, one row per number: check, item (dotted, lower-case), value, se
(estimates only), kind (count, estimate, z, share, corr, factor, number), pages, tables,
source. spirometry.numbers turns each row into checks.<check>.<item>.

Definitions (as the triage computed them, triage/TRIAGE.md I, J, L, G3, G4):
- fake patch: meta-regression (spirometry.meta, random effects) of the fake effect in
  log-odds on the eventual dose x, intercept + slope, per horizon; |z| > 2 counts with honest
  SEs and with z / factor (factor = the second patch's robust placebo sd, deduplicated pairs,
  all weeks, from the same tables' placebo_diagnostics_summary.csv); expected counts from that
  summary's share of |z| > 2; toward the eventual change = sign(fake beta) = sign(x);
  correlation of fake and real weeks 0-3 log-odds effects.
- regression to the mean: J1 / J4 counts from j_premove.csv (opposes = pre-movement against
  the patch-note direction; big = |pre| > 2 SE), J2 models and J3 weekly slopes as saved.
- control scope: slope per patch on the ln ruler (spirometry.sensitivity, triage and primary
  specs) with each scope's estimates; per patch, the median |shift| from "color" in color SEs,
  how many move by more than one color SE, and sign changes.
- token subset: slope per patch (triage spec's 38 line tweaks) on the subset fits, with and
  without token fixed effects, SEs clustered by run and by token; placebo z spread under both
  clusterings; median se_token / se_run on the real tweaks.
- per-group dose lines: group_lines.csv's slopes and z diff, as saved.
"""
import argparse
import datetime
import json
import pathlib

import numpy as np
import pandas as pd

from spirometry import sensitivity as S

TRIAGE_PAGES = 1873          # triage/out/: the 1,873-page tables (TRIAGE.md, Part 2 header)
FINAL, OLD = "out_final", "out"
FILES = {"fake_patch": ["i_fake_patch.csv"],
         "reversion": ["j_premove.csv", "j_models.csv", "j_weekly.csv"],
         "token": ["g3_token_fits.csv", "g4_token_placebo.csv"],
         "control_scope": ["did_h3_ctrl_other.csv", "did_h3_ctrl_all.csv"]}
COLUMNS = ["check", "item", "value", "se", "kind", "pages", "tables", "source"]


class ChecksError(RuntimeError):
    pass


def tables_label(pages):
    return f"{int(pages):,}-page tables"


def locate(triage, check, final_pages, built_at):
    """(folder, pages) holding every file of `check`: triage/out_final/ when all are there
    (each newer than the tables' build stamp), else triage/out/ (1,873 pages), else None."""
    triage = pathlib.Path(triage)
    for sub, pages in [(FINAL, final_pages), (OLD, TRIAGE_PAGES)]:
        paths = [triage / sub / f for f in FILES[check]]
        if all(p.exists() for p in paths):
            if sub == FINAL:
                old = [p.name for p in paths if datetime.datetime.fromtimestamp(
                    p.stat().st_mtime, datetime.timezone.utc) < built_at]
                if old:
                    raise ChecksError(f"{triage / sub}: {', '.join(old)} older than the run "
                                      f"tables ({built_at.isoformat()})")
            return triage / sub, pages
    return None


class Rows:
    def __init__(self, check, pages, source):
        self.check, self.pages, self.source, self.rows = check, int(pages), str(source), []

    def add(self, item, value, kind, se=np.nan):
        self.rows.append(dict(check=self.check, item=item, value=float(value), se=float(se),
                              kind=kind, pages=self.pages, tables=tables_label(self.pages),
                              source=self.source))

    def slopes(self, prefix, r):
        """slopes_by_patch's dict: both slopes, the difference and its z, n."""
        self.add(f"{prefix}.slope_first", r["slope1"], "estimate", r["se1"])
        self.add(f"{prefix}.slope_second", r["slope2"], "estimate", r["se2"])
        self.add(f"{prefix}.diff", r["diff"], "estimate", r["se_diff"])
        self.add(f"{prefix}.z_diff", r["z_diff"], "z")
        self.add(f"{prefix}.n_first", r["n1"], "count")
        self.add(f"{prefix}.n_second", r["n2"], "count")


def _line_fit(y, se, x):
    """Intercept + slope meta-regression: (b, se(b), tau2)."""
    b, cov, tau2, *_ = S.fit(y, se, np.column_stack([np.ones(len(x)), x]))
    return b, np.sqrt(np.diag(cov)), tau2


def placebo_second(summary):
    """(robust sd, share |z| > 2) of the second patch's deduplicated placebo pairs."""
    s = summary[(summary.dedupe.astype(str).str.lower() == "true")
                & (summary.split == "patch") & (summary.level == "second")]
    if len(s) != 1:
        raise ChecksError("placebo summary: no second-patch deduplicated row")
    return float(s.robust_sd_z.iloc[0]), float(s.share_abs_z_gt2.iloc[0])


def fake_patch(df, factor, share_gt2, R):
    for horizon, d in df.groupby("horizon", sort=False):
        h = "h3" if horizon == "weeks 0-3" else "all"
        z = d.beta / d.se
        b, s, tau2 = _line_fit(d.beta_lo, d.se_lo, d.x)
        R.add(f"{h}.n", len(d), "count")
        R.add(f"{h}.slope", b[1], "estimate", s[1])
        R.add(f"{h}.slope_z", b[1] / s[1], "z")
        R.add(f"{h}.intercept", b[0], "estimate", s[0])
        R.add(f"{h}.tau2", tau2, "number")
        R.add(f"{h}.n_abs_z_gt2", (z.abs() > 2).sum(), "count")
        R.add(f"{h}.n_abs_z_gt3", (z.abs() > 3).sum(), "count")
        R.add(f"{h}.n_abs_z_gt2_calibrated", (z.abs() / factor > 2).sum(), "count")
        R.add(f"{h}.expected_abs_z_gt2", share_gt2 * len(d), "number")
        R.add(f"{h}.n_toward", (np.sign(d.beta) == np.sign(d.x)).sum(), "count")
        R.add(f"{h}.corr_real", np.corrcoef(d.beta_lo, d.real_beta_lo)[0, 1], "corr")
        R.add(f"{h}.sd_fake", d.beta_lo.std(), "number")
        R.add(f"{h}.sd_real", d.real_beta_lo.std(), "number")
    R.add("factor", factor, "factor")


def reversion(pre, models, weekly, R):
    for patch, tag in [("first", "j1"), ("second", "j4")]:
        d = pre[pre.patch == patch]
        big = d.pre_lo.abs() > 2 * d.pre_se_lo
        opp = d.opposes.astype(str).str.lower() == "true"
        R.add(f"{tag}.n", len(d), "count")
        R.add(f"{tag}.n_opposes", opp.sum(), "count")
        R.add(f"{tag}.n_big", big.sum(), "count")
        R.add(f"{tag}.n_big_opposes", (opp & big).sum(), "count")
        R.add(f"{tag}.median_abs_pre", d.pre_lo.abs().median(), "number")
        R.add(f"{tag}.median_abs_pre_pp", d.pre_pp.abs().median(), "number")
        R.add(f"{tag}.median_pre_se", d.pre_se_lo.median(), "number")
        R.add(f"{tag}.median_abs_effect", d.beta_lo.abs().median(), "number")
        R.add(f"{tag}.corr_pre_x", np.corrcoef(d.pre_lo, d.x)[0, 1], "corr")
    names = {"effect ~ x": "j2.without_pre", "effect ~ x + pre (declared)": "j2.declared",
             "effect ~ x + 3 x pre-slope (weeks -5..-1)": "j2.pre_slope",
             "effect ~ x + pre (comparison only)": "j4.model"}
    for m in models.itertuples():
        key = names.get(m.model, "j2.leave_out" if m.model.startswith("declared, without")
                        else None)
        if key is None:
            continue
        R.add(f"{key}.slope_x", m.slope_x, "estimate", m.se_x)
        if pd.notna(m.pre_coef):
            R.add(f"{key}.pre_coef", m.pre_coef, "estimate", m.pre_se)
            R.add(f"{key}.pre_z", m.pre_coef / m.pre_se, "z")
        R.add(f"{key}.n", m.n, "count")
    for w in weekly.dropna(subset=["slope"]).itertuples():
        R.add(f"j3.week{int(w.week)}.slope", w.slope, "estimate", w.se)
        R.add(f"j3.week{int(w.week)}.n", w.n_tweaks, "count")


def _with(base, est, cols=("beta", "se", "beta_lo", "se_lo")):
    """`base` (a prepared did_h3) with `est`'s estimate columns (by card_patch_id)."""
    d = base.copy()
    e = est.set_index("card_patch_id") if "card_patch_id" in est.columns else est
    for c in cols:
        d[c] = pd.to_numeric(e[c], errors="coerce").reindex(d.index)
    return d


def control_scope(color, scopes, R, color_same_tables=True):
    """color: prepared did_h3 of the same tables (None: shifts left out); scopes: {name:
    did_h3_ctrl_<name>.csv}."""
    for name, est in scopes.items():
        d = _with(color, est)
        for spec in ("triage", S.PRIMARY):
            R.slopes(f"{name}.{spec}", S.slopes_by_patch(S.dose_line(d, spec)))
        if not color_same_tables:
            continue
        shift = (d.beta - color.beta) / color.se
        flip = np.sign(d.beta) != np.sign(color.beta)
        for patch in ("first", "second"):
            g = color.patch == patch
            R.add(f"{name}.{patch}.median_abs_shift_se", shift[g].abs().median(), "number")
            R.add(f"{name}.{patch}.n_moved_1se", (shift[g].abs() > 1).sum(), "count")
            R.add(f"{name}.{patch}.n", g.sum(), "count")
            R.add(f"{name}.{patch}.sign_changes", flip[g].sum(), "count")
        R.add(f"{name}.min_control_cards", pd.to_numeric(est.n_control_cards).min(), "count")
        R.add(f"{name}.max_control_cards", pd.to_numeric(est.n_control_cards).max(), "count")
    for spec in ("triage", S.PRIMARY):
        R.slopes(f"color.{spec}", S.slopes_by_patch(S.dose_line(color, spec)))


def _rsd(z):
    return 1.4826 * (z - z.median()).abs().median()


def token(fits, placebo, color, R):
    """Subset fits on the triage spec's line (the notebooks' 38: the subset fits only those)."""
    for tfe, tag in [(False, "subset"), (True, "subset_token_fe")]:
        f = fits[(fits.token_fe.astype(str).str.lower() == str(tfe).lower())
                 & (fits.error.fillna("") == "")]
        d = _with(color, f.assign(se=f.se_run))
        d = d[d.index.isin(f.card_patch_id)]
        R.slopes(f"{tag}.run_clustered", S.slopes_by_patch(S.notebook_line(d)))
        d["se_lo"] = d.index.map(f.set_index("card_patch_id").se_lo_tok)
        R.slopes(f"{tag}.token_clustered", S.slopes_by_patch(S.notebook_line(d)))
    f = fits[fits.token_fe.astype(str).str.lower() == "false"]
    R.add("se_token_over_run.median", (f.se_tok / f.se_run).median(), "number")
    P = placebo[placebo.error.fillna("") == ""]
    zr, zt = P.beta / P.se_run, P.beta / P.se_tok
    for lab, m in [("all", np.ones(len(P), bool))] + [(p, (P.patch == p).to_numpy())
                                                     for p in ("first", "second")]:
        R.add(f"placebo.{lab}.n", m.sum(), "count")
        R.add(f"placebo.{lab}.sd_z_run", zr[m].std(), "z")
        R.add(f"placebo.{lab}.sd_z_token", zt[m].std(), "z")
        R.add(f"placebo.{lab}.robust_sd_z_run", _rsd(zr[m]), "z")
        R.add(f"placebo.{lab}.robust_sd_z_token", _rsd(zt[m]), "z")


def group_lines(g, R):
    for r in g.itertuples():
        h = "h3" if r.horizon == "weeks 0-3" else "all"
        R.slopes(f"{r.group}.{h}.{r.spec}", dict(slope1=r.slope1, se1=r.se1, slope2=r.slope2,
                                                 se2=r.se2, diff=r.diff, se_diff=r.se_diff,
                                                 z_diff=r.z_diff, n1=r.n1, n2=r.n2))


def build(triage="triage", analysis="data/analysis", results="results",
          old_analysis="data/analysis_p1873"):
    """Every check found. Returns (rows, missing): missing = [(check, reason)]."""
    meta = json.loads((pathlib.Path(results) / "meta.json").read_text())
    built_at = datetime.datetime.fromisoformat(meta["tables_built_at_utc"])
    pages = int(meta["snapshot_pages"])
    an, old_an = pathlib.Path(analysis), pathlib.Path(old_analysis)
    out, missing = [], []

    def fits_of(folder_pages):
        """(prepared did_h3, placebo summary) of the tables a triage folder came from."""
        a = an if folder_pages == pages else old_an
        if not (a / "did_h3.parquet").exists():
            return None, None
        summ = a / "placebo_diagnostics_summary.csv"
        return (S.prepare(pd.read_parquet(a / "did_h3.parquet")),
                pd.read_csv(summ) if summ.exists() else None)

    for check in FILES:
        loc = locate(triage, check, pages, built_at)
        if loc is None:
            missing.append((check, "no saved output in triage/out_final/ or triage/out/"))
            continue
        folder, pg = loc
        R = Rows(check, pg, folder)
        read = lambda f: pd.read_csv(folder / f)
        color, summ = fits_of(pg)
        if check == "fake_patch":
            if summ is None:
                missing.append((check, f"no placebo summary for the {tables_label(pg)}"))
                continue
            fake_patch(read("i_fake_patch.csv"), *placebo_second(summ), R)
        elif check == "reversion":
            reversion(read("j_premove.csv"), read("j_models.csv"), read("j_weekly.csv"), R)
        elif check == "token":
            if color is None:
                missing.append((check, f"no did_h3 for the {tables_label(pg)}"))
                continue
            token(read("g3_token_fits.csv"), read("g4_token_placebo.csv"), color, R)
        elif check == "control_scope":
            same = color is not None
            if not same:          # slopes need the dose columns: take them from today's fits
                color = S.prepare(pd.read_parquet(an / "did_h3.parquet"))
            control_scope(color, {"other": read("did_h3_ctrl_other.csv"),
                                  "all": read("did_h3_ctrl_all.csv")}, R, same)
        out += R.rows
    g = an / "writeup" / "group_lines.csv"
    if g.exists():
        R = Rows("group_lines", pages, g)
        group_lines(pd.read_csv(g), R)
        out += R.rows
    else:
        missing.append(("group_lines", f"{g} not found (spirometry.sensitivity writes it)"))
    return pd.DataFrame(out, columns=COLUMNS), missing


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--triage", default="triage")
    p.add_argument("--analysis", default="data/analysis")
    p.add_argument("--results", default="results")
    p.add_argument("--old-analysis", default="data/analysis_p1873",
                   help="saved fits of the 1,873-page tables (for triage/out/'s comparisons)")
    p.add_argument("--out", default="data/analysis/writeup")
    a = p.parse_args(argv)
    from spirometry.export import check_output
    try:
        df, missing = build(a.triage, a.analysis, a.results, a.old_analysis)
    except ChecksError as e:
        raise SystemExit(f"checks stopped: {e}")
    check_output("design_checks", df)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "design_checks.csv", index=False)
    for (check, tables), g in df.groupby(["check", "tables"], sort=False):
        print(f"{check:14s} {len(g):4d} rows  ({tables}, {g.source.iloc[0]})")
    for check, why in missing:
        print(f"missing: {check}: {why}")
    print(f"-> {out / 'design_checks.csv'}")


if __name__ == "__main__":
    main()
