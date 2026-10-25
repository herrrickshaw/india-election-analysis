"""Assumption tests for the vote-share -> seat engine shared by
coalition-game-theory/seat-bias-analysis/scripts/01 and 05 and the from-working-files
expanded-simulation / state-wise / reverse-monte-carlo scripts:
per-seat Dirichlet(conc * state_mean) draw, winner = argmax over NDA/INDIA/Other (FPTP),
every seat drawn independently, state means = 2024 SEAT shares."""
import numpy as np
import pandas as pd
import pytest

from _history import (BLOCS, ROOT, YEARS, implied_dirichlet_concentration, paired, pc_shares,
                      seats_from_shares, simulate_seats, state_mean_shares, state_swings, winners)
from _scriptload import load

SWEEP = "coalition-game-theory/seat-bias-analysis/scripts/01_seat_bias_sweep_534_to_1000.py"
PAIRS = list(zip(YEARS[:-1], YEARS[1:]))


def _seat_share_means_2024():
    """Exactly the scripts' construction: 2024 seat shares, clipped at 0.02, renormalised."""
    st = pd.read_csv(ROOT / "coalition-game-theory/seat-bias-analysis/data/state_2024_bloc_results.csv")
    st = st.drop_duplicates("State")
    sh = pd.DataFrame({"n": st.NDA_2024, "i": st.INDIA_2024, "o": st.Other_2024}).div(st.Seats_2024, axis=0)
    sh = sh.clip(lower=0.02)
    return sh.div(sh.sum(axis=1), axis=0).values, st.Seats_2024.values.astype(float)


def _realised(year):
    return seats_from_shares(pc_shares().query("Year == @year").set_index(["State_Name", "PC_No"])[BLOCS])


# --- E0 the helper is a faithful copy of the script's engine ------------------------------
def test_helper_reproduces_script_engine_bit_for_bit():
    ns = load(SWEEP, "simulate_election")
    means, seats = _seat_share_means_2024()
    ns.update(state_names=np.arange(len(seats)), state_seat_counts=seats, mean_shares=means)
    r1, r2 = np.random.default_rng(11), np.random.default_rng(11)
    for _ in range(20):
        script_counts, _ = ns["simulate_election"](r1, 543)
        mine = simulate_seats(r2, means, seats, 1, n_seats=543)[0]
        assert (script_counts == mine).all()


# --- E1 Dirichlet concentration 18 ---------------------------------------------------------
def test_concentration_18_matches_within_state_dispersion():
    """HOLDS. Method-of-moments on V_NDA within each state-year (96 state-years with >=5
    PCs) gives median concentration 18.7 (IQR 6.4-54). The repo's own assumption audit
    (seat-bias 09_build_assumption_audit.py, A2) says the 'correct' value is ~5, but that
    figure came from the NATIONAL spread, which also contains between-state variance that
    the engine already models through per-state means. 18 is the right order."""
    c = implied_dirichlet_concentration()
    assert len(c) == 96
    assert 14 <= np.median(c) <= 24
    assert np.percentile(c, 25) > 5


# --- E2 seat share used as the vote-share mean ---------------------------------------------
@pytest.mark.xfail(strict=True, reason=(
    "Feeding SEAT shares in as Dirichlet vote-share means applies FPTP's winner's bonus "
    "twice. Backtest on 2019 (same engine, conc 18): seat-share means give NDA 367 seats, "
    "vote-share means give 321, realised (3-bloc FPTP) 310 -- a +57-seat bias. The repo "
    "documents the direction (A1) but the magnitude is large."))
def test_seat_share_means_do_not_bias_seat_projection():
    y = 2019
    vm, n = state_mean_shares(y)
    w = winners().query("Year == @y")
    sm = (w.groupby("State_Name")["Bloc"].value_counts(normalize=True).unstack()
          .reindex(columns=["NDA", "INDIA", "Other"]).fillna(0).clip(lower=0.02))
    sm = sm.div(sm.sum(axis=1), axis=0).loc[vm.index]
    rng = np.random.default_rng(1)
    by_votes = simulate_seats(rng, vm.values, n.values, 400)[:, 0].mean()
    by_seats = simulate_seats(rng, sm.values, n.values, 400)[:, 0].mean()
    real = _realised(y)["V_NDA"]
    assert real == 310 and abs(by_votes - real) < 20 and by_seats - real > 40
    assert abs(by_seats - real) < 20


# --- E3 independence of constituencies (no common swing) -----------------------------------
def _backtest(correlated):
    """Persistence forecast y0 -> y1 using y0 state vote means. Correlated variant adds a
    national NDA-vs-INDIA shock and per-state shocks whose SDs are estimated
    leave-one-transition-out from the other three transitions."""
    S = pd.DataFrame({f"{a}-{b}": state_swings(a, b) for a, b in PAIRS}).dropna()
    nat, idio = S.mean(), S - S.mean()
    hits, widths = [], []
    for a, b in PAIRS:
        v0, _ = paired(a, b)
        means = v0.groupby(level="State_Name").mean()
        seats = v0.groupby(level="State_Name").size()
        others = [c for c in S.columns if c != f"{a}-{b}"]
        nsd = float(np.sqrt((nat[others] ** 2).mean())) if correlated else 0.0
        ssd = float(idio[others].std().mean()) if correlated else 0.0
        sims = simulate_seats(np.random.default_rng(0), means.values, seats.values, 1000,
                              national_sd=nsd, state_sd=ssd)[:, 0]
        lo, hi = np.percentile(sims, [5, 95])
        hits.append(lo <= _realised(b)["V_NDA"] <= hi)
        widths.append(hi - lo)
    return hits, float(np.mean(widths))


@pytest.mark.xfail(strict=True, reason=(
    "Every seat is drawn independently given fixed state means, so seat totals only carry "
    "binomial-sized noise (90% interval ~29 seats wide). Backtest 1999->2019: the interval "
    "contains the next election's NDA seats in 1 of 4 transitions."))
def test_independent_engine_intervals_are_calibrated():
    hits, width = _backtest(correlated=False)
    assert sum(hits) == 1 and width < 40
    assert sum(hits) >= 3


def test_correlated_swing_restores_coverage_and_widens_interval():
    """Measured: adding a national shock (sd 5.8-7.6pp) + state shocks (sd 8.6-10.5pp), estimated
    out-of-sample, covers 3 of 4 transitions with a 90% interval ~212 seats wide (7.4x)."""
    hits_i, width_i = _backtest(correlated=False)
    hits_c, width_c = _backtest(correlated=True)
    assert sum(hits_c) >= 3
    assert width_c > 5 * width_i


# --- E4 the 'more seats entrench the leader' headline --------------------------------------
def _p_majority(n_seats, national_sd):
    means, seats = _seat_share_means_2024()
    x = simulate_seats(np.random.default_rng(11), means, seats, 1500,
                       n_seats=n_seats, national_sd=national_sd)
    return float((x[:, 0] >= n_seats // 2 + 1).mean())


def test_engine_reproduces_published_entrenchment_numbers():
    """README: P(NDA majority) 96.9% at 534 seats -> 99.5% at 1,000."""
    assert _p_majority(534, 0.0) == pytest.approx(0.969, abs=0.002)
    assert _p_majority(1000, 0.0) == pytest.approx(0.995, abs=0.002)


@pytest.mark.xfail(strict=True, reason=(
    "The 96.9-99.5% level is an artefact of independent seats. With one national swing "
    "(sd 6.5pp, the 1999-2019 NDA swing scale) P(NDA majority) is ~70% at 534 and ~72% at "
    "1,000 seats: the rise with house size shrinks to within simulation noise and the "
    "level falls by ~27pp."))
def test_entrenchment_level_robust_to_correlated_swing():
    p534, p1000 = _p_majority(534, 0.065), _p_majority(1000, 0.065)
    assert 0.6 < p534 < 0.8 and 0.6 < p1000 < 0.8
    assert p534 > 0.9


# --- E5 three-bloc FPTP ---------------------------------------------------------------------
def test_three_bloc_argmax_recovers_real_winning_bloc():
    """HOLDS (approximately): collapsing every PC to NDA/INDIA/Other and taking the argmax
    picks the real winner's bloc in 85.7% of 2,704 PC-years (78-91% by year)."""
    v = pc_shares().merge(winners()[["State_Name", "Year", "PC_No", "Bloc"]],
                          on=["State_Name", "Year", "PC_No"])
    hit = v[BLOCS].idxmax(axis=1).str[2:] == v["Bloc"]
    assert hit.mean() == pytest.approx(0.857, abs=0.002)
    assert hit.groupby(v.Year).mean().min() > 0.75


# --- E6 uniform national NDA:INDIA split in scenario construction --------------------------
@pytest.mark.xfail(strict=True, reason=(
    "build_scenario_shares() gives every state the SAME NDA:INDIA split (only 'Other' keeps "
    "its state value). Replaying 1999-2019 with the realised national split, NDA seat error "
    "averages ~62 seats vs ~19 when each state keeps its own lean -- the scenarios discard "
    "most of the geography that drives FPTP outcomes."))
def test_uniform_national_split_preserves_seat_accuracy():
    err_u, err_s = [], []
    for y in YEARS:
        vm, n = state_mean_shares(y)
        two = vm.V_NDA + vm.V_INDIA
        f = (vm.V_NDA * n).sum() / (two * n).sum()
        u = vm.copy()
        u["V_NDA"], u["V_INDIA"] = f * two, (1 - f) * two
        rng = np.random.default_rng(0)
        real = _realised(y)["V_NDA"]
        err_s.append(abs(simulate_seats(rng, vm.values, n.values, 300)[:, 0].mean() - real))
        err_u.append(abs(simulate_seats(rng, u.values, n.values, 300)[:, 0].mean() - real))
    assert np.mean(err_u) > 2 * np.mean(err_s)       # measured ~62 vs ~19
    assert np.mean(err_u) <= 1.25 * np.mean(err_s)
