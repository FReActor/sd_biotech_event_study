# Information Efficiency in Life Sciences Equity Prices

This event study tests whether equity prices absorb clinical trial results more slowly than quarterly earnings. 
Clinical announcements are more technical and harder to understand, while earnings are standardized. If interpretive 
difficulty slows price discovery, the two should behave differently.

**Sample:** 60 San Diego life sciences firms, 2,349 events, 2019–2025.

**Finding:** Clinical announcements produce a significant same-day price
reaction, but no pre-announcement leakage and no post-announcement drift.
No detectable difference from earnings announcements.

📄 [Summary paper](summary paper/Charles_Cheng_Information_Efficiency.pdf)

**Results**
| Window | Clinical | Placebo baseline | p |
|---|---|---|---|
| CAR[−10, −2] — leakage | −0.494% | −2.625% | 0.057 |
| AR(0) — announcement | −1.367% | −0.226% | <0.001 |
| CAR[+2, +10] — drift | −1.931% | −1.796% | 0.870 |

## Pipeline

| Script | What it does | Output |
|---|---|---|
| `01_fetch_universe.py` | Scans 7,997 SEC EDGAR filers, extracts address and SIC code for each | `all_companies.csv` |
| `02_filter_companies.py` | Filters to San Diego County life sciences firms | `sd_lifesci_companies.csv` |
| `03_fetch_filings.py` | Pulls 8-K metadata and filing text, including EX-99 exhibits | `events_8-k.csv`, `data/raw/filings/` |
| `04_classify.py` | Labels filings via the Anthropic API: CLINICAL / REGULATORY / PRESENTATION / OTHER | `llm_labels_*.csv` |
| `05_build_events.py` | Aligns events to trading days, deduplicates, flags exclusions | `events_aligned.csv` |
| `06_estimate_car.py` | Estimates per-event market models, computes AR and CAR | `car.csv`, `ar_panel.csv` |
| `07_placebo.py` | Draws 24,600 matched non-event dates, runs the identical pipeline | `placebo_car.csv` |
| `08_tests.py` | Primary hypothesis tests | console |
| `09_robustness.py` | Five robustness specifications | console |
| `10_plot.py` | Figures | `figures/` |

## Data sources
- SEC EDGAR submissions API — company metadata and 8-K filings
- yfinance — daily adjusted prices, SPY as market factor
All data are public

Median values. p-values are empirical, obtained by resampling the placebo
distribution at the real sample size. Two-sided, Bonferroni-corrected
across three primary tests (threshold 0.0167).

## AI assistance

Code was developed with AI assistance. Event classification used the
Anthropic API (`claude-haiku-4-5-20251001`) and was validated against
hand-labelled ground truth. All methodological choices, parameter 
selections, and interpretations are the author's.

---

## Author

Charles Cheng · B.S. Applied Mathematics, UC San Diego
zic065@ucsd.edu
