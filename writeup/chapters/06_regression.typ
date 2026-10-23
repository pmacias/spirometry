#import "../style.typ": *

= Regression: comparing like with like <ch-regression>

#lead[What the model in notebook 02 adds to the hand calculation, how it computes its answer,
  and how its error bars are built.]

The 2×2 table of @ch-did gives the right idea and nearly the right number. Your notebook, notebook 02, fits a
regression instead. It gives the same kind of answer, but it compares like with like (same
uploader group, same act, same ascension) and it comes with error bars that match how the
data were collected. This chapter explains what the model line means, when it must agree with
the hand calculation and when it needn't, how each kind of standard error is computed, and
what the model's adjustments do not tell you.

Notation for the chapter, as in @ch-data: an offer is indexed by $i$, and $y_i$ is its
outcome, one if the card was picked and zero if not (@eq-offer). $n$ is the number of offers in
a fit. Everything else is defined where it first appears; the notation table in @app-glossary
collects it.

== A line through points, or a difference of averages

#picture[
  Plot height against age for children and draw the best straight line through the points.
  The line's slope says how much taller a child is, on average, for each extra year. Now keep
  only seven-year-olds and eight-year-olds, coded zero and one. The dots form two columns, and
  the best line passes through each column's average. The columns are one unit apart, so the
  slope is the difference between the two averages. A regression with yes-or-no inputs is a
  machine for computing differences of averages, adjusted for whatever else you put in.
]

#words[
  - *Regression*: a fitted relation between an outcome and one or more inputs.
  - *Coefficient (β)*: the fitted effect of one input on the outcome, holding the other
    inputs fixed.
  - *Least squares (OLS, ordinary least squares)*: the rule that picks the line. Of all
    lines, take the one with the smallest sum of squared vertical distances to the points.
  - *Residual*: an observation's outcome minus the line's fitted value for it, $e_i$.
  - *Linear probability model*: a regression whose outcome is zero or one (here, picked).
    Its fitted values are pick rates and its coefficients are in pick-rate units: a
    coefficient of five hundredths means five more picks per hundred offers.
  - *Saturated model*: a model with one number per cell of the table, so it reproduces every
    cell's average exactly.
]

A straight line through points $(x_i, y_i)$ is

$ y_i = a + b x_i + epsilon_i $ <eq-line>

In words: each outcome $y_i$ is an intercept $a$, plus a slope $b$ times the input $x_i$, plus
whatever the line leaves over, $epsilon_i$. Least squares chooses the estimates $hat(a)$ and
$hat(b)$ (the hats mark numbers computed from data) that make the leftovers as small as
possible in total:

$ (hat(a), hat(b)) = "argmin"_(a, b) sum_i (y_i - a - b x_i)^2 $ <eq-ls>

In words: the fitted intercept and slope are the pair that minimises the sum of squared
vertical distances from the points to the line. The answer for the slope is a standard
formula, with $overline(x)$ and $overline(y)$ the averages of the inputs and outcomes:

$ hat(b) = (sum_i (x_i - overline(x)) (y_i - overline(y))) / (sum_i (x_i - overline(x))^2) $ <eq-slope>

In words: the slope is how much $x$ and $y$ move together, divided by how much $x$ moves on its
own.

*Why the line passes through the averages.* Within one column the input doesn't vary, so the
best a straight line can do there is hit the column's middle. The middle that minimises a sum
of squares is the average: set the derivative of $sum_i (y_i - m)^2$ with respect to $m$ to
zero and you get $m = overline(y)$. With two columns one unit apart, rise over run is the
difference of the averages divided by one. Write $overline(y)_1$ for the average outcome of
the column at one and $overline(y)_0$ for the column at zero:

$ hat(b) = overline(y)_1 - overline(y)_0, quad hat(a) = overline(y)_0 $ <eq-slope-binary>

In words: with a zero-or-one input, the fitted slope is the difference between the two
columns' averages, and the intercept is the average of the column at zero.

#mathfull[
  Put @eq-slope to work on a zero-or-one input. Say $n_1$ observations have $x_i = 1$ and
  $n_0$ have $x_i = 0$, with $n = n_0 + n_1$. Then $overline(x) = n_1 slash n$, so
  $x_i - overline(x)$ is $n_0 slash n$ in the first column and $-n_1 slash n$ in the second.

  The denominator: $sum_i (x_i - overline(x))^2 = n_1 (n_0 slash n)^2 + n_0 (n_1 slash n)^2
  = n_1 n_0 slash n$.

  The numerator: because $sum_i (x_i - overline(x)) = 0$, the $overline(y)$ term drops out
  and $sum_i (x_i - overline(x)) y_i = (n_0 slash n) n_1 overline(y)_1 - (n_1 slash n) n_0
  overline(y)_0 = (n_1 n_0 slash n)(overline(y)_1 - overline(y)_0)$.

  Divide, and the $n_1 n_0 slash n$ cancels: $hat(b) = overline(y)_1 - overline(y)_0$. The
  intercept follows from $hat(a) = overline(y) - hat(b) overline(x)$, which works out to
  $overline(y)_0$.
]

#mixup[
  You might read "zero and one" as erasing the real ages and keeping only a before-or-after
  flag, and conclude that a binary axis has no sensible slope. It has one, and it is exactly
  the number you want. The axis is still a number line; it just has points at two places.
  The best line runs through the two column averages, and because the columns sit one unit
  apart, its slope is their difference (@eq-slope-binary). A flag coded zero and one turns a
  regression into a calculator for differences of averages.
]

*The 2×2 table as a regression.* Write the DiD with three yes-or-no inputs: the labels of
@ch-did, $T_i = 1$ if the offer is of the treated card and $A_i = 1$ if it is in the after
block, and their product $D_i = T_i A_i$, which is one only for the treated card after the
patch:

$ y_i = a + b T_i + c A_i + d D_i + epsilon_i $ <eq-twobytwo>

In words: an offer's chance of being picked is the controls' rate before ($a$), plus the gap
between the treated card and the controls before ($b$) if it is the treated card, plus the
controls' change over time ($c$) if it is after the patch, plus $d$ if it is both. With
$overline(y)_(t, s)$ the average outcome in the cell with $T = t$ and $A = s$ (as in @eq-did),
the model's fitted value in each cell is the cell's average:

#align(center, ftable(
  columns: (auto, auto, auto),
  [], [*Before* ($A = 0$)], [*After* ($A = 1$)],
  [*Controls* ($T = 0$)], [$overline(y)_(0, 0) = hat(a)$], [$overline(y)_(0, 1) = hat(a) + hat(c)$],
  [*Treated* ($T = 1$)], [$overline(y)_(1, 0) = hat(a) + hat(b)$],
  [$overline(y)_(1, 1) = hat(a) + hat(b) + hat(c) + hat(d)$],
))

Take the treated row's change and subtract the controls' change, and everything but $hat(d)$
cancels:

$ hat(d) = (overline(y)_(1, 1) - overline(y)_(1, 0)) - (overline(y)_(0, 1) - overline(y)_(0, 0)) $ <eq-did-cells>

In words: the coefficient on "treated and after" is the treated card's change minus the
controls' change, which is the DiD of @eq-did. The model has four numbers for four cells, so it
can match every cell exactly: it is saturated, and here the regression and the hand
calculation agree by construction.

#fig("fig_toy_two_columns", width: small, [A simulation with known truth: the best line through two columns
  joins their averages. Heights of #n("toy.two_columns.n") simulated children, true gap
  #n("toy.two_columns.true_gap") cm; the dots are spread sideways only so they show.])

#project[
  *A simulation with known truth.* In the heights example the fitted
  slope is #n("toy.two_columns.slope") cm and the difference of the two columns' averages is
  #n("toy.two_columns.mean_diff") cm: the same number, as @eq-slope-binary says it must be. In a
  simulated 2×2 of #n("toy.did_regression.n") offers with a true DiD of
  #n("toy.did_regression.true_did"), the interaction coefficient is
  $hat(d) = #n("toy.did_regression.d")$ and the DiD from the four cell averages is
  #n("toy.did_regression.did_by_hand"), equal to every printed digit.

  *Your data.* In notebook 02 the outcome is "picked" for each offer of the treated card and
  its controls, and the input of interest is "this is the treated card, in the after block".
  Its coefficient is the DiD. For Parry the model gives #n("tweak.parry.v0_103_2.all.beta_pp_pm")
  points, the hand calculation #n("tweak.parry.v0_103_2.did_raw_pp").
]

#incode("teaching_sims.did_regression", [The 2×2 table as a regression, in a simulation.])[
  *What goes in:* a number of offers and a true DiD. *What comes out:* the four
  coefficients, the four cell averages and the DiD worked out by hand. The lines that matter:
  `X = np.c_[...]` builds the four columns of @eq-twobytwo (a column of ones for $a$, then
  $T$, $A$ and $T times A$), and `np.linalg.lstsq` solves the least-squares problem of
  @eq-ls for all four at once. The `m` helper averages one cell, and `did_by_hand` is
  @eq-did-cells. The test suite checks that $hat(d)$ and the hand DiD agree.
]

#watch[
  A coefficient "holding the others fixed" is only as good as the list of others. A
  regression adjusts for what you put in, never for what you left out.
]

#skill[
  *Seeing a regression as a comparison.* Before reading coefficients, ask which two groups of
  observations the key coefficient compares, and what is held equal between them.
]

#check(
  ([In a regression with one yes-or-no input, what does the best-fitting line do?],
   [It joins the two group averages, so the slope is the difference between them.]),
  ([With the input coded zero and one, why is the slope exactly the difference of the two
    averages?],
   [The line passes through each column's average (the average is the value that minimises
    a column's sum of squares), and the columns are one unit apart, so rise over run is the
    difference of averages divided by one.]),
  ([What does β mean in a linear probability model?],
   [The change in the probability of the outcome (here, the pick rate) associated with the
    input, holding the other inputs fixed.]),
  ([In the four-number version of the 2×2 table, which number is the DiD, and what are the
    other three?],
   [The coefficient $d$ on "treated and after". The others: $a$, the controls' rate before;
    $b$, the treated card's gap to its controls before; $c$, the controls' change over
    time.]),
  ([Why do the hand calculation and the model for Parry differ slightly?],
   [The model compares offers within the same uploader group, act and ascension and weights
    them by how much data each comparison has; the hand calculation pools everything.]),
)

== Reading the model line

#words[
  - *Fixed effects*: a separate baseline for each group, so comparisons happen within the
    group. A fixed effect for each card means each card has its own usual pick rate.
  - *Singleton*: a fixed-effect group with a single observation. It can't be compared with
    anything, so it is dropped.
  - *Design matrix* ($X$): the inputs laid out as a table, one row per offer and one column
    per number the model estimates.
]

#picture[
  Grading students within their own class: a teacher who marks hard and a teacher who marks
  easy both produce fair rankings within their class. Fixed effects do the same: each card
  (and each uploader group, block, act and ascension level) gets its own baseline, and the
  effect is read from the differences within those baselines.
]

The model in words. Whether an offer was picked depends on:
- which card it is, with upgraded and un-upgraded versions as separate cards, and a separate
  baseline in each uploader group;
- the block (before or after) in each uploader group, which captures everything that moved
  all of the character's cards between builds;
- the act of the run in which the card was offered;
- the ascension level, one baseline per level;
- and the treated card in the after block. This term's coefficient is the effect.

The same model in symbols. For offer $i$, let $"card"_i$ be the card, $"upg"_i$ whether it
was upgraded, $"grp"_i$ the uploader group (tagged or untagged), $"blk"_i$ the block (before
or after), $"act"_i$ the act and $"asc"_i$ the ascension level, and $D_i = T_i A_i$ as before.
The subscripts are named after the columns of your data:

$ y_i = alpha_("card"_i, "upg"_i) + phi_("card"_i, "grp"_i) + gamma_("blk"_i, "grp"_i)
  + delta_("act"_i) + eta_("asc"_i) + beta D_i + epsilon_i $ <eq-model>

In words: an offer's chance of being picked is its card's baseline for that upgrade state
($alpha$), adjusted for the card's standing in that uploader group ($phi$), plus the shift of
the whole block in that uploader group ($gamma$), plus an act term ($delta$) and an ascension
term ($eta$), plus the effect $beta$ if it is the treated card after the patch. Each Greek
letter with subscripts is a fixed effect: a whole set of numbers, one per card, per block, per
act or per level. $beta$ is the one number the notebook reports. With one uploader group in
the data, $phi$ drops out and $gamma$ is per block only. The card terms replace $a + b T_i$ of
@eq-twobytwo, and the block terms replace $c A_i$.

Every model of this kind is solved the same way. Stack the outcomes into a column $y$ and the
inputs into the design matrix $X$, with one column per number to estimate; the least-squares
estimates of all of them at once are

$ hat(bold(beta)) = (X^top X)^(-1) X^top y $ <eq-ols>

In words: the vector of fitted coefficients is the inverse of the inputs' cross-products,
times the inputs' cross-products with the outcome. It is @eq-slope with many inputs: $X^top y$
plays the part of "how inputs and outcome move together" and $X^top X$ the part of "how the
inputs move on their own". (Bold $bold(beta)$ is the whole vector of coefficients; plain
$beta$ is the one on $D$.)

#mathfull[
  Least squares minimises $S(bold(beta)) = (y - X bold(beta))^top (y - X bold(beta))$, the
  sum of squared residuals. Its gradient is $-2 X^top (y - X bold(beta))$. Setting it to zero
  gives the *normal equations* $X^top X hat(bold(beta)) = X^top y$, and when $X^top X$ can be
  inverted (no column is a combination of the others) the solution is @eq-ols. One reading
  of the normal equations is useful: $X^top e = 0$, so the residuals are uncorrelated with
  every input. Whatever the model can explain with its columns, it has explained.
]

With thousands of fixed-effect levels, $X$ would have thousands of columns, so software
doesn't build it. It uses a result known as the Frisch–Waugh–Lovell theorem: the coefficient
on $D$ is the same as the slope from a simpler regression of leftovers on leftovers. Write
$tilde(y)_i$ and $tilde(D)_i$ for what is left of $y_i$ and $D_i$ after removing every fixed
effect (each offer's value minus what the card, group, block, act and ascension baselines
predict for it). Then

$ hat(beta) = (sum_i tilde(D)_i tilde(y)_i) / (sum_i tilde(D)_i^2) $ <eq-fwl>

In words: the effect is how much the leftover pick outcome moves with the leftover "treated
and after" indicator, divided by how much that indicator moves on its own once the baselines
are taken out. It is @eq-slope again, on residuals. The package your notebooks use,
`pyfixest`, removes the fixed effects this way ("demeaning") and then fits the one slope.

#incode("did.fit_did", [The DiD fit as code: the fixed effects, the fit and the three
  standard errors.])[
  *What goes in:* the window's offers (`d`, from `load_window` and the filters) and the
  options. *What comes out:* $hat(beta)$ and its standard errors, the counts and the formula.
  The lines that matter:
  - `_fixed_effects` writes the terms of @eq-model. `"card_id^upg"` is $alpha$ (a level per
    card and upgrade state; `^` means "every combination of"), `"card_id^group"` is $phi$,
    `"block^group"` is $gamma$, and `"act"` and `"asc"` are $delta$ and $eta$. With one
    group, or `pooled_groups`, the group terms drop, as the text says.
  - `fml = "picked ~ treat_post | " + ...` is @eq-model as a formula: the outcome, then the
    one coefficient to report ($D$, called `treat_post`), then after the bar the fixed
    effects that are removed first (@eq-fwl).
  - `_feols` fits it with `vcov={"CRV1": CLUSTER}`: errors clustered by `run_key`, the
    formula of @eq-v-cr below. The two `fit.vcov(...)` lines refit only the errors, as
    `"hetero"` (HC1, @eq-v-hc) and `"iid"` (@eq-v-iid).
  - `n_singletons_dropped` counts the offers `pyfixest` dropped because they were alone in a
    fixed-effect cell.
  `treat_post` itself is built in `_subset` (the next listing): one for an offer of the
  treated card in the after block, zero otherwise.
]

#listing("did.subset_columns", [Where $D_i$ comes from: the columns `_subset` adds before the
  fit. (The filters above the cut apply the fit's options.)])

#project[
  *Your data.* The block term is where the controls do their work: they pin down how much every
  card moved between the blocks, and the treated card's coefficient is what is left. Dropping
  the uploader-group terms moves the estimates by a median
  #n("robustness.h3_pooled_groups.median_shift_se") SEs, so they changed little; they stay in
  because the groups differ (@ch-confounding). Singletons: #n("did.singletons_dropped.total")
  offers dropped across #n("did.singletons_dropped.n_tweaks") tweaks, at most
  #n("did.singletons_dropped.max") in any one. Offers with no recorded ascension are dropped.
  Whether each ascension level should be its own baseline or levels should be grouped in bands
  is #unverified[an open choice] (PLAN item 14).
]

#watch[
  A fixed effect for ascension is not a study of ascension. It removes differences between
  ascension levels from the comparison and nothing more; its own coefficients are not
  results. The section "What the fixed effects don't tell you" below takes this further.
]

#skill[
  *Reading a model specification.* Turn each term of a formula into a sentence about what
  is held fixed. If you can't say what a term absorbs, you can't say what the coefficient
  means.
]

#check(
  ([What does a fixed effect for each card do?],
   [It gives each card its own baseline pick rate, so the model compares a card's offers
    with that card's usual rate rather than with other cards' rates.]),
  ([Which term in the model absorbs "everything that moved all of the character's cards
    between builds"?],
   [The block term (before or after, in each uploader group), $gamma_("blk", "grp")$ in
    @eq-model, estimated mostly from the control cards.]),
  ([Match each term of the formula `picked ~ treat_post | card_id^upg + card_id^group +
    block^group + act + asc` to a symbol of the model.],
   [`treat_post` is $D$ with coefficient $beta$; `card_id^upg` is $alpha$; `card_id^group`
    is $phi$; `block^group` is $gamma$; `act` is $delta$; `asc` is $eta$.]),
  ([Why is a singleton dropped?],
   [It is the only observation in its group, so its group's baseline fits it exactly and it
    carries no information about the effect.]),
  ([In @eq-fwl, what are $tilde(y)$ and $tilde(D)$, and why does the software work with
    them rather than with the full design matrix?],
   [They are the outcome and the treated-after indicator with every fixed effect removed
    (what is left after the baselines). The coefficient on $D$ is the slope of one on the
    other, so the thousands of baseline columns never have to be built or inverted.]),
)

== When the model and the hand calculation differ

The 2×2 regression of @eq-twobytwo always reproduces the hand DiD, because it is saturated.
Your model isn't saturated: it has a baseline for every card, block, act and ascension level,
far fewer numbers than cells. Its coefficient becomes a weighted average of many small DiDs,
one per comparison it can make, weighted by how much each comparison contributes to
$sum_i tilde(D)_i^2$ in @eq-fwl. Comparisons with more offers, and with a more even split of
treated and control offers, get more weight. That's usually close to the hand calculation, and
when it isn't, the model is usually the one to trust: it compares each card with itself, so a
change in _which_ cards were offered can't masquerade as a change in how often they were
picked.

#words[
  - *Composition*: which cards (or acts, or ascension levels) make up a group's offers. If it
    shifts between blocks, a pooled average moves even when no card's own rate did.
  - *Weighted average*: an average in which some parts count more than others.
]

#picture[
  A shop's average sale goes up because it sold more of its expensive items, not because any
  price rose. Comparing each item's sales with its own past, not the shop's average with its
  past, removes that.
]

#mixup[
  You might read the exact match between the interaction coefficient and the hand DiD (the
  simulation above) as something that is always true of a regression. It is true only of a
  saturated model, where there is one number per cell and the fit has to hit every cell
  average. Add baselines that cut across the cells (cards, acts, ascension levels) and the
  coefficient becomes a weighted average of many small comparisons. It then differs from the
  pooled hand calculation, on purpose: it is adjusting for things a pooled average gets
  wrong.
]

#project[
  *A simulation with known truth.* A popular control card is offered more often after the
  patch: its share of offers goes from #n("toy.composition.share_popular_before") to
  #n("toy.composition.share_popular_after"). The true effect is
  #n("toy.composition.true_effect")\; the hand calculation on pooled controls gives
  #n("toy.composition.raw")\; the model with a baseline per card gives
  #n("toy.composition.fe"), close to the truth within the simulation's noise.

  *Your data.* For Parry the two agree (#n("tweak.parry.v0_103_2.did_raw_pp") by hand,
  #n("tweak.parry.v0_103_2.all.beta_pp_pm") from the model): the offer mix barely moved.
  Over all #n("did.hand_vs_model.n_tweaks") tweaks the model and the hand calculation are a
  median #n("did.hand_vs_model.median_gap_se") SEs apart, at most
  #n("did.hand_vs_model.max_gap_se") (all weeks).
]

#incode("teaching_sims.composition", [A shift in which controls are offered, in a
  simulation.])[
  *What goes in:* a number of offers and a true effect. *What comes out:* the raw pooled DiD
  and the coefficient from a regression with one column per card. The lines that matter:
  `mix_after` raises the popular control's share after the patch, so the pooled controls'
  average rises with no card's rate changing. `raw` is @eq-did-cells on the pooled cells.
  `X = np.c_[np.eye(4)[card], after, ...]` gives each card its own column (a card fixed
  effect, the $alpha$ of @eq-model), a shared after column ($gamma$) and the treated-after
  column ($D$); its last coefficient is $hat(beta)$ (@eq-ols).
]

#watch[
  Agreement between the model and the hand calculation is a check, not proof. Disagreement
  isn't automatically an error either: find which comparison the model is weighting
  differently, and why.
]

#skill[
  *Knowing when a model must reproduce a hand calculation.* A saturated model always will.
  Anything else is a weighted average; ask what the weights are.
]

#check(
  ([Why does the simple 2×2 regression always reproduce the hand DiD, while your model
    doesn't?],
   [The 2×2 has one number per cell. Your model has many more cells than numbers, so its
    coefficient is a weighted average of many small comparisons.]),
  ([A control card that's usually picked often is offered more after the patch. Which way
    does that push the hand calculation, and why doesn't it push the model?],
   [The pooled controls' rate rises from the mix alone, so the hand DiD comes out too low for
    a buff. The model compares each card with its own baseline.]),
  ([Which comparisons get the most weight in the model's coefficient?],
   [Those that contribute most to $sum_i tilde(D)_i^2$: comparisons with many offers and a
    fairly even split between treated and control offers.]),
)

== Why several kinds of standard error

#words[
  - *iid SE*: assumes every offer is independent and equally noisy.
  - *Robust (heteroskedasticity-robust) SE*: allows offers to be unequally noisy (a card
    picked half the time is noisier per offer than one picked rarely, @eq-bern-var). Your
    notebooks use the most common small-sample version of it, called HC1.
  - *Clustered SE*: also allows offers in the same run to be related. The main errors in
    this guide are clustered by run.
  - *Sandwich*: the shape of the robust and clustered formulas: the same "bread" on both
    sides of a "meat" built from the residuals.
]

#picture[
  Ask ten strangers whether they like a film and you have ten opinions. Ask ten members of
  one family and you have something closer to one opinion said ten times: they watched it
  together and talked about it. Clustering admits that offers from one run are a family: the
  same player, the same deck, the same run going well or badly.
]

All three estimate the same thing: how far the coefficient would move on a fresh sample
(@ch-noise; @eq-var-phat is the simplest case). They estimate it from the model's residuals, $e_i = y_i - hat(y)_i$, each offer's
outcome minus its fitted value. Below, $K$ is the number of columns in $X$ (`k` in the code) (numbers the model
estimates) and $hat(V)$ is the estimated variance of the coefficients; the SE of $hat(beta)$ is
the square root of its entry in $hat(V)$.

*iid: one shared noise level.* Every offer gets the same noise variance $hat(sigma)^2$,
estimated from all residuals together:

$ hat(V)_"iid" = hat(sigma)^2 (X^top X)^(-1), quad
  hat(sigma)^2 = 1 / (n - K) dot sum_i e_i^2 $ <eq-v-iid>

In words: the variance of the coefficients is the average squared residual times the inverse
of the inputs' cross-products. $(X^top X)^(-1)$ measures how little information the inputs
carry about each coefficient; the shared noise level scales it. It is wrong for a zero-or-one
outcome, whose variance is $p(1 - p)$ (@eq-bern-var) and differs from card to card.

*Robust: each offer keeps its own squared residual.*

$ hat(V)_"HC1" = n / (n - K) dot (X^top X)^(-1) (sum_i e_i^2 x_i x_i^top) (X^top X)^(-1) $ <eq-v-hc>

In words: the variance is the bread $(X^top X)^(-1)$ on both sides of a meat that adds up every
offer's own squared residual (with $x_i$ its row of $X$), times a small-sample factor
$n slash (n - K)$. Noisier offers count as noisier. For the 2×2 table it is the hand rule, each
cell's squared SE added (@eq-se-diff, one cell at a time), up to the
small-sample factors. Write $s_(t, s)^2$ for the variance of the outcome in a cell and
$n_(t, s)$ for its number of offers:

$ "SE"_"hand" (hat(d)) = sqrt(sum_(t, s) s_(t, s)^2 / n_(t, s)) $ <eq-se-hand>

In words: the hand SE of the DiD is the square root of the four cells' squared SEs added
together, because the DiD adds or subtracts the four cell averages and independent errors add
in quadrature.

*Clustered: sum within each run before squaring.* Let $g$ index runs (the clusters), $G$ be
the number of runs, and $X_g$ and $e_g$ be one run's rows of $X$ and its residuals:

$ hat(V)_"CR1" = G / (G - 1) dot (n - 1) / (n - K) dot (X^top X)^(-1)
  (sum_g (X_g^top e_g) (X_g^top e_g)^top) (X^top X)^(-1) $ <eq-v-cr>

In words: the same bread, but the meat first adds up each run's residual contributions and only
then squares them, with a small-sample factor in front. If a run's offers lean the same way,
their sum is larger than independent offers would give, and the error bar widens. Each run
counts as one independent piece of evidence. This is `pyfixest`'s `"CRV1"`, the `se` of every
fit in this guide.

#mathfull[
  Why summing first widens the error bar. Take a run with $m$ offers whose contributions
  $z_j = x_j e_j$ (for one coefficient) each have variance $v$, and any two of them have
  correlation $rho$. The variance of their sum is

  $ "Var"(sum_j z_j) &= sum_j "Var"(z_j) + sum_(j != l) "Cov"(z_j, z_l) \
    &= m v + m(m - 1) rho v = m v (1 + (m - 1) rho) $

  The robust meat counts only the first term, $m v$; the clustered meat counts both. The
  factor $1 + (m - 1) rho$ (the *design effect*, or Moulton factor) is how much the variance
  grows, and its square root is how much the SE grows. With $rho = 0$ the two meats agree;
  with many offers per run, even a small positive $rho$ adds up.

  Which correlation matters is the correlation of $x_j e_j$, not of the outcomes alone. A run
  that goes well for every card raises every residual in the run by the same amount. Within an
  after-block run, the "treated and after" column, once the fixed effects are removed, is
  positive for the treated card's offers and negative for the controls', so that shared lift
  enters $X_g^top e_g$ with both signs and largely cancels. A player's taste for the treated
  card alone does not cancel: it moves only the treated card's residuals. That is why
  clustering adds little to your SEs, and why the simulation below gives the player such a
  taste.
]

#fig("fig_toy_se_layers", width: medium, [A simulation with known truth: four standard errors of the DiD,
  from one dataset, against the true wobble of the estimate over
  #n("toy.se_layers.n_reruns") simulated reruns. Each run's player has their own taste for the
  treated card.])

#project[
  *A simulation with known truth.* #n("toy.se_layers.n_runs") runs of
  #n("toy.se_layers.per_run") offers each, and each run's player has a personal taste for the
  treated card. The hand rule, iid and robust SEs agree at #n("toy.se_layers.se_hand"),
  #n("toy.se_layers.se_iid") and #n("toy.se_layers.se_hc1")\; the clustered SE is
  #n("toy.se_layers.se_clustered")\; and the actual wobble of the DiD over
  #n("toy.se_layers.n_reruns") simulated reruns is #n("toy.se_layers.true_wobble"). Only
  clustering sees the taste: it reaches #n("toy.se_layers.ratio_clustered") of the true wobble,
  the iid SE #n("toy.se_layers.ratio_iid").

  *Your data.* Clustered SEs are larger than robust ones by a median factor of
  #n("se.clustered_over_robust.median") over the #n("tweaks.solo_estimable") tweaks (range
  #n("se.clustered_over_robust.min") to #n("se.clustered_over_robust.max")); Parry's is
  #n("tweak.parry.v0_103_2.se_over_robust"). The largest factors belong to common cards offered
  many times per run (Crescent Spear #n("tweak.crescent_spear.v0_107_1.se_over_robust")).
  Against iid SEs the ratio ranges from #n("se.clustered_over_iid.min") to
  #n("se.clustered_over_iid.max"), median #n("se.clustered_over_iid.median"), but that ratio
  mostly measures unequal noise between cards, which is why clustering is judged against the
  robust SE, not the iid one.
]

#fig("fig_se_ratio", [Clustered SE divided by robust SE for each tweak, against the treated
  card's number of offers.])

#incode("teaching_sims.fit_layers", [Four standard errors of one DiD, as in
  @eq-v-iid to @eq-se-hand.])[
  *What goes in:* each offer's run, treated and after flags, and outcome (from
  `simulate_runs`, which gives every run's player a taste for the treated card). *What comes
  out:* the interaction coefficient, the hand DiD and the four SEs. The lines that matter:
  - `bread = np.linalg.inv(X.T @ X)` is $(X^top X)^(-1)$, and `b = bread @ X.T @ y` is
    @eq-ols.
  - `V_iid` is @eq-v-iid: the average squared residual times the bread.
  - `V_hc1` is @eq-v-hc: `(X.T * e**2) @ X` is the meat $sum_i e_i^2 x_i x_i^top$.
  - `np.add.at(S, run, X * e[:, None])` adds each offer's $x_i e_i$ into its run's row, so
    `S.T @ S` is the clustered meat of @eq-v-cr. This one line is the whole difference
    between robust and clustered errors.
  - `se_hand` is @eq-se-hand.
  Set `taste_sd=0` and all four agree, because nothing ties a run's offers together.
]

#watch[
  Clustering by run handles offers within a run. It does not handle other ways offers could
  be related, such as one player's many runs, or a card being valued differently by
  different groups week after week. @ch-placebo finds that something like that is going on,
  and that the clustered errors are much too small.
]

#skill[
  *Matching the error bars to the data's structure.* Ask what makes observations related
  (people, sessions, places, time) and cluster at that level. Then check, as @ch-placebo
  does, whether that was enough.
]

#check(
  ([Explain to a friend why offers from one run shouldn't count as independent.],
   [They come from the same player, deck and run: if the run is going badly, or the player
    has a style, several offers are affected together, like a family answering a survey.]),
  ([In one sentence, what does clustering change in the calculation?],
   [It sums each run's residual contributions before squaring, so a run counts as one piece
    of evidence and offers that lean together widen the error bar.]),
  ([Why is the iid formula wrong for a zero-or-one outcome even when offers are
    independent?],
   [It assumes one noise level for every offer, but a zero-or-one outcome has variance
    $p(1 - p)$, which differs between cards with different pick rates.]),
  ([Why is clustering judged against robust SEs and not iid ones?],
   [The iid ratio mixes two things: unequal noise between cards and relatedness within runs.
    The robust SE already allows unequal noise, so the clustered-to-robust ratio isolates the
    effect of relatedness.]),
  ([A run that goes badly lowers the pick rate of every card in it. Why does that barely move
    the clustered SE of the DiD?],
   [Within the run it shifts the treated card's and the controls' residuals alike, and the
    treated-after column (after the fixed effects) has opposite signs for the two, so the
    shared shift largely cancels in the run's sum.]),
  ([Clustering widened the error bars by only a few percent. Does that prove the errors are
    honest?],
   [No. It shows that relatedness within a run matters little. Other sources of relatedness
    could make the errors too small, and the placebo test in @ch-placebo shows that they do.]),
  ([Clustered SEs were still too small in the placebo tests. What kind of correlation can't
    clustering by run see?],
   [Correlation across runs, such as a card's popularity drifting from week to week, which
    moves many runs together.]),
)

== What the fixed effects don't tell you

Each fixed effect gives a group its own baseline and then compares within groups. It answers
"is the effect still there after allowing for ascension?", not "does the effect differ by
ascension?". The model reports one effect, $beta$, averaged over everyone in the data. If
experienced players respond less and there are more of them in one patch than another, that
patch's average shrinks with nothing changing within any group. Telling those apart takes a
comparison within each group.

#words[
  - *Effect heterogeneity*: the patch's effect differs between groups (ascension levels,
    uploader groups, players).
  - *Interaction*: an input built as a product of two others, such as "treated and after"
    times "high ascension". Its coefficient is the difference between the groups' effects.
]

#picture[
  A school's average test score falls. Either every class did worse, or the school took in
  more students from a class that always scores lower. Only the class-by-class scores tell you
  which.
]

With two bands of players, low and high ascension, with effects $beta_"low"$ and
$beta_"high"$, and a share $w$ of the offers in the high band, the single effect a model
like @eq-model reports is close to the mix of the two:

$ beta_"avg" approx (1 - w) beta_"low" + w beta_"high" $ <eq-mix>

In words: the averaged effect is the low band's effect weighted by its share, plus the high
band's effect weighted by its share. It moves if either band's effect moves, or if $w$ moves.
(The model's weights are the ones of @eq-fwl rather than plain shares, so this is a
simplification; the point stands.) To measure the difference instead of averaging it away, add
an indicator $H_i$ for the high band and its product with $D_i$:

$ y_i = dots.c + beta D_i + lambda D_i H_i + epsilon_i $ <eq-interaction>

In words: the low band's effect is $beta$, the high band's is $beta + lambda$, so the interaction
coefficient $lambda$ is the difference between the bands' effects. (The dots stand for the fixed
effects of @eq-model, which would then also get a version per band.)

#project[
  *A simulation with known truth.* Two bands with true effects of
  #n("toy.heterogeneity.effect_low_pp") points (low ascension) and
  #n("toy.heterogeneity.effect_high_pp") (high), the same in both "patches"; between them only
  the high band's share changes, from #n("toy.heterogeneity.share_first") to
  #n("toy.heterogeneity.share_second").

  #align(center, ftable(
    columns: (auto, auto, auto),
    [*DiD, points*], [*First patch*], [*Second patch*],
    [All players], [#n("toy.heterogeneity.first.all_pp")], [#n("toy.heterogeneity.second.all_pp")],
    [Low band], [#n("toy.heterogeneity.first.low_pp")], [#n("toy.heterogeneity.second.low_pp")],
    [High band], [#n("toy.heterogeneity.first.high_pp")], [#n("toy.heterogeneity.second.high_pp")],
  ))

  The averaged effect drops though nothing changed within either band.

  *Your data.* Effects by ascension band were #unverified[not estimated]\; the banding itself
  is open (PLAN item 14), and the comparison is listed as an open question in @ch-open.
  The aggregate checks of @ch-explanations, on the earlier #n("const.earlier_tables.pages")-page
  tables, found both releases brought higher ascension in their first weeks, about equally.
]

#incode("teaching_sims.heterogeneity", [A mix shift moves an averaged effect, in a
  simulation.])[
  *What goes in:* the two bands' true effects and the high band's share in each patch. *What
  comes out:* the DiD for everyone and within each band, in each patch. The lines that
  matter: `eff = np.where(high, effect_high, effect_low)` gives each offer its band's effect,
  the same in both patches; `patch_fit(share)` changes only who is playing; and `did(mask)`
  is @eq-did-cells within a band, or over everyone. Comparing `did(~high)` and `did(high)`
  across the two patches is the within-band comparison the text asks for.
]

#mixup[
  You might read the ascension term in the model as a breakdown of the effect by ascension:
  surely, with ascension "in the model", the notebook could say how high-ascension players
  reacted. It can't. The term gives each level its own baseline pick rate so that comparisons
  happen within a level, and then reports one effect for everyone. Whether players at
  different levels reacted differently is a separate question, effect heterogeneity, and needs
  an interaction (@eq-interaction) or a fit per band.
]

#watch[
  A difference between ascension bands mixes who the players are with how the game plays at
  that level. Harder fights can change which cards are good, so "high-ascension players
  responded less" doesn't by itself mean they resist change. A comparison chosen after seeing
  the results also needs its bands declared before it is fitted, and every band reported.
]

#skill[
  *Separating "controlled for" from "studied".* Say for each term in a model whether it
  removes a difference or measures one.
]

#check(
  ([What does the ascension fixed effect do, and what doesn't it do?],
   [It gives each level its own baseline so comparisons happen within a level. It doesn't
    estimate whether the effect differs by level.]),
  ([An averaged effect shrinks between two patches. Name two explanations and the comparison
    that separates them.],
   [Players at every level responded less, or the mix shifted toward players who always
    respond less (@eq-mix). Compare the patches within each group: the first shows the drop
    in every band, the second in none.]),
  ([In @eq-interaction, what is the high band's effect, and what does $lambda$ measure?],
   [The high band's effect is $beta + lambda$; $lambda$ is the difference between the high and
    the low band's effects.]),
)

== Log-odds

#words[
  - *Odds*: picks divided by passes, $p slash (1 - p)$. A pick rate of one in four is odds of
    one to three.
  - *Log-odds (logit)*: the natural logarithm of the odds. It stretches the scale near zero
    and one.
  - *Delta method*: a standard way to convert an estimate and its SE from one scale to
    another, using the slope of the conversion at the starting point.
]

#picture[
  Betting odds. Moving a long shot from a hundred to one to fifty to one is a big change in
  how good the horse is thought to be, even though its chance of winning moved by only half a
  point. Log-odds measure changes the way a bookmaker would: a few points matter more for a
  card nobody picks than for a card everyone picks. Astronomers do the same with brightness:
  a star twice as bright is the same number of magnitudes brighter whether it is a bright star
  or a faint one.
]

For a pick rate $p$ the log-odds are

$ "logit"(p) = ln lr((p / (1 - p))) $ <eq-logit>

In words: the log-odds of a pick rate is the natural log of picks per pass. It runs from minus
infinity (never picked) to plus infinity (always picked) and is zero at a coin flip.

Effects in this guide are reported in percentage points, which are easy to say. The
dose-response chapter (@ch-dose) converts each effect to log-odds first, so that cards with
very different starting pick rates are on a common scale. The conversion uses the treated
card's pick rate before the patch, $p_0$, and the delta method. The slope of the logit is
$dif "logit"(p) slash dif p = 1 / p + 1 / (1 - p) = 1 / (p(1 - p))$, so a small change
$hat(beta)$ in probability becomes

$ hat(beta)_"lo" approx hat(beta) / (p_0 (1 - p_0)), quad
  "SE"_"lo" approx "SE" / (p_0 (1 - p_0)) $ <eq-delta>

In words: the effect in log-odds is the effect in probability divided by $p_0(1 - p_0)$, and
its SE is divided by the same number. Read backwards, it is the rule of thumb for what a
log-odds change $Delta$ means in points: about $Delta dot p_0(1 - p_0)$. The same push is
largest at a coin flip, where $p_0(1 - p_0)$ peaks, and small near zero or one.

#mathfull[
  The delta method is a first-order Taylor expansion. For a smooth function $f$ and an
  estimate $hat(theta)$ near its true value $theta$,
  $f(hat(theta)) approx f(theta) + f'(theta) (hat(theta) - theta)$, so
  $"Var"(f(hat(theta))) approx f'(theta)^2 "Var"(hat(theta))$ and
  $"SE"(f(hat(theta))) approx |f'(theta)| "SE"(hat(theta))$. Here $f$ is the logit, the
  change is the effect $hat(beta)$ added to $p_0$, and $f'(p_0) = 1 slash (p_0 (1 - p_0))$,
  which gives @eq-delta. It is good when $hat(beta)$ is small next to $p_0$ and $1 - p_0$. It
  is not the coefficient a logit regression would give: that model would fit the log-odds
  directly, with its own weighting of the offers.
]

#fig("fig_toy_log_odds", width: medium, [A worked example, not your data: the same log-odds push of
  #n("toy.log_odds_push.delta") measured in percentage points at every starting pick rate,
  exactly and by the rule of thumb.])

#mixup[
  You might expect each card's baseline to cancel in a before-and-after difference, so that
  the scale shouldn't matter. The baseline's _level_ does cancel: each card's effect is a
  change from its own before-rate, and the card fixed effects of @eq-model see to that. The
  _conversion_ doesn't: a change of a given size in log-odds is a different number of points
  at different baselines (@eq-delta). That is why points can't be compared across cards with
  different pick rates, and log-odds can.
]

#project[
  *A worked example, not your data.* A push of #n("toy.log_odds_push.delta") in log-odds is
  #n("toy.log_odds_push.p50.exact_pp") points for a card picked
  #n("toy.log_odds_push.p50.base") of the time, #n("toy.log_odds_push.p30.exact_pp") at
  #n("toy.log_odds_push.p30.base"), and only #n("toy.log_odds_push.p03.exact_pp") at
  #n("toy.log_odds_push.p03.base"). The rule of thumb gives
  #n("toy.log_odds_push.p50.approx_pp"), #n("toy.log_odds_push.p30.approx_pp") and
  #n("toy.log_odds_push.p03.approx_pp").

  *Your data.* Parry's weeks 0–3 effect is #n("tweak.parry.v0_103_2.h3.beta_pp_pm") points, or
  #n("tweak.parry.v0_103_2.h3.beta_lo_pm") in log-odds, starting from a pick rate of
  #n("tweak.parry.v0_103_2.treated_rate_before"): the points divided by
  $p_0(1 - p_0)$, as in @eq-delta.
]

#incode("did.to_log_odds", [The delta-method conversion used for every log-odds effect in
  this guide.])[
  *What goes in:* an effect and its SE in probability units, and the treated card's pick rate
  before. *What comes out:* both in log-odds. The line that matters is
  `k = p_before * (1 - p_before)`: dividing the effect and the SE by it is @eq-delta. A rate
  of exactly zero or one has no slope to divide by, so it returns blanks.
]

#watch[
  A log-odds effect can't be read as points without knowing the starting rate. Always say
  which scale an effect is on.
]

#skill[
  *Choosing a scale.* Use the scale on which effects are comparable for the question (log-odds
  across cards with different baselines) and report on the scale people understand (points).
]

#check(
  ([A card is picked one time in four. What are its odds?],
   [One pick for every three passes: odds of one to three.]),
  ([Why convert effects to log-odds before comparing cards with very different pick rates?],
   [A few points is a big change for a rarely picked card and a small one for a popular card.
    Log-odds put the changes on a common scale.]),
  ([Why can't you directly compare a move of a few points on a card picked rarely with the
    same move on a card picked half the time?],
   [On the rarely picked card the same points are a large share of its rate, a big shift in
    preference and a large log-odds change; on the half-time card they are a small one.
    @eq-delta divides by $p_0(1 - p_0)$, which is small near zero and largest at a half.]),
  ([What does the delta method do?],
   [It converts an estimate and its SE from one scale to another (here points to log-odds)
    using the slope of the conversion at the starting value.]),
  ([Does each card's baseline cancel in a log-odds effect?],
   [Its level does: each effect is a change from the card's own before-rate. The conversion
    doesn't: the same log-odds change is a different number of points at different
    baselines.]),
)
