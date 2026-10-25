"""Assumption tests for the 20,000-draw coalition Monte Carlo
(coalition-game-theory/scripts/04_monte_carlo_simulation.py, summarised by
10_build_montecarlo_sheet.py and reused by 06_monte_carlo_with_women.py)."""
import math

import numpy as np
import pandas as pd
import pytest

from _history import ROOT, YEARS, bloc_seats
from _scriptload import load

MC = "coalition-game-theory/scripts/04_monte_carlo_simulation.py"
DRAWS = ROOT / "coalition-game-theory" / "data" / "monte_carlo_draws.csv"


def _gen(ranges=None):
    ns = load(MC, "generate_one_draw")
    if ranges is not None:
        ns["party_ranges"] = ranges
    ns["players"] = list(ns["party_ranges"])
    ns["n_players"] = len(ns["players"])
    return ns


def _probs(ranges, n=5000, seed=42):
    ns = _gen(ranges)
    rng = np.random.default_rng(seed)
    d = pd.DataFrame([ns["generate_one_draw"](rng) for _ in range(n)])
    nda = (d.NDA >= 272).mean()
    india = ((d.NDA < 272) & (d.INDIA >= 272)).mean()
    return nda, india, 1 - nda - india


@pytest.fixture(scope="module")
def draws():
    return pd.read_csv(DRAWS)


@pytest.fixture(scope="module")
def history():
    """NDA / INDIA seats 1999-2019 from the TCPD winners file (repo bloc map), plus 2024
    from coalition-game-theory/seat-bias-analysis/data/state_2024_bloc_results.csv."""
    nda = {y: bloc_seats(y)["NDA"] for y in YEARS}
    india = {y: bloc_seats(y)["INDIA"] for y in YEARS}
    st = pd.read_csv(ROOT / "coalition-game-theory/seat-bias-analysis/data/state_2024_bloc_results.csv")
    nda[2024], india[2024] = int(st.NDA_2024.sum()), int(st.INDIA_2024.sum())
    return nda, india


# --- M1 seed handling / reproducibility ---------------------------------------------------
def test_committed_draws_reproduce_exactly_from_seed_42(draws):
    ns = _gen()
    rng = np.random.default_rng(42)
    regen = pd.DataFrame([ns["generate_one_draw"](rng) for _ in range(len(draws))])
    assert (regen.values == draws.drop(columns="is_hung").values).all()
    assert (draws.drop(columns="is_hung").sum(axis=1) == 543).all()


# --- M2 number of draws -----------------------------------------------------------------
def test_20000_draws_give_sub_half_point_standard_error(draws):
    p = draws.is_hung.mean()                       # 0.379
    se = math.sqrt(p * (1 - p) / len(draws))       # 0.0034
    assert len(draws) == 20000 and se < 0.005


# --- M3 majority threshold --------------------------------------------------------------
def test_quota_is_simple_majority_of_543():
    assert load(MC)["QUOTA"] == 543 // 2 + 1 == 272


# --- M4 independence between NDA and INDIA ----------------------------------------------
def test_sum_to_543_rescaling_makes_nda_and_india_strongly_anticorrelated(draws, history):
    """NDA and INDIA are drawn independently, but the rescale-to-543 step induces
    corr = -0.94, close to the historical -0.98 (1999-2024, n=6). Assumption holds."""
    nda, india = history
    hist_corr = np.corrcoef(list(nda.values()), list(india.values()))[0, 1]
    mc_corr = draws[["NDA", "INDIA"]].corr().iloc[0, 1]
    assert mc_corr < -0.9 and hist_corr < -0.9


# --- M5 'historically plausible' ranges ---------------------------------------------------
@pytest.mark.xfail(strict=True, reason=(
    "Ranges NDA 220-360 / INDIA 180-320 are said to reflect 2014/2019/2024. With the repo's "
    "own bloc map, INDIA won 105 (2014) and 111 (2019) and NDA 170 (2004) and 160 (2009): "
    "the INDIA range excludes 2 of the 3 elections it cites and both ranges miss 2 of 6 "
    "elections 1999-2024."))
def test_uniform_ranges_contain_every_historical_outcome(history):
    nda, india = history
    rng = load(MC)["party_ranges"]
    assert nda == {1999: 248, 2004: 170, 2009: 160, 2014: 319, 2019: 341, 2024: 291}
    assert india == {1999: 210, 2004: 287, 2009: 302, 2014: 105, 2019: 111, 2024: 231}
    assert all(rng["NDA"][0] <= v <= rng["NDA"][1] for v in nda.values())
    assert all(rng["INDIA"][0] <= v <= rng["INDIA"][1] for v in india.values())


@pytest.mark.xfail(strict=True, reason=(
    "Calibration backtest: the Monte Carlo's central 90% intervals (NDA 226-319, INDIA "
    "189-281) contain the realised seats in only 3/6 (NDA) and 2/6 (INDIA) Lok Sabha "
    "elections 1999-2024. The README already says the output is not a calibrated "
    "probability; this quantifies it."))
def test_90pct_intervals_cover_history_at_nominal_rate(draws, history):
    nda, india = history
    lo_n, hi_n = np.percentile(draws.NDA, [5, 95])
    lo_i, hi_i = np.percentile(draws.INDIA, [5, 95])
    cov_n = np.mean([lo_n <= v <= hi_n for v in nda.values()])
    cov_i = np.mean([lo_i <= v <= hi_i for v in india.values()])
    assert (round(cov_n, 2), round(cov_i, 2)) == (0.5, 0.33)
    assert cov_n >= 0.8 and cov_i >= 0.8


# --- M6 sensitivity of the headline probabilities to the hand-set ranges -----------------
def test_headline_probabilities_are_driven_by_range_endpoints():
    """One-at-a-time: widening only the lower bound to the 1999-2019 historical minimum
    moves NDA-majority from 51.6% to 36.5% (NDA floor 160) or to 68.2% (INDIA floor 105);
    hung-parliament moves between 25% and 38%. Recorded as a regular test because it is a
    property of the model, not a defect -- but the headline is a function of the ranges."""
    base = dict(load(MC)["party_ranges"])
    p0 = _probs(base)
    nda_lo = _probs({**base, "NDA": (160, 360)})
    ind_lo = _probs({**base, "INDIA": (105, 320)})
    joint = _probs({**base, "NDA": (160, 360), "INDIA": (105, 320)})
    assert p0[0] == pytest.approx(0.516, abs=0.015) and p0[2] == pytest.approx(0.379, abs=0.015)
    assert nda_lo[0] < p0[0] - 0.1             # ~0.365
    assert ind_lo[0] > p0[0] + 0.1             # ~0.682
    assert joint[2] < p0[2] - 0.08             # hung ~0.27
