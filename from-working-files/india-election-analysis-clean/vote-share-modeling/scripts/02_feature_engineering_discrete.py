"""
Feature engineering + chronological train/validation/test split for REAL Lok Sabha
PC-level winner data, 1999-2019 (5 elections, rolled up from TCPD AC-segment data).

CHRONOLOGICAL SPLIT (not random): preserves the time-series nature of the data so the
model is always evaluated on elections strictly after what it trained on.
  TRAIN:      1999, 2004 (2 elections)
  VALIDATION: 2009 (1 election) -- model selection
  TEST:       2014, 2019 (2 elections) -- held out until final evaluation

This window is shorter than the original 75-year ask because the gated TCPD portal
only made this AC-segment Lok Sabha extract available for 1999-2019 in this session.
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

TRAIN_YEARS = [1999, 2004]
VAL_YEARS = [2009]
TEST_YEARS = [2014, 2019]

def build_features(winners_df):
    df = winners_df.copy()
    df["Bloc"] = df["Party"].apply(map_bloc)

    # Incumbent retention: did the SAME bloc win this PC (by PC_No+State) last election?
    df = df.sort_values(["State_Name", "PC_No", "Year"])
    df["Prev_Bloc"] = df.groupby(["State_Name", "PC_No"])["Bloc"].shift(1)
    df["Bloc_Retained"] = (df["Bloc"] == df["Prev_Bloc"]).astype(int)
    df["Has_Prev_Result"] = df["Prev_Bloc"].notna().astype(int)

    # Previous margin (if available) as a feature -- proxy for "how safe was this seat"
    df["Prev_Margin_Pct"] = df.groupby(["State_Name", "PC_No"])["Margin_Pct"].shift(1)

    df["split"] = df["Year"].apply(
        lambda y: "train" if y in TRAIN_YEARS else ("validation" if y in VAL_YEARS else ("test" if y in TEST_YEARS else "unused"))
    )
    return df

if __name__ == "__main__":
    winners = pd.read_csv("ga_pc_level_winners.csv")
    features = build_features(winners)
    print("\n--- Split summary ---")
    for s in ["train", "validation", "test", "unused"]:
        sub = features[features["split"] == s]
        print(f"{s.upper():12s}: {len(sub):5d} rows | years: {sorted(sub['Year'].unique())}")
    print("\n--- Bloc distribution by year ---")
    print(features.groupby(["Year", "Bloc"]).size().unstack(fill_value=0))
    features.to_csv("ga_features.csv", index=False)
    print("\nSaved ga_features.csv")
