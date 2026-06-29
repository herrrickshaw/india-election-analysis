"""
Builds the continuous outcome V_{p,c}: vote share for each bloc p (NDA/INDIA/Other) in
each constituency c, for each election year. This is the actual quantity requested --
continuous, not the discrete win/lose classification used in the earlier (failed) attempt.

Aggregates all real candidate-level rows (not just winners) within a PC-year by bloc,
summing vote shares across all candidates aligned with that bloc.
"""
import pandas as pd
import numpy as np

PARTY_TO_BLOC = {
    "BJP": "NDA", "JD(U)": "NDA", "TDP": "NDA", "SHS": "NDA", "AGP": "NDA",
    "AJSU": "NDA", "HAM(S)": "NDA", "RLD": "NDA", "JD(S)": "NDA", "JSP": "NDA",
    "INC": "INDIA", "SP": "INDIA", "AITC": "INDIA", "DMK": "INDIA", "NCP": "INDIA",
    "CPI": "INDIA", "CPM": "INDIA", "RJD": "INDIA", "JMM": "INDIA",
    "BSP": "Other", "AIMIM": "Other", "IND": "Other", "YSRCP": "Other",
    "BJD": "Other", "ADMK": "Other", "TRS": "Other", "SAD": "Other", "LJP": "Other",
}
def map_bloc(party):
    return PARTY_TO_BLOC.get(party, "Other")

df = pd.read_csv("ga_pc_level_all_candidates.csv")
df = df[df["Party"] != "NOTA"].copy()
df["Bloc"] = df["Party"].apply(map_bloc)

# V_{p,c}: bloc vote share per PC-year (sum candidate shares within each bloc)
bloc_share = (
    df.groupby(["State_Name", "Year", "PC_No", "Bloc"])
    .agg(Bloc_Votes=("Total_Votes", "sum"), PC_Name=("PC_Name", "first"))
    .reset_index()
)
pc_totals = df.groupby(["State_Name","Year","PC_No"])["Total_Votes"].sum().rename("PC_Total_Votes")
bloc_share = bloc_share.merge(pc_totals, on=["State_Name","Year","PC_No"])
bloc_share["V"] = bloc_share["Bloc_Votes"] / bloc_share["PC_Total_Votes"]  # the continuous target

# Pivot wide: one row per PC-year, columns = V_NDA, V_INDIA, V_Other (should sum to ~1)
wide = bloc_share.pivot_table(index=["State_Name","Year","PC_No","PC_Name"], columns="Bloc", values="V", fill_value=0).reset_index()
wide.columns.name = None
for b in ["NDA","INDIA","Other"]:
    if b not in wide.columns:
        wide[b] = 0.0
wide = wide.rename(columns={"NDA":"V_NDA","INDIA":"V_INDIA","Other":"V_Other"})
wide["V_sum_check"] = wide["V_NDA"] + wide["V_INDIA"] + wide["V_Other"]

print(f"Total PC-year rows: {len(wide)}")
print(f"V_sum_check stats (should be ~1.0): min={wide['V_sum_check'].min():.4f}, max={wide['V_sum_check'].max():.4f}, mean={wide['V_sum_check'].mean():.4f}")
print(f"\nYears: {sorted(wide['Year'].unique())}")
print(f"\nSample rows:")
print(wide.head(10)[["State_Name","Year","PC_Name","V_NDA","V_INDIA","V_Other","V_sum_check"]].to_string())

wide.to_csv("vote_share_continuous.csv", index=False)
print("\nSaved vote_share_continuous.csv")
