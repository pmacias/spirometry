"""Field guide v2 figures: every figure in writeup/OUTLINE.md that the saved outputs supply,
one function per figure, drawn with matplotlib into writeup/figures/<name>.png.

    python scripts/writeup/figures.py [--analysis data/analysis] [--results results]
        [--ref reference] [--triage triage] [--out writeup/figures] [--only fig_dose ...]

Run it after scripts/writeup/phil_runs.sh (the build refuses a figure older than the run
tables). Inputs are aggregates only (the export's tables, spirometry.sensitivity's and
iv_sim's tables, notebook 01's audit summaries, the placebo fits' z and the triage's
card-level CSVs); nothing here opens the run database. A figure whose input is missing is
skipped and listed at the end; the build then prints its placeholder.

Colors are the dashboard's (dashboard/charts.py, Okabe-Ito): blue / vermillion for buff /
nerf, dark goldenrod / purple for the first / second patch, always with a marker shape
(circle / square) so color is never the only cue; black / grey for treated / controls.

Not drawn: fig_power_check (task 9, future work).
"""
import argparse
import json
import pathlib
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

BUFF, NERF, NO_DIRECTION = "#0072B2", "#D55E00", "#767676"
PATCH_COLOR = {"first": "#B8860B", "second": "#6A3D9A"}
PATCH_MARKER = {"first": "o", "second": "s"}
TREATED, CONTROLS = "#000000", "#999999"
STABLE, BETA = "#0072B2", "#D55E00"
INK, MUTED, GRID = "#222222", "#666666", "#cccccc"
PATCH_LABEL = {"first": "first patch (v0.103.2)", "second": "second patch (v0.107.1)"}
DPI = 200

plt.rcParams.update({
    "figure.dpi": DPI, "savefig.dpi": DPI, "figure.facecolor": "white",
    "axes.facecolor": "white", "axes.edgecolor": MUTED, "axes.labelcolor": INK,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.5, "grid.alpha": 0.7,
    "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK,
    "font.size": 9, "axes.titlesize": 10, "legend.frameon": False,
    "lines.linewidth": 2, "lines.markersize": 5,
})


class Missing(Exception):
    pass


def card_name(card_id):
    """'SIC_EM' -> 'Sic Em'."""
    return str(card_id).replace("_", " ").title()


def tweak_label(row):
    return f"{card_name(row.card_id)} ({row.stable_build})"


class Inputs:
    """Lazy readers for every input; a missing file raises Missing(path)."""

    def __init__(self, analysis, results, ref, triage):
        self.an, self.res, self.ref, self.triage = (pathlib.Path(p) for p in
                                                    (analysis, results, ref, triage))

    def _path(self, p):
        if not p.exists():
            raise Missing(str(p))
        return p

    def csv(self, where, name, **kw):
        base = {"an": self.an, "w": self.an / "writeup", "res": self.res, "ref": self.ref}[where]
        return pd.read_csv(self._path(base / name), **kw)

    def parquet(self, name, columns):
        return pd.read_parquet(self._path(self.an / name), columns=columns)

    def triage_csv(self, name):
        """A triage output from out_final/ (current tables) or out/ (1,873 pages), with the
        tables' label for the caption."""
        for sub, label in [("out_final", self.pages_label()), ("out", "1,873-page tables")]:
            p = self.triage / sub / name
            if p.exists():
                return pd.read_csv(p), label
        raise Missing(str(self.triage / "out_final" / name))

    def pages_label(self):
        m = json.loads(self._path(self.res / "meta.json").read_text())
        return f"{int(m['snapshot_pages']):,}-page tables"

    def pick_rate(self):
        return self.csv("res", "pick_rate_did.csv")


def save(fig, out, name):
    fig.tight_layout()
    fig.savefig(out / f"{name}.png", bbox_inches="tight")   # keeps outside legends
    plt.close(fig)


def zero_line(ax, axis="y"):
    (ax.axhline if axis == "y" else ax.axvline)(0, color=MUTED, lw=1, zorder=1)


def patch_legend(ax, **kw):
    handles = [plt.Line2D([], [], ls="", marker=PATCH_MARKER[p], color=PATCH_COLOR[p],
                          markersize=6, label=PATCH_LABEL[p]) for p in PATCH_COLOR]
    ax.legend(handles=handles, **kw)


def one(p, card_id, stable_build=None):
    d = p[p.card_id == card_id]
    if stable_build:
        d = d[d.stable_build == stable_build]
    if d.empty:
        raise Missing(f"{card_id} not in pick_rate_did.csv")
    return d.iloc[0]


def example_cards(p):
    """Parry and Corrosive Wave on the real tables; in another set of outputs (the synthetic
    test), the largest buff and the largest nerf of the first patch."""
    names = ["PARRY", "CORROSIVE_WAVE"]
    if all((p.card_id == c).any() for c in names):
        return [one(p, c) for c in names]
    first = p[(p.patch == "first") & (p.upgrade_only != "yes")].sort_values("beta")
    return [first.iloc[-1], first.iloc[0]]


# ------------------------------------------------------------------------------ ch 0-1

def fig_timeline(I, out):
    """Builds on a calendar by branch, with the two stable patches' windows."""
    b = I.csv("ref", "builds.csv", dtype=str, keep_default_na=False)
    b = b[(b.release_date != "") & ~b.build_id.str.endswith("-beta")].copy()
    b["date"] = pd.to_datetime(b.release_date)
    p = I.pick_rate()
    fig, ax = plt.subplots(figsize=(7, 2.6))
    for br, y, c, m in [("stable", 1, STABLE, "o"), ("beta", 0, BETA, "s")]:
        d = b[b.branch == br]
        ax.scatter(d.date, [y] * len(d), color=c, marker=m, s=28, zorder=3, label=br)
    for i, (pt, g) in enumerate(p.groupby("patch")):
        before, after = g.window.iloc[0].split(" -> ")
        dates = b.set_index("build_id").date
        start = dates.get(before.split()[0])
        stable = dates.get(g.stable_build.iloc[0])
        if pd.notna(start) and pd.notna(stable):
            ax.axvspan(start, stable, ymin=0.62, ymax=0.9, color=PATCH_COLOR[pt], alpha=0.15,
                       lw=0)
            ax.text(start, 1.35, f"{pt} window: {before} -> {after}", fontsize=7,
                    color=INK, va="bottom")
            ax.axvline(stable, color=PATCH_COLOR[pt], lw=1.5, ls="--")
    for r in b[b.branch == "stable"].itertuples():
        ax.annotate(r.build_id, (r.date, 1), xytext=(0, -12), textcoords="offset points",
                    rotation=60, ha="right", fontsize=6, color=MUTED)
    ax.set(yticks=[0, 1], yticklabels=["beta", "stable"], ylim=(-0.6, 1.8))
    ax.grid(axis="y", visible=False)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.set_title("Builds by release date, stable and beta, with the two patch windows")
    save(fig, out, "fig_timeline")


def fig_runs_per_build(I, out):
    """Primary and all distinct runs per build, by branch (notebook 01's aggregates)."""
    d = I.csv("an", "audit_runs_per_build.csv")
    x = np.arange(len(d))
    color = np.where(d.branch == "beta", BETA, STABLE)
    fig, ax = plt.subplots(figsize=(7, 3.2))
    ax.bar(x, d.runs, color=color, alpha=0.3, width=0.8, label="distinct runs")
    ax.bar(x, d.primary, color=color, width=0.8, label="primary runs")
    if "thin" in d:
        for i in np.flatnonzero(d.thin.astype(str).str.lower() == "true"):
            ax.annotate("thin", (x[i], d.primary.iloc[i]), xytext=(0, 3),
                        textcoords="offset points", ha="center", fontsize=6, color=INK)
    ax.set_yscale("log")
    ax.set_xticks(x, d.build_id, rotation=60, ha="right", fontsize=6)
    ax.set(ylabel="runs (log scale)", title="Runs per build: light = distinct, solid = primary")
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=STABLE, label="stable"),
                       plt.Rectangle((0, 0), 1, 1, color=BETA, label="beta")], ncol=2,
              loc="upper left")
    ax.grid(axis="x", visible=False)
    save(fig, out, "fig_runs_per_build")


def fig_upload_lag(I, out):
    """Share of primary runs uploaded more than d days after being played, by group."""
    d = I.csv("an", "audit_upload_lag.csv")
    fig, ax = plt.subplots(figsize=(6, 3.2))
    for col, c, ls, lab in [("share_all", INK, "-", "all primary runs"),
                            ("share_tagged", BUFF, "--", "tagged (SlayTheStats)"),
                            ("share_untagged", NERF, ":", "untagged")]:
        ax.plot(d.days, 100 * d[col], color=c, ls=ls, label=lab)
    ax.set(xlabel="days between playing and uploading (d)",
           ylabel="% uploaded later than d days", ylim=(0, 100),
           title="Backfill: how late runs are uploaded")
    ax.legend()
    save(fig, out, "fig_upload_lag")


# -------------------------------------------------------------------------------- ch 2

def fig_confounding_dag(I, out):
    """Skill points to picking and to winning; picking points to winning. Drawn, no data."""
    fig, ax = plt.subplots(figsize=(5, 2.6))
    ax.set_axis_off()
    nodes = {"skill": (0.5, 0.85), "picks the card": (0.12, 0.2), "wins the run": (0.88, 0.2)}
    for name, (x, y) in nodes.items():
        ax.text(x, y, name, ha="center", va="center", fontsize=10,
                bbox=dict(boxstyle="round,pad=0.4", fc="white", ec=INK, lw=1))
    arrows = [((0.44, 0.76), (0.18, 0.3), MUTED), ((0.56, 0.76), (0.82, 0.3), MUTED),
              ((0.28, 0.2), (0.72, 0.2), BUFF)]                 # (from, to, color)
    for start, end, c in arrows:
        ax.annotate("", xy=end, xytext=start, arrowprops=dict(arrowstyle="-|>", color=c, lw=2))
    ax.text(0.5, 0.12, "the effect we want", ha="center", fontsize=8, color=BUFF)
    ax.text(0.5, 0.55, "confounder: drives both", ha="center", fontsize=8, color=MUTED)
    ax.set(xlim=(0, 1), ylim=(0, 1))
    save(fig, out, "fig_confounding_dag")


# ------------------------------------------------------------------------------ ch 3-6

def fig_before_after(I, out):
    """Two tweaks' pick rates before and after, with their controls (all weeks)."""
    p = I.pick_rate()
    cards = example_cards(p)
    fig, axes = plt.subplots(1, 2, figsize=(7, 3), sharey=True)
    for ax, r in zip(axes, cards):
        for who, b, a, c, m in [("treated card", r.treated_rate_before, r.treated_rate_after,
                                 TREATED, "o"),
                                ("controls", r.control_rate_before, r.control_rate_after,
                                 CONTROLS, "s")]:
            ax.plot([0, 1], [100 * b, 100 * a], color=c, marker=m, markersize=6, label=who)
            ax.annotate(f"{100 * a:.1f}%", (1, 100 * a), xytext=(6, 0),
                        textcoords="offset points", va="center", fontsize=7, color=INK)
            ax.annotate(f"{100 * b:.1f}%", (0, 100 * b), xytext=(-6, 0),
                        textcoords="offset points", va="center", ha="right", fontsize=7,
                        color=INK)
        ax.set(xticks=[0, 1], xticklabels=["before", "after"], xlim=(-0.4, 1.4),
               title=tweak_label(r))
    axes[0].set_ylabel("pick rate (%)")
    axes[0].legend(loc="upper left")
    save(fig, out, "fig_before_after")


def fig_se_curve(I, out):
    """SE of a pick rate against offers (the square-root rule), one tweak marked."""
    p = I.pick_rate()
    r = example_cards(p)[0]
    rate = r.treated_rate_before
    n = np.logspace(2, 6, 200)
    fig, ax = plt.subplots(figsize=(6, 3.2))
    ax.plot(n, 100 * np.sqrt(rate * (1 - rate) / n), color=INK,
            label=f"pick rate {100 * rate:.0f}%: SE = sqrt(p(1 - p) / n)")
    nr = r.n_treated_offers
    ax.plot([nr], [100 * np.sqrt(rate * (1 - rate) / nr)], marker="o", markersize=8,
            color=BUFF, ls="", label=f"{card_name(r.card_id)}'s offers after the patch")
    ax.set(xscale="log", yscale="log", xlabel="offers (n)", ylabel="standard error (points)",
           title="Ten times the offers, about a third of the noise")
    ax.legend()
    save(fig, out, "fig_se_curve")


def fig_parry_did(I, out):
    """One tweak and its controls before and after, with the counterfactual dashed."""
    r = example_cards(I.pick_rate())[0]
    tb, ta, cb, ca = (100 * r.treated_rate_before, 100 * r.treated_rate_after,
                      100 * r.control_rate_before, 100 * r.control_rate_after)
    fig, ax = plt.subplots(figsize=(5.5, 3.4))
    ax.plot([0, 1], [cb, ca], color=CONTROLS, marker="s", markersize=6, label="controls")
    ax.plot([0, 1], [tb, ta], color=TREATED, marker="o", markersize=6, label="treated card")
    ax.plot([0, 1], [tb, tb + (ca - cb)], color=TREATED, ls="--", lw=1.5,
            label="treated card if it had moved like the controls")
    ax.annotate("", xy=(1.05, ta), xytext=(1.05, tb + ca - cb),
                arrowprops=dict(arrowstyle="<->", color=BUFF, lw=1.5))
    ax.text(1.09, (ta + tb + ca - cb) / 2, f"DiD\n{(ta - tb) - (ca - cb):+.1f} pts",
            color=INK, fontsize=8, va="center")
    ax.set(xticks=[0, 1], xticklabels=["before", "after"], xlim=(-0.2, 1.45),
           ylabel="pick rate (%)", title=f"Difference-in-differences: {tweak_label(r)}")
    ax.legend(loc="upper left", fontsize=7)
    save(fig, out, "fig_parry_did")


def _weekly_panel(ax, w, title):
    for blk, c, m in [("before", CONTROLS, "s"), ("after", BUFF, "o")]:
        d = w[w.block == blk].sort_values("week")
        ax.errorbar(d.week, 100 * d.coef, yerr=196 * d.se, color=c, marker=m, ls="-",
                    lw=1.5, capsize=0, label=f"{blk} block")
    zero_line(ax)
    ax.axvline(-0.5, color=MUTED, ls="--", lw=1)
    ax.set(xlabel="weeks from the new stable build's release", ylabel="gap to controls (pts)",
           title=title)


def fig_parry_weekly(I, out):
    """One tweak's weekly gap to its controls (the event study)."""
    p, w = I.pick_rate(), I.csv("res", "weekly.csv")
    r = example_cards(p)[0]
    fig, ax = plt.subplots(figsize=(6, 3.2))
    _weekly_panel(ax, w[w.card_patch_id == r.card_patch_id], f"{tweak_label(r)}, week by week")
    ax.legend(fontsize=7)
    save(fig, out, "fig_parry_weekly")


def fig_se_ratio(I, out):
    """Clustered over robust SE per tweak, against the treated card's offers."""
    p = I.pick_rate()
    fig, ax = plt.subplots(figsize=(6, 3.2))
    for pt in PATCH_COLOR:
        d = p[p.patch == pt]
        ax.scatter(d.n_treated_offers, d.se / d.se_hc, color=PATCH_COLOR[pt],
                   marker=PATCH_MARKER[pt], s=24)
    ax.axhline(1, color=MUTED, lw=1)
    ax.set(xscale="log", xlabel="treated card's offers", ylabel="clustered SE / robust SE",
           title="How much clustering by run widens the error bars")
    patch_legend(ax)
    save(fig, out, "fig_se_ratio")


# -------------------------------------------------------------------------------- ch 7

def fig_offer_rate(I, out):
    """Offer-share log ratio against the controls, per tweak, flagged ones labelled."""
    f = I.csv("res", "flags.csv").dropna(subset=["offer_share_vs_controls"])
    f = f.sort_values("offer_share_vs_controls")
    y = np.arange(len(f))
    fig, ax = plt.subplots(figsize=(6, 0.16 * len(f) + 1.2))
    flag = f.offer_rate_flag.eq("yes").to_numpy()
    ax.scatter(f.offer_share_vs_controls, y, color=np.where(flag, NERF, MUTED),
               marker="o", s=18)
    ax.set_yticks(y, [card_name(c) for c in f.card_id], fontsize=6)
    zero_line(ax, "x")
    ax.set(xlabel="change in offer share against the controls (log ratio)",
           title="Did the patch change how often a card is offered? (vermillion = flagged)")
    save(fig, out, "fig_offer_rate")


def fig_event_study(I, out):
    """Weekly gaps for one tweak and the tweak with the steepest pre-trend."""
    p, w, f = I.pick_rate(), I.csv("res", "weekly.csv"), I.csv("res", "flags.csv")
    r = example_cards(p)[0]
    f = f.dropna(subset=["pretrend_slope", "pretrend_slope_se"])
    pre = f.loc[(f.pretrend_slope / f.pretrend_slope_se).abs().idxmax()]
    q = p.set_index("card_patch_id").loc[pre.card_patch_id]
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.2), sharey=False)
    _weekly_panel(axes[0], w[w.card_patch_id == r.card_patch_id], tweak_label(r))
    _weekly_panel(axes[1], w[w.card_patch_id == pre.card_patch_id],
                  f"{card_name(q.card_id)} ({q.stable_build}): steepest pre-trend")
    axes[0].legend(fontsize=7)
    save(fig, out, "fig_event_study")


def fig_robustness(I, out):
    """Each check's shift from the main estimate, in the main estimate's SEs (both
    horizons: h3_ checks against weeks 0-3)."""
    p, rob = I.pick_rate().set_index("card_patch_id"), I.csv("res", "robustness.csv")
    rows = []
    for check, g in rob.groupby("check"):
        h3 = check.startswith("h3_")
        b, s = (p.beta_h, p.se_h) if h3 else (p.beta, p.se)
        g = g.set_index("card_patch_id")
        shift = ((g.beta - b.reindex(g.index)) / s.reindex(g.index)).dropna()
        rows.append((check, shift))
    rows.sort(key=lambda r: r[1].abs().median())
    fig, ax = plt.subplots(figsize=(6.5, 0.32 * len(rows) + 1.2))
    for i, (check, shift) in enumerate(rows):
        c = PATCH_COLOR["second"] if check.startswith("h3_") else PATCH_COLOR["first"]
        jitter = np.random.default_rng(i).uniform(-0.15, 0.15, len(shift))
        ax.scatter(shift.abs(), i + jitter, s=10, color=c, alpha=0.6,
                   marker="s" if check.startswith("h3_") else "o")
        ax.plot([shift.abs().median()] * 2, [i - 0.3, i + 0.3], color=INK, lw=2)
    ax.set_yticks(range(len(rows)), [r[0].replace("_", " ") for r in rows], fontsize=7)
    ax.axvline(2, color=MUTED, ls=":", lw=1)
    ax.set_xlim(left=0)
    ax.set(xlabel="|shift| from the main estimate (in its SEs); bar = median; dotted = 2",
           title="Robustness checks (squares: weeks 0-3, circles: all weeks)")
    save(fig, out, "fig_robustness")


def fig_anticipation(I, out):
    """Post-beta gap against the main effect, informative tweaks."""
    a = I.csv("res", "anticipation.csv")
    a = a[a.status == "informative"]
    if a.empty:
        raise Missing("no informative tweak in anticipation.csv")
    fig, ax = plt.subplots(figsize=(5.5, 4))
    for pt in PATCH_COLOR:
        d = a[a.patch == pt]
        ax.errorbar(100 * d.beta_main, 100 * d.beta_postbeta, yerr=196 * d.se, ls="",
                    marker=PATCH_MARKER[pt], color=PATCH_COLOR[pt], capsize=0, lw=1)
    lim = 100 * np.nanmax(np.abs(np.r_[a.beta_main, a.beta_postbeta])) * 1.1
    ax.plot([-lim, lim], [-lim, lim], color=MUTED, ls="--", lw=1)
    zero_line(ax)
    zero_line(ax, "x")
    ax.set(xlabel="main effect (pts)", ylabel="gap after the first beta (pts)",
           title="Anticipation: reacting before the stable release?")
    patch_legend(ax, fontsize=7)
    save(fig, out, "fig_anticipation")


# -------------------------------------------------------------------------------- ch 8

def fig_placebo_z(I, out):
    """Placebo z by patch against the standard normal (all weeks fits)."""
    pl = I.parquet("placebo_main.parquet", ["z", "patch", "error"])
    pl = pl[(pl.error.fillna("") == "") & np.isfinite(pl.z)]
    fig, ax = plt.subplots(figsize=(6, 3.2))
    bins = np.linspace(-15, 15, 61)
    for pt in PATCH_COLOR:
        ax.hist(pl.z[pl.patch == pt].clip(-15, 15), bins=bins, density=True,
                histtype="step", lw=2, color=PATCH_COLOR[pt], label=PATCH_LABEL[pt])
    x = np.linspace(-15, 15, 400)
    ax.plot(x, np.exp(-x ** 2 / 2) / np.sqrt(2 * np.pi), color=INK, ls="--", lw=1.5,
            label="honest errors: standard normal")
    ax.set(xlabel="placebo z (clipped at ±15)", ylabel="density",
           title="Cards that did not change: z should look like the dashed curve")
    ax.legend(fontsize=7)
    save(fig, out, "fig_placebo_z")


def fig_real_vs_placebo(I, out):
    """|beta| of each real tweak against its own window's placebos."""
    v = I.csv("an", "placebo_diagnostics_vs_real.csv").dropna(subset=["placebo_beta_sd"])
    v = v.assign(abs_real=100 * v.beta_real.abs(), spread=100 * v.placebo_beta_sd)
    fig, ax = plt.subplots(figsize=(5.5, 4))
    for pt in PATCH_COLOR:
        d = v[v.patch == pt]
        ax.scatter(d.spread, d.abs_real, color=PATCH_COLOR[pt], marker=PATCH_MARKER[pt], s=26)
    lim = max(v.spread.max(), v.abs_real.max()) * 1.1
    for k, ls in [(1, "--"), (2, ":")]:
        ax.plot([0, lim / k], [0, lim], color=MUTED, ls=ls, lw=1)
    ax.set(xlabel="sd of the window's placebo effects (pts)", ylabel="|real effect| (pts)",
           xlim=(0, lim), ylim=(0, lim),
           title="Real effects against what unchanged cards do (lines: 1x and 2x)")
    patch_legend(ax, fontsize=7)
    save(fig, out, "fig_real_vs_placebo")


# -------------------------------------------------------------------------------- ch 9

def fig_forest(I, out):
    """Every tweak's weeks 0-3 effect with clustered and placebo-scaled 95% intervals."""
    p = I.pick_rate().dropna(subset=["beta_h", "se_h"])
    c = I.csv("w", "calibrated_counts.csv")
    fac = {}
    for h in ("weeks 0-3", "all weeks"):
        r = c[(c.horizon == h) & (c.spread == "robust sd") & (c.status == "ok")]
        if len(r) and not fac:
            fac = dict(zip(r.patch, r.factor))
            fac_h = h
    p = p.sort_values(["patch", "beta_h"])
    y = np.arange(len(p))[::-1]
    fig, ax = plt.subplots(figsize=(6.5, 0.17 * len(p) + 1.4))
    col = np.where(p.change == "nerf", NERF, np.where(p.change == "buff", BUFF, NO_DIRECTION))
    if fac:
        f = p.patch.map(fac).to_numpy()
        ax.hlines(y, 100 * (p.beta_h - 1.96 * f * p.se_h), 100 * (p.beta_h + 1.96 * f * p.se_h),
                  color=col, lw=1, alpha=0.35)
    ax.hlines(y, 100 * p.ci_lo_h, 100 * p.ci_hi_h, color=col, lw=2)
    for pt in PATCH_COLOR:
        m = (p.patch == pt).to_numpy()
        ax.scatter(100 * p.beta_h[m], y[m], color=col[m], marker=PATCH_MARKER[pt], s=18, zorder=3)
    ax.set_yticks(y, [card_name(cid) for cid in p.card_id], fontsize=6)
    zero_line(ax, "x")
    note = (f"thin: placebo-scaled (robust placebo sd, {fac_h} placebos)" if fac else
            "placebo-scaled intervals not drawn: no calibration factor")
    ax.set(xlabel="effect on pick rate, weeks 0-3 (pts); thick: clustered 95% CI; " + note,
           title="Every tweak (blue: buff, vermillion: nerf; circles first patch, squares second)")
    ax.xaxis.label.set_size(7)
    save(fig, out, "fig_forest")


# ------------------------------------------------------------------------------ ch 10-11

def fig_dose(I, out):
    """Effect (log-odds) against dose by patch, with the per-patch lines, primary spec."""
    pts = I.csv("w", "dose_points.csv")
    rul = I.csv("w", "rulers.csv")
    d = pts[(pts.spec == "primary") & pts.on_ln_line.astype(str).str.lower().eq("true")]
    r = rul[(rul.spec == "primary") & (rul.ruler == "ln(new/old)")].iloc[0]
    fig, ax = plt.subplots(figsize=(6, 4))
    for pt, (slope, shift) in {"first": (r.slope1, 0.0), "second": (r.slope2, r.shift)}.items():
        g = d[d.patch == pt]
        ax.errorbar(g.x_ln, g.beta_lo, yerr=1.96 * g.se_lo, ls="", marker=PATCH_MARKER[pt],
                    color=PATCH_COLOR[pt], capsize=0, lw=1, label=PATCH_LABEL[pt])
        # intercept a for the first patch, a + c for the second: from the fitted points
        xs = np.linspace(g.x_ln.min(), g.x_ln.max(), 2)
        w = 1 / (g.se_lo ** 2 + r.tau2)
        a = np.average(g.beta_lo - slope * g.x_ln, weights=w)
        ax.plot(xs, a + slope * xs, color=PATCH_COLOR[pt], lw=2)
    zero_line(ax)
    zero_line(ax, "x")
    ax.set(xlabel="dose: ln(new / old), signed by the patch-note direction",
           ylabel="effect on picks (log-odds)",
           title=f"Dose-response, weeks 0-3, primary spec (slopes {r.slope1:.2f} and {r.slope2:+.2f})")
    ax.legend(fontsize=7, loc="upper left")
    save(fig, out, "fig_dose")


RULER_SHORT = {"ln(new/old)": "ln(new/old)", "outcome in pp, ln dose": "pp outcome",
               "absolute (new - old)": "absolute", "rank": "rank", "percent": "percent",
               "ln / kind's median |ln|": "ln / kind", "sign only": "sign",
               "(new - old) / kind's median |new - old|": "absolute / kind",
               "mean of base and upgraded ln": "base + upgraded"}


def fig_rulers(I, out):
    """Patch difference (z) by ruler and spec; the post hoc hybrid marked."""
    r = I.csv("w", "rulers.csv")
    specs = list(dict.fromkeys(r.spec))
    rulers = list(dict.fromkeys(r.ruler))
    markers = ["o", "s", "^", "D"]
    fig, ax = plt.subplots(figsize=(6.5, 0.3 * len(rulers) + 1.4))
    for j, (spec, m) in enumerate(zip(specs, markers)):
        d = r[r.spec == spec].set_index("ruler").reindex(rulers)
        ax.scatter(d.z_diff, np.arange(len(rulers)) + (j - 1.5) * 0.12, marker=m, s=22,
                   color=[INK, MUTED, BUFF, NERF][j], label=spec)
    ax.set_yticks(range(len(rulers)),
                  [RULER_SHORT.get(x, "hybrid (post hoc)" if x.startswith("hybrid") else x)
                   for x in rulers], fontsize=7)
    for v in (-2, 2):
        ax.axvline(v, color=MUTED, ls=":", lw=1)
    zero_line(ax, "x")
    ax.set(xlabel="z of the patch difference (slope 2 - slope 1)",
           title="Does the flat second patch depend on the ruler?")
    ax.legend(fontsize=6, loc="lower right")
    save(fig, out, "fig_rulers")


def fig_leave_out(I, out):
    """Second-patch slope with each tweak left out (primary spec)."""
    lo = I.csv("w", "leave_out.csv")
    lo = lo[lo.spec == "primary"]
    base = lo[lo.level == "none"].iloc[0]
    t = lo[(lo.level == "tweak") & (lo.patch == "second")].sort_values("slope2")
    y = np.arange(len(t))
    fig, ax = plt.subplots(figsize=(6, 0.22 * len(t) + 1.4))
    ax.errorbar(t.slope2, y, xerr=1.96 * t.se2, ls="", marker="s",
                color=PATCH_COLOR["second"], capsize=0, lw=1)
    ax.axvline(base.slope2, color=PATCH_COLOR["second"], ls="--", lw=1.5,
               label=f"all tweaks: {base.slope2:+.2f}")
    ax.axvline(base.slope1, color=PATCH_COLOR["first"], ls="-", lw=1.5,
               label=f"first patch: {base.slope1:.2f}")
    ax.set_yticks(y, [f"without {card_name(c)}" for c in t.card_id], fontsize=6)
    ax.set(xlabel="second-patch slope (log-odds per unit ln dose)",
           title="Leave one out: is the flat second patch one card?")
    ax.legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.18 - 0.4 / len(t)), ncol=2)
    save(fig, out, "fig_leave_out")


# -------------------------------------------------------------------------------- ch 12

def fig_power(I, out):
    """Detection share against the planted second-patch slope (primary spec)."""
    p = I.csv("w", "power.csv")
    p = p[p.spec == "primary"]
    fig, ax = plt.subplots(figsize=(6, 3.4))
    for (s, g), c, m in zip(p.groupby("setting", sort=False), [INK, NERF, BUFF], "os^"):
        ax.plot(g.planted, 100 * g.power_slope2_ne_0, color=c, marker=m, markersize=6,
                label=s)
    ax.axhline(5, color=MUTED, ls=":", lw=1)
    ax.set(xlabel="planted second-patch slope", ylabel="% of simulations detecting it",
           ylim=(0, 100), title="Power: could a real second-patch slope have been seen?")
    ax.legend(fontsize=7)
    save(fig, out, "fig_power")


def fig_fake_patch(I, out):
    """Fake-patch effects (v0.103.2 -> v0.103.3) against the real second-patch effects."""
    f, label = I.triage_csv("i_fake_patch.csv")
    f = f[f.horizon == "weeks 0-3"]
    fig, ax = plt.subplots(figsize=(5.5, 4))
    ax.errorbar(f.real_beta_lo, f.beta_lo, yerr=1.96 * f.se_lo, ls="", marker="s",
                color=PATCH_COLOR["second"], capsize=0, lw=1)
    for r in f.itertuples():
        ax.annotate(card_name(r.card_id), (r.real_beta_lo, r.beta_lo), xytext=(4, 2),
                    textcoords="offset points", fontsize=6, color=MUTED)
    zero_line(ax)
    zero_line(ax, "x")
    ax.set(xlabel="real second-patch effect, weeks 0-3 (log-odds)",
           ylabel="fake-patch effect (log-odds)",
           title=f"A patch where nothing changed ({label})")
    save(fig, out, "fig_fake_patch")


def fig_slope_by_week(I, out):
    """First-patch dose-response slope by week after release (regression to the mean, J3)."""
    w, label = I.triage_csv("j_weekly.csv")
    w = w.dropna(subset=["slope"])
    fig, ax = plt.subplots(figsize=(6, 3.2))
    ax.errorbar(w.week, w.slope, yerr=1.96 * w.se, color=PATCH_COLOR["first"], marker="o",
                capsize=0, lw=2)
    zero_line(ax)
    ax.set(xlabel="week after the first patch's release", ylabel="slope (log-odds per ln)",
           title=f"First-patch slope, week by week ({label})")
    save(fig, out, "fig_slope_by_week")


# -------------------------------------------------------------------------------- ch 13

def fig_iv_three(I, out):
    """The simulated game: naive, ITT, first stage, IV, and the truth."""
    s = I.csv("w", "iv_sim_single.csv")
    truth = s.truth.dropna().iloc[0]
    fig, ax = plt.subplots(figsize=(6, 3))
    y = np.arange(len(s))[::-1]
    ax.errorbar(s.estimate, y, xerr=1.96 * s.se, ls="", marker="o", color=INK, capsize=0)
    ax.axvline(truth, color=BUFF, ls="--", lw=1.5, label=f"true effect of picking: {truth:g}")
    ax.set_yticks(y, s.label, fontsize=7)
    zero_line(ax, "x")
    ax.set(xlabel="estimate (simulation)", title="The IV primer's game: one draw")
    ax.legend(fontsize=7)
    save(fig, out, "fig_iv_three")


def fig_iv_draws(I, out):
    """Naive against IV estimates over many simulated draws."""
    d = I.csv("w", "iv_sim_draws.csv")
    s = I.csv("w", "iv_sim_single.csv")
    truth = s.truth.dropna().iloc[0]
    fig, ax = plt.subplots(figsize=(6, 3.2))
    bins = np.linspace(min(d.naive.min(), d.iv.min()), max(d.naive.max(), d.iv.max()), 40)
    ax.hist(d.naive, bins=bins, histtype="step", lw=2, color=NERF, label="naive (took vs not)")
    ax.hist(d.iv, bins=bins, histtype="step", lw=2, color=BUFF, label="IV")
    ax.axvline(truth, color=INK, ls="--", lw=1.5, label="truth")
    ax.set(xlabel="estimate", ylabel="draws", title=f"{len(d)} simulated draws")
    ax.legend(fontsize=7)
    save(fig, out, "fig_iv_draws")


def fig_iv_weak(I, out):
    """IV's spread against the first stage's F (weak instruments)."""
    w = I.csv("w", "iv_sim_weak.csv").sort_values("F")
    fig, ax = plt.subplots(figsize=(6, 3.2))
    ax.fill_between(w.F, w.iv_p10, w.iv_p90, color=BUFF, alpha=0.2, lw=0,
                    label="IV, 10th to 90th percentile")
    ax.plot(w.F, w.iv_median, color=BUFF, marker="o", markersize=6, label="IV median")
    ax.plot(w.F, w.naive_median, color=NERF, marker="s", markersize=6, label="naive median")
    ax.axvline(10, color=MUTED, ls=":", lw=1)
    ax.set(xscale="log", xlabel="first-stage F (log scale; dotted: F = 10)",
           ylabel="estimate", title="A weak instrument makes IV unreliable")
    ax.legend(fontsize=7)
    save(fig, out, "fig_iv_weak")


FIGURES = [fig_timeline, fig_runs_per_build, fig_upload_lag, fig_confounding_dag,
           fig_before_after, fig_se_curve, fig_parry_did, fig_parry_weekly, fig_se_ratio,
           fig_offer_rate, fig_event_study, fig_robustness, fig_anticipation, fig_placebo_z,
           fig_real_vs_placebo, fig_forest, fig_dose, fig_rulers, fig_leave_out, fig_power,
           fig_fake_patch, fig_slope_by_week, fig_iv_three, fig_iv_draws, fig_iv_weak]


def draw(analysis="data/analysis", results="results", ref="reference", triage="triage",
         out="writeup/figures", only=None):
    """Every figure (or those in `only`). Returns (drawn, skipped: {name: missing input})."""
    I = Inputs(analysis, results, ref, triage)
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    drawn, skipped = [], {}
    for f in FIGURES:
        if only and f.__name__ not in only:
            continue
        try:
            f(I, out)
            drawn.append(f.__name__)
        except Missing as e:
            plt.close("all")
            skipped[f.__name__] = str(e)
    return drawn, skipped


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--analysis", default="data/analysis")
    p.add_argument("--results", default="results")
    p.add_argument("--ref", default="reference")
    p.add_argument("--triage", default="triage")
    p.add_argument("--out", default="writeup/figures")
    p.add_argument("--only", nargs="*")
    a = p.parse_args(argv)
    unknown = set(a.only or []) - {f.__name__ for f in FIGURES}
    if unknown:
        sys.exit(f"unknown figure(s): {', '.join(sorted(unknown))}")
    drawn, skipped = draw(a.analysis, a.results, a.ref, a.triage, a.out, a.only)
    print(f"{len(drawn)} figures -> {a.out}/")
    for name, why in skipped.items():
        print(f"skipped {name}: missing {why}")


if __name__ == "__main__":
    main()
