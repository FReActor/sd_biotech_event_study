import random, os
files = os.listdir("data/raw/filings")
for f in random.sample(files, 20):
    text = open(f"data/raw/filings/{f}", encoding="utf-8").read()
    print("="*60)
    print(f)
    print(text[:800])

import os, re
files = os.listdir("data/raw/filings")
SD = re.compile(r"san\s+diego|carlsbad|la\s+jolla|solana\s+beach|"
                r"escondido|oceanside|encinitas|poway|vista|san\s+marcos|"
                r"el\s+cajon", re.IGNORECASE)

no_sd = [f for f in files
         if not SD.search(open(f"data/raw/filings/{f}", encoding="utf-8").read())]
print(len(no_sd), "of", len(files))

import pandas as pd
events = pd.read_csv("data/processed/events_8-k.csv", dtype=str)
bad = {f.replace(".txt", "") for f in no_sd}
print(events[events["accession"].isin(bad)]["name"].value_counts().head(25))