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
| `notes/` | Investigation notes (e.g. how the patch history endpoints behave) |
| `snapshot_export.py` | Downloads the run export, resumable, rate-limit aware |

## Setup

```bash
mamba create -n spirometry python=3.11
mamba activate spirometry
pip install -e .                  # core
pip install -e ".[analysis]"      # notebooks and analysis
```

Download the run snapshot (about 15 hours at the export's rate limit; resumable):

```bash
python snapshot_export.py
python snapshot_export.py --count-only   # runs per build from what's saved
```

## Data

Run data and game data come from [Spire Codex](https://spire-codex.com)
([source](https://github.com/ptrlrd/spire-codex)), a community database of Slay the Spire 2
runs and game files. Spire Codex is not affiliated with Mega Crit, and neither is this project.

Raw run data is not included in this repository. Player IDs are hashed in all derived tables,
and only aggregates are published.
