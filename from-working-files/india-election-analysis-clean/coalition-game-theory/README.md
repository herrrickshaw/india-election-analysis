# coalition-game-theory

Monte Carlo simulation of Lok Sabha coalition formation under different total seat counts.
Includes Banzhaf power index, Minimal Winning Coalition enumeration, and a seat-bias
sub-project testing the symmetry of electoral entrenchment.

## ⚠️ Disclaimers — read before using any numbers from this project

**D-CGT-1 · Seat-share used as vote-share proxy (material upward bias).**
The Dirichlet distribution mean for each constituency is set to its state's
2024 *seat share* (seats won / total state seats), not the real *vote share*.
NDA's seat share (~52.9%) exceeds its real vote share (~36–46% depending on
bloc definition) by 7–17 percentage points. P(majority) numbers are therefore
**upward-biased in level**. Directional findings — does the probability rise or
fall with more seats? — are robust. Absolute probabilities should not be cited
as point estimates.

**D-CGT-2 · Dirichlet concentration = 18 is ~1.8× too tight.**
The per-seat vote-share standard deviation implied by concentration=18 is
±11.5pp. Real TCPD constituency data shows ±20–21pp (implied concentration
≈ 4.5–5). Using the correct concentration raises the mean winner's bonus from
~1.2pp to ~3.3pp. All directional findings hold at concentration=5; the
parameter should be corrected in future versions. See the Assumption Audit
sheet in `seat-bias-analysis/output/Seat-Total_Bias_Analysis_534_to_1000.xlsx`
for the full sensitivity analysis.

**D-CGT-3 · "Debiased" means de-anchored from 2024, not unbiased overall.**
The simulation re-draws every seat's bloc outcome from a noisy Dirichlet
distribution each run, so the literal 2024 result is not locked in. However,
the *centre* of that distribution is still 2024 seat shares (see D-CGT-1).
"Debiased" in this context means "not deterministically anchored to a single
outcome", not "free of any partisan lean".

**D-CGT-4 · Seat-total sweep ≠ delimitation simulation.**
The 534–1,000 sweep adds simulated seats to states proportional to *current*
seat counts, not to 2011 Census population. This is the correct design for
testing the effect of House *size* in isolation. The PRS Delimitation Bill's
specific state-by-state reallocation is modelled separately in earlier work
(not included in this clean repo).

**D-CGT-5 · 1,000 seats is a stress test, not a proposal.**
The actual Delimitation Bill 2026 proposed a ceiling of 850 seats and was
defeated. 1,000 is used solely to test whether the pattern reverses at
extreme scale. It does not.

## Core simulation

**Data inputs** (`data/`):
- `party_seats.csv` — 2024 declared Lok Sabha seat counts by party/bloc
- `monte_carlo_draws.csv` — stored draws from the main simulation

**Scripts** (`scripts/01–12`): build the coalition game-theory Excel workbook
step by step. Run in numbered order from the `coalition-game-theory/` directory.

**Output:** `output/Lok_Sabha_Coalition_Game_Theory_Simulator.xlsx`
Contains: scenarios, MWC table, Banzhaf index, Monte Carlo results, dashboard.

## Seat-bias sub-project

See `seat-bias-analysis/README.md` for full detail. In brief:

- Sweeps winner's bonus (Gallagher disproportionality) and P(incumbent majority)
  from 534 to 1,000 seats in steps of 10, at 1,500 simulations per point
- Five counterfactual scenarios confirm the entrenchment effect is **symmetric**:
  it tracks distance from 50%, not which party leads
- Honest coin-flip disclaimer: more seats narrow the distribution around whatever
  mean already exists; if that mean is above 50%, more seats entrench the lead
  further, not less

## Key honest findings

1. No seat-total in 534–1,000 reduces *average* winner's bonus toward the leading
   bloc. The bonus is flat at ~1.1–1.2pp across the full range.
2. P(NDA majority under 2024 inputs) rises from 96.9% (534 seats) to 99.5%
   (1,000 seats). More seats ≠ fairer outcome.
3. In a genuine 50/50 toss-up, neither bloc benefits from more seats; instead the
   *hung-parliament rate* climbs from 48.1% to 58.8%.
4. Entrenchment is symmetric: INDIA with a 3pp lead behaves almost identically to
   NDA with a 3pp lead (95.1%→99.1% vs 95.9%→98.8%).
