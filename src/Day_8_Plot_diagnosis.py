
from pathlib import Path
 
import matplotlib
matplotlib.use("Agg")            # write files, do not open a window
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
 
CAR = "data/processed/car.csv"
PANEL = "data/processed/ar_panel.csv"
FIGDIR = Path("figures")
FIGDIR.mkdir(exist_ok=True)
 
MAIN = ["CLINICAL", "EARNINGS", "REGULATORY"]
COLORS = {"CLINICAL": "#c1440e", "EARNINGS": "#1f6f8b", "REGULATORY": "#6b8e23"}
 
car = pd.read_csv(CAR, parse_dates=["t0"])
panel = pd.read_csv(PANEL)
 
car = car[car["label"].isin(MAIN)]
panel = panel[panel["label"].isin(MAIN)]
 
 
# --- Figure 1: AR(0) distribution ------------------------------------
fig, axes = plt.subplots(1, 3, figsize=(14, 4), sharey=False)
 
for ax, label in zip(axes, MAIN):
    vals = car.loc[car["label"] == label, "ar0"].dropna() * 100
    ax.hist(vals, bins=60, color=COLORS[label], alpha=0.75)
    ax.axvline(0, color="black", lw=0.8)
    ax.axvline(vals.mean(), color="red", ls="--", lw=1.2,
               label=f"mean {vals.mean():.2f}%")
    ax.axvline(vals.median(), color="black", ls=":", lw=1.2,
               label=f"median {vals.median():.2f}%")
    ax.set_title(f"{label}  (n={len(vals)})")
    ax.set_xlabel("AR on t0 (%)")
    ax.legend(fontsize=8)
 
axes[0].set_ylabel("count")
fig.suptitle("Announcement-day abnormal return: mean vs median")
fig.tight_layout()
fig.savefig(FIGDIR / "fig1_ar0_distribution.png", dpi=150)
plt.close(fig)
 
 
# --- Figure 2: same thing, zoomed to the bulk -------------------------
# The full range is dominated by a handful of extreme clinical outcomes,
# which hides the shape of the mass. Clip the x-axis to see it.
fig, axes = plt.subplots(1, 3, figsize=(14, 4))
 
for ax, label in zip(axes, MAIN):
    vals = car.loc[car["label"] == label, "ar0"].dropna() * 100
    clipped = vals[(vals > -30) & (vals < 30)]
    ax.hist(clipped, bins=50, color=COLORS[label], alpha=0.75)
    ax.axvline(0, color="black", lw=0.8)
    ax.set_title(f"{label}  ({len(vals) - len(clipped)} outside +/-30%)")
    ax.set_xlabel("AR on t0 (%), clipped")
 
axes[0].set_ylabel("count")
fig.suptitle("Same distributions, clipped to +/-30%")
fig.tight_layout()
fig.savefig(FIGDIR / "fig2_ar0_clipped.png", dpi=150)
plt.close(fig)
 
 
# --- Figure 3: event-time cumulative path -----------------------------
# The core figure of the paper. Mean and median are plotted separately
# because they tell different stories.
fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharex=True)
 
for stat, ax in zip(["mean", "median"], axes):
    for label in MAIN:
        sub = panel[panel["label"] == label]
        by_offset = sub.groupby("offset")["ar"].agg(stat).sort_index()
        cum = by_offset.cumsum() * 100
        ax.plot(cum.index, cum.values, marker="o", ms=3,
                color=COLORS[label], label=label)
 
    ax.axvline(0, color="black", lw=0.8, ls="--")
    ax.axhline(0, color="black", lw=0.5)
    ax.set_title(f"Cumulative abnormal return ({stat})")
    ax.set_xlabel("trading days relative to t0")
    ax.grid(alpha=0.25)
 
axes[0].set_ylabel("CAR (%)")
axes[0].legend()
fig.tight_layout()
fig.savefig(FIGDIR / "fig3_event_time_car.png", dpi=150)
plt.close(fig)
 
 
# --- Figure 4: drift regression scatter -------------------------------
# Q2: does the day-0 move predict what happens over the next nine days?
fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
 
for ax, label in zip(axes, MAIN):
    sub = car[car["label"] == label].dropna(subset=["ar0", "car_drift"])
    x = sub["ar0"] * 100
    y = sub["car_drift"] * 100
 
    ax.scatter(x, y, s=10, alpha=0.4, color=COLORS[label])
 
    if len(sub) > 2:
        b, a = np.polyfit(x, y, 1)
        xs = np.linspace(x.min(), x.max(), 50)
        ax.plot(xs, a + b * xs, color="black", lw=1.4,
                label=f"slope {b:.3f}")
        ax.legend(fontsize=8)
 
    ax.axhline(0, color="black", lw=0.5)
    ax.axvline(0, color="black", lw=0.5)
    ax.set_title(f"{label}  (n={len(sub)})")
    ax.set_xlabel("AR on t0 (%)")
    ax.grid(alpha=0.25)
 
axes[0].set_ylabel("CAR [+2, +10] (%)")
fig.suptitle("Drift: positive slope = underreaction, negative = overreaction")
fig.tight_layout()
fig.savefig(FIGDIR / "fig4_drift_scatter.png", dpi=150)
plt.close(fig)
 
 
# --- numbers to read alongside the plots ------------------------------
print("=== Skewness and tails of AR(0) ===\n")
for label in MAIN:
    v = car.loc[car["label"] == label, "ar0"].dropna() * 100
    print(f"{label}  (n={len(v)})")
    print(f"  mean {v.mean():7.3f}   median {v.median():7.3f}")
    print(f"  skew {v.skew():7.3f}   kurtosis {v.kurtosis():7.3f}")
    print(f"  min  {v.min():7.2f}   max    {v.max():7.2f}")
    print(f"  share negative: {(v < 0).mean():.1%}")
    print(f"  p1 {v.quantile(0.01):7.2f}  p99 {v.quantile(0.99):7.2f}\n")
 
print("=== Largest 5 absolute AR(0), clinical ===")
cl = car[car["label"] == "CLINICAL"].dropna(subset=["ar0"]).copy()
cl["abs_ar0"] = cl["ar0"].abs()
print(cl.nlargest(5, "abs_ar0")[["ticker", "t0", "ar0", "car_drift"]]
        .assign(ar0=lambda d: (d["ar0"] * 100).round(1),
                car_drift=lambda d: (d["car_drift"] * 100).round(1))
        .to_string(index=False))
 
print(f"\nFigures written to {FIGDIR}/")


p = pd.read_csv("data/processed/prices.csv", parse_dates=["date"])
eq = p[(p["ticker"] == "EQ") & (p["date"].between("2020-07-01", "2020-07-31"))]
print(eq[["date", "adj_close", "volume"]].to_string(index=False))