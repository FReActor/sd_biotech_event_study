"""Event explorer: pick any single announcement and see how the stock reacted."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from charts import PLOTLY_CONFIG, end_label, shade_windows, style
from data import (
    ALL_WINDOWS, LABEL_COLORS, PLACEBO_COLOR, VALID_LABELS,
    load_ar_panel, load_car, load_prices, pct,
)
from ui import article_header, chart_title, source

car = load_car()
panel = load_ar_panel()
prices = load_prices()

article_header(
    kicker="Explore",
    headline="Every filing, one at a time",
    dek=(
        f"Each of the {len(car):,} filings behind the results. Pick one to see how "
        "the stock moved around it, and how much of that move was the news."
    ),
    page=True,
)


def jump_to_event() -> None:
    """Callback for the 'biggest moves' table: select the clicked event.

    Callbacks run before the page script on the next rerun, which is the only
    moment widget values (company, event) may be changed from code.
    """
    rows = st.session_state["big_moves"].selection.rows
    if not rows:
        return
    accession = st.session_state["big_moves_ids"][rows[0]]
    row = car.loc[car["accession"] == accession].iloc[0]
    if row["label"] not in st.session_state.get("ex_labels", []):
        st.session_state["ex_labels"] = st.session_state.get("ex_labels", []) + [row["label"]]
    st.session_state["ex_company"] = row["name"]
    st.session_state["ex_event"] = row["accession"]


# --- filters ------------------------------------------------------------------
# Accession of the event the page opens on: Viking Therapeutics' Feb 27, 2024
# obesity trial readout (VK2735), a well-known move that makes a clear example
DEFAULT_EVENT = "0000950170-24-020616"

if "ex_labels" not in st.session_state:
    first = car[car["accession"] == DEFAULT_EVENT]
    if first.empty:  # fall back to the largest clinical move
        first = car[car["label"] == "CLINICAL"].assign(m=lambda d: d["ar0"].abs()).nlargest(1, "m")
    first = first.iloc[0]
    st.session_state["ex_labels"] = [first["label"]]
    st.session_state["ex_company"] = first["name"]
    st.session_state["ex_event"] = first["accession"]

labels = st.multiselect(
    "Event types", VALID_LABELS, key="ex_labels", format_func=str.title,
)
pool = car[car["label"].isin(labels or VALID_LABELS)]

companies = pool.groupby("name").size().sort_index()
if st.session_state.get("ex_company") not in companies.index:
    st.session_state["ex_company"] = companies.index[0]
f2, f3 = st.columns(2)
company = f2.selectbox(
    "Company", companies.index, key="ex_company",
    format_func=lambda n: f"{n.title()} ({companies[n]})",
)

events = pool[pool["name"] == company].sort_values("t0", ascending=False)
event_ids = events["accession"].tolist()
if st.session_state.get("ex_event") not in event_ids:
    st.session_state["ex_event"] = event_ids[0]
lookup = events.set_index("accession")
event_id = f3.selectbox(
    "Announcement", event_ids, key="ex_event",
    format_func=lambda a: (
        f"{lookup.at[a, 't0']:%Y-%m-%d} · {lookup.at[a, 'label'].title()} · "
        f"day 0 {pct(lookup.at[a, 'ar0'], 1)}"
    ),
)
ev = lookup.loc[event_id]
ticker = ev["ticker"]

# --- headline numbers -----------------------------------------------------
st.subheader(f"{company.title()} ({ticker}) · {ev['label'].title()} · {ev['t0']:%B %d, %Y}")
m = st.columns(4)
m[0].metric("Day 0", pct(ev["ar0"], 1), help="Abnormal return on the filing day")
m[1].metric("Before", pct(ev["car_leak"], 1), help="Days −10 to −2")
m[2].metric("After", pct(ev["car_drift"], 1), help="Days +2 to +10")
m[3].metric("Beta", f"{ev['beta']:.2f}", help="Sensitivity to the S&P 500")

notes = []
if bool(ev.get("after_hours")):
    notes.append("Filed after the 4 pm close, so day 0 is the next trading day.")
if isinstance(ev.get("items"), str):
    notes.append(f"8-K items: {ev['items']}.")
if ev.get("filing_url"):
    notes.append(f"[Read the filing on SEC EDGAR]({ev['filing_url']})")
st.caption("  ".join(notes))

# --- price chart --------------------------------------------------------------
spy = prices[prices["ticker"] == "SPY"].set_index("date")["adj_close"]
stock = prices[prices["ticker"] == ticker].set_index("date")["adj_close"].reindex(spy.index)
days = spy.index
t0_idx = days.searchsorted(ev["t0"])
lo, hi = max(t0_idx - 30, 0), min(t0_idx + 21, len(days))
window = pd.DataFrame({
    "offset": range(lo - t0_idx, hi - t0_idx),
    "date": days[lo:hi],
    "stock": stock.iloc[lo:hi].to_numpy(),
    "spy": spy.iloc[lo:hi].to_numpy(),
})
base = window.loc[window["offset"] == -1]
if not base.empty and base["stock"].notna().all():
    window["stock_idx"] = window["stock"] / base["stock"].iloc[0] * 100
    window["spy_idx"] = window["spy"] / base["spy"].iloc[0] * 100

    price_fig = go.Figure()
    price_fig.add_trace(go.Scatter(
        x=window["offset"], y=window["spy_idx"], name="S&P 500",
        line=dict(color=PLACEBO_COLOR, width=2, dash="dash"),
        customdata=window["date"].dt.strftime("%Y-%m-%d"),
        hovertemplate="%{customdata}<br>SPY %{y:.1f}<extra></extra>",
    ))
    price_fig.add_trace(go.Scatter(
        x=window["offset"], y=window["stock_idx"], name=ticker,
        line=dict(color=LABEL_COLORS[ev["label"]], width=2),
        customdata=window[["date", "stock"]].assign(date=lambda d: d["date"].dt.strftime("%Y-%m-%d")),
        hovertemplate="%{customdata[0]}<br>" + ticker + " %{y:.1f} ($%{customdata[1]:.2f})<extra></extra>",
    ))
    last = window.dropna(subset=["stock_idx"]).iloc[-1]
    end_label(price_fig, last["offset"], last["stock_idx"], ticker, LABEL_COLORS[ev["label"]])
    end_label(price_fig, last["offset"], last["spy_idx"], "S&P 500", PLACEBO_COLOR)
    shade_windows(price_fig, {"Before": (-10, -2), "After": (2, 10)})
    price_fig.update_layout(hovermode="x unified", margin=dict(r=70))
    price_fig.update_xaxes(title="Trading days from the filing", dtick=5)
    price_fig.update_yaxes(title=None, zeroline=False)

chart_title(f"{ticker} vs. the market", "Share price, indexed to 100 the day before the filing")
if base.empty or base["stock"].isna().any():
    st.warning("Price data is missing around this date.")
else:
    st.plotly_chart(style(price_fig, height=340), config=PLOTLY_CONFIG, width="stretch")

# --- abnormal return bars -----------------------------------------------------
ar = panel[panel["accession"] == event_id].sort_values("offset")
bars = go.Figure(go.Bar(
    x=ar["offset"], y=ar["ar"] * 100,
    marker=dict(color=LABEL_COLORS[ev["label"]], cornerradius=3),
    hovertemplate="Day %{x:+d}<br>AR %{y:.2f}%<extra></extra>",
))
shade_windows(bars, {"Before": (-10, -2), "After": (2, 10)}, labels=False)
bars.update_xaxes(title="Trading days from the filing", dtick=2)
bars.update_yaxes(title=None, ticksuffix="%")
chart_title("How much of each day's move was the news", "Daily abnormal return: the return beyond what the market predicted, %")
st.plotly_chart(style(bars, height=300), config=PLOTLY_CONFIG, width="stretch")

with st.expander("How the abnormal return is computed for this event"):
    st.markdown(
        f"A market model is fitted on this stock's returns from trading day "
        f"−250 to −31 ({int(ev['n_est'])} usable days):"
    )
    st.latex(
        rf"\hat R_{{{ticker},t}} = {ev['alpha']:+.4f} + {ev['beta']:.2f}\,R_{{SPY,t}}"
        rf"\qquad \sigma_\varepsilon = {ev['resid_sd'] * 100:.2f}\%"
    )
    st.markdown(
        "The abnormal return on each day is the actual return minus this "
        "prediction. Summing abnormal returns over a window gives the CAR."
    )
    st.dataframe(
        pd.DataFrame(
            [(formal, short, pct(ev[col])) for col, (short, formal, _) in ALL_WINDOWS.items()],
            columns=["Window", "Meaning", "Value"],
        ),
        hide_index=True, width="stretch",
    )

# --- biggest moves ------------------------------------------------------------
st.header("The biggest day-zero moves")
source("Click a row to open that filing above.")
top = (
    pool.assign(abs_ar0=pool["ar0"].abs())
    .nlargest(15, "abs_ar0")
    .reset_index(drop=True)
)
table = pd.DataFrame({
    "Date": top["t0"].dt.strftime("%Y-%m-%d"),
    "Company": top["name"].str.title(),
    "Ticker": top["ticker"],
    "Type": top["label"].str.title(),
    "Day 0 %": (top["ar0"] * 100).round(1),
    "After %": (top["car_drift"] * 100).round(1),
})
st.session_state["big_moves_ids"] = top["accession"].tolist()
st.dataframe(
    table, hide_index=True, width="stretch",
    on_select=jump_to_event, selection_mode="single-row", key="big_moves",
    column_config={
        "Day 0 %": st.column_config.NumberColumn(format="%+.1f"),
        "After %": st.column_config.NumberColumn(format="%+.1f"),
    },
)
