#!/usr/bin/env python3
"""
Phase 4a: Lok Sabha Extension
Analyze women's representation and candidacy at national level.
Extend Phase 1 analysis (candidacy dashboard) to Lok Sabha elections.
"""

import pandas as pd
import gzip
import numpy as np
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
DATA_RAW = REPO_ROOT / "data" / "raw"
DATA_PROCESSED = REPO_ROOT / "data" / "processed"
DATA_WOMENS = REPO_ROOT / "coalition-game-theory" / "data" / "womens-participation"

print("=== Phase 4a: Lok Sabha Women's Candidacy Analysis ===\n")

# Load TCPD Lok Sabha (General Assembly) Elections
print("Loading TCPD Lok Sabha data...")
with gzip.open(DATA_RAW / "TCPD_GA_All_States_2026-6-29.csv.gz", "rt") as f:
    df = pd.read_csv(f)

print(f"Total candidates: {len(df):,}")
print(f"Years covered: {sorted(df['Year'].unique())}")
print(f"States: {df['State_Name'].nunique()}")

# === PART 1: NATIONAL-LEVEL SUMMARY ===
print("\n--- Part 1: National Lok Sabha Summary ---")

# Filter to women
women_df = df[df['Sex'] == 'FEMALE'].copy()

# Target: Position == 1 (winner/incumbent)
df['Won'] = (df['Position'] == 1).astype(int)

total_cands = len(df)
women_cands = len(women_df)
women_pct = 100 * women_cands / total_cands

women_winners = women_df[women_df['Position'] == 1]
women_win_rate = 100 * len(women_winners) / women_cands if women_cands > 0 else 0

all_winners = df[df['Position'] == 1]
overall_win_pct = 100 * len(all_winners) / total_cands

print(f"Total Lok Sabha candidates (1999–2019): {total_cands:,}")
print(f"  Women candidates: {women_cands:,} ({women_pct:.2f}%)")
print(f"  Women winners: {len(women_winners):,} ({women_win_rate:.1f}%)")
print(f"  Overall win rate: {overall_win_pct:.1f}%")

# By election year
print("\n--- By Election Year ---")
yearly_summary = []
for year in sorted(df['Year'].unique()):
    year_data = df[df['Year'] == year]
    year_women = women_df[women_df['Year'] == year]
    year_winners = year_data[year_data['Position'] == 1]
    year_women_winners = year_women[year_women['Position'] == 1]

    yearly_summary.append({
        'Year': year,
        'Total_Candidates': len(year_data),
        'Women_Candidates': len(year_women),
        'Women_Pct': 100 * len(year_women) / len(year_data) if len(year_data) > 0 else 0,
        'Winners': len(year_winners),
        'Women_Winners': len(year_women_winners),
        'Women_Win_Rate': 100 * len(year_women_winners) / len(year_women) if len(year_women) > 0 else 0,
    })

yearly_df = pd.DataFrame(yearly_summary)
print(yearly_df.to_string(index=False))

# === PART 2: STATE-WISE ANALYSIS (LOK SABHA) ===
print("\n--- Part 2: State-Wise Lok Sabha Performance ---")

state_summary = []
for state in sorted(df['State_Name'].unique()):
    state_data = df[df['State_Name'] == state]
    state_women = women_df[women_df['State_Name'] == state]

    total = len(state_data)
    women_total = len(state_women)
    women_pct = 100 * women_total / total if total > 0 else 0

    winners = state_data[state_data['Position'] == 1]
    women_winners = state_women[state_women['Position'] == 1]
    women_win_rate = 100 * len(women_winners) / women_total if women_total > 0 else 0

    # Seats (typically 1 winner per constituency, so #winners ≈ #seats)
    num_seats = len(winners)

    state_summary.append({
        'State': state,
        'LS_Seats': num_seats,
        'Women_Candidates': women_total,
        'Women_Candidacy_Pct': women_pct,
        'Women_Winners': len(women_winners),
        'Women_Win_Rate_Pct': women_win_rate,
    })

state_summary_df = pd.DataFrame(state_summary).sort_values('Women_Win_Rate_Pct', ascending=False)

print("\nTop 10 States (Women's Win Rate):")
print(state_summary_df.head(10)[['State', 'LS_Seats', 'Women_Candidates', 'Women_Win_Rate_Pct']].to_string(index=False))

print("\nBottom 10 States:")
print(state_summary_df.tail(10)[['State', 'LS_Seats', 'Women_Candidates', 'Women_Win_Rate_Pct']].to_string(index=False))

# === PART 3: COMPARISON TO ASSEMBLY ===
print("\n--- Part 3: Lok Sabha vs State Assembly Comparison ---")

print(f"\nWomen's Candidacy Rate:")
print(f"  Lok Sabha (1999–2019): {women_pct:.2f}%")
print(f"  State Assembly (1961–2023): 0.10%")
print(f"  Ratio: Lok Sabha is {women_pct/0.10:.1f}x higher")

print(f"\nWomen's Win Rate (when fielded):")
print(f"  Lok Sabha: {women_win_rate:.1f}%")
print(f"  State Assembly: 10.0%")
print(f"  Difference: {women_win_rate - 10:.1f} percentage points")

# === PART 4: BASELINE FOR RESERVATION ===
print("\n--- Part 4: Baseline for 33% Reservation ---")

# Total LS seats
total_ls_seats = 543
current_women = len(df[df['Won'] == True])
current_women_pct = 100 * current_women / total_ls_seats

reserved_seats_target = int(np.ceil(total_ls_seats * 0.33))
women_shortfall = reserved_seats_target - current_women

print(f"\nLok Sabha Baseline:")
print(f"  Total seats: {total_ls_seats}")
print(f"  Current women MPs (18th, 2024 implied): {current_women}")
print(f"  Current women %: {current_women_pct:.1f}%")
print(f"  33% target: {reserved_seats_target} seats")
print(f"  Shortfall: {women_shortfall} seats")

# === PART 5: PARTY COMPOSITION ===
print("\n--- Part 5: Party Composition (Latest Election) ---")

latest_year = df['Year'].max()
latest_data = df[df['Year'] == latest_year]
latest_women = latest_data[latest_data['Sex'] == 'FEMALE']

print(f"\n{latest_year} Lok Sabha Election:")
print(f"  Total candidates: {len(latest_data):,}")
print(f"  Women candidates: {len(latest_women):,} ({100*len(latest_women)/len(latest_data):.2f}%)")

# Top parties
top_parties = latest_data['Party'].value_counts().head(10)
print(f"\nTop 10 parties by candidate count:")
print(top_parties.to_string())

# Women candidates by top parties
print(f"\nWomen candidates in top parties:")
for party in top_parties.index[:5]:
    party_data = latest_data[latest_data['Party'] == party]
    party_women = party_data[party_data['Sex'] == 'FEMALE']
    pct = 100 * len(party_women) / len(party_data) if len(party_data) > 0 else 0
    print(f"  {party}: {len(party_women)} / {len(party_data)} ({pct:.1f}%)")

# === SAVE OUTPUTS ===
print("\n--- Saving Outputs ---")

state_summary_df.to_csv(DATA_PROCESSED / "lok_sabha_women_candidacy_by_state.csv", index=False)
yearly_df.to_csv(DATA_PROCESSED / "lok_sabha_women_candidacy_by_year.csv", index=False)

summary_stats = {
    'Total_LS_Candidates': total_cands,
    'Total_Women_LS_Candidates': women_cands,
    'Women_LS_Candidacy_Rate_Pct': women_pct,
    'Women_LS_Win_Rate_Pct': women_win_rate,
    'Total_Women_LS_Winners': len(women_winners),
    'LS_Seats_Total': total_ls_seats,
    'LS_Seats_Reserved_33pct': reserved_seats_target,
    'LS_Women_Shortfall': women_shortfall,
}

pd.DataFrame([summary_stats]).to_csv(DATA_PROCESSED / "lok_sabha_summary.csv", index=False)

print(f"✅ Saved: lok_sabha_women_candidacy_by_state.csv ({len(state_summary_df)} states)")
print(f"✅ Saved: lok_sabha_women_candidacy_by_year.csv ({len(yearly_df)} years)")
print(f"✅ Saved: lok_sabha_summary.csv")

print("\n=== Phase 4a Complete ===")
print(f"Key finding: Women's Lok Sabha candidacy ({women_pct:.2f}%) >> state assembly (0.10%)")
print(f"But still far below 33% target. Reservation will reshape national candidate pool.")
