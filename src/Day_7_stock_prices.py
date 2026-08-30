import time
from pathlib import Path

import pandas as pd
import yfinance as yf

EVENTS = Path("data/processed/events_final.csv")
COMPANIES = Path("data/processed/sd_lifesci_companies.csv")
RAW_DIR = Path("data/raw/prices")
OUT = Path("data/processed/prices.csv")

START = "2018-01-01"
END = "2026-03-31"

RAW_DIR.mkdir(parents=True, exist_ok=True)

events = pd.read_csv(EVENTS, dtype=str)
companies = pd.read_csv(COMPANIES, dtype=str)

tickers = companies[companies["cik"].isin(events["cik"].unique())]["ticker"].dropna().unique().tolist()
tickers = sorted(set(tickers) | {"SPY"})
print(f"{len(tickers)} tickers to fetch (including SPY)")

def fetch_ticker(ticker):
    cache_path = RAW_DIR / f"{ticker}.csv"
    if cache_path.exists():
        if cache_path.stat().st_size == 0:
            return pd.DataFrame()
        return pd.read_csv(cache_path, parse_dates=["Date"])

    try:
        df = yf.download(ticker, start=START, end=END, auto_adjust=False, progress=False)
    except Exception as e:
        print(f"  ERROR fetching {ticker}: {e}")
        df = pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    if df.empty:
        cache_path.touch()  # empty file marks "fetched, no data" so we don't refetch
        return df

    df = df.reset_index()
    df.to_csv(cache_path, index=False)
    return df

no_data = []
long_rows = []
coverage_rows = []

for ticker in tickers:
    df = fetch_ticker(ticker)
    time.sleep(0.2)

    if df.empty:
        no_data.append(ticker)
        continue

    df = df[["Date", "Adj Close", "Volume"]].dropna(subset=["Adj Close"]).sort_values("Date")
    df.columns = ["date", "adj_close", "volume"]
    df["ticker"] = ticker
    long_rows.append(df[["ticker", "date", "adj_close", "volume"]])

    pre_2019 = df[df["date"] < "2019-01-01"]
    zero_return_share = (df["adj_close"].diff() == 0).mean()

    coverage_rows.append({
        "ticker": ticker,
        "first_date": df["date"].min(),
        "last_date": df["date"].max(),
        "rows_before_2019": len(pre_2019),
        "zero_return_share": zero_return_share,
    })

prices = pd.concat(long_rows, ignore_index=True)
prices.to_csv(OUT, index=False)
print(f"\nSaved {len(prices)} rows to {OUT}")

coverage = pd.DataFrame(coverage_rows)
pd.set_option("display.max_rows", None)
pd.set_option("display.width", 200)

print(f"\nTickers with no data at all ({len(no_data)}): {no_data}")

print("\nFirst/last available date per ticker:")
print(coverage[["ticker", "first_date", "last_date"]].to_string(index=False))

thin = coverage[coverage["rows_before_2019"] < 250]
print(f"\nTickers with fewer than 250 rows before 2019-01-01 ({len(thin)}):")
print(thin[["ticker", "rows_before_2019"]].to_string(index=False))

print("\nZero-return-day share per ticker:")
print(coverage[["ticker", "zero_return_share"]].to_string(index=False))