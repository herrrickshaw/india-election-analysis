"""
Counterfactual scenario generator (not a literal GAN -- see note below) testing whether
the "more seats entrench whoever is ahead" finding is symmetric: does it hold the same
way if INDIA is the favored bloc instead of NDA, and does the effect scale with the SIZE
of the lead? This directly tests the hypothesis from the coin-flip critique: entrenchment
should depend on DISTANCE FROM 50%, not on which bloc happens to be ahead.

NOTE ON METHOD: a literal Generative Adversarial Network (generator vs. discriminator
trained via adversarial loss) needs real training data to learn a distribution from --
not applicable here, since our "data" is itself a parametric simulation (Dirichlet draws
around a per-state mean), not an empirical sample large enough to train a GAN against.
What this script actually builds is a COUNTERFACTUAL SCENARIO GENERATOR: the same
validated simulation mechanism, run under different LEAD-FAVORING configurations, so the
results are directly comparable to each other and to the original NDA-favoring run.

SCENARIOS:
  S0_NDA_Real    -- baseline, NDA's actual 2024 lead (~53.6% vs ~42.5%, +11.1pp)
  S1_INDIA_Mirror -- exact mirror: INDIA leads by the SAME +11.1pp margin NDA had
  S2_Tossup      -- genuine 50/50 race (the literal "fair coin" case)
  S3_INDIA_Small -- INDIA leads by a SMALL margin (+3pp) -- tests if effect scales with lead size
  S4_NDA_Small   -- NDA leads by a SMALL margin (+3pp) -- mirror of S3, for symmetry check
"""
import numpy as np
import pandas as pd
import time

np.random.seed(11)
N_SIMULATIONS = 1500
DIRICHLET_CONCENTRATION = 18
SEAT_TOTALS = sorted(set(list(range(534, 1001, 20)) + [543, 850, 1000]))

state_df = pd.read_csv("state_2024_bloc_results.csv")
pop_df = pd.read_csv("/home/claude/election_analysis/state_data_raw.csv")[["State","Census2011_Pop"]]
df = state_df.merge(pop_df, on="State", how="left")
df = df.drop_duplicates(subset="State")
df["Census2011_Pop"] = df["Census2011_Pop"].fillna(df["Census2011_Pop"].median())
state_seat_counts = df["Seats_2024"].values.astype(float)

df["NDA_share_2024"] = df["NDA_2024"] / df["Seats_2024"]
df["INDIA_share_2024"] = df["INDIA_2024"] / df["Seats_2024"]
df["Other_share_2024"] = df["Other_2024"] / df["Seats_2024"]
for col in ["NDA_share_2024","INDIA_share_2024","Other_share_2024"]:
    df[col] = df[col].clip(lower=0.02)
share_sum = df["NDA_share_2024"] + df["INDIA_share_2024"] + df["Other_share_2024"]
df["NDA_share_2024"] /= share_sum
df["INDIA_share_2024"] /= share_sum
df["Other_share_2024"] /= share_sum

def build_scenario_shares(target_leader, lead_margin_pp, base_shares_df):
    """
    FINAL APPROACH (after two imperfectly-symmetric attempts, documented in the workbook's
    methodology sheet): per-state regional-lean preservation kept fighting against
    per-state Other-share heterogeneity, producing scenarios that were close to but not
    exactly symmetric mirrors of each other -- which matters a lot for a test whose whole
    point IS exact symmetry. This version uses a UNIFORM national target: every state
    gets the SAME (NDA_share, INDIA_share) split, with each state's real "Other" share
    preserved (so geographic variation in third-party/regional strength is retained, but
    the NDA-vs-INDIA contest itself is uniform nationally). This guarantees EXACT symmetry
    between mirrored scenarios by construction -- the realism trade-off (losing each
    state's individual NDA-vs-INDIA lean) is deliberate and stated explicitly.
    """
    other = base_shares_df["Other_share_2024"].values.copy()
    two_bloc_total = 1.0 - other  # whatever isn't "Other" is split between NDA/INDIA

    if target_leader == "NDA":
        nda_frac = 0.5 + (lead_margin_pp / 100.0) / 2.0
    elif target_leader == "INDIA":
        nda_frac = 0.5 - (lead_margin_pp / 100.0) / 2.0
    else:
        nda_frac = 0.5

    nda_new = nda_frac * two_bloc_total
    india_new = (1 - nda_frac) * two_bloc_total
    total = nda_new + india_new + other
    nda_new, india_new, other_new = nda_new/total, india_new/total, other/total
    return nda_new, india_new, other_new

def simulate_election(rng, n_seats, mean_shares_3col):
    weights = state_seat_counts / state_seat_counts.sum()
    chosen_idx = rng.choice(len(state_seat_counts), size=n_seats, p=weights)
    alpha = mean_shares_3col[chosen_idx] * DIRICHLET_CONCENTRATION
    alpha = np.clip(alpha, 0.3, None)
    gamma_draws = rng.standard_gamma(alpha)
    draws = gamma_draws / gamma_draws.sum(axis=1, keepdims=True)
    winners = np.argmax(draws, axis=1)
    seat_counts = np.array([np.sum(winners == k) for k in range(3)])
    vote_shares = draws.mean(axis=0)
    return seat_counts, vote_shares

SCENARIOS = {
    "S0_NDA_Real":     ("NDA", 11.1, "NDA"),
    "S1_INDIA_Mirror": ("INDIA", 11.1, "INDIA"),
    "S2_Tossup":       ("NDA", 0.0, "tossup"),
    "S3_INDIA_Small":  ("INDIA", 3.0, "INDIA"),
    "S4_NDA_Small":    ("NDA", 3.0, "NDA"),
}
BLOC_IDX = {"NDA": 0, "INDIA": 1, "Other": 2}

print(f"Testing {len(SEAT_TOTALS)} seat-totals across {len(SCENARIOS)} scenarios: {SEAT_TOTALS}")
all_results = []
t0 = time.time()

for scen_name, (track_bloc, margin, target_leader) in SCENARIOS.items():
    nda_new, india_new, other_new = build_scenario_shares(target_leader, margin, df)
    mean_shares_3col = np.column_stack([nda_new, india_new, other_new])
    track_idx = BLOC_IDX[track_bloc]

    for total in SEAT_TOTALS:
        quota = total // 2 + 1
        rng = np.random.default_rng(11)
        seat_share_draws, vote_share_draws, win_count = [], [], 0
        for sim in range(N_SIMULATIONS):
            seat_counts, vote_shares = simulate_election(rng, total, mean_shares_3col)
            seat_share_draws.append(seat_counts / total)
            vote_share_draws.append(vote_shares)
            if seat_counts[track_idx] >= quota:
                win_count += 1
        seat_share_mean = np.mean(seat_share_draws, axis=0)
        vote_share_mean = np.mean(vote_share_draws, axis=0)
        per_sim_bonus = [s[track_idx] - v[track_idx] for s, v in zip(seat_share_draws, vote_share_draws)]
        bonus_mean = np.mean(per_sim_bonus)
        bonus_std = np.std(per_sim_bonus)

        all_results.append({
            "scenario": scen_name, "tracked_bloc": track_bloc, "target_margin_pp": margin,
            "total_seats": total, "quota": quota,
            "tracked_seat_share": seat_share_mean[track_idx],
            "tracked_vote_share": vote_share_mean[track_idx],
            "mean_bonus": bonus_mean, "bonus_std": bonus_std,
            "pct_tracked_majority": win_count / N_SIMULATIONS,
        })
    print(f"{scen_name}: done ({time.time()-t0:.1f}s elapsed)")

results_df = pd.DataFrame(all_results)
results_df.to_csv("gan_scenario_results.csv", index=False)
print(f"\nTotal elapsed: {time.time()-t0:.1f}s")
print("Saved gan_scenario_results.csv")

print("\n--- Summary: P(tracked bloc majority) at min and max seat-total per scenario ---")
for scen in SCENARIOS:
    sub = results_df[results_df.scenario == scen]
    lo = sub[sub.total_seats == sub.total_seats.min()]
    hi = sub[sub.total_seats == sub.total_seats.max()]
    corr = np.corrcoef(sub["total_seats"], sub["pct_tracked_majority"])[0,1]
    print(f"{scen}: P(majority) {lo['pct_tracked_majority'].values[0]:.3f} -> {hi['pct_tracked_majority'].values[0]:.3f} "
          f"(seats {int(lo['total_seats'].values[0])}->{int(hi['total_seats'].values[0])}), corr={corr:.3f}")
