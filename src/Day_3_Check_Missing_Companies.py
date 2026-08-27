# After running the code, I found that 8-K filings for 5 companies were missing. Next is to search up the companies.
import time

import pandas as pd

events = pd.read_csv("data/processed/events_8-k.csv", dtype=str)
companies = pd.read_csv("data/processed/sd_lifesci_companies.csv", dtype=str)

have = set(events["name"])
missing = companies[~companies["name"].isin(have)]["name"]
print(missing.tolist())

#check the missing companies' filings and see if they are out of the date I chose
import requests
HEADERS = {"User-Agent": "Charles Cheng zic065@ucsd.edu"}

miss_ciks = companies[companies["name"].isin(missing)][["name", "cik"]]

for name, cik in zip(miss_ciks["name"], miss_ciks["cik"]):
    sub = requests.get(f"https://data.sec.gov/submissions/CIK{cik}.json",
                       headers=HEADERS).json()
    r = sub["filings"]["recent"]
    forms = set(r["form"])
    dates = r["filingDate"]
    print(f"\n{name}")
    print(f"  forms: {sorted(forms)}")
    if dates:
        print(f"  range: {min(dates)} to {max(dates)}")

#Out of the 5 companies, 1 doesn't have 8-k filings(submits 6-k instead), and 3 were listed after 2025-12-31. The only company that has 8-k filings in the date range is "Aethlon Medical, Inc." and I will download its filings.
r = sub["filings"]["recent"]
for f, d in zip(r["form"], r["filingDate"]):
    if f == "8-K":
        print(d)
# I downloaded the data and realized that it only has 8-k in 2026.

# This made me decide to check all of the companies to see if they have 6-k filings
for name, cik in zip(companies["name"], companies["cik"]):
    sub = requests.get(f"https://data.sec.gov/submissions/CIK{cik}.json",
                       headers=HEADERS).json()
    forms = set(sub["filings"]["recent"]["form"])
    if "6-K" in forms or "20-F" in forms:
        print(name, "has foreign forms")
    time.sleep(0.1)
# tunrs out only 3 companies have foreign forms, and only 1(connect biopharma) is in the date range. I will download the data for further examine
for f, d in zip(r["form"], r["filingDate"]):
    if f in ("8-K", "6-K"):
        print(f, d)

# After analyzing the outcome, I decided to not keep the company
EXCLUDE = ["Connect Biopharma"]

events = events[~events["name"].str.contains("|".join(EXCLUDE))]
events.to_csv("data/processed/events_8-k.csv", index=False)
print(len(events))