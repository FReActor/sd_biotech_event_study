import re
from pathlib import Path
 
import pandas as pd
 
pd.set_option("display.max_colwidth", 100)
pd.set_option("display.width", 250)
 
FILINGS = Path("data/raw/filings")
EVENTS = Path("data/processed/events_8-k.csv")
OUT = Path("data/processed/classified_701.csv")
 
HEADLINE_CHARS = 250
COVER_OFFSET = 1200
ITEM_SEARCH_WINDOW = 2000
 
COVER_END_MARKERS = [
    "emerging growth company",
    "securities registered pursuant to section 12(b)",
    "registrant's telephone number",
    "registrant\u2019s telephone number",
]
 
ITEM_HEADER = re.compile(r"item\s+\d\.\d\d\.?", re.IGNORECASE)
 
PRESENTATION = [
    "corporate overview", "corporate presentation", "investor presentation",
    "company overview", "forward looking statements", "forward-looking statements",
    "investor day", "analyst day", "corporate deck",
]
 
CLINICAL = [
    "topline", "top-line", "phase 1", "phase 2", "phase 3",
    "phase i", "phase ii", "phase iii", "clinical trial", "clinical data",
    "clinical results", "trial results", "primary endpoint",
    "secondary endpoint", "interim analysis", "interim data",
    "study results", "pivotal", "readout",
]
 
REGULATORY = [
    "fda", "food and drug administration", "ema",
    "complete response letter", "breakthrough therapy", "orphan drug",
    "fast track", "clinical hold", "pdufa", "510(k)",
    "premarket approval", "marketing authorization", "regulatory approval",
]
 
# Announces data without specifying preclinical vs human trial. Checked
# only after CLINICAL and REGULATORY, so explicit phase language wins.
AMBIGUOUS = [
    "presents data", "present data", "presentation of data",
    "announces data", "announce data", "reports data", "report data",
    "new data", "positive data", "preliminary data",
    "data supporting", "data demonstrating", "data at",
]
 
CORPORATE = [
    "appoints", "appointment", "names ", "resigns", "resignation",
    "to acquire", "acquisition of", "merger", "to divest", "divestiture",
    "announces offering", "pricing of", "private placement",
    "investment from", "stockholders", "annual meeting", "special meeting",
    "restructuring", "workforce reduction", "streamlines",
    "nasdaq", "minimum bid price", "regains compliance", "regain compliance",
    "advisory board", "participation at", "to participate in",
    "business combination", "uplisting", "financial results",
    "strategic investment", "launches", "product launch", "conference",
    "registered direct", "offering of common stock", "public offering",
    "research agreement", "collaboration agreement", "shareholder letter",
    "update letter", "letter to shareholders", "sponsored research",
]
 
 
def item_set(s):
    return {i.strip() for i in str(s).split(",")}
 
 
def strip_exhibit_preamble(body):
    """Remove 'EX-99.1 2 file.htm EX-99.1 Document Exhibit 99.1' prefixes."""
    return re.sub(
        r"^EX-99[^\n]{0,120}?Exhibit\s+99\.?\d*\s*",
        "",
        body,
        flags=re.IGNORECASE,
    )
 
 
def find_cover_end(text):
    """Index just past the last cover-page marker, or None."""
    low = text.lower()
    best = None
    for marker in COVER_END_MARKERS:
        idx = low.rfind(marker)
        if idx >= 0:
            end = idx + len(marker)
            if best is None or end > best:
                best = end
    return best
 
 
def get_headline(accession):
    """Return (headline, source). Source records which extraction path ran."""
    path = FILINGS / f"{accession}.txt"
    if not path.exists():
        return None, "missing_file"
 
    text = path.read_text(encoding="utf-8", errors="ignore")
    if not text.strip():
        return None, "empty_file"
 
    idx = text.find("EX-99")
    if idx >= 0:
        body = strip_exhibit_preamble(text[idx:])
        source = "exhibit"
    else:
        start = find_cover_end(text)
        if start is None:
            body = text[COVER_OFFSET:]
            source = "primary_fallback"
        else:
            # The cover page ends with one more sentence about the
            # transition period, then the Item header begins the body.
            window = text[start:start + ITEM_SEARCH_WINDOW]
            m = ITEM_HEADER.search(window)
            if m:
                body = text[start + m.end():]
                source = "primary_item"
            else:
                body = text[start:]
                source = "primary_marker_only"
 
    body = re.sub(r"\s+", " ", body).strip()
    return body[:HEADLINE_CHARS], source
 
 
def matched(headline, keywords):
    low = headline.lower()
    return any(k in low for k in keywords)
 
 
def classify(headline):
    """Return (labels, primary_label)."""
    if not headline:
        return [], "NO_TEXT"
 
    if matched(headline, PRESENTATION):
        return ["PRESENTATION"], "PRESENTATION"
 
    labels = []
    if matched(headline, CLINICAL):
        labels.append("CLINICAL")
    if matched(headline, REGULATORY):
        labels.append("REGULATORY")
 
    if labels:
        # CLINICAL first: when a filing carries both trial data and a
        # regulatory action, the trial data is the part requiring
        # interpretation, which is what this study measures.
        return labels, labels[0]
 
    if matched(headline, AMBIGUOUS):
        return ["AMBIGUOUS"], "AMBIGUOUS"
 
    if matched(headline, CORPORATE):
        return ["CORPORATE"], "CORPORATE"
 
    return [], "OTHER"
 
 
def main():
    events = pd.read_csv(EVENTS, dtype=str)
    pool = events[events["items"].apply(lambda s: "7.01" in item_set(s))]
    print(f"7.01 filings: {len(pool)}\n")
 
    rows = []
    for _, row in pool.iterrows():
        headline, source = get_headline(row["accession"])
        labels, primary = classify(headline)
        rows.append({
            "accession": row["accession"],
            "cik": row["cik"],
            "name": row["name"],
            "filing_date": row["filing_date"],
            "acceptance_et": row["acceptance_et"],
            "after_hours": row["after_hours"],
            "items": row["items"],
            "primary_label": primary,
            "labels": ",".join(labels),
            "text_source": source,
            "headline": headline or "",
        })
 
    result = pd.DataFrame(rows)
    result.to_csv(OUT, index=False)
 
    print("Label distribution:")
    print(result["primary_label"].value_counts())
 
    print("\nText source:")
    print(result["text_source"].value_counts())
 
    # --- NO_TEXT diagnostics -------------------------------------------
    missing = result[result["primary_label"] == "NO_TEXT"]
    if len(missing):
        print(f"\n{len(missing)} filings with no usable text:")
        print(missing[["accession", "name", "filing_date", "text_source"]]
              .to_string(index=False))
 
    # --- AMBIGUOUS review ----------------------------------------------
    amb = result[result["primary_label"] == "AMBIGUOUS"]
    print(f"\n{len(amb)} AMBIGUOUS. 10 examples:")
    if len(amb):
        print(amb.sample(min(10, len(amb)), random_state=1)[["name", "headline"]]
              .to_string(index=False))
 
    # --- remaining OTHER ------------------------------------------------
    others = result[result["primary_label"] == "OTHER"]
    print(f"\n{len(others)} still OTHER. 15 examples:")
    if len(others):
        print(others.sample(min(15, len(others)), random_state=1)
              [["name", "text_source", "headline"]].to_string(index=False))
 
    print(f"\nSaved to {OUT}")
 
 
if __name__ == "__main__":
    main()