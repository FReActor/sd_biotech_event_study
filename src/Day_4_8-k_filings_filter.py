import pandas as pd

events = pd.read_csv("data/processed/events_8-k.csv", dtype=str)
# I am checking the distribution of item codes in the 8-K filings.
# each filing can list multiple item codes (e.g. "5.02,9.01") -> split into one row per code
items = events["items"].str.split(",").explode().str.strip()
counts = items.value_counts()
print(counts)
print(f"\n{counts.sum()} item-code instances across {len(events)} filings")

counts.to_csv("data/processed/item_code_distribution.csv", header=["count"])

# checking the groups with only 5.02 to serve as the second baseline group
KEEP = {"7.01", "8.01", "1.01", "2.02"}

def item_set(s):
    return {i.strip() for i in str(s).split(",")}

pure_502 = events[events["items"].apply(
    lambda s: "5.02" in item_set(s) and not (KEEP & item_set(s))
)]
print(len(pure_502))

# checking how many filings are left
KEEP_ITEMS = {"7.01", "8.01", "1.01", "2.02", "5.02"}

filtered = events[events["items"].apply(lambda s: bool(KEEP_ITEMS & item_set(s)))]
print(len(filtered))
filtered.to_csv("data/processed/events_screened.csv", index=False)