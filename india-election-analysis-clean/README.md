# India Election Analysis

Quantitative analysis of Lok Sabha (Indian general election) seat allocation,
coalition formation, and party win-probability across hypothetical House sizes.

**Three sub-projects, each self-contained:**

| Folder | Question | Method |
|---|---|---|
| `election-data-analysis/` | How has voter-per-seat inequality grown since 2014? | State-level ECI data, descriptive |
| `coalition-game-theory/` | What seat-total makes a hung parliament more or less likely? | Monte Carlo + Banzhaf power index |
| `vote-share-modeling/` | Can historical TCPD data predict constituency bloc outcomes? | Discrete classifier, MrP Bayes, Dirichlet-Swing |

---

## ⚠️ Global disclaimers — read before citing any number from this repo

### D1 · Seat-share used as vote-share proxy (material upward bias)
All simulations in `coalition-game-theory/` are driven by each state's 2024
**seat share** (which bloc won how many seats), not its true **vote share**.
NDA's 2024 national vote share was approximately 36–46% depending on how blocs
are aggregated; the model uses ~52.9% as the Dirichlet mean. This overstates
NDA's competitive position per constituency and biases P(majority) numbers
**upward**. Directional findings are robust; absolute probabilities are not
suitable as point estimates.

### D2 · Dirichlet concentration parameter too tight by ~1.8×
The per-seat vote-share variance assumed (Dirichlet concentration = 18,
implying ±11.5pp per-seat std) is roughly half the real constituency-level
variance observed in TCPD Lok Dhaba data (±20–21pp, implying concentration
≈ 4.5–5). Using the empirically correct concentration (~5) raises the mean
winner's bonus from ~1.2pp to ~3.3pp but preserves all directional findings.
This parameter should be updated to ~5 in any future version.

### D3 · Data covers 2024 (not a forward forecast)
All political inputs are anchored to the 2024 Lok Sabha declared result.
The models produce structural/arithmetic projections under stated assumptions,
not forecasts of a future election. Political realignments, new alliances,
delimitation outcomes, and shifts in voter preference are not modelled.

### D4 · TCPD data covers 1999–2019 only (not the full 75-year span)
The `vote-share-modeling/` project uses TCPD Lok Dhaba's AC-segment-wise
export, which covers 1999–2019 (5 elections). The full historical archive
from 1952 requires a separate download from lokdhaba.ashoka.edu.in and is
not included in this repo (size + licensing).

### D5 · No model reliably beat a naive baseline on held-out test data
All three vote-share models (discrete classifier, hierarchical MrP-Bayes,
Dirichlet-Swing) were evaluated with a strict chronological train/validation/
test split and **none outperformed a trivial "assume no change" baseline** on
the genuine held-out test years (2014, 2019). This is the honest headline
result, not buried in a footnote.

---

## Project 1 · `election-data-analysis/`

**Question:** how has constituency malapportionment grown since the 1976 seat freeze?

**Data:** State-level LS seat counts (ECI), 2011 Census population, 2024
electoral roll totals. All sourced from public ECI/Delimitation Commission
records; no TCPD data used here.

**Output:** `output/India_Election_Voters_per_Constituency_Analysis.xlsx`
(5 sheets: state comparison, national trend, growth map, dashboard).

**Key finding:** NDA's average constituency held ~17.9 lakh electors in 2024;
the national average rose 16% from 2014 to 2024 with seats frozen at 543.
Delhi's average (22.5 lakh) is >14× Lakshadweep's. The Delimitation Bill
2026 was defeated on 17 April 2026.

---

## Project 2 · `coalition-game-theory/`

**Question:** does changing the total number of Lok Sabha seats make a hung
parliament more or less likely — and does that depend on which bloc is ahead?

**Method:** Monte Carlo simulation (1,500–3,000 draws per seat-total), Banzhaf
power index, Minimal Winning Coalition enumeration. Debiased: every simulated
seat's bloc outcome is re-drawn from a noisy Dirichlet distribution centred on
its state's 2024 bloc share, so the literal 2024 result is one possible draw,
not a locked-in anchor.

**Core output:** `output/Lok_Sabha_Coalition_Game_Theory_Simulator.xlsx`

**Seat-bias sub-project** (`seat-bias-analysis/`):
- Sweeps P(incumbent majority) and winner's bonus from 534 to 1,000 seats
- Five counterfactual scenarios: NDA real lead, INDIA mirror, toss-up, small
  leads each direction — confirms entrenchment is symmetric (tracks distance
  from 50%, not party identity)
- Assumption audit sheet in the workbook documents both material biases (D1, D2)

**Key finding:** no seat-total in 534–1,000 reduces average FPTP bias toward
whoever is currently leading; the mean winner's bonus stays flat (~1.1–1.2pp).
More seats make outcomes more *predictable* around whatever mean already exists,
not more *fair* — because predictability and fairness are different things.

---

## Project 3 · `vote-share-modeling/`

**Question:** can constituency-level structural features (incumbency, margin,
fragmentation) predict which bloc wins each seat?

**Data:** TCPD Lok Dhaba GA (Lok Sabha) AC-segment-wise export, 1999–2019,
rolled up to true PC-level (constituency) winners. AE (Assembly) 1961–2023
for long-term state-politics trend.

**Three approaches:**
1. Discrete win/lose classifier (LightGBM, Random Forest, Logistic Regression)
2. Hierarchical Bayesian model (MrP-inspired partial pooling, PyMC/NUTS)
3. Dirichlet-Swing Matrix Model (Mitra 2026, PLOS ONE)

**Chronological split:** train 1999/2004 | validation 2009 | test 2014/2019.

**Honest result:** all three approaches fail on the genuine test split.
The 2014 BJP/NDA wave was a real political regime change that no model trained
on pre-2014 data could anticipate — this is a property of Indian electoral
history, not a modeling failure. Continuous vote-share models (approaches 2, 3)
degrade more gracefully than the discrete classifier, but neither beats a
trivial "assume no change" baseline on held-out data.

---

## Interactive visualisations

Four self-contained HTML files in `visualisations/` — open in any browser,
no server required, all data embedded inline.

| File | What it shows |
|---|---|
| `lok_sabha_scenarios_explorer.html` | Scenario explorer: parliament hemicycle, seat-slider, P(majority) curves, heatmap |
| `lok_sabha_full_simulation.html` | 8 scenarios, three-way NDA/INDIA/Hung split, tipping-point state chart |
| `lok_sabha_reverse_mc_1952_2039.html` | Historical reversals 1952–2024, four future scenarios to 2039, power-flow timeline |
| `lok_sabha_state_analysis.html` | **Most comprehensive**: state heatmap, seat reallocation, trends, scenario outcomes |

## Additional sub-projects (in `coalition-game-theory/`)

### `state-wise-analysis/`
State-level wins and losses across 6 elections (1999–2024), population-proportional
seat reallocation at 543–1,000 seats, per-state NDA vote-share trends and 2029
projections. Includes a full scenario simulation using empirically-calibrated
Dirichlet concentration (≈5, from TCPD constituency data) rather than the earlier
assumption of 18.

### `expanded-simulation/`
Eight scenarios with full three-way outcome breakdown (NDA majority / INDIA majority
/ Hung parliament), all summing to 100%. Includes state-level tipping-point
attribution: in the razor-edge (+1pp NDA) scenario, UP appears as the pivotal state
in 99.9% of hung simulations — its 80 seats and near-50/50 2024 split alone
determines whether the national NDA total crosses 272.

### `reverse-monte-carlo/`
All 18 historical elections reversed (Congress ↔ BJP seat swap), followed by four
forward scenarios to 2039: actual trajectory, reversed trajectory, convergence
(both blocs at ~35%), and deep reversal (Congress returns to 1952-era dominance).
Monte Carlo uncertainty sweeps (±0, ±3pp, ±6pp noise on projected vote shares)
show how probability distributions widen as the trend becomes less certain.

## Documentation

`docs/India_Election_Analysis_Problem_Solution.docx` — 442-paragraph Word document
covering the full problem statement and step-by-step solution for all three
sub-projects plus the extensions. Includes every bug found during development,
the assumption audit, model comparison tables, and all five global disclaimers.

---

## Running the code

```bash
git clone <this-repo>
cd india-election-analysis
pip install -r requirements.txt

# Project 1
cd election-data-analysis && python scripts/01_build_state_data.py && ...

# Project 2
cd coalition-game-theory && python scripts/01_party_seat_data.py && ...

# Project 3 — requires TCPD raw files (user's own download, not in repo)
# Place TCPD_GA_All_States_*.csv and TCPD_AE_All_States_*.csv in vote-share-modeling/
cd vote-share-modeling && python scripts/01_rollup_ga_to_pc_level.py && ...
```

See each subfolder's `README.md` for the full step-by-step run order.

---

## Sources

| Source | Used for |
|---|---|
| ECI declared results 2024 | State-wise NDA/INDIA/Other seat counts |
| Wikipedia "List of Indian general elections" | National election history 1952–2024 |
| TCPD Lok Dhaba (lokdhaba.ashoka.edu.in) | Constituency-level GA/AE data 1999–2019 |
| PRS Legislative Research | Delimitation Bill 2026, seat reallocation annexure |
| Census of India 2011 | State population for seat-weighting |
| Cerina & Duch (2021, PLOS ONE) | MrP methodology reference |
| Mitra (2026, PLOS ONE) | Dirichlet-Swing Matrix Model reference |

---

*All analysis is independent academic/research work. No affiliation with any
political party, electoral authority, or government body.*
