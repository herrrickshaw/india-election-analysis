# Vote-Share Modeling on Real TCPD Lok Dhaba Data

Three progressively different modeling approaches applied to real Lok Sabha election
data (1999-2019, rolled up from TCPD's AC-segment-wise export), each evaluated with a
genuine chronological train/validation/test split.

**None of the three approaches reliably beats a naive baseline on the held-out test
years.** This is reported as the headline finding, not buried — see below.

## Background: data scope

The source files (`TCPD_GA_All_States_*.csv.gz`, `TCPD_AE_All_States_*.csv.gz`,
~180MB combined) are **not committed** to this repo — they're the user's own download
from [Lok Dhaba](https://lokdhaba.ashoka.edu.in/browse-data), too large and not ours to
redistribute. Only the *derived* datasets built from them are committed (see `data/`).

- **GA** (Lok Sabha, "AC Segment Wise" export): covers 1999-2019 (5 elections), not the
  full 75-year span originally requested — the complete historical archive sits behind
  Lok Dhaba's registration portal.
- **AE** (State Assembly): covers 1961-2023 (62 years), used only for long-term
  national bloc-share trend context.

## The three approaches, in order

### 1. Discrete classifier (win/lose label per constituency)
Predicts which bloc (NDA/INDIA/Other) wins each constituency. **Failed**: test accuracy
21-29% on a 3-class problem where random guessing gives ~33%. Root cause: train years
(1999, 2004) were INDIA-predecessor-dominant; test years (2014, 2019) were the BJP/NDA
wave — a genuine regime change discrete labels cannot survive.

### 2. Hierarchical Bayesian model (MrP-inspired partial pooling)
Adapts the core logic of Cerina & Duch (2021, PLOS ONE) — multilevel regression with
partial pooling across states — to predict **continuous** vote share `V_NDA` instead of
a discrete label. Fit with PyMC/NUTS. Beats the naive baseline on validation (2009) but
loses to it on test (2014+2019). Credible-interval coverage on test was only 13.5%
(should be ~90%) — the model is honestly calibrated for in-regime noise but has no way
to anticipate a national-level shift it never saw in training.

### 3. Dirichlet-Swing Matrix Model
Implements Mitra (2026, PLOS ONE)'s better-performing swing model: a Dirichlet-
distributed transition matrix describing where each bloc's previous plurality
redistributes next election. **Two real numerical bugs were found and fixed** while
implementing this on real data — see the output workbook's "Dirichlet-Swing Diagnostics"
sheet for the full debugging story (digamma-inversion overflow, then a deeper MLE-
degeneracy problem caused by ~25% exact-zero vote shares in some constituencies,
ultimately fixed by switching from MLE to method-of-moments estimation). Also loses to
the naive baseline on every test split.

## Outputs

| File | Contents |
|---|---|
| `output/TCPD_Real_Data_Discrete_Classifier_Results.xlsx` | Approach 1: rollup methodology, classifier results, 62-year AE trend |
| `output/Continuous_Vote_Share_Models_MrP_DirichletSwing.xlsx` | Approaches 2 and 3: model comparison, Dirichlet-Swing debugging diagnostics, credible-interval calibration check |

## How it was built

Scripts in `scripts/` are numbered in run order. Steps 1-9 build the discrete classifier
and its supporting workbook; steps 10-16 build the continuous vote-share models and
their workbook.

```bash
cd vote-share-modeling
# Requires the user's own TCPD_GA_All_States_*.csv and TCPD_AE_All_States_*.csv
# (gunzip'd) in the working directory -- not included in this repo.
python3 scripts/01_rollup_ga_to_pc_level.py
python3 scripts/02_feature_engineering_discrete.py
python3 scripts/03_train_discrete_classifier.py
python3 scripts/04_recency_sensitivity_check.py
python3 scripts/05_ae_long_term_trend.py
python3 scripts/06_build_workbook_readme.py
python3 scripts/07_build_ae_trend_sheet.py
python3 scripts/08_build_classifier_results_sheet.py
python3 scripts/09_build_raw_sample_sheet.py
python3 scripts/10_build_continuous_vote_share.py
python3 scripts/11_hierarchical_mrp_model.py
python3 scripts/12_dirichlet_swing_model.py
python3 scripts/13_build_vsm_workbook_readme.py
python3 scripts/14_build_model_comparison_sheet.py
python3 scripts/15_build_dsmm_diagnostics_sheet.py
python3 scripts/16_build_calibration_sheet.py
```

Requires `pandas`, `numpy`, `scikit-learn`, `lightgbm`, `pymc`, `arviz`, `scipy`,
`openpyxl` (see top-level `requirements.txt` for the core set; `pymc`/`arviz`/`lightgbm`
are additional to the other two projects in this repo).

## Key honest findings

1. **Data rollup matters**: the raw TCPD "AC Segment Wise" export records results at the
   assembly-segment level, not the actual parliamentary-constituency level — these must
   be summed per candidate before determining the true winner. Two real data quirks were
   found and fixed during this rollup (NOTA spuriously ranking #1 in an artifactual
   sub-grouping; the same seat appearing under inconsistent name strings across rows).
2. **Continuous modeling degrades more gracefully than discrete classification** under a
   political regime shift, but neither approach actually beats "assume no change" on
   real, held-out future elections.
3. **Dirichlet MLE is genuinely unstable on zero-inflated compositional data** — a
   documented statistical pathology, not a one-off bug — and required a methodology
   change (MLE to method-of-moments) to fix properly.
4. **No amount of modeling sophistication can see a genuine realignment coming** from
   pre-realignment data alone. Any vote-share "prediction" from these models should be
   read as a structural projection under stated assumptions, not a forecast.
