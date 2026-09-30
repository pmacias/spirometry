"""Chart functions for the dashboard (Altair). Each takes a tidy DataFrame and returns a
chart; no data wrangling beyond unit conversion happens here.

Colors: Okabe-Ito blue / vermillion for buff / nerf; dark goldenrod / purple for the first
and second patch, always paired with a marker shape so color is never the only cue. All
pairs pass a colorblind-separation check on a light background (the app pins Streamlit's
light theme in .streamlit/config.toml).
"""
import altair as alt
import numpy as np
import pandas as pd

BUFF, NERF, NO_DIRECTION = "#0072B2", "#D55E00", "#767676"
PATCH_COLOR = {"first": "#B8860B", "second": "#6A3D9A"}
PATCH_SHAPE = {"first": "circle", "second": "square"}
BEFORE, AFTER = "#767676", "#0072B2"
TREATED, CONTROLS = "#000000", "#999999"
GRID = "#bbbbbb"


def _patch_scales(patches):
    patches = [p for p in PATCH_COLOR if p in set(patches)]
    color = alt.Scale(domain=patches, range=[PATCH_COLOR[p] for p in patches])
    shape = alt.Scale(domain=patches, range=[PATCH_SHAPE[p] for p in patches])
    return color, shape


def _zero(axis="x"):
    """A thin reference line at zero."""
    enc = alt.X("zero:Q") if axis == "x" else alt.Y("zero:Q")
    return alt.Chart(pd.DataFrame({"zero": [0]})).mark_rule(color=GRID).encode(enc)


def forest(df, title, domain):
    """One row per tweak: effect in percentage points with its 95% interval.
    df: label, beta_pp, lo_pp, hi_pp, change (buff / nerf / ''), plus tooltip columns.
    domain: the x range (shared between panels so they compare directly)."""
    df = df.assign(change=df.change.replace("", "no single direction"))
    order = df.sort_values("beta_pp").label.tolist()
    color = alt.Color("change:N", title="Change",
                      scale=alt.Scale(domain=["buff", "nerf", "no single direction"],
                                      range=[BUFF, NERF, NO_DIRECTION]))
    y = alt.Y("label:N", sort=order, title=None, axis=alt.Axis(labelLimit=240))
    tooltip = [alt.Tooltip("label:N", title="card"),
               alt.Tooltip("beta_pp:Q", title="change (pp)", format="+.1f"),
               alt.Tooltip("lo_pp:Q", title="95% low", format="+.1f"),
               alt.Tooltip("hi_pp:Q", title="95% high", format="+.1f"),
               alt.Tooltip("rate_before_pp:Q", title="pick rate before (%)", format=".1f"),
               alt.Tooltip("rate_after_pp:Q", title="pick rate after (%)", format=".1f"),
               alt.Tooltip("n_treated_offers:Q", title="offers of the card", format=",")]
    base = alt.Chart(df).encode(y=y, color=color, tooltip=tooltip)
    interval = base.mark_rule(strokeWidth=2).encode(
        x=alt.X("lo_pp:Q", title="change in pick rate vs. unchanged cards "
                                  "(percentage points)", scale=alt.Scale(domain=domain)),
        x2="hi_pp:Q")
    point = base.mark_point(filled=True, size=70, opacity=1).encode(x="beta_pp:Q")
    return (_zero("x") + interval + point).properties(title=title, height=alt.Step(22))


def dose_response(points, lines, title):
    """Effect (log-odds) against size of change, one color and shape per patch. Filled
    points are on the fitted line; open points (mixed direction, upgrade-only) are not.
    points: label, x, y, y_lo, y_hi, patch, on_line (bool), kind.
    lines: x, y, patch ('first' / 'second', or 'all tweaks' for one line over both)."""
    groups = [g for g in ["first", "second", "all tweaks"]
              if g in set(points.patch) | set(lines.patch)]
    colors = {**PATCH_COLOR, "all tweaks": NO_DIRECTION}
    shapes = {**PATCH_SHAPE, "all tweaks": "diamond"}
    color = alt.Color("patch:N", title="Patch",
                      scale=alt.Scale(domain=groups, range=[colors[g] for g in groups]))
    shape = alt.Shape("patch:N", title="Patch",
                      scale=alt.Scale(domain=groups, range=[shapes[g] for g in groups]))
    x = alt.X("x:Q", title="size of change: direction × ln(new / old)")
    tooltip = [alt.Tooltip("label:N", title="card"), alt.Tooltip("kind:N", title="tweak"),
               alt.Tooltip("x:Q", title="size of change", format="+.2f"),
               alt.Tooltip("y:Q", title="effect (log-odds)", format="+.2f")]
    base = alt.Chart(points)
    bars = base.mark_rule(strokeWidth=1.5, opacity=0.5).encode(
        x=x, y=alt.Y("y_lo:Q", title="effect on pick rate (log-odds)"), y2="y_hi:Q",
        color=color)
    on = base.transform_filter("datum.on_line").mark_point(
        filled=True, size=70, opacity=1).encode(x=x, y="y:Q", color=color, shape=shape,
                                                tooltip=tooltip)
    off = base.transform_filter("!datum.on_line").mark_point(
        filled=False, size=90, strokeWidth=2, opacity=1).encode(
        x=x, y="y:Q", color=color, shape=shape, tooltip=tooltip)
    fitted = alt.Chart(lines).mark_line(strokeWidth=2).encode(
        x="x:Q", y="y:Q", color=color, detail="patch:N")
    return alt.layer(_zero("x"), _zero("y"), fitted, bars, on, off).properties(
        title=title, height=460)


def before_after(df, title):
    """Pick rate before and after, treated card vs. its unchanged controls (a slope chart).
    df: who ('this card' / 'unchanged': its controls), block ('before' / 'after'), rate_pp."""
    df = df.assign(block=pd.Categorical(df.block, ["before", "after"]))
    color = alt.Color("who:N", legend=None,          # labelled directly at the right
                      scale=alt.Scale(domain=["this card", "unchanged"],
                                      range=[TREATED, CONTROLS]))
    base = alt.Chart(df).encode(
        x=alt.X("block:N", sort=["before", "after"], title=None,
                axis=alt.Axis(labelAngle=0)),
        y=alt.Y("rate_pp:Q", title="pick rate (%)", scale=alt.Scale(zero=True)),
        color=color, detail="who:N",
        tooltip=[alt.Tooltip("who:N"), alt.Tooltip("block:N"),
                 alt.Tooltip("rate_pp:Q", title="pick rate (%)", format=".1f")])
    labels = base.transform_filter("datum.block == 'after'").mark_text(
        align="left", dx=8, color="#333333").encode(text="who:N")
    return (base.mark_line(strokeWidth=2) + base.mark_point(filled=True, size=70)
            + labels).properties(title=title, height=300)


def weekly(df, title):
    """The card's gap to its controls by week from the release (week 0 = release week),
    relative to the last week before it (week -1, drawn as an open square at 0).
    df: week, block, coef_pp, lo_pp, hi_pp, n_offers."""
    color = alt.Color("block:N", title="Build",
                      scale=alt.Scale(domain=["before", "after"], range=[BEFORE, AFTER]),
                      legend=alt.Legend(labelExpr="datum.label == 'before' ? "
                                                  "'old build' : 'new build'"))
    x = alt.X("week_x:Q", title="weeks from the release (week 0 = release week)",
              axis=alt.Axis(tickMinStep=1))
    df = df.assign(week_x=df.week + np.where(df.block == "before", -0.12, 0.12))
    tooltip = [alt.Tooltip("week:Q"), alt.Tooltip("block:N", title="build"),
               alt.Tooltip("coef_pp:Q", title="gap vs. week −1 (pp)", format="+.1f"),
               alt.Tooltip("n_offers:Q", title="offers of the card", format=",")]
    base = alt.Chart(df).encode(x=x, color=color, tooltip=tooltip)
    bars = base.mark_rule(strokeWidth=1.5).encode(
        y=alt.Y("lo_pp:Q", title="gap vs. week −1 (percentage points)"), y2="hi_pp:Q")
    pts = base.mark_point(filled=True, size=60, opacity=1).encode(y="coef_pp:Q")
    ref = alt.Chart(pd.DataFrame({"week_x": [-1], "y": [0]})).mark_point(
        shape="square", filled=False, size=60, color=BEFORE, strokeWidth=2).encode(
        x="week_x:Q", y="y:Q")
    release = alt.Chart(pd.DataFrame({"week_x": [-0.5], "text": ["release"]}))
    rule = release.mark_rule(strokeDash=[4, 4], color="#333333").encode(x="week_x:Q")
    text = release.mark_text(align="left", dx=4, dy=-6, color="#333333",
                             baseline="top").encode(x="week_x:Q", y=alt.value(0),
                                                    text="text:N")
    return alt.layer(_zero("y"), rule, text, bars, pts, ref).properties(
        title=title, height=320)


def anticipation(df, title):
    """Change at the first-beta date (old-card builds) against the main effect, with a
    y = x line. df: label, patch, main_pp, post_pp, lo_pp, hi_pp, lead_days."""
    color, shape = _patch_scales(df.patch)
    lim = float(np.nanmax(np.abs(np.r_[df.main_pp, df.lo_pp, df.hi_pp]))) * 1.1 or 1.0
    domain = alt.Scale(domain=[-lim, lim])
    diag = alt.Chart(pd.DataFrame({"x": [-lim, lim], "y": [-lim, lim]})).mark_line(
        strokeDash=[2, 3], color=NO_DIRECTION).encode(x="x:Q", y="y:Q")
    x = alt.X("main_pp:Q", title="main effect at the stable release (pp)", scale=domain)
    color = alt.Color("patch:N", title="Patch", scale=color)
    tooltip = [alt.Tooltip("label:N", title="card"),
               alt.Tooltip("main_pp:Q", title="main effect (pp)", format="+.1f"),
               alt.Tooltip("post_pp:Q", title="change at beta date (pp)", format="+.1f"),
               alt.Tooltip("lead_days:Q", title="lead time (days)")]
    base = alt.Chart(df)
    bars = base.mark_rule(strokeWidth=1.5, opacity=0.5).encode(
        x=x, y=alt.Y("lo_pp:Q", title="change at the first-beta date, old-card builds (pp)",
                     scale=domain), y2="hi_pp:Q", color=color)
    pts = base.mark_point(filled=True, size=70, opacity=1).encode(
        x=x, y="post_pp:Q", color=color, shape=alt.Shape("patch:N", title="Patch",
                                                          scale=shape), tooltip=tooltip)
    return alt.layer(_zero("x"), _zero("y"), diag, bars, pts).properties(
        title=title, height=460, width=460)
