"""
Rolls up TCPD's AC-segment-wise Lok Sabha (GA) data to the actual PC-level (Parliamentary
Constituency) result: sums each candidate's votes across all AC segments within their PC-
year, then determines the true PC winner as the candidate with the highest summed total.

This is necessary because the uploaded file is the "seg=true" (AC Segment Wise) export --
the per-row 'Position' field reflects standing WITHIN one AC segment, not the overall PC
result, which is what actually determines who wins the Lok Sabha seat.

KEY FIX: group by (State_Name, Year, PC_No) as the true PC identity, NOT PC_Name, since
the same PC_No can appear under slightly different PC_Name strings in the raw data (e.g.
"Gopalganj" vs "Gopalganj (SC)" for the same seat/year), which would otherwise create
spurious duplicate "PCs". PC_Name is kept only as a DISPLAY label via first-occurrence.
"""
import pandas as pd
import numpy as np

print("Loading GA (AC-segment-wise Lok Sabha) data...")
df = pd.read_csv("TCPD_GA_All_States_2026-6-29_csv", low_memory=False)
print(f"Raw rows: {len(df):,}")
print(f"Years: {sorted(df['Year'].unique())}")
print(f"States: {df['State_Name'].nunique()}")

# Exclude NOTA -- not a winnable party; can spuriously rank #1 within artifactual
# PC_Name sub-groupings if left in.
n_nota = (df["Party"] == "NOTA").sum()
print(f"\nExcluding {n_nota} NOTA rows before rollup (not a winnable party).")
df = df[df["Party"] != "NOTA"].copy()

PC_KEY = ["State_Name", "Year", "PC_No"]

# Sum votes per candidate across all AC segments within a PC-year (true key: PC_No, not PC_Name)
pc_candidate = (
    df.groupby(PC_KEY + ["Party", "Candidate", "Sex"], dropna=False)
    .agg(Total_Votes=("Votes", "sum"), N_Segments=("Constituency_No", "nunique"),
         PC_Name=("PC_Name", "first"))
    .reset_index()
)
print(f"\nRolled up to candidate-level (within PC): {len(pc_candidate):,} rows")

# Determine PC-level position: rank candidates within each PC-year by total votes
pc_candidate["PC_Position"] = (
    pc_candidate.groupby(PC_KEY)["Total_Votes"]
    .rank(method="first", ascending=False)
    .astype(int)
)

pc_totals = pc_candidate.groupby(PC_KEY)["Total_Votes"].sum().rename("PC_Total_Votes")
pc_candidate = pc_candidate.merge(pc_totals, on=PC_KEY)
pc_candidate["PC_Vote_Share"] = pc_candidate["Total_Votes"] / pc_candidate["PC_Total_Votes"] * 100

n_cand = pc_candidate.groupby(PC_KEY).size().rename("N_Candidates_PC")
pc_candidate = pc_candidate.merge(n_cand, on=PC_KEY)

winners = pc_candidate[pc_candidate["PC_Position"] == 1].copy()
runners_up = pc_candidate[pc_candidate["PC_Position"] == 2][
    PC_KEY + ["Total_Votes", "Party"]
].rename(columns={"Total_Votes": "RunnerUp_Votes", "Party": "RunnerUp_Party"})

winners = winners.merge(runners_up, on=PC_KEY, how="left")
winners["Margin_Votes"] = winners["Total_Votes"] - winners["RunnerUp_Votes"]
winners["Margin_Pct"] = winners["Margin_Votes"] / winners["PC_Total_Votes"] * 100

def enp(group):
    shares = group["PC_Vote_Share"].dropna() / 100.0
    if shares.sum() == 0:
        return np.nan
    return 1.0 / (shares**2).sum()
enp_series = pc_candidate.groupby(PC_KEY).apply(enp, include_groups=False)
enp_series.name = "Effective_N_Parties"
winners = winners.merge(enp_series, on=PC_KEY, how="left")

print(f"\nTotal PC-year winner rows: {len(winners):,}")
print("Per-year PC counts (should match known Lok Sabha seat totals closely):")
print(winners.groupby("Year").size())

# Re-verify no duplicate (State_Name, Year, PC_No) remain
dupes = winners.groupby(PC_KEY).size()
print(f"\nDuplicate (State,Year,PC_No) winner rows remaining: {(dupes>1).sum()}")

winners.to_csv("ga_pc_level_winners.csv", index=False)
pc_candidate.to_csv("ga_pc_level_all_candidates.csv", index=False)
print("\nSaved ga_pc_level_winners.csv and ga_pc_level_all_candidates.csv")
