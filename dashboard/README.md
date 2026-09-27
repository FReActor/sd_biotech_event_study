# SD Biotech Analyzer (interactive dashboard)

A Streamlit app that presents the study's results. It reads only the files
already in `data/processed/`, so it needs no API keys and makes no network calls.

## Run locally

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py
```

The app opens at http://localhost:8501.

## Pages

| Page | What it does |
|---|---|
| Screener (home) | Search any company; rank companies by biggest one-day gain or average change; trial-vs-earnings bar chart |
| Company | Brokerage-style price chart with every filing marked, the filing list with AI labels, and any filing up close vs. the market |
| Risk check | Trial-vs-earnings multiple for the company, the historical day-0 move range for a news type in % and dollars, and each past filing's move |
| Research → The study | The research write-up as a data-journalism article |
| Research → Methods | Sample construction, classifier validation, the market model |

Company and risk pages read the ticker from the URL, e.g. `/company?ticker=VKTX`, so every company has a shareable link.

## Files

```
dashboard/
├── app.py            entry point: page config, logo, navigation
├── data.py           research layer: loaders, constants, placebo test, event-time path
├── product.py        product layer: names, headlines, company stats, risk profile
├── charts.py         shared Plotly styling, annotations and line labels
├── ui.py             HTML pieces: article header, chart titles, big numbers
├── assets/           logo, icon, style.css
├── static/fonts/     Inter and Source Serif 4 (SIL Open Font License)
├── views/            one file per page
└── requirements.txt
.streamlit/config.toml   theme, fonts, toolbar (at the repository root)
```

## Deploy to Streamlit Community Cloud

1. Push this folder and `.streamlit/` to GitHub.
2. Go to share.streamlit.io and sign in with GitHub.
3. Create app → repository `FReActor/sd_biotech_event_study`, branch `main`,
   main file path `dashboard/app.py`.
4. Deploy. The first build takes a few minutes.

Apps on the free tier sleep after a period of no traffic. Open the link a few
minutes before a demo to wake it up.

## Notes

- Events whose LLM label was not a valid category (`INVALID:...`, `NO_TEXT`)
  are excluded everywhere in the app.
- p-values are Monte Carlo estimates (10,000 resamples, fixed seed) and are
  shown to two decimals.
