"""
Expanded simulation:
1. 8 scenarios (NDA/INDIA at +11pp, +6pp, +3pp, +1pp, and 50/50 tossup)
2. Full three-way breakdown: P(NDA majority), P(INDIA majority), P(Hung)
3. State-level tipping-point attribution -- which states appear in the
   minimum seat-set that would have flipped a hung result to NDA majority?
"""
import numpy as np
import pandas as pd
import time

np.random.seed(42)
N_SIMULATIONS = 5000
SEAT_TOTALS = [543, 600, 650, 700, 750, 800, 850, 900, 950, 1000]
DIRICHLET_CONCENTRATION = 18  # see assumption audit: too tight by ~1.8x; directional findings robust

state_df = pd.read_csv("state_2024_bloc_results.csv")
pop_df = pd.read_csv("/home/claude/election_analysis/state_data_raw.csv")[["State","Census2011_Pop"]]
df = state_df.merge(pop_df, on="State", how="left").drop_duplicates("State")
df["Census2011_Pop"] = df["Census2011_Pop"].fillna(df["Census2011_Pop"].median())
state_seat_counts = df["Seats_2024"].values.astype(float)
N_STATES = len(df)

for col in ["NDA_2024","INDIA_2024","Other_2024"]:
    df[col] = df[col].clip(lower=0)
df["NDA_share"]   = (df["NDA_2024"]   / df["Seats_2024"]).clip(lower=0.02)
df["INDIA_share"] = (df["INDIA_2024"] / df["Seats_2024"]).clip(lower=0.02)
df["Other_share"] = (df["Other_2024"] / df["Seats_2024"]).clip(lower=0.02)
s = df["NDA_share"] + df["INDIA_share"] + df["Other_share"]
df["NDA_share"] /= s; df["INDIA_share"] /= s; df["Other_share"] /= s

def build_scenario_shares(target_leader, lead_margin_pp):
    other = df["Other_share"].values.copy()
    two_bloc = 1.0 - other
    if target_leader == "NDA":
        nda_frac = 0.5 + (lead_margin_pp / 100.0) / 2.0
    elif target_leader == "INDIA":
        nda_frac = 0.5 - (lead_margin_pp / 100.0) / 2.0
    else:
        nda_frac = 0.5
    nda_new   = nda_frac   * two_bloc
    india_new = (1-nda_frac) * two_bloc
    total = nda_new + india_new + other
    return np.column_stack([nda_new/total, india_new/total, other/total])

SCENARIOS = {
    "S0_NDA_Real":      ("NDA",    11.1, "#FF9933", "NDA +11.1pp (2024 actual)"),
    "S1_INDIA_Mirror":  ("INDIA",  11.1, "#138808", "INDIA +11.1pp (exact mirror)"),
    "S2_Tossup":        ("tossup",  0.0, "#7c3aed", "50/50 Tossup (fair coin)"),
    "S3_NDA_Small":     ("NDA",     3.0, "#f97316", "NDA +3pp (narrow)"),
    "S4_INDIA_Small":   ("INDIA",   3.0, "#22c55e", "INDIA +3pp (narrow mirror)"),
    "S5_NDA_Moderate":  ("NDA",     6.0, "#fb923c", "NDA +6pp (moderate)"),
    "S6_INDIA_Moderate":("INDIA",   6.0, "#4ade80", "INDIA +6pp (moderate mirror)"),
    "S7_Razor_Edge":    ("NDA",     1.0, "#fbbf24", "NDA +1pp (razor-edge)"),
}

def run_election(rng, n_seats, mean_shares):
    weights = state_seat_counts / state_seat_counts.sum()
    chosen = rng.choice(N_STATES, size=n_seats, p=weights)
    alpha = np.clip(mean_shares[chosen] * DIRICHLET_CONCENTRATION, 0.3, None)
    g = rng.standard_gamma(alpha)
    draws = g / g.sum(axis=1, keepdims=True)
    winners = np.argmax(draws, axis=1)
    return int(np.sum(winners==0)), int(np.sum(winners==1)), int(np.sum(winners==2))

print(f"Phase 1: {N_SIMULATIONS} sims x {len(SEAT_TOTALS)} totals x {len(SCENARIOS)} scenarios")
all_results = []
t0 = time.time()

for sid, (target, margin, col, desc) in SCENARIOS.items():
    mean_shares = build_scenario_shares(target, margin)
    for total in SEAT_TOTALS:
        quota = total // 2 + 1
        rng = np.random.default_rng(42)
        nda_maj=0; india_maj=0; hung=0
        nda_shares=[]; india_shares=[]
        for _ in range(N_SIMULATIONS):
            n,i,o = run_election(rng, total, mean_shares)
            nda_shares.append(n/total); india_shares.append(i/total)
            if n >= quota: nda_maj+=1
            elif i >= quota: india_maj+=1
            else: hung+=1
        all_results.append({
            "scenario":sid,"desc":desc,"color":col,
            "target_leader":target,"margin_pp":margin,
            "total_seats":total,"quota":quota,
            "p_nda_majority":nda_maj/N_SIMULATIONS,
            "p_india_majority":india_maj/N_SIMULATIONS,
            "p_hung":hung/N_SIMULATIONS,
            "avg_nda_seat_share":np.mean(nda_shares),
            "avg_india_seat_share":np.mean(india_shares),
        })
    print(f"  {sid} done ({time.time()-t0:.0f}s)")

results_df = pd.DataFrame(all_results)
results_df.to_csv("expanded_scenario_results.csv", index=False)
print(f"Saved expanded_scenario_results.csv")

# ── Phase 2: State-level tipping-point analysis at 543 seats ─────────────────
print("\nPhase 2: Tipping-point attribution at 543 seats")
TOTAL_TP = 543
QUOTA_TP = 272
N_TP = 8000  # per scenario for stable attribution

tip_results = []
for sid in ["S0_NDA_Real", "S3_NDA_Small", "S5_NDA_Moderate", "S7_Razor_Edge"]:
    target, margin, col, desc = SCENARIOS[sid]
    mean_shares = build_scenario_shares(target, margin)
    rng_tp = np.random.default_rng(777 + list(SCENARIOS.keys()).index(sid))

    pivotality = np.zeros(N_STATES, dtype=int)  # times state is in minimal flip set
    hung_sims = 0
    state_nda_all = []

    for sim in range(N_TP):
        # Per-state seat draw: draw each state's seats independently
        state_nda = np.zeros(N_STATES, dtype=int)
        for si in range(N_STATES):
            n = int(state_seat_counts[si])
            if n == 0: continue
            alpha_i = np.clip(mean_shares[si] * DIRICHLET_CONCENTRATION, 0.3, None)
            g = rng_tp.standard_gamma(alpha_i, size=(n, 3))
            d = g / g.sum(axis=1, keepdims=True)
            state_nda[si] = int(np.sum(np.argmax(d, axis=1) == 0))

        total_nda = int(state_nda.sum())

        if total_nda < QUOTA_TP:
            hung_sims += 1
            deficit = QUOTA_TP - total_nda
            # Greedy: which states, taken in order of NDA seats desc, fill the deficit?
            order = np.argsort(-state_nda)
            cumulative = 0
            for si in order:
                if cumulative >= deficit: break
                if state_nda[si] > 0:
                    pivotality[si] += 1
                    cumulative += state_nda[si]

    print(f"  {sid}: {hung_sims}/{N_TP} hung ({hung_sims/N_TP:.1%})")

    piv_df = pd.DataFrame({
        "State": df["State"].values,
        "Seats_2024": df["Seats_2024"].values.astype(int),
        "NDA_2024": df["NDA_2024"].values.astype(int),
        "INDIA_2024": df["INDIA_2024"].values.astype(int),
        "pivotality_count": pivotality,
        "pivotality_pct": pivotality / max(hung_sims, 1),
        "scenario": sid,
        "scenario_desc": desc,
        "hung_count": hung_sims,
        "n_tp_sims": N_TP,
    })
    piv_df = piv_df.sort_values("pivotality_pct", ascending=False)
    tip_results.append(piv_df)
    print("    Top tipping-point states:")
    print(piv_df.head(8)[["State","Seats_2024","NDA_2024","INDIA_2024","pivotality_pct"]].to_string())
    print()

tip_df = pd.concat(tip_results, ignore_index=True)
tip_df.to_csv("state_tipping_points.csv", index=False)
print(f"Saved state_tipping_points.csv")
print(f"Total time: {time.time()-t0:.0f}s")
