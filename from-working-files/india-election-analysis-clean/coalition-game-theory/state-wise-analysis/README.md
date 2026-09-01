# state-wise-analysis/

State-level Lok Sabha wins, losses, seat reallocation under population-proportional
allocation, and vote-share trends with 2029 projections.

## ⚠️ Disclaimers

**D-SWA-1 · Seat-share used as vote-share proxy.**
NDA vote-share estimates are derived from 2024 seat shares (NDA_seats / total_seats
per state), not real vote shares. This is documented but unavoidable without
constituency-level vote totals for 2024 (not in the TCPD GA export, which covers
1999–2019 only). The 2024 national mean NDA "vote share" from this proxy is ~47%,
vs the real ECI vote share of ~37%. P(majority) numbers are upward-biased.

**D-SWA-2 · Historical data limited to 1999–2024.**
TCPD Lok Dhaba GA data covers five elections (1999, 2004, 2009, 2014, 2019).
The 2024 election is appended from ECI declared results. Pre-1999 state-level
breakdown is not in the GA export.

**D-SWA-3 · 2029 projections are linear extrapolations, not forecasts.**
Fitted on 1999–2024 (six elections). Indian politics has not followed any linear
trend for more than 2–3 consecutive elections. Use as directional indication only.

**D-SWA-4 · Seat reallocation uses 2024 electoral rolls, not 2026 projected population.**
The Hamilton/largest-remainder method is applied to 2024 elector counts. Future
delimitation would use population data from the next Census (not yet released as
of this analysis).

## Data files

| File | Rows | Contents |
|---|---|---|
| `state_historical_1999_2024.csv` | 199 | State × year × NDA/INDIA/Other seat counts. Source: TCPD GA 1999–2019 (party→bloc mapping) + ECI 2024 declared. |
| `state_seat_projection.csv` | 36 | Per-state seat allocation at House sizes 543/600/650/700/750/800/850/1,000. Hamilton method, min 1 seat per state. |
| `state_vote_share_trends.csv` | 35 | Per-state NDA/INDIA vote-share trend: slope (all elections), slope (recent 3 elections), 2029 projection. From TCPD vote-share data. |
| `state_full_data.csv` | 36 | Merged: seat projections + vote-share trends + 2024 actual NDA/INDIA seat shares. |
| `scenario_outcomes.csv` | 12 | MC simulation outcomes: 12 scenarios (2024 vs 2029 shares × 6 House sizes). 3,000 sims, Dirichlet conc=5. |

## Script

`scripts/01_expanded_simulation.py` — reads `state_2024_bloc_results.csv` (in
`seat-bias-analysis/data/`) and `state_seat_projection.csv`, runs per-state
Dirichlet simulation at each seat-total under 2024 and 2029 projected vote
shares, saves `scenario_outcomes.csv`.

## Key findings

**Seat reallocation (frozen 543 → pop-proportional 850):**
- UP gains 48 seats (86 → 134) — the single largest beneficiary
- Bihar +24, Maharashtra +30, MP +18, Gujarat +16
- No large state loses seats; only very small UTs (Lakshadweep, Goa) are affected

**State trends (NDA, 2014–2024 recent slope):**
- Fastest gaining: Odisha (+0.73/decade), Tripura (+0.56), Arunachal (+0.54),
  MP (+0.45), Andhra Pradesh (+0.46), Gujarat (+0.36), Bihar (+0.29)
- Fastest declining: Maharashtra (−0.13), Chandigarh (−0.43), Manipur (−0.12)

**Scenario outcomes (all anchored to 2024's strong NDA majority):**
- P(NDA majority) is 99.8–100% in all 12 scenarios — the interesting dimension
  is the average NDA seat count (296 at current frozen vs 474 at pop-prop 850)
  and the 2029 trend (NDA slightly gains seat count due to gaining states having
  large electorates)
