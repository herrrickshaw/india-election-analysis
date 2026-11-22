"""Seat-bias sweep (01), counterfactual scenario generator (05) and the two election-data
constant tables (01, 02); plus the DSMM pipeline body of vote-share-modeling/12.

The seat-bias scripts hard-code an absolute /home/claude input path and a large simulation grid;
the tests redirect the path into tmp_path and shrink the grid with text substitutions."""
import pickle

import numpy as np
import pandas as pd
import pytest

from _runscript import run_script

SB = "coalition-game-theory/seat-bias-analysis/scripts"
ED = "election-data-analysis/scripts"


@pytest.fixture
def cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _state_inputs(cwd):
    pd.DataFrame(
        [("A", 30, 20, 8, 2), ("A", 30, 20, 8, 2),  # duplicate row must be dropped
         ("B", 10, 2, 6, 2), ("C", 5, 5, 0, 0)],
        columns=["State", "Seats_2024", "NDA_2024", "INDIA_2024", "Other_2024"]).to_csv(
        cwd / "state_2024_bloc_results.csv", index=False)
    pd.DataFrame([("A", 1000), ("B", 3000)], columns=["State", "Census2011_Pop"]).to_csv(
        cwd / "state_data_raw.csv", index=False)  # C is missing: filled with the median


# ---------------------------------------------------------------- 01 seat-bias sweep
SWEEP_SUBS = lambda cwd: [  # noqa: E731
    ("/home/claude/coalition_model/state_2024_bloc_results.csv", str(cwd / "state_2024_bloc_results.csv")),
    ("/home/claude/election_analysis/state_data_raw.csv", str(cwd / "state_data_raw.csv")),
    ("N_SIMULATIONS = 1500", "N_SIMULATIONS = 40"),
    ("SEAT_TOTALS = sorted(set(list(range(534, 1001, 10)) + [850, 1000]))", "SEAT_TOTALS = [543, 600, 1000]"),
]


@pytest.fixture
def sweep(cwd, capsys):
    _state_inputs(cwd)
    ns = run_script(f"{SB}/01_seat_bias_sweep_534_to_1000.py", cwd / "_runner.py", subs=SWEEP_SUBS(cwd))
    return ns, pd.read_csv(cwd / "seat_bias_sweep_v2_to1000.csv"), capsys.readouterr().out


def test_sweep_state_share_preparation(sweep):
    ns, _, _ = sweep
    df = ns["df"]
    assert list(df.State) == ["A", "B", "C"]  # duplicate dropped
    shares = df[["NDA_share_2024", "INDIA_share_2024", "Other_share_2024"]]
    np.testing.assert_allclose(shares.sum(axis=1), 1.0)
    c = df[df.State == "C"].iloc[0]
    # zero INDIA/Other shares are floored at 0.02 before renormalising: 1 / 1.04
    assert c.NDA_share_2024 == pytest.approx(1 / 1.04) and c.INDIA_share_2024 == pytest.approx(0.02 / 1.04)
    assert df.loc[df.State == "C", "Census2011_Pop"].iloc[0] == 2000  # median(1000, 3000)
    a = df[df.State == "A"].iloc[0]
    assert a.NDA_share_2024 == pytest.approx(20 / 30)


def test_sweep_rows_follow_quota_and_share_identities(sweep):
    _, r, out = sweep
    assert r.total_seats.tolist() == [543, 600, 1000]
    assert (r.quota == r.total_seats // 2 + 1).all()
    for side in ("seat", "vote"):
        np.testing.assert_allclose(r[[f"nda_{side}_share", f"india_{side}_share", f"other_{side}_share"]].sum(axis=1), 1.0)
    np.testing.assert_allclose(r.seat_bonus_leader, r.nda_seat_share - r.nda_vote_share)
    gal = np.sqrt(0.5 * ((r.nda_seat_share - r.nda_vote_share) ** 2 + (r.india_seat_share - r.india_vote_share) ** 2
                         + (r.other_seat_share - r.other_vote_share) ** 2)) * 100
    np.testing.assert_allclose(r.gallagher_index, gal)
    assert r.pct_nda_majority.between(0, 1).all() and (r.bonus_std_across_elections >= 0).all()
    assert "Testing 3 seat-totals: [543, 600, 1000]" in out
    assert "Saved seat_bias_sweep_v2_to1000.csv" in out
    assert "Correlation(seats, Gallagher index):" in out


def test_sweep_is_deterministic(cwd, sweep):
    _, first, _ = sweep
    run_script(f"{SB}/01_seat_bias_sweep_534_to_1000.py", cwd / "_runner.py", subs=SWEEP_SUBS(cwd))
    pd.testing.assert_frame_equal(first, pd.read_csv(cwd / "seat_bias_sweep_v2_to1000.csv"))


def test_simulate_election_seat_counts_and_vote_shares(sweep):
    ns, _, _ = sweep
    sc, vs = ns["simulate_election"](np.random.default_rng(5), 200)
    assert sc.sum() == 200 and vs.sum() == pytest.approx(1.0) and (vs > 0).all()


def test_simulate_election_decisive_state_always_elects_its_bloc(sweep):
    ns, _, _ = sweep
    # a state whose mean shares are overwhelmingly NDA must elect NDA in (almost) every seat
    ns["state_names"] = np.array(["only"])
    ns["state_seat_counts"] = np.array([10.0])
    ns["mean_shares"] = np.array([[0.96, 0.02, 0.02]])
    sc, _ = ns["simulate_election"](np.random.default_rng(1), 300)
    assert sc[0] >= 295


# ---------------------------------------------------------------- 05 counterfactual generator
CF_SUBS = lambda cwd: [  # noqa: E731
    ("/home/claude/election_analysis/state_data_raw.csv", str(cwd / "state_data_raw.csv")),
    ("N_SIMULATIONS = 1500", "N_SIMULATIONS = 30"),
    ("SEAT_TOTALS = sorted(set(list(range(534, 1001, 20)) + [543, 850, 1000]))", "SEAT_TOTALS = [543, 600]"),
]


@pytest.fixture
def cf(cwd, capsys):
    _state_inputs(cwd)
    ns = run_script(f"{SB}/05_counterfactual_scenario_generator.py", cwd / "_runner.py", subs=CF_SUBS(cwd))
    return ns, pd.read_csv(cwd / "gan_scenario_results.csv"), capsys.readouterr().out


def test_counterfactual_grid_and_quota(cf):
    _, r, out = cf
    assert len(r) == 5 * 2
    assert r.groupby("scenario").total_seats.apply(list).to_dict() == {
        s: [543, 600] for s in ("S0_NDA_Real", "S1_INDIA_Mirror", "S2_Tossup", "S3_INDIA_Small", "S4_NDA_Small")}
    assert (r.quota == r.total_seats // 2 + 1).all()
    assert r.groupby("scenario").tracked_bloc.first().to_dict() == {
        "S0_NDA_Real": "NDA", "S1_INDIA_Mirror": "INDIA", "S2_Tossup": "NDA",
        "S3_INDIA_Small": "INDIA", "S4_NDA_Small": "NDA"}
    assert "S4_NDA_Small: done" in out and "P(majority)" in out


def test_build_scenario_shares_mirror_symmetry_and_other_preserved(cf):
    ns, _, _ = cf
    base = ns["df"]
    b = ns["build_scenario_shares"]
    nda_n, ind_n, oth_n = b("NDA", 11.1, base)
    nda_i, ind_i, oth_i = b("INDIA", 11.1, base)
    np.testing.assert_allclose(nda_n, ind_i)  # exact mirror by construction
    np.testing.assert_allclose(ind_n, nda_i)
    np.testing.assert_allclose(oth_n, oth_i)
    np.testing.assert_allclose(oth_n, base["Other_share_2024"].values)
    np.testing.assert_allclose(nda_n + ind_n + oth_n, 1.0)
    # NDA leads the two-bloc split by exactly 11.1 points of the two-bloc total
    two = 1 - oth_n
    np.testing.assert_allclose((nda_n - ind_n) / two, 0.111)


def test_build_scenario_shares_tossup_and_unknown_leader_are_even(cf):
    ns, _, _ = cf
    for leader in ("tossup", "nobody"):
        nda, ind, _ = ns["build_scenario_shares"](leader, 50.0, ns["df"])  # margin is ignored
        np.testing.assert_allclose(nda, ind)


def test_counterfactual_simulate_election_uses_given_mean_shares(cf):
    ns, _, _ = cf
    ns["state_seat_counts"] = np.array([1.0])
    sc, vs = ns["simulate_election"](np.random.default_rng(2), 100, np.array([[0.02, 0.96, 0.02]]))
    assert sc.argmax() == 1 and sc.sum() == 100 and vs.sum() == pytest.approx(1.0)


# ---------------------------------------------------------------- election-data constants
def test_state_table_is_complete_and_consistent(cwd, capsys):
    run_script(f"{ED}/01_build_state_data.py", cwd / "_runner.py")
    d = pd.read_csv("state_data_raw.csv")
    assert len(d) == 36 and d.State.is_unique
    assert d.LS_Seats_2024.sum() == 543
    assert d.Electors_2024.notna().all()  # every state has an elector count
    assert d.Assembly_Seats.isna().sum() == 5  # the five UTs without a legislature
    assert d.loc[d.State == "Uttar Pradesh", "LS_Seats_2024"].iloc[0] == 80
    assert d.loc[d.State == "Delhi", "Assembly_Seats"].iloc[0] == 70
    out = capsys.readouterr().out
    assert "Total LS seats: 543" in out and "Total 2024 electors: 973634811" in out


def test_national_trend_average_electors_per_seat(cwd):
    run_script(f"{ED}/02_build_national_trend.py", cwd / "_runner.py")
    t = pd.read_csv("national_trend.csv").set_index("Year")
    assert t.index.tolist() == [2014, 2019, 2024]
    assert t.loc[2019, "LS_Seats"] == 542  # Vellore poll countermanded in 2019
    np.testing.assert_allclose(t.Avg_Electors_per_Seat, t.Total_Electors / t.LS_Seats)
    assert t.loc[2024, "Avg_Electors_per_Seat"] == pytest.approx(968_800_000 / 543)


# ---------------------------------------------------------------- 12 DSMM pipeline body
VSM = "vote-share-modeling/scripts/12_dirichlet_swing_model.py"
BL = ["V_NDA", "V_INDIA", "V_Other"]


def _pcs(cwd, per_year):
    rows = []
    for year, fn in per_year.items():
        for i in range(10):
            rows.append(("S", i, year, *fn(i), 1.0))
    pd.DataFrame(rows, columns=["State_Name", "PC_No", "Year"] + BL + ["V_sum_check"]).to_csv(
        cwd / "vote_share_continuous.csv", index=False)


def _alt(i):
    return [0.5, 0.4, 0.1] if i % 2 == 0 else [0.3, 0.6, 0.1]


def test_dsmm_pipeline_analytic_world(cwd, capsys):
    const = lambda i: [0.4, 0.5, 0.1]  # noqa: E731
    _pcs(cwd, {1999: lambda i: [0.6, 0.3, 0.1], 2004: _alt, 2009: const, 2014: const, 2019: const})
    run_script(VSM, cwd / "_runner.py")
    with open("dsmm_results.pkl", "rb") as f:
        r = pickle.load(f)
    # 1999 -> 2004: all 10 PCs are NDA-plurality; current shares alternate (0.5,0.4,0.1)/(0.3,0.6,0.1)
    # so mean (0.4,0.5,0.1), variance (0.01, 0.01, 0) and alpha0 = median(23, 24) = 23.5
    T = r["swing_matrix_train"]
    assert T[0] == pytest.approx([9.4, 11.75, 2.35])
    assert T[1] == pytest.approx([1, 1, 1]) and T[2] == pytest.approx([1, 1, 1])  # <5 origin seats
    assert r["dirichlet_means_train"][0] == pytest.approx([0.4, 0.5, 0.1])
    # validation 2004 -> 2009: naive error is 0.2/3 per PC; the DSMM error is 0 for NDA-origin
    # PCs and mean|1/3 - (.4,.5,.1)| = 0.4667/3 for the INDIA-origin ones
    assert r["val_mae_naive"] == pytest.approx(0.2 / 3)
    assert r["val_mae_dsmm"] == pytest.approx((0 + 0.4666667 / 3) / 2, abs=1e-6)
    # a world with no change after 2009 is predicted exactly, by both models
    for k in ("test1_mae", "test1_naive_mae", "test2_mae", "test2_naive_mae",
              "combined_test_mae", "combined_test_naive"):
        assert r[k] == pytest.approx(0, abs=1e-5)
    out = capsys.readouterr().out
    assert "COMBINED TEST (2014+2019, pooled)" in out and "Saved dsmm_results.pkl" in out


def test_dsmm_combined_mae_is_pc_weighted(cwd):
    const = lambda i: [0.4, 0.5, 0.1]  # noqa: E731
    shifted = lambda i: [0.3, 0.6, 0.1]  # noqa: E731
    # 2014 has 10 PCs, 2019 only the first 4: the pooled MAE weights by merged PC count
    rows = []
    for year in (1999, 2004, 2009, 2014, 2019):
        n = 4 if year == 2019 else 10
        for i in range(n):
            rows.append(("S", i, year, *(shifted(i) if year == 2019 else const(i)), 1.0))
    pd.DataFrame(rows, columns=["State_Name", "PC_No", "Year"] + BL + ["V_sum_check"]).to_csv(
        cwd / "vote_share_continuous.csv", index=False)
    run_script(VSM, cwd / "_runner.py")
    with open("dsmm_results.pkl", "rb") as f:
        r = pickle.load(f)
    expected = (r["test1_mae"] * 10 + r["test2_mae"] * 4) / 14
    assert r["combined_test_mae"] == pytest.approx(expected)
    assert r["test2_naive_mae"] == pytest.approx(0.2 / 3)  # (|.1|, |.1|, 0) per PC
    assert r["combined_test_naive"] == pytest.approx(0.2 / 3 * 4 / 14)
