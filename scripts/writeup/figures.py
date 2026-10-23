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


# ------------------------------------------------------------------ toy simulations
# spirometry.teaching_sims (rework, 2026-10-22): every title says "simulation", because
# nothing here is your data.

SIM = "Simulation with known truth"
CALC = "Worked example, not your data"


def _toy(I, toy, part):
    return I.csv("w", f"toy_{toy}_{part}.csv")


def _toy_value(I, toy, quantity):
    s = I.csv("w", "teaching_sims.csv")
    v = s.loc[(s.toy == toy) & (s.quantity == quantity), "value"]
    if v.empty:
        raise Missing(f"teaching_sims.csv: {toy} {quantity}")
    return float(v.iloc[0])


def fig_toy_bernoulli_sd(I, out):
    """§1: the spread of one yes/no offer, sqrt(p(1 - p))."""
    c = _toy(I, "bernoulli_spread", "curve")
    fig, ax = plt.subplots(figsize=(5.5, 3))
    ax.plot(c.p, c.sd, color=INK)
    for p in (0.2, 0.5):
        sd = np.sqrt(p * (1 - p))
        ax.plot(p, sd, "o", color=BUFF, markersize=7)
        ax.annotate(f"p = {p:g}: SD = {sd:.2f}", (p, sd), textcoords="offset points",
                    xytext=(8, -14), fontsize=8)
    ax.set(xlabel="pick rate p", ylabel="SD of one offer", ylim=(0, 0.55),
           title=f"{CALC}: the spread of one yes/no offer, √(p(1 − p))")
    save(fig, out, "fig_toy_bernoulli_sd")


def fig_toy_sd_vs_se(I, out):
    """§2: the data (two bars) against the estimate over imagined reruns."""
    r = _toy(I, "sd_vs_se", "reruns")
    p, n = _toy_value(I, "sd_vs_se", "p_true"), int(_toy_value(I, "sd_vs_se", "n"))
    share = _toy_value(I, "sd_vs_se", "share_picked")
    sd, se = _toy_value(I, "sd_vs_se", "sd_data"), _toy_value(I, "sd_vs_se", "se_formula")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.5, 3))
    a1.bar([0, 1], [1 - share, share], width=0.35, color=MUTED)
    a1.set_xticks([0, 1], ["skip (0)", "pick (1)"])
    a1.set(ylabel="share of offers", title=f"The data: one dataset of {n:,} offers\n"
           f"SD = {sd:.2f}")
    a2.hist(r.estimate, bins=40, density=True, color=BUFF, alpha=0.5)
    x = np.linspace(r.estimate.min(), r.estimate.max(), 200)
    a2.plot(x, np.exp(-0.5 * ((x - p) / se) ** 2) / (se * np.sqrt(2 * np.pi)), color=INK, lw=1)
    a2.set(xlabel="estimated pick rate", ylabel="density",
           title=f"The estimate over {len(r):,} reruns\nSE = SD / √n = {se:.3f}")
    fig.suptitle(SIM, fontsize=8, color=MUTED)
    save(fig, out, "fig_toy_sd_vs_se")


def fig_toy_lln_clt(I, out):
    """§3: Picture B (CLT) at growing n on top; Picture A (LLN) below."""
    c, r = _toy(I, "lln_clt", "clt"), _toy(I, "lln_clt", "running")
    p = _toy_value(I, "lln_clt", "p")
    ns = sorted(c.n.unique())
    fig = plt.figure(figsize=(8, 5))
    for i, n in enumerate(ns):
        ax = fig.add_subplot(2, len(ns), i + 1)
        e = c.estimate[c.n == n]
        if n <= 10:
            vals, counts = np.unique(e, return_counts=True)
            ax.bar(vals, counts / len(e), width=0.8 / n, color=BUFF, alpha=0.7)
        else:
            ax.hist(e, bins=30, density=True, color=BUFF, alpha=0.6)
            se = np.sqrt(p * (1 - p) / n)
            x = np.linspace(e.min(), e.max(), 200)
            ax.plot(x, np.exp(-0.5 * ((x - p) / se) ** 2) / (se * np.sqrt(2 * np.pi)),
                    color=INK, lw=1)
        ax.axvline(p, color=NERF, ls="--", lw=1)
        ax.set_title(f"n = {n:,}", fontsize=8)
        ax.tick_params(labelsize=6)
        ax.set_yticks([])
    ax = fig.add_subplot(2, 1, 2)
    k = r.offers.to_numpy()
    se_k = np.sqrt(p * (1 - p) / k)
    ax.plot(k, r.estimate, color=INK, lw=1, label="running estimate, one dataset")
    ax.fill_between(k, p - se_k, p + se_k, color=BUFF, alpha=0.2, lw=0, label="true p ± 1 SE")
    ax.axhline(p, color=NERF, ls="--", lw=1, label="true p")
    ax.set(xscale="log", ylim=(0, 1), xlabel="offers so far (log scale)",
           ylabel="estimated pick rate")
    ax.legend(fontsize=7, loc="upper right")
    fig.suptitle(f"{SIM}. Top: the estimate over many reruns at fixed n (central limit "
                 "theorem). Bottom: one dataset growing (law of large numbers).",
                 fontsize=8, color=MUTED)
    save(fig, out, "fig_toy_lln_clt")


def fig_toy_posterior(I, out):
    """§4: a flat prior updated offer by offer."""
    d = _toy(I, "small_samples", "posterior")
    p = _toy_value(I, "small_samples", "p_true")
    fig, ax = plt.subplots(figsize=(6, 3.4))
    ns = sorted(d.n.unique())
    shades = np.linspace(0.75, 0.0, len(ns))
    for n, g in zip(ns, shades):
        s = d[d.n == n]
        ax.plot(s.p, s.density, color=str(g) if n else MUTED, lw=1.5,
                ls="--" if n == 0 else "-", label=f"n = {n:,}, picks = {int(s.k.iloc[0])}")
    ax.axvline(p, color=NERF, ls=":", lw=1.5, label="true p")
    ax.set(xlabel="pick rate p", ylabel="posterior density", ylim=(0, 20),
           title=f"{SIM}: a flat prior updated offer by offer")
    ax.legend(fontsize=7, ncol=2)
    save(fig, out, "fig_toy_posterior")


def fig_toy_log_odds(I, out):
    """§5: the same log-odds push at every baseline, in points."""
    c, pts = _toy(I, "log_odds_push", "curve"), _toy(I, "log_odds_push", "points")
    delta = _toy_value(I, "log_odds_push", "delta")
    fig, ax = plt.subplots(figsize=(5.8, 3.2))
    ax.plot(100 * c.p0, 100 * c.exact, color=INK, label="exact")
    ax.plot(100 * c.p0, 100 * c.approx, color=BUFF, ls="--", lw=1.5,
            label="rule of thumb: Δ · p(1 − p)")
    for r in pts.itertuples():
        ax.plot(100 * r.p0, 100 * r.exact, "o", color=INK, markersize=6)
        ax.annotate(f"{100 * r.p0:.0f}% card: +{100 * r.exact:.1f} points",
                    (100 * r.p0, 100 * r.exact), textcoords="offset points",
                    xytext=(8, 6) if r.p0 >= 0.45 else (6, -12), fontsize=7)
    ax.set(xlabel="pick rate before (%)", ylabel="change in pick rate (points)",
           ylim=(0, 1.15 * 100 * c.exact.max()),
           title=f"{CALC}: a +{delta:g} log-odds push at different baselines")
    ax.legend(fontsize=7, loc="lower center")
    save(fig, out, "fig_toy_log_odds")


def fig_toy_fixed_bias(I, out):
    """§6: a fixed bias at growing n: precise and wrong."""
    e = _toy(I, "fixed_bias", "estimates")
    p = _toy_value(I, "fixed_bias", "p_true")
    bias = _toy_value(I, "fixed_bias", "bias_pp")
    ns = sorted(e.n.unique())
    fig, axes = plt.subplots(1, len(ns), figsize=(8, 2.6), sharey=False)
    for ax, n in zip(axes, ns):
        s = e.estimate[e.n == n]
        se = np.sqrt(p * (1 - p) / n)
        lo, hi = min(s.min(), p) - 0.002, max(s.max(), p) + 0.002
        ax.hist(s, bins=np.linspace(lo, hi, 35), color=MUTED, alpha=0.7)
        ax.axvline(p, color=NERF, ls="--", lw=1.5, label="truth")
        ax.axvline(p + bias, color=INK, lw=1, label="where it centres")
        ax.set_title(f"n = {n:,}\nbias / SE = {bias / se:.1f}", fontsize=8)
        ax.set_yticks([])
        ax.tick_params(labelsize=6)
        ax.xaxis.set_major_locator(plt.MaxNLocator(3))
    axes[0].legend(fontsize=6, loc="upper left")
    fig.supxlabel("estimated pick rate", fontsize=8)
    fig.suptitle(f"{SIM}: an estimate one point too high, at growing sample size",
                 fontsize=9)
    save(fig, out, "fig_toy_fixed_bias")


def fig_toy_se_difference(I, out):
    """§7: the SE of a difference floors at its smaller side."""
    c = _toy(I, "se_difference", "curve")
    nb = int(_toy_value(I, "se_difference", "n_before"))
    se_b = _toy_value(I, "se_difference", "se_before_pp")
    fig, ax = plt.subplots(figsize=(5.8, 3.2))
    ax.plot(c.n_after, 100 * c.se_diff, color=INK, label="SE of the difference")
    ax.axhline(100 * se_b, color=BUFF, ls="--", lw=1.5,
               label="before block's SE alone (the floor)")
    ax.axvline(nb, color=MUTED, ls=":", lw=1)
    ax.set(xscale="log", xlabel="offers in the after block (log scale; dotted: equal sizes)",
           ylabel="SE (points)", ylim=(0, None),
           title=f"{CALC}: a difference is limited by its smaller side\n"
                 f"(before block fixed at {nb:,} offers)")
    ax.legend(fontsize=7)
    save(fig, out, "fig_toy_se_difference")


def fig_toy_buffs_nerfs(I, out):
    """§8: buffs and nerfs on one line."""
    d = _toy(I, "buffs_nerfs", "points")
    slope = _toy_value(I, "buffs_nerfs", "slope")
    fig, ax = plt.subplots(figsize=(5, 3.4))
    for ch, col, mk in (("buff", BUFF, "o"), ("nerf", NERF, "s")):
        s = d[d.change == ch]
        ax.scatter(s.dose, s.effect, color=col, marker=mk, s=40, label=f"{ch}s", zorder=3)
    b, a = np.polyfit(d.dose, d.effect, 1)
    xx = np.array([-0.4, 0.4])
    ax.plot(xx, a + b * xx, color=INK, lw=1, label=f"fitted slope {slope:.2f}")
    zero_line(ax)
    zero_line(ax, "x")
    ax.set(xlabel="dose = ln(new / old)", ylabel="effect on picks (log-odds)",
           title=f"{SIM}: the mean effect cancels, the slope doesn't")
    ax.legend(fontsize=7)
    save(fig, out, "fig_toy_buffs_nerfs")


def fig_toy_type_shock(I, out):
    """§9: a type-wide shock leaks through mixed controls."""
    names = [("truth_pp", "truth"), ("naive_pp", "naive before/after"),
             ("did_mixed_pp", "DiD, same-character controls"),
             ("did_skill_only_pp", "DiD, skill-only controls")]
    v = [_toy_value(I, "type_shock", q) for q, _ in names]
    fig, ax = plt.subplots(figsize=(5.8, 2.4))
    y = np.arange(len(v))[::-1]
    ax.barh(y, [100 * x for x in v], color=[INK, MUTED, NERF, BUFF], height=0.55)
    ax.set_yticks(y, [lab for _, lab in names], fontsize=8)
    ax.axvline(100 * v[0], color=INK, ls="--", lw=1)
    zero_line(ax, "x")
    ax.set(xlabel="estimated effect of the nerf (points)",
           title=f"{SIM}: a shock to one card type leaks through mixed controls")
    save(fig, out, "fig_toy_type_shock")


def fig_toy_power(I, out):
    """§10: a toy power curve."""
    t = _toy(I, "toy_power", "curve")
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.plot(t.planted, 100 * t.detected, color=INK, marker="o", markersize=7)
    ax.axhline(5, color=MUTED, ls=":", lw=1)
    ax.set(xlabel="planted slope", ylabel="detected (% of simulations)", ylim=(0, 100),
           title=f"{SIM}: a toy power curve (dotted: 5%)")
    save(fig, out, "fig_toy_power")


def fig_toy_false_alarms(I, out):
    """§11: understated error bars inflate the share of null fits flagged."""
    c = _toy(I, "false_alarms", "curve")
    fig, ax = plt.subplots(figsize=(5.5, 3.2))
    ax.plot(c.f, 100 * c.share, color=INK)
    ax.set(xlabel="true scatter ÷ reported SE", ylabel="null fits flagged |z| > 2 (%)",
           ylim=(0, 100), title=f"{CALC} (normal scatter assumed):\n"
                                 "how understated error bars inflate false alarms")
    save(fig, out, "fig_toy_false_alarms")


def fig_toy_spillover(I, out):
    """§13: spillover with one card nerfed against eight buffed."""
    e = _toy(I, "spillover", "estimates").set_index("scenario")
    rows = [("did_other", "other characters"), ("did_same", "same character"),
            ("did_drop_screens", "same char., drop treated's screens")]
    fig, axes = plt.subplots(1, 2, figsize=(8, 2.6), sharey=True)
    for ax, s, title in zip(axes, ("a", "b"), ("A: one card nerfed", "B: eight cards buffed")):
        v = [100 * e.loc[s, q] for q, _ in rows]
        y = np.arange(len(v))[::-1]
        ax.barh(y, v, color=MUTED, height=0.55)
        ax.axvline(100 * e.loc[s, "truth"], color=INK, ls="--", lw=1.2)
        ax.set_yticks(y, [lab for _, lab in rows], fontsize=8)
        zero_line(ax, "x")
        ax.set(title=title, xlabel="estimated effect on card 0 (points)")
    fig.suptitle(SIM + ": DiD with the controls named on the left; dashed line: the truth "
                 "(card 0's own change)", fontsize=8, color=MUTED)
    save(fig, out, "fig_toy_spillover")


def fig_toy_drift(I, out):
    """§15: skips and one card's discovery trend with no patch."""
    w = _toy(I, "drift", "weeks")
    wk = _toy_value(I, "drift", "fake_patch_week")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(8, 2.9))
    a1.plot(w.week, 100 * w.skip, color=NERF, marker="s", label="skip rate")
    a1.plot(w.week, 100 * w.controls, color=MUTED, marker="o", label="controls' pick rate")
    a1.set(xlabel="week", ylabel="%", title="The total isn't fixed: skips can trend")
    a1.legend(fontsize=7)
    a2.plot(w.week, 100 * (w.card0 - w.controls), color=INK, marker="o")
    a2.axvline(wk - 0.5, color=MUTED, ls="--", lw=1)
    a2.text(wk - 0.4, a2.get_ylim()[0], " fake patch date", va="bottom", fontsize=7,
            color=MUTED)
    a2.set(xlabel="week", ylabel="card 0 minus controls (points)",
           title="One card can trend against the rest")
    fig.suptitle(SIM + ": no patch at all", fontsize=8, color=MUTED)
    save(fig, out, "fig_toy_drift")


def fig_toy_two_columns(I, out):
    """§16: the best line through two columns joins their averages."""
    d = _toy(I, "two_columns", "points")
    rng = np.random.default_rng(0)                       # jitter only, so the dots show
    fig, ax = plt.subplots(figsize=(4.6, 3.4))
    ax.scatter(d.x + rng.uniform(-0.06, 0.06, len(d)), d.height, s=9, color=MUTED, alpha=0.6,
               lw=0)
    m = d.groupby("x").height.mean()
    ax.plot([0, 1], [m[0], m[1]], color=INK, lw=1.5, zorder=3, label="fitted line")
    ax.plot([0, 1], [m[0], m[1]], "D", color=BUFF, markersize=8, zorder=4,
            label="column averages")
    ax.set_xticks([0, 1], ["age 7 (x = 0)", "age 8 (x = 1)"])
    ax.set(xlim=(-0.4, 1.4), ylabel="height (cm)",
           title=f"{SIM}:\nthe best line through two columns joins their averages")
    ax.legend(fontsize=7, loc="upper left")
    save(fig, out, "fig_toy_two_columns")


def fig_toy_se_layers(I, out):
    """§18: four SEs from one dataset against the true wobble over reruns."""
    s = _toy(I, "se_layers", "se")
    n_reruns = int(_toy_value(I, "se_layers", "n_reruns"))
    label = {"hand": "hand rule (cells in quadrature)", "iid": "classical (iid)",
             "hc1": "robust (HC1, sandwich)", "clustered": "clustered by run"}
    fig, ax = plt.subplots(figsize=(5.8, 2.6))
    y = np.arange(len(s))[::-1]
    ax.barh(y, s.se, color=[MUTED, MUTED, MUTED, BUFF], height=0.55)
    truth = s.true_wobble.iloc[0]
    ax.axvline(truth, color=INK, ls="--", lw=1.2)
    ax.text(truth, y.max() + 0.45, f" true wobble:\n sd over {n_reruns} reruns", fontsize=7,
            va="top", ha="left")
    ax.set_yticks(y, [label[e] for e in s.estimator], fontsize=8)
    ax.set(xlabel="standard error of the DiD", xlim=(0, 1.45 * truth),
           title=f"{SIM}: each player has a taste for the treated card")
    save(fig, out, "fig_toy_se_layers")


FIGURES = [fig_timeline, fig_runs_per_build, fig_upload_lag, fig_confounding_dag,
           fig_before_after, fig_se_curve, fig_parry_did, fig_parry_weekly, fig_se_ratio,
           fig_offer_rate, fig_event_study, fig_robustness, fig_anticipation, fig_placebo_z,
           fig_real_vs_placebo, fig_forest, fig_dose, fig_rulers, fig_leave_out, fig_power,
           fig_fake_patch, fig_slope_by_week, fig_iv_three, fig_iv_draws, fig_iv_weak,
           fig_toy_bernoulli_sd, fig_toy_sd_vs_se, fig_toy_lln_clt, fig_toy_posterior,
           fig_toy_log_odds, fig_toy_fixed_bias, fig_toy_se_difference, fig_toy_buffs_nerfs,
           fig_toy_type_shock, fig_toy_power, fig_toy_false_alarms, fig_toy_spillover,
           fig_toy_drift, fig_toy_two_columns, fig_toy_se_layers]


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
