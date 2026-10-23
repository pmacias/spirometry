"""The field guide's toy simulations: every toy from the reading notes (field guide v2 rework,
2026-10-22), as small seeded functions with known truth.

Each toy is a function that returns a dict of results (scalars and arrays). They are kept as
short as the notes' code because the guide shows them as listings. Nothing here reads run data:
every number is from a simulation, and the guide labels it so.

    python -m spirometry.teaching_sims --out data/analysis/writeup [--quick]

writes
    teaching_sims.csv           one row per number the guide may print: toy, quantity, value,
                                kind and decimals (how spirometry.numbers formats it), label.
                                spirometry.numbers turns each row into the key
                                toy.<toy>.<quantity>.
    toy_<toy>_<part>.csv        the data each toy's figure draws (scripts/writeup/figures.py).

--quick runs the toys with fewer draws (tests and the synthetic build); seeds are unchanged.

Toys, by the notes' section (§) and the chapter that uses them:
    bernoulli_spread   §1   ch 3   one offer's mean, variance, SD (RMS) and MAD
    sd_vs_se           §2   ch 4   the data's spread against the estimate's spread
    lln_clt            §3   ch 4   law of large numbers and central limit theorem
    small_samples      §4   ch 4   plug-in, Wilson and Bayesian intervals; posterior updating
    log_odds_push      §5   ch 6   one log-odds push in points at different baselines
    fixed_bias         §6   ch 4   a fixed bias becomes "significant" as n grows
    se_difference      §7   ch 4   a difference is limited by its smaller side
    buffs_nerfs        §8   ch 10  buffs and nerfs don't cancel in a slope
    type_shock         §9   ch 5   a shock to one card type leaks through mixed controls
    toy_power          §10  ch 12  a toy power curve
    false_alarms       §11  ch 8   understated error bars inflate the share flagged
    spillover          §13  ch 5   substitution: one card nerfed against many cards buffed
    four_ways          §14  ch 5   after-only, before/after and DiD on three 2x2 tables
    drift              §15  ch 5   skips and one card's discovery trend with no patch
    two_columns        §16  ch 6   the best line through two columns joins their averages
    did_regression     §16  ch 6   the interaction coefficient is the hand DiD
    composition        §18  ch 6   a shift in which controls are offered biases a pooled DiD
    se_layers          §18  ch 6   iid, robust and clustered SEs against the rerun wobble
    heterogeneity      §19  ch 6   a mix shift moves an averaged effect
"""
import argparse
import pathlib

import numpy as np
import pandas as pd
from scipy.special import expit, logit
from scipy.stats import beta, norm


# ------------------------------------------------------------------------- §1 one offer

def bernoulli_spread(ps=(0.5, 0.2, 0.05)):
    """One offer is 1 (picked) with probability p, else 0: its signed average distance from
    the mean, variance, SD (root of the mean square) and mean absolute deviation."""
    rows = []
    for p in ps:
        d_pick, d_skip = 1 - p, 0 - p                    # distances from the mean
        signed = p * d_pick + (1 - p) * d_skip           # always 0: the cancellation problem
        var = p * d_pick**2 + (1 - p) * d_skip**2        # square, then average
        sd = np.sqrt(var)                                # then root
        mad = p * abs(d_pick) + (1 - p) * abs(d_skip)    # plain distances, averaged
        rows.append(dict(p=p, signed=signed, var=var, p1mp=p * (1 - p), sd=sd, mad=mad))
    curve = np.linspace(0, 1, 401)
    return dict(table=pd.DataFrame(rows),
                curve=pd.DataFrame(dict(p=curve, sd=np.sqrt(curve * (1 - curve)))))


# ------------------------------------------------------------------------ §2 SD and SE

def sd_vs_se(p_true=0.2, n=1600, n_reruns=5000, seed=2):
    """One dataset (the SD world) against the estimate over imagined reruns (the SE world)."""
    rng = np.random.default_rng(seed)
    one_dataset = rng.random(n) < p_true                      # one real dataset
    reruns = rng.binomial(n, p_true, size=n_reruns) / n       # one estimate per rerun
    se = np.sqrt(p_true * (1 - p_true) / n)
    return dict(p_true=p_true, n=n, n_reruns=n_reruns, sd_data=one_dataset.std(),
                share_picked=one_dataset.mean(), se_formula=se, sd_reruns=reruns.std(),
                sqrt_n=np.sqrt(n), reruns=reruns)


# --------------------------------------------------------------------------- §3 LLN, CLT

def lln_clt(p=0.2, ns=(1, 2, 10, 100, 1600), n_reruns=10_000, n_long=5000, seed=0):
    """Picture B (CLT): many reruns at each fixed n. Picture A (LLN): one dataset growing."""
    rng = np.random.default_rng(seed)
    clt = {n: rng.binomial(n, p, size=n_reruns) / n for n in ns}   # one estimate per rerun
    offers = rng.random(n_long) < p                                # one long dataset
    running = np.cumsum(offers) / np.arange(1, n_long + 1)
    return dict(p=p, ns=ns, n_reruns=n_reruns, clt=clt, running=running,
                se={n: np.sqrt(p * (1 - p) / n) for n in ns})


# ------------------------------------------------------------------- §4 small samples

def plugin(k, n):
    ph = k / n
    se = np.sqrt(ph * (1 - ph) / n)
    return ph, ph - 1.96 * se, ph + 1.96 * se


def wilson(k, n, z=1.96):
    ph = k / n
    centre = (ph + z**2 / (2 * n)) / (1 + z**2 / n)
    half = z / (1 + z**2 / n) * np.sqrt(ph * (1 - ph) / n + z**2 / (4 * n**2))
    return centre, centre - half, centre + half


def bayes(k, n):
    post = beta(1 + k, 1 + n - k)                  # flat prior, k picks in n offers
    return post.mean(), post.ppf(0.025), post.ppf(0.975)


def small_samples(cases=((0, 1), (1, 1), (0, 3), (1, 5), (30, 600), (320, 1600)),
                  p_true=0.2, checkpoints=(0, 1, 2, 5, 20, 100, 1600), seed=1):
    """Three 95% intervals for small and large samples, and a flat prior updated offer by
    offer."""
    rows = []
    for k, n in cases:
        for name, f in (("plugin", plugin), ("wilson", wilson), ("bayes", bayes)):
            c, lo, hi = f(k, n)
            rows.append(dict(k=k, n=n, method=name, centre=c, lo=max(lo, 0), hi=min(hi, 1)))
    rng = np.random.default_rng(seed)
    offers = rng.random(max(checkpoints)) < p_true
    x = np.linspace(0, 1, 1001)
    post = []
    for n in checkpoints:
        k = int(offers[:n].sum())
        post.append(pd.DataFrame(dict(n=n, k=k, p=x, density=beta(1 + k, 1 + n - k).pdf(x))))
    return dict(table=pd.DataFrame(rows), posterior=pd.concat(post), p_true=p_true)


# ------------------------------------------------------------------------ §5 log-odds

def log_odds_push(delta=0.2, baselines=(0.03, 0.30, 0.50)):
    """The same log-odds push at every baseline, measured in probability: exact, and the
    rule of thumb delta * p(1 - p)."""
    def exact(p0):
        return expit(logit(p0) + delta) - p0
    p0 = np.linspace(0.01, 0.99, 300)
    curve = pd.DataFrame(dict(p0=p0, exact=exact(p0), approx=delta * p0 * (1 - p0)))
    points = pd.DataFrame(dict(p0=baselines, exact=[exact(b) for b in baselines],
                               approx=[delta * b * (1 - b) for b in baselines]))
    return dict(delta=delta, curve=curve, points=points)


# ----------------------------------------------------------------------- §6 fixed bias

def fixed_bias(p_true=0.30, bias=0.01, ns=(1_000, 10_000, 100_000, 1_000_000),
               n_reruns=3000, seed=0):
    """A pick-rate estimate that reads one point heavy, at growing n: precise and wrong."""
    rng = np.random.default_rng(seed)
    rows, est = [], {}
    for n in ns:
        e = rng.binomial(n, p_true + bias, size=n_reruns) / n
        se = np.sqrt(p_true * (1 - p_true) / n)
        covers = np.abs(e - p_true) < 1.96 * se          # 95% interval contains the truth
        rows.append(dict(n=n, se=se, bias_over_se=bias / se, mean=e.mean(),
                         share_covers=covers.mean()))
        est[n] = e
    return dict(p_true=p_true, bias=bias, table=pd.DataFrame(rows), estimates=est)


# ---------------------------------------------------------------- §7 SE of a difference

def se_difference(p=0.3, n_before=2_000, n_after=np.logspace(2, 6, 200)):
    """SE of an after-minus-before difference, the before block fixed: SEs add in
    quadrature, so the smaller side sets a floor."""
    se_b = np.sqrt(p * (1 - p) / n_before)
    se_a = np.sqrt(p * (1 - p) / n_after)
    se_diff = np.sqrt(se_b**2 + se_a**2)                 # quadrature
    at = lambda m: float(np.sqrt(se_b**2 + p * (1 - p) / m))
    return dict(p=p, n_before=n_before, se_before=se_b, se_diff_equal=at(n_before),
                se_diff_10x=at(10 * n_before), se_diff_100x=at(100 * n_before),
                curve=pd.DataFrame(dict(n_after=n_after, se_diff=se_diff)))


# ------------------------------------------------------------- §8 buffs and nerfs

def buffs_nerfs(true_slope=1.4, scatter=0.13, seed=4):
    """Five buffs and five nerfs on one line: the mean effect cancels, the slope doesn't."""
    rng = np.random.default_rng(seed)
    dose = np.r_[rng.uniform(0.05, 0.35, 5), -rng.uniform(0.05, 0.35, 5)]   # 5 buffs, 5 nerfs
    effect = true_slope * dose + rng.normal(0, scatter, dose.size)
    slope, intercept = np.polyfit(dose, effect, 1)
    return dict(true_slope=true_slope, scatter=scatter, mean_effect=effect.mean(),
                slope=slope, intercept=intercept, n_buffs=5, n_nerfs=5,
                points=pd.DataFrame(dict(dose=dose, effect=effect,
                                         change=["buff"] * 5 + ["nerf"] * 5)))


# ------------------------------------------------------------------ §9 a type-wide shock

def type_shock(n_ctrl_skill=6, n_ctrl_attack=14, true_nerf=-0.03, boss_hit_on_skills=-0.04,
               seed=9):
    """A skill is nerfed in the patch that adds a boss punishing every skill. Controls: some
    skills, more attacks."""
    rng = np.random.default_rng(seed)
    before_t = 0.35
    after_t = before_t + true_nerf + boss_hit_on_skills          # the treated card is a skill
    before_s = rng.uniform(0.2, 0.5, n_ctrl_skill)
    after_s = before_s + boss_hit_on_skills                      # the boss hits skills
    before_a = rng.uniform(0.2, 0.5, n_ctrl_attack)
    after_a = before_a + 0.0                                     # attacks untouched
    change_t = after_t - before_t
    all_ctrl = np.r_[after_s - before_s, after_a - before_a].mean()
    skill_ctrl = (after_s - before_s).mean()
    return dict(truth=true_nerf, boss_hit=boss_hit_on_skills, n_ctrl_skill=n_ctrl_skill,
                n_ctrl_attack=n_ctrl_attack, naive=change_t, did_mixed=change_t - all_ctrl,
                did_skill_only=change_t - skill_ctrl)


# ------------------------------------------------------------------------- §10 power

def slope_and_se(x, y):
    X = np.c_[np.ones_like(x), x]
    coef = np.linalg.lstsq(X, y, rcond=None)[0]
    resid = y - X @ coef
    s2 = resid @ resid / (len(x) - 2)
    cov = s2 * np.linalg.inv(X.T @ X)
    return coef[1], np.sqrt(cov[1, 1])


def toy_power(n_tweaks=17, n_sim=2000, total_scatter=0.41, first_patch_slope=1.40,
              fractions=(0.0, 0.2, 0.5, 1.0), seed=20261007):
    """Plant a slope, add scatter, refit, count |slope / SE| > 2; repeat."""
    rng = np.random.default_rng(seed)
    dose = rng.choice([-1, 1], n_tweaks) * rng.uniform(0.05, 0.4, n_tweaks)   # fixed doses
    rows, ses = [], []
    for f in fractions:
        s, hits = f * first_patch_slope, 0
        for _ in range(n_sim):
            y = s * dose + rng.normal(0, total_scatter, n_tweaks)
            b, se = slope_and_se(dose, y)
            ses.append(se)
            hits += abs(b / se) > 2
        rows.append(dict(fraction=f, planted=s, detected=hits / n_sim))
    return dict(n_tweaks=n_tweaks, n_sim=n_sim, total_scatter=total_scatter,
                first_patch_slope=first_patch_slope, typical_se=np.median(ses),
                table=pd.DataFrame(rows))


# --------------------------------------------------------------- §11 false alarms

def false_alarms(f=np.linspace(1, 5, 400)):
    """If the true scatter is f times the reported SE and the truth is zero, the share of
    |z_reported| > 2. Gaussian scatter assumed."""
    share = 2 * norm.sf(2 / f)
    return dict(honest=float(2 * norm.sf(2)), share_at_2=float(2 * norm.sf(1)),
                share_at_3=float(2 * norm.sf(2 / 3)),
                curve=pd.DataFrame(dict(f=f, share=share)))


def implied_factor(share):
    """The f for which honest-looking z's flag `share` of null fits (the inverse of
    false_alarms' curve)."""
    return 2 / norm.isf(share / 2)


# ------------------------------------------------------------------- §13 spillover

def simulate_screens(rng, appeal, n_screens):
    """Reward screens of 3 distinct cards plus a skip; logit choice on appeal."""
    K = appeal.size
    cards = np.argsort(rng.random((n_screens, K)), axis=1)[:, :3]    # 3 distinct cards
    u = np.c_[appeal[cards], np.zeros(n_screens)]                    # last column = skip
    prob = np.exp(u) / np.exp(u).sum(1, keepdims=True)
    choice = (rng.random((n_screens, 1)) > prob.cumsum(1)).sum(1)
    picked = np.stack([choice == j for j in range(3)], axis=1)
    return cards, picked


def pick_rate(cards, picked, ids, drop_screens_with=None):
    keep = np.isin(cards, ids)
    if drop_screens_with is not None:
        keep &= ~np.isin(cards, drop_screens_with).any(1, keepdims=True)
    return picked[keep].mean()


def spillover(K=21, n_screens=300_000, seed=5):
    """Scenario A nerfs card 0 alone; B buffs cards 0-7 at once. No other shocks, so card 0's
    own change is the truth and other characters' controls (change zero) recover it."""
    rng = np.random.default_rng(seed)
    appeal = rng.normal(-0.3, 0.6, K)                # log-odds appeal of each card vs skipping

    def scenario(changed, shift):
        after = appeal.copy()
        after[changed] += shift
        cb, pb = simulate_screens(rng, appeal, n_screens)
        ca, pa = simulate_screens(rng, after, n_screens)
        controls = np.setdiff1d(np.arange(K), changed)
        d_treated = pick_rate(ca, pa, [0]) - pick_rate(cb, pb, [0])
        d_ctrl = pick_rate(ca, pa, controls) - pick_rate(cb, pb, controls)
        d_ctrl_drop = (pick_rate(ca, pa, controls, drop_screens_with=[0])
                       - pick_rate(cb, pb, controls, drop_screens_with=[0]))
        return dict(truth=d_treated, ctrl_change=d_ctrl, did_same=d_treated - d_ctrl,
                    did_drop_screens=d_treated - d_ctrl_drop, did_other=d_treated - 0.0)

    return dict(K=K, n_screens=n_screens, n_buffed=8, nerf_shift=-1.0, buff_shift=0.5,
                a=scenario([0], -1.0), b=scenario(list(range(8)), +0.5))


# ------------------------------------------------------------------- §14 four ways

def four_ways(cases=(("parry_like", 15, 30, 30, 30), ("meta_shift", 15, 35, 30, 35),
                     ("popular", 40, 45, 30, 30), ("held_still", 50, 50, 30, 40))):
    """After-only, before/after and DiD on 2x2 tables of pick rates (in points)."""
    rows = []
    for label, t_before, t_after, c_before, c_after in cases:
        rows.append(dict(case=label, t_before=t_before, t_after=t_after, c_before=c_before,
                         c_after=c_after, after_only=t_after - c_after,
                         before_after=t_after - t_before,
                         did=(t_after - t_before) - (c_after - c_before)))
    return dict(table=pd.DataFrame(rows))


# ------------------------------------------------------------------------ §15 drift

def drift(K=21, weeks=10, screens_per_week=40_000, skip_drift=0.08, discovery=0.10,
          fake_patch_week=5, seed=15):
    """Weekly pick rates with a slowly rising skip rate and one card (card 0) being
    discovered. No patch at all; a DiD at fake_patch_week still reports an effect."""
    rng = np.random.default_rng(seed)
    appeal = rng.normal(-0.3, 0.6, K)
    rows = []
    for w in range(weeks):
        a = appeal.copy()
        a[0] += discovery * w
        cards = np.argsort(rng.random((screens_per_week, K)), axis=1)[:, :3]
        u = np.c_[a[cards], np.full(screens_per_week, skip_drift * w)]   # last = skip
        prob = np.exp(u) / np.exp(u).sum(1, keepdims=True)
        choice = (rng.random((screens_per_week, 1)) > prob.cumsum(1)).sum(1)
        picked = np.stack([choice == j for j in range(3)], 1)
        rows.append(dict(week=w, skip=np.mean(choice == 3), card0=picked[cards == 0].mean(),
                         controls=picked[cards != 0].mean()))
    t = pd.DataFrame(rows)
    before, after = t.week < fake_patch_week, t.week >= fake_patch_week
    did = ((t.card0[after] - t.card0[before].mean()).mean()
           - (t.controls[after] - t.controls[before].mean()).mean())
    return dict(weeks=t, did=did, fake_patch_week=fake_patch_week,
                skip_first=t.skip.iloc[0], skip_last=t.skip.iloc[-1])


# ---------------------------------------------------------- §16 regression on yes/no

def two_columns(n=200, true_gap=6.0, seed=16):
    """Heights of 7-year-olds (x = 0) and 8-year-olds (x = 1); the fitted line through the
    two columns."""
    rng = np.random.default_rng(seed)
    x = rng.integers(0, 2, n)                         # 0 = age 7, 1 = age 8
    height = 122 + true_gap * x + rng.normal(0, 5, n)  # cm
    slope, intercept = np.polyfit(x, height, 1)
    return dict(n=n, true_gap=true_gap, slope=slope, intercept=intercept,
                mean_diff=height[x == 1].mean() - height[x == 0].mean(),
                mean0=height[x == 0].mean(), mean1=height[x == 1].mean(),
                points=pd.DataFrame(dict(x=x, height=height)))


def did_regression(n=40_000, true_did=0.15, seed=161):
    """The 2x2 table as a regression with yes/no inputs and a yes/no outcome (picked)."""
    rng = np.random.default_rng(seed)
    treated = rng.integers(0, 2, n)                   # the treated card (1) or a control (0)
    after = rng.integers(0, 2, n)                     # after the patch (1) or before (0)
    p = 0.30 - 0.15 * treated + 0.02 * after + true_did * treated * after
    picked = (rng.random(n) < p).astype(float)
    X = np.c_[np.ones(n), treated, after, treated * after]
    a, b, c, d = np.linalg.lstsq(X, picked, rcond=None)[0]
    m = lambda t, s: picked[(treated == t) & (after == s)].mean()
    did_by_hand = (m(1, 1) - m(1, 0)) - (m(0, 1) - m(0, 0))
    return dict(n=n, true_did=true_did, a=a, b=b, c=c, d=d, did_by_hand=did_by_hand,
                cell00=m(0, 0), cell01=m(0, 1), cell10=m(1, 0), cell11=m(1, 1))


# --------------------------------------------------------- §18 composition, SE layers

def composition(n=60_000, true_effect=0.10, seed=3):
    """A popular control is offered more after the patch: the raw pooled DiD against a
    regression with one level per card (card fixed effects)."""
    rng = np.random.default_rng(seed)
    after = rng.integers(0, 2, n)
    base = np.array([0.2, 0.1, 0.3, 0.5])                 # card 0 treated; 1-3 controls
    mix_before = [0.25, 0.25, 0.25, 0.25]
    mix_after = [0.25, 0.15, 0.25, 0.35]                  # popular control 3 offered more
    card = np.where(after == 1, rng.choice(4, n, p=mix_after), rng.choice(4, n, p=mix_before))
    y = (rng.random(n) < base[card] + true_effect * ((card == 0) & (after == 1))).astype(float)
    t = card == 0
    raw = (y[t & (after == 1)].mean() - y[t & (after == 0)].mean()) \
        - (y[~t & (after == 1)].mean() - y[~t & (after == 0)].mean())
    X = np.c_[np.eye(4)[card], after, t & (after == 1)]   # one column per card
    fe = np.linalg.lstsq(X, y, rcond=None)[0][-1]
    return dict(n=n, true_effect=true_effect, raw=raw, fe=fe,
                share_popular_before=mix_before[3], share_popular_after=mix_after[3])


def simulate_runs(rng, n_runs=4000, per_run=10, taste_sd=0.25):
    """Offers in runs; each run's player has their own taste for the treated card."""
    run = np.repeat(np.arange(n_runs), per_run)
    after = np.repeat(rng.integers(0, 2, n_runs), per_run)       # a run is before or after
    treated = rng.integers(0, 2, run.size)                        # treated card or not
    taste = np.repeat(rng.normal(0, taste_sd, n_runs), per_run)  # this player's taste
    p = np.clip(0.30 - 0.15 * treated + 0.02 * after + 0.10 * treated * after
                + treated * taste, 0.01, 0.99)
    y = (rng.random(run.size) < p).astype(float)
    return run, treated, after, y


def fit_layers(run, treated, after, y):
    """The 2x2 regression with four standard errors for the interaction: iid, HC1
    (sandwich), clustered by run, and the hand rule (cells added in quadrature)."""
    X = np.c_[np.ones(y.size), treated, after, treated * after]
    n, k = X.shape
    bread = np.linalg.inv(X.T @ X)
    b = bread @ X.T @ y
    e = y - X @ b                                                 # residuals
    V_iid = (e @ e / (n - k)) * bread
    V_hc1 = bread @ (X.T * e**2) @ X @ bread * n / (n - k)
    G = run.max() + 1
    S = np.zeros((G, k))
    np.add.at(S, run, X * e[:, None])                             # sum within each run
    V_cl = bread @ (S.T @ S) @ bread * G / (G - 1) * (n - 1) / (n - k)
    cell = lambda tt, aa: y[(treated == tt) & (after == aa)]
    se_hand = np.sqrt(sum(c.var(ddof=1) / c.size
                          for c in (cell(tt, aa) for tt in (0, 1) for aa in (0, 1))))
    did = (cell(1, 1).mean() - cell(1, 0).mean()) - (cell(0, 1).mean() - cell(0, 0).mean())
    se = dict(hand=se_hand, iid=np.sqrt(V_iid[3, 3]), hc1=np.sqrt(V_hc1[3, 3]),
              clustered=np.sqrt(V_cl[3, 3]))
    return b[3], did, se


def se_layers(n_reruns=300, taste_sd=0.25, n_runs=4000, per_run=10, seed=18):
    """Four SEs from one dataset against the true wobble of the interaction over reruns."""
    rng = np.random.default_rng(seed)
    d, did, se = fit_layers(*simulate_runs(rng, n_runs, per_run, taste_sd))
    reruns = [fit_layers(*simulate_runs(rng, n_runs, per_run, taste_sd))[0]
              for _ in range(n_reruns)]
    return dict(d=d, did_by_hand=did, se=se, true_wobble=np.std(reruns), n_reruns=n_reruns,
                n_runs=n_runs, per_run=per_run, taste_sd=taste_sd)


# ------------------------------------------------------------------ §19 heterogeneity

def heterogeneity(effect_low=0.08, effect_high=0.02, share_high=(0.30, 0.60), n=600_000,
                  seed=19):
    """Two ascension bands with different effects, the same in both patches; between the
    patches only the share of high-band players changes."""
    rng = np.random.default_rng(seed)

    def patch_fit(share):
        high = rng.random(n) < share
        treated, after = rng.integers(0, 2, n), rng.integers(0, 2, n)
        eff = np.where(high, effect_high, effect_low)
        y = (rng.random(n) < 0.30 - 0.10 * treated + 0.02 * after + eff * treated * after)

        def did(mask):
            m = lambda t, a: y[mask & (treated == t) & (after == a)].mean()
            return (m(1, 1) - m(1, 0)) - (m(0, 1) - m(0, 0))
        return dict(all=did(np.ones(n, bool)), low=did(~high), high=did(high))

    first, second = (patch_fit(s) for s in share_high)
    return dict(effect_low=effect_low, effect_high=effect_high, share_first=share_high[0],
                share_second=share_high[1], first=first, second=second)


# ------------------------------------------------------------------------ the tables

QUICK = dict(sd_vs_se=dict(n_reruns=1000), lln_clt=dict(n_reruns=2000),
             fixed_bias=dict(n_reruns=500), toy_power=dict(n_sim=200),
             spillover=dict(n_screens=30_000), drift=dict(screens_per_week=8_000),
             se_layers=dict(n_reruns=40), heterogeneity=dict(n=100_000),
             composition=dict(n=20_000))


def _p(x):
    """A probability as a key suffix: 0.05 -> 'p05', 0.5 -> 'p50'."""
    return f"p{round(100 * x):02d}"


def _rows(name, r):
    """[(quantity, value, kind, decimals, label)] for one toy's result. Kinds (formatted by
    spirometry.numbers): count, number, signed, pp (probability x 100, signed), ppu
    (probability x 100, unsigned), pct (share as a percentage)."""
    R = []
    add = lambda q, v, kind, d, label: R.append((q, float(v), kind, d, label))
    if name == "bernoulli_spread":
        for t in r["table"].itertuples():
            k = _p(t.p)
            add(f"{k}.p", t.p, "number", 2, "pick probability")
            for c, d in (("signed", 2), ("var", 4), ("p1mp", 4), ("sd", 3), ("mad", 3)):
                add(f"{k}.{c}", getattr(t, c), "number", d, c)
    elif name == "sd_vs_se":
        for q in ("p_true", "sd_data", "se_formula", "sd_reruns"):
            add(q, r[q], "number", 3 if q != "p_true" else 1, q)
        add("share_picked", r["share_picked"], "pct", 1, "share picked in the one dataset")
        add("n", r["n"], "count", 0, "offers per dataset")
        add("n_reruns", r["n_reruns"], "count", 0, "imagined reruns")
        add("sqrt_n", r["sqrt_n"], "number", 0, "square root of n")
    elif name == "lln_clt":
        add("p", r["p"], "number", 1, "true pick rate")
        add("n_reruns", r["n_reruns"], "count", 0, "reruns per n")
        for n in r["ns"]:
            add(f"n{n}.n", n, "count", 0, "offers per rerun")
            add(f"n{n}.se", r["se"][n], "number", 3, "SE formula")
            add(f"n{n}.sd_estimates", r["clt"][n].std(), "number", 3, "sd over reruns")
    elif name == "small_samples":
        for t in r["table"].itertuples():
            k = f"k{t.k}_n{t.n}.{t.method}"
            if t.method == "plugin":
                add(f"k{t.k}_n{t.n}.k", t.k, "count", 0, "picks")
                add(f"k{t.k}_n{t.n}.n", t.n, "count", 0, "offers")
            for c in ("centre", "lo", "hi"):
                add(f"{k}.{c}", getattr(t, c), "number", 3, f"{t.method} {c}")
        add("p_true", r["p_true"], "number", 1, "true pick rate (updating)")
    elif name == "log_odds_push":
        add("delta", r["delta"], "number", 1, "log-odds push")
        for t in r["points"].itertuples():
            k = _p(t.p0)
            add(f"{k}.base", t.p0, "pct", 0, "baseline pick rate")
            add(f"{k}.exact_pp", t.exact, "pp", 1, "exact change, points")
            add(f"{k}.approx_pp", t.approx, "pp", 1, "delta p(1 - p), points")
    elif name == "fixed_bias":
        add("p_true", r["p_true"], "pct", 0, "true pick rate")
        add("bias_pp", r["bias"], "ppu", 0, "bias, points")
        for t in r["table"].itertuples():
            k = f"n{int(t.n)}"
            add(f"{k}.n", t.n, "count", 0, "offers")
            add(f"{k}.se_pp", t.se, "ppu", 2, "SE, points")
            add(f"{k}.bias_over_se", t.bias_over_se, "number", 1, "bias / SE")
            add(f"{k}.share_covers", t.share_covers, "pct", 0, "95% intervals covering truth")
    elif name == "se_difference":
        add("p", r["p"], "number", 1, "pick rate")
        add("n_before", r["n_before"], "count", 0, "before-block offers")
        for q in ("se_before", "se_diff_equal", "se_diff_10x", "se_diff_100x"):
            add(f"{q}_pp", r[q], "ppu", 2, q + ", points")
    elif name == "buffs_nerfs":
        for q, kind, d in (("true_slope", "number", 1), ("scatter", "number", 2),
                           ("mean_effect", "signed", 3), ("slope", "number", 2),
                           ("n_buffs", "count", 0), ("n_nerfs", "count", 0)):
            add(q, r[q], kind, d, q)
    elif name == "type_shock":
        for q in ("truth", "boss_hit", "naive", "did_mixed", "did_skill_only"):
            add(f"{q}_pp", r[q], "pp", 1, q + ", points")
        add("n_ctrl_skill", r["n_ctrl_skill"], "count", 0, "skill controls")
        add("n_ctrl_attack", r["n_ctrl_attack"], "count", 0, "attack controls")
    elif name == "toy_power":
        add("n_tweaks", r["n_tweaks"], "count", 0, "tweaks")
        add("n_sim", r["n_sim"], "count", 0, "simulations per planted slope")
        add("typical_se", r["typical_se"], "number", 2, "median slope SE")
        add("first_patch_slope", r["first_patch_slope"], "number", 2, "first-patch-sized slope")
        for t in r["table"].itertuples():
            k = f"f{round(100 * t.fraction):03d}"
            add(f"{k}.planted", t.planted, "number", 2, "planted slope")
            add(f"{k}.detected", t.detected, "pct", 0, "share detected")
    elif name == "false_alarms":
        add("honest", r["honest"], "pct", 1, "flagged with honest SEs")
        add("share_at_2", r["share_at_2"], "pct", 0, "flagged when f = 2")
        add("share_at_3", r["share_at_3"], "pct", 0, "flagged when f = 3")
    elif name == "spillover":
        add("k", r["K"], "count", 0, "cards of the character")
        add("n_screens", r["n_screens"], "count", 0, "screens per block")
        add("n_buffed", r["n_buffed"], "count", 0, "cards buffed in scenario B")
        for s in ("a", "b"):
            for q, v in r[s].items():
                add(f"{s}.{q}_pp", v, "pp", 2, f"scenario {s.upper()}: {q}, points")
    elif name == "four_ways":
        for t in r["table"].itertuples():
            for c in ("t_before", "t_after", "c_before", "c_after", "after_only",
                      "before_after", "did"):
                add(f"{t.case}.{c}", getattr(t, c), "count" if c.startswith(("t_", "c_"))
                    else "signed", 0, c)
    elif name == "drift":
        add("did_pp", r["did"], "pp", 1, "DiD at the fake patch date, points")
        add("fake_patch_week", r["fake_patch_week"], "count", 0, "fake patch week")
        add("skip_first", r["skip_first"], "pct", 0, "skip rate, first week")
        add("skip_last", r["skip_last"], "pct", 0, "skip rate, last week")
    elif name == "two_columns":
        for q, d in (("slope", 2), ("intercept", 2), ("mean_diff", 2), ("mean0", 2),
                     ("mean1", 2), ("true_gap", 0)):
            add(q, r[q], "number", d, q + " (cm)")
        add("n", r["n"], "count", 0, "children")
    elif name == "did_regression":
        for q in ("a", "b", "c"):
            add(q, r[q], "signed", 3, q)
        for q in ("d", "did_by_hand"):
            add(q, r[q], "signed", 4, q)
        for q in ("cell00", "cell01", "cell10", "cell11"):
            add(q, r[q], "number", 3, q)
        add("true_did", r["true_did"], "signed", 2, "true DiD")
        add("n", r["n"], "count", 0, "offers")
    elif name == "composition":
        for q in ("true_effect", "raw", "fe"):
            add(q, r[q], "signed", 3, q)
        add("share_popular_before", r["share_popular_before"], "pct", 0, "popular control's share before")
        add("share_popular_after", r["share_popular_after"], "pct", 0, "popular control's share after")
    elif name == "se_layers":
        for q, v in r["se"].items():
            add(f"se_{q}", v, "number", 4, f"SE: {q}")
        add("true_wobble", r["true_wobble"], "number", 4, "sd of d over reruns")
        add("ratio_clustered", r["se"]["clustered"] / r["true_wobble"], "number", 2,
            "clustered SE / true wobble")
        add("ratio_iid", r["se"]["iid"] / r["true_wobble"], "number", 2, "iid SE / true wobble")
        add("d", r["d"], "signed", 4, "interaction")
        add("did_by_hand", r["did_by_hand"], "signed", 4, "hand DiD")
        for q in ("n_reruns", "n_runs", "per_run"):
            add(q, r[q], "count", 0, q)
        add("taste_sd", r["taste_sd"], "number", 2, "sd of the taste")
    elif name == "heterogeneity":
        add("effect_low_pp", r["effect_low"], "pp", 0, "true effect, low band")
        add("effect_high_pp", r["effect_high"], "pp", 0, "true effect, high band")
        add("share_first", r["share_first"], "pct", 0, "high-band share, first patch")
        add("share_second", r["share_second"], "pct", 0, "high-band share, second patch")
        for patch in ("first", "second"):
            for band, v in r[patch].items():
                add(f"{patch}.{band}_pp", v, "pp", 1, f"{patch} patch, {band}")
    return R


def _data(name, r):
    """{part: DataFrame} that the toy's figure draws."""
    if name == "bernoulli_spread":
        return dict(curve=r["curve"])
    if name == "sd_vs_se":
        return dict(reruns=pd.DataFrame(dict(estimate=r["reruns"])))
    if name == "lln_clt":
        clt = pd.concat([pd.DataFrame(dict(n=n, estimate=e)) for n, e in r["clt"].items()])
        k = np.arange(1, r["running"].size + 1)
        return dict(clt=clt, running=pd.DataFrame(dict(offers=k, estimate=r["running"])))
    if name == "small_samples":
        return dict(posterior=r["posterior"], intervals=r["table"])
    if name == "log_odds_push":
        return dict(curve=r["curve"], points=r["points"])
    if name == "fixed_bias":
        return dict(estimates=pd.concat([pd.DataFrame(dict(n=n, estimate=e))
                                         for n, e in r["estimates"].items()]))
    if name == "se_difference":
        return dict(curve=r["curve"])
    if name == "buffs_nerfs":
        return dict(points=r["points"])
    if name == "toy_power":
        return dict(curve=r["table"])
    if name == "false_alarms":
        return dict(curve=r["curve"])
    if name == "spillover":
        return dict(estimates=pd.DataFrame([dict(scenario=s, **r[s]) for s in ("a", "b")]))
    if name == "four_ways":
        return dict(table=r["table"])
    if name == "drift":
        return dict(weeks=r["weeks"])
    if name == "two_columns":
        return dict(points=r["points"])
    if name == "se_layers":
        return dict(se=pd.DataFrame(dict(estimator=list(r["se"]), se=list(r["se"].values()),
                                         true_wobble=r["true_wobble"])))
    if name == "heterogeneity":
        return dict(table=pd.DataFrame([dict(patch=p, band=b, effect=v)
                                        for p in ("first", "second")
                                        for b, v in r[p].items()]))
    return {}


TOYS = {f.__name__: f for f in [
    bernoulli_spread, sd_vs_se, lln_clt, small_samples, log_odds_push, fixed_bias,
    se_difference, buffs_nerfs, type_shock, toy_power, false_alarms, spillover, four_ways,
    drift, two_columns, did_regression, composition, se_layers, heterogeneity]}


def run(out=None, quick=False, only=None):
    """Every toy (or those in `only`). Returns (summary DataFrame, {toy: result}); with
    `out`, writes teaching_sims.csv and the figures' toy_<toy>_<part>.csv there."""
    results, rows = {}, []
    for name, f in TOYS.items():
        if only and name not in only:
            continue
        r = f(**(QUICK.get(name, {}) if quick else {}))
        results[name] = r
        rows += [dict(toy=name, quantity=q, value=v, kind=k, decimals=d, label=lab)
                 for q, v, k, d, lab in _rows(name, r)]
    summary = pd.DataFrame(rows, columns=["toy", "quantity", "value", "kind", "decimals",
                                          "label"])
    if out:
        o = pathlib.Path(out)
        o.mkdir(parents=True, exist_ok=True)
        summary.to_csv(o / "teaching_sims.csv", index=False)
        for name, r in results.items():
            for part, d in _data(name, r).items():
                d.to_csv(o / f"toy_{name}_{part}.csv", index=False)
    return summary, results


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--out", default="data/analysis/writeup")
    p.add_argument("--quick", action="store_true", help="fewer draws (tests)")
    p.add_argument("--only", nargs="*", choices=list(TOYS))
    a = p.parse_args(argv)
    summary, _ = run(a.out, a.quick, a.only)
    print(f"{len(summary)} numbers from {summary.toy.nunique()} toys -> "
          f"{a.out}/teaching_sims.csv")


if __name__ == "__main__":
    main()
