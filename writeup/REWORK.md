# Field guide v2 rework: tracker

Phil's brief of 2026-10-22: typeset math throughout, code listings from the source, and the
reading notes ported in (decision log, PLAN.md). Four phases, one PR each. **Every rework session
starts here**: finish anything an earlier phase left open (marked *open* below) before starting
the phase Phil names.

Source material (git-ignored, Phil's study notes: read, never commit or copy outside
`writeup/`): `notes/field_guide_review/corrections.md` (items 1–9), `additions.md` (chapter 6
in full, then a backlog by chapter), `teaching_notes.md` (§1–§19, each with its "where I got
stuck", toy code and check questions).

| Phase | Scope | Status |
|---|---|---|
| 1 | Infrastructure; chapter 6 as the pilot | Done (CC, 2026-10-22). Phil reviews before phase 2 |
| 2 | Chapters 0–5 | Not started |
| 3 | Chapters 7–10 | Not started |
| 4 | Chapters 11–14, appendices A–E, full read-through | Not started |

## Per chapter

"Eqs" and "listings" count what the rework added. Teaching-notes sections are §N; additions are
the backlog lines of `additions.md`; corrections are items of `corrections.md`.

| Chapter | Status | Corrections | Additions | Teaching notes | Eqs | Listings | Suggestions for Phil's passages |
|---|---|---|---|---|---|---|---|
| 0 Project | Not started | | | | | | |
| 1 Data | Not started | | | | | | |
| 2 Confounding | Not started | | | | | | |
| 3 Counting | Not started | | | | | | |
| 4 Noise | Not started | | | | | | |
| 5 DiD | Not started | | | | | | |
| 6 Regression | **Done** (phase 1) | 7 | 6A, 6B, 6C, 6D; log-odds (§5) | §5, §16, §18, §19 | 18 | 7 | none (no Phil passage in ch 6) |
| 7 Checks | Not started; answer 7.8's wording fixed (item 6) in phase 1 | 6 (answer only) | | | | | |
| 8 Placebo | Not started | | | | | | |
| 9 Results | Not started | | | | | | |
| 10 Dose | Not started | | | | | | |
| 11 Rulers | Not started | | | | | | |
| 12 Explanations | Not started | | | | | | |
| 13 Wins | Not started | | | | | | |
| 14 Open | Not started; one "Still open" line's wording fixed (item 6) in phase 1 | 6 (one line) | | | | | |
| A Answers | Generated from `#check` | | | | | | |
| B Glossary | Chapter 6 terms added; notation table started (chapter 6 symbols) | | | | | | |
| C Numbers | Not started | | | | | | |
| D Open | Not started | | | | | | |
| E Talking | Not started | | | | | | |

### Chapter 6 (phase 1), what's in it

- Sections: a line through points (6A, the new opening picture, the 0/1 slope derivation, the
  2×2 as a saturated regression); reading the model line (the model in symbols matched to
  `fit_did`'s formula, OLS, normal equations, Frisch–Waugh–Lovell); when the model and the hand
  calculation differ (6B); why several kinds of SE (6C: iid, HC1, CR1, the hand rule, the design
  effect); what the fixed effects don't tell you (6D); log-odds (§5, logit, delta method).
- Equations `eq-line`, `eq-ls`, `eq-slope`, `eq-slope-binary`, `eq-twobytwo`, `eq-did-cells`,
  `eq-model`, `eq-ols`, `eq-fwl`, `eq-v-iid`, `eq-v-hc`, `eq-se-hand`, `eq-v-cr`, (the design
  effect, unlabelled), `eq-mix`, `eq-interaction`, `eq-logit`, `eq-delta`.
- Listings: `teaching_sims.did_regression`, `did.fit_did` (`_fixed_effects`, `_feols`,
  `_fit_did`), `did.subset_columns`, `teaching_sims.composition`, `teaching_sims.fit_layers`,
  `teaching_sims.heterogeneity`, `did.to_log_odds`.
- Mix-ups: §16 (binary axis has no slope), §18 (the exact match is always true), §19 (the
  ascension term is a breakdown), §5 (the baseline cancels).
- Figures: `fig_toy_two_columns`, `fig_toy_se_layers`, `fig_toy_log_odds`, plus the existing
  `fig_se_ratio`.
- New real-data key: `did.hand_vs_model.*` (decision log; flagged for Phil).

## Infrastructure (phase 1), for later phases

- **Boxes** (`style.typ`): `#mixup[...]` (COMMON MIX-UP), `#mathfull[...]` (THE MATH, IN FULL;
  may break across pages), `#incode("name", [caption])[walk-through]` (IN CODE), plus v1's and
  `#skill`. Each "where I got stuck" in the notes becomes a `#mixup`, in neutral second person.
- **Listings**: `#listing("name", [caption])`. A name is `<module>.<function>` under
  `spirometry`, or an entry in `writeup.LISTINGS` (several functions; an excerpt by start/end
  pattern; `doc="first"` or `"none"` to shorten a docstring). At most 60 lines; show the core of
  a longer function with start/end. `python -m spirometry.writeup listings` extracts them alone.
- **Equations**: `$ ... $ <eq-name>`; numbered by chapter automatically; refer with `@eq-name`
  ("Equation (6.3)"). No digits in labels. Every display equation is followed by a sentence
  starting "In words:" that reads it from the left-hand side.
- **Digit lint in math**: single digits are fine; decimals and multi-digit integers need a key
  (`$#n("key")$` works inside math) or an `ALLOW` entry. 1.96, 1.4826, HC1/CR1/CRV1 are allowed.
- **Toys**: `spirometry.teaching_sims` has every toy of §1–§19 (all 19 with code). Keys
  `toy.<toy>.<quantity>` (see `teaching_sims.csv` or `writeup/numbers.csv` for the list); label
  every toy number "a simulation with known truth" (or "a worked example, not your data" for the
  arithmetic ones). Figures already drawn, not yet placed:

  | Figure | Toy (§) | Target chapter |
  |---|---|---|
  | `fig_toy_bernoulli_sd` | §1 | 3 |
  | `fig_toy_sd_vs_se` | §2 | 4 |
  | `fig_toy_lln_clt` | §3 | 4 |
  | `fig_toy_posterior` | §4 | 4 |
  | `fig_toy_fixed_bias` | §6 | 4 |
  | `fig_toy_se_difference` | §7 | 4 |
  | `fig_toy_type_shock` | §9 | 5 |
  | `fig_toy_spillover` | §13 | 5 or 12 |
  | `fig_toy_drift` | §15 | 5 |
  | `fig_toy_false_alarms` | §11 | 8 |
  | `fig_toy_buffs_nerfs` | §8 | 9 or 10 |
  | `fig_toy_power` | §10 | 12 |

  Toys with numbers but no figure (tables in the text): `four_ways` (§14, ch 5; includes the
  check question's case), `did_regression`, `composition`, `heterogeneity` (ch 6, used),
  `small_samples` intervals (§4, ch 4).
- **Figure widths**: `#fig("name", width: small, [...])` (or `medium`); default full width.
- **Typst gotchas** met in phase 1: write `\;` after `#n(...)` or `#unverified[...]` (a bare `;`
  is swallowed); never put an apostrophe straight after a reference (`@ch-noise's` prints a
  prime): reword ("the rule in @ch-noise"); in math, separate letters (`T_i A_i`, not `T_iA_i`),
  quote words (`"Var"`), and use `dot` between fractions (`a / b dot c / d`).
- **Checks**: `pytest` (tests that read `reference/raw/` fail in the sandbox, 47 of them, as
  before); real build, then render the changed pages (`pdftoppm -r 100`) and read them.

## Open items for later phases

- *Phase 2*: chapter 0 needs listings of `numbers.build` and `writeup.lint_text` (both too long:
  add `LISTINGS` excerpts). The run parser's `run_key` and player-ID hashing (chapter 1,
  `spirometry.runs`). Chapters 3–4 define $p$, $n$, $hat(p)$, SE and the quadrature rule before
  chapter 6 uses them: move those rows of the notation table to chapters 3–4 and make chapter
  6's references point at the new equations (chapter 6 now says "the rule for a difference in
  @ch-noise" in words, and "@ch-counting" for $p(1 - p)$; link to the equations once they
  exist). Corrections item 1 (chapter 4's
  watch-out box). Chapter 5's DiD as four cell means: chapter 6 writes it as `eq-did-cells`;
  chapter 5 should define it first and chapter 6 should refer back.
- *Phase 3*: chapter 8's "what 51% flagged implies" needs a key computed from the real placebo
  share with `teaching_sims.implied_factor` (add to `spirometry.numbers`; it is a transformation
  of an existing number). Listings: `did.placebo_fit`, `placebo_summary`, the calibrated count
  (`sensitivity.calibrated_counts`), `meta.meta_regression` / `dose_response_fits`,
  `did.control_cards`, `did.load_window` (probably an excerpt: it builds SQL). Corrections item 8
  goes to chapter 14 / Appendix D, not chapter 7's body.
- *Phase 4*: corrections items 2, 3, 8, 9 as open questions (not run) in chapter 14 and
  Appendix D; Appendix B's glossary gets the teaching notes' physics analogues (a fourth column,
  or in the meaning); Appendix E's interview vocabulary; listings of
  `sensitivity.power_simulation`, `wins.iv` / `first_stage` / `itt`, `iv_sim`; then the full
  read-through for notation, cross-references and equation numbers.
- Not in the brief's scope (pipeline): corrections items 4 and 5.
