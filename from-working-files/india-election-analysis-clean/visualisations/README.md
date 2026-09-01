# visualisations/

Four self-contained interactive HTML files. No server required — open directly
in any browser. All data is embedded inline; no external files needed.

## Files

### `lok_sabha_scenarios_explorer.html`
**Scenario explorer for the seat-bias analysis.**
Three tabs: (1) interactive scenario selector with a parliament hemicycle that
fills with bloc colour as you drag a seat-total slider; (2) full heatmap of
P(majority) across all five scenarios × 27 seat-totals; (3) winner's bonus
volatility chart. Five scenarios: NDA real lead, INDIA mirror, toss-up, small
leads each direction.

### `lok_sabha_full_simulation.html`
**Eight-scenario full simulation with tipping-point state analysis.**
Shows the complete three-way split (NDA majority / INDIA majority / Hung) for
all eight scenarios (NDA/INDIA at +11pp, +6pp, +3pp, +1pp, 50/50 tossup) across
seat-totals 543–1,000. Includes a state-by-state pivotality chart (greedy
Banzhaf attribution in the razor-edge +1pp scenario) showing UP dominates at
99.9% pivotality. Click any scenario pill to highlight it across all panels.

### `lok_sabha_reverse_mc_1952_2039.html`
**Reverse Monte Carlo across all 18 historical elections (1952–2024) plus four
forward scenarios to 2039.**
Three tabs: (1) side-by-side actual vs reversed seat outcomes for every election,
with a vote-share trajectory chart; (2) four future scenarios (actual trajectory,
reversed, convergence, deep reversal) with a noise slider that widens or narrows
the probability distributions; (3) power-flow timeline showing actual vs
counterfactual political history side by side.

### `lok_sabha_state_analysis.html`  ← **most comprehensive**
**State-wise historical analysis, seat reallocation, and scenario outcomes.**
Four tabs:
- **Historical Heatmap**: NDA seat share across 36 states × 6 elections. Toggle
  between NDA%, INDIA%, raw seats, and swing-since-1999 views. Sort by seats,
  NDA strength, trend slope, or A–Z. Click any cell or state name for full detail.
- **Seat Reallocation**: population-proportional reallocation at 543/600/650/750/
  850/1,000 seats using the Hamilton/largest-remainder method. Which states gain
  and lose seats at each House size; full state-by-state comparison table.
- **State Trends**: NDA vote-share trend by state (1999–2024 actual + 2029 linear
  projection). Filter by gaining/declining/large states. Mini-charts rank fastest
  gainers and decliners.
- **Scenario Outcomes**: Monte Carlo results under 2024 actual bloc shares or 2029
  trend projection, at each House size. Average NDA seat counts with 10th–90th
  percentile ranges.

## Data sources embedded in each file

| Data | Source |
|---|---|
| State-level NDA/INDIA/Other seats 1999–2019 | TCPD Lok Dhaba GA export, rolled up to PC-level |
| State-level 2024 results | ECI declared results (cross-checked The Week, DD News) |
| Population / electorate size | Census of India 2011; ECI Electoral Roll Summary 2024 |
| Historical national results 1952–2024 | ECI press notes; Wikipedia 'Indian general elections' |

## Disclaimers

All four files display disclaimer panels. Key points:
- D1: Seat-share used as vote-share proxy → P(majority) upward-biased
- D2: Dirichlet concentration=5 (empirically calibrated to TCPD data; earlier
  analyses used 18, which understated variance ~1.8×)
- D3: Anchored to 2024 declared results, not a forecast
- D4: TCPD data covers 1999–2019 only; 1952–1998 national totals from public records
