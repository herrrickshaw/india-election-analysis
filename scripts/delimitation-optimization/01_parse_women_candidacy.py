#!/usr/bin/env python3
"""
Phase 1: Women Candidacy Dashboard
Parse TCPD Assembly Elections data to identify women-friendly vs women-hostile states/constituencies.
"""

import pandas as pd
import gzip
import os
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).parent.parent.parent
DATA_RAW = REPO_ROOT / "data" / "raw"
DATA_PROCESSED = REPO_ROOT / "data" / "processed"
OUTPUT_DIR = REPO_ROOT / "coalition-game-theory" / "output"

DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

# Load TCPD Assembly Elections
print("Loading TCPD Assembly Elections data...")
with gzip.open(DATA_RAW / "TCPD_AE_All_States_2026-6-29.csv.gz", "rt") as f:
    df = pd.read_csv(f)

print(f"Total rows: {len(df):,}")
print(f"Columns: {df.columns.tolist()}")
print(f"Years covered: {sorted(df['Year'].unique())}")
print(f"States: {df['State_Name'].nunique()}")

# === PART 1: Women Candidacy by State ===
print("\n=== Part 1: Women Candidacy by State ===")

# Filter to women candidates only
women_df = df[df['Sex'] == 'FEMALE'].copy()
print(f"Total women candidates: {len(women_df):,} ({100*len(women_df)/len(df):.1f}% of all candidates)")

# State-level summary: women candidacy rate, win rate, incumbency
state_summary = []
for state in sorted(df['State_Name'].unique()):
    state_data = df[df['State_Name'] == state]
    state_women = women_df[women_df['State_Name'] == state]

    total_cands = len(state_data)
    women_cands = len(state_women)
    women_pct = 100 * women_cands / total_cands if total_cands > 0 else 0

    # Women winners (Position == 1)
    women_winners = state_women[state_women['Position'] == 1]
    women_win_pct = 100 * len(women_winners) / women_cands if women_cands > 0 else 0

    # Women incumbents
    women_incumbents = state_women[state_women['Incumbent'] == True]
    women_inc_pct = 100 * len(women_incumbents) / women_cands if women_cands > 0 else 0

    # All-candidate win rates (for comparison)
    all_winners = state_data[state_data['Position'] == 1]
    overall_win_pct = 100 * len(all_winners) / total_cands if total_cands > 0 else 0

    state_summary.append({
        'State': state,
        'Total_Candidates': total_cands,
        'Women_Candidates': women_cands,
        'Women_Candidacy_Pct': women_pct,
        'Women_Winners': len(women_winners),
        'Women_Win_Pct': women_win_pct,
        'Women_Incumbents': len(women_incumbents),
        'Women_Incumbent_Pct': women_inc_pct,
        'Overall_Win_Pct': overall_win_pct,
        'Win_Rate_Gap': women_win_pct - overall_win_pct,  # Negative = women underperform
    })

state_summary_df = pd.DataFrame(state_summary).sort_values('Women_Win_Pct', ascending=False)

print("\nTop 10 States (Women Win Rate):")
print(state_summary_df.head(10)[['State', 'Women_Candidates', 'Women_Win_Pct', 'Women_Candidacy_Pct', 'Win_Rate_Gap']].to_string(index=False))

print("\nBottom 10 States (Women Win Rate):")
print(state_summary_df.tail(10)[['State', 'Women_Candidates', 'Women_Win_Pct', 'Women_Candidacy_Pct', 'Win_Rate_Gap']].to_string(index=False))

# === PART 2: Constituency-Level Analysis ===
print("\n=== Part 2: Constituency-Level Women Candidacy ===")

constituency_summary = []
for (state, const_name), group in df.groupby(['State_Name', 'Constituency_Name']):
    const_women = women_df[(women_df['State_Name'] == state) & (women_df['Constituency_Name'] == const_name)]

    total_cands = len(group)
    women_cands = len(const_women)
    women_pct = 100 * women_cands / total_cands if total_cands > 0 else 0

    # Women winner
    women_winner = const_women[const_women['Position'] == 1]
    women_won = len(women_winner) > 0

    # Electors in this constituency (take latest)
    electors = group['Electors'].iloc[0] if 'Electors' in group.columns else None

    # Turnout
    turnout = group['Turnout_Percentage'].iloc[0] if 'Turnout_Percentage' in group.columns else None

    constituency_summary.append({
        'State': state,
        'Constituency': const_name,
        'Women_Candidates': women_cands,
        'Women_Candidacy_Pct': women_pct,
        'Women_Won': women_won,
        'Total_Candidates': total_cands,
        'Electors': electors,
        'Turnout_Pct': turnout,
    })

const_summary_df = pd.DataFrame(constituency_summary)

# Constituencies where women won
women_won_constituencies = const_summary_df[const_summary_df['Women_Won'] == True]
print(f"\nConstituencies with women winners: {len(women_won_constituencies):,} / {len(const_summary_df):,} ({100*len(women_won_constituencies)/len(const_summary_df):.1f}%)")

# Top constituencies by women candidacy rate
print("\nTop 15 Constituencies (Women Candidacy Rate):")
top_const = const_summary_df.nlargest(15, 'Women_Candidacy_Pct')[['State', 'Constituency', 'Women_Candidacy_Pct', 'Women_Won']]
print(top_const.to_string(index=False))

# === PART 3: Save outputs ===
print("\n=== Saving outputs ===")
state_summary_df.to_csv(DATA_PROCESSED / "women_candidacy_by_state.csv", index=False)
const_summary_df.to_csv(DATA_PROCESSED / "women_candidacy_by_constituency.csv", index=False)

# Summary statistics for dashboard
summary_stats = {
    'Total_Assembly_Elections_Candidates': len(df),
    'Total_Women_Candidates': len(women_df),
    'Women_Candidacy_Rate_Pct': 100 * len(women_df) / len(df),
    'Total_Women_Winners': len(women_df[women_df['Position'] == 1]),
    'Overall_Women_Win_Rate_Pct': 100 * len(women_df[women_df['Position'] == 1]) / len(women_df),
    'Constituencies_With_Women_Winners': len(women_won_constituencies),
    'Total_Constituencies': len(const_summary_df),
    'States_Analyzed': state_summary_df['State'].nunique(),
}

print("\n=== Summary Statistics ===")
for key, val in summary_stats.items():
    if 'Pct' in key:
        print(f"{key}: {val:.1f}%")
    else:
        print(f"{key}: {val:,}")

# Save to CSV for dashboard
pd.DataFrame([summary_stats]).to_csv(DATA_PROCESSED / "women_candidacy_summary.csv", index=False)

print("\n✅ Phase 1 complete. Outputs saved to data/processed/")
