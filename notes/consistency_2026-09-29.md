# Consistency pass, 2026-09-29

What changed in the docs and notebooks after the rerun on the 1,393-page tables (parser 1.7.0,
submissions to ~2026-08-23), and where each new number comes from. The first-pass outputs are
kept in `data/analysis_p949/` and `data/audit_p949/`.

## Sources

- **nb01 outputs** (`01_data_audit.ipynb`, run 2026-09-28): funnel, runs per build, thin
  builds, before-release and non-release counts, fast wins, mod-marker counts, upload lag,
  uploader-group table, the v0.103.2 weekly table.
- **nb02 outputs** (`02_pick_rate_did.ipynb` v3, run 2026-09-29): data checks, offers per
  build, offer-rate table, Parry by hand, clustering ratios, robustness summary, second-patch
  checks, dose-response (weeks 0–3), placebos, timing balance.
- **Recomputed from the saved fits** (`data/analysis/*.parquet`, no refitting): counts "in
  the direction of the change", pre-trend slopes, old-build offers after release, the
  all-weeks dose-response, the tagged–untagged correlation and χ². Each definition was
  checked first by reproducing the first-pass numbers from `data/analysis_p949/` exactly
  (22/18, 6/4, 1.03 ± 0.18, 1.10 ± 0.18, 0.68 and χ² 63, 8,315 and ~1,500).
- **Download log and raw pages** (`snapshot.log`, `sts2_snapshot/`): the repeated pages, the
  cursor date, snapshot size.
- **Reference tables**: v0.110.0's card events and none on v0.110.1.

## Files

| New file | Replaces | What changed |
|---|---|---|
| `SPIROMETRY_new.md` | `SPIROMETRY.md` | Status header; snapshot facts (size, cursor date, the repeated pages and why they're harmless, `player_token` coverage); run-table duplicate counts; "Phase 5 results" rewritten on the new numbers, with a "Changes from the first pass" paragraph; "Audit decisions" rewritten (thin builds, backfill numbers, ascension finding, uploader table); Known data issues counts; Open questions item 1 |
| `PLAN_new.md` | `PLAN.md` | Phase 1, 2, 3, 4 and 5 status lines; Next up items 1, 2, 5, 6, 7 (new (l), (m); (f) done), 8 (empty cached lists); decision log: three entries annotated, one appended (v0.110.0 thin, to confirm) |
| `README_new.md` | `README.md` | Status line; notebooks row (02 and the IV primer); `data/analysis/` row |
| `notebooks/01_data_audit_new.ipynb` | `01_data_audit.ipynb` | One markdown line (snapshot reach). Code and outputs untouched |
| `notebooks/02_pick_rate_did_new.ipynb` | `02_pick_rate_did.ipynb` | Six markdown cells (deck version, version 3 note, dedup note, timing-bias sentence, Skewer ratio, after-period lengths, section 9 item); `con.close()` added as the last cell. Other code and all outputs untouched |

Swap in from the repo root, one file at a time, e.g. `mv SPIROMETRY_new.md SPIROMETRY.md`,
then `git diff`.

## Interpretations that changed

1. **Upgrade-only placebos.** Royalties −3.0 ± 1.2 and Untouchable (v0.107.1) −1.3 ± 0.5
   points on un-upgraded offers, about 2.6σ; the first pass had all three within 1.6 SE.
   The docs no longer say "no attention effect"; drift in the second patch is the first
   candidate. New PLAN item 7 (l).
2. **Tagged-only fits** diverge more (median shift 1.5 → 2.3 main SEs); the SE ratio alone
   explains about 1.2. Feeds item (g).
3. **Second patch**: all 6 clearly nonzero estimates now go the expected way (was 4 of 6);
   still no dose-response.
4. **Pre-trends**: Fight Me now above 2 SE, Gather Light below.
5. **Offer-rate**: The Scythe sits at the threshold (z 3.00) and no longer flags.
6. **Audit**: rising ascension doesn't explain the within-build win-rate drift; v0.110.0 is
   the new thin build.

## Not updated, and why

- **"When in the run"** (SPIROMETRY.md): kept at the first-pass numbers and marked as not
  rechecked. nb02's new summary table uses each act's first and last floor, which land on
  boss floors, so it can't replace the old numbers. Cell to run (scratch is fine):

  ```python
  with duckdb.connect(str(DB), read_only=True) as c:
      bf = c.execute('''
          SELECT act, floor, count(*) AS offers, avg(picked::INT) AS pick_rate,
                 1 - avg(set_picked_any::INT) AS skip_rate
          FROM offers_with_version
          WHERE build_id IN ('v0.103.2', 'v0.107.1')
          GROUP BY act, floor ORDER BY floor''').df()
  display(bf[bf.floor.isin([2, 8, 15, 19, 25, 31, 36, 42, 47])].round(3))
  ```

- **`notes/phase5_deck_v3.pdf`**: a kickoff record; its numbers (slides 12–13) are from the
  949-page tables. SPIROMETRY.md's status header now says so.
- **Decision-log entries** are records of when a decision was made. Old numbers in them are
  left, with the new number added in parentheses where it matters.
- **`notes/*.md`**: none quote snapshot-dependent numbers.
- **The IV primer**: PLAN and README call it `notebooks/iv_primer.ipynb`; the file is still
  `iv_primer_draft.ipynb` (untracked). Rename it when you commit, or change the two
  references.
