"""
DISCLAIMER: See project README.md before using any numbers from this script.

Key caveats that apply to ALL outputs:
  - Dirichlet means are set from 2024 SEAT shares, not vote shares.
    P(majority) numbers are upward-biased; directional findings are robust.
  - Dirichlet concentration=18 implies per-seat variance of +/-11.5pp.
    Real constituency variance is +/-20-21pp (correct concentration ~5).
    Winner's bonus is ~1.8x understated. Directional findings still hold.
  - "Debiased" means not anchored to the literal 2024 result as a fixed floor;
    it does NOT mean free of partisan lean in the underlying state-level inputs.
"""

import numpy as np
import pandas as pd
from itertools import combinations
import pickle

np.random.seed(42)  # reproducibility
QUOTA = 272
TOTAL = 543
N_SIMULATIONS = 20000

# ============================================================
# PLAYERS & REALISTIC RANGES
# Anchored on current/historical performance of EXISTING parties only.
# NDA and INDIA modeled as blocs (their real bargaining behavior); unaligned
# parties modeled individually since they're the realistic kingmakers.
#
# Ranges reflect each party/bloc's plausible band based on 2014/2019/2024 performance
# and current strength, not arbitrary -- e.g. NDA has ranged 293-353 in last 3 elections
# (before the 2026 TMC merger), unaligned regionals have historically held single-digit
# to ~25 seat ranges depending on state-election cycles.
# ============================================================

party_ranges = {
    # party: (min_plausible, max_plausible, "weight" for Dirichlet concentration)
    "NDA":    (220, 360),
    "INDIA":  (180, 320),
    "YSRCP":  (0, 25),      # 2019: 22 seats; 2024: 0 seats -- genuinely volatile
    "AAP":    (0, 15),
    "AD(WPD)":(0, 5),
    "AIMIM":  (0, 6),
    "ASP(KR)":(0, 3),
    "SAD":    (0, 5),
    "UPPL":   (0, 2),
    "ZPM":    (0, 2),
    "JKAIP":  (0, 2),
    "IND":    (0, 10),
}

players = list(party_ranges.keys())
n_players = len(players)

def generate_one_draw(rng):
    """Generate one random-but-plausible seat distribution summing to 543."""
    # Sample each party's seat count uniformly within its plausible range
    raw = {}
    for p in players:
        lo, hi = party_ranges[p]
        raw[p] = rng.integers(lo, hi+1)

    # Scale to sum exactly to TOTAL via proportional adjustment + integer correction
    total_raw = sum(raw.values())
    if total_raw == 0:
        return None
    scale = TOTAL / total_raw
    scaled = {p: raw[p]*scale for p in players}
    floored = {p: int(np.floor(scaled[p])) for p in players}
    remainder = TOTAL - sum(floored.values())
    # distribute remainder by largest fractional part
    fracs = sorted(players, key=lambda p: -(scaled[p]-floored[p]))
    for i in range(remainder):
        floored[fracs[i % n_players]] += 1
    # Re-clip to respect max bounds approximately (soft clip then redistribute overflow to NDA/INDIA)
    overflow = 0
    for p in players:
        lo, hi = party_ranges[p]
        if floored[p] > hi:
            overflow += floored[p] - hi
            floored[p] = hi
    if overflow > 0:
        floored["NDA"] += overflow // 2
        floored["INDIA"] += overflow - overflow // 2
    assert sum(floored.values()) == TOTAL, f"sum={sum(floored.values())}"
    return floored

def analyze(players_weights, quota=QUOTA):
    names = [p for p, w in players_weights if w > 0]
    weights = [w for p, w in players_weights if w > 0]
    n = len(names)

    nda_w = dict(players_weights).get("NDA", 0)
    india_w = dict(players_weights).get("INDIA", 0)
    is_hung = nda_w < quota and india_w < quota

    # Minimal winning coalitions (only computed for hung cases - else trivial)
    num_mwc = None
    banzhaf = None
    if is_hung and n <= 14:  # tractable
        all_subsets = []
        for r in range(1, n+1):
            for combo in combinations(range(n), r):
                w = sum(weights[i] for i in combo)
                all_subsets.append((combo, w))
        winning = [(c, w) for c, w in all_subsets if w >= quota]
        def is_minimal(combo, w):
            return all(w - weights[i] < quota for i in combo)
        mwc = [(c, w) for c, w in winning if is_minimal(c, w)]
        num_mwc = len(mwc)

        banzhaf_counts = {p: 0 for p in names}
        for r in range(0, n):
            for combo in combinations(range(n), r):
                w = sum(weights[i] for i in combo)
                if w >= quota:
                    continue
                for i in range(n):
                    if i in combo:
                        continue
                    if w + weights[i] >= quota:
                        banzhaf_counts[names[i]] += 1
        total_swings = sum(banzhaf_counts.values())
        banzhaf = {p: (banzhaf_counts[p]/total_swings if total_swings else 0) for p in names}

    return {
        "is_hung": is_hung,
        "nda": nda_w,
        "india": india_w,
        "num_mwc": num_mwc,
        "banzhaf": banzhaf,
    }

import time
rng = np.random.default_rng(42)
draws = []
hung_count = 0
nda_majority_count = 0
india_majority_count = 0
banzhaf_accumulator = {p: [] for p in players}
mwc_counts_when_hung = []

t0 = time.time()
for sim in range(N_SIMULATIONS):
    draw = generate_one_draw(rng)
    if draw is None:
        continue
    pw = list(draw.items())
    result = analyze(pw)
    draws.append({**draw, "is_hung": result["is_hung"]})

    if result["is_hung"]:
        hung_count += 1
        if result["num_mwc"] is not None:
            mwc_counts_when_hung.append(result["num_mwc"])
        if result["banzhaf"]:
            for p, b in result["banzhaf"].items():
                banzhaf_accumulator[p].append(b)
    elif draw["NDA"] >= QUOTA:
        nda_majority_count += 1
    elif draw["INDIA"] >= QUOTA:
        india_majority_count += 1

print(f"Total valid simulations: {len(draws)}")
print(f"Elapsed: {time.time()-t0:.1f}s")
print(f"NDA outright majority: {nda_majority_count} ({nda_majority_count/len(draws)*100:.1f}%)")
print(f"INDIA outright majority: {india_majority_count} ({india_majority_count/len(draws)*100:.1f}%)")
print(f"HUNG parliament: {hung_count} ({hung_count/len(draws)*100:.1f}%)")
print(f"\nAmong hung scenarios, avg # minimal winning coalitions: {np.mean(mwc_counts_when_hung):.1f} (median {np.median(mwc_counts_when_hung):.0f})")

print("\nAverage Banzhaf power index (averaged ONLY over hung-parliament draws where party had nonzero seats):")
avg_banzhaf = {}
for p in players:
    vals = banzhaf_accumulator[p]
    avg_banzhaf[p] = np.mean(vals) if vals else 0.0
for p, v in sorted(avg_banzhaf.items(), key=lambda x: -x[1]):
    print(f"  {p}: {v:.4f}  (appeared in {len(banzhaf_accumulator[p])} hung draws)")

# Save everything
draws_df = pd.DataFrame(draws)
draws_df.to_csv("monte_carlo_draws.csv", index=False)

summary = {
    "n_simulations": len(draws),
    "nda_majority_count": nda_majority_count,
    "india_majority_count": india_majority_count,
    "hung_count": hung_count,
    "mwc_counts_when_hung": mwc_counts_when_hung,
    "avg_banzhaf": avg_banzhaf,
    "banzhaf_accumulator": banzhaf_accumulator,
}
with open("monte_carlo_summary.pkl", "wb") as f:
    pickle.dump(summary, f)
print("\nSaved monte_carlo_draws.csv and monte_carlo_summary.pkl")
