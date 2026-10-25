"""Dirichlet estimators and the 'swing matrix' predictor in
vote-share-modeling/scripts/12_dirichlet_swing_model.py, on simulated data."""
import numpy as np
import pandas as pd
import pytest
from scipy.special import digamma

from _scriptload import load

M = load("vote-share-modeling/scripts/12_dirichlet_swing_model.py",
         "_invert_digamma", "minka_fixed_point_dirichlet", "method_of_moments_dirichlet",
         "fit_swing_matrix", "predict_with_swing_matrix")
BLOCS = M["BLOCS"]


@pytest.mark.parametrize("x", [0.05, 0.5, 1.0, 3.0, 25.0, 400.0])
def test_invert_digamma_roundtrip(x):
    assert M["_invert_digamma"](digamma(x)) == pytest.approx(x, rel=1e-5)


ALPHA = np.array([8.0, 5.0, 2.0])
SAMPLE = np.random.default_rng(0).dirichlet(ALPHA, size=20000)


def test_method_of_moments_recovers_known_alpha():
    assert M["method_of_moments_dirichlet"](SAMPLE) == pytest.approx(ALPHA, rel=0.05)


def test_minka_mle_recovers_known_alpha():
    # Well-behaved, non-degenerate Dirichlet data: the MLE must converge near
    # the true parameters, not run to the [1e-3, alpha_cap] clip bounds.
    assert M["minka_fixed_point_dirichlet"](SAMPLE) == pytest.approx(ALPHA, rel=0.05)


def test_mom_degenerate_variance_fallback():
    X = np.tile([0.5, 0.3, 0.2], (10, 1))
    assert M["method_of_moments_dirichlet"](X) == pytest.approx([50, 30, 20])


def _frame(rows):
    return pd.DataFrame(rows, columns=["State_Name", "PC_No"] + BLOCS)


def test_fit_swing_matrix_uses_ones_for_small_origin_groups():
    rng = np.random.default_rng(1)
    prev, cur = [], []
    for i in range(40):  # all NDA-plurality seats
        prev.append(["S", i, 0.6, 0.3, 0.1])
        cur.append(["S", i, *rng.dirichlet([6, 3, 1])])
    T = M["fit_swing_matrix"](_frame(prev), _frame(cur))
    assert T.shape == (3, 3)
    assert T[1] == pytest.approx([1, 1, 1]) and T[2] == pytest.approx([1, 1, 1])
    mean0 = T[0] / T[0].sum()
    assert mean0 == pytest.approx([0.6, 0.3, 0.1], abs=0.05)


@pytest.mark.xfail(strict=True, reason=(
    "Known model mismatch (not fixed): the docstring describes a voter-transition "
    "matrix applied to prior shares, but predict_with_swing_matrix gives every seat "
    "in an origin bloc the same Dirichlet mean, ignoring its prior shares beyond argmax."))
def test_prediction_depends_on_prior_shares_not_only_plurality_bloc():
    T = np.array([[8.0, 1.0, 1.0], [1.0, 8.0, 1.0], [1.0, 1.0, 8.0]])
    prior = pd.DataFrame([[0.90, 0.05, 0.05], [0.40, 0.39, 0.21]], columns=BLOCS)
    p = M["predict_with_swing_matrix"](prior, T)
    # Transition semantics: pred = prior @ row-normalised T, so a 90% NDA seat and a
    # 40/39 marginal seat cannot get identical forecasts.
    assert not np.allclose(p[0], p[1])
