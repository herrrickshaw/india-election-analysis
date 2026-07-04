# election-data-analysis

State-level analysis of constituency size inequality in the Lok Sabha (2014–2024),
with population growth context for the delimitation debate.

## What this measures

- **Electors per constituency** by state (2014, 2019, 2024 electoral rolls)
- **Growth rate** of electors per seat since the 2014 baseline
- **Malapportionment** — how far each state's average seat size deviates from
  the national mean, given that seats have been frozen since 1976

## ⚠️ Disclaimers

**D-EDA-1 · Seat share ≠ vote share.**
This project measures *seats* and *electors*, not votes cast. Voter turnout
varies significantly by state and election, so "electors per seat" is a proxy
for constituency size, not a direct measure of actual voter representation.

**D-EDA-2 · Data source limitations.**
State-level electoral roll totals are sourced from ECI press releases and
Wikipedia summaries, not from ECI's constituency-level raw roll downloads.
Figures may differ marginally from official ECI tabulations due to rounding or
post-publication corrections.

**D-EDA-3 · No delimitation outcome assumed.**
The Delimitation Bill 2026 was defeated on 17 April 2026. This project
documents the *existing* malapportionment under the frozen 1976 allocation;
it does not model what a future delimitation would produce.

## Data

| File | Contents | Source |
|---|---|---|
| `data/state_data_raw.csv` | State-wise LS seats, 2011 Census pop, 2024 electors | ECI, Census of India |
| `data/national_trend.csv` | National average electors/seat, 2014–2024 | ECI electoral rolls |

## Scripts (run in order)

```bash
python scripts/01_build_state_data.py        # builds state_data_raw.csv
python scripts/02_build_national_trend.py    # builds national_trend.csv
python scripts/03_build_workbook_sheets1-2.py
python scripts/04_build_national_trend_sheet.py
python scripts/05_build_growth_delimitation_sheet.py
python scripts/06_build_dashboard.py
```

## Output

`output/India_Election_Voters_per_Constituency_Analysis.xlsx` (5 sheets):
- Sheet 1: State-wise electors per seat comparison
- Sheet 2: National trend 2014–2024
- Sheet 3: Growth rate and state deviation from national mean
- Sheet 4: Delimitation context
- Sheet 5: Dashboard

## Key numbers

- National average (2024): **~16.8 lakh electors per seat**
- NDA-average constituency (2024): **~17.9 lakh**
- Highest: Delhi (~22.5 lakh) · Lowest: Lakshadweep (~55k)
- Growth since 2014: **+16% nationally**, seats unchanged at 543
