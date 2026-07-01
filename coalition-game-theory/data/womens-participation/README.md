# Women's Political Participation — Representation Gap & Reservation Scenario

_Data module for `coalition-game-theory/expanded-simulation`_

## Why this sits in the coalition-simulation repo

The existing simulation models coalition arithmetic and vote-share dynamics over the
current (largely male) composition of the Lok Sabha and state assemblies. The **Nari
Shakti Vandan Adhiniyam (106th Constitutional Amendment, 2023)** will, once the census
and delimitation are complete, reserve **one-third of Lok Sabha and state-assembly seats
for women** on a rotating basis.

That is a structural shock to the candidate pool and, potentially, to coalition
behaviour. This module supplies the **baseline representation data** needed to model it —
the "before" state against which a 33%-reservation "after" can be simulated:

- Which seats/houses are furthest from the 33% floor (largest forced turnover).
- How rotational reservation could reshuffle incumbents and alliance seat-shares.
- Whether reservation shifts coalition formation in closely-divided assemblies.

## Contents

| File | Description |
|------|-------------|
| `India_Women_Legislatures.xlsx` | 3-sheet workbook: national summary, state-wise assembly detail (ranked, with per-house shortfall to 33%), and a policy/notes sheet with coverage caveats and sources. All figures are live formulas. |

## Headline baseline (current)

| Tier | Seats | Women | Women % | Shortfall to 33% |
|------|------:|------:|--------:|-----------------:|
| Lok Sabha (18th, 2024) | 543 | 74 | 13.6% | 107 |
| Rajya Sabha (2025)* | 245 | 42 | 17.1% | — |
| State/UT assemblies (30) | 4,120 | ~334 | 8.1% | ~1,040 |
| **All legislatures** | **~4,908** | **~450** | **~9.2%** | **~1,186** |

\* Rajya Sabha and state Legislative Councils are **not** covered by the reservation and
are shown for context only.

## Modelling hooks (suggested extensions)

1. **Rotation draw** — implement the delimitation-cycle seat-rotation rule and Monte-Carlo
   the set of reserved constituencies per cycle.
2. **Incumbent-displacement** — flag general seats that flip to reserved and estimate
   displaced-incumbent behaviour (retirement, proxy candidature, seat-swap).
3. **Coalition sensitivity** — re-run the existing coalition game-theory engine on the
   post-reservation candidate pool and compare equilibrium coalitions.

## Data vintage & sources

State-assembly figures are an ADR compilation from candidate affidavits (ECI Form 26);
India's assemblies are elected in staggered years, so the snapshot is inherently
mixed-vintage. ADR's 2026 update reports ~390 women across 4,123 MLA seats nationally.

- 18th Lok Sabha (74/543): ADR / Factly, 2024
- Rajya Sabha (~42, ~17%): PIB / Ministry of WCD, 2025
- State detail: ADR, "Women Representation among Elected Representatives" (ECI affidavits)
- Policy text: PRS Legislative Research; Constitution (106th Amendment) Act, 2023
