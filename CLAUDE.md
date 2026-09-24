# Instructions for Claude Code sessions

Read `PLAN.md` (roadmap and status) and `SPIROMETRY.md` (scope, data, known issues) before
starting. Treat anything `SPIROMETRY.md` marks "not yet verified" as unverified.

## Git
- Run `git fetch origin` and base your branch on `origin/main`. PRs are squash-merged, so
  old branches are stale.
- One task per branch. Finish by pushing and opening a pull request. Never merge; Phil does.

## Data
- Never touch `sts2_snapshot/`, `data/`, or any `*.duckdb` file. The full snapshot lives only
  on Phil's machine.
- For development, fetch at most a page or two from `/api/exports/runs` (each page costs one
  credit of a 120/hour budget that the local snapshot also uses). Keep fetched runs out of git.
- Other Spire Codex endpoints: at most 10 requests per minute. Cache raw responses and reuse
  the cache on reruns.
- Hash player IDs in anything derived from runs. Never commit raw run data.
- Don't guess missing values (dates, branches, versions). Leave them blank and say why.

## Code
- Package lives in `src/spirometry/`; dependencies only in `pyproject.toml`.
- Tests with pytest on small fixtures or fetched sample pages.
- Analysis notebooks and plots are Phil's. Build tables and tooling, not conclusions.

## Docs
- Update the relevant status line in `PLAN.md` and add any decisions to its decision log.
- Update `SPIROMETRY.md` when a fact about the data changes.
- Keep `README.md`'s repository table and setup commands current when you add, move, or
  rename files or change how something is run.
- End with a short summary: what changed, what you checked, what's still open.
