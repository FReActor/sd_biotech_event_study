"""Findings: the headline answer, the three tests, and the event-time path."""

import plotly.graph_objects as go
import streamlit as st

from charts import PLOTLY_CONFIG, shade_windows, style
from data import (
    BONFERRONI, INK, INK_MUTED, LABEL_COLORS, MAIN_LABELS, PAPER_URL, REPO_URL,
    WINDOWS, event_time_path, fmt_p, funnel_counts, load_car,
    pct, placebo_test,
)
from ui import hero, result_cards

car = load_car()
counts = funnel_counts()

n_clinical = int((car["label"] == "CLINICAL").sum())

hero(
    eyebrow="Event study · San Diego life sciences · 2019–2025",
    title="Do markets digest clinical trial news more slowly than earnings?",
    lede=(
        "Clinical trial results are technical and hard to interpret; quarterly "
        "earnings are standardized. If interpretive difficulty slows price "
        "discovery, stock prices should react to the two differently."
    ),
    answer=(
        "<b>No.</b> Clinical announcements move prices on the day they are made, "
        "with no detectable leakage before and no drift after, the same pattern "
        "as earnings."
    ),
    buttons=[
        ("Read the paper", PAPER_URL, True),
        ("View the code", REPO_URL, False),
        ("Explore events →", "explorer", False),
    ],
    stats=[
        (f"{counts['final_firms']}", "San Diego firms"),
        (f"{counts['events_with_car']:,}", "8-K events"),
        (f"{n_clinical}", "clinical readouts"),
        ("0.817", "LLM vs human kappa"),
    ],
    byline="Charles Cheng · B.S. Applied Mathematics, UC San Diego",
)

# --- the three primary tests -----------------------------------------------
st.header("The three tests")
st.caption(
    "Median abnormal return for real announcements versus a placebo baseline of "
    "matched non-event dates. p-values are two-sided and Bonferroni-corrected "
    f"across three tests (significant if p < {BONFERRONI:.4f})."
)

label = st.segmented_control(
    "Event type", MAIN_LABELS, default="CLINICAL",
    format_func=str.title, key="findings_label", required=True,
)

questions = {
    "car_leak": "Did prices move <b>before</b> the announcement?",
    "ar0": "Did prices move <b>on</b> the announcement day?",
    "car_drift": "Did prices keep moving <b>after</b>?",
}

cards = []
for column, (short, formal, _) in WINDOWS.items():
    res = placebo_test(label, column)
    significant = res["p"] < BONFERRONI
    cards.append({
        "kicker": short,
        "window": formal,
        "question": questions[column],
        "value": pct(res["observed"]),
        "sub": f"Median of {res['n_real']} events · placebo {pct(res['placebo'])}",
        "pill": ("Significant" if significant else "Not significant") + f" · p {fmt_p(res['p'])}",
        "significant": significant,
        "color": LABEL_COLORS[label],
    })
result_cards(cards)

# --- event-time path --------------------------------------------------------
st.header("What happens around the announcement")
left, right = st.columns([3, 1])
with right:
    stat = st.radio(
        "Aggregate across events by",
        ["median", "mean"],
        format_func=str.title,
        help="The median shows the typical event. The mean is pulled around "
        "by a few enormous clinical moves.",
    )
    shown = st.multiselect(
        "Event types", MAIN_LABELS, default=MAIN_LABELS, format_func=str.title
    )
    st.caption(
        "Cumulative abnormal return from day −10, built per event and then "
        "aggregated. Shaded bands are the leakage and drift windows."
    )

path = event_time_path(stat)
fig = go.Figure()
for lab in MAIN_LABELS:
    if lab not in shown:
        continue
    sub = path[path["label"] == lab]
    fig.add_trace(go.Scatter(
        x=sub["offset"], y=sub["car"] * 100, name=f"{lab.title()} (n={sub['n'].iloc[0]})",
        mode="lines+markers", line=dict(color=LABEL_COLORS[lab], width=2),
        marker=dict(size=6),
        hovertemplate="Day %{x:+d}<br>CAR %{y:.2f}%<extra>" + lab.title() + "</extra>",
    ))
shade_windows(fig, {"Leakage": (-10, -2), "Drift": (2, 10)})
fig.update_layout(hovermode="x unified")
fig.update_xaxes(title="Trading days relative to announcement", dtick=2)
fig.update_yaxes(title=f"{stat.title()} cumulative abnormal return (%)")
with left:
    st.plotly_chart(style(fig, height=420), config=PLOTLY_CONFIG, width="stretch")

# --- mean vs median ---------------------------------------------------------
st.header("Why the median, not the mean")
vals = car.loc[car["label"] == label, "ar0"].dropna() * 100
share_neg = (vals < 0).mean()
clipped = vals[(vals > -30) & (vals < 30)]

left, right = st.columns([3, 1])
with right:
    st.metric("Negative day-0 moves", f"{share_neg:.0%}")
    st.metric("Mean AR(0)", f"{vals.mean():+.2f}%")
    st.metric("Median AR(0)", f"{vals.median():+.2f}%")
    if label == "CLINICAL":
        st.caption(
            "Most clinical readouts disappoint and the stock slips, but the rare "
            "success can double the price. The mean and median disagree in sign, "
            "so the tests use the median."
        )
    st.caption(f"{len(vals) - len(clipped)} events outside ±30% are not drawn.")

hist = go.Figure(go.Histogram(
    x=clipped, nbinsx=40, marker=dict(color=LABEL_COLORS[label], line=dict(color="white", width=1)),
    hovertemplate="AR(0) %{x}%<br>%{y} events<extra></extra>",
))
for value, name, dash in [(vals.mean(), "Mean", "dash"), (vals.median(), "Median", "dot")]:
    hist.add_vline(
        x=value, line_dash=dash, line_color=INK, line_width=1.5,
        annotation_text=f"{name} {value:+.2f}%", annotation_font=dict(size=11, color=INK_MUTED),
        annotation_position="top right" if name == "Mean" else "top left",
    )
hist.update_xaxes(title=f"Announcement-day abnormal return, {label.title()} (%)")
hist.update_yaxes(title="Events")
with left:
    st.plotly_chart(style(hist, height=360, legend=False), config=PLOTLY_CONFIG, width="stretch")
