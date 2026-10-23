# Field guide v2 rework: tracker

Phil's brief of 2026-10-22: typeset math throughout, code listings from the source, and the
reading notes ported in (decision log, PLAN.md). Four phases, one PR each. **Every rework session
starts here**: finish anything an earlier phase left open (marked *open* below) before starting
the phase Phil names.

Source material (git-ignored, Phil's study notes: read, never commit or copy outside
`writeup/`): `notes/field_guide_review/corrections.md` (items 1–9), `additions.md` (chapter 6
in full, then a backlog by chapter), `teaching_notes.md` (§1–§19, each with its "where I got
stuck", toy code and check questions).

## For Phil to check

Everything across the phases that Phil should look at when he reads the finished guide.

**New statements about real data** (summaries or readings of existing outputs; no new analysis):
- *Phase 1.* Key family `did.hand_vs_model.*` (chapter 6, "When the model and the hand
  calculation differ"): median and largest gap between model and hand 2×2 over the 43 tweaks.
- *Phase 2, no new keys.* Statements built from existing keys or columns:
  - Ch 1, mix-up on "short, smaller": v0.103.3 is "about half the size of the other before
    blocks" (`audit.offers_0_103_3` against `audit.offers_0_103_2`; the runs counts in the notes
    were not checked here because no per-build runs key exists).
  - Ch 2, "Selection bias, written out": "The effect the project reports for each tweak is an
    estimate of τ_ATT for that card" (a notation claim about the design), and Parry's before rate
    against its controls' as an instance of selection (existing Parry keys).
  - Ch 3, last section's project box: a single before-patch offer of Parry "sat well below the
    coin-flip maximum" of spread (qualitative, from `treated_rate_before`).
  - Ch 4, "The error of a difference": v0.103.3's offers set the floor of every second-patch
    effect's error (`audit.offers_0_107_1`, `audit.offers_0_103_3`); "a few thousand offers for
    a typical card" (from the notes' rough count, stated as rough).
  - Ch 5, spillover section: the real drop-shared-screens shift
    (`robustness.h3_drop_shared_screens.median_shift_se`) "looks more like B than A", and the
    reading "the first patch had much more to spill", labelled "One reading, not tested" (it is
    your reading from the notes, §13).
  - Ch 5, type-wide shocks: "whether non-card changes hit one card type unevenly is not
    checked" (red label), pointing to chapter 14 (corrections item 3; the open question itself
    is phase 4's to add).

**Suggested changes to your passages:** none so far (chapters 0–6 hold no "what was found"
passage).

**Notation and structure that affect the whole guide** (phase 2; details in the decision log):
- Potential outcomes as in chapter 2: $D_i$ treatment, $Y_i(1)$, $Y_i(0)$, $τ_i$, $τ_ATE$, $τ_ATT$,
  $E[·]$. Chapter 5 adds $μ_{t,s}$, a cell's untreated pick rate. Chapters 7–14 should reuse
  these (for instance the IV chapter's $Z$, $D$, $Y$).
- Renamed to keep one meaning per letter: chapter 6's interaction coefficient θ → λ (θ is the
  generic true value, used by chapter 6's delta-method box too); chapter 6's number of columns
  k → K (k is the number of picks; the code still says `k`, and the text says so); chapter 1's
  build is $B$ (not $b$, the slope); spillover is ψ (not σ); the hashing key is "salt"; bias is
  written out ("bias"), not $b$; the Wilson half-width is "hw"; a week is $u$.
- Chapter 1 defines $y_i$ and $i$ (eq. 1.1); chapter 5 defines $T_i$, $A_i$, $\bar y_{t,s}$ and
  the DiD (eq. 5.1); chapter 6 now recaps them and refers back.
- Corrections item 1's replacement text went into chapter 2's WATCH OUT, where the quoted text
  ("Error bars measure luck only") actually was. Chapter 4 got the full precision/accuracy
  treatment (§6) as a section.

**Anything I was unsure of:**
- Chapter 1 says the salt "lives only on Phil's machine" (CLAUDE.md and `runs.py` say it is a
  git-ignored file or an environment variable; I took "only on Phil's machine" from the
  snapshot rule).
- Chapter 1's collision remark ("vanishingly small" for a few million records at 64 bits) is
  arithmetic in words, not a key.
- Toy parameters stated in words, not keys (as phase 1 did): "ten weeks" (drift), "fifty
  offers", "three cards per screen".

| Phase | Scope | Status |
|---|---|---|
| 1 | Infrastructure; chapter 6 as the pilot | Done (CC, 2026-10-22); Phil approved the approach |
| 2 | Chapters 0–5 | Done (CC, 2026-10-22): 112 → 152 pages |
| 3 | Chapters 7–10 | Not started |
| 4 | Chapters 11–14, appendices A–E, full read-through | Not started |

## Per chapter

"Eqs" and "listings" count what the rework added. Teaching-notes sections are §N; additions are
the backlog lines of `additions.md`; corrections are items of `corrections.md`.

| Chapter | Status | Corrections | Additions | Teaching notes | Eqs | Listings | Suggestions for Phil's passages |
|---|---|---|---|---|---|---|---|
| 0 Project | **Done** (phase 2) | | "how this guide is built" (brief) | | 0 | 3 | none (no Phil passage) |
| 1 Data | **Done** (phase 2) | 6 (mix-up) | thin builds and pooling (§12, ch 1 part) | §12 | 10 | 3 | none |
| 2 Confounding | **Done** (phase 2) | 1 (WATCH OUT) | | §9 (skill), §6 (box) | 5 | 0 | none |
| 3 Counting | **Done** (phase 2) | | spread of one offer (§1); log-odds pointer (§5) | §1, §5 (pointer) | 7 | 1 | none |
| 4 Noise | **Done** (phase 2) | 1 (via §6) | standard errors (§2–4); bias box (§6) | §2, §3, §4, §6, §7 | 15 | 5 | none |
| 5 DiD | **Done** (phase 2) | 3 (named, unverified) | simpler comparisons (§14); parallel trends (§15); spillover (§13, ch 5 part) | §9, §13, §14, §15 | 10 | 4 | none |
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
| B Glossary | Chapters 0–6 terms added; notation table covers chapters 0–6 (phase 2) | | | | | | |
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

### Chapters 0–5 (phase 2), what's in them

- **Ch 0**: the plain box names the toys' labels; "How to read this guide" introduces the three
  new boxes and the math conventions (hat, bar, $i$, E, Greek letters); new section "How the
  guide keeps its numbers honest" with IN CODE `numbers.build_start` (an excerpt), 
  `numbers.table_add` (`fmt_num`, `Table.add`) and `writeup.lint_text`. No equations.
- **Ch 1**: `eq-offer` ($y_i$), `eq-window`, `eq-run-key`, `eq-retried`, `eq-player-hash`,
  the collision bound (in THE MATH, IN FULL, unlabelled), `eq-primary`, `eq-offers`,
  `eq-thin`, `eq-pool`. Listings `runs.keys`, `runs.dedup_views` (SQL constants),
  `runs.primary_filter`. Mix-ups: "not checked against the patch notes" (§12); v0.103.3 is short
  and smaller, not thin (corrections item 6).
- **Ch 2**: potential outcomes (`eq-po-observed`, `eq-tau-unit`, `eq-ate-att`); new section
  "Selection bias, written out" (`eq-naive`, derivation in THE MATH, IN FULL, randomization
  makes the term vanish); mix-up: skill threatens the strength question directly and the pick
  question only through a mix shift (§9). Corrections item 1's WATCH OUT. A fourth check on
  the "more data" section (narrow and in the wrong place).
- **Ch 3**: `eq-phat`, `eq-bern-mean`, `eq-points-percent`, `eq-mean-var`; new section "The
  spread of one offer, and why we square" (§1): `eq-signed`, `eq-bern-var`, `eq-bern-sd`,
  shortcuts and MAD ≤ SD in THE MATH, IN FULL, seesaw (moment of inertia) picture, figure
  `fig_toy_bernoulli_sd`, listing `teaching_sims.bernoulli_spread`, three mix-ups (one offer has
  no spread; the coin-flip coincidence; the two-thirds rule). Log-odds: a pointer paragraph
  to chapter 6, not a second treatment.
- **Ch 4**: SE derived (`eq-var-sum`, covariance form in THE MATH, IN FULL, `eq-var-phat`,
  `eq-se`); new sections "The spread of the data against the spread of the estimate" (§2,
  `fig_toy_sd_vs_se`, listing `sd_vs_se`, mix-up), "Why the bell" (§3, `eq-lln`, `eq-clt`,
  `fig_toy_lln_clt`, a table of SE against reruns, listing `lln_clt`, two mix-ups), "The error
  of a difference" (§7, `eq-se-diff`, `fig_toy_se_difference`, listing `se_difference`, mix-up
  on sample size, v0.103.3 as the floor), "Very small samples" (§4, `eq-wilson`,
  `eq-posterior`, Bayes in THE MATH, IN FULL, `fig_toy_posterior`, the intervals table, listing
  `teaching_sims.intervals`, mix-up); intervals gain `eq-ci`, `eq-z`, `eq-false-share`; the
  last section becomes "Precision, accuracy, and what a standard error does not cover" (§6,
  `eq-mse` with derivation, `eq-bias-z`, `fig_toy_fixed_bias`, coverage table, listing
  `fixed_bias`, `eq-expected-false`).
- **Ch 5**: `eq-did` (the DiD from four cells; chapter 6 refers to it), `eq-did-cells-po`,
  `eq-after-only`, `eq-before-after` (each simpler comparison as effect plus a named term),
  `eq-did-bias`, `eq-parallel`; the A/B test and what its control is, CUPED, the beta branch as a
  staggered rollout, the offer randomization (§14, `four_ways` table and listing, mix-up). New
  section "Can pick rates trend if cards compete?" (§15: `eq-screen-total`, `eq-drift-step`,
  `fig_toy_drift`, listing `drift`, mix-up, flat-after and horizon discipline). New section
  "When the controls are partly treated: spillover" (§13: SUTVA, `eq-spillover`,
  `fig_toy_spillover`, the A/B scenario table, listing `teaching_sims.spillover_all`, control
  scope, the estimand question). New section "Shocks to one kind of card" (§9:
  `eq-type-shock`, `fig_toy_type_shock`, listing `type_shock`, corrections item 3 as
  unverified).
- **Ch 6**: references now point at `eq-did`, `eq-bern-var`, `eq-var-phat`, `eq-se-diff`,
  `eq-offer`; θ → λ for the interaction; k → K for the number of columns.
- **Appendix B**: glossary rows for chapters 0–5's new terms (spillover and event study now
  introduced in chapter 5); notation table reordered from chapter 0 with chapters 1–5's
  symbols.

## Infrastructure (phase 1), for later phases

- **Boxes** (`style.typ`): `#mixup[...]` (COMMON MIX-UP), `#mathfull[...]` (THE MATH, IN FULL;
  may break across pages), `#incode("name", [caption])[walk-through]` (IN CODE), plus v1's and
  `#skill`. Each "where I got stuck" in the notes becomes a `#mixup`, in neutral second person.
- **Listings**: `#listing("name", [caption])`. A name is `<module>.<function>` under
  `spirometry`, or an entry in `writeup.LISTINGS` (several functions; an excerpt by start/end
  pattern; `doc="first"` or `"none"` to shorten a docstring). Since phase 2 a module-level
  constant (`NAME = ...`, such as `runs.PRIMARY_FILTER`) works too, with the comment block
  above it. At most 60 lines; show the core of
  a longer function with start/end. `python -m spirometry.writeup listings` extracts them alone.
- **Equations**: `$ ... $ <eq-name>`; numbered by chapter automatically; refer with `@eq-name`
  ("Equation (6.3)"). No digits in labels. Every display equation is followed by a sentence
  starting "In words:" that reads it from the left-hand side.
- **Digit lint in math**: single digits are fine; decimals and multi-digit integers need a key
  (`$#n("key")$` works inside math) or an `ALLOW` entry. 1.96, 1.4826, HC1/CR1/CRV1 and (phase
  2) SHA-256 / HMAC-SHA256 / `hashlib.sha256` are allowed. Never write a literal key call in
  prose (`#n("...")` inside backticks): the key test reads it as a key.
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
  before); real build, then render the changed pages (`pdftoppm -r 100`) and read them. In the
  local sandbox pytest can't even stat `.spirometry_salt` while collecting; a tiny plugin that
  ignores that path (`pytest_ignore_collect`) gets round it without touching the repo.
- **Notation**: check the notation table in Appendix B before choosing a letter. Taken across
  chapters 0–6: $i, r, c, y, B, W, N, L, D, Y, τ, E, p, k, n, s, z, θ, μ, σ, T, A, g, u, κ, ψ, h,
  w, x, a, b, c, d, ε, e, α, φ, γ, δ, η, β, X, K, V, G, ρ, m, H, λ, Δ$. Free and natural for
  phase 3: $f$ (calibration factor, as the notes use), $d_j$ (dose; chapter 6's $d$ is a 2×2
  coefficient, so consider $x_j$ or "dose"$_j$), $s$ is taken (sample SD), so the dose slope
  needs another letter or a subscript.

## Open items for later phases

- *Phase 2*: done (see above). Nothing left open.
- *Phase 3*: recap, don't repeat, what chapters 4–5 now cover: the event study and drift
  (chapter 7 should cite `eq-drift-step` and the drift toy, and add the event-study regression
  itself), precision against accuracy and `eq-bias-z` (chapter 8's calibration), `eq-se-diff`
  (the before-block pooling decision, §17). Chapter 7's offer-rate z's use `eq-z`. Chapter 8's
  "what 51% flagged implies" needs a key computed from the real placebo
  share with `teaching_sims.implied_factor` (add to `spirometry.numbers`; it is a transformation
  of an existing number). Listings: `did.placebo_fit`, `placebo_summary`, the calibrated count
  (`sensitivity.calibrated_counts`), `meta.meta_regression` / `dose_response_fits`,
  `did.control_cards`, `did.load_window` (probably an excerpt: it builds SQL). Corrections item 8
  goes to chapter 14 / Appendix D, not chapter 7's body.
- *Phase 4*: corrections items 2, 3, 8, 9 as open questions (not run) in chapter 14 and
  Appendix D (chapter 5 already points to chapter 14 for item 3's type-level placebo, so that
  question must exist there); chapter 12's spillover and control-scope section should recap
  chapter 5's spillover section and toy rather than repeat them; Appendix B's glossary gets the teaching notes' physics analogues (a fourth column,
  or in the meaning); Appendix E's interview vocabulary; listings of
  `sensitivity.power_simulation`, `wins.iv` / `first_stage` / `itt`, `iv_sim`; then the full
  read-through for notation, cross-references and equation numbers.
- Not in the brief's scope (pipeline): corrections items 4 and 5.
