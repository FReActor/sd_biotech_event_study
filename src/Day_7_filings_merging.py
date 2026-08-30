import pandas as pd

L701 = "data/processed/llm_labels_701.csv"
L801 = "data/processed/llm_labels_801.csv"
EVENTS_CLEAN = "data/processed/events_clean.csv"
OUT = "data/processed/events_final.csv"
CONFOUNDED_OUT = "data/processed/events_confounded.csv"

COLUMNS = ["accession", "cik", "name", "filing_date", "acceptance_et",
           "after_hours", "items", "label"]

def item_set(s):
    return {i.strip() for i in str(s).split(",")}

events_clean = pd.read_csv(EVENTS_CLEAN, dtype=str)
allowed_cik = set(events_clean["cik"].unique())

# --- merge the two LLM-classified pools, dedup by accession ---
l701 = pd.read_csv(L701, dtype=str)
l801 = pd.read_csv(L801, dtype=str)
llm = pd.concat([l701, l801]).drop_duplicates(subset="accession", keep="first")
llm = llm.rename(columns={"llm_label": "label"})
llm = llm[llm["cik"].isin(allowed_cik)]

# --- confounded: 2.02 co-occurring with 7.01 or 8.01, can't attribute the reaction ---
is_confounded = llm["items"].apply(
    lambda s: "2.02" in item_set(s) and bool({"7.01", "8.01"} & item_set(s))
)
confounded = llm[is_confounded]
llm = llm[~is_confounded]

confounded[COLUMNS].to_csv(CONFOUNDED_OUT, index=False)
print(f"Confounded (2.02 + 7.01/8.01): {len(confounded)}, saved to {CONFOUNDED_OUT}")

# --- pure 2.02 filings (not in the 7.01/8.01 pool at all) -> EARNINGS ---
pure_202 = events_clean[events_clean["items"].apply(
    lambda s: item_set(s) - {"9.01"} == {"2.02"}
)].copy()
pure_202 = pure_202[pure_202["cik"].isin(allowed_cik)]
pure_202["label"] = "EARNINGS"

final = pd.concat([llm[COLUMNS], pure_202[COLUMNS]], ignore_index=True)
final = final.drop_duplicates(subset="accession", keep="first")
final.to_csv(OUT, index=False)

print(f"\nSaved {len(final)} filings to {OUT}")
print("\nLabel distribution:")
print(final["label"].value_counts())
print(f"\nUnique companies: {final['cik'].nunique()}")
