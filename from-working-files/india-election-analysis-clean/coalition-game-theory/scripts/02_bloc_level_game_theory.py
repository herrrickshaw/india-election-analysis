import pandas as pd
import numpy as np
from itertools import combinations

df = pd.read_csv("party_seats.csv")
QUOTA = 272
TOTAL_SEATS = 543
VACANT = 3

# ============================================================
# REALISTIC BARGAINING UNITS
# In practice, Indian coalition formation happens at two levels:
#  (1) Pre-election blocs (NDA, INDIA) that mostly hold together post-election
#  (2) "Swing" parties unaligned pre-election (or capable of defection) who become
#      pivotal ONLY in a hung-parliament scenario
# We model BOTH: (a) the realistic bloc-locked scenario (today's actual situation),
# and (b) a hypothetical "all parties as free agents" game to identify which
# UNALIGNED/swing parties would be kingmakers if the blocs fragment.
# ============================================================

# ---- Treat NDA and INDIA as cohesive blocs (their actual current behavior) ----
nda_seats = int(df[df.Bloc=="NDA"]["Seats"].sum())
india_seats = int(df[df.Bloc=="INDIA"]["Seats"].sum())
unaligned = df[df.Bloc=="UNALIGNED"][["Party","Seats"]].sort_values("Seats", ascending=False).reset_index(drop=True)
unaligned_total = int(unaligned["Seats"].sum())

print(f"NDA (cohesive): {nda_seats}")
print(f"INDIA (cohesive): {india_seats}")
print(f"Unaligned total: {unaligned_total}")
print(f"Vacant: {VACANT}")
print(f"Sum check: {nda_seats+india_seats+unaligned_total+VACANT} == {TOTAL_SEATS}")
print(f"\nUnaligned breakdown:\n{unaligned.to_string()}")

# ---- Players for the bloc-level game: NDA, INDIA, + each unaligned party individually ----
players = ["NDA", "INDIA"] + list(unaligned["Party"])
weights = [nda_seats, india_seats] + list(unaligned["Seats"])
n = len(players)
print(f"\nBloc-level game: {n} players, 2^{n} = {2**n} subsets (fully tractable)")

# Exact winning coalition enumeration
all_subsets = []
for r in range(1, n+1):
    for combo in combinations(range(n), r):
        w = sum(weights[i] for i in combo)
        all_subsets.append((combo, w))

winning = [(c, w) for c, w in all_subsets if w >= QUOTA]
print(f"\nTotal winning coalitions (>=272): {len(winning)} out of {len(all_subsets)} total subsets")

# Minimal winning coalitions: winning, but removing any member drops below quota
def is_minimal(combo, w, weights):
    for i in combo:
        if w - weights[i] >= QUOTA:
            return False
    return True

minimal_winning = [(c, w) for c, w in winning if is_minimal(c, w, weights)]
print(f"Minimal winning coalitions: {len(minimal_winning)}")
print("\n--- Minimal Winning Coalitions ---")
for c, w in sorted(minimal_winning, key=lambda x: len(x[0])):
    names = [players[i] for i in c]
    print(f"  {names} -> {w} seats (margin +{w-QUOTA})")

# ---- Exact Banzhaf Power Index over these players ----
# Banzhaf: for each player i, count subsets S (not containing i) such that S is losing
# but S+{i} is winning. i.e. i is "critical" / "swing" in that subset.
banzhaf_counts = {p: 0 for p in players}
for r in range(0, n):
    for combo in combinations(range(n), r):
        w = sum(weights[i] for i in combo)
        if w >= QUOTA:
            continue  # already winning without any additional player
        for i in range(n):
            if i in combo:
                continue
            if w + weights[i] >= QUOTA:
                banzhaf_counts[players[i]] += 1

total_swings = sum(banzhaf_counts.values())
banzhaf_index = {p: banzhaf_counts[p]/total_swings for p in players}

bdf = pd.DataFrame({
    "Player": players,
    "Seats": weights,
    "Swing_Count": [banzhaf_counts[p] for p in players],
    "Banzhaf_Index": [banzhaf_index[p] for p in players],
}).sort_values("Banzhaf_Index", ascending=False).reset_index(drop=True)

print("\n--- Banzhaf Power Index (bloc-level game) ---")
print(bdf.to_string())

bdf.to_csv("banzhaf_bloc_level.csv", index=False)
pd.DataFrame(minimal_winning, columns=["combo_idx","seats"]).to_csv("minimal_winning_raw.csv", index=False)

# Save minimal winning coalitions with names
mwc_rows = []
for c, w in minimal_winning:
    names = [players[i] for i in c]
    mwc_rows.append({"Coalition": " + ".join(names), "Seats": w, "Margin": w-QUOTA, "Num_Parties": len(c)})
mwc_df = pd.DataFrame(mwc_rows).sort_values(["Num_Parties","Seats"])
mwc_df.to_csv("minimal_winning_coalitions.csv", index=False)
print(f"\nSaved {len(mwc_df)} minimal winning coalitions.")
