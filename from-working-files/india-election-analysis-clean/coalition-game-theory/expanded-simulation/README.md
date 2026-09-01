# expanded-simulation/

Eight counterfactual scenarios with full three-way outcome breakdown (NDA majority
/ INDIA majority / Hung parliament) and state-level tipping-point attribution.

## What's new vs the earlier seat-bias-analysis/

The earlier `seat-bias-analysis/` work tracked only one bloc (NDA) and used five
scenarios. This sub-project:
- Tracks **all three outcomes simultaneously**: P(NDA) + P(INDIA) + P(Hung) = 1.0
- Tests **eight scenarios** covering NDA/INDIA at +11pp, +6pp, +3pp, +1pp, and 50/50
- Runs **state-level tipping-point attribution** (Banzhaf-style greedy pivotality)
  for four NDA-leading scenarios at 543 seats, identifying which states appear in
  the minimum seat-set that would flip a hung result to NDA majority
- Uses 5,000 simulations per scenario (vs 1,500 in the earlier sweep)

## Data files

| File | Rows | Contents |
|---|---|---|
| `expanded_scenario_results.csv` | 80 | 8 scenarios × 10 seat-totals (543–1,000). P(NDA majority), P(INDIA majority), P(Hung), avg NDA/INDIA seats, 10–90th percentile ranges. |
| `state_tipping_points.csv` | 144 | Per-state greedy pivotality for 4 NDA scenarios at 543 seats. 8,000 simulations each. |

## Key findings

**Razor-edge scenario (NDA +1pp):**
- At 543 seats: P(NDA)=56.7%, P(INDIA)=8.5%, Hung=34.8%
- As seats increase to 1,000: P(NDA)≈57%, INDIA squeezed to ~3%, Hung≈40%
- More seats don't help NDA decisively — it stays around 55–58% at all House sizes

**Tossup (50/50):**
- P(NDA)≈26%, P(INDIA)≈26% (symmetric by construction)
- Hung rises from 46% (534 seats) to 62% (1,000 seats)
- Confirms coin-flip principle: more seats make hung outcomes more certain when
  neither bloc genuinely leads

**Tipping-point analysis (razor-edge at 543 seats):**
- UP appears pivotal in 99.9% of hung simulations — 80 seats, 36/43 NDA/INDIA
  split in 2024, typical NDA deficit of 5–20 seats is covered by UP's swing alone
- Maharashtra is secondary at 0.3%
- This is a greedy-fill metric, not a marginal-effect metric; it overweights
  large states by design (documented in the state_tipping_points.csv header)

## Caveats

Inherits D1 (seat-share proxy) and D2 (concentration=18 in the original run;
corrected to 5 in the state-wise-analysis scripts). See seat-bias-analysis/
assumption audit for full documentation.
