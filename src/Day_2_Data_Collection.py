import csv
import time
from pathlib import Path 
import requests
 
HEADERS = {"User-Agent": "Charles Cheng zic065@ucsd.edu"}
 
PAUSE = 0.12          # SEC allows 10 requests/sec
PROGRESS_EVERY = 250
 
PROCESSED = Path("data/processed")
PROCESSED.mkdir(parents=True, exist_ok=True)
 
ALL_CSV = PROCESSED / "all_companies.csv"
SD_CSV = PROCESSED / "sd_candidates.csv"
 
FIELDS = ["cik", "ticker", "name", "sic", "sic_desc", "city", "state", "zip"]
 
 
def load_done_ciks():
    if not ALL_CSV.exists():
        return set()
    with ALL_CSV.open(newline="", encoding="utf-8") as f:
        return {row["cik"] for row in csv.DictReader(f)}
 
# to deal with incomplete data, return None if the request fails or the JSON is missing expected fields
def fetch_company(cik_padded, ticker):
    url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
    resp = requests.get(url, headers=HEADERS, timeout=30)
 
    if resp.status_code != 200:
        return None
 
    sub = resp.json()
    addr = sub.get("addresses", {}).get("business", {}) or {}
 
    zip_raw = addr.get("zipCode") or ""
    zip5 = zip_raw[:5]
 
    return {
        "cik": cik_padded,
        "ticker": ticker,
        "name": sub.get("name", ""),
        "sic": sub.get("sic", ""),
        "sic_desc": sub.get("sicDescription", ""),
        "city": addr.get("city", ""),
        "state": addr.get("stateOrCountry", ""),
        "zip": zip5,
    }
 
 
def main():
    print("Downloading ticker -> CIK map")
    tickers_raw = requests.get(
        "https://www.sec.gov/files/company_tickers.json",
        headers=HEADERS,
    ).json()
 
    # One CIK can have several tickers (share classes). Keep one row per CIK.
    by_cik = {}
    for record in tickers_raw.values():
        cik_padded = str(record["cik_str"]).zfill(10)
        by_cik.setdefault(cik_padded, record["ticker"])
 
    print(f"{len(by_cik)} unique CIKs")
 
    done = load_done_ciks()
    todo = [(c, t) for c, t in by_cik.items() if c not in done]
 
    if done:
        print(f"Resuming: {len(done)} already done, {len(todo)} remaining")
 
    # Append mode so a resumed run adds to the existing file
    write_header = not ALL_CSV.exists()
    failures = 0
 
    with ALL_CSV.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if write_header:
            writer.writeheader()
 
        for i, (cik_padded, ticker) in enumerate(todo, start=1):
            try:
                row = fetch_company(cik_padded, ticker)
            except Exception as exc:
                print(f"  error on {ticker} ({cik_padded}): {exc}")
                row = None
 
            if row is None:
                failures += 1
            else:
                writer.writerow(row)
                f.flush()   # write to disk immediately, so Ctrl+C is safe
 
            time.sleep(PAUSE)
 
            if i % PROGRESS_EVERY == 0:
                pct = 100 * i / len(todo)
                print(f"  {i}/{len(todo)} ({pct:.1f}%)  failures so far: {failures}")
 
    print(f"\nDone. {failures} failures.")
    
if __name__ == "__main__":
    main()