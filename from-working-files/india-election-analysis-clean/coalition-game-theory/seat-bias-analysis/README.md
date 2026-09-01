# seat-bias-analysis

Tests whether any Lok Sabha seat-total between 534 and 1,000 produces electoral
outcomes that are less biased toward whoever currently holds the majority, and
whether this effect is specific to NDA or applies symmetrically.

## ⚠️ Disclaimers

Inherits D-CGT-1 through D-CGT-5 from `../README.md`. Additional:

**D-SBA-1 · "Unbiased" has two distinct meanings here — keep them separate.**
- *Average bias* (mean winner's bonus across many elections at a fixed seat-total):
  flat throughout 534–1,000. No seat-total is more or less biased on average.
- *Outcome certainty* (P(tracked bloc wins majority)): rises monotonically with
  seats when the tracked bloc has a real lead. This is *not* a fairness gain —
  it is the law of large numbers narrowing the distribution around an off-centre
  mean, making the existing advantage more certain, not less. These two meanings
  must not be conflated.

**D-SBA-2 · The coin-flip critique is correct and material.**
A fair coin's win probability per flip never depends on the number of flips.
More flips only narrow the spread of the total count around whatever the coin's
true probability is. If the true probability is not 50%, more flips make the
unfair outcome *more* certain, not less. This applies directly: India's seats
are not 50/50 coins, so a larger House entrenches whoever is ahead, not 50/50
fairness. This disclaimer is displayed prominently in the output workbook.

**D-SBA-3 · The "GAN" is actually a counterfactual scenario generator.**
A literal Generative Adversarial Network requires training data; this project
uses a parametric simulation (Dirichlet draws around a specified mean). The
five counterfactual scenarios are labelled S0–S4, not "GAN scenarios", in all
code comments. The workbook README sheet explains this distinction.

**D-SBA-4 · Two bugs were found and fixed during development (documented).**
1. Vote-share measurement bug: first attempt measured vote share using the same
   draw that determined the winner, producing near-zero bonus everywhere. Fixed
   by using independent Dirichlet draws for the vote-share measurement.
2. Asymmetric scenario construction: three attempts were required to produce
   exact NDA/INDIA symmetry (additive shift, logit-space shift, then final
   uniform-split method). All three attempts and the final fix are documented
   in script 05 comments.

## What each script does

| Script | Purpose |
|---|---|
| `01_seat_bias_sweep_534_to_1000.py` | Main sweep: winner's bonus, Gallagher index, P(majority) at every 10 seats from 534 to 1,000. Saves `seat_bias_sweep_v2_to1000.csv`. |
| `02_build_direct_answer_sheet.py` | Builds the "Direct Answer" workbook sheet with disclaimer block. |
| `03_build_full_sweep_sheet.py` | Builds the data table and three charts sheet. |
| `04_build_methodology_sheet.py` | Documents simulation design and assumption corrections. |
| `05_counterfactual_scenario_generator.py` | Runs five counterfactual scenarios (S0 NDA real, S1 INDIA mirror, S2 toss-up, S3/S4 small leads). Documents all three construction-method attempts and final fix. Saves `gan_scenario_results.csv`. |
| `06–08` | Build the symmetry-test workbook (README, results, chart sheets). |
| `09_build_assumption_audit.py` | Adds the post-hoc assumption audit sheet to the bias-analysis workbook. |

## Data files

| File | Rows | Contents |
|---|---|---|
| `data/state_2024_bloc_results.csv` | 36 | Real 2024 NDA/INDIA/Other seats per state/UT, cross-checked against The Week, Al Jazeera, DD News |
| `data/seat_bias_sweep_v2_to1000.csv` | 49 | Winner's bonus, Gallagher index, P(NDA majority) at 534–1,000 seats (every 10) |
| `data/gan_scenario_results.csv` | 135 | P(tracked majority), mean bonus, bonus std for all 5 scenarios × 27 seat-totals |

## Outputs

| File | Contents |
|---|---|
| `output/Seat-Total_Bias_Analysis_534_to_1000.xlsx` | 4 sheets: Direct Answer (with disclaimer), Full Sweep Data & Charts, Methodology, Assumption Audit |
| `output/Entrenchment_Symmetry_Test.xlsx` | 3 sheets: Symmetry Test Results, README, All Scenarios Chart Data |

## Key findings (with honest caveats)

| Finding | Robust? | Caveat |
|---|---|---|
| Mean winner's bonus flat at ~1.1–1.2pp across all seat-totals | Yes | Absolute level is ~1.8× understated due to D-CGT-2 |
| P(majority) rises with seats when bloc leads | Yes | Absolute level upward-biased due to D-CGT-1 |
| Entrenchment is symmetric (NDA ≈ INDIA given equal leads) | Yes | Exact symmetry requires the uniform-split construction; earlier additive-shift construction broke symmetry |
| Toss-up case: hung rate rises with seats, not one bloc's majority | Yes | Confirmed by checking P(NDA win) = P(INDIA win) ≈ 26% in toss-up at 534 seats |
