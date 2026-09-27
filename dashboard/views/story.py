"""The story: the study told as a data-journalism article.

Structure
  1. A concrete opening: two San Diego stocks on Feb. 27, 2024
  2. The question, and the three windows used to test it
  3. The event-time chart: the move happens on day zero
  4. The three tests against fake announcement dates
  5. Why the median: most trials disappoint, a few change everything
  6. How it was built, with links to the other pages
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from charts import PLOTLY_CONFIG, end_label, note, shade_windows, style
from data import (
    BG, BONFERRONI, INK, INK_MUTED, LABEL_COLORS, MAIN_LABELS, PAPER_URL,
    PLACEBO_COLOR, REPO_URL, WINDOWS, event_time_path, fmt_p, funnel_counts,
    load_car, load_manual_labels, load_prices, placebo_test,
)
from ui import narrow, article_header, big_numbers, chart_title, source, three_windows

narrow()

car = load_car()
counts = funnel_counts()
prices = load_prices()
clinical = car[car["label"] == "CLINICAL"]
earnings = car[car["label"] == "EARNINGS"]

# --- headline -----------------------------------------------------------------
article_header(
    kicker="San Diego biotech · An event study",
    headline="Wall Street prices a drug trial in a day",
    dek=(
        "Clinical trial results are dense, technical and hard to judge. You might "
        "expect investors to need days to work them out. Across "
        f"{counts['events_with_car']:,} filings from {counts['final_firms']} San Diego "
        "life sciences companies, they didn't."
    ),
    byline=(
        "By <b>Charles Cheng</b> · B.S. Applied Mathematics, UC San Diego · "
        f'<a href="{PAPER_URL}" target="_blank">Read the paper</a> · '
        f'<a href="{REPO_URL}" target="_blank">Code</a>'
    ),
)

# --- 1. the opening example ------------------------------------------------------
EVENT_DAY = pd.Timestamp("2024-02-27")


def stock_path(ticker: str) -> pd.DataFrame:
    """Close prices around Feb. 27, 2024, indexed to 100 on the day before."""
    s = prices[prices["ticker"] == ticker].set_index("date")["adj_close"].sort_index()
    i = s.index.searchsorted(EVENT_DAY)
    window = s.iloc[i - 20: i + 21]
    base = s.iloc[i - 1]
    return pd.DataFrame({"date": window.index, "close": window.values,
                         "index": window.values / base * 100})


vktx, janx, spy = stock_path("VKTX"), stock_path("JANX"), stock_path("SPY")
vktx_move = vktx.loc[vktx["date"] == EVENT_DAY, "index"].iloc[0] - 100
janx_move = janx.loc[janx["date"] == EVENT_DAY, "index"].iloc[0] - 100
vktx_before = vktx.loc[vktx["date"] < EVENT_DAY, "close"].iloc[-1]
vktx_after = vktx.loc[vktx["date"] == EVENT_DAY, "close"].iloc[0]

st.markdown(
    "Before the opening bell on Feb. 27, 2024, Viking Therapeutics posted results "
    "from a mid-stage trial of its obesity drug. By the close, its stock had gone "
    f"from **\\${vktx_before:.2f} to \\${vktx_after:.2f}**. A few miles away, Janux "
    "Therapeutics, which had released early clinical data the evening before, "
    f"closed the same day up **{janx_move:.0f}%**."
)

chart_title(
    "Two San Diego stocks, one trading day",
    "Share price, indexed to 100 at the close on Feb. 26, 2024",
)
fig = go.Figure()
for df, name, color, dash, width in [
    (spy, "S&P 500", PLACEBO_COLOR, "dot", 1.5),
    (janx, "Janux", INK, "solid", 2),
    (vktx, "Viking", LABEL_COLORS["CLINICAL"], "solid", 2.5),
]:
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["index"], name=name, mode="lines",
        line=dict(color=color, width=width, dash=dash),
        customdata=df["close"],
        hovertemplate=name + ": %{y:.0f} ($%{customdata:.2f})<extra></extra>",
    ))
    end_label(fig, df["date"].iloc[-1], df["index"].iloc[-1], name, color)
note(fig, EVENT_DAY, 100 + janx_move, f"Janux +{janx_move:.0f}%", ax=-70, ay=0, align="right")
note(fig, EVENT_DAY, 100 + vktx_move, f"Viking +{vktx_move:.0f}%", ax=-70, ay=10, align="right")
fig.update_yaxes(title=None, rangemode="tozero")
fig.update_xaxes(tickformat="%b %d")
fig.update_layout(margin=dict(r=60), hovermode="x unified")
st.plotly_chart(style(fig, height=360), config=PLOTLY_CONFIG, width="stretch")
source("Source: Yahoo Finance daily adjusted closes.")

st.markdown(
    "Days like that are why biotech investors watch trial calendars so closely. "
    "They also raise an old question in finance: **when news is hard to "
    "understand, does the market get it right away, or does the price keep "
    "adjusting for days while investors catch up?**"
)

# --- 2. the question -------------------------------------------------------------
st.header("What slow digestion would look like")
st.markdown(
    "If the market struggles with complex news, it should show up on one side of "
    "the announcement or the other. Prices would **drift** in the days after, as "
    "investors slowly work out what the results mean. Or, if some people "
    "understood the science sooner than others, prices would start moving "
    "**before** the filing."
)
three_windows()
st.markdown(
    "To test both, I measured each stock's move in these windows against what "
    "the overall market predicted for it, and compared clinical trial readouts "
    "with quarterly earnings reports, which are about as standardized as company "
    "news gets."
)

# --- 3. event-time chart ---------------------------------------------------------
st.header("The move happens on day zero")

view = st.segmented_control(
    "Show", ["Typical event", "Average event"], default="Typical event",
    key="story_stat", required=True,
)
stat = "median" if view == "Typical event" else "mean"
path = event_time_path(stat)
cl = path[path["label"] == "CLINICAL"].set_index("offset")["car"] * 100
er = path[path["label"] == "EARNINGS"].set_index("offset")["car"] * 100

if stat == "median":
    chart_title(
        "The drop comes on day zero, not after",
        f"Median cumulative abnormal return, {len(clinical)} clinical readouts and "
        f"{len(earnings)} earnings reports, %",
    )
else:
    chart_title(
        "The average is pulled around by a few huge moves",
        f"Mean cumulative abnormal return, {len(clinical)} clinical readouts and "
        f"{len(earnings)} earnings reports, %",
    )

fig = go.Figure()
for series, lab, name in [(er, "EARNINGS", "Earnings"), (cl, "CLINICAL", "Clinical")]:
    fig.add_trace(go.Scatter(
        x=series.index, y=series.values, name=name, mode="lines+markers",
        line=dict(color=LABEL_COLORS[lab], width=2.5), marker=dict(size=5),
        hovertemplate=f"{name}, day %{{x:+d}}: %{{y:.2f}}%<extra></extra>",
    ))
    end_label(fig, series.index[-1], series.iloc[-1], name, LABEL_COLORS[lab])
shade_windows(fig, {"Before": (-10, -2), "After": (2, 10)})
if stat == "median":
    note(fig, 1, cl.loc[1], f"Days 0–1: {cl.loc[1] - cl.loc[-1]:+.1f} pts", ax=50, ay=35)
    note(fig, 6, cl.loc[6], "Days 2–10: no sustained drift", ax=0, ay=42, arrow=False)
fig.update_xaxes(title="Trading days from the filing", dtick=2, range=[-10.6, 10.6])
fig.update_yaxes(title=None, ticksuffix="%")
fig.update_layout(margin=dict(r=70), hovermode="x unified")
st.plotly_chart(style(fig, height=380), config=PLOTLY_CONFIG, width="stretch")
source(
    "Abnormal return = the stock's return minus what a market model fitted on "
    "its prior year predicts. Each event's path is built first, then aggregated."
)

st.markdown(
    "For the typical clinical readout, the reaction lands on the day of the "
    "filing and the next. After that there's no sustained slide as investors "
    "catch up; the wiggles that remain are the size of ordinary noise. Before the filing, clinical stocks track earnings "
    "stocks closely, with no sign of an early move."
)

# --- 4. the tests ---------------------------------------------------------------
st.header("Only day zero stands out from chance")
st.markdown(
    "Small biotech stocks drift on their own, so a raw number isn't enough. For "
    "each real filing I drew **20 fake announcement dates** for the same stock "
    "in the same month, and ran them through the identical pipeline. A real "
    "effect has to beat that noise."
)

label = st.segmented_control(
    "Event type", MAIN_LABELS, default="CLINICAL", format_func=str.title,
    key="story_label", required=True,
)
rows = []
for column, (short, formal, _) in WINDOWS.items():
    res = placebo_test(label, column)
    name = {"car_leak": "Before", "ar0": "Day 0", "car_drift": "After"}[column]
    verdict = "stands out" if res["p"] < BONFERRONI else "within chance"
    rows.append({
        "tick": f"<b>{name}</b><br>p {fmt_p(res['p'])} · {verdict}",
        "real": res["observed"] * 100, "fake": res["placebo"] * 100,
        "n": res["n_real"],
    })
tests = pd.DataFrame(rows)

chart_title(
    f"{label.title()} filings vs. fake dates",
    f"Median abnormal return, % · filled dot: {tests['n'].iloc[0]} real filings · "
    "open circle: fake dates",
)
fig = go.Figure()
for _, r in tests.iterrows():
    fig.add_trace(go.Scatter(
        x=[r["fake"], r["real"]], y=[r["tick"], r["tick"]], mode="lines",
        line=dict(color="rgba(255,255,255,0.22)", width=3), hoverinfo="skip",
    ))
fig.add_trace(go.Scatter(
    x=tests["fake"], y=tests["tick"], mode="markers", name="Fake dates",
    marker=dict(size=13, color=BG, line=dict(color=INK_MUTED, width=2)),
    hovertemplate="Fake dates: %{x:.2f}%<extra></extra>",
))
fig.add_trace(go.Scatter(
    x=tests["real"], y=tests["tick"], mode="markers", name="Real filings",
    marker=dict(size=15, color=LABEL_COLORS[label], line=dict(color=BG, width=2)),
    hovertemplate="Real filings: %{x:.2f}%<extra></extra>",
))
fig.update_yaxes(autorange="reversed", zeroline=False, showgrid=False,
                 tickfont=dict(size=12, color=INK))
fig.update_xaxes(ticksuffix="%", zeroline=True, zerolinecolor="rgba(255,255,255,0.3)",
                 showgrid=True, gridcolor="rgba(255,255,255,0.08)")
st.plotly_chart(style(fig, height=280), config=PLOTLY_CONFIG, width="stretch")
source(
    "p-values: two-sided, from 10,000 resamples of the fake dates. "
    f"“Stands out” means p < {BONFERRONI:.4f} (0.05 split across three tests)."
)

if label == "CLINICAL":
    st.markdown(
        "For clinical readouts, only the announcement day is clearly different from "
        "the fake dates. The *before* window comes closest (p = 0.06), but not close "
        "enough once you account for running three tests. The *after* window is "
        "indistinguishable from noise."
    )
else:
    st.markdown(
        "Switch back to **Clinical** for the main result. Earnings and regulatory "
        "filings run through the same test show no significant drift either."
    )

# --- 5. distribution -------------------------------------------------------------
st.header("Most trials disappoint. A few change everything.")

ar0 = clinical["ar0"].dropna() * 100
er0 = earnings["ar0"].dropna() * 100
big_numbers([
    (f"{(ar0 < 0).mean():.0%}", "of clinical readouts sent the stock down on the day"),
    (f"{(ar0.abs() > 20).mean():.0%}",
     f"moved it more than 20% in a single day, against {(er0.abs() > 20).mean():.0%} of earnings reports"),
    (f"{ar0.mean():+.1f}%", f"average day-zero move, though the typical one was {ar0.median():+.1f}%"),
])

clipped = ar0[(ar0 > -30) & (ar0 < 30)]
chart_title(
    "Day-zero moves, clinical readouts",
    f"Abnormal return on the filing day, %, {len(ar0)} readouts",
)
fig = go.Figure(go.Histogram(
    x=clipped, xbins=dict(start=-30, end=30, size=2),
    marker=dict(color=LABEL_COLORS["CLINICAL"], line=dict(color=BG, width=1)),
    hovertemplate="%{x}%: %{y} readouts<extra></extra>",
))
for value, name, shift in [(ar0.median(), "Typical", "left"), (ar0.mean(), "Average", "right")]:
    fig.add_vline(x=value, line_color=INK, line_width=1.5,
                  line_dash="dot" if name == "Typical" else "dash")
    fig.add_annotation(
        x=value, y=1, yref="paper", text=f"{name} {value:+.1f}%", showarrow=False,
        xanchor="right" if shift == "left" else "left", xshift=-4 if shift == "left" else 4,
        yanchor="top", font=dict(size=12, color=INK),
    )
fig.update_xaxes(ticksuffix="%", title=None)
fig.update_yaxes(title=None)
st.plotly_chart(style(fig, height=300), config=PLOTLY_CONFIG, width="stretch")
source(
    f"{(ar0 >= 30).sum()} readouts rose more than 30% and {(ar0 <= -30).sum()} fell "
    "more than 30%; they are off the edges of this chart."
)

st.markdown(
    "Most readouts are small letdowns. A handful are enormous wins, like Viking and "
    "Janux, big enough to drag the average up even though the typical stock fell. "
    "That lopsidedness is why every test here uses the **median**: it describes "
    "the typical filing instead of the rare blowout."
)

# --- 6. how it was built --------------------------------------------------------
st.header("How this was built")
manual = load_manual_labels()
agreement = (manual["my_label"] == manual["llm_label"]).mean()
st.markdown(
    f"I scanned all **{counts['edgar_filers']:,}** companies that file with the SEC "
    f"to find **{counts['final_firms']}** San Diego life sciences firms, then "
    f"collected their **{counts['filings_8k']:,}** 8-K filings from 2019 to 2025. "
    "Because trial results, investor decks and financings all arrive under the "
    "same filing items, I had **Claude Haiku** read each one and sort it into "
    "clinical, regulatory, presentation or other. On 100 filings I labelled by "
    f"hand, it agreed with me **{agreement:.0%}** of the time (Cohen's kappa 0.817)."
)

c1, c2, c3 = st.columns(3)
c1.page_link("views/screener.py", label="Open the screener →")
c2.page_link("views/company.py", label="Look up a company →")
c3.page_link("views/pipeline.py", label="Full methods →")

source(
    "Data: SEC EDGAR filings; Yahoo Finance prices via yfinance; SPY as the market. "
    "Classification: Anthropic API (claude-haiku-4-5), validated against hand labels. "
    "All methodological choices and interpretations are the author's."
)
