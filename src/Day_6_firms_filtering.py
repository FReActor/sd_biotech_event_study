import re, pandas as pd
from pathlib import Path

SD = re.compile(r"san\s*diego|carlsbad|la\s*jolla|solana\s*beach|escondido|"
                r"oceanside|encinitas|poway|vista|san\s*marcos|el\s*cajon|"
                r"del\s*mar|chula\s*vista", re.IGNORECASE)
ADDR = re.compile(r"address\s+of\s+principal\s+executive\s+offices", re.IGNORECASE)

events = pd.read_csv("data/processed/events_8-k.csv", dtype=str)

rows = []
for _, r in events.iterrows():
    p = Path(f"data/raw/filings/{r['accession']}.txt")
    if not p.exists():
        rows.append({**r, "in_sd": None})
        continue
    t = p.read_text(encoding="utf-8", errors="ignore")
    m = ADDR.search(t)
    if m:
        addr_block = t[max(0, m.start()-250):m.start()]
        rows.append({**r, "in_sd": bool(SD.search(addr_block))})
    else:
        rows.append({**r, "in_sd": None})

df = pd.DataFrame(rows)
print(df["in_sd"].value_counts(dropna=False))

known = df[df["in_sd"].notna()]
s = known.groupby("name")["in_sd"].agg(["sum", "count"])
s["pct_sd"] = s["sum"] / s["count"]
print(s[s["count"] >= 5].sort_values("pct_sd").head(25).to_string())

summary = df.groupby("name")["in_sd"].agg(["sum", "count"])
summary["pct_sd"] = summary["sum"] / summary["count"]
print(summary.sort_values("pct_sd").head(25).to_string())

false_rows = df[df["in_sd"] == False]
print(false_rows["name"].value_counts().head(15))

false_rows = df[df["in_sd"] == False]
ADDR = re.compile(r"address\s+of\s+principal\s+executive", re.IGNORECASE)

for name in ["GYRE THERAPEUTICS, INC.", "Zura Bio Ltd",
             "KIORA PHARMACEUTICALS INC", "LIGAND PHARMACEUTICALS INC",
             "CAPRICOR THERAPEUTICS, INC."]:
    sub = false_rows[false_rows["name"] == name].head(2)
    for _, r in sub.iterrows():
        p = Path(f"data/raw/filings/{r['accession']}.txt")
        if not p.exists():
            continue
        t = p.read_text(encoding="utf-8", errors="ignore")
        m = ADDR.search(t)
        if m:
            print(f"\n{name} | {r['filing_date']}")
            print("   ", t[max(0, m.start()-200):m.start()].strip()[-150:])

known = df[df["in_sd"].notna()]
pct = known.groupby("name")["in_sd"].mean()

THRESHOLD = 0.5
drop = pct[pct < THRESHOLD].index.tolist()

print(f"Dropping {len(drop)} companies:")
for n in drop:
    print(f"  {n}  ({pct[n]:.2f})")

clean = df[~df["name"].isin(drop)]
print(f"\nFilings: {len(df)} -> {len(clean)}")
print(f"Companies: {df['name'].nunique()} -> {clean['name'].nunique()}")

clean.to_csv("data/processed/events_clean.csv", index=False)