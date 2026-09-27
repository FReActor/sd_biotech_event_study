"""Filing feed: every 8-K, sorted by AI, with the stock's reaction."""

import streamlit as st

from data import LABEL_COLORS, VALID_LABELS
from product import LABEL_NAMES, load_companies, load_events
from ui import feed, page_intro, source, tag

PAGE = 20

ev = load_events()
comp = load_companies().sort_values("company")

page_intro(
    "Filing feed",
    f"Every 8-K from {len(comp)} San Diego life sciences companies since 2019. "
    "AI reads each filing and labels it; the number on the right is how much it "
    "moved the stock that day.",
)

# --- filters -----------------------------------------------------------------------------
types = st.pills(
    "Type", VALID_LABELS, selection_mode="multi", default=VALID_LABELS,
    format_func=LABEL_NAMES.get, key="feed_types",
)
c1, c2, c3 = st.columns([3, 2, 2])
companies = c1.multiselect(
    "Companies", comp["ticker"], placeholder="All companies",
    format_func=lambda t: comp.set_index("ticker").at[t, "company"],
)
sort = c2.selectbox("Sort", ["Biggest move first", "Newest first"])
big_only = c3.toggle("Moves over 10% only", value=False)
query = st.text_input("Search headlines", placeholder="e.g. Phase 3, FDA, offering",
                      label_visibility="collapsed")

rows = ev[ev["label"].isin(types or [])]
if companies:
    rows = rows[rows["ticker"].isin(companies)]
if big_only:
    rows = rows[rows["abs_move"] > 10]
if query:
    rows = rows[rows["headline"].fillna("").str.contains(query, case=False, regex=False)]
rows = rows.sort_values("abs_move" if sort == "Biggest move first" else "t0", ascending=False)

# Reset paging whenever the filters change
signature = (tuple(types or []), tuple(companies), sort, big_only, query)
if st.session_state.get("feed_sig") != signature:
    st.session_state["feed_sig"] = signature
    st.session_state["feed_n"] = PAGE
n = st.session_state["feed_n"]

source(f"{len(rows):,} filings" + (f" · showing {min(n, len(rows))}" if len(rows) > n else ""))
feed([
    {
        "date": f"{r.t0:%b %d, %Y}",
        "company": r.company,
        "ticker": r.ticker,
        "tag_html": tag(LABEL_NAMES[r.label], LABEL_COLORS[r.label]),
        "ai": r.source == "AI",
        "headline": r.headline if isinstance(r.headline, str) else None,
        "move": r.move,
        "sec_url": r.filing_url,
    }
    for r in rows.head(n).itertuples()
])

if len(rows) > n:
    if st.button(f"Show {min(PAGE, len(rows) - n)} more"):
        st.session_state["feed_n"] = n + PAGE
        st.rerun()

st.caption(
    "Labels marked AI were assigned by Claude Haiku when the study ran; on 100 filings "
    "checked by hand it agreed 90% of the time. Earnings come from the filing's "
    "Item 2.02 flag. Text previews exist for Item 7.01 filings only."
)
