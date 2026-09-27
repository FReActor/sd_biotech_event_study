"""How it was built: sample construction, LLM classification, market model."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from charts import PLOTLY_CONFIG, style
from ui import narrow, article_header, chart_title, source
from data import (
    EST_WINDOW, INK_MUTED, LABEL_COLORS, VALID_LABELS, ALL_WINDOWS,
    funnel_counts, load_car, load_manual_labels, load_system_prompt,
)

narrow()

counts = funnel_counts()
car = load_car()

article_header(
    kicker="Methods",
    headline="How the study was built",
    dek=(
        "Public SEC filings in; a labelled event sample and abnormal returns out. "
        "Every number on this page is read from the pipeline's output files."
    ),
    page=True,
)

# --- 1. sample --------------------------------------------------------------
st.header("1. Building the sample")


def steps(title: str, stages: list[tuple[str, int]]) -> None:
    """A row of numbers showing how the sample narrows at each step."""
    chart_title(title)
    cols = st.columns(len(stages))
    for i, (col, (name, n)) in enumerate(zip(cols, stages)):
        col.metric(("→ " if i else "") + name, f"{n:,}")


steps("Firms", [
    ("SEC filers", counts["edgar_filers"]),
    ("San Diego", counts["sd_companies"]),
    ("Life sciences", counts["sd_lifesci"]),
    ("Final sample", counts["final_firms"]),
])
steps("Filings", [
    ("8-K filings", counts["filings_8k"]),
    ("Labelled", counts["labelled_events"]),
    ("With returns", counts["events_with_car"]),
    ("Main 3 types", counts["main_events"]),
])

source(
    f"{counts['confounded']} filings that bundled earnings (Item 2.02) with a "
    "catalyst (Item 7.01 or 8.01) were dropped, since the price reaction "
    "can't be attributed to either one. Earnings events come from Item 2.02; "
    "the other labels come from the LLM classifier below."
)

# --- 2. classification ------------------------------------------------------
st.header("2. Classifying filings with an LLM")
st.markdown(
    "Item 7.01 and 8.01 filings are free text: a trial readout, an investor "
    "deck and a financing all file under the same items. Claude Haiku "
    "(`claude-haiku-4-5`) reads the first 1,500 characters of each filing and "
    "assigns one label. To check it, 100 filings were labelled by hand, blind "
    "to the model's answers."
)

manual = load_manual_labels()
order = ["CLINICAL", "REGULATORY", "PRESENTATION", "OTHER"]

# Confusion matrix and Cohen's kappa, computed directly with pandas
cm = pd.crosstab(manual["my_label"], manual["llm_label"]).reindex(
    index=order, columns=order, fill_value=0
).to_numpy()
n = cm.sum()
agreement = cm.trace() / n
chance = (cm.sum(axis=1) * cm.sum(axis=0)).sum() / n**2
kappa = (agreement - chance) / (1 - chance)

c1, c2, c3 = st.columns(3)
c1.metric("Cohen's kappa", f"{kappa:.3f}", help="0.61–0.80 is "
          "conventionally 'substantial' agreement, above 0.80 'almost perfect'.")
c2.metric("Raw agreement", f"{agreement:.0%}")
c3.metric("Hand-labelled", f"{len(manual)}")

names = [o.title() for o in order]

heat = go.Figure(go.Heatmap(
    z=cm, x=names, y=names, text=cm, texttemplate="%{text}",
    colorscale=[[0, "#1c1c1a"], [1, "#e4602a"]], showscale=False,
    xgap=3, ygap=3,
    hovertemplate="Hand: %{y}<br>LLM: %{x}<br>%{z} filings<extra></extra>",
))
heat.update_xaxes(title="LLM label", side="bottom")
heat.update_yaxes(title="My label", autorange="reversed", zeroline=False)
chart_title("Where the model and I disagreed", "100 hand-labelled filings; the diagonal is agreement")
st.plotly_chart(style(heat, height=320), config=PLOTLY_CONFIG, width="stretch")

mix = car["label"].value_counts().reindex(VALID_LABELS)
bars = go.Figure(go.Bar(
    x=mix.values, y=[v.title() for v in mix.index], orientation="h",
    marker=dict(color=[LABEL_COLORS[v] for v in mix.index], cornerradius=3),
    text=mix.values, textposition="outside", textfont=dict(color=INK_MUTED),
    hovertemplate="%{y}: %{x} events<extra></extra>",
))
bars.update_yaxes(autorange="reversed", zeroline=False)
bars.update_xaxes(title=None, range=[0, mix.max() * 1.15])
chart_title("The final event mix", "Filings with abnormal returns, by label")
st.plotly_chart(style(bars, height=260), config=PLOTLY_CONFIG, width="stretch")

with st.expander("The classification prompt"):
    st.code(load_system_prompt(), language=None, wrap_lines=True)

# --- 3. market model --------------------------------------------------------
st.header("3. Measuring the price reaction")
st.markdown(
    f"For each event, a market model is estimated on the stock's own daily "
    f"returns from trading day {EST_WINDOW[0]} to {EST_WINDOW[1]}, with SPY as "
    "the market. The abnormal return is what the stock did beyond what the "
    "market predicts:"
)
st.latex(r"AR_{i,t} = R_{i,t} - (\hat\alpha_i + \hat\beta_i R_{m,t}), \qquad "
         r"CAR_i[a,b] = \sum_{t=a}^{b} AR_{i,t}")
st.markdown(
    "Filings accepted after the 4 pm close are assigned to the next trading "
    "day. Each window answers one question:"
)
st.dataframe(
    pd.DataFrame(
        [(formal, short, f"{lo:+d} to {hi:+d}") for short, formal, (lo, hi) in ALL_WINDOWS.values()],
        columns=["Window", "Question", "Trading days"],
    ),
    hide_index=True, width="stretch",
)

source(
    "Classification used the Anthropic API and was validated against "
    "hand-labelled ground truth. All methodological choices, parameters, and "
    "interpretations are the author's."
)
