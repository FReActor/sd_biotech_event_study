"""Home: look up a company, see who gains most on news, compare trial vs earnings days."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from charts import PLOTLY_CONFIG, style
from data import INK_MUTED, LABEL_COLORS
from product import APP_NAME, LABEL_NAMES, TAGLINE, load_companies, load_events
from ui import chart_title, color_moves, hero_intro, source, stat_strip

ev = load_events()
comp = load_companies().sort_values("company")
names = comp.set_index("ticker")["company"]

hero_intro(
    kicker=APP_NAME,
    title=TAGLINE,
    subtitle=(
        f"Every 8-K filed by {len(comp)} San Diego life sciences companies since 2019, "
        "sorted by AI and matched to how the stock reacted that day."
    ),
)

# --- search ----------------------------------------------------------------------
pick = st.selectbox(
    "Look up a company", comp["ticker"], index=None,
    placeholder=f"Search {len(comp)} companies by name or ticker…",
    format_func=lambda t: f"{names[t]} ({t})", label_visibility="collapsed",
)
if pick:
    st.switch_page("views/company.py", query_params={"ticker": pick})

clinical = ev[ev["label"] == "CLINICAL"]
earnings = ev[ev["label"] == "EARNINGS"]
stat_strip([
    (f"{len(comp)}", "companies"),
    (f"{len(ev):,}", "filings measured"),
    (f"{len(clinical)}", "trial readouts"),
    (f"±{clinical['abs_move'].median():.1f}%", "typical trial-day move",
     f"vs ±{earnings['abs_move'].median():.1f}% on earnings"),
])

# --- who increases the most ----------------------------------------------------------
st.header("Who increases the most")

c1, c2, c3 = st.columns([5, 5, 3])
kind = c1.segmented_control(
    "News type", ["CLINICAL", "EARNINGS", "ALL"], default="CLINICAL", required=True,
    format_func=lambda k: {"ALL": "Any filing"}.get(k, LABEL_NAMES.get(k, k)),
    key="screen_kind",
)
rank = c2.segmented_control(
    "Rank by", ["best", "avg"], default="best", required=True, key="screen_rank",
    format_func={"best": "Biggest one-day gain", "avg": "Average change"}.get,
)
min_n = c3.selectbox("Minimum filings", [1, 3, 5], index=1, key="screen_min",
                     format_func=lambda n: f"{n}+")

sub = ev if kind == "ALL" else ev[ev["label"] == kind]
g = sub.groupby("ticker")["move"]
board = pd.DataFrame({
    "filings": g.size(),
    "best": g.max(),
    "avg": g.mean(),
    "up": g.apply(lambda s: (s > 0).mean() * 100),
})
best_rows = sub.loc[g.idxmax()].set_index("ticker")
board["best_date"] = best_rows["t0"]
board = board[board["filings"] >= min_n].sort_values(rank, ascending=False).reset_index()
board["company"] = board["ticker"].map(names)

# All columns stay visible; "Rank by" only changes the sort order.
table = pd.DataFrame({
    "Company": board["company"] + " (" + board["ticker"] + ")",
    "Biggest gain": board["best"],
    "On": board["best_date"],
    "Average change": board["avg"],
    "Up days": board["up"],
    "Filings": board["filings"],
})
moves = ["Biggest gain", "Average change"]
formats = {"Biggest gain": "{:+.1f}%", "On": "{:%b %Y}",
           "Average change": "{:+.1f}%", "Up days": "{:.0f}%"}
helps = {
    "Biggest gain": "Largest one-day rise after a filing of this type",
    "On": "When that rise happened",
    "Average change": "Mean day-0 move across these filings, up or down",
    "Up days": "Share of these filings the stock rose on",
    "Filings": "Number of filings of this type",
}

source(
    f"{len(board)} companies, sorted by "
    + ("biggest one-day gain" if rank == "best" else "average change")
    + " · day-0 move, adjusted for the overall market · click a row to open the company"
)
sel = st.dataframe(
    color_moves(table, moves, formats), hide_index=True, width="stretch", height=390,
    on_select="rerun", selection_mode="single-row", key=f"screen_table_{rank}",
    column_config={
        "Company": st.column_config.Column(width="large"),
        **{col: st.column_config.Column(help=text) for col, text in helps.items()},
    },
)
if sel.selection.rows:
    st.switch_page("views/company.py",
                   query_params={"ticker": board.at[sel.selection.rows[0], "ticker"]})

# --- trial news vs earnings ---------------------------------------------------------------
st.header("Trial news vs. earnings")
both = comp[(comp["readouts"] >= 2) & (comp["earnings"] >= 2)]
top = both.nlargest(12, "readout_move").iloc[::-1]   # reversed: largest at the top

chart_title(
    "For these companies, trial news moves the stock far more than earnings",
    f"Typical size of the day-0 move. Top 12 of {len(both)} companies with at least "
    "two trial readouts and two earnings reports. Click a bar to open the company.",
)
fig = go.Figure()
for col, lab, name in [("earnings_move", "EARNINGS", "Earnings"),
                       ("readout_move", "CLINICAL", "Trial readouts")]:
    fig.add_trace(go.Bar(
        y=top["company"], x=top[col], name=name, orientation="h",
        marker=dict(color=LABEL_COLORS[lab], cornerradius=3),
        text=[f"±{v:.0f}%" for v in top[col]], textposition="outside",
        textfont=dict(size=11, color=INK_MUTED), cliponaxis=False,
        customdata=top[["ticker"]],
        hovertemplate="%{y}<br>" + name + ": ±%{x:.1f}%<extra></extra>",
    ))
fig.update_layout(barmode="group", bargap=0.28, bargroupgap=0.08,
                  legend=dict(traceorder="reversed"))
fig.update_xaxes(ticksuffix="%", title=None, showgrid=True, gridcolor="rgba(255,255,255,0.08)",
                 range=[0, float(top["readout_move"].max()) * 1.15])
fig.update_yaxes(title=None, zeroline=False, tickfont=dict(size=12))
event = st.plotly_chart(
    style(fig, height=560, legend=True), config=PLOTLY_CONFIG, width="stretch",
    on_select="rerun", selection_mode="points", key="screen_bars",
)
points = event.selection.points if event else []
if points and points[0].get("customdata"):
    st.switch_page("views/company.py", query_params={"ticker": points[0]["customdata"][0]})
