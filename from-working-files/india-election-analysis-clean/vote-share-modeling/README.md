# vote-share-modeling

Constituency-level vote-share prediction using real TCPD Lok Dhaba data (1999–2019),
evaluated with a strict chronological train/validation/test split.

## ⚠️ Disclaimers — read before using any results from this project

**D-VSM-1 · None of the three models beat a naive baseline on held-out data.**
The headline result of this project is a negative finding: all three modeling
approaches (discrete classifier, Bayesian hierarchical MrP, Dirichlet-Swing)
fail to outperform a trivial "assume next election = same as last" baseline on
the genuine held-out test years (2014, 2019). This is reported as the main
result, not buried. Numbers from these models should not be used for prediction.

**D-VSM-2 · Data covers 1999–2019 only, not the full 75-year span.**
The TCPD Lok Dhaba GA AC-segment-wise export used here covers five elections
(1999, 2004, 2009, 2014, 2019). The complete historical archive from 1952
requires a separate download from lokdhaba.ashoka.edu.in and is not included
in this repo. Raw source files (`TCPD_GA_All_States_*.csv.gz`,
`TCPD_AE_All_States_*.csv.gz`) are listed in `.gitignore` and must be
provided by the user.

**D-VSM-3 · The raw TCPD file is AC-segment-wise, not PC-level.**
The GA export (`?seg=true`) records votes by assembly-constituency segment
within each parliamentary constituency. Script 01 rolls these up to true
PC-level winners by summing each candidate's votes across their AC segments.
Two data-cleaning issues were fixed during rollup (NOTA spuriously ranking #1
in an artifactual PC_Name sub-grouping; same seat appearing under different
name strings) — documented in script 01 comments.

**D-VSM-4 · Chronological split, not random — important for interpretation.**
Train: 1999/2004 | Validation: 2009 | Test: 2014/2019.
A random train/test split would constitute temporal leakage and produce
artificially inflated accuracy. The chronological split deliberately evaluates
the model's forward-looking ability, which is the only meaningful test for
election forecasting.

**D-VSM-5 · Regime-change failure is the correct, expected outcome.**
Train years (1999, 2004) were dominated by INC/INDIA-predecessor parties;
test years (2014, 2019) were the BJP/NDA wave. No model trained on one
political era can reliably predict outcomes after a genuine realignment. This
is a property of Indian electoral history, not a deficiency in the models.
Continuous vote-share modeling (MrP, Dirichlet-Swing) degrades more gracefully
than discrete classification but still fails to beat the naive baseline.

**D-VSM-6 · Dirichlet-Swing MLE degeneracy was found and fixed.**
Minka's fixed-point MLE algorithm for Dirichlet parameters is unstable on
data with substantial exact-zero mass (which occurs in this data because ~25%
of "Other"-origin constituencies have exactly zero NDA vote share in 1999–2004).
After testing two failed regularization approaches, MLE was replaced with
method-of-moments estimation. Full debugging history is in script 12 and in
the workbook's "Dirichlet-Swing Diagnostics" sheet.

## Data files (derived — original raw files not included)

| File | Rows | Contents |
|---|---|---|
| `data/ga_pc_level_winners.csv` | 2,704 | Real PC-level winner per election per constituency, rolled up from TCPD AC-segment data |
| `data/ga_pc_level_all_candidates.csv` | 34,466 | All candidates' PC-level vote totals (summed across AC segments) |
| `data/ga_features.csv` | 2,704 | Winner rows with engineered features (incumbency, margin, ENP, bloc label) |
| `data/vote_share_continuous.csv` | 2,704 | Continuous V_NDA, V_INDIA, V_Other per constituency-year |
| `data/ae_national_bloc_trend.csv` | ~61 | National NDA/INDIA/Other seat-share trend, 1961–2023, from AE data |

## Scripts (run in order)

Requires `TCPD_GA_All_States_*.csv` (gunzip'd) and `TCPD_AE_All_States_*.csv`
(gunzip'd) in the working directory — not included in this repo.

```bash
python scripts/01_rollup_ga_to_pc_level.py   # rolls up AC-segment rows to PC winners
python scripts/02_feature_engineering_discrete.py
python scripts/03_train_discrete_classifier.py
python scripts/04_recency_sensitivity_check.py
python scripts/05_ae_long_term_trend.py
python scripts/06_build_workbook_readme.py
python scripts/07_build_ae_trend_sheet.py
python scripts/08_build_classifier_results_sheet.py
python scripts/09_build_raw_sample_sheet.py
python scripts/10_build_continuous_vote_share.py
python scripts/11_hierarchical_mrp_model.py   # requires pymc; takes ~5 min
python scripts/12_dirichlet_swing_model.py
python scripts/13_build_vsm_workbook_readme.py
python scripts/14_build_model_comparison_sheet.py
python scripts/15_build_dsmm_diagnostics_sheet.py
python scripts/16_build_calibration_sheet.py
```

## Outputs

| File | Contents |
|---|---|
| `output/TCPD_Real_Data_Discrete_Classifier_Results.xlsx` | Discrete classifier results, 62-year AE trend, raw PC-level sample |
| `output/Continuous_Vote_Share_Models_MrP_DirichletSwing.xlsx` | Model comparison table, Dirichlet-Swing debugging diagnostics, MrP calibration check |

## Results summary

| Model | Validation MAE | Test MAE | Naive baseline MAE | Beats baseline? |
|---|---|---|---|---|
| Hierarchical Bayes (MrP) | 0.0995 | 0.1347 | 0.1198 | ❌ No |
| Dirichlet-Swing Matrix | 0.1475 | 0.1552 (pooled) | 0.1261 | ❌ No |
| Discrete classifier (LightGBM) | 55.6% acc | 29.3% acc | 19.9% baseline | ✅ Marginally |

Marginal classifier accuracy at 29.3% on a 3-class problem where random guessing
gives ~33% is not operationally useful. "Beats baseline" in that row is technically
true but meaningless in practice.
