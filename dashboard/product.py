"""Product layer: company profiles, catalyst risk and the filing feed.

Built on top of data.py (the research outputs). Everything here is derived
from files already in data/processed/, so the app needs no API keys and makes
no network calls.

Terms used in the app
  day-0 move   the event's abnormal return on the filing day (AR(0)): the
               stock's return minus what the market model predicted.
  typical move the median of |day-0 move| over a set of events.
"""

import re

import numpy as np
import pandas as pd
import streamlit as st

from data import DATA, load_car

APP_NAME = "SD Biotech Analyzer"
TAGLINE = "How hard do San Diego biotech stocks move on news?"

LABEL_NAMES = {
    "CLINICAL": "Clinical data",
    "EARNINGS": "Earnings",
    "REGULATORY": "Regulatory",
    "PRESENTATION": "Presentation",
    "OTHER": "Other",
}
# Labels that came from the Claude Haiku classifier; earnings come from Item 2.02
AI_LABELS = {"CLINICAL", "REGULATORY", "PRESENTATION", "OTHER"}

# Below this many events, a company's own history is too thin to lean on
MIN_OWN_EVENTS = 5


# --- names --------------------------------------------------------------------
_KEEP_UPPER = {"CV", "GRI", "ARS", "II", "III"}
_NAME_FIXES = {
    "aTYR PHARMA INC": "aTyr Pharma, Inc.",
    "MEDICINOVA INC": "MediciNova, Inc.",
    "ANAPTYSBIO, INC": "AnaptysBio, Inc.",
    "RESMED INC": "ResMed Inc.",
    "MARAVAI LIFESCIENCES HOLDINGS, INC.": "Maravai LifeSciences Holdings, Inc.",
}


def display_name(raw: str) -> str:
    """Turn EDGAR's 'DEXCOM INC' style names into 'Dexcom Inc'."""
    if raw in _NAME_FIXES:
        return _NAME_FIXES[raw]
    name = raw.replace("/DE/", "").strip()
    words = []
    for w in name.split():
        core = re.sub(r"[^A-Za-z]", "", w)
        if core.isupper() and core not in _KEEP_UPPER and len(core) > 1:
            w = w[0] + w[1:].lower()
        words.append(w)
    return " ".join(words).replace("Inc.,", "Inc.").strip(" ,")


def short_name(raw: str) -> str:
    """Company name without the legal suffix: 'Viking Therapeutics'."""
    name = display_name(raw)
    name = re.sub(r",?\s+(Holdings,?\s+)?(Inc\.?|Corp\.?|Corporation|Ltd\.?|Co\.?)$", "", name)
    return name.strip(" ,")


# --- headlines ----------------------------------------------------------------
_MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
_DATELINE = re.compile(
    rf"\s+(?:[A-Z][A-Za-z.]+(?:\s[A-Z][A-Za-z.]+)*,?\s*(?:CA|Calif\.?|California)?\.?,?\s*[–—-]?\s*)?"
    rf"\(?(?:{_MONTHS})\s\d{{1,2}},\s\d{{4}}"
)
_PREFIXES = [
    r"^EX-\d+(?:\.\d+)?\s+\d+\s+\S+\.htm\s*",
    r"^EX-\d+(?:\.\d+)?\s*",
    r"^(?:Exhibit|Ex\.)\s*99\.?\d*\s*",
    r"^PRESS RELEASE\s*",
    r"^For Immediate Release\s*",
]
# "... issued a press release announcing that X" -> "X"
_ANNOUNCING = re.compile(
    r"^.{0,220}?(?:issued|released|announced)\s+(?:a\s+)?press\s+release\s+"
    r"(?:announcing|titled|entitled|regarding|reporting)\s+(?:that\s+)?",
    re.IGNORECASE,
)
_BOILERPLATE = re.compile(
    r"^(Regulation FD|Results of Operations|Other Events|This presentation contains|"
    r"Material Modification|Forward[- ]Looking)", re.IGNORECASE,
)


def clean_headline(text: str, max_len: int = 170) -> str | None:
    """Best-effort headline from the first 250 characters of a filing."""
    if not isinstance(text, str) or not text.strip():
        return None
    t = " ".join(text.split())
    for _ in range(3):
        for p in _PREFIXES:
            t = re.sub(p, "", t, flags=re.IGNORECASE)
    lead = _ANNOUNCING.match(t)
    if lead and len(t) - lead.end() > 30:
        t = t[lead.end():]
        t = t[0].upper() + t[1:]
    elif not _BOILERPLATE.match(t):
        cut = _DATELINE.search(t)
        if cut and cut.start() > 25:
            t = t[: cut.start()]
    t = t.strip(" –—-,:")
    if len(t) > max_len:
        t = t[:max_len].rsplit(" ", 1)[0] + "…"
    elif not t.endswith(("…", ".", "!", "?")) and len(" ".join(text.split())) >= 245:
        t += "…"   # the stored text stops at 250 characters
    return t


# --- events -------------------------------------------------------------------
@st.cache_data
def load_events() -> pd.DataFrame:
    """Every filing with a measured price reaction, ready for the product pages."""
    ev = load_car().copy()
    heads = pd.read_csv(DATA / "classified_701.csv", usecols=["accession", "headline"])
    ev = ev.merge(heads, on="accession", how="left")
    ev["headline"] = ev["headline"].map(clean_headline)
    ev["company"] = ev["name"].map(short_name)
    ev["label_name"] = ev["label"].map(LABEL_NAMES)
    ev["source"] = np.where(ev["label"].isin(AI_LABELS), "AI", "Item 2.02")
    ev["move"] = ev["ar0"] * 100
    ev["abs_move"] = ev["move"].abs()
    ev["after"] = ev["car_drift"] * 100
    return ev.sort_values("t0", ascending=False).reset_index(drop=True)


@st.cache_data
def load_companies() -> pd.DataFrame:
    """One row per company with its catalyst statistics."""
    ev = load_events()
    meta = pd.read_csv(DATA / "sd_lifesci_companies.csv", usecols=["ticker", "sic_desc", "city"])

    def stats(g: pd.DataFrame) -> pd.Series:
        cl = g[g["label"] == "CLINICAL"]
        er = g[g["label"] == "EARNINGS"]
        biggest = g.loc[g["abs_move"].idxmax()]
        return pd.Series({
            "company": g["company"].iloc[0],
            "name": g["name"].iloc[0],
            "events": len(g),
            "readouts": len(cl),
            "readout_move": cl["abs_move"].median() if len(cl) else np.nan,
            "earnings": len(er),
            "earnings_move": er["abs_move"].median() if len(er) else np.nan,
            "all_move": g["abs_move"].median(),
            "biggest_move": biggest["move"],
            "biggest_date": biggest["t0"],
            "biggest_label": biggest["label"],
            "last_filing": g["t0"].max(),
        })

    comp = ev.groupby("ticker").apply(stats, include_groups=False).reset_index()
    comp = comp.merge(meta.drop_duplicates("ticker"), on="ticker", how="left")
    comp["city"] = comp["city"].fillna("").str.title()
    comp["sic_desc"] = comp["sic_desc"].fillna("")
    return comp


def risk_profile(ticker: str, label: str) -> dict:
    """Historical day-0 move distribution for one company and event type.

    Uses the company's own events when it has at least MIN_OWN_EVENTS of that
    type; otherwise falls back to every company's events of that type.
    """
    ev = load_events()
    of_type = ev[ev["label"] == label]
    own = of_type[of_type["ticker"] == ticker]
    use_own = len(own) >= MIN_OWN_EVENTS
    basis = own if use_own else of_type
    m = basis["move"].to_numpy()
    a = np.abs(m)
    return {
        "own": own,
        "peers": of_type,
        "use_own": use_own,
        "n": len(basis),
        "typical": float(np.median(a)),
        "p75": float(np.percentile(a, 75)),
        "p90": float(np.percentile(a, 90)),
        "share_up": float((m > 0).mean()),
        "share_10": float((a > 10).mean()),
        "band50": (float(np.percentile(m, 25)), float(np.percentile(m, 75))),
        "band80": (float(np.percentile(m, 10)), float(np.percentile(m, 90))),
    }


