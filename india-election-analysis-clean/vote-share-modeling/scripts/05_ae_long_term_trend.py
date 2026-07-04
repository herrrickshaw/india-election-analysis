"""
Aggregates real AE (State Assembly) data, 1961-2023, into a national-level NDA/INDIA/
Other bloc seat-share trend by year -- the genuine 60+ year political trend context
requested, built from real TCPD data (not constructed/approximated).
"""
import pandas as pd

PARTY_TO_BLOC = {
    "BJP": "NDA", "JD(U)": "NDA", "TDP": "NDA", "SHS": "NDA", "AGP": "NDA",
    "AJSU": "NDA", "HAM(S)": "NDA", "RLD": "NDA", "JD(S)": "NDA", "JSP": "NDA",
    "JNS": "NDA", "BJS": "NDA",  # Jana Sangh, BJP's direct predecessor pre-1980
    "INC": "INDIA", "SP": "INDIA", "AITC": "INDIA", "DMK": "INDIA", "NCP": "INDIA",
    "CPI": "INDIA", "CPM": "INDIA", "RJD": "INDIA", "JMM": "INDIA",
    "INC(I)": "INDIA", "INC(O)": "INDIA", "INC(U)": "INDIA",  # Congress splits
    "BSP": "Other", "AIMIM": "Other", "IND": "Other", "YSRCP": "Other",
    "BJD": "Other", "ADMK": "Other", "AIADMK": "Other", "TRS": "Other", "SAD": "Other",
    "JD": "Other", "JNP": "Other",  # Janata Dal / Janata Party -- genuinely cross-cutting,
                                       # not a clean predecessor of either current bloc
}

def map_bloc(party):
    return PARTY_TO_BLOC.get(party, "Other")

print("Loading AE data (this is a large file)...")
df = pd.read_csv("TCPD_AE_All_States_2026-6-29_csv", usecols=["Year","State_Name","Party","Position"], low_memory=False)
winners = df[df["Position"] == 1].copy()
winners["Bloc"] = winners["Party"].apply(map_bloc)
print(f"Total AE winner rows: {len(winners):,}")

trend = winners.groupby(["Year","Bloc"]).size().unstack(fill_value=0)
trend["Total"] = trend.sum(axis=1)
for b in ["NDA","INDIA","Other"]:
    if b not in trend.columns:
        trend[b] = 0
    trend[f"{b}_Share"] = trend[b] / trend["Total"]

trend = trend.reset_index()
print(trend[["Year","NDA","INDIA","Other","Total","NDA_Share","INDIA_Share"]].to_string())
trend.to_csv("ae_national_bloc_trend.csv", index=False)
print("\nSaved ae_national_bloc_trend.csv")
