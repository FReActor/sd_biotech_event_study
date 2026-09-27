"""Small HTML building blocks for the newspaper-style layout.

Each function renders one piece with st.html. The look comes from
assets/style.css, which app.py loads once per page view.

HTML basics used here:
  <div class="x">...</div>   a box; the class name links it to CSS rules
  <a href="...">...</a>      a link
  <b>...</b>                 bold text
"""

from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

ASSETS = Path(__file__).parent / "assets"

# Price moves: green up, red down (US convention). Swap the two to flip it.
# The +/- sign is always shown too, so up/down never relies on color alone.
UP_COLOR = "#34a862"
DOWN_COLOR = "#f05a4f"


def tone(value: str) -> str:
    """CSS class for a formatted number: 'up' for +x, 'down' for -x, else ''."""
    v = value.strip()
    if v.startswith("+"):
        return "up"
    if v.startswith(("-", "−")):
        return "down"
    return ""


def color_moves(df: pd.DataFrame, move_cols: list[str], formats: dict):
    """Pandas Styler for st.dataframe: signed % columns in green/red.

    formats: {column: format string or callable}, applied for display.
    """
    def paint(v):
        if pd.isna(v) or v == 0:
            return ""
        return f"color: {UP_COLOR if v > 0 else DOWN_COLOR}; font-weight: 600"

    return df.style.map(paint, subset=move_cols).format(formats, na_rep="–")


def load_css() -> None:
    """Inject assets/style.css into the page."""
    css = (ASSETS / "style.css").read_text(encoding="utf-8")
    st.html(f"<style>{css}</style>")


def narrow() -> None:
    """Limit the page to a readable column (used by the research pages)."""
    st.html('<style>[data-testid="stMainBlockContainer"]{max-width: 780px;}</style>')


def article_header(kicker: str, headline: str, dek: str = "", byline: str = "",
                   page: bool = False) -> None:
    """Kicker, headline, dek (the subtitle) and an optional byline.

    byline may contain simple HTML such as <b> and <a> tags.
    page=True uses a smaller headline for secondary pages.
    """
    size = " is-page" if page else ""
    dek_html = f'<p class="sd-dek">{escape(dek)}</p>' if dek else ""
    byline_html = f'<div class="sd-byline">{byline}</div>' if byline else ""
    st.html(f"""
    <header>
      <div class="sd-kicker">{escape(kicker)}</div>
      <h1 class="sd-headline{size}">{escape(headline)}</h1>
      {dek_html}
      {byline_html}
    </header>
    """)


def chart_title(title: str, subtitle: str = "") -> None:
    """Bold chart title with a one-line description, placed above a chart."""
    sub = f'<p class="sd-chart-sub">{escape(subtitle)}</p>' if subtitle else ""
    st.html(f'<div class="sd-chart-title">{escape(title)}</div>{sub}')


def source(text: str) -> None:
    """Small source / note line placed under a chart."""
    st.html(f'<p class="sd-source">{escape(text)}</p>')


def big_numbers(items: list[tuple[str, str]]) -> None:
    """A row of large figures, each with a short explanation.

    items: (value, explanation)
    """
    cells = "".join(
        f'<div class="sd-bignum"><div class="sd-bignum-value">{escape(v)}</div>'
        f'<div class="sd-bignum-text">{escape(t)}</div></div>'
        for v, t in items
    )
    st.html(f'<div class="sd-bignums">{cells}</div>')


def three_windows() -> None:
    """Diagram of the before / day-zero / after windows on a trading-day axis."""
    st.html("""
    <div class="sd-timeline">
      <div class="sd-zone"><b>Before</b>Did prices move early? (leakage)</div>
      <div class="sd-zone is-gap"></div>
      <div class="sd-zone is-day0"><b>Day 0</b></div>
      <div class="sd-zone is-gap"></div>
      <div class="sd-zone is-after"><b>After</b>Did prices keep moving? (drift)</div>
    </div>
    <div class="sd-timeline-axis">
      <span>Day −10 to −2</span><span></span><span>Filing</span><span></span>
      <span>Day +2 to +10</span>
    </div>
    """)


# =====================================================================
# Product pages
# =====================================================================

def page_intro(title: str, subtitle: str = "") -> None:
    """Title and one-line description at the top of an app page."""
    sub = f'<p class="sd-app-sub">{escape(subtitle)}</p>' if subtitle else ""
    st.html(f'<h1 class="sd-app-title">{escape(title)}</h1>{sub}')


def hero_intro(kicker: str, title: str, subtitle: str) -> None:
    """Bigger title block for the home page."""
    st.html(f"""
    <div class="sd-kicker">{escape(kicker)}</div>
    <h1 class="sd-hero-title">{escape(title)}</h1>
    <p class="sd-app-sub">{escape(subtitle)}</p>
    """)


def risk_headline(line_html: str, note: str) -> None:
    st.html(f'<div class="sd-risk"><div class="sd-risk-line">{line_html}</div>'
            f'<div class="sd-risk-note">{escape(note)}</div></div>')


def stat_strip(items: list[tuple[str, str]] | list[tuple[str, str, str]]) -> None:
    """A compact row of numbers: (value, label) or (value, label, small note).

    Lighter than a row of bordered metric cards; wraps to two per row on phones.
    """
    cells = ""
    for item in items:
        value, label = item[0], item[1]
        note = f'<div class="sd-strip-note">{escape(item[2])}</div>' if len(item) > 2 and item[2] else ""
        cells += (f'<div class="sd-strip-cell"><div class="sd-strip-value {tone(value)}">{escape(value)}</div>'
                  f'<div class="sd-strip-label">{escape(label)}</div>{note}</div>')
    st.html(f'<div class="sd-strip">{cells}</div>')


def company_picker(companies, key: str, default: str = "VKTX", label: str = "Company",
                   container=None) -> str:
    """Company selectbox that stays in sync with ?ticker= in the URL.

    companies: DataFrame indexed by ticker with a "company" column.

    The widget has a fixed key and writes the URL in its on_change callback.
    (Computing its default index from the URL on every run made Streamlit
    treat it as a new widget after each change, so the first click was lost.)
    """
    container = container or st
    url_key = f"{key}_url"
    wanted = st.query_params.get("ticker", default)
    if wanted not in companies.index:
        wanted = default
    # Adopt the URL's ticker on first load, or when arriving from a link
    if key not in st.session_state or st.session_state.get(url_key) != wanted:
        st.session_state[key] = wanted
        st.session_state[url_key] = wanted

    def sync() -> None:
        st.query_params["ticker"] = st.session_state[key]
        st.session_state[url_key] = st.session_state[key]

    container.selectbox(
        label, companies.index, key=key, on_change=sync,
        format_func=lambda t: f"{companies.at[t, 'company']} ({t})",
    )
    return st.session_state[key]


def quote(price: str, change: str, period: str, note: str) -> None:
    """Brokerage-style price header: big price, colored change, period, as-of note."""
    st.html(f"""
    <div class="sd-quote">
      <div class="sd-quote-price">{escape(price)}</div>
      <div class="sd-quote-change {tone(change)}">{escape(change)}
        <span>{escape(period)}</span></div>
      <div class="sd-quote-note">{escape(note)}</div>
    </div>
    """)


def insight(big: str, text_html: str) -> None:
    """Highlighted key finding: a large figure on the left, one sentence beside it."""
    st.html(f'<div class="sd-insight"><div class="sd-insight-big">{escape(big)}</div>'
            f'<div class="sd-insight-text">{text_html}</div></div>')


def footer(text: str) -> None:
    st.html(f'<div class="sd-footer">{escape(text)}</div>')
