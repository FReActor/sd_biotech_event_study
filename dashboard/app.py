"""Entry point for Readout.

Run from the repository root:
    streamlit run dashboard/app.py

Streamlit reruns this file top to bottom on every interaction. st.navigation
decides which page file to run underneath the shared header and footer.
"""

from pathlib import Path

import streamlit as st

from product import APP_NAME
from ui import footer, load_css

ASSETS = Path(__file__).parent / "assets"

st.set_page_config(
    page_title=f"{APP_NAME} · San Diego biotech catalysts",
    page_icon=str(ASSETS / "icon.svg"),
    layout="wide",
)

st.logo(str(ASSETS / "logo.svg"), icon_image=str(ASSETS / "icon.svg"), size="large")
load_css()

# The app pages sit in the top bar; the research write-up lives in a
# "Research" dropdown, so the product comes first and the study backs it up.
pages = {
    "": [
        st.Page("views/screener.py", title="Screener", default=True),
        st.Page("views/company.py", title="Company", url_path="company"),
        st.Page("views/risk.py", title="Risk check", url_path="risk"),
    ],
    "Research": [
        st.Page("views/story.py", title="The study", url_path="study"),
        st.Page("views/pipeline.py", title="Methods", url_path="methods"),
    ],
}
nav = st.navigation(pages, position="top")
nav.run()

footer(
    f"{APP_NAME} · Data: SEC EDGAR 8-K filings and daily prices, 2019–2025 · "
    "Built by Charles Cheng, UC San Diego · Historical data, not investment advice."
)
