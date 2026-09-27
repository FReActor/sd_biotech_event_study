"""Placebo test: where the p-values come from."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from charts import PLOTLY_CONFIG, style
from data import (
    BONFERRONI, INK, INK_MUTED, LABEL_COLORS, MAIN_LABELS, N_RESAMPLES, WINDOWS,
    fmt_p, pct, placebo_test,
)
from ui import article_header, chart_title, source

WINDOW_NAMES = {"car_leak": "Before", "ar0": "Day 0", "car_drift": "After"}

article_header(
    kicker="Methods · Placebo test",
    headline="Beating fake announcements",
    dek=(
        "Small biotech stocks drift on their own, and no market model is perfect. "
        "So every real filing is compared with fake ones."
    ),
    page=True,
)

st.markdown(
    "For each real filing, 20 fake announcement dates are drawn for the same "
    "stock, in the same calendar month, more than 5 trading days away from any "
    "real filing. The fake dates go through the identical pipeline. A result "
    "only counts if the real filings look different from these."
)

c1, c2 = st.columns(2)
label = c1.segmented_control(
    "Event type", MAIN_LABELS, default="CLINICAL", format_func=str.title,
    key="placebo_label", required=True,
)
column = c2.segmented_control(
    "Window", list(WINDOWS), default="ar0", key="placebo_window", required=True,
    format_func=lambda c: WINDOW_NAMES[c],
)

res = placebo_test(label, column)
null = res["null_medians"] * 100
observed = res["observed"] * 100
center = res["placebo"] * 100
significant = res["p"] < BONFERRONI

m = st.columns(3)
m[0].metric(f"Real filings (n={res['n_real']})", pct(res["observed"]))
m[1].metric(f"Fake dates (n={res['n_placebo']:,})", pct(res["placebo"]))
m[2].metric(
    "p-value", fmt_p(res["p"]).lstrip("= "),
    help=f"Counts as significant below {BONFERRONI:.4f} (0.05 split across three tests)",
)

short, formal, _ = WINDOWS[column]
chart_title(
    "Real result vs. what chance produces" if significant
    else "Real result sits inside what chance produces",
    f"Median {formal} across {res['n_real']} {label.lower()} filings, %. "
    f"Gray: {N_RESAMPLES:,} medians of equally sized samples of fake dates.",
)
fig = go.Figure(go.Histogram(
    x=null, nbinsx=50, marker=dict(color="#cfccc4", line=dict(color="#fbfaf7", width=1)),
    hovertemplate="Median %{x}%: %{y} resamples<extra></extra>",
))
fig.add_vline(x=center, line_color=INK_MUTED, line_dash="dot", line_width=1)
fig.add_vline(x=observed, line_color=LABEL_COLORS[label], line_width=3)
fig.add_annotation(
    x=observed, y=1, yref="paper", yanchor="bottom", showarrow=False,
    text=f"<b>Real: {observed:+.2f}%</b>", font=dict(size=12, color=INK),
)
fig.update_xaxes(ticksuffix="%")
fig.update_yaxes(title=None)
fig.update_layout(margin=dict(t=30))
st.plotly_chart(style(fig, height=340), config=PLOTLY_CONFIG, width="stretch")
source(
    "The p-value is the share of gray medians at least as far from the fake-date "
    "center (dotted line) as the real median. It is a Monte Carlo estimate, so "
    "the third decimal varies with the random seed."
)

st.header("All nine tests")
rows = []
for lab in MAIN_LABELS:
    for col in WINDOWS:
        r = placebo_test(lab, col)
        rows.append({
            "Event type": lab.title(),
            "Window": f"{WINDOW_NAMES[col]} · {WINDOWS[col][1]}",
            "Real median": pct(r["observed"], 2),
            "Fake dates": pct(r["placebo"], 2),
            "p": fmt_p(r["p"]).lstrip("= "),
            "Significant": "Yes" if r["p"] < BONFERRONI else "No",
        })
st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
source(
    "The paper's primary tests are the clinical rows. Earnings and regulatory rows "
    "use the same method and are shown for comparison."
)
