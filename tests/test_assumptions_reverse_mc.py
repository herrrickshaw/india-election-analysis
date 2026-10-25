"""Reverse Monte Carlo (from-working-files/.../reverse-monte-carlo/): the historical
Congress/BJP table that feeds the 'reversal' and the 2029-2039 trend projections,
cross-checked against the TCPD winners/candidates files for 1999-2019."""
import numpy as np
import pandas as pd
import pytest

from _history import ROOT, VSM, winners

RMC = ROOT / "from-working-files/india-election-analysis-clean/coalition-game-theory/reverse-monte-carlo/data"


@pytest.fixture(scope="module")
def table():
    return pd.read_csv(RMC / "historical_reversals.csv").set_index("year")


@pytest.fixture(scope="module")
def tcpd():
    w = winners()
    seats = w[w.Party.isin(["BJP", "INC"])].pivot_table(index="Year", columns="Party", values="PC_No", aggfunc="size")
    a = pd.read_csv(VSM / "ga_pc_level_all_candidates.csv", usecols=["Year", "Party", "Total_Votes"])
    a = a[a.Party != "NOTA"]
    vote = a.groupby(["Year", "Party"]).Total_Votes.sum().div(a.groupby("Year").Total_Votes.sum(), level=0) * 100
    return seats, vote.unstack()[["BJP", "INC"]]


def _check(table, tcpd, year):
    seats, vote = tcpd
    r = table.loc[year]
    assert abs(r.bjp_seats - seats.loc[year, "BJP"]) <= 3, ("BJP seats", r.bjp_seats, seats.loc[year, "BJP"])
    assert abs(r.con_seats - seats.loc[year, "INC"]) <= 3, ("INC seats", r.con_seats, seats.loc[year, "INC"])
    assert abs(r.bjp_vote - vote.loc[year, "BJP"]) <= 1.0, ("BJP vote", r.bjp_vote, vote.loc[year, "BJP"])
    assert abs(r.con_vote - vote.loc[year, "INC"]) <= 1.0, ("INC vote", r.con_vote, vote.loc[year, "INC"])


@pytest.mark.parametrize("year", [2009, 2014, 2019])
def test_historical_rows_match_tcpd(table, tcpd, year):
    """Tolerance: 3 seats (TCPD's 1999/2004 extract lacks 5 PCs) and 1pp of vote."""
    _check(table, tcpd, year)


@pytest.mark.xfail(strict=True, reason=(
    "1999 row has BJP 303 seats / 36.5% (2019-like values). TCPD: BJP 180 seats, 23.7%. "
    "The row's actual_outcome 'BJP' (single-party majority) should be HUNG."))
def test_1999_row_matches_tcpd(table, tcpd):
    _check(table, tcpd, 1999)


@pytest.mark.xfail(strict=True, reason=(
    "2004 row has Congress 222 seats (roughly the UPA-wide figure). TCPD: INC 142 "
    "(official 145)."))
def test_2004_row_matches_tcpd(table, tcpd):
    _check(table, tcpd, 2004)


def test_projection_A_is_the_linear_trend_of_the_table_including_the_1999_error(table):
    """The published scenario A (NDA 36.2 / 37.9 / 39.6% in 2029/34/39) is reproduced
    exactly by a 1999-2024 OLS line through the table -- so it inherits the 1999 error.
    With 1999 BJP = 23.7% (TCPD) the same method gives 40.5 / 44.0 / 47.5%."""
    proj = pd.read_csv(RMC / "future_projections_v2.csv").query("scenario == 'A_Actual' and noise_sd_pp == 0")
    r = table.loc[1999:]
    years = [2029, 2034, 2039]
    fit = np.round(np.polyval(np.polyfit(r.index, r.bjp_vote, 1), years), 1)
    assert list(fit) == list(proj.bloc1_vote)
    fixed = r.bjp_vote.copy()
    fixed.loc[1999] = 23.7
    assert list(np.round(np.polyval(np.polyfit(r.index, fixed, 1), years), 1)) == [40.5, 44.0, 47.5]


def test_projection_probabilities_are_set_by_the_unestimated_noise_term():
    """Scenario C (NDA 35% v INDIA 33%): P(NDA majority) is 0.957 with no noise, 0.617
    at 3pp and 0.579 at 6pp. The noise SD is a free parameter; the 1999-2019 national NDA
    swing RMS in the repo data is ~6.5pp, i.e. the 6pp rows are the data-consistent ones."""
    c = pd.read_csv(RMC / "future_projections_v2.csv").query("scenario == 'C_Convergence' and year == 2029")
    p = c.set_index("noise_sd_pp").p_bloc1_majority
    assert p[0.0] - p[6.0] > 0.35
