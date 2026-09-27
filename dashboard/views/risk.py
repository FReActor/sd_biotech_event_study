"""Risk check: how big have this company's past filings of a given type been?"""

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from charts import PLOTLY_CONFIG, style
from data import INK, INK_MUTED
from product import LABEL_NAMES, MIN_OWN_EVENTS, load_companies, risk_profile
from ui import (DOWN_COLOR, UP_COLOR, chart_title, company_picker, insight, page_intro,
                risk_headline, source, stat_strip)

comp = load_companies().sort_values("company").set_index("ticker")

page_intro(
    "Risk check",
    "Before a company reports, see how far its past reports have moved the stock "
    "on the day, and what that means for a position you hold.",
)

c1, c2, c3 = st.columns([4, 4, 2], vertical_alignment="top")
ticker = company_picker(comp, key="risk_ticker", container=c1)
label = c2.segmented_control(
    "Type of news", ["CLINICAL", "EARNINGS", "REGULATORY"], default="CLINICAL",
    required=True, format_func=LABEL_NAMES.get, key="risk_label",
)
size = c3.number_input("Position ($)", min_value=0, value=10_000, step=1_000)

name = comp.at[ticker, "company"]
kind = LABEL_NAMES[label].lower()
r = risk_profile(ticker, label)
own = r["own"]


def dollars(pct: float) -> str:
    return f"${size * pct / 100:,.0f}"


# --- headline insight: trial news vs earnings for this company ----------------------
c = comp.loc[ticker]
if c["readouts"] >= 2 and c["earnings"] >= 2 and c["earnings_move"] > 0:
    ratio = c["readout_move"] / c["earnings_move"]
    insight(
        f"{ratio:.1f}×",
        f"For <b>{name}</b>, a trial readout has typically moved the stock {ratio:.1f} times "
        "as much as an earnings report."
        f'<span class="sub">±{c["readout_move"]:.1f}% on trial days vs ±{c["earnings_move"]:.1f}% '
        f'on earnings days · {int(c["readouts"])} readouts, {int(c["earnings"])} earnings reports</span>',
    )

# --- the answer ----------------------------------------------------------------------
if r["use_own"]:
    note = f"Based on {r['n']} past {kind} filings from {name}, 2019–2025."
else:
    if len(own):
        have = f"only {len(own)} past {kind} filing" + ("s" if len(own) > 1 else "")
        note = (f"{name} has {have}, too few to rely on (under {MIN_OWN_EVENTS}), so this "
                f"uses all {r['n']} {kind} filings from San Diego life sciences companies.")
    else:
        note = (f"{name} has no past {kind} filings, so this uses all {r['n']} {kind} "
                "filings from San Diego life sciences companies.")
article = "an" if kind[0] in "aeiou" else "a"
line = (f"On {article} {kind} day, {name if r['use_own'] else 'a company like ' + name} has "
        f"typically moved <b>±{r['typical']:.1f}%</b>"
        + (f", about <b>{dollars(r['typical'])}</b> on your position." if size else "."))
risk_headline(line, note)

stat_strip([
    (f"±{r['typical']:.1f}%", "typical move", dollars(r["typical"]) if size else ""),
    (f"±{r['p75']:.1f}%", "1 in 4 moved more than", dollars(r["p75"]) if size else ""),
    (f"±{r['p90']:.1f}%", "1 in 10 moved more than", dollars(r["p90"]) if size else ""),
    (f"{r['share_up']:.0%}", "of these days the stock rose"),
])

# --- this company's past filings -------------------------------------------------------------
st.header(f"{name}'s past {kind} filings")
if own.empty:
    why = (" Many companies here make devices, diagnostics or research tools rather than "
           "running drug trials." if label == "CLINICAL" else "")
    st.info(f"{name} has no past {kind} filings to show.{why} Try another type of news.")
else:
    if c["readouts"] < 2:
        source(f"{name} has fewer than two trial readouts, so there is no trial-vs-earnings "
               "comparison for it.")
    CAP = 100
    recent = own.sort_values("t0", ascending=False).head(20).iloc[::-1]   # newest at the top
    labels_y = recent["t0"].dt.strftime("%b %d, %Y")
    # Two filings on the same day would share a label and merge into one bar
    nth = labels_y.groupby(labels_y).cumcount()
    labels_y = labels_y.where(nth == 0, labels_y + " (" + (nth + 1).astype(str) + ")")
    chart_title(
        "How the stock moved on each one",
        f"Day-0 move, green up and red down. Dotted lines: the typical move of ±{r['typical']:.1f}%"
        + ("" if r["use_own"] else " (all San Diego filings)") + ".",
    )
    fig = go.Figure(go.Bar(
        y=labels_y, x=recent["move"].clip(-CAP, CAP), orientation="h",
        marker=dict(color=np.where(recent["move"] > 0, UP_COLOR, DOWN_COLOR), cornerradius=3),
        text=[f"{v:+.1f}%" for v in recent["move"]], textposition="outside", cliponaxis=False,
        textfont=dict(size=12, color=INK),
        customdata=recent["headline"].fillna(""),
        hovertemplate="%{y}: %{text}<br>%{customdata}<extra></extra>",
    ))
    for x in (-r["typical"], r["typical"]):
        fig.add_vline(x=x, line=dict(color=INK_MUTED, width=1, dash="dot"))
    reach = float(min(max(recent["move"].abs().max(), r["typical"]) * 1.25, CAP * 1.2))
    fig.update_xaxes(range=[-reach, reach], ticksuffix="%", zeroline=True,
                     zerolinecolor=INK_MUTED, showgrid=True, gridcolor="rgba(255,255,255,0.08)")
    fig.update_yaxes(title=None, zeroline=False, type="category")
    st.plotly_chart(style(fig, height=90 + 34 * len(recent)), config=PLOTLY_CONFIG, width="stretch")
    if len(own) > len(recent):
        source(f"Showing the {len(recent)} most recent of {len(own)}.")

with st.expander("About these numbers"):
    st.markdown(
        "- **Day-0 move** is market-adjusted: the stock's return on the filing day minus "
        "what the overall market's move would predict for it.\n"
        "- **Typical move** is the median size of that move, up or down. "
        "\"1 in 4\" and \"1 in 10\" are the 75th and 90th percentiles.\n"
        "- Bars beyond ±100% are cut at the edge; the label shows the real move.\n"
        f"- A company needs at least {MIN_OWN_EVENTS} filings of a type to use its own "
        "history; otherwise all San Diego life sciences filings of that type are used.\n"
        "- This describes past moves from 2019–2025. It is not a forecast or investment "
        "advice, and filings of the same type can carry very different amounts of news."
    )
