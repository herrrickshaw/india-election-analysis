import pandas as pd
from itertools import combinations

QUOTA = 272
TOTAL = 543

def analyze_scenario(name, players_weights, quota=QUOTA):
    """players_weights: list of (name, seats). Returns dict with results."""
    players = [p for p, w in players_weights]
    weights = [w for p, w in players_weights]
    n = len(players)

    # Winning coalitions & minimal winning coalitions
    all_subsets = []
    for r in range(1, n+1):
        for combo in combinations(range(n), r):
            w = sum(weights[i] for i in combo)
            all_subsets.append((combo, w))
    winning = [(c, w) for c, w in all_subsets if w >= quota]

    def is_minimal(combo, w):
        for i in combo:
            if w - weights[i] >= quota:
                return False
        return True
    minimal_winning = [(c, w) for c, w in winning if is_minimal(c, w)]

    # Banzhaf
    banzhaf_counts = {p: 0 for p in players}
    for r in range(0, n):
        for combo in combinations(range(n), r):
            w = sum(weights[i] for i in combo)
            if w >= quota:
                continue
            for i in range(n):
                if i in combo:
                    continue
                if w + weights[i] >= quota:
                    banzhaf_counts[players[i]] += 1
    total_swings = sum(banzhaf_counts.values())
    banzhaf_index = {p: (banzhaf_counts[p]/total_swings if total_swings else 0) for p in players}

    is_hung = not any(w >= quota for p, w in players_weights)  # no single player has majority alone

    mwc_list = []
    for c, w in minimal_winning:
        names = [players[i] for i in c]
        mwc_list.append({"coalition": names, "seats": w, "margin": w - quota})

    return {
        "scenario": name,
        "players": list(zip(players, weights)),
        "is_hung": is_hung,
        "minimal_winning_coalitions": sorted(mwc_list, key=lambda x: (len(x["coalition"]), -x["seats"])),
        "banzhaf": sorted(banzhaf_index.items(), key=lambda x: -x[1]),
        "num_winning_coalitions": len(winning),
    }

# ============================================================
# SCENARIOS - using only parties/blocs that exist today (no new parties)
# Seat numbers are illustrative reallocations of the 543 total, varying how the
# SAME current parties might perform relative to 2024, not predictions.
# ============================================================

scenarios = {}

# S0: ACTUAL CURRENT (post TMC-split, June 2026) - baseline (3 seats vacant: Basirhat, Shillong, Nagaon)
scenarios["S0_Actual_Current"] = [
    ("NDA", 318), ("INDIA", 206), ("YSRCP", 4), ("AAP", 3), ("AD(WPD)", 2),
    ("AIMIM", 1), ("ASP(KR)", 1), ("SAD", 1), ("UPPL", 1), ("ZPM", 1), ("JKAIP", 1), ("IND", 1),
    ("Vacant", 3),
]

# S1: 2024 RESULT AS DECLARED (pre TMC-split) - the actual election outcome
scenarios["S1_2024_AsDeclared"] = [
    ("NDA", 293), ("INDIA", 234), ("YSRCP", 4), ("AAP", 3), ("AD(WPD)", 2),
    ("AIMIM", 1), ("ASP(KR)", 1), ("SAD", 1), ("UPPL", 1), ("ZPM", 1), ("JKAIP", 1), ("IND", 1),
]

# S2: BJP UNDERPERFORMS, NEITHER BLOC REACHES MAJORITY -> genuine hung parliament
# NDA drops to 255, INDIA rises to 260 (still short of 272), regional/unaligned parties swell to 28
scenarios["S2_NDA_Falls_Short"] = [
    ("NDA", 255), ("INDIA", 260), ("YSRCP", 10), ("AAP", 6), ("AD(WPD)", 4),
    ("AIMIM", 2), ("ASP(KR)", 2), ("SAD", 2), ("UPPL", 1), ("ZPM", 1),
]

# S3: TRUE HUNG PARLIAMENT - both major blocs well short, large swing bloc decisive
# NDA 240, INDIA 230, unaligned regional parties surge to 73 (redistributing from both blocs' allies defecting)
scenarios["S3_Deep_Hung_Parliament"] = [
    ("NDA", 240), ("INDIA", 230), ("YSRCP", 25), ("AAP", 12), ("BJD_revival", 15),
    ("AIMIM", 5), ("Other_regional", 16),
]

# S4: NDA NARROWLY SHORT, NEEDS ONE MAJOR SWING PARTY (e.g. YSRCP-scale revival)
scenarios["S4_NDA_Needs_Swing"] = [
    ("NDA", 260), ("INDIA", 245), ("YSRCP", 20), ("AAP", 6), ("AD(WPD)", 3),
    ("AIMIM", 2), ("ASP(KR)", 2), ("SAD", 2), ("UPPL", 1), ("ZPM", 1), ("JKAIP", 1),
]

# S5: INDIA BLOC OVERTAKES NDA BUT FALLS SHORT OF MAJORITY (role reversal from 2024)
scenarios["S5_INDIA_Largest_No_Majority"] = [
    ("NDA", 235), ("INDIA", 260), ("YSRCP", 16), ("AAP", 8), ("AD(WPD)", 4),
    ("AIMIM", 3), ("ASP(KR)", 2), ("SAD", 2), ("UPPL", 2), ("ZPM", 2), ("JKAIP", 2), ("IND", 7),
]

results = {}
for name, pw in scenarios.items():
    total_check = sum(w for p, w in pw)
    assert total_check == 543, f"{name}: seats sum to {total_check}, not 543"
    results[name] = analyze_scenario(name, pw)
    print(f"\n{'='*70}\nSCENARIO: {name}  (HUNG: {results[name]['is_hung']})")
    print(f"  Players: {pw}")
    print(f"  # Minimal winning coalitions: {len(results[name]['minimal_winning_coalitions'])}")
    for mwc in results[name]['minimal_winning_coalitions'][:8]:
        print(f"    {mwc['coalition']} -> {mwc['seats']} seats (margin +{mwc['margin']})")
    print(f"  Banzhaf power (top 6):")
    for p, b in results[name]['banzhaf'][:6]:
        print(f"    {p}: {b:.3f}")

import pickle
with open("scenario_results.pkl", "wb") as f:
    pickle.dump(results, f)
print("\n\nSaved scenario_results.pkl")
