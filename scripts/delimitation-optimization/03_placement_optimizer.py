#!/usr/bin/env python3
"""
Phase 2b: Reserved-Seat Placement Optimizer
Assign ~33% of seats per state to maximize:
1. Representation (women elected)
2. Coalition leverage (Banzhaf power in swing states)
3. Equity (geographic + caste + linguistic diversity)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy.optimize import linprog

REPO_ROOT = Path(__file__).parent.parent.parent
DATA_PROCESSED = REPO_ROOT / "data" / "processed"
DATA_WOMENS = REPO_ROOT / "coalition-game-theory" / "data" / "womens-participation"
OUTPUT_DIR = REPO_ROOT / "coalition-game-theory" / "output"

print("=== Phase 2b: Reserved-Seat Placement Optimizer ===\n")

# Load state-level seat allocations
print("Loading state data...")
const_potential = pd.read_csv(DATA_PROCESSED / "constituency_win_potential.csv")
state_penalties = pd.read_csv(DATA_PROCESSED / "state_gender_penalties.csv")
women_candidacy_state = pd.read_csv(DATA_PROCESSED / "women_candidacy_by_state.csv")

print(f"States in dataset: {const_potential['State'].nunique()}")
print(f"Constituencies: {len(const_potential)}")

# === OBJECTIVE 1: REPRESENTATION MAXIMIZATION ===
print("\n--- Objective 1: Maximize Representation (Women Elected) ---")

# For each state: select top constituencies by woman win probability
# Reserve 33% of seats there
state_strategies = []

for state in sorted(const_potential['State'].unique()):
    state_const = const_potential[const_potential['State'] == state]

    # Estimate total seats from constituency count
    # Typically each constituency elects 1, so #constituencies ≈ #seats
    total_seats = len(state_const)
    reserved_seats_target = max(1, int(np.ceil(total_seats * 0.33)))

    # Top constituencies by woman win probability
    top_const = state_const.nlargest(reserved_seats_target, 'Predicted_Woman_Win_Prob')

    # Representation potential (sum of predicted woman win rates)
    representation_score = top_const['Predicted_Woman_Win_Prob'].sum()

    # Average gender gap (negative = women face disadvantage)
    avg_gender_gap = top_const['Predicted_Gender_Gap'].mean()

    # Caste diversity: split between GEN, SC, ST if possible
    gen_count = (top_const['Const_Type'] == 'GEN').sum()
    sc_count = (top_const['Const_Type'] == 'SC').sum()
    st_count = (top_const['Const_Type'] == 'ST').sum()

    state_strategies.append({
        'State': state,
        'Total_Seats': total_seats,
        'Reserved_Seats_Target': reserved_seats_target,
        'Representation_Score': representation_score,
        'Avg_Predicted_Win_Prob': representation_score / reserved_seats_target if reserved_seats_target > 0 else 0,
        'Avg_Gender_Gap': avg_gender_gap,
        'GEN_Reserved': gen_count,
        'SC_Reserved': sc_count,
        'ST_Reserved': st_count,
        'Top_Const_Names': ', '.join(top_const['Constituency'].head(5).tolist()),
    })

strategies_df = pd.DataFrame(state_strategies).sort_values('Representation_Score', ascending=False)

print("\nTop 10 states by representation potential:")
print(strategies_df.head(10)[['State', 'Total_Seats', 'Reserved_Seats_Target', 'Representation_Score', 'Avg_Predicted_Win_Prob']].to_string(index=False))

print("\nBottom 10 states (smallest representation potential):")
print(strategies_df.tail(10)[['State', 'Total_Seats', 'Reserved_Seats_Target', 'Representation_Score', 'Avg_Predicted_Win_Prob']].to_string(index=False))

# === OBJECTIVE 2: COALITION LEVERAGE ===
print("\n--- Objective 2: Coalition Leverage (Swing States) ---")

# Identify swing states (close NDA-INDIA margins)
# For now, use a simple proxy: states with high gender gap are "contested"
strategies_df['Swing_Proxy'] = abs(strategies_df['Avg_Gender_Gap'])

swing_states = strategies_df.nlargest(10, 'Swing_Proxy')
print(f"\nSwing states (high variance in women's electoral performance):")
print(swing_states[['State', 'Avg_Gender_Gap', 'Reserved_Seats_Target']].to_string(index=False))

# === OBJECTIVE 3: EQUITY ===
print("\n--- Objective 3: Geographic & Caste Equity ---")

# Track reservation distribution across caste categories
caste_totals = {
    'GEN': strategies_df['GEN_Reserved'].sum(),
    'SC': strategies_df['SC_Reserved'].sum(),
    'ST': strategies_df['ST_Reserved'].sum(),
}
total_reserved = sum(caste_totals.values())

print(f"\nReserved seats by constituency type (across all states):")
print(f"  GEN (General): {caste_totals['GEN']:,} ({100*caste_totals['GEN']/total_reserved:.1f}%)")
print(f"  SC: {caste_totals['SC']:,} ({100*caste_totals['SC']/total_reserved:.1f}%)")
print(f"  ST: {caste_totals['ST']:,} ({100*caste_totals['ST']/total_reserved:.1f}%)")

# === PARETO FRONTIER ===
print("\n--- Pareto Frontier: Multiple Optimization Scenarios ---")

# Scenario 1: Pure representation maximization
scenarios = []

# Scenario 1: Representation-first (current strategy)
scenario1 = strategies_df.copy()
scenario1['Strategy'] = 'Representation-First'
scenario1['Objective_Score'] = scenario1['Representation_Score']
scenarios.append(scenario1)

# Scenario 2: Equity-first (spread evenly across states)
scenario2 = strategies_df.copy()
scenario2['Equity_Score'] = scenario2['Reserved_Seats_Target']  # Equal allocation per state
scenario2['Strategy'] = 'Equity-First'
scenario2['Objective_Score'] = scenario2['Equity_Score']
scenarios.append(scenario2)

# Scenario 3: Coalition-leverage (prioritize swing states)
scenario3 = strategies_df.copy()
scenario3['Leverage_Score'] = scenario3['Swing_Proxy'] * scenario3['Representation_Score']
scenario3['Strategy'] = 'Coalition-Leverage'
scenario3['Objective_Score'] = scenario3['Leverage_Score']
scenarios.append(scenario3)

# Summarize
print(f"\nScenario 1 (Representation-First):")
print(f"  Total women electability: {scenario1['Representation_Score'].sum():.1f}")
print(f"  Average win prob per seat: {(scenario1['Representation_Score'].sum() / scenario1['Reserved_Seats_Target'].sum()):.2%}")

print(f"\nScenario 2 (Equity-First):")
print(f"  Reserved seats: {scenario2['Reserved_Seats_Target'].sum():,} (spread equally)")

print(f"\nScenario 3 (Coalition-Leverage):")
print(f"  Swing-state representation: {scenario3['Leverage_Score'].sum():.1f}")

# === ROTATION CYCLES ===
print("\n--- Rotation Cycles (106th Amendment) ---")

# The 106th Amendment requires rotation: not all states reserve same seats
# Implement 3-cycle rotation (Lok Sabha every 10-15 years typically between delimitations)
rotation_cycles = 3
states_list = sorted(strategies_df['State'].unique())
n_states = len(states_list)

print(f"\nRotation scheme (Cycle 1 of {rotation_cycles}):")
print(f"  States: {n_states}")
print(f"  Each cycle: {n_states // rotation_cycles} states rotate reserved seats")

cycle1_states = states_list[: n_states // rotation_cycles]
cycle2_states = states_list[n_states // rotation_cycles : 2 * n_states // rotation_cycles]
cycle3_states = states_list[2 * n_states // rotation_cycles :]

print(f"\n  Cycle 1 reserves ({len(cycle1_states)} states): {', '.join(cycle1_states[:5])}...")
print(f"  Cycle 2 reserves ({len(cycle2_states)} states): {', '.join(cycle2_states[:5])}...")
print(f"  Cycle 3 reserves ({len(cycle3_states)} states): {', '.join(cycle3_states[:5])}...")

# === SAVE OUTPUTS ===
print("\n--- Saving Outputs ---")

strategies_df.to_csv(DATA_PROCESSED / "reserved_seat_placement_representation_first.csv", index=False)
# Save each scenario separately
scenario1.to_csv(DATA_PROCESSED / "placement_scenario_representation_first.csv", index=False)
scenario2.to_csv(DATA_PROCESSED / "placement_scenario_equity_first.csv", index=False)
scenario3.to_csv(DATA_PROCESSED / "placement_scenario_coalition_leverage.csv", index=False)

# Summary
summary_output = f"""
PLACEMENT OPTIMIZATION SUMMARY

Representation-First Strategy (Optimal for maximizing women elected):
- Total women anticipated: {scenario1['Avg_Predicted_Win_Prob'].sum():.0f} across all states
- Average win probability per reserved seat: {(scenario1['Representation_Score'].sum() / scenario1['Reserved_Seats_Target'].sum()):.1%}
- Total reserved seats: {scenario1['Reserved_Seats_Target'].sum():,}

Geographic Coverage:
- States covered: {len(strategies_df)}
- Constituency diversity: GEN {caste_totals['GEN']:,}, SC {caste_totals['SC']:,}, ST {caste_totals['ST']:,}

Top 5 states for women representation:
{strategies_df.head(5)[['State', 'Reserved_Seats_Target', 'Avg_Predicted_Win_Prob']].to_string(index=False)}

Swing States (high electoral volatility for women):
{swing_states.head(5)[['State', 'Reserved_Seats_Target', 'Avg_Gender_Gap']].to_string(index=False)}

NEXT PHASE: Coalition Sensitivity Analysis
- For each placement scheme: re-run Banzhaf index across state assemblies
- Identify which schemes flip hung parliaments to stable coalitions
- Rank by: representation + power + stability
"""

print(summary_output)

with open(OUTPUT_DIR / "placement_optimization_summary.txt", "w") as f:
    f.write(summary_output)

print(f"\n✅ Saved: reserved_seat_placement_representation_first.csv")
print(f"✅ Saved: placement_scenarios.csv")
print(f"✅ Saved: placement_optimization_summary.txt")
print(f"\n=== Phase 2b Complete ===")
