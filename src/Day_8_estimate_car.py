import numpy as np
import pandas as pd
 
PRICES = "data/processed/prices.csv"
EVENTS = "data/processed/events_aligned.csv"
OUT_CAR = "data/processed/car.csv"
OUT_PANEL = "data/processed/ar_panel.csv"
 
EST_START, EST_END = 250, 31        # [t0-250, t0-31]
MIN_ESTIMATION_DAYS = 100
 
WINDOWS = {
    "car_leak":  (-10, -2),
    "car_event": (0, 1),
    "car_drift": (2, 10),
    "car_aux":   (-1, 1),
}
 
PANEL_RANGE = (-10, 10)             # per-day AR for the event-time plot
 
 
# --- load ------------------------------------------------------------
prices = pd.read_csv(PRICES, parse_dates=["date"]).sort_values(["ticker", "date"])
prices["ret"] = prices.groupby("ticker")["adj_close"].pct_change()
 
spy = prices[prices["ticker"] == "SPY"].set_index("date")
trading_days = np.sort(spy.index.unique().values)
n_days = len(trading_days)
 
mkt_ret = spy["ret"].reindex(trading_days).to_numpy()
 
ret_arrays = {}
for ticker, grp in prices[prices["ticker"] != "SPY"].groupby("ticker"):
    ret_arrays[ticker] = (
        grp.set_index("date")["ret"].reindex(trading_days).to_numpy()
    )
 
events = pd.read_csv(EVENTS, parse_dates=["t0"])
 
flag_cols = [
    "no_price_at_t0",
    "insufficient_estimation_window",
    "high_zero_return_share",
    "insufficient_post_window",
]
events = events[~events[flag_cols].any(axis=1)].copy()
print(f"Events passing exclusion criteria: {len(events)}")
 
 
# --- estimation ------------------------------------------------------
def fit_market_model(stock_ret, idx):
    """OLS of stock returns on SPY over the estimation window.
 
    Returns (alpha, beta, resid_sd, n_obs), or None if too few
    overlapping observations.
    """
    lo, hi = max(idx - EST_START, 0), idx - EST_END + 1
    if hi <= lo:
        return None
 
    y = stock_ret[lo:hi]
    x = mkt_ret[lo:hi]
 
    ok = ~(np.isnan(y) | np.isnan(x))
    if ok.sum() < MIN_ESTIMATION_DAYS:
        return None
 
    y, x = y[ok], x[ok]
 
    # Closed-form OLS. Faster than statsmodels across ~2,300 fits, and
    # the coefficients are all that is needed here.
    x_mean, y_mean = x.mean(), y.mean()
    xc, yc = x - x_mean, y - y_mean
    denom = (xc ** 2).sum()
    if denom == 0:
        return None
 
    beta = (xc * yc).sum() / denom
    alpha = y_mean - beta * x_mean
 
    resid = y - (alpha + beta * x)
    resid_sd = np.sqrt((resid ** 2).sum() / (len(y) - 2))
 
    return alpha, beta, resid_sd, int(len(y))
 
 
rows = []
panel_rows = []
n_failed = 0
 
for ev in events.itertuples():
    stock_ret = ret_arrays.get(ev.ticker)
    if stock_ret is None:
        n_failed += 1
        continue
 
    idx = int(ev.t0_idx)
    fit = fit_market_model(stock_ret, idx)
    if fit is None:
        n_failed += 1
        continue
 
    alpha, beta, resid_sd, n_obs = fit
 
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
        "accession": ev.accession,
        "ticker": ev.ticker,
        "name": ev.name,
        "label": ev.label,
        "t0": ev.t0,
        "alpha": alpha,
        "beta": beta,
        "resid_sd": resid_sd,
        "n_est": n_obs,
        "ar0": ar_by_offset.get(0, np.nan),
    }
 
    for name, (lo, hi) in WINDOWS.items():
        vals = [ar_by_offset[o] for o in range(lo, hi + 1) if o in ar_by_offset]
        expected = hi - lo + 1
        # Require the complete window. A partial CAR is not comparable to
        # a full one, and quietly summing fewer days would understate the
        # magnitude without any visible signal that it happened.
        row[name] = sum(vals) if len(vals) == expected else np.nan
        row[f"{name}_n"] = len(vals)
 
    rows.append(row)
 
    for offset, ar in ar_by_offset.items():
        panel_rows.append({
            "accession": ev.accession,
            "label": ev.label,
            "offset": offset,
            "ar": ar,
        })
 
car = pd.DataFrame(rows)
panel = pd.DataFrame(panel_rows)
 
car.to_csv(OUT_CAR, index=False)
panel.to_csv(OUT_PANEL, index=False)
 
print(f"Estimated: {len(car)}   failed: {n_failed}")
 
 
# --- diagnostics -----------------------------------------------------
print("\n--- Beta distribution ---")
print(car["beta"].describe().round(3).to_string())
extreme = car[(car["beta"] < -1) | (car["beta"] > 5)]
print(f"Beta outside [-1, 5]: {len(extreme)}")
if len(extreme):
    print(extreme[["ticker", "t0", "beta", "n_est"]].head(10).to_string(index=False))
 
print("\n--- Events by label ---")
print(car["label"].value_counts().to_string())
 
MAIN_LABELS = ["CLINICAL", "EARNINGS", "REGULATORY"]
main = car[car["label"].isin(MAIN_LABELS)]
 
print("\n--- Complete windows by label ---")
for w in WINDOWS:
    counts = main.groupby("label")[w].apply(lambda s: s.notna().sum())
    print(f"{w:12s} " + "  ".join(f"{k}={v}" for k, v in counts.items()))
 
print("\n--- Mean CAR by label, percent (raw, no tests yet) ---")
summary = main.groupby("label")[list(WINDOWS) + ["ar0"]].mean() * 100
print(summary.round(3).to_string())
 
print("\n--- Median CAR by label, percent ---")
med = main.groupby("label")[list(WINDOWS) + ["ar0"]].median() * 100
print(med.round(3).to_string())
 
print(f"\nSaved {OUT_CAR} and {OUT_PANEL}")