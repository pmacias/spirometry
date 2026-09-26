# Spirometry

Measuring what Slay the Spire 2's early-access balance patches actually did.

**Status:** work in progress — data acquisition. No results yet.

## The question

Slay the Spire 2's developers changed cards every few weeks during early access. Each change
is a natural experiment: the same card, before and after, played across hundreds of thousands
of community-submitted runs. For each change, this project estimates two things:

- **Behavior:** did players pick the card more or less often when it was offered?
- **Strength:** did picking it actually help runs win more or less?

Raw win rates can't answer the second question, because strong runs make different choices
than weak ones. The designs here lean on the fact that the game's RNG decides which cards are
offered, and on unchanged cards as a control for everything else that shifts between patches.
See [PLAN.md](PLAN.md) for the research questions and methods.

## Repository

| File | What it is |
|---|---|
| [PLAN.md](PLAN.md) | Research questions, phases, status, decision log |
| [SPIROMETRY.md](SPIROMETRY.md) | Reference: data sources, record structure, known data issues |
| [CLAUDE.md](CLAUDE.md) | Standing instructions for Claude Code sessions |
| `notes/` | Investigation notes: patch history endpoints (`patch_history.md`), run file structure and table proposal (`run_schema.md`), patch notes vs. card tables (`patch_notes_crosscheck.md`), card versions and DiD windows (`treatment_table.md`) |
| `src/spirometry/` | The package. `patch_history.py` builds the card patch dataset from Spire Codex; `patch_notes.py` parses the official patch notes and reconciles `builds.csv`; `notes_crosscheck.py` compares the two; `treatment.py` builds the per-build card versions and DiD windows from them; `runs.py` parses the run snapshot into Parquet + DuckDB run tables |
| `scripts/snapshot_export.py` | Downloads the run export, resumable, rate-limit aware |
| `scripts/audit_extract.py` | Interim: compact audit tables from the snapshot (runs, aggregated offer counts) into `data/audit/` |
| `notebooks/` | Analysis notebooks. `01_data_audit.ipynb`: integrity, coverage, filters, population mix, offers, power |
| `reference/` | Small committed reference tables: game builds, card changes, text-only labels, patch-note card mentions, cross-check, bug-fix behavior changes, beta-only changes, change events, card-patch net fields, per-build card versions, DiD windows (+ raw caches in `reference/raw/`: Spire Codex API incl. the game's enchantment, event, encounter and monster lists used as mod markers, wiki pages) |
| `data/runs/` | Run tables built locally by `spirometry.runs` (git-ignored, never committed) |
| `data/audit/` | Audit tables built locally by `scripts/audit_extract.py` (git-ignored) |
| `tests/` | pytest tests; `tests/fixtures/sample_runs.jsonl` holds 6 sample runs (the only run data in git; co-op player IDs replaced) |

## Setup

```bash
mamba create -n spirometry python=3.11
mamba activate spirometry
pip install -e .                  # core
pip install -e ".[analysis]"      # notebooks and analysis
pip install -e ".[dev]"           # tests
python -m pytest
```

Download the run snapshot (resumable; the export allows 120 pages an hour and has a daily
cap, so it takes a few days; the script sleeps through the limits):

```bash
python scripts/snapshot_export.py              # run from the repo root
python scripts/snapshot_export.py --count-only # runs per build from what's saved
```

Build the run tables from the snapshot (Parquet in `data/runs/<table>/`, views in
`data/runs/runs.duckdb`; rebuilding overwrites them). Player IDs are hashed with a key that
must stay the same between builds: create it once, keep a backup, never commit it.

```bash
python -m spirometry.runs init-salt          # once: writes .spirometry_salt (git-ignored)
python -m spirometry.runs build              # all pages, one worker per CPU
python -m spirometry.runs build --pages 2    # quick test on the first 2 pages
# options: --snapshot sts2_snapshot --out data/runs --workers N
# (or set SPIROMETRY_SALT instead of the file)
```

Data audit (interim tables from the raw snapshot, then the notebook):

```bash
python scripts/audit_extract.py              # all pages -> data/audit/*.parquet (a few minutes)
python scripts/audit_extract.py --pages 20   # quick test
# then run notebooks/01_data_audit.ipynb
```

Rebuild the card patch dataset in `reference/` (reads the committed API cache; fetches only
what's missing, at most 10 requests per minute). The build applies the card-change decisions
in PLAN.md's decision log and, when `patch_notes_cards.csv` exists, reruns the cross-check
and adds the notes-only rows to `card_changes.csv`:

```bash
python -m spirometry.patch_history          # fetch missing + build
python -m spirometry.patch_history build    # build from the cache only
```

Parse the official patch notes (wiki mirror, cached in `reference/raw/wiki/`), reconcile
`builds.csv`, and rebuild the cross-check tables:

```bash
python -m spirometry.patch_notes            # fetch missing pages + build
python -m spirometry.patch_notes build      # build from the cache only
```

Build the treatment tables (card change events, card-patch net fields, per-build card versions, DiD windows at event and card-patch level) from
the reference tables above; prints the stable-window check and the counts:

```bash
python -m spirometry.treatment
```

`python -m spirometry.runs build` then adds `offers_with_version` to `runs.duckdb`
(`primary_offers` with the card version on each run's build).

## Data

Run data and game data come from [Spire Codex](https://spire-codex.com)
([source](https://github.com/ptrlrd/spire-codex)), a community database of Slay the Spire 2
runs and game files. Spire Codex is not affiliated with Mega Crit, and neither is this project.

Patch notes are Mega Crit's, as transcribed on the [Slay the Spire Wiki](https://slaythespire.wiki.gg/wiki/Slay_the_Spire_2:Patch_Notes)
(CC BY-SA 4.0); the cached pages and the tables derived from them are under the same license.

Raw run data is not included in this repository. Player IDs are hashed in all derived tables,
and only aggregates are published.
