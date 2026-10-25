"""Assumption tests for the women's-reservation / women-candidacy pipeline
(scripts/delimitation-optimization/*). Checked against the TCPD-derived Lok Sabha
candidate file committed under vote-share-modeling/data/ (1999-2019)."""
import re
import sys

import numpy as np
import pandas as pd
import pytest

from _history import ROOT, VSM, winners
from _scriptload import load

DO = ROOT / "scripts" / "delimitation-optimization"
WOMEN_MC = "scripts/delimitation-optimization/06_monte_carlo_with_women.py"
SEX_SCRIPTS = [
    "01_parse_women_candidacy.py",
    "02_fit_electability_model.py",
    "05_lok_sabha_analysis.py",
]


# --------------------------------------------------------------------------------------
# W1  Sex coding: TCPD codes candidate sex as M / F / O, not "FEMALE"   (code bug, fixed)
# --------------------------------------------------------------------------------------
def test_tcpd_sex_codes_are_single_letters():
    sex = pd.read_csv(VSM / "ga_pc_level_all_candidates.csv", usecols=["Sex"])["Sex"]
    assert set(sex.dropna().unique()) <= {"M", "F", "O"}
    assert (sex == "F").sum() == 2601          # 7.5% of 34,466 LS candidate rows
    assert (sex == "FEMALE").sum() == 0


@pytest.mark.parametrize("script", SEX_SCRIPTS)
def test_women_filters_do_not_compare_against_FEMALE_only(script):
    """`df['Sex'] == 'FEMALE'` matches no TCPD row coded 'F'; that is why
    data/processed/lok_sabha_women_candidacy_by_year.csv reports 0 women in every
    Lok Sabha year and women_candidacy_summary.csv reports a 0.1% candidacy rate."""
    src = (DO / script).read_text()
    assert not re.search(r"\[['\"]Sex['\"]\]\s*==\s*['\"]FEMALE['\"]", src), script


def test_is_female_accepts_tcpd_and_long_codes():
    sys.path.insert(0, str(DO))
    from sexcode import is_female

    s = pd.Series(["F", "M", "O", "FEMALE", "female", " f ", None, np.nan])
    assert is_female(s).tolist() == [True, False, False, True, True, True, False, False]


@pytest.mark.xfail(strict=True, reason=(
    "Committed women-candidacy outputs were produced with the 'FEMALE' filter and are "
    "stale: they report 0 women LS candidates 1999-2019, but the committed TCPD file has "
    "2,601 female candidate rows and 297 female winners. Regenerating needs the raw TCPD "
    "files (not in the repo)."))
def test_committed_women_outputs_agree_with_candidate_data():
    by_year = pd.read_csv(ROOT / "data/processed/lok_sabha_women_candidacy_by_year.csv")
    assert by_year["Women_Candidates"].sum() > 0


# --------------------------------------------------------------------------------------
# W2  06_monte_carlo_with_women.py: pre-reservation outcome used the POST seat count
# --------------------------------------------------------------------------------------
def test_pre_reservation_outcome_uses_pre_reservation_seats():
    ns = load(WOMEN_MC, "classify_scenario")
    r = ns["classify_scenario"](nda_pre=275, india_pre=200, women=31, quota=272)
    assert r["Outcome_Pre"] == "NDA Majority"          # 275 >= 272 before any carving
    assert r["NDA_Post"] == 265                         # 275 - int(31/3)
    assert r["Outcome_Post"] == "NDA + Women (Kingmakers)"
    assert r["NDA_Post"] + r["INDIA_Post"] + r["Other_Post"] + r["Women"] == 543


def test_published_six_scenarios_unchanged_by_the_fix():
    """None of the six published scenarios sits in 272..281, so the published
    monte_carlo_women_impact_scenarios.csv is unaffected by the bug."""
    ns = load(WOMEN_MC, "classify_scenario")
    pub = pd.read_csv(ROOT / "data/processed/monte_carlo_women_impact_scenarios.csv")
    for _, row in pub.iterrows():
        r = ns["classify_scenario"](row.NDA_Pre, row.INDIA_Pre, 31, 272)
        assert (r["Outcome_Pre"], r["Outcome_Post"]) == (row.Outcome_Pre, row.Outcome_Post)


# --------------------------------------------------------------------------------------
# W3  Hard-coded post-reservation probabilities
# --------------------------------------------------------------------------------------
def _published():
    return pd.read_csv(ROOT / "data/processed/monte_carlo_summary.csv").iloc[0]


def test_baseline_probabilities_match_the_committed_draws():
    d = pd.read_csv(ROOT / "coalition-game-theory/data/monte_carlo_draws.csv")
    p = _published()
    assert (d.NDA >= 272).mean() == pytest.approx(p.Baseline_NDA_Majority_Prob, abs=1e-9)
    assert ((d.NDA < 272) & (d.INDIA >= 272)).mean() == pytest.approx(p.Baseline_INDIA_Majority_Prob, abs=1e-9)
    assert d.is_hung.mean() == pytest.approx(p.Baseline_Hung_Prob, abs=1e-9)


@pytest.mark.xfail(strict=True, reason=(
    "Post-reservation probabilities are hand-set (5% / 2% / +8%) and are not a "
    "distribution: NDA 0.490 + INDIA 0.103 + hung 0.485 = 1.078 > 1."))
def test_post_reservation_probabilities_sum_to_one():
    p = _published()
    total = p.Post_Women_NDA_Majority_Prob + p.Post_Women_INDIA_Majority_Prob + p.Post_Women_Hung_Prob
    assert total == pytest.approx(1.0, abs=0.005)


@pytest.mark.xfail(strict=True, reason=(
    "Applying the script's OWN equal-carving rule (NDA-10, INDIA-10, women bloc of 31) to "
    "the 20,000 committed draws gives NDA majority 37.8% (published 49.0%), INDIA 4.7% "
    "(published 10.3%) and a women-pivotal outcome in 56.2% of draws (published 8%)."))
def test_hard_coded_shifts_match_carving_applied_to_draws():
    d = pd.read_csv(ROOT / "coalition-game-theory/data/monte_carlo_draws.csv")
    c, w, q = int(31 / 3), 31, 272
    nda, india = d.NDA - c, d.INDIA - c
    p_nda = (nda >= q).mean()
    p_india = ((nda < q) & (india >= q)).mean()
    p_king = ((nda < q) & (india < q) & ((nda + w >= q) | (india + w >= q))).mean()
    assert p_nda == pytest.approx(0.3776, abs=1e-3)       # pin the measured values
    assert p_india == pytest.approx(0.0471, abs=1e-3)
    assert p_king == pytest.approx(0.5618, abs=1e-3)
    p = _published()
    assert abs(p_nda - p.Post_Women_NDA_Majority_Prob) < 0.02
    assert abs(p_king - p.Post_Women_Kingmakers_Prob) < 0.02


# --------------------------------------------------------------------------------------
# W4  "31 women elected" and the 188-seat reservation
# --------------------------------------------------------------------------------------
def test_women_mps_without_reservation_already_exceed_31():
    """Held: data contradicts the 31 estimate even before any reservation."""
    f = winners().query("Sex == 'F'").groupby("Year").size()
    assert f.to_dict() == {1999: 51, 2004: 47, 2009: 58, 2014: 63, 2019: 78}
    assert f.min() > 31


@pytest.mark.xfail(strict=True, reason=(
    "women_elected_est = 31 (a '5.7% win rate' applied to reserved seats). Under Art. "
    "330A every reserved seat can only be won by a woman, so reserved seats alone elect "
    "~181 women; and 78 women already won in 2019 with no reservation."))
def test_women_elected_estimate_is_at_least_reserved_seats():
    ns = load(WOMEN_MC)
    assert ns["women_elected_est"] >= round(543 / 3)


@pytest.mark.xfail(strict=True, reason=(
    "188 is 34.6% of 543; 'one-third, as nearly as may be' is 181 (543/3 = 181). The "
    "repo also uses 180 (ceil(543*0.33), 05_lok_sabha_placement.py) for the same quantity."))
def test_reserved_seat_count_is_one_third():
    ns = load(WOMEN_MC)
    assert ns["women_reserved_ls"] == round(543 / 3)


@pytest.mark.xfail(strict=True, reason=(
    "Women are modelled as a separate 31-seat bloc carved equally from NDA/INDIA/others "
    "and voting cohesively. Women MPs are elected on party tickets: in 2019 the 78 "
    "women winners split 43 NDA / 18 INDIA / 17 Other (by the repo's bloc map), so "
    "they are inside the blocs, not a pivot between them, and not equally drawn."))
def test_women_winners_split_equally_across_blocs():
    f = winners().query("Year == 2019 and Sex == 'F'")["Bloc"].value_counts()
    assert f.to_dict() == {"NDA": 43, "INDIA": 18, "Other": 17}
    assert f.max() - f.min() <= 5


# --------------------------------------------------------------------------------------
# W5  State-level hung-parliament risk (04_coalition_sensitivity.py)
# --------------------------------------------------------------------------------------
@pytest.mark.xfail(strict=True, reason=(
    "04_coalition_sensitivity.py assumes NDA = INDIA = 35% of seats in EVERY state, so "
    "'High' hung risk is guaranteed in all 34 states by construction (0.35 < 0.5). In "
    "the repo's 2024 state results, one bloc held a seat majority in 28 of 36 states."))
def test_state_hung_risk_is_not_fixed_by_construction():
    risk = pd.read_csv(ROOT / "data/processed/hung_parliament_risk_assessment.csv")
    assert (risk.NDA_Seats_Est == risk.INDIA_Seats_Est).all()
    st = pd.read_csv(ROOT / "coalition-game-theory/seat-bias-analysis/data/state_2024_bloc_results.csv")
    majority = ((st.NDA_2024 > st.Seats_2024 / 2) | (st.INDIA_2024 > st.Seats_2024 / 2)).sum()
    assert majority == 28 and len(st) == 36
    assert (risk.Hung_Parliament_Risk == "High").mean() < 0.5


# --------------------------------------------------------------------------------------
# W6  Electability model read-outs (02_fit_electability_model / 02b workbook)
# --------------------------------------------------------------------------------------
@pytest.mark.xfail(strict=True, reason=(
    "Logistic coefficients are read as probability changes ('+1.80 -> incumbents 180% "
    "more likely'). 1.80 is a log-odds coefficient: odds ratio exp(1.80) = 6.05, and the "
    "change in win probability depends on the baseline (e.g. 10% -> 40%)."))
def test_incumbency_readout_matches_odds_ratio():
    src = (DO / "02b_build_electability_workbook.py").read_text()
    assert "180% more likely" not in src
    assert np.exp(1.80) == pytest.approx(6.05, abs=0.01)


@pytest.mark.xfail(strict=True, reason=(
    "Bloc definitions disagree across modules: 02_fit_electability_model puts AITC in NDA "
    "and TMC in INDIA (same party, ECI code AITC), lists BJD in both sets and YSRCP/AAP "
    "inside blocs, while coalition-game-theory/data/party_seats.csv has AITC in INDIA and "
    "YSRCP/AAP unaligned."))
def test_bloc_definitions_are_consistent_across_modules():
    src = (DO / "02_fit_electability_model.py").read_text()
    nda = set(re.findall(r"'([^']+)'", re.search(r"nda_parties = \{(.*?)\}", src).group(1)))
    india = set(re.findall(r"'([^']+)'", re.search(r"india_parties = \{(.*?)\}", src).group(1)))
    seats = pd.read_csv(ROOT / "coalition-game-theory/data/party_seats.csv").set_index("Party")["Bloc"]
    assert not (nda & india)
    for p in nda & set(seats.index):
        assert seats[p] == "NDA", p
