"""
CORRECTED seat-bias sweep. The first version measured "vote share" as the same random
draw used to pick the winner -- which meant seat share and vote share tracked each other
almost perfectly by construction and showed near-zero bonus everywhere. That is NOT how
a real winner's bonus arises.

REAL MECHANISM: First-Past-The-Post converts a narrow vote-share LEAD within a seat into
a full win (100% of that seat's representation). A bloc that wins many seats by small
margins gets a seat share that exceeds its true national vote share. This is the actual
disproportionality literature's "winner's bonus".

FIX: for each simulated seat, draw an actual CONTINUOUS vote-share vector (NDA, INDIA,
Other) from a Dirichlet distribution centered on the state's known 2024 bloc shares. The
WINNER is whichever bloc has the highest drawn share in that seat (the FPTP mechanism).
The national VOTE SHARE is the seat-count-weighted AVERAGE of the continuous vote-share
vectors across all seats -- independent of who "won" each one. This is what lets seat
share and vote share genuinely diverge.
"""
import numpy as np
import pandas as pd
import time

np.random.seed(11)
N_SIMULATIONS = 1500
DIRICHLET_CONCENTRATION = 18

state_df = pd.read_csv("/home/claude/coalition_model/state_2024_bloc_results.csv")
pop_df = pd.read_csv("/home/claude/election_analysis/state_data_raw.csv")[["State","Census2011_Pop"]]
df = state_df.merge(pop_df, on="State", how="left")
df = df.drop_duplicates(subset="State")
df["Census2011_Pop"] = df["Census2011_Pop"].fillna(df["Census2011_Pop"].median())

df["NDA_share_2024"] = df["NDA_2024"] / df["Seats_2024"]
df["INDIA_share_2024"] = df["INDIA_2024"] / df["Seats_2024"]
df["Other_share_2024"] = df["Other_2024"] / df["Seats_2024"]
for col in ["NDA_share_2024","INDIA_share_2024","Other_share_2024"]:
    df[col] = df[col].clip(lower=0.02)
share_sum = df["NDA_share_2024"] + df["INDIA_share_2024"] + df["Other_share_2024"]
df["NDA_share_2024"] /= share_sum
df["INDIA_share_2024"] /= share_sum
df["Other_share_2024"] /= share_sum

state_names = df["State"].values
state_seat_counts = df["Seats_2024"].values.astype(float)
mean_shares = df[["NDA_share_2024","INDIA_share_2024","Other_share_2024"]].values

def simulate_election(rng, n_seats):
    weights = state_seat_counts / state_seat_counts.sum()
    chosen_idx = rng.choice(len(state_names), size=n_seats, p=weights)
    alpha = mean_shares[chosen_idx] * DIRICHLET_CONCENTRATION
    alpha = np.clip(alpha, 0.3, None)
    # Vectorized Dirichlet via Gamma: Dir(alpha) = Gamma(alpha_k)/sum(Gamma(alpha_k))
    gamma_draws = rng.standard_gamma(alpha)  # (n_seats, 3), shape params vary per row
    draws = gamma_draws / gamma_draws.sum(axis=1, keepdims=True)
    winners = np.argmax(draws, axis=1)
    seat_counts = np.array([np.sum(winners == k) for k in range(3)])
    vote_shares = draws.mean(axis=0)
    return seat_counts, vote_shares

SEAT_TOTALS = sorted(set(list(range(534, 1001, 10)) + [850, 1000]))
print(f"Testing {len(SEAT_TOTALS)} seat-totals: {SEAT_TOTALS}")

results = []
t0 = time.time()
for total in SEAT_TOTALS:
    quota = total // 2 + 1
    rng = np.random.default_rng(11)

    seat_share_draws = []
    vote_share_draws = []
    per_sim_bonus = []
    nda_majority_count = 0
    for sim in range(N_SIMULATIONS):
        seat_counts, vote_shares = simulate_election(rng, total)
        seat_shares = seat_counts / total
        seat_share_draws.append(seat_shares)
        vote_share_draws.append(vote_shares)
        per_sim_bonus.append(seat_shares[0] - vote_shares[0])  # THIS election's realized bonus
        if seat_counts[0] >= quota:
            nda_majority_count += 1

    seat_share_mean = np.mean(seat_share_draws, axis=0)
    vote_share_mean = np.mean(vote_share_draws, axis=0)
    bonus_mean = np.mean(per_sim_bonus)       # average realized bonus, single elections
    bonus_std = np.std(per_sim_bonus)         # KEY: how much the bonus VARIES election-to-
                                                # election -- this is what the literature's
                                                # "smaller assemblies = bigger swings/bonus
                                                # variance" prediction is actually about

    seat_bonus_leader = seat_share_mean[0] - vote_share_mean[0]
    gallagher = np.sqrt(0.5 * np.sum((seat_share_mean - vote_share_mean)**2)) * 100

    results.append({
        "total_seats": total, "quota": quota,
        "nda_seat_share": seat_share_mean[0], "nda_vote_share": vote_share_mean[0],
        "india_seat_share": seat_share_mean[1], "india_vote_share": vote_share_mean[1],
        "other_seat_share": seat_share_mean[2], "other_vote_share": vote_share_mean[2],
        "seat_bonus_leader": seat_bonus_leader,
        "bonus_std_across_elections": bonus_std,
        "gallagher_index": gallagher,
        "pct_nda_majority": nda_majority_count / N_SIMULATIONS,
    })
    print(f"Seats={total:>4} | NDA seat%={seat_share_mean[0]:.4f} vote%={vote_share_mean[0]:.4f} "
          f"| mean_bonus={seat_bonus_leader:+.4f} | bonus_std={bonus_std:.4f} | Gallagher={gallagher:.3f} | P(majority)={nda_majority_count/N_SIMULATIONS:.3f}")

print(f"\nElapsed: {time.time()-t0:.1f}s")
results_df = pd.DataFrame(results)
results_df.to_csv("seat_bias_sweep_v2_to1000.csv", index=False)
print("\nSaved seat_bias_sweep_v2_to1000.csv")

min_bonus_row = results_df.loc[results_df["seat_bonus_leader"].abs().idxmin()]
min_gallagher_row = results_df.loc[results_df["gallagher_index"].idxmin()]
print(f"\nSeat-total with smallest |seat bonus| to leader: {min_bonus_row['total_seats']:.0f} (bonus={min_bonus_row['seat_bonus_leader']:+.4f})")
print(f"Seat-total with smallest Gallagher index: {min_gallagher_row['total_seats']:.0f} (Gallagher={min_gallagher_row['gallagher_index']:.3f})")

corr_bonus = np.corrcoef(results_df["total_seats"], results_df["seat_bonus_leader"].abs())[0,1]
corr_gallagher = np.corrcoef(results_df["total_seats"], results_df["gallagher_index"])[0,1]
print(f"\nCorrelation(seats, |seat bonus|): {corr_bonus:.3f}")
print(f"Correlation(seats, Gallagher index): {corr_gallagher:.3f}")
print("(negative correlation = bias falls as seats increase, consistent with literature)")
