"""Swing-model assumptions, tested on the committed TCPD-derived PC-level bloc vote shares
(vote-share-modeling/data/vote_share_continuous.csv, 1999-2019). Each test uses the
REALISED aggregate swing ("oracle swing") so only the swing rule itself is compared."""
import numpy as np
import pandas as pd
import pytest

from _history import YEARS, pc_shares, state_swings, swing_seat_error

PAIRS = list(zip(YEARS[:-1], YEARS[1:]))


def _errors(method, level):
    return [swing_seat_error(a, b, method, level)[0] for a, b in PAIRS]


def test_uniform_swing_is_at_least_as_good_as_proportional():
    """HOLDS, narrowly. Total bloc-seat error over the four transitions
    (1999->2004 ... 2014->2019), state-level oracle swing: uniform 254, proportional 264.
    Uniform is better in 3 of 4 (incl. fit-2014-predict-2019: 58 v 68 seats), proportional
    in 1999->2004 (60 v 70). The gap (4%) is small: the choice is not a major driver."""
    u, p = _errors("uniform", "state"), _errors("proportional", "state")
    assert u == [70, 84, 42, 58] and p == [60, 88, 48, 68]
    assert sum(a < b for a, b in zip(u, p)) == 3
    assert abs(sum(u) - sum(p)) / min(sum(u), sum(p)) < 0.1


def test_state_level_swing_beats_a_single_national_swing():
    """HOLDS for the vote-share models; it is the assumption the coalition scenario
    generators drop (see test_assumptions_seat_engine E6). Uniform swing seat error:
    state-level 254 vs national 342 over four transitions; PC winner accuracy is higher
    with state swing in every transition."""
    assert sum(_errors("uniform", "state")) < 0.8 * sum(_errors("uniform", "national"))
    for a, b in PAIRS:
        assert swing_seat_error(a, b, "uniform", "state")[1] > swing_seat_error(a, b, "uniform", "national")[1]


def test_state_swings_share_a_national_component():
    """State NDA swings are positively correlated through a common national swing: in 3 of
    4 transitions >=77% of states move in the national direction, and the national mean
    accounts for ~33% of state-swing variance (27 states present in all five elections).
    So any Monte Carlo that draws states/constituencies independently understates
    uncertainty -- quantified in test_assumptions_seat_engine E3."""
    S = pd.DataFrame({f"{a}-{b}": state_swings(a, b) for a, b in PAIRS}).dropna()
    nat, idio = S.mean(), S - S.mean()
    same_sign = (np.sign(S) == np.sign(nat)).mean()
    share = nat.var() / (nat.var() + idio.var().mean())
    assert len(S) == 27
    assert (same_sign >= 0.77).sum() == 3
    assert 0.25 < share < 0.45


def test_retroactive_bloc_map_reverses_the_vote_seat_ordering_in_1999():
    """Documented, not judged: the repo assigns parties to CURRENT alliances for every
    year. In 1999 that gives 'INDIA' a 13.6pp higher mean PC vote share than 'NDA' but
    38 fewer seats (210 v 248) -- consistent with parties that were then NDA allies
    (e.g. DMK, AITC) being counted as INDIA. Contemporaneous alliance data are not in the
    repo, so the size of this misclassification is untestable here."""
    m = pc_shares().query("Year == 1999")[["V_NDA", "V_INDIA"]].mean()
    assert m.V_INDIA - m.V_NDA == pytest.approx(0.136, abs=0.002)
