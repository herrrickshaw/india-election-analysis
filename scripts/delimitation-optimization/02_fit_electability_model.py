#!/usr/bin/env python3
"""
Phase 2a: Women's Electability Model
Logistic regression: predict win probability from gender, incumbency, state, constituency type.
Quantify the "gender penalty" per state and identify high-potential constituencies.
"""

import pandas as pd
import gzip
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
from pathlib import Path
import pickle

# Paths
REPO_ROOT = Path(__file__).parent.parent.parent
DATA_RAW = REPO_ROOT / "data" / "raw"
DATA_PROCESSED = REPO_ROOT / "data" / "processed"

print("=== Phase 2a: Women's Electability Model ===\n")

# Load TCPD Assembly Elections
print("Loading TCPD data...")
with gzip.open(DATA_RAW / "TCPD_AE_All_States_2026-6-29.csv.gz", "rt") as f:
    df = pd.read_csv(f, dtype_backend="numpy_nullable")

print(f"Total candidates: {len(df):,}")

# === FEATURE ENGINEERING ===
print("\n--- Feature Engineering ---")

# Target: Position == 1 (winner)
df['Won'] = (df['Position'] == 1).astype(int)
print(f"Winners (Position==1): {df['Won'].sum():,} ({100*df['Won'].mean():.2f}%)")

# Features (handle nulls)
df['Female'] = (df['Sex'] == 'FEMALE').fillna(False).astype(int)
df['Incumbent'] = df['Incumbent'].fillna(False).astype(int)

print(f"Female candidates: {df['Female'].sum():,} ({100*df['Female'].mean():.2f}%)")
print(f"Incumbents: {df['Incumbent'].sum():,} ({100*df['Incumbent'].mean():.2f}%)")

# Constituency type (GEN, SC, ST)
df['Const_Type'] = df['Constituency_Type'].fillna('GEN')
print(f"Constituency types: {df['Const_Type'].value_counts().to_dict()}")

# Turnout (continuous, normalized)
df['Turnout_Normalized'] = df['Turnout_Percentage'].fillna(df['Turnout_Percentage'].median())

# Party as bloc (NDA vs INDIA vs Others)
nda_parties = {'BJP', 'JDU', 'BJD', 'TDP', 'LJP', 'ADMK', 'PMK', 'YSRCP', 'TRS', 'AIADMK', 'AITC'}
india_parties = {'INC', 'DMK', 'SS', 'NCP', 'RJD', 'SP', 'AAP', 'TMC', 'CPI', 'CPI(M)', 'CPI(ML)', 'BJD'}

df['Bloc'] = df['Party'].apply(
    lambda x: 'NDA' if x in nda_parties else ('INDIA' if x in india_parties else 'Other')
)
print(f"Bloc distribution: {df['Bloc'].value_counts().to_dict()}")

# === MODEL 1: OVERALL ELECTABILITY ===
print("\n--- Model 1: Overall Electability (All States) ---")

# Remove rows with missing critical features (keep extra columns for later analysis)
model_data = df[['Female', 'Incumbent', 'Const_Type', 'Turnout_Normalized', 'Bloc', 'State_Name', 'Constituency_Name', 'Won']].dropna()
print(f"Complete records for modeling: {len(model_data):,}")

# Encode categorical features
le_const = LabelEncoder()
le_bloc = LabelEncoder()
le_state = LabelEncoder()

model_data_encoded = model_data.copy()
model_data_encoded['Const_Type_Enc'] = le_const.fit_transform(model_data_encoded['Const_Type'])
model_data_encoded['Bloc_Enc'] = le_bloc.fit_transform(model_data_encoded['Bloc'])
model_data_encoded['State_Enc'] = le_state.fit_transform(model_data_encoded['State_Name'])

# Features and target
X = model_data_encoded[['Female', 'Incumbent', 'Const_Type_Enc', 'Turnout_Normalized', 'Bloc_Enc', 'State_Enc']]
y = model_data_encoded['Won']

# Fit logistic regression
log_reg = LogisticRegression(max_iter=1000, random_state=42)
log_reg.fit(X, y)
accuracy = log_reg.score(X, y)
print(f"Model accuracy: {accuracy:.2%}")

# Feature importance (coefficients)
feature_names = ['Female', 'Incumbent', 'Const_Type', 'Turnout', 'Bloc', 'State']
print("\nFeature Coefficients (impact on win probability):")
for fname, coef in zip(feature_names, log_reg.coef_[0]):
    impact = "↓ Decreases" if coef < 0 else "↑ Increases"
    print(f"  {fname:15} {coef:+.4f}  {impact} win probability")

gender_penalty = log_reg.coef_[0][0]
incumbent_boost = log_reg.coef_[0][1]
print(f"\n→ Gender penalty: {gender_penalty:.4f} (women's win prob {100*abs(gender_penalty):.1f}% lower, all else equal)")
print(f"→ Incumbency boost: {incumbent_boost:.4f} (incumbents {100*incumbent_boost:.1f}% more likely to win)")

# === MODEL 2: STATE-LEVEL GENDER PENALTY ===
print("\n--- Model 2: State-Level Gender Penalties ---")

state_penalties = []
for state in sorted(df['State_Name'].unique()):
    state_data = model_data_encoded[model_data_encoded['State_Name'] == state]
    if len(state_data) < 20:  # Skip very small states
        continue

    X_state = state_data[['Female', 'Incumbent', 'Const_Type_Enc', 'Turnout_Normalized', 'Bloc_Enc']]
    y_state = state_data['Won']

    try:
        lr_state = LogisticRegression(max_iter=1000, random_state=42)
        lr_state.fit(X_state, y_state)
        gender_penalty_state = lr_state.coef_[0][0]

        # Women vs men win rate (empirical)
        women_win_rate = state_data[state_data['Female'] == 1]['Won'].mean() if (state_data['Female'] == 1).any() else 0
        men_win_rate = state_data[state_data['Female'] == 0]['Won'].mean() if (state_data['Female'] == 0).any() else 0
        empirical_gap = women_win_rate - men_win_rate

        state_penalties.append({
            'State': state,
            'Gender_Penalty_Coef': gender_penalty_state,
            'Women_Win_Rate_Pct': 100 * women_win_rate,
            'Men_Win_Rate_Pct': 100 * men_win_rate,
            'Empirical_Gap_Pct': 100 * empirical_gap,
            'Total_Candidates': len(state_data),
            'Women_Candidates': (state_data['Female'] == 1).sum(),
        })
    except:
        pass

penalties_df = pd.DataFrame(state_penalties).sort_values('Empirical_Gap_Pct')

print("\nStates where women underperform most (largest negative gap):")
print(penalties_df.head(10)[['State', 'Women_Win_Rate_Pct', 'Men_Win_Rate_Pct', 'Empirical_Gap_Pct']].to_string(index=False))

print("\nStates where women perform best (smallest gap or positive):")
print(penalties_df.tail(10)[['State', 'Women_Win_Rate_Pct', 'Men_Win_Rate_Pct', 'Empirical_Gap_Pct']].to_string(index=False))

# === MODEL 3: HIGH-POTENTIAL CONSTITUENCIES ===
print("\n--- Model 3: Identifying High-Potential Constituencies for Women ---")

# For each constituency: predict win probability for a hypothetical woman candidate
# vs. a hypothetical man, all else equal
constituency_potential = []

# Merge model_data with encoded features
model_data_full = model_data.copy()
model_data_full['Const_Type_Enc'] = le_const.transform(model_data_full['Const_Type'])
model_data_full['Bloc_Enc'] = le_bloc.transform(model_data_full['Bloc'])
model_data_full['State_Enc'] = le_state.transform(model_data_full['State_Name'])
model_data_full['Turnout_Normalized'] = model_data_full['Turnout_Normalized']

for (state, const_name), group in model_data_full.groupby(['State_Name', 'Constituency_Name']):
    if len(group) < 5:  # Need minimum data
        continue

    # Use average conditions
    avg_const_type = group['Const_Type_Enc'].mean()
    avg_turnout = group['Turnout_Normalized'].mean()
    avg_bloc = group['Bloc_Enc'].mean()
    state_enc = group['State_Enc'].iloc[0]

    # Predict for woman incumbent and man incumbent
    woman_incumbent = np.array([[1, 1, avg_const_type, avg_turnout, avg_bloc, state_enc]])
    man_incumbent = np.array([[0, 1, avg_const_type, avg_turnout, avg_bloc, state_enc]])

    woman_win_prob = log_reg.predict_proba(woman_incumbent)[0][1]
    man_win_prob = log_reg.predict_proba(man_incumbent)[0][1]

    gap = man_win_prob - woman_win_prob

    # Empirical data from this constituency
    women_in_const = group[group['Female'] == 1]
    men_in_const = group[group['Female'] == 0]

    women_empirical_win = women_in_const['Won'].mean() if len(women_in_const) > 0 else 0
    men_empirical_win = men_in_const['Won'].mean() if len(men_in_const) > 0 else 0

    constituency_potential.append({
        'State': state,
        'Constituency': const_name,
        'Predicted_Woman_Win_Prob': woman_win_prob,
        'Predicted_Man_Win_Prob': man_win_prob,
        'Predicted_Gender_Gap': gap,
        'Empirical_Women_Win_Rate': women_empirical_win,
        'Empirical_Men_Win_Rate': men_empirical_win,
        'Women_Fielded': len(women_in_const),
        'Total_Candidates': len(group),
        'Const_Type': group['Const_Type'].iloc[0],
    })

const_potential_df = pd.DataFrame(constituency_potential)

# High-potential: low predicted gender gap + good overall win rates
const_potential_df['Potential_Score'] = (
    (1.0 - const_potential_df['Predicted_Gender_Gap']) *
    const_potential_df['Predicted_Woman_Win_Prob'] * 100
)

print(f"\nHigh-potential constituencies for women (smallest predicted gender gap):")
top_potential = const_potential_df.nsmallest(15, 'Predicted_Gender_Gap')
print(top_potential[['State', 'Constituency', 'Predicted_Woman_Win_Prob', 'Predicted_Gender_Gap']].to_string(index=False))

# === SAVE OUTPUTS ===
print("\n--- Saving Outputs ---")
penalties_df.to_csv(DATA_PROCESSED / "state_gender_penalties.csv", index=False)
const_potential_df.to_csv(DATA_PROCESSED / "constituency_win_potential.csv", index=False)

# Save model
with open(DATA_PROCESSED / "electability_model.pkl", "wb") as f:
    pickle.dump({
        'log_reg': log_reg,
        'le_const': le_const,
        'le_bloc': le_bloc,
        'le_state': le_state,
        'feature_names': feature_names,
    }, f)

print(f"✅ Saved: state_gender_penalties.csv ({len(penalties_df)} states)")
print(f"✅ Saved: constituency_win_potential.csv ({len(const_potential_df)} constituencies)")
print(f"✅ Saved: electability_model.pkl (logistic regression + encoders)")

print("\n=== Phase 2a Complete ===")
print(f"Key insight: Women face {abs(gender_penalty):.2f} coefficient penalty (all else equal)")
print(f"State-level penalties range from {penalties_df['Empirical_Gap_Pct'].min():.1f}% to {penalties_df['Empirical_Gap_Pct'].max():.1f}%")
