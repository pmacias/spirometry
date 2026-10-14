"""spirometry.numbers on synthetic saved outputs (spirometry.sample_results.write_numbers_inputs):
the keys, the formatting, and the stamp, staleness and privacy guards. No run data."""
import json
import os

import numpy as np
import pandas as pd
import pytest

from spirometry import numbers as N, sample_results

MINUS = "−"


@pytest.fixture()
def dirs(tmp_path):
    a, r, ref = tmp_path / "analysis", tmp_path / "results", tmp_path / "ref"
    sample_results.write_numbers_inputs(a, r, ref, seed=3)
    return a, r


def build(dirs, **kw):
    return N.build(*dirs, allow_sample=True, snapshot_log=dirs[1].parent / "snapshot.log",
                   **kw)


def test_formatting():
    assert N.fmt_int(2071) == "2,071" and N.fmt_int(1525369) == "1,525,369"
    assert N.fmt_num(1.39979, 2) == "1.40"
    assert N.fmt_num(-2.97, 2) == f"{MINUS}2.97"
    assert N.fmt_num(0.054, 2, sign=True) == "+0.05"
    assert N.fmt_num(-0.001, 2, sign=True) == "0.00"           # no sign on a printed zero
    assert N.fmt_pm(0.0539, 0.30696, 2) == "0.05 ± 0.31"
    assert N.fmt_pm(-15.94, 0.71, 1, sign=True) == f"{MINUS}15.9 ± 0.7"
    assert N.fmt_pct(0.7154) == "72%"
    assert N.fmt_time("2026-10-09T21:18:20+00:00") == "2026-10-09 21:18 UTC"


def test_expected_keys_and_values(dirs):
    df, header = build(dirs)
    k = df.set_index("key")
    assert df.key.is_unique and len(df) > 50
    for key in ["build.tables_built_at", "build.parser_version", "snapshot.pages",
                "tweaks.solo_estimable", "tweaks.first", "tweaks.second",
                "snapshot.records", "snapshot.last_page", "snapshot.start_date",
                "snapshot.end_date",
                "did.all.first.uncalibrated.clearly_nonzero",
                "did.h3.second.uncalibrated.clearly_nonzero_toward",
                "did.all.first.calibrated.clearly_nonzero",
                "did.all.second.calibrated.factor",
                "did.all.second.calibrated_plain_sd.clearly_nonzero_toward",
                "did.h3.first.median_abs_beta_pp",
                "dose.triage.h3.slope_first_pm", "dose.triage.all.slope_second",
                "dose.primary.h3.slope_second_pm", "dose.primary.h3.z_diff",
                "dose.primary.h3.placebo_robust_sd.slope_first_pm",
                "placebo.fits.first.sd_z", "placebo.pairs.all.sd_z",
                "placebo.pairs.second.robust_sd_z"]:
        assert key in k.index, key
    # values agree with the sources
    p = pd.read_csv(dirs[1] / "pick_rate_did.csv")
    assert k.loc["tweaks.solo_estimable", "value"] == len(p)
    first = p[p.patch == "first"]
    assert (k.loc["did.all.first.uncalibrated.clearly_nonzero", "value"]
            == (first.clearly_nonzero == "yes").sum())
    toward = first[(first.clearly_nonzero == "yes") & (first.toward_change == "yes")]
    assert k.loc["did.all.first.uncalibrated.clearly_nonzero_toward", "value"] == len(toward)
    assert "uncalibrated" in k.loc["did.all.first.uncalibrated.clearly_nonzero", "column"]
    # snapshot keys: the log's last page and total, meta.json's primary play dates
    assert k.loc["snapshot.last_page", "value"] == 12
    assert k.loc["snapshot.records", "text"] == "11,234"
    assert k.loc["snapshot.records", "source"].endswith("snapshot.log")
    assert (k.loc["snapshot.start_date", "value"], k.loc["snapshot.end_date", "value"]) \
        == ("2026-03-18", "2026-07-02")
    # calibrated counts: as calibrated_counts.csv, factor > 1 can only remove results
    c = pd.read_csv(dirs[0] / "writeup" / "calibrated_counts.csv")
    r = c[(c.horizon == "all weeks") & (c.patch == "first") & (c.spread == "robust sd")].iloc[0]
    assert k.loc["did.all.first.calibrated.clearly_nonzero", "value"] == r.n_clearly_nonzero
    assert k.loc["did.all.first.calibrated.factor", "text"] == N.fmt_num(r.factor, 2)
    assert (k.loc["did.all.first.calibrated.clearly_nonzero", "value"]
            <= k.loc["did.all.first.uncalibrated.clearly_nonzero", "value"])
    d = pd.read_csv(dirs[1] / "dose_response.csv")
    r = d[(d.horizon == "weeks 0-3") & (d.model == "slope per patch")
          & (d.term == "slope_first")].iloc[0]
    assert k.loc["dose.triage.h3.slope_first", "value"] == pytest.approx(r.coef)
    assert k.loc["dose.triage.h3.slope_first_pm", "text"] == N.fmt_pm(r.coef, r.se, 2)
    pl = pd.read_csv(dirs[0] / "placebo_diagnostics_summary.csv")
    r = pl[(pl.dedupe) & (pl.level == "second")].iloc[0]
    assert k.loc["placebo.pairs.second.sd_z", "value"] == pytest.approx(r.sd_z)
    # metadata on every row
    assert (df.build.str.contains("12 pages") & df.build.str.contains("parser sample")).all()
    assert set(df.horizon) <= {"", "weeks 0-3", "all weeks"}
    assert k.loc["dose.primary.h3.slope_first", "spec"] == "primary"
    assert k.loc["did.h3.first.uncalibrated.clearly_nonzero", "horizon"] == "weeks 0-3"
    assert k.loc["snapshot.pages", "appendix"] and not k.loc["dose.triage.h3.z_diff", "appendix"]
    assert header["sample"] is True
    # the synthetic placebo fits are all weeks: weeks 0-3 calibrated keys are missing
    assert not any(key.startswith("did.h3.first.calibrated") for key in k.index)
    assert {m["keys"] for m in header["missing"]} == {
        f"did.h3.{pt}.{s}.*" for pt in ["first", "second"]
        for s in ["calibrated", "calibrated_plain_sd"]}
    assert all("weeks 0-3" in m["reason"] for m in header["missing"])


def test_toward_change_weeks_0_3_uses_the_export_rule(dirs):
    df, _ = build(dirs)
    k = df.set_index("key")
    p = pd.read_csv(dirs[1] / "pick_rate_did.csv")
    s = p[(p.patch == "second") & (p.clearly_nonzero_h == "yes") & (p.mixed_direction != "yes")
          & (p.upgrade_only != "yes") & p.dose_x.notna()]
    n = ((s.beta_h > 0) == (s.dose_x > 0)).sum()
    assert k.loc["did.h3.second.uncalibrated.clearly_nonzero_toward", "value"] == n


def test_writes_json_and_csv(dirs, tmp_path):
    df, header = build(dirs)
    out = tmp_path / "writeup" / "numbers.json"
    N.write(df, header, out)
    j = json.loads(out.read_text())
    assert j["build"]["snapshot_pages"] == "12"
    row = j["numbers"]["dose.primary.h3.z_diff"]
    assert set(row) == set(N.COLUMNS) - {"key"}
    assert row["text"].startswith((MINUS, "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"))
    assert "-" not in row["text"]                              # minus sign, not hyphen
    c = pd.read_csv(out.with_suffix(".csv"))
    assert list(c.columns) == N.COLUMNS and len(c) == len(df)


def test_cli(dirs, tmp_path, capsys):
    out = tmp_path / "w" / "numbers.json"
    N.main(["--analysis", str(dirs[0]), "--results", str(dirs[1]), "--out", str(out),
            "--snapshot-log", str(dirs[1].parent / "snapshot.log"), "--allow-sample"])
    assert out.exists() and out.with_suffix(".csv").exists()
    assert "numbers" in capsys.readouterr().out


def test_refuses_sample_without_flag(dirs):
    with pytest.raises(N.NumbersError, match="sample"):
        N.build(*dirs, snapshot_log=dirs[1].parent / "snapshot.log")


def test_staleness_guard_names_the_old_file(dirs):
    old = dirs[0] / "writeup" / "rulers.csv"
    t = pd.Timestamp("2025-12-01T00:00:00Z").timestamp()     # before the 2026-01-01 stamp
    os.utime(old, (t, t))
    with pytest.raises(N.NumbersError, match="rulers.csv"):
        build(dirs)


def test_missing_build_stamp_refused(dirs):
    m = json.loads((dirs[1] / "meta.json").read_text())
    m["tables_built_at_utc"] = ""
    (dirs[1] / "meta.json").write_text(json.dumps(m))
    with pytest.raises(N.NumbersError, match="build stamp"):
        build(dirs)


def test_privacy_guard_fires_on_an_id_column(dirs):
    p = dirs[1] / "pick_rate_did.csv"
    df = pd.read_csv(p)
    df["run_key"] = "x"
    df.to_csv(p, index=False)
    with pytest.raises(N.NumbersError, match="privacy.*run_key"):
        build(dirs)


def test_privacy_guard_fires_on_a_hashed_value(dirs):
    p = dirs[0] / "placebo_diagnostics_summary.csv"
    df = pd.read_csv(p)
    df["note"] = "0123456789abcdef"
    df.to_csv(p, index=False)
    with pytest.raises(N.NumbersError, match="hashed id"):
        build(dirs)


def test_missing_value_refused(dirs):
    p = dirs[1] / "dose_response.csv"
    df = pd.read_csv(p)
    df.loc[df.term == "slope_second", "coef"] = None
    df.to_csv(p, index=False)
    with pytest.raises(N.NumbersError, match="value missing"):
        build(dirs)


def test_bad_or_repeated_key_refused():
    T = N.Table("stamp")
    with pytest.raises(N.NumbersError, match="bad key"):
        T.add("Dose-Slope", 1.0, "1.0", "src", "col")
    T.add("a.b", 1.0, "1.0", "src", "col")
    with pytest.raises(N.NumbersError, match="twice"):
        T.add("a.b", 2.0, "2.0", "src", "col")


@pytest.mark.parametrize("field", ["snapshot_start_date", "snapshot_end_date"])
def test_blank_play_dates_refused(dirs, field):
    m = json.loads((dirs[1] / "meta.json").read_text())
    m[field] = ""
    (dirs[1] / "meta.json").write_text(json.dumps(m))
    with pytest.raises(N.NumbersError, match=field):
        build(dirs)


def test_snapshot_log_guards(dirs):
    log = dirs[1].parent / "snapshot.log"
    sample_results.write_snapshot_log(log, pages=12, end=False)
    with pytest.raises(N.NumbersError, match="reached end of export"):
        build(dirs)
    sample_results.write_snapshot_log(log, pages=11)
    with pytest.raises(N.NumbersError, match="ends at page 11"):
        build(dirs)
    log.unlink()
    with pytest.raises(N.NumbersError, match="missing input"):
        build(dirs)


def test_read_snapshot_log(tmp_path):
    log = sample_results.write_snapshot_log(tmp_path / "s.log", pages=7)
    assert N.read_snapshot_log(log) == (7, sample_results.SAMPLE_LOG_TOTAL[0])


def test_uncalibrated_rows_must_match_pick_rate(dirs):
    p = dirs[0] / "writeup" / "calibrated_counts.csv"
    c = pd.read_csv(p)
    c.loc[c.spread == "none", "n_clearly_nonzero"] += 1
    c.to_csv(p, index=False)
    with pytest.raises(N.NumbersError, match="differ from pick_rate_did"):
        build(dirs)


def test_weeks_0_3_calibrated_keys_when_placebos_exist(dirs):
    from spirometry import sensitivity as S
    a, r = dirs
    ref = a.parent / "ref"
    D = {}
    for name in ["h3", "main"]:
        f = pd.read_parquet(a / f"did_{name}.parquet")
        for col in ["log_ratio", "upgraded_log_ratio", "direction"]:
            f[col] = pd.to_numeric(f[col], errors="coerce")
        D[name] = S.prepare(f)
    rng = np.random.default_rng(0)
    placebo = sample_results.placebo_fits(D["h3"], rng, horizons=(None, 3))
    S.calibrated_counts({"weeks 0-3": D["h3"], "all weeks": D["main"]},
                        S.placebo_factors_by_horizon(placebo, ref=ref)).to_csv(
        a / "writeup" / "calibrated_counts.csv", index=False)
    df, header = build(dirs)
    assert header["missing"] == []
    assert "did.h3.second.calibrated.clearly_nonzero_toward" in set(df.key)
