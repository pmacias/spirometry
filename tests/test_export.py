"""spirometry.export on synthetic saved fits (spirometry.sample_results: the column layout
notebooks 02 and 03 save). No run data."""
import json
import pathlib

import numpy as np
import pandas as pd
import pytest

from spirometry import export, sample_results

ROOT = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture()
def inputs(tmp_path):
    a, r = tmp_path / "analysis", tmp_path / "ref"
    sample_results.write_inputs(a, r, seed=5)
    return a, r


def run(inputs, tmp_path, **kw):
    a, r = inputs
    return export.export(a, tmp_path / "out", r, **kw), tmp_path / "out"


def test_writes_every_table(inputs, tmp_path):
    t, out = run(inputs, tmp_path)
    for name in ["pick_rate_did", "flags", "weekly", "dose_response", "robustness",
                 "anticipation"]:
        assert (out / f"{name}.csv").exists()
    m = json.loads((out / "meta.json").read_text())
    assert m["sample"] is False and m["horizon"] == "weeks 0-3"
    assert m["parser_version"] == "" and "no --db" in m["blank_reasons"]["parser_version"]
    assert m["snapshot_end_date"] == ""


def test_pick_rate_table(inputs, tmp_path):
    t, out = run(inputs, tmp_path)
    p = pd.read_csv(out / "pick_rate_did.csv", keep_default_na=False, na_values=[""])
    main = export.read_fit(inputs[0] / "did_main.parquet")
    assert len(p) == len(main) and p.card_patch_id.is_unique
    assert "SAMPLE_99@v0.107.1/patch" not in set(p.card_patch_id)   # not solo-estimable
    assert set(p.patch) == {"first", "second"}
    assert (p.window[p.patch == "first"] == "v0.99.1 -> v0.103.2").all()
    # derived columns
    k = p.treated_rate_before * (1 - p.treated_rate_before)
    np.testing.assert_allclose(p.beta_lo, p.beta / k, rtol=1e-4)
    assert ((p.beta.abs() > 2 * p.se) == (p.clearly_nonzero == "yes")).all()
    assert ((p.beta_h.abs() > 2 * p.se_h) == (p.clearly_nonzero_h == "yes")).all()
    for col, est, se, factors in [
            ("clearly_nonzero_cal", p.beta, p.se, export.PLACEBO_FACTORS_ALL),
            ("clearly_nonzero_h_cal", p.beta_h, p.se_h, export.PLACEBO_FACTORS_H3)]:
        assert ((est.abs() > 2 * se * p.patch.map(factors)) == (p[col] == "yes")).all()
    single = (p.mixed_direction == "no") & (p.upgrade_only == "no")
    assert (p.toward_change[~single].isna()).all()
    s = p[single]
    assert ((np.sign(s.beta) == np.sign(s.direction * s.log_ratio))
            == (s.toward_change == "yes")).all()
    up = p[p.upgrade_only == "yes"]
    assert (up.change == "buff").all()                      # +3 -> +5
    h3 = export.read_fit(inputs[0] / "did_h3.parquet").set_index("card_patch_id")
    np.testing.assert_allclose(p.set_index("card_patch_id").beta_h,
                               h3.beta.reindex(p.card_patch_id), rtol=1e-4)


def test_log_odds_matches_did():
    did = pytest.importorskip("spirometry.did")
    b, s = export.to_log_odds(pd.Series([0.03, 0.01]), pd.Series([0.01, 0.002]),
                              pd.Series([0.2, 0.0]))
    assert (b.iloc[0], s.iloc[0]) == pytest.approx(did.to_log_odds(0.03, 0.01, 0.2))
    assert np.isnan(b.iloc[1])


def test_flags_weekly_and_dose_response(inputs, tmp_path):
    t, out = run(inputs, tmp_path)
    f = t["flags"].set_index("card_patch_id")
    assert (f.offer_rate_flag == "yes").sum() == 1
    up = t["pick_rate_did"].query("upgrade_only == 'yes'").card_patch_id
    assert f.loc[up, "placebo_se"].notna().all()
    assert f.placebo_se.notna().sum() == len(up)
    second = t["pick_rate_did"].query("patch == 'second'").card_patch_id
    assert f.loc[second, "pooled_before_beta"].notna().all()
    first = f[f.patch == "first"]
    assert first.pretrend_n_weeks.eq(3).all() and first.pretrend_slope.notna().all()
    assert f[f.patch == "second"].pretrend_slope.isna().all()          # one pre week
    # pretrend slope = the notebook's weighted fit
    es = export.read_fit(inputs[0] / "event_studies.parquet")
    g = es[(es.card_patch_id == first.index[0]) & (es.block == "before") & (es.week < 0)]
    slope = np.polyfit(g.week, g.coef, 1, w=1 / g.se)[0]
    assert first.pretrend_slope.iloc[0] == pytest.approx(slope)
    w = t["weekly"]
    assert (w.n_offers >= 10).all()
    assert not ((w.block == "before") & (w.week == 2)).any()          # thin cells dropped
    d = t["dose_response"]
    assert set(d.horizon) == {"weeks 0-3", "all weeks"}
    assert d.groupby("horizon").n_tweaks.first().eq(len(t["pick_rate_did"]) - 3).all()


def test_anticipation_optional(inputs, tmp_path):
    a, r = inputs
    t, out = run(inputs, tmp_path)
    an = t["anticipation"]
    assert list(an.columns[:6]) == ["card_patch_id", "card_id", "patch", "window", "status",
                                    "reason"]
    assert (an.reason[an.status == "informative"] == "").all()
    assert (an.first_beta_date != "").all()
    (a / "anticipation_main.parquet").unlink()
    t, out = run(inputs, tmp_path)
    assert "anticipation" not in t and not (out / "anticipation.csv").exists()
    assert any("anticipation_main.parquet not found" in n for n in t["meta"]["notes"])


def test_offer_rate_optional(inputs, tmp_path):
    (inputs[0] / "offer_rate.parquet").unlink()
    t, _ = run(inputs, tmp_path)
    assert t["flags"].offer_rate_flag.isna().all()
    assert any("offer_rate.parquet" in n for n in t["meta"]["notes"])


def test_refuses_error_rows_unless_skipped(inputs, tmp_path):
    a, _ = inputs
    main = pd.read_parquet(a / "did_main.parquet")
    bad = main.index[2]
    main.loc[bad, "error"] = "ValueError: no treated offers in the before block"
    main.loc[bad, ["beta", "se"]] = np.nan
    main.to_parquet(a / "did_main.parquet")
    with pytest.raises(export.ExportError, match="error row"):
        run(inputs, tmp_path)
    assert not (tmp_path / "out").exists()                  # nothing half-written
    t, _ = run(inputs, tmp_path, skip_errors=True)
    assert bad not in set(t["pick_rate_did"].card_patch_id)
    assert t["meta"]["skipped"] == [dict(table="did_main.parquet", card_patch_ids=[bad])]


def test_refuses_event_study_and_anticipation_errors(inputs, tmp_path):
    a, _ = inputs
    ant = pd.read_parquet(a / "anticipation_main.parquet")
    ant.loc[0, "status"] = "error"
    ant.to_parquet(a / "anticipation_main.parquet")
    with pytest.raises(export.ExportError, match="status 'error'"):
        run(inputs, tmp_path)
    es = pd.read_parquet(a / "event_studies.parquet")
    es.loc[0, "error"] = "ValueError: no treated offers in the reference cell"
    es.to_parquet(a / "event_studies.parquet")
    with pytest.raises(export.ExportError, match="event_studies"):
        run(inputs, tmp_path)
    t, _ = run(inputs, tmp_path, skip_errors=True)
    assert {s["table"] for s in t["meta"]["skipped"]} == {"event_studies.parquet",
                                                           "anticipation_main.parquet"}


FORBIDDEN = ["uploader_hash", "run_key", "player_token", "player_id", "seed", "run_hash"]


def test_no_identifiers_in_output(inputs, tmp_path):
    """Identifier columns in the inputs never reach the output, and the output check stops
    any table that carries one."""
    a, _ = inputs
    for f in a.glob("*.parquet"):
        df = pd.read_parquet(f)
        for c in FORBIDDEN:
            df[c] = "0123456789abcdef"
        df.to_parquet(f)
    t, out = run(inputs, tmp_path)
    for f in out.glob("*.csv"):
        cols = pd.read_csv(f, nrows=0).columns
        assert not [c for c in cols if c in FORBIDDEN or c.startswith("player_")], f.name
        assert "0123456789abcdef" not in f.read_text(), f.name
    for c in FORBIDDEN + ["player_anything"]:
        with pytest.raises(export.ExportError, match="identifier"):
            export.check_output("pick_rate_did", t["pick_rate_did"].assign(**{c: 1}))


def test_hash_like_values_and_repeated_keys_stop_the_export(inputs, tmp_path):
    t, _ = run(inputs, tmp_path)
    p = t["pick_rate_did"].copy()
    p.loc[0, "fit_on"] = "dropped uploader 3f9a0c1d2e4b5a69"
    with pytest.raises(export.ExportError, match="hashed id"):
        export.check_output("pick_rate_did", p)
    with pytest.raises(export.ExportError, match="repeated"):
        export.check_output("weekly", pd.concat([t["weekly"], t["weekly"].head(1)]))


def test_meta_from_build_info(inputs, tmp_path):
    pytest.importorskip("duckdb")
    db = sample_results.write_sample_db(tmp_path / "runs.duckdb", build_info={
        **sample_results.SAMPLE_BUILD_INFO, "parser_version": "1.7.0", "pages_parsed": "12",
        "last_page": "11", "built_at_utc": "2026-09-29T10:00:00+00:00"})
    t, out = run(inputs, tmp_path, db=db, snapshot_end="2026-08-30")
    m = t["meta"]
    assert (m["parser_version"], m["snapshot_pages"]) == ("1.7.0", "12")
    assert m["snapshot_end_date"] == "2026-08-30" and m["blank_reasons"] == {}
    assert m["snapshot_end_date_source"] == "--snapshot-end"


def test_meta_dedup_fields_from_build_info(inputs, tmp_path):
    pytest.importorskip("duckdb")
    db = sample_results.write_sample_db(tmp_path / "runs.duckdb")
    t, out = run(inputs, tmp_path, db=db)
    d = json.loads((out / "meta.json").read_text())["dedup"]
    info = sample_results.SAMPLE_BUILD_INFO
    assert set(d) == set(export.DEDUP_FIELDS)
    for name, key in export.DEDUP_FIELDS.items():
        assert d[name] == int(info[key]) and isinstance(d[name], int)
    assert d["exact_repeats_dropped"] == 321 and d["primary_run_keys_retried"] == 2
    # a build_info without them (an older parser): left out, with the reason
    db2 = sample_results.write_sample_db(tmp_path / "old.duckdb", build_info={
        "parser_version": "1.4.0", "pages_parsed": "12", "last_page": "11",
        "built_at_utc": "2026-09-29T10:00:00+00:00"})
    m = run(inputs, tmp_path, db=db2)[0]["meta"]
    assert m["dedup"] == {}
    assert m["blank_reasons"]["dedup.solo_run_keys_retried"] == "not in build_info"
    # without --db: blank, reason "no --db given"
    m = run(inputs, tmp_path)[0]["meta"]
    assert m["dedup"] == {} and m["blank_reasons"]["dedup.records_read"] == "no --db given"


def test_meta_play_dates_from_run_tables(inputs, tmp_path):
    pytest.importorskip("duckdb")
    db = sample_results.write_sample_db(tmp_path / "runs.duckdb")
    t, out = run(inputs, tmp_path, db=db)
    m = json.loads((out / "meta.json").read_text())
    # primary runs only: the playtest-build record and the before-release one are outside
    assert (m["snapshot_start_date"], m["snapshot_end_date"]) == ("2026-03-18", "2026-07-02")
    assert m["play_dates_all_records"] == {"start": "2026-02-27", "end": "2026-07-04"}
    assert m["snapshot_end_date_source"] == "run tables"
    assert "primary" in m["snapshot_dates_source"] and m["blank_reasons"] == {}
    blob = json.dumps(m)
    assert not export.HASH_VALUE.search(blob)                 # aggregates only


def test_meta_play_dates_blank_without_runs(inputs, tmp_path):
    pytest.importorskip("duckdb")
    db = sample_results.write_sample_db(tmp_path / "runs.duckdb", runs=False)
    t, out = run(inputs, tmp_path, db=db)
    m = t["meta"]
    assert m["snapshot_start_date"] == "" and m["snapshot_end_date"] == ""
    assert "no runs table" in m["blank_reasons"]["snapshot_start_date"]
    t, out = run(inputs, tmp_path)
    assert "no --db" in t["meta"]["blank_reasons"]["snapshot_end_date"]


def test_cli(inputs, tmp_path, capsys):
    a, r = inputs
    export.main(["--analysis", str(a), "--out", str(tmp_path / "cli"), "--ref", str(r)])
    assert "pick_rate_did.csv" in capsys.readouterr().out
    with pytest.raises(SystemExit, match="export stopped"):
        export.main(["--analysis", str(tmp_path / "nowhere"), "--ref", str(r)])


def test_calibrated_rule_scales_the_se_by_the_patch_factor():
    beta = pd.Series([0.03, 0.05, 0.05, 0.0, np.nan, 0.05])
    se = pd.Series([0.01] * 6)
    patch = pd.Series(["first", "first", "second", "second", "second", "third"])
    got = export.clearly_nonzero_calibrated(beta, se, patch, {"first": 2.0, "second": 3.0})
    # z 3 and 5 against 2 x 2.0; z 5 and 0 against 2 x 3.0; no beta; no factor for the patch
    assert list(got) == ["no", "yes", "no", "no", "", ""]


def test_committed_results_give_the_calibrated_counts():
    """The factors, rounded as the site uses them, on the published estimates give the
    headline counts, and they agree with the unrounded factors in the numbers table."""
    p = pd.read_csv(ROOT / "results" / "pick_rate_did.csv")
    assert ((p.patch == "first").sum(), (p.patch == "second").sum()) == (26, 17)
    for est, se, factors, want in [(p.beta_h, p.se_h, export.PLACEBO_FACTORS_H3, (13, 2)),
                                   (p.beta, p.se, export.PLACEBO_FACTORS_ALL, (13, 4))]:
        clear = export.clearly_nonzero_calibrated(est, se, p.patch, factors) == "yes"
        assert (clear[p.patch == "first"].sum(), clear[p.patch == "second"].sum()) == want
    nums = json.loads((ROOT / "writeup" / "numbers.json").read_text())["numbers"]
    for hz, factors in [("h3", export.PLACEBO_FACTORS_H3), ("all", export.PLACEBO_FACTORS_ALL)]:
        for patch, f in factors.items():
            assert round(nums[f"did.{hz}.{patch}.calibrated.factor"]["value"], 2) == f
