# Seat-Total Bias Analysis (534-1,000 Seats)

Tests whether any Lok Sabha seat-total between 534 and 1,000 makes electoral outcomes
less biased toward whoever currently holds the majority — and whether that finding is
specific to NDA or applies symmetrically to whichever bloc leads.

## Two outputs, two questions

### 1. `output/Seat-Total_Bias_Analysis_534_to_1000.xlsx`
**Question:** is there a seat-total in this range that reduces electoral bias toward the
incumbent (NDA)?

**Answer:** No. The mean "winner's bonus" (leading bloc's seat share minus its true vote
share) stays flat at 1.11–1.21 percentage points across the entire range. But the
*probability* of the incumbent keeping its majority rises steadily from 96.9% (534
seats) to 99.5% (1,000 seats) — more seats don't make the system fairer, they make the
existing lead more certain.

**Includes a prominent, explicit disclaimer** addressing the "coin flip" critique: a
coin's win probability per flip never depends on flip count. More seats narrowing the
spread around a *50/50* mean would be neutral — but NDA's true support isn't at 50%, so
narrowing the spread around its *off-center* mean entrenches the lead instead. The
workbook states this distinction loudly before presenting any results.

### 2. `output/Entrenchment_Symmetry_Test.xlsx`
**Question:** does the entrenchment effect from (1) apply specifically to NDA, or to
whichever bloc happens to be ahead?

**Answer:** It's symmetric. Five scenarios using the same simulation engine — NDA's real
lead, an exact INDIA mirror of that lead, a true 50/50 toss-up, and small ±3pp leads for
each side — confirm entrenchment tracks *distance from 50%*, not party identity. In the
toss-up case, neither side's win probability rises; instead the *hung-parliament rate*
climbs symmetrically for both blocs (48.1% to 58.8% from 534 to 1,000 seats).

This is **not a literal GAN** (no generator/discriminator trained adversarially — there's
no real dataset large enough to train one against). It's a counterfactual scenario
generator: the same validated simulation, re-run under different lead-favoring
configurations so results are directly comparable. This naming distinction is stated
explicitly in the workbook's README sheet.

## Two real bugs found and fixed (documented for transparency)

1. **Vote-share measurement bug (Seat-Total Bias Analysis):** the first simulation
   attempt measured "vote share" using the same random draw that picked each seat's
   winner, so seat share and vote share tracked each other almost perfectly by
   construction and showed a near-zero bonus everywhere. Fixed by drawing an actual
   continuous Dirichlet vote-share vector per seat, with the winner determined by FPTP
   (highest draw wins) and national vote share computed independently as the seat-
   weighted average of the underlying draws.

2. **Asymmetric scenario construction bug (Entrenchment Symmetry Test):** the first
   counterfactual-scenario method shifted NDA/INDIA shares additively, which could push
   values negative before clipping when flipping an 11-point lead to the opposite side (a
   ~22pp total swing) — the clip then distorted the two mirrored scenarios asymmetrically.
   A logit-space attempt got closer but was still off by ~2pp due to per-state "Other"
   share heterogeneity. Final fix: uniform national NDA-vs-INDIA split (each state's real
   "Other" share preserved, but the NDA/INDIA contest itself made uniform), verified to 6
   decimal places before trusting any further results.

   A third anomaly (NDA's win probability falling with more seats in the toss-up
   scenario) initially looked like a leftover bug but turned out to be correct behavior:
   with NDA and INDIA tied, neither clears 50% on average, so more seats make a hung
   outcome more likely for both sides — verified by checking that NDA and INDIA's
   individual win probabilities stayed nearly identical throughout (26.0% vs 25.9% at 534
   seats).

## How it was built

Scripts in `scripts/` are numbered in run order:

```bash
cd seat-bias-analysis
python3 scripts/01_seat_bias_sweep_534_to_1000.py
python3 scripts/02_build_direct_answer_sheet.py
python3 scripts/03_build_full_sweep_sheet.py
python3 scripts/04_build_methodology_sheet.py
python3 scripts/05_counterfactual_scenario_generator.py
python3 scripts/06_build_symmetry_test_readme.py
python3 scripts/07_build_symmetry_test_results.py
python3 scripts/08_build_symmetry_test_chart.py
```

Script 01 reads `data/state_2024_bloc_results.csv` (real 2024 state-wise NDA/INDIA/Other
seat results, compiled earlier in this project) and writes
`seat_bias_sweep_v2_to1000.csv`. Scripts 02-04 build the first workbook from that output.
Script 05 reads the same state-level data and writes `gan_scenario_results.csv`. Scripts
06-08 build the second workbook from that output. Run in a working directory containing
both this folder's `data/` files and write access for the generated CSVs and `.xlsx`
files.

## Assumption audit (post-hoc, added before commit)

A systematic check of every modeling assumption and random variable was conducted before
committing. **Two material issues found**:

1. **A1 — seat-share used as vote-share proxy (MATERIAL, upward bias in P(majority))**:
   The Dirichlet mean per constituency was set to each state's 2024 *seat share* (which
   bloc won how many seats), not its true *vote share*. NDA's seat share (~52.9%) exceeds
   its actual national vote share by 7–17pp depending on definition. This makes P(majority)
   numbers upward-biased in level. **Directional findings are not affected**; the absolute
   numbers should not be cited as point estimates without this caveat. Fix requires
   constituency-level vote-share data (TCPD Lok Dhaba full GA file).

2. **A2 — Dirichlet concentration = 18 too tight by ~1.8x (MATERIAL, winner's bonus understated)**:
   Concentration 18 gives per-seat std of ±11.5pp. Real TCPD 2014/2019 data shows ±20–21pp,
   implying an empirically correct concentration of ~4.5–5. Using conc=5 raises the mean
   winner's bonus from +1.2pp to +3.3pp. **Directional findings hold at conc=5**; would
   break at conc=2 or below. `conc=5` is the correct value for future versions.

Both issues are quantified in the workbook's "Assumption Audit" sheet. The symmetry test
(NDA vs INDIA mirroring) is unaffected by both biases because they apply equally to both
sides and cancel in the comparison.



1. No seat-total in 534-1,000 reduces *average* electoral bias toward whoever leads —
   that bias is structural to FPTP, not a tunable function of House size.
2. More seats does make outcomes more consistent/predictable around whatever the true
   underlying lean is — but predictability is not the same thing as fairness, and the
   first version of this analysis didn't make that distinction clearly enough (corrected
   explicitly in the final workbook).
3. The entrenchment effect is symmetric: it favors whichever bloc is ahead, by however
   much it's ahead — not NDA specifically. A genuine toss-up shows no such advantage to
   either side; it just makes hung parliaments more likely as the House grows.
