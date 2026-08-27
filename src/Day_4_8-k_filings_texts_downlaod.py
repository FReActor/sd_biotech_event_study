import os
import re
import time
import pandas as pd
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Charles Cheng zic065@ucsd.edu"}
RAW_DIR = "data/raw/filings"
os.makedirs(RAW_DIR, exist_ok=True)

SKIP_SUFFIXES = (".xsd", ".xml", ".jpg", ".jpeg", ".png", ".gif", ".zip",
                  ".css", ".js", ".xlsx")
SKIP_NAMES = {"filingsummary.xml", "metalinks.json"}
TEXT_ITEMS = {"5.02", "1.01", "7.01", "8.01"}

def item_set(s):
    return {i.strip() for i in str(s).split(",")}

def is_skippable(name):
    lname = name.lower()
    if lname.endswith(SKIP_SUFFIXES) or lname in SKIP_NAMES:
        return True
    if "-index" in lname:
        return True
    if re.match(r"^r\d+\.htm$", lname):
        return True
    return False

def fetch_text(url):
    html = requests.get(url, headers=HEADERS).text
    time.sleep(0.12)
    return BeautifulSoup(html, "html.parser").get_text(separator=" ", strip=True)

def get_primary_doc_map(cik):
    sub = requests.get(f"https://data.sec.gov/submissions/CIK{cik}.json", headers=HEADERS).json()
    time.sleep(0.12)
    recent = sub["filings"]["recent"]
    return dict(zip(recent["accessionNumber"], recent["primaryDocument"]))

def cache_filing_text(cik, accession, primary_doc):
    cache_path = f"{RAW_DIR}/{accession}.txt"
    if os.path.exists(cache_path):
        return

    cik_int = int(cik)
    accession_nodash = accession.replace("-", "")
    base = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession_nodash}"

    index = requests.get(f"{base}/index.json", headers=HEADERS).json()["directory"]["item"]
    time.sleep(0.12)
    names = [f["name"] for f in index if not is_skippable(f["name"])]
    exhibits = [n for n in names if ("exhibit99" in n.lower() or "ex99" in n.lower())
                and n != primary_doc]

    docs = [d for d in [primary_doc] + exhibits if d]
    docs = list(dict.fromkeys(docs))

    parts = [fetch_text(f"{base}/{doc}") for doc in docs]
    text = "\n\n".join(parts)

    with open(cache_path, "w", encoding="utf-8") as f:
        f.write(text)

events = pd.read_csv("data/processed/events_8-k.csv", dtype=str)
needs_text = events[events["items"].apply(lambda s: bool(TEXT_ITEMS & item_set(s)))]
print(f"{len(needs_text)} filings need text out of {len(events)} total")

for i, cik in enumerate(needs_text["cik"].unique()):
    company_rows = needs_text[needs_text["cik"] == cik]
    primary_doc_map = get_primary_doc_map(cik)

    for _, row in company_rows.iterrows():
        accession = row["accession"]
        primary_doc = primary_doc_map.get(accession)
        if primary_doc is None:
            print(f"  WARNING: no primaryDocument for {row['name']} {accession}, skipping")
            continue
        try:
            cache_filing_text(cik, accession, primary_doc)
        except Exception as e:
            print(f"  ERROR on {row['name']} {accession}: {e}")

    if (i + 1) % 10 == 0:
        print(f"{i+1} companies done")

print("done")