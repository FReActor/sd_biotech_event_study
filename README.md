# Information Efficiency in Life Sciences Equity Prices

This event study tests whether equity prices absorb clinical trial results more slowly than quarterly earnings. 
Clinical announcements are more technical and harder to understand, while earnings are standardized. If interpretive 
difficulty slows price discovery, the two should behave differently.

**Sample:** 60 San Diego life sciences firms, 2,349 events, 2019–2025.

**Finding:** Clinical announcements produce a significant same-day price
reaction, but no pre-announcement leakage and no post-announcement drift.
No detectable difference from earnings announcements.

📄 [Summary paper](paper/Charles_Cheng_Information_Efficiency.pdf)

**Results**
| Window | Clinical | Placebo baseline | p |
|---|---|---|---|
| CAR[−10, −2] — leakage | −0.494% | −2.625% | 0.057 |
| AR(0) — announcement | −1.367% | −0.226% | <0.001 |
| CAR[+2, +10] — drift | −1.931% | −1.796% | 0.870 |

## Pipeline

| Script | What it does | Output |
|---|---|---|
| `Day_2_Data_Collection.py` | Scans 7,997 SEC EDGAR filers, extracts address and SIC code for each | `all_companies.csv` |
| `Day_2_Data_Filter.py` | Filters to San Diego County life sciences firms | `sd_lifesci_companies.csv` |
| `Day_3_8-k_Collection.py.py` | Pulls 8-K metadata and filing text | `events_8-k.csv`|
| `Day_6_All_701_filings.py` | Classifies Item 7.01 filings via the Anthropic API | `llm_labels_701.csv` |
| `Day_6_All_801_filings.py` | 	Classifies Item 8.01 filings | `llm_labels_801.csv` |
| `Day_6_kappa.py` | Compares LLM labels against the 100 hand-labelled filings, reports Cohen's kappa and the confusion matrix | console |
| `Day_7_filings_merging.py` | Merges 7.01 and 8.01 labels, adds EARNINGS from Item 2.02, drops 206 confounded filings | `events_final.csv` |
| `Day_8_estimate_car.py` | Estimates a market model per event over [t−250, t−31] | `car.csv`, `ar_panel.csv` |
| `Day_9_Time_placebo_test.py` | Draws 20 matched non-event dates per event and runs the identical pipeline | `placebo_car.csv` |

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
