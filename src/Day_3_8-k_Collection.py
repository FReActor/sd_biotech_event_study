import pandas as pd
import requests
import time
from datetime import datetime
from zoneinfo import ZoneInfo
HEADERS = {'User-Agent': 'Charles Cheng zic065@ucsd.edu'}
ET = ZoneInfo("America/New_York")

# I downloaded all 8-K filings from 2019-01-01 to 2025-12-31 for the 73 life science companies in San Diego County and saved them to a CSV file.
rows = []
companies = pd.read_csv("data/processed/sd_lifesci_companies.csv", dtype=str)

for name, cik in zip(companies["name"], companies["cik"]):
    #print(name, cik)
    sub = requests.get(f"https://data.sec.gov/submissions/CIK{cik}.json",
                       headers=HEADERS).json()
    recent = sub["filings"]["recent"]

    for form, date, acc, adt, items in zip(
            recent["form"], recent["filingDate"],
            recent["accessionNumber"], recent["acceptanceDateTime"],
            recent["items"]):
        if form == "8-K" and "2019-01-01" <= date <= "2025-12-31":
            dt = datetime.fromisoformat(adt).astimezone(ET)
            rows.append({
                "cik": cik,
                "name": name,
                "accession": acc,
                "filing_date": date,
                "acceptance_et": dt.isoformat(),
                "after_hours": dt.hour >= 16,
                "items": items,
            })
            #print(date, dt.strftime("%Y-%m-%d %H:%M:%S %Z"), items)
    time.sleep(0.1)
events = pd.DataFrame(rows)
events.to_csv("data/processed/events_8-k.csv", index=False)
print(f"\nTotal 8-K: {len(events)}")
print(events["name"].nunique(), "of 73 companies")
print(events.groupby("name")["filing_date"].min().sort_values(ascending=False).head(10))