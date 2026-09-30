"""Pick-rate results dashboard (Streamlit). Local only: no deployment until the release
checklist in PLAN.md is done.

    streamlit run dashboard/app.py          # from the repo root

Reads the aggregate tables from `python -m spirometry.export` in results/, or the
synthetic ones in results_sample/ when results/ is empty (every page then says SAMPLE
DATA). It shows the exported numbers and the documented definitions; interpretation lives
in SPIROMETRY.md and the notebooks.
"""
import numpy as np
import pandas as pd
import streamlit as st

from spirometry import meta

import charts
import data

st.set_page_config(page_title="Spirometry: pick-rate results", layout="wide")
D = data.load()
PRD = D["pick_rate_did"]
PATCH_TITLE = {"first": "First patch", "second": "Second patch"}


def patch_title(patch):
    """'First patch (v0.99.1 -> v0.103.2)', from the table's own window column."""
    w = PRD.loc[PRD.patch == patch, "window"].iloc[0]
    return f"{PATCH_TITLE.get(patch, patch.title() + ' patch')} ({w.replace('->', '→')})"


def pp(s):
    """Probability units -> percentage points."""
    return 100 * s


def sample_banner():
    if D["is_sample"]:
        st.warning("**SAMPLE DATA.** Synthetic numbers from "
                   "`scripts/make_sample_results.py`, not results. Run "
                   "`python -m spirometry.export` to show the real tables.", icon="⚠️")


def horizon_choice(key):
    """All after weeks, or the fixed horizon (weeks 0-3) the dose-response uses."""
    fixed = D["meta"].get("horizon", "weeks 0-3")
    choice = st.radio("After period", ["All after weeks", f"First weeks only ({fixed})"],
                      horizontal=True, key=key)
    return choice == "All after weeks"


# ---------------------------------------------------------------------------- pages

def overview():
    st.title("Pick-rate change per tweak")
    sample_banner()
    st.caption("Each row: how much the card's pick rate (picked ÷ offered) changed after "
               "its patch, compared with unchanged cards of the same character, with a 95% "
               "interval. See About for definitions.")
    c1, c2, c3 = st.columns([2, 3, 3])
    with c1:
        all_weeks = horizon_choice("overview_horizon")
    with c2:
        patches = st.multiselect("Patch", list(PRD.patch.unique()),
                                 default=list(PRD.patch.unique()), format_func=patch_title)
    with c3:
        characters = sorted(PRD.character.unique())
        chosen = st.multiselect("Character", characters, default=characters,
                                format_func=str.title)
    b, lo, hi = ("beta", "ci_lo", "ci_hi") if all_weeks else ("beta_h", "ci_lo_h", "ci_hi_h")
    nz = "clearly_nonzero" if all_weeks else "clearly_nonzero_h"
    df = PRD[PRD.patch.isin(patches) & PRD.character.isin(chosen) & PRD[b].notna()]
    df = df.assign(beta_pp=pp(df[b]), lo_pp=pp(df[lo]), hi_pp=pp(df[hi]),
                   rate_before_pp=pp(df.treated_rate_before),
                   rate_after_pp=pp(df.treated_rate_after),
                   label=df.label + np.where(df.mixed_direction == "yes", " *", "")
                   + np.where(df.upgrade_only == "yes", " (upg)", ""))
    domain = [float(df.lo_pp.min()), float(df.hi_pp.max())] if len(df) else [-1, 1]
    for patch, g in df.groupby("patch", sort=False):
        counts = (f"{len(g)} tweaks; {int((g[nz] == 'yes').sum())} clearly nonzero, "
                  f"{int(((g[nz] == 'yes') & (g.toward_change == 'yes')).sum())} of them in "
                  f"the direction of the change")
        st.altair_chart(charts.forest(g, f"{patch_title(patch)}: {counts}", domain),
                        width="stretch")
    st.caption("\\* mixed direction: one number went up and another down; colored by the "
               "main number's change. (upg) upgrade only: fitted on upgraded offers and "
               "colored by the upgrade's change. \"In the direction of the change\" leaves "
               "both out.")
    with st.expander("Table"):
        st.dataframe(df[["label", "patch", "character", "main_field", "old", "new",
                         "beta_pp", "lo_pp", "hi_pp", nz, "toward_change",
                         "n_treated_offers"]].rename(columns={nz: "clearly_nonzero"}),
                     hide_index=True, width="stretch")


def dose_response():
    st.title("Size of change against effect")
    sample_banner()
    st.caption("x: direction × ln(new ÷ old) of the card's main number (positive = buff). "
               "y: the pick-rate change on the log-odds scale, beta ÷ (p(1 − p)) with p the "
               "card's pick rate before, a first-order approximation. Bars: 95% intervals. "
               "Lines: random-effects meta-regressions (weights 1 ÷ (se² + τ²)).")
    dr = D["dose_response"]
    horizons = list(dr.horizon.unique())
    c1, c2 = st.columns(2)
    with c1:
        horizon = st.radio("After period", horizons, horizontal=True,
                           format_func=lambda h: "all after weeks" if h == "all weeks" else h)
    with c2:
        model = st.selectbox("Fitted model", list(dict.fromkeys(dr.model)),
                             index=list(dict.fromkeys(dr.model)).index("slope per patch"))
    y, se = ("beta_lo", "se_lo") if horizon == "all weeks" else ("beta_lo_h", "se_lo_h")

    upg = PRD.upgrade_only == "yes"
    pts = PRD.assign(x=np.where(upg, PRD.dose_x_upgraded, PRD.dose_x), y=PRD[y])
    pts = pts[pts.x.notna() & pts.y.notna()]
    pts = pts.assign(y_lo=pts.y - 1.96 * pts[se], y_hi=pts.y + 1.96 * pts[se],
                     on_line=(pts.mixed_direction != "yes") & (pts.upgrade_only != "yes"),
                     kind=np.where(pts.upgrade_only == "yes", "upgrade only (x = upgrade)",
                                   np.where(pts.mixed_direction == "yes",
                                            "mixed direction (x = main number)", "on the line")))

    coefs = dr[(dr.horizon == horizon) & (dr.model == model)].set_index("term").coef.to_dict()
    xs = np.linspace(min(pts.x.min(), 0) - 0.05, max(pts.x.max(), 0) + 0.05, 50)
    if model == "one slope":
        lines = pd.DataFrame(dict(x=xs, y=meta.predict(coefs, model, xs, 0),
                                  patch="all tweaks"))
    else:                                     # one line per patch
        lines = pd.concat([pd.DataFrame(dict(x=xs, y=meta.predict(coefs, model, xs, second),
                                             patch=patch))
                           for patch, second in [("first", 0), ("second", 1)]],
                          ignore_index=True)
    st.altair_chart(charts.dose_response(pts, lines, f"Dose-response ({horizon})"),
                    width="stretch")
    st.caption("Lines: the chosen model's fit for each patch (\"one slope\": one line for "
               "both). Filled points are on the fitted line. Open points are left off it: "
               "mixed-direction tweaks (no single size) at their main number's x, "
               "upgrade-only tweaks at the upgraded card's change.")
    t = dr[dr.horizon == horizon].drop(columns=["horizon", "term"])
    st.subheader("Fitted coefficients")
    st.dataframe(t, hide_index=True, width="stretch")


def card():
    st.title("One tweak")
    sample_banner()
    opts = PRD.sort_values(["patch", "label"])
    cpid = st.selectbox("Tweak", opts.card_patch_id,
                        format_func=lambda c: f"{opts.set_index('card_patch_id').label[c]} "
                                              f"({patch_title(opts.set_index('card_patch_id').patch[c])})")
    r = PRD.set_index("card_patch_id").loc[cpid]
    change = (f"{r.main_field} {r['old']} → {r['new']}" if r.upgrade_only != "yes"
              else f"{r.upgrade_field} {r.upgrade_old} → {r.upgrade_new} (upgrade only)")
    st.markdown(f"**{r.label}** · {r.character.title()} · {change} · fitted on {r.fit_on}")
    m1, m2, m3 = st.columns(3)
    m1.metric("Change, all after weeks",
              f"{pp(r.beta):+.1f} pp", help="95% interval "
              f"{pp(r.ci_lo):+.1f} to {pp(r.ci_hi):+.1f}")
    if pd.notna(r.beta_h):
        m2.metric(f"First weeks only ({D['meta'].get('horizon', 'weeks 0-3')})",
                  f"{pp(r.beta_h):+.1f} pp", help="95% interval "
                  f"{pp(r.ci_lo_h):+.1f} to {pp(r.ci_hi_h):+.1f}")
    m3.metric("Offers of the card in the fit", f"{int(r.n_treated_offers):,}")

    c1, c2 = st.columns([1, 2])
    with c1:
        ba = pd.DataFrame(dict(
            who=["this card"] * 2 + ["unchanged"] * 2,
            block=["before", "after"] * 2,
            rate_pp=pp(np.array([r.treated_rate_before, r.treated_rate_after,
                                 r.control_rate_before, r.control_rate_after]))))
        st.altair_chart(charts.before_after(ba, "Pick rate before and after"),
                        width="stretch")
    with c2:
        wk = D["weekly"][D["weekly"].card_patch_id == cpid]
        min_offers = st.slider("Hide weeks with fewer offers of the card than", 0, 500, 100,
                               step=10)
        wk = wk[wk.n_offers >= min_offers]
        if wk.empty:
            st.info("No weekly cells for this tweak at this threshold.")
        else:
            wk = wk.assign(coef_pp=pp(wk.coef), lo_pp=pp(wk.coef - 1.96 * wk.se),
                           hi_pp=pp(wk.coef + 1.96 * wk.se))
            st.altair_chart(charts.weekly(wk, "Gap to unchanged cards, week by week"),
                            width="stretch")
            st.caption("Old build at weeks ≥ 0: people still playing the old build after "
                       "the release.")
    st.subheader("Checks")
    st.dataframe(flag_rows(cpid), hide_index=True, width="stretch")
    rb = D.get("robustness")
    if rb is not None and (rb.card_patch_id == cpid).any():
        st.subheader("Robustness fits")
        rr = rb[rb.card_patch_id == cpid]
        st.dataframe(pd.DataFrame({"check": rr.check, "change (pp)": pp(rr.beta).round(2),
                                   "se (pp)": pp(rr.se).round(2),
                                   "shift in main se": ((rr.beta - r.beta) / r.se).round(2)}),
                     hide_index=True, width="stretch")


def flag_rows(cpid):
    """The card's rows of flags.csv as (check, value, meaning)."""
    f = D["flags"].set_index("card_patch_id").loc[cpid]

    def pm(b, s):
        return "" if pd.isna(b) else f"{pp(b):+.2f} ± {pp(s):.2f} pp"

    def yn(v):
        return "not in this export" if pd.isna(v) or v == "" else v

    rows = [
        ("Offer-rate flag, all controls", yn(f.offer_rate_flag),
         "The card's share of offers moved unusually next to unchanged cards "
         "(both |z| > 3)."),
        ("Offer-rate flag, same rarity", yn(f.offer_rate_flag_rarity),
         "The same, against unchanged cards of the card's rarity."),
        ("Pre-trend slope", "" if pd.isna(f.pretrend_slope) else
         f"{pp(f.pretrend_slope):+.2f} ± {pp(f.pretrend_slope_se):.2f} pp a week "
         f"({int(f.pretrend_n_weeks)} weeks)",
         "Weekly drift of the gap before the release (blank with fewer than 2 weeks)."),
    ]
    if pd.notna(f.placebo_beta):
        rows.append(("Upgrade-only placebo (un-upgraded offers)",
                     pm(f.placebo_beta, f.placebo_se),
                     "Only the upgraded card changed, so this should be about zero."))
    if pd.notna(f.pooled_before_beta):
        rows.append(("Before block v0.103.2 + v0.103.3", pm(f.pooled_before_beta,
                                                             f.pooled_before_se), ""))
        rows.append(("No first-patch cards in the controls",
                     pm(f.no_first_patch_controls_beta, f.no_first_patch_controls_se), ""))
    return pd.DataFrame(rows, columns=["check", "value", "meaning"])


def anticipation():
    st.title("Did picks move before the stable release?")
    sample_banner()
    st.caption("On stable builds where players still had the old card: the change in the "
               "gap between the card and its controls at the date the change first appeared "
               "on a beta. Only tweaks with enough data on both sides of that date "
               "(informative) are plotted.")
    a = D["anticipation"]
    inf = a[(a.status == "informative") & a.beta_postbeta.notna() & a.beta_main.notna()]
    inf = inf.assign(main_pp=pp(inf.beta_main), post_pp=pp(inf.beta_postbeta),
                     lo_pp=pp(inf.beta_postbeta - 1.96 * inf.se),
                     hi_pp=pp(inf.beta_postbeta + 1.96 * inf.se))
    st.markdown(f"{len(inf)} of {len(a)} tweaks informative.")
    if len(inf):
        st.altair_chart(charts.anticipation(inf, "Change at the first-beta date against the "
                                                 "main effect"))
        st.caption("Dotted line: y = x, a landmark, not a target. Bars: 95% intervals.")
        with st.expander("Informative tweaks"):
            st.dataframe(inf[["label", "patch", "lead_days", "main_pp", "post_pp",
                              "ratio_to_main", "share_before_release", "first_beta_date"]],
                         hide_index=True, width="stretch")
    st.subheader("Not informative")
    st.dataframe(a[a.status != "informative"][["label", "patch", "lead_days", "status",
                                               "reason"]],
                 hide_index=True, width="stretch")


def about():
    st.title("About these numbers")
    sample_banner()
    m = D["meta"]
    why = m.get("blank_reasons", {})

    def val(key):
        return m.get(key) or f"not recorded ({why.get(key, 'unknown')})"

    st.info("**Provisional.** The run download is not finished and late uploads still "
            "add runs, so these numbers will move.", icon="ℹ️")
    st.table(pd.DataFrame(
        [("Snapshot pages", val("snapshot_pages")),
         ("Last page", val("snapshot_last_page")),
         ("Snapshot end date", val("snapshot_end_date")),
         ("Run tables: parser version", val("parser_version")),
         ("Run tables built", val("tables_built_at_utc")),
         ("Exported", m.get("exported_at_utc", ""))],
        columns=["", "value"]).set_index(""))
    st.markdown(ABOUT)
    if m.get("notes") or m.get("skipped"):
        st.subheader("Export notes")
        for n in m.get("notes", []):
            st.markdown(f"- {n}")
        for s in m.get("skipped", []):
            st.markdown(f"- skipped in {s['table']}: {', '.join(s['card_patch_ids'])}")


ABOUT = """
### Definitions

- **Offer rate** and **pick rate.** Each card-reward screen offers a few cards. A card's
  offer share is its share of its character's offers; its pick rate is picked ÷ offered.
- **Difference-in-differences.** For each changed card, the change in its pick rate from
  the builds before its patch to the builds after, minus the same change for the unchanged
  cards of the same character (the controls). The controls carry everything else that moved
  between the builds. Estimated as a linear probability model with fixed effects for card ×
  upgraded, card × uploader group, block × uploader group, act and ascension; errors
  clustered by run. Effects are in percentage points of pick rate.
- **Clearly nonzero.** |effect| > 2 standard errors.
- **In the direction of the change.** The effect has the sign of the change (a buff picked
  more, a nerf less). Mixed-direction and upgrade-only tweaks are left out.
- **All after weeks / first weeks only.** The first patch's after period is longer than the
  second's. The fixed-horizon fit keeps after-build offers from the release week and the
  three weeks after it, so both patches compare at the same horizon; the dose-response uses
  it by default.
- **Log-odds scale.** effect ÷ (p(1 − p)), p the card's pick rate before: a first-order
  approximation, so cards picked 5% and 50% of the time can compare.
- **Offer-rate check.** A number change should not change how often the RNG offers a card.
  A flag means the card's offer share moved unusually next to the controls; a flag against
  same-rarity controls too means it isn't a change in that rarity's pool.
- **Pre-trend.** The weekly slope of the gap before the release, from the event study.
- **Upgrade-only placebo.** When only the upgraded card changed, the un-upgraded offers
  should show no effect.
- **Anticipation check.** On stable builds where players still had the old card, did the
  gap move at the date the change first appeared on a beta? Informative when each side of
  that date has at least 2,000 offers of the card and 3 days with one.

### Population

Solo runs from the Spire Codex export; no modifiers or mods; builds with a known release,
runs not started before it; runs that start at Neow; card-reward offers after combat, elite,
boss and event fights; one copy per run when a run was uploaded twice; the character's own
cards. Upgrade-only tweaks are fitted on upgraded offers.

### Uploader groups

Runs uploaded through the SlayTheStats mod carry a tag. Tagged and untagged uploaders rank
cards differently, already before the mod's community tooltips, so the fits include
uploader-group terms, and fits within each group are robustness checks. Uploaders are
self-selected and probably more dedicated than the average player.

### Where the discussion is

Open questions, caveats and the numbers' write-up are in `SPIROMETRY.md` ("Phase 5
results", including "Anticipation") and `notebooks/02_pick_rate_did.ipynb`,
`notebooks/03_anticipation.ipynb`. This dashboard shows the exported tables only.
"""

pages = [st.Page(overview, title="Overview", default=True),
         st.Page(dose_response, title="Dose-response", url_path="dose-response"),
         st.Page(card, title="Card", url_path="card")]
if "anticipation" in D:
    pages.append(st.Page(anticipation, title="Anticipation", url_path="anticipation"))
pages.append(st.Page(about, title="About", url_path="about"))
st.sidebar.caption(f"Data: `{D['folder'].name}/`" + (" (sample)" if D["is_sample"] else ""))
st.navigation(pages).run()
