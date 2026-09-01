import pandas as pd
p = pd.read_csv("data/processed/placebo_car.csv")

# 各组 car_leak 的分布
for label in ["CLINICAL", "EARNINGS", "REGULATORY"]:
    v = p.loc[p["label"] == label, "car_leak"].dropna() * 100
    print(f"\n{label}  n={len(v)}")
    print(f"  mean {v.mean():7.2f}  median {v.median():7.2f}")
    print(f"  p25 {v.quantile(.25):7.2f}  p75 {v.quantile(.75):7.2f}")
    print(f"  skew {v.skew():6.2f}")

# 是不是集中在少数几只股票
cl = p[p["label"] == "CLINICAL"]
by_ticker = cl.groupby("ticker")["car_leak"].agg(["median", "count"])
print("\n最负的 10 只:")
print((by_ticker.sort_values("median").head(10) * 100).round(2).to_string())