import pandas as pd
pd.set_option("display.max_rows", None)

# I displayed all cities that belong to San Diego County.
df = pd.read_csv("data/processed/all_companies.csv", dtype=str)
print(f"Total: {len(df)}")
SD_CITIES = {
    "SAN DIEGO", "CARLSBAD", "LA JOLLA", "SOLANA BEACH",
    "ESCONDIDO", "VISTA", "POWAY", "EL CAJON",
    "OCEANSIDE", "ENCINITAS", "SAN MARCOS",
}

df["city"] = df["city"].fillna("")
sd = df[df["city"].str.upper().str.strip().isin(SD_CITIES)]
print(f"San Diego: {len(sd)}")

# I listed all the companies in San Diego County with their SICs and saved them to a CSV file.
sd.to_csv("data/processed/sd_companies.csv", index=False)
print(sd.groupby(["sic", "sic_desc"]).size().sort_values(ascending=False))

# After manually research and filtering, I decided to keep the following SICs and displayed them
KEEP_SIC = {"2834","2836", "3841", "3826", "2835", "8071"}
EXCLUDE_NAMES = {
    "Premier Air Charter Holdings Inc.",
    "PURE BIOSCIENCE, INC.",
}
lifesci = sd[sd["sic"].isin(KEEP_SIC)]
lifesci = lifesci[~lifesci["name"].isin(EXCLUDE_NAMES)]

print(len(lifesci))
lifesci.to_csv("data/processed/sd_lifesci_companies.csv", index=False)