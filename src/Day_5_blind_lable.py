from pathlib import Path
 
import pandas as pd
 
IN = Path("data/processed/classified_701.csv")
OUT = Path("data/processed/manual_labels.csv")
 
SAMPLE_SIZE = 100
SEED = 7          # fixed so the sample is reproducible
 
VALID_LABELS = ["CLINICAL", "REGULATORY", "PRESENTATION", "OTHER"]
 
 
def main():
    df = pd.read_csv(IN, dtype=str)
    print(f"Total 7.01 filings: {len(df)}")
 
    # Filings with no usable text cannot be labeled from a headline.
    labelable = df[df["primary_label"] != "NO_TEXT"].copy()
    print(f"Labelable (has text): {len(labelable)}")
 
    n = min(SAMPLE_SIZE, len(labelable))
    sample = labelable.sample(n, random_state=SEED).copy()
 
    # Deliberately NOT including primary_label. Seeing the keyword
    # classifier's guess would bias the manual labels toward agreeing
    # with it, which would inflate kappa.
    out = sample[["accession", "name", "filing_date", "headline"]].copy()
    out.insert(0, "row", range(1, len(out) + 1))
    out["my_label"] = ""
 
    out.to_csv(OUT, index=False, encoding="utf-8-sig")
 
    print(f"\nWrote {len(out)} rows to {OUT}")
    print(f"\nFill in my_label with one of: {', '.join(VALID_LABELS)}")
    print("\nLabeling rules:")
    print("  CLINICAL     - results or data from a HUMAN clinical trial,")
    print("                 including first disclosure at a conference")
    print("  REGULATORY   - a decision, designation, or action by FDA or")
    print("                 another regulator, in any country")
    print("  PRESENTATION - investor deck or corporate overview that")
    print("                 restates already-public information")
    print("  OTHER        - everything else, including preclinical/animal")
    print("                 data, financings, personnel, M&A, compliance")
 
 
if __name__ == "__main__":
    main()