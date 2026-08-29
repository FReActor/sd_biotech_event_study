import pandas as pd
from sklearn.metrics import cohen_kappa_score, confusion_matrix, classification_report

df = pd.read_csv("data/processed/llm_labels_manual100.csv")

df["my_label"] = df["my_label"].str.upper().str.replace("OTHERS", "OTHER")
df["llm_label"] = df["llm_label"].str.upper().str.split().str[0]

k = cohen_kappa_score(df["my_label"], df["llm_label"])
print(f"Cohen's kappa: {k:.3f}")

agree = (df["my_label"] == df["llm_label"]).mean()
print(f"Raw agreement: {agree:.1%}\n")

labels = ["CLINICAL", "REGULATORY", "PRESENTATION", "OTHER"]
cm = confusion_matrix(df["my_label"], df["llm_label"], labels=labels)
print("Rows = my label, columns = LLM label")
print(pd.DataFrame(cm, index=labels, columns=labels))

print("\n", classification_report(df["my_label"], df["llm_label"],
                                  labels=labels, zero_division=0))