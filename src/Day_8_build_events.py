"""
Align 8-K filings to trading days and flag exclusion criteria.

Nothing is dropped here. Every event is written out with boolean flags so
the exclusion table can be inspected before deciding on thresholds.

Run: py src/build_events.py
"""

import numpy as np
import pandas as pd

PRICES = "data/processed/prices.csv"
EVENTS = "data/processed/events_final.csv"
COMPANIES = "data/processed/sd_lifesci_companies.csv"
OUT = "data/processed/events_aligned.csv"

LABEL_PRIORITY = {
    "CLINICAL": 0,
    "REGULATORY": 1,
    "EARNINGS": 2,
    "PRESENTATION": 3,
    "OTHER": 4,
}

EST_WINDOW = (250, 31)        # [t0-250, t0-31], inclusive
MIN_ESTIMATION_DAYS = 100
ZERO_RETURN_WINDOW = 60       # trading days strictly before t0
ZERO_RETURN_THRESHOLD = 0.20
MIN_POST_DAYS = 11            # need through t0+10 for the drift window


# --- Step 1: returns -------------------------------------------------
prices = pd.read_csv(PRICES, parse_dates=["date"])
prices = prices.sort_values(["ticker", "date"])
prices["ret"] = prices.groupby("ticker")["adj_close"].pct_change()

spy = prices[prices["ticker"] == "SPY"].set_index("date")
stocks = prices[prices["ticker"] != "SPY"]


# --- Step 2: trading calendar ----------------------------------------
trading_days = np.sort(spy.index.unique().values)
n_days = len(trading_days)
print(f"Trading calendar: {n_days} days, "
      f"{pd.Timestamp(trading_days[0]).date()} to "
      f"{pd.Timestamp(trading_days[-1]).date()}")

# Reindex each ticker onto the full calendar so positions line up.
# NaN marks days the ticker did not trade.
price_arrays, ret_arrays = {}, {}
for ticker, grp in stocks.groupby("ticker"):
    s = grp.set_index("date")
    price_arrays[ticker] = s["adj_close"].reindex(trading_days).to_numpy()
    ret_arrays[ticker] = s["ret"].reindex(trading_days).to_numpy()


# --- Step 3: align t0 -------------------------------------------------
events = pd.read_csv(EVENTS, dtype=str)
companies = pd.read_csv(COMPANIES, dtype=str)
events = events.merge(companies[["cik", "ticker"]], on="cik", how="left")

missing_ticker = events["ticker"].isna().sum()
if missing_ticker:
    print(f"WARNING: {missing_ticker} events have no ticker after merge")

# acceptance_et carries a UTC offset that changes with daylight saving
# (-04:00 in summer, -05:00 in winter), so pandas refuses to parse the
# column directly. Parse as UTC first, then convert back to Eastern.
# Converting to UTC and stopping there would break the 16:00 test, since
# the hour must be Eastern.
events["acceptance_dt"] = (
    pd.to_datetime(events["acceptance_et"], utc=True)
      .dt.tz_convert("America/New_York")
)

print("\nFiling hour distribution (US/Eastern):")
print("Expect peaks pre-market (6-9) and after close (16-18),")
print("with few filings during the 9:30-16:00 session.")
hour_counts = events["acceptance_dt"].dt.hour.value_counts().sort_index()
for hour, n in hour_counts.items():
    bar = "#" * max(1, int(n / max(hour_counts) * 50))
    print(f"  {hour:2d}:00  {n:5d}  {bar}")

after_close = events["acceptance_dt"].dt.hour >= 16
print(f"\nAfter-hours filings (t0 rolls to next trading day): "
      f"{after_close.sum()} of {len(events)}")

# tz_localize(None) drops the offset so the dates compare cleanly against
# the naive trading calendar.
target_date = (
    events["acceptance_dt"].dt.tz_localize(None).dt.normalize()
    + pd.to_timedelta(after_close.astype(int), unit="D")
)

t0_idx = np.searchsorted(trading_days, target_date.values.astype("datetime64[ns]"))
events["t0_out_of_range"] = t0_idx >= n_days
events["t0_idx"] = np.clip(t0_idx, 0, n_days - 1)
events["t0"] = trading_days[events["t0_idx"]]


# --- Step 4: deduplicate by (ticker, t0) ------------------------------
events["label_priority"] = events["label"].map(LABEL_PRIORITY)
# Unknown labels (NO_TEXT, INVALID:...) sort last
events["label_priority"] = events["label_priority"].fillna(99)

events_sorted = events.sort_values(["ticker", "t0", "label_priority"])

before_by_label = events["label"].value_counts()

group_sizes = events_sorted.groupby(["ticker", "t0"]).size()
n_groups_collapsed = int((group_sizes > 1).sum())
n_rows_removed = int((group_sizes - 1).clip(lower=0).sum())

dedup = events_sorted.drop_duplicates(subset=["ticker", "t0"], keep="first").copy()
after_by_label = dedup["label"].value_counts()

print("\n--- Deduplication ---")
print(f"Events before: {len(events)}   after: {len(dedup)}")
print(f"Groups with multiple filings on the same (ticker, t0): {n_groups_collapsed}")
print(f"Rows removed: {n_rows_removed}")

comparison = pd.DataFrame({"before": before_by_label, "after": after_by_label})
comparison["removed"] = comparison["before"] - comparison["after"]
print("\n", comparison.fillna(0).astype(int).to_string())


# --- Step 5: exclusion flags (report only) ----------------------------
def window_stats(arr, start, end):
    """Valid and zero counts within arr[start:end], clipped to bounds."""
    start, end = max(start, 0), min(end, len(arr))
    if end <= start:
        return 0, 0
    window = arr[start:end]
    valid = ~np.isnan(window)
    return int(valid.sum()), int((window[valid] == 0).sum())


flags = []
for row in dedup.itertuples():
    ticker, idx = row.ticker, row.t0_idx
    price_arr = price_arrays.get(ticker)
    ret_arr = ret_arrays.get(ticker)

    if price_arr is None or ret_arr is None:
        flags.append((True, True, True, True))
        continue

    no_price = bool(np.isnan(price_arr[idx]))

    est_valid, _ = window_stats(ret_arr, idx - EST_WINDOW[0], idx - EST_WINDOW[1] + 1)
    insufficient_est = est_valid < MIN_ESTIMATION_DAYS

    zr_valid, zr_zero = window_stats(ret_arr, idx - ZERO_RETURN_WINDOW, idx)
    zero_share = (zr_zero / zr_valid) if zr_valid > 0 else 1.0
    high_zero = zero_share > ZERO_RETURN_THRESHOLD

    insufficient_post = (n_days - 1 - idx) < MIN_POST_DAYS

    flags.append((no_price, insufficient_est, high_zero, insufficient_post))

flag_cols = [
    "no_price_at_t0",
    "insufficient_estimation_window",
    "high_zero_return_share",
    "insufficient_post_window",
]
dedup[flag_cols] = pd.DataFrame(flags, index=dedup.index, columns=flag_cols)

print("\n--- Exclusion criteria (nothing dropped yet) ---")
print(f"No price on t0:                        {dedup['no_price_at_t0'].sum()}")
print(f"Estimation window < {MIN_ESTIMATION_DAYS} valid days:     "
      f"{dedup['insufficient_estimation_window'].sum()}")
print(f"Zero-return share > {ZERO_RETURN_THRESHOLD:.0%} pre-event:   "
      f"{dedup['high_zero_return_share'].sum()}")
print(f"Fewer than {MIN_POST_DAYS} trading days after t0:  "
      f"{dedup['insufficient_post_window'].sum()}")

any_flag = dedup[flag_cols].any(axis=1)
print(f"\nEvents failing at least one criterion:  {any_flag.sum()}")
print(f"Events passing all criteria:           {(~any_flag).sum()}")

print("\nSurviving events by label:")
print(dedup.loc[~any_flag, "label"].value_counts())


out_cols = (["accession", "cik", "ticker", "name", "filing_date",
             "acceptance_et", "after_hours", "items", "label",
             "t0", "t0_idx", "t0_out_of_range"] + flag_cols)
dedup[out_cols].to_csv(OUT, index=False)
print(f"\nSaved {len(dedup)} events to {OUT}")