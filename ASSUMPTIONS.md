# Modelling assumptions: audit and tests

Audit date: 2026-10-25. Each load-bearing assumption in the analysis code is listed below
with where it lives, what the data in this repo says about it, and a verdict. Evidence comes
only from data already committed here:

- TCPD-derived Lok Sabha files, 1999-2019, PC level: `vote-share-modeling/data/*`
- 2024 state bloc seat totals: `coalition-game-theory/seat-bias-analysis/data/state_2024_bloc_results.csv`
- Committed Monte Carlo draws and outputs under `coalition-game-theory/data/` and `data/processed/`

Nothing was fetched from the network.

Every row has a test in `tests/test_assumptions_*.py`. Assumptions that hold are ordinary
tests, and each one states its threshold. Assumptions the data contradicts are
`xfail(strict=True)` tests whose `reason=` gives the numbers. If someone fixes the model,
the matching xfail starts passing, strict mode turns that into a failure, and the marker
has to be removed. Run the tests with `pytest tests/`.

Bloc seats for 1999-2019 use the repo's own party-to-bloc map
(`vote-share-modeling/scripts/02_feature_engineering_discrete.py:17`). That map assigns every
party to its current alliance in every year (see S4). "Realised (3-bloc)" means the bloc with
the largest summed vote share in each PC. That rule matches the actual winner's bloc in 85.7%
of PC-years (E5).

## Verdict table

| # | Assumption | Where | Evidence (repo data) | Verdict | Impact on headline results |
|---|---|---|---|---|---|
| **Coalition Monte Carlo** (`coalition-game-theory/scripts/04_monte_carlo_simulation.py`) ||||||
| M1 | Fixed seed makes results reproducible | `04_…:122` (`default_rng(42)`; `np.random.seed(42)` at :6 is unused) | Regenerating with seed 42 reproduces all 20,000 rows of `monte_carlo_draws.csv` bit for bit, and every row sums to 543 | **Holds** | None |
| M2 | 20,000 draws are enough | `04_…:9` | Standard error of P(hung) = 0.34pp | **Holds** | None |
| M3 | Majority = 272 of 543 | `04_…:7`, `06_…:50` | 543//2+1 = 272. With the 3 vacancies noted in `01_party_seat_data.py:63` the bar would be 271 of 540 | **Holds** (minor) | ±1 seat at the boundary |
| M4 | NDA and INDIA can be drawn independently | `04_…:42-73` | Rescaling each draw to 543 makes them strongly anti-correlated: corr = −0.94, against −0.98 historically (n=6) | **Holds** (by construction) | None |
| M5 | Uniform ranges NDA 220-360 and INDIA 180-320 are "historically plausible (2014/2019/2024)" | `04_…:23-37` | INDIA won 105 seats in 2014 and 111 in 2019. NDA won 170 in 2004 and 160 in 2009. Each range misses 2 of the 6 elections from 1999 to 2024 | **Contradicted** | The outcome space excludes a 2014/2019-style INDIA collapse |
| M6 | MC percentages are calibrated | `10_build_montecarlo_sheet.py`, README | The central 90% bands (NDA 226-319, INDIA 189-281) contain the realised result in 3/6 elections for NDA and 2/6 for INDIA. The README already says the output is not calibrated | **Contradicted** | Present 51.6% / 10.5% / 37.9% as properties of the chosen ranges, not as probabilities |
| M7 | Headline does not depend much on the ranges | `04_…:23-37` | Changing one range at a time: NDA floor set to 160 (the 1999-2019 minimum) moves NDA-majority from 51.6% to 36.5%. INDIA floor set to 105 moves it to 68.2%. Changing both moves hung from 37.9% to 27% | **Contradicted** (sensitivity measured) | The ±15-17pp swing comes from hand-set endpoints |
| **Vote-share-to-seat engine** (`seat-bias-analysis/scripts/01:47`, `05`; `expanded-simulation/01:57`; `state-wise-analysis/01`; reverse MC) ||||||
| E1 | Dirichlet concentration = 18 | `01_seat_bias…:25`, `expanded…:15` | Method of moments on within-state V_NDA dispersion over 96 state-years gives a median of 18.7 (IQR 6.4-54). The repo's own audit claimed "correct ≈ 5", but that figure came from the national spread, which double-counts between-state variance | **Holds**. The audit's proposed correction to 5 is not supported | Leave conc at 18 |
| E2 | State 2024 seat shares can stand in for vote-share means | `01_seat_bias…:33-42`, `05_…:39`, `expanded…:26` | The 2019 backtest with the same engine: seat-share means give NDA 367 seats, vote-share means give 321, realised (3-bloc) was 310. That is +57 seats, because FPTP's winner's bonus is applied twice | **Contradicted** (the repo flags the direction; this measures the size) | Every P(majority) figure in seat-bias, expanded and state-wise analyses is biased toward the 2024 leader |
| E3 | Constituencies are independent given state means (no common swing) | same engine | The independent engine's 90% interval for next-election NDA seats is about 29 seats wide and covers the realised result in **1 of 4** transitions (1999 to 2019). Adding a national swing (SD 5.8-7.6pp) and state swings (SD 8.6-10.5pp), both estimated out of sample, covers **3 of 4** with an interval about 212 seats wide (**7.4x**) | **Contradicted** | Uncertainty is understated by roughly an order of magnitude |
| E4 | "More seats entrench the leader": P(NDA majority) 96.9% at 534 seats rising to 99.5% at 1,000 | seat-bias README; `01_seat_bias…` | The engine reproduces 96.9% and 99.5% exactly. With one national swing of SD 6.5pp, the figures become 69.6% and 71.5%. The rise is within simulation noise | **Contradicted** (artefact of E3) | The headline level falls by about 27pp, and the entrenchment trend is not robust |
| E5 | 3-bloc FPTP (argmax over NDA/INDIA/Other) | `01_seat_bias…:56` | The argmax matches the real winning bloc in 85.7% of PC-years (78-91% by year) | **Holds** (approximately) | Small |
| E6 | Scenarios give every state the same NDA:INDIA split | `05_…:49` `build_scenario_shares`, `expanded…:32` | Replaying 1999-2019 with the realised national split gives a mean NDA seat error of about 62. Keeping each state's own lean gives about 19 | **Contradicted** | Scenario outputs (symmetry test, tipping points) ignore state geography |
| **Swing models** (`vote-share-modeling/`) ||||||
| S1 | Uniform swing vs proportional swing | `12_dirichlet_swing_model.py`; tests compare both rules | Using the realised (oracle) state swing, seat error summed over 4 transitions is 254 for uniform and 264 for proportional. Uniform is better in 3 of 4. Fitting on 2014 and predicting 2019: uniform 58, proportional 68 | **Holds** (uniform is at least as good, gap 4%) | Low |
| S2 | Swing should be measured per state, not nationally | as S1 | Uniform seat error is 254 with state swing and 342 with national swing. PC accuracy is higher with state swing in every transition | **Holds** | Supports E6 being a real problem |
| S3 | State swings are independent | implicit in E3 | A common national component explains about 33% of state-swing variance. In 3 of 4 transitions, at least 77% of states moved in the national direction | **Contradicted** | See E3 |
| S4 | Current alliances can be applied to every year | `02_feature_engineering_discrete.py:17`, `10_…:11` | In 1999, "INDIA" has a mean PC vote share 13.6pp above "NDA" but 38 fewer seats. That fits 1999 NDA allies (DMK, AITC) being counted as INDIA. Contemporaneous alliance data is not in the repo | **Untestable** (indicative only) | Biases 1999-2009 "regime-change" findings |
| S5 | The "Dirichlet swing" transition applies to prior shares | `12_dirichlet_swing_model.py` | Already a strict xfail from PR #1 (`tests/test_dirichlet_swing_model.py`): every seat in a bloc gets the same mean prediction | **Contradicted** (PR #1) | The model is a bloc-mean predictor, not a swing model |
| S6 | MrP model calibration (13.5% coverage) and discrete classifier | `11_hierarchical_mrp_model.py`, `03_train_…` | pymc and lightgbm are not installed here | **Untestable** in this environment | None |
| **Women's reservation** (`scripts/delimitation-optimization/`) ||||||
| W1 | `Sex == 'FEMALE'` selects women | `01_…:38`, `02_fit_…:42`, `05_lok_sabha_analysis.py:37,151,166` | TCPD codes sex as M/F/O. The committed LS file has 2,601 F rows and 0 FEMALE rows, so committed outputs show 0 women LS candidates and a 0.1% AE candidacy rate | **Code bug, fixed** (`sexcode.is_female`). Outputs are **stale** (strict xfail) until rerun on raw TCPD | All women-candidacy, electability and placement outputs need regenerating |
| W2 | Pre-reservation outcome | `06_monte_carlo_with_women.py` `classify_scenario` | The pre-reservation outcome tested post-carving NDA seats, so an NDA of 272-281 was labelled Hung | **Code bug, fixed** | None of the 6 published scenarios is affected (verified by rerun) |
| W3 | Baseline 51.58 / 10.505 / 37.915% | `06_…:21` | Exactly equal to the committed draws | **Holds** | None |
| W4 | Post-reservation shifts (−5%, −2%, +8% kingmaker) | `06_…:179-183` | Hand-set numbers. The published probabilities add up to 1.078. Applying the script's own carving rule to the 20,000 draws gives NDA majority 37.8% (published 49.0%), INDIA 4.7% (published 10.3%), and a women-pivotal outcome in 56.2% of draws (published 8%) | **Contradicted** | The "~8% kingmaker" and "~49% NDA" headlines do not follow from the model |
| W5 | 31 women elected (a "5.7% win rate") | `06_…:69`, `05_lok_sabha_placement.py:100` | Under Art. 330A, reserved seats can only be won by women, so reservation alone elects about 181. Without any reservation, 78 women won in 2019 (51-78 per election, 1999-2019) | **Contradicted** | The women's bloc size is understated about 6x |
| W6 | 188 reserved seats ("33% of 543") | `06_…:68` | 543/3 = 181. 188 is 34.6%. Elsewhere the repo uses 180 (`ceil(543*0.33)`) for the same quantity | **Contradicted** | Inconsistent across modules |
| W7 | Women form a separate cohesive bloc, carved equally from NDA, INDIA and others | `06_…:85` | Women MPs are elected on party tickets. In 2019 the 78 women split 43 NDA / 18 INDIA / 17 Other | **Contradicted** | The kingmaker framing does not fit how seats are won |
| W8 | NDA = INDIA = 35% of seats in every state | `04_coalition_sensitivity.py:85-86,199-200` | This makes hung risk "High" in all 34 states by construction. In 2024, one bloc held a seat majority in 28 of 36 states | **Contradicted** | `hung_parliament_risk_assessment.csv` and the state Banzhaf shifts carry no information |
| W9 | Logistic coefficient read as a probability change ("+1.80 → 180% more likely") | `02b_build_electability_workbook.py:43,120` | 1.80 is in log-odds. The odds ratio is e^1.80 = 6.05, and the probability change depends on the baseline | **Contradicted** (interpretation) | The electability workbook's prose is misleading. The coefficients are not |
| W10 | Bloc definitions are consistent across modules | `02_fit_…:56-57` vs `party_seats.csv` | AITC is in NDA and TMC is in INDIA (they are the same party). BJD is in both sets. YSRCP and AAP are in blocs here but unaligned in the coalition model | **Contradicted** | Bloc features in the electability model are mislabelled |
| **Reverse Monte Carlo** (`from-working-files/…/reverse-monte-carlo/`) ||||||
| R1 | The historical CON/BJP table is accurate | `data/historical_reversals.csv` | 2009, 2014 and 2019 match TCPD (within 3 seats and 1pp). **1999** has BJP at 303 seats / 36.5%, where TCPD has 180 / 23.7%, so the outcome "BJP majority" should be HUNG. **2004** has INC at 222, where TCPD has 142 | **Contradicted** (data errors) | The 1999 reversal row and its outcome are wrong |
| R2 | Projection scenario A is a linear trend | `data/future_projections_v2.csv` | A 1999-2024 OLS fit through the table reproduces 36.2 / 37.9 / 39.6% exactly. With 1999 corrected, the same method gives 40.5 / 44.0 / 47.5% | **Holds as a method; its input is wrong** | The 2029-39 projections inherit R1 |
| R3 | The noise SD (0 / 3 / 6pp) is a sensitivity input | same | Scenario C P(NDA majority) is 0.957 at 0pp and 0.579 at 6pp. The 1999-2019 national NDA swing RMS is about 6.5pp, so only the 6pp rows match the data | **Holds** (only at 6pp) | Quote the 6pp rows |
| **Coalition formation** (`02_bloc_level_game_theory.py`, `03_scripted_scenarios.py`) ||||||
| C1 | Pre-poll blocs hold together after the election. Unaligned parties are the only free agents | `02_…:21-35` | The repo has no data on post-poll defection or alliance switching | **Untestable** with this data | Banzhaf and MWC results are conditional on it |
| C2 | Late-June-2026 party strengths (the TMC split and Shiv Sena migration) | `01_party_seat_data.py:4-57` | These are hypothetical or current-event inputs, and the repo has no source data for them | **Untestable** | S0 scenario only |

## What this means for the published conclusions

1. **The seat-total bias / entrenchment finding (seat-bias README: 96.9% rising to 99.5%) is
   an artefact.** It comes from treating every seat as an independent draw (E3) and from
   using seat shares as vote means (E2). With a single national swing at the historical
   scale, P(NDA majority) is about 70% at both 534 and 1,000 seats. The independent engine's
   90% intervals covered the next election's NDA seats in only 1 of 4 historical
   transitions. The symmetry result (E6 scenarios) is still logically valid, but its levels
   share the same bias.
2. **The women-reservation Monte Carlo headlines do not follow from the model.** The quoted
   "NDA ~49% post-reservation" and "women kingmakers in ~8% of draws" are hand-set (W4).
   They are not even a probability distribution. The script's own carving rule gives 37.8%
   and 56.2%. The bloc size of 31 contradicts both the law (about 181 reserved seats, all
   won by women) and the data (78 women MPs in 2019) (W5-W7). Every women-candidacy and
   electability output was built with a filter that dropped almost all women (W1). The
   filter is now fixed, but the outputs must be regenerated from the raw TCPD files before
   any of them is cited.
3. **The 51.6% / 10.5% / 37.9% coalition Monte Carlo split describes the hand-chosen ranges,
   not the electorate (M5-M7).** The ranges exclude two of the last six elections, and
   moving one floor to its historical minimum shifts the headline by 15-17pp. The baseline
   numbers are, however, exactly reproducible from the committed draws (M1, W3).
4. **What holds:** the fixed seed and reproducibility; the draw count; the 272 quota; a
   Dirichlet concentration of about 18 (the repo's own audit was wrong to suggest 5);
   3-bloc FPTP as an approximation; and uniform state-level swing (no worse than
   proportional). The vote-share-modelling write-up's negative result ("nothing beats the
   naive baseline") fits the large, correlated national swings measured here (S3).

**Untestable with this data:** post-poll coalition behaviour (C1), the 2026 party-strength
inputs (C2), the size of the retroactive-bloc misclassification (S4), and the MrP and
discrete-classifier results (S6: pymc and lightgbm are not installed).

**Code fixes in this audit** (each proven with a failing test first): the Sex filter (W1) and
the pre-reservation outcome (W2). No modelling choice was changed. Every contradicted
assumption above is left in the code, recorded here, and covered by a strict xfail.

**Reproducibility note (not an assumption):** `seat-bias-analysis/scripts/01`, `05` and the
`from-working-files` simulation scripts read `/home/claude/...` paths that do not exist in
this repo. The tests rebuild their engine from the committed CSVs instead
(`tests/test_assumptions_seat_engine.py::test_helper_reproduces_script_engine_bit_for_bit`).
