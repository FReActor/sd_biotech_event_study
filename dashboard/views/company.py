"""Company profile: price history with every filing, and any single filing up close."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from plotly.subplots import make_subplots

from charts import PLOTLY_CONFIG, style
from data import BG, INK, INK_MUTED, PLACEBO_COLOR, load_prices
from product import LABEL_NAMES, load_companies, load_events
from ui import (DOWN_COLOR, UP_COLOR, chart_title, color_moves, company_picker, page_intro,
                quote, source, stat_strip)

# Filing groups offered in the type filter
GROUPS = {
    "ALL": ("All", None),
    "CLINICAL": ("Clinical", ["CLINICAL"]),
    "EARNINGS": ("Earnings", ["EARNINGS"]),
    "OTHER_NEWS": ("Other", ["REGULATORY", "PRESENTATION", "OTHER"]),
}

ev = load_events()
comp = load_companies().sort_values("company").set_index("ticker")
prices = load_prices()

# --- which company ---------------------------------------------------------------------
# The ticker lives in the URL (?ticker=VKTX), so every company has its own link.
top_left, top_right = st.columns([4, 1], vertical_alignment="bottom")
ticker = company_picker(comp, key="company_ticker", container=top_left)
if top_right.button("Risk check →", width="stretch"):
    st.switch_page("views/risk.py", query_params={"ticker": ticker})

c = comp.loc[ticker]
mine = ev[ev["ticker"] == ticker]

page_intro(f"{c['company']} ({ticker})", " · ".join(x for x in [c["sic_desc"], c["city"]] if x))

best = mine.loc[mine["move"].idxmax()]
stat_strip([
    (f"{int(c['events'])}", "filings tracked"),
    (f"{int(c['readouts'])}", "trial readouts"),
    (f"±{c['readout_move']:.1f}%" if c["readouts"] else "–", "typical trial-day move"),
    (f"±{c['earnings_move']:.1f}%" if c["earnings"] else "–", "typical earnings move"),
    (f"{best['move']:+.0f}%", "biggest one-day gain", f"{best['t0']:%b %Y} · {LABEL_NAMES[best['label']]}"),
])

# --- price chart, styled like a brokerage app ------------------------------------------------
RANGES = {"1M": 30, "6M": 182, "1Y": 365, "3Y": 3 * 365, "5Y": 5 * 365, "Max": None}

px_all = prices[(prices["ticker"] == ticker) & (prices["date"] >= "2019-01-01")].sort_values("date")
r1, r2 = st.columns([3, 2], vertical_alignment="bottom")
span = r1.segmented_control("Range", list(RANGES), default="Max", required=True, key="co_range")
group = r2.segmented_control(
    "Mark filings", list(GROUPS), default="ALL", required=True,
    format_func=lambda g: GROUPS[g][0], key="co_group",
)
labels = GROUPS[group][1]
shown = mine if labels is None else mine[mine["label"].isin(labels)]

end_date = px_all["date"].max()
days = RANGES[span]
px = px_all if days is None else px_all[px_all["date"] >= end_date - pd.Timedelta(days=days)]
first, last = px["adj_close"].iloc[0], px["adj_close"].iloc[-1]
change = last / first - 1
line_color = UP_COLOR if change >= 0 else DOWN_COLOR
fill_color = "rgba(52,168,98,0.14)" if change >= 0 else "rgba(240,90,79,0.14)"
period = {"1M": "past month", "6M": "past 6 months", "1Y": "past year",
          "3Y": "past 3 years", "5Y": "past 5 years",
          "Max": f"since {px['date'].iloc[0]:%b %Y}"}[span]
quote(
    price=f"${last:,.2f}",
    change=f"{change * 100:+.1f}% ({'+' if last >= first else '−'}${abs(last - first):,.2f})",
    period=period,
    note=f"Close on {end_date:%b %d, %Y} · split- and dividend-adjusted",
)

in_range = shown[(shown["t0"] >= px["date"].iloc[0]) & (shown["t0"] <= end_date)]
close_by_date = px_all.set_index("date")["adj_close"]

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.8, 0.2],
                    vertical_spacing=0.03)
fig.add_trace(go.Scatter(
    x=px["date"], y=px["adj_close"], mode="lines", fill="tozeroy",
    line=dict(color=line_color, width=2), fillcolor=fill_color, name="Price",
    hovertemplate="$%{y:.2f}<extra></extra>",
), row=1, col=1)
if len(in_range):
    fig.add_trace(go.Scatter(
        x=in_range["t0"], y=close_by_date.reindex(in_range["t0"]).to_numpy(),
        mode="markers", name="Filing",
        marker=dict(size=7, color=BG, line=dict(color=INK, width=1.5)),
        customdata=np.stack([in_range["label"].map(LABEL_NAMES), in_range["move"]], axis=1),
        hovertemplate="%{customdata[0]} filing · day-0 move %{customdata[1]:+.1f}%<extra></extra>",
    ), row=1, col=1)
fig.add_trace(go.Bar(
    x=px["date"], y=px["volume"], marker=dict(color="rgba(255,255,255,0.22)"), name="Volume",
    hovertemplate="Volume %{y:,.0f}<extra></extra>",
), row=2, col=1)
fig.add_hline(y=first, line=dict(color=INK_MUTED, width=1, dash="dot"), row=1, col=1)
lo, hi = px["adj_close"].min(), px["adj_close"].max()
pad = (hi - lo) * 0.08 or hi * 0.05
fig.update_yaxes(range=[max(lo - pad, 0), hi + pad], tickprefix="$", side="right",
                 zeroline=False, title=None, row=1, col=1)
fig.update_yaxes(showticklabels=False, showgrid=False, zeroline=False, title=None, row=2, col=1)
fig.update_xaxes(title=None, showspikes=True, spikemode="across", spikethickness=1,
                 spikedash="dot", spikecolor=INK_MUTED)
fig.update_layout(hovermode="x unified", bargap=0)
st.plotly_chart(style(fig, height=420), config=PLOTLY_CONFIG, width="stretch")
source("Circles mark filings; hover for the day's move. Gray bars: trading volume. "
       "Dotted line: price at the start of the range.")

# --- filing list -------------------------------------------------------------------------------
st.header("Filings")
listing = shown.reset_index(drop=True)
if listing.empty:
    st.info("No filings of this type.")
    st.stop()
table = pd.DataFrame({
    "Date": listing["t0"],
    "Type": listing["label"].map(LABEL_NAMES),
    "Headline": listing["headline"].fillna("–"),
    "Day 0": listing["move"],
    "After": listing["after"],
})
source("Click a filing to see it up close. Types other than earnings were labelled by AI.")
sel = st.dataframe(
    color_moves(table, ["Day 0", "After"],
                {"Date": "{:%b %d, %Y}", "Day 0": "{:+.1f}%", "After": "{:+.1f}%"}),
    hide_index=True, width="stretch", height=300,
    on_select="rerun", selection_mode="single-row", key=f"co_table_{ticker}_{group}",
    column_config={
        "Date": st.column_config.Column(width="small"),
        "Type": st.column_config.Column(width="small"),
        "Headline": st.column_config.Column(width="large"),
        "Day 0": st.column_config.Column(width="small", help="Market-adjusted move on the filing day"),
        "After": st.column_config.Column(width="small", help="Days +2 to +10"),
    },
)
row = listing.loc[sel.selection.rows[0]] if sel.selection.rows else listing.loc[listing["abs_move"].idxmax()]

# --- one filing up close -------------------------------------------------------------------------
st.header("Up close")
st.markdown(
    f"**{row['t0']:%B %d, %Y} · {LABEL_NAMES[row['label']]}**"
    + ("" if sel.selection.rows else " · the biggest move on record")
)
if isinstance(row["headline"], str):
    st.caption(row["headline"])
stat_strip([
    (f"{row['move']:+.1f}%", "day 0"),
    (f"{row['car_leak'] * 100:+.1f}%", "10 days before"),
    (f"{row['after']:+.1f}%", "10 days after"),
])

# Same look as the price chart above: % change from the close before the filing,
# green or red area, dotted baseline, price axis on the right, circle on the filing.
spy = prices[prices["ticker"] == "SPY"].set_index("date")["adj_close"]
stock = prices[prices["ticker"] == ticker].set_index("date")["adj_close"].reindex(spy.index)
i0 = spy.index.searchsorted(row["t0"])
lo, hi = max(i0 - 30, 0), min(i0 + 21, len(spy))
win = pd.DataFrame({
    "date": spy.index[lo:hi],
    "offset": np.arange(lo - i0, hi - i0),
    "stock": stock.iloc[lo:hi].to_numpy(),
    "spy": spy.iloc[lo:hi].to_numpy(),
})
base = win.loc[win["offset"] == -1]
if not base.empty and base["stock"].notna().all():
    win["stock_pct"] = (win["stock"] / base["stock"].iloc[0] - 1) * 100
    win["spy_pct"] = (win["spy"] / base["spy"].iloc[0] - 1) * 100
    end_pct = win["stock_pct"].dropna().iloc[-1]
    up = end_pct >= 0
    f2 = go.Figure()
    f2.add_trace(go.Scatter(
        x=win["date"], y=win["stock_pct"], mode="lines", name=ticker, fill="tozeroy",
        line=dict(color=UP_COLOR if up else DOWN_COLOR, width=2),
        fillcolor="rgba(52,168,98,0.14)" if up else "rgba(240,90,79,0.14)",
        customdata=win["stock"],
        hovertemplate=ticker + " %{y:+.1f}% ($%{customdata:.2f})<extra></extra>",
    ))
    f2.add_trace(go.Scatter(
        x=win["date"], y=win["spy_pct"], mode="lines", name="S&P 500",
        line=dict(color=PLACEBO_COLOR, width=1.5, dash="dot"),
        hovertemplate="S&P 500 %{y:+.1f}%<extra></extra>",
    ))
    day0 = win.loc[win["offset"] == 0]
    if not day0.empty:
        f2.add_trace(go.Scatter(
            x=day0["date"], y=day0["stock_pct"], mode="markers", name="Filing",
            marker=dict(size=9, color=BG, line=dict(color=INK, width=2)),
            hovertemplate="Filing day<extra></extra>", showlegend=False,
        ))
        f2.add_vline(x=day0["date"].iloc[0], line=dict(color=INK_MUTED, width=1, dash="dot"))
    f2.add_hline(y=0, line=dict(color=INK_MUTED, width=1, dash="dot"))
    f2.update_yaxes(ticksuffix="%", side="right", zeroline=False, title=None)
    f2.update_xaxes(title=None, showspikes=True, spikemode="across", spikethickness=1,
                    spikedash="dot", spikecolor=INK_MUTED)
    f2.update_layout(hovermode="x unified")
    chart_title(f"{ticker} vs. the market",
                "% change from the close before the filing (dotted line), "
                "30 trading days before to 20 after")
    st.plotly_chart(style(f2, height=340, legend=True), config=PLOTLY_CONFIG, width="stretch")
else:
    st.info("Price data is missing around this date.")

links = []
if row.get("filing_url"):
    links.append(f"[Read the filing on SEC EDGAR ↗]({row['filing_url']})")
links.append("Labelled by Claude Haiku" if row["source"] == "AI" else "Earnings (Item 2.02)")
st.caption(" · ".join(links))
