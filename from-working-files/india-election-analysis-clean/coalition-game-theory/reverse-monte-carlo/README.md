# reverse-monte-carlo/

Three analytical layers applied to all 18 Lok Sabha elections (1952–2024) plus
forward projections to 2039 under four counterfactual scenarios.

## What this does

**Layer A — Seat reversal (deterministic):**
For every historical election, swap Congress and BJP seat counts. Recompute
the outcome (CON majority / BJP majority / Hung) under the swapped totals.
14 of 18 elections change outcome; 4 genuinely hung elections (1989, 1991,
1996, 1998, 2004, 2024) largely stay hung because Others are unchanged.

**Layer B — Vote-share reversal:**
Swap the national vote shares between Congress and BJP in each election.
This gives the "reversed trajectory" that feeds into Layer C.

**Layer C — Monte Carlo forward projection (2029, 2034, 2039):**
Fit a linear trend on the reversed vote-share trajectory (1999–2024) and
project forward. Run Dirichlet Monte Carlo simulations under four scenarios:
- **A: Actual trajectory** — BJP/NDA continues ~36–40%, Congress declines
- **B: Reversed trajectory** — Congress gets BJP's actual trend arc
- **C: Convergence** — both blocs approach 35%/33% parity
- **D: Deep reversal** — Congress returns to 1952-era dominance (~45%)

Uncertainty noise sweeps (±0, ±3pp, ±6pp added to each simulation's draw)
show how the probability distributions widen as the trend becomes less certain.

## Data files

| File | Rows | Contents |
|---|---|---|
| `historical_reversals.csv` | 18 | Per election: actual seats, reversed seats, actual outcome, reversed outcome, vote shares both directions. |
| `future_projections_v2.csv` | 36 | 4 scenarios × 3 years × 3 noise levels. P(Bloc1 majority), P(Bloc2 majority), P(Hung) at each. |

## Key findings

**Structural asymmetry:** The reversed timeline is very different from reality.
In the reversed world: BJP dominates 1952–1971 (when Congress was winning 350+
seats), the 1984 sympathy wave produces a BJP supermajority of 404 seats, and
the BJP era of 2014–2024 becomes a Congress resurgence. The FPTP amplification
mechanism is identical in both worlds — only the direction of dominance changes.

**Convergence scenario (C) is the most analytically interesting:**
At ±3pp uncertainty with both blocs near parity, the 2029 distribution is:
NDA ~62%, INDIA ~29%, Hung ~9%. This is where Monte Carlo adds genuine value
over linear extrapolation — the noise sweep makes the uncertainty visible.

**Deep reversal (D) shows a power transfer mid-projection:**
CON's simulated seat count overtakes BJP's between 2034 and 2039 as the reversed
trend compounds, producing the only scenario where the leading party actually
changes across the projection window.

## ⚠️ Disclaimers specific to this sub-project

**D-RMC-1 · Historical vote shares are national totals, not state-level.**
Pre-1999 state-level data is not in the TCPD export. National totals come from
ECI press notes and Wikipedia. Treating 'BJP' in 1952 as 'Jana Sangh' conflates
distinct party organisations with different support bases.

**D-RMC-2 · Reversal is pure arithmetic, not political simulation.**
The actual conditions that produced historical results (dynasty incumbency,
RSS network, Emergency, coalition dynamics) are not replicated by swapping
seat counts. The thought experiment tests FPTP arithmetic symmetry, not
counterfactual political history.

**D-RMC-3 · Future projection uses 2024 state-level geographic distribution.**
All forward simulations use the 2024 state-seat allocation and 2024 bloc
geographic distribution. Pre-delimitation seat maps are not modelled.

**D-RMC-4 · Linear trend extrapolation is not a forecast.**
Indian politics has never followed a linear trend for more than 2–3 consecutive
elections. The convergence and deep-reversal scenarios are illustrative, not
predictive.
