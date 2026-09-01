from pathlib import Path
 
import numpy as np
import pandas as pd
 
PRICES = "data/processed/prices.csv"
EVENTS = "data/processed/events_aligned.csv"
OUT = "data/processed/placebo_car.csv"
 
SEED = 20260901
N_DRAWS = 20                  # placebo events per real event
EXCLUSION_RADIUS = 5        # trading days around any real event to avoid
 
EST_START, EST_END = 250, 31
MIN_ESTIMATION_DAYS = 100
 
WINDOWS = {
    "car_leak":  (-10, -2),
    "car_event": (0, 1),
    "car_drift": (2, 10),
    "car_aux":   (-1, 1),
}
PANEL_RANGE = (-10, 10)
 
MAIN_LABELS = ["CLINICAL", "EARNINGS", "REGULATORY"]
 
rng = np.random.default_rng(SEED)
 
 
# --- load -------------------------------------------------------------
prices = pd.read_csv(PRICES, parse_dates=["date"]).sort_values(["ticker", "date"])
prices["ret"] = prices.groupby("ticker")["adj_close"].pct_change()
 
spy = prices[prices["ticker"] == "SPY"].set_index("date")
trading_days = np.sort(spy.index.unique().values)
n_days = len(trading_days)
mkt_ret = spy["ret"].reindex(trading_days).to_numpy()
 
ret_arrays, price_arrays = {}, {}
for ticker, grp in prices[prices["ticker"] != "SPY"].groupby("ticker"):
    s = grp.set_index("date")
    ret_arrays[ticker] = s["ret"].reindex(trading_days).to_numpy()
    price_arrays[ticker] = s["adj_close"].reindex(trading_days).to_numpy()
 
# Calendar month for each trading-day index, used for matching
cal = pd.DatetimeIndex(trading_days)
month_key = np.array([f"{y}-{m:02d}" for y, m in zip(cal.year, cal.month)])
 
events = pd.read_csv(EVENTS, parse_dates=["t0"])
flag_cols = [
    "no_price_at_t0",
    "insufficient_estimation_window",
    "high_zero_return_share",
    "insufficient_post_window",
]
events = events[~events[flag_cols].any(axis=1)]
events = events[events["label"].isin(MAIN_LABELS)].copy()
print(f"Real events to match: {len(events)}")
 
# Every real event index per ticker, so placebos can avoid their neighbourhoods.
# ALL events are excluded, not just the ones in MAIN_LABELS, since a
# presentation or an M&A filing would contaminate a placebo just as much.
all_events = pd.read_csv(EVENTS, parse_dates=["t0"])
real_idx_by_ticker = (
    all_events.groupby("ticker")["t0_idx"].apply(lambda s: set(s.astype(int)))
    .to_dict()
)
 
 
# --- market model (identical to estimate_car.py) ----------------------
def fit_market_model(stock_ret, idx):
    lo, hi = max(idx - EST_START, 0), idx - EST_END + 1
    if hi <= lo:
        return None
    y, x = stock_ret[lo:hi], mkt_ret[lo:hi]
    ok = ~(np.isnan(y) | np.isnan(x))
    if ok.sum() < MIN_ESTIMATION_DAYS:
        return None
    y, x = y[ok], x[ok]
    xm, ym = x.mean(), y.mean()
    xc, yc = x - xm, y - ym
    denom = (xc ** 2).sum()
    if denom == 0:
        return None
    beta = (xc * yc).sum() / denom
    alpha = ym - beta * xm
    return alpha, beta
 
 
def candidate_indices(ticker, real_idx):
    """Trading days in the same calendar month, far from any real event."""
    target_month = month_key[real_idx]
    same_month = np.flatnonzero(month_key == target_month)
 
    blocked = real_idx_by_ticker.get(ticker, set())
    ret_arr = ret_arrays[ticker]
    price_arr = price_arrays[ticker]
 
    out = []
    for j in same_month:
        if any(abs(j - b) <= EXCLUSION_RADIUS for b in blocked):
            continue
        if j < EST_START or j + PANEL_RANGE[1] >= n_days:
            continue
        if np.isnan(price_arr[j]):
            continue
        out.append(j)
    return out
 
 
# --- draw placebos ----------------------------------------------------
rows, panel_rows = [], []
n_no_candidate, n_no_fit = 0, 0
 
for ev in events.itertuples():
    ticker = ev.ticker
    if ticker not in ret_arrays:
        continue
 
    cands = candidate_indices(ticker, int(ev.t0_idx))
    if not cands:
        n_no_candidate += 1
        continue
 
    for _ in range(N_DRAWS):
        idx = int(rng.choice(cands))
        stock_ret = ret_arrays[ticker]
 
        fit = fit_market_model(stock_ret, idx)
        if fit is None:
            n_no_fit += 1
            continue
        alpha, beta = fit
 
        ar_by_offset = {}
        for offset in range(PANEL_RANGE[0], PANEL_RANGE[1] + 1):
            j = idx + offset
            if j < 0 or j >= n_days:
                continue
            r, m = stock_ret[j], mkt_ret[j]
            if np.isnan(r) or np.isnan(m):
                continue
            ar_by_offset[offset] = r - (alpha + beta * m)
 
        row = {
            "ticker": ticker,
            "label": ev.label,
            "real_t0": ev.t0,
            "placebo_t0": pd.Timestamp(trading_days[idx]),
            "ar0": ar_by_offset.get(0, np.nan),
        }
        for name, (lo, hi) in WINDOWS.items():
            vals = [ar_by_offset[o] for o in range(lo, hi + 1) if o in ar_by_offset]
            row[name] = sum(vals) if len(vals) == (hi - lo + 1) else np.nan
 
        rows.append(row)
        for offset, ar in ar_by_offset.items():
            panel_rows.append({"label": ev.label, "offset": offset, "ar": ar})
 
placebo = pd.DataFrame(rows)
placebo.to_csv(OUT, index=False)
 
print(f"Placebo events drawn: {len(placebo)}")
print(f"  no candidate date in month: {n_no_candidate}")
print(f"  estimation failed:          {n_no_fit}")
 
 
# --- compare against the real events ----------------------------------
real = pd.read_csv("data/processed/car.csv")
real = real[real["label"].isin(MAIN_LABELS)]
 
print("\n" + "=" * 62)
print("MEDIAN CAR, computed per event then aggregated (the correct way)")
print("=" * 62)
 
cols = list(WINDOWS) + ["ar0"]
for label in MAIN_LABELS:
    r = real[real["label"] == label]
    p = placebo[placebo["label"] == label]
    print(f"\n{label}   real n={len(r)}   placebo n={len(p)}")
    print(f"{'window':12s} {'real':>10s} {'placebo':>10s} {'diff':>10s}")
    for c in cols:
        rv = r[c].median() * 100
        pv = p[c].median() * 100
        print(f"{c:12s} {rv:10.3f} {pv:10.3f} {rv - pv:10.3f}")
 
print("\n" + "=" * 62)
print("MEAN CAR")
print("=" * 62)
for label in MAIN_LABELS:
    r = real[real["label"] == label]
    p = placebo[placebo["label"] == label]
    print(f"\n{label}")
    print(f"{'window':12s} {'real':>10s} {'placebo':>10s} {'diff':>10s}")
    for c in cols:
        rv = r[c].mean() * 100
        pv = p[c].mean() * 100
        print(f"{c:12s} {rv:10.3f} {pv:10.3f} {rv - pv:10.3f}")
 
print("\n" + "=" * 62)
print("PLACEBO EVENT-TIME PATH (median of per-day AR, cumulated)")
print("If this declines monotonically, the drift is a model artifact.")
print("=" * 62)
pan = pd.DataFrame(panel_rows)
for label in MAIN_LABELS:
    sub = pan[pan["label"] == label]
    daily = sub.groupby("offset")["ar"].median().sort_index()
    cum = daily.cumsum() * 100
    print(f"\n{label}:")
    print("  " + "  ".join(f"{o:+d}:{v:6.2f}" for o, v in cum.items()))
 
print(f"\nSaved {OUT}")