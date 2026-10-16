"""spirometry.checks on synthetic triage outputs (sample_results.write_triage_outputs): which
tables each check comes from and how it is labelled, the staleness guard, and the summaries
against direct computation. No run data."""
import os
import shutil

import numpy as np
import pandas as pd
import pytest

from spirometry import checks as C, sample_results, sensitivity as S


@pytest.fixture()
def dirs(tmp_path):
    a, r, ref = tmp_path / "analysis", tmp_path / "results", tmp_path / "ref"
    sample_results.write_numbers_inputs(a, r, ref, seed=5)
    return a, r, tmp_path / "triage"


def build(dirs, old=None):
    a, r, t = dirs
    return C.build(t, a, r, old_analysis=old or a.parent / "no_old_tables")


def test_final_outputs_labelled_with_the_current_tables(dirs):
    rows, missing = build(dirs)
    assert missing == []
    assert set(rows.check) == {"fake_patch", "reversion", "token", "control_scope",
                               "group_lines"}
    assert (rows.pages == 12).all() and (rows.tables == "12-page tables").all()
    assert rows.groupby(["check", "item"]).size().max() == 1
    assert set(rows.kind) <= {"count", "estimate", "z", "share", "corr", "factor", "number"}
    assert rows[rows.kind == "estimate"].se.notna().all()


def test_fallback_to_the_triage_record_is_labelled_1873(dirs):
    a, r, t = dirs
    (t / "out").mkdir()
    for f in C.FILES["control_scope"]:
        shutil.move(t / "out_final" / f, t / "out" / f)
    # without the 1,873-page fits the shifts are left out but the slopes stay
    rows, _ = build(dirs)
    cs = rows[rows.check == "control_scope"]
    assert (cs.pages == C.TRIAGE_PAGES).all() and (cs.tables == "1,873-page tables").all()
    assert str(cs.source.iloc[0]).endswith("out")
    assert not cs.item.str.contains("median_abs_shift_se").any()
    assert "other.triage.slope_first" in set(cs.item)
    # with them (data/analysis_p1873 stand-in), the shifts are computed against them
    old = a.parent / "old"
    old.mkdir()
    shutil.copy(a / "did_h3.parquet", old / "did_h3.parquet")
    rows, _ = build(dirs, old=old)
    assert "other.first.median_abs_shift_se" in set(rows[rows.check == "control_scope"].item)
    # the other checks still come from out_final
    assert (rows[rows.check == "fake_patch"].pages == 12).all()


def test_stale_final_output_refused(dirs):
    a, r, t = dirs
    old = pd.Timestamp("2025-12-01T00:00:00Z").timestamp()     # before the sample stamp
    os.utime(t / "out_final" / "i_fake_patch.csv", (old, old))
    with pytest.raises(C.ChecksError, match="i_fake_patch.csv older than the run tables"):
        build(dirs)


def test_missing_check_listed(dirs):
    a, r, t = dirs
    (t / "out_final" / "g4_token_placebo.csv").unlink()
    rows, missing = build(dirs)
    assert "token" not in set(rows.check)
    assert [m[0] for m in missing] == ["token"]


def test_fake_patch_and_control_scope_values(dirs):
    a, r, t = dirs
    rows, _ = build(dirs)
    v = rows.set_index(["check", "item"])
    f = pd.read_csv(t / "out_final" / "i_fake_patch.csv")
    d = f[f.horizon == "weeks 0-3"]
    b, cov, *_ = S.fit(d.beta_lo, d.se_lo, np.column_stack([np.ones(len(d)), d.x]))
    assert v.loc[("fake_patch", "h3.slope"), "value"] == pytest.approx(b[1])
    assert v.loc[("fake_patch", "h3.slope"), "se"] == pytest.approx(np.sqrt(cov[1, 1]))
    summ = pd.read_csv(a / "placebo_diagnostics_summary.csv")
    factor, share = C.placebo_second(summ)
    z = d.beta / d.se
    assert v.loc[("fake_patch", "h3.n_abs_z_gt2_calibrated"), "value"] == \
        (z.abs() / factor > 2).sum()
    assert v.loc[("fake_patch", "h3.expected_abs_z_gt2"), "value"] == pytest.approx(share * len(d))
    # control scope: the "color" slope is did_h3's own (sensitivity's ruler table)
    rulers = pd.read_csv(a / "writeup" / "rulers.csv").set_index(["spec", "ruler"])
    assert v.loc[("control_scope", "color.primary.slope_first"), "value"] == pytest.approx(
        rulers.loc[("primary", "ln(new/old)"), "slope1"])
    # the synthetic "other" scope shifts every first-patch tweak up: none in the second
    assert v.loc[("control_scope", "other.second.n_moved_1se"), "value"] == 0


def test_cli_writes_csv(dirs, tmp_path, capsys):
    a, r, t = dirs
    out = tmp_path / "w"
    C.main(["--triage", str(t), "--analysis", str(a), "--results", str(r), "--out", str(out),
            "--old-analysis", str(tmp_path / "none")])
    df = pd.read_csv(out / "design_checks.csv")
    assert list(df.columns) == C.COLUMNS and len(df) > 50
    assert "fake_patch" in capsys.readouterr().out
