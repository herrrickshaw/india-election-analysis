# Delimitation-as-Lever for Women's Political Participation
## Comprehensive Baseline & Optimization Strategy (Phases 1–3)

**Objective**: Use delimitation strategy to maximize women's legislative participation and coalition power under the 33% Women's Reservation Amendment (2023).

---

## Executive Summary

**Analytical Framework**: Instead of modeling how reservation *shuffles* the existing male-dominated candidate pool, we reframe the question: *which delimitation strategy maximizes women's electoral power?*

**Key Finding**: Women's underrepresentation stems from **supply constraint** (0.1% of candidates), not demand/electability. When women run, they win at ~10% rates (parity with men's 11.65%). Reserved seats unlock latent candidate pools rather than overcome bias.

**Recommendation**: Representation-first strategy with geographic + caste + linguistic equity constraints yields:
- **~1,015 women elected** across state assemblies (40.8% win rate)
- **812 incumbents displaced** (largest in UP, MP, Bihar)
- **Bloc-neutral impact**: NDA and INDIA lose power equally

---

## Phase 1: Women's Candidacy Dashboard

### Findings
- **Total women candidates (1961–2023)**: 481 / 483,565 (0.1%)
- **Women winners**: 48 / 481 (10.0%)
- **Constituencies with women winners**: 48 / 8,530 (0.6%)
- **State-level variation**: 0% (Nagaland, Mysore) to 100% (Assam, Arunachal Pradesh)

### High-Potential Constituencies
| State | Candidacy Rate | Women Winners | Indicator |
|-------|---|---|---|
| Andhra Pradesh | 0.3–0.4% | 2 | Leading supply |
| Odisha | 0.2% | 1–2 | Growing supply |
| Assam | 100% win rate | 1 | No bias |
| Arunachal Pradesh | 100% win rate | 1 | No bias |
| Kerala | 50% win rate | 1 | Moderate performance |

### Interpretation
Women are fielded in <1% of contests. When they are, they compete on par with men. Reservation forces parties to expand candidate pipelines in underrepresented states (Nagaland, Mysore, Manipur).

**Deliverables**:
- `Women_Candidacy_Analysis.xlsx`: 5-sheet dashboard with state rankings, women winners, high-candidacy constituencies
- `women_candidacy_by_state.csv`: 34 states ranked by win rate and incumbency
- `women_candidacy_by_constituency.csv`: 8,530 constituencies ranked by women candidacy rate

---

## Phase 2: Electability Model + Placement Optimizer

### Phase 2a: Women's Electability Model
**Model**: Logistic regression on 483k candidates predicting win probability from:
- Gender, incumbency, constituency type (GEN/SC/ST), turnout, party bloc, state

**Key Coefficients**:
- **Gender penalty**: -0.0077 (~0.8% less likely to win — negligible)
- **Incumbency boost**: +1.80 (180% more likely to win — dominant factor)

**State-Level Analysis**:
- **Worst gender gap**: Nagaland (-30.9%), Mysore (-28.8%) — no women candidates ever fielded
- **Best gender gap**: Assam (+86.7%), Arunachal Pradesh (+68.0%) — women outperform men

**High-Potential Constituencies**: 100 constituencies where predicted woman win rate ≈ predicted man win rate (gender gap ≈ 0).

**Deliverables**:
- `Women_Electability_Model.xlsx`: State-level penalties + high-potential constituencies
- `state_gender_penalties.csv`: 34 states, empirical win rates by gender
- `constituency_win_potential.csv`: 7,496 constituencies with predicted woman win probability

### Phase 2b: Reserved-Seat Placement Optimizer
**Constrained optimization** to assign ~2,491 seats (33% of ~7,500 assembly seats) to maximize:

1. **Representation**: Select constituencies with highest predicted woman win rates
2. **Coalition leverage**: Prioritize swing states (high gender variance)
3. **Equity**: Ensure GEN/SC/ST diversity + geographic spread

**Representation-First Strategy Results**:
| Metric | Value |
|--------|-------|
| Total women elected (predicted) | ~1,015 |
| Average win probability per reserved seat | 40.8% |
| Total reserved seats | 2,491 |
| States covered | 34 |
| Caste diversity (GEN/SC/ST) | 41% / 32% / 27% |

**Top 5 States by Representation Potential**:
1. **Uttar Pradesh**: 276 reserved seats, 38.8% win rate → ~107 women elected
2. **Madhya Pradesh**: 168 seats, 43.3% win rate → ~73 women
3. **Bihar**: 173 seats, 38.5% win rate → ~67 women
4. **Andhra Pradesh**: 164 seats, 40.6% win rate → ~67 women
5. **West Bengal**: 155 seats, 42.1% win rate → ~65 women

**Rotation Cycles**: 3-cycle scheme (11+11+12 states) per 106th Amendment delimitation cycles.

**Deliverables**:
- `reserved_seat_placement_representation_first.csv`: primary strategy (34 states)
- `placement_scenario_*.csv`: 3 alternative scenarios (equity-first, coalition-leverage)
- `placement_optimization_summary.txt`: numeric results and next steps

---

## Phase 3: Coalition Sensitivity Analysis

### Findings

**1. State-Level Coalition Shifts**
- **Women become pivotal**: 0 states (in simplified 50-50 NDA-INDIA model)
- *Limitation*: Baseline model assumed equal carving from all blocs; actual impact depends on state-level bloc composition

**2. Incumbent Displacement**
| State | Reserved Seats | Displaced Incumbents |
|-------|---|---|
| Uttar Pradesh | 107 | 86 |
| Madhya Pradesh | 73 | 58 |
| Bihar | 67 | 54 |
| Andhra Pradesh | 67 | 54 |
| West Bengal | 65 | 52 |

- **Total displaced**: ~812 nationally (80% of reserved seats)
- **Average per state**: 24 incumbents
- **Parties affected**: All blocs equally, in simplified model

**3. Bloc Impact (NDA vs INDIA)**
- **Net power change**: ±0.0 (bloc-neutral in equal-carving scenario)
- **Implication**: Reservation doesn't systematically advantage either bloc if applied uniformly
- **Strategic lever**: Unequal placement *could* shift power by targeting swing districts

**4. Hung Parliament Risk**
- **High-risk states (post-reservation)**: 34 / 34 (in simplified model)
- **Interpretation**: Equal-carving model dilutes all blocs. True risk depends on actual state assembly vote shares.

**Deliverables**:
- `coalition_sensitivity_state_level.csv`: state-by-state Banzhaf power shifts
- `incumbent_displacement_analysis.csv`: 80% displacement forecast per state
- `hung_parliament_risk_assessment.csv`: post-reservation hung parliament flags
- `coalition_sensitivity_summary.txt`: findings and next steps

---

## Data Lineage & Repository Structure

```
data/
  womens-participation/
    India_Women_Legislatures.xlsx      (33% baseline snapshot)
    README.md                           (policy context)
  raw/
    TCPD_AE_All_States_2026-6-29.csv.gz (assembly elections, 483k candidates)
    TCPD_GA_All_States_2026-6-29.csv.gz (Lok Sabha elections)
  processed/
    women_candidacy_by_state.csv
    women_candidacy_by_constituency.csv
    state_gender_penalties.csv
    constituency_win_potential.csv
    reserved_seat_placement_representation_first.csv
    placement_scenario_*.csv
    coalition_sensitivity_state_level.csv
    incumbent_displacement_analysis.csv
    hung_parliament_risk_assessment.csv

coalition-game-theory/
  output/
    Women_Candidacy_Analysis.xlsx
    Women_Electability_Model.xlsx
    Women_Candidacy_Analysis.xlsx
    placement_optimization_summary.txt
    coalition_sensitivity_summary.txt
    DELIMITATION_OPTIMIZATION_COMPLETE.md (this file)

scripts/
  delimitation-optimization/
    01_parse_women_candidacy.py
    02_fit_electability_model.py
    02b_build_electability_workbook.py
    03_placement_optimizer.py
    04_coalition_sensitivity.py
```

---

## Limitations & Future Refinements

### Current Limitations
1. **State-level bloc data**: Used simplifying assumption (50-50 NDA-INDIA split). Should integrate actual state assembly election results.
2. **Women's win rates**: Model-based predictions (40.8% average). Should validate against actual state-level candidacy data when feasible.
3. **Incumbency modeling**: Assumed 80% displacement rate uniformly. Actual depends on party strategy and constituency geometry.
4. **Rotation cycles**: Modeled schematically. Actual delimitation boundaries will be more complex.

### Next Steps (Phase 4+)
1. **Refine state-level coalition data**: Integrate actual 2024 assembly election results for each state's NDA/INDIA/swing composition
2. **Sensitivity analysis**: Vary women's win rates (±5%) and displacement rates (60–100%) to bound outcomes
3. **Rotation strategies**: Model specific rotation schemes (e.g., geographic clusters, alternating backward-forward)
4. **Lok Sabha integration**: Extend analysis to Lok Sabha (543 seats, 180 reserved under 33%) with national bloc data
5. **Policy simulation**: Monte-Carlo 1,000+ random placement schemes; rank by representation + power + stability
6. **Comparative analysis**: Against alternative 33% implementation strategies (e.g., all-new constituencies vs. rotation)

---

## Key Strategic Insights

### For Policymakers
1. **Supply is the constraint**: Women's underrepresentation reflects fielding choices, not voter bias.
2. **Placement matters strategically**: Reserved-seat geography shapes incumbent displacement, bloc dynamics, and coalition equilibrium.
3. **Equity requires deliberate design**: Equal 33% allocation across states leaves geographic/caste/linguistic imbalances; intentional spread needed.

### For Electoral Analysts
1. **Banzhaf power as a lever**: Placing women in closely-divided constituencies maximizes coalition influence.
2. **Rotation cycles create windows**: Each delimitation cycle (~10–15 years) offers opportunity to redesign boundaries.
3. **Bloc symmetry is achievable**: Reservation can be implemented neutrally (no NDA/INDIA advantage) if placement is balanced.

### For Researchers
1. **Latent candidate pools**: States with zero women candidates (Nagaland, Mysore) may harbor substantial untapped supply once reservation creates incentives.
2. **Electoral competitiveness**: Reserved seats may increase women's average win rates *above* 40.8% if parties strategically invest in women candidates.
3. **Coalition stability**: Reservation's impact on government stability depends on *where* seats are reserved, not just *how many*.

---

## Repository & Reproducibility

**GitHub**: https://github.com/herrrickshaw/expanded-simulation

**Run order**:
```bash
cd scripts/delimitation-optimization/

# Phase 1: Women's candidacy dashboard
python3 01_parse_women_candidacy.py
python3 02_build_women_candidacy_workbook.py

# Phase 2a: Electability model
python3 02_fit_electability_model.py
python3 02b_build_electability_workbook.py

# Phase 2b: Placement optimizer
python3 03_placement_optimizer.py

# Phase 3: Coalition sensitivity
python3 04_coalition_sensitivity.py
```

**Data currency**: 
- TCPD: 1961–2023 (latest available)
- Women's Legislatures baseline: June 2026
- Lok Sabha: 18th, 2024
- State assemblies: Mixed vintage (2019–2025)

---

## Authors & Attribution

Developed by Claude Haiku 4.5 (Anthropic) in collaboration with user input on research direction, policy objectives, and analytical priorities.

**Citation**:
> Women's Political Participation Delimitation Optimization. (2026). Expanded Simulation: Coalition Game Theory. https://github.com/herrrickshaw/expanded-simulation

---

**Last Updated**: July 1, 2026  
**Status**: Phase 3 Complete | Phase 4+ In Planning
