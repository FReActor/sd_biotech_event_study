"""Data loading and shared computations for the dashboard.

Everything here reads the files the research pipeline already produced in
data/processed/. Nothing is downloaded or re-estimated at runtime.

Functions decorated with @st.cache_data run once per set of arguments and
are then served from memory, so the app does not re-read CSVs on every click.
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
SRC = ROOT / "src"

REPO_URL = "https://github.com/FReActor/sd_biotech_event_study"
PAPER_URL = f"{REPO_URL}/blob/main/paper/Charles_Cheng_Information_Efficiency.pdf"

# --- labels and colors ------------------------------------------------------
MAIN_LABELS = ["CLINICAL", "EARNINGS", "REGULATORY"]
VALID_LABELS = MAIN_LABELS + ["PRESENTATION", "OTHER"]

# Tuned for the dark theme (checked with a colorblind-safety validator against
# the dark surface): orange for clinical, blue for earnings, green for regulatory.
LABEL_COLORS = {
    "CLINICAL": "#e4602a",
    "EARNINGS": "#3a8fd0",
    "REGULATORY": "#6f9e2d",
    "PRESENTATION": "#9b7fd6",
    "OTHER": "#8f8d86",
}
PLACEBO_COLOR = "#8f8d86"
INK = "#f3f2ee"          # main text on the dark background
INK_MUTED = "#a09e96"    # secondary text, axes
BG = "#0f0f0e"           # page background
SURFACE = "#1c1c1a"      # cards, hover labels
ACCENT = "#ff7a3d"       # orange for controls and key figures

# --- event windows ----------------------------------------------------------
# column -> (short name, formal name, (first offset, last offset))
WINDOWS = {
    "car_leak": ("Before (leakage)", "CAR[−10, −2]", (-10, -2)),
    "ar0": ("Day 0 (reaction)", "AR(0)", (0, 0)),
    "car_drift": ("After (drift)", "CAR[+2, +10]", (2, 10)),
}
EXTRA_WINDOWS = {
    "car_event": ("Days 0 to +1", "CAR[0, +1]", (0, 1)),
    "car_aux": ("Days −1 to +1", "CAR[−1, +1]", (-1, 1)),
}
ALL_WINDOWS = {**WINDOWS, **EXTRA_WINDOWS}

EST_WINDOW = (-250, -31)
N_PRIMARY_TESTS = 3
BONFERRONI = 0.05 / N_PRIMARY_TESTS

# Placebo resampling settings
N_RESAMPLES = 10_000
SEED = 20260901


# --- loaders ----------------------------------------------------------------
@st.cache_data
def load_car() -> pd.DataFrame:
    """One row per event with its market-model fit and CARs.

    Rows whose LLM label is not a real category (INVALID:..., NO_TEXT) are
    dropped here so they never appear anywhere in the app.
    """
    car = pd.read_csv(DATA / "car.csv", parse_dates=["t0"])
    events = pd.read_csv(DATA / "events_final.csv", dtype={"cik": str})
    car = car.merge(
        events[["accession", "cik", "items", "after_hours", "acceptance_et"]],
        on="accession",
        how="left",
    )
    car = car[car["label"].isin(VALID_LABELS)].copy()
    car["filing_url"] = car.apply(filing_url, axis=1)
    return car


@st.cache_data
def load_ar_panel() -> pd.DataFrame:
    """Daily abnormal returns for offsets -10..+10 around each event."""
    panel = pd.read_csv(DATA / "ar_panel.csv")
    return panel[panel["label"].isin(VALID_LABELS)]


@st.cache_data
def load_placebo() -> pd.DataFrame:
    return pd.read_csv(DATA / "placebo_car.csv")


@st.cache_data
def load_prices() -> pd.DataFrame:
    return pd.read_csv(DATA / "prices.csv", parse_dates=["date"])


@st.cache_data
def load_manual_labels() -> pd.DataFrame:
    """The 100 hand-labelled filings, normalized the same way as Day_6_kappa.py."""
    df = pd.read_csv(DATA / "llm_labels_manual100.csv")
    df["my_label"] = df["my_label"].str.upper().str.replace("OTHERS", "OTHER")
    df["llm_label"] = df["llm_label"].str.upper().str.split().str[0]
    return df


@st.cache_data
def load_system_prompt() -> str:
    """Read the classification prompt straight from the pipeline source."""
    text = (SRC / "Day_6_LLM_prompt").read_text(encoding="utf-8")
    match = re.search(r'SYSTEM_PROMPT = """(.*?)"""', text, flags=re.DOTALL)
    return match.group(1).strip() if match else ""


@st.cache_data
def funnel_counts() -> dict:
    """Sample-construction counts, read from the pipeline outputs."""
    car = load_car()
    return {
        "edgar_filers": len(pd.read_csv(DATA / "all_companies.csv")),
        "sd_companies": len(pd.read_csv(DATA / "sd_companies.csv")),
        "sd_lifesci": len(pd.read_csv(DATA / "sd_lifesci_companies.csv")),
        "final_firms": pd.read_csv(DATA / "events_final.csv")["cik"].nunique(),
        "filings_8k": len(pd.read_csv(DATA / "events_8-k.csv")),
        "confounded": len(pd.read_csv(DATA / "events_confounded.csv")),
        "labelled_events": len(pd.read_csv(DATA / "events_final.csv")),
        "events_with_car": len(car),
        "main_events": int(car["label"].isin(MAIN_LABELS).sum()),
    }


# --- helpers ----------------------------------------------------------------
def filing_url(row) -> str | None:
    """Link to the filing's folder on SEC EDGAR."""
    if pd.isna(row.get("cik")):
        return None
    return (
        "https://www.sec.gov/Archives/edgar/data/"
        f"{int(row['cik'])}/{row['accession'].replace('-', '')}/"
    )


def pct(x: float, digits: int = 2) -> str:
    """Format a decimal return as a signed percent string."""
    return f"{x * 100:+.{digits}f}%"


def fmt_p(p: float) -> str:
    """Two decimals, matching the precision the Monte Carlo p-values support."""
    return "< 0.001" if p < 0.001 else f"= {p:.2f}"


# --- statistics -------------------------------------------------------------
@st.cache_data
def placebo_test(label: str, column: str) -> dict:
    """Empirical two-sided p-value for the median, from the placebo distribution.

    Method (same as the paper): draw N real-sized samples, with replacement,
    from the placebo events of the same label; take each sample's median.
    The p-value is the share of resampled medians at least as far from the
    placebo median as the observed median is.
    """
    car = load_car()
    placebo = load_placebo()

    real = car.loc[car["label"] == label, column].dropna().to_numpy()
    pool = placebo.loc[placebo["label"] == label, column].dropna().to_numpy()

    observed = float(np.median(real))
    center = float(np.median(pool))

    rng = np.random.default_rng(SEED)
    draws = rng.choice(pool, size=(N_RESAMPLES, len(real)), replace=True)
    null_medians = np.median(draws, axis=1)

    p_value = float(np.mean(np.abs(null_medians - center) >= abs(observed - center)))
    return {
        "observed": observed,
        "placebo": center,
        "p": p_value,
        "n_real": len(real),
        "n_placebo": len(pool),
        "null_medians": null_medians,
    }


@st.cache_data
def event_time_path(stat: str) -> pd.DataFrame:
    """Cumulative abnormal return from day -10 to +10, per label.

    Each event's own CAR path is built first, then aggregated across events
    with the chosen statistic (mean or median).
    """
    panel = load_ar_panel()
    panel = panel[panel["label"].isin(MAIN_LABELS)]
    wide = panel.pivot_table(index=["accession", "label"], columns="offset", values="ar")
    cum = wide.sort_index(axis=1).fillna(0).cumsum(axis=1)
    agg = cum.groupby(level="label").agg(stat)
    out = agg.stack().rename("car").reset_index()
    counts = wide.groupby(level="label").size().rename("n").reset_index()
    return out.merge(counts, on="label")
