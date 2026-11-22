"""End-to-end characterisation of coalition-game-theory/scripts 01-04 (party seat table, bloc
level game, scripted scenarios, Monte Carlo). The scripts read/write relative paths, so each
test runs them with the working directory switched to tmp_path."""
import itertools
import pickle

import numpy as np
import pandas as pd
import pytest

from _runscript import run_script

CG = "coalition-game-theory/scripts"


@pytest.fixture
def cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def run(cwd, name, **kw):
    return run_script(f"{CG}/{name}", cwd / "_runner.py", **kw)


# ---------------------------------------------------------------- 01 party seat table
def test_party_seat_table_blocs_and_vacancies(cwd, capsys):
    run(cwd, "01_party_seat_data.py")
    df = pd.read_csv(cwd / "party_seats.csv")
    assert list(df.columns) == ["Party", "Seats", "Bloc", "Vacant_adj"]
    assert len(df) == 45 and df.Party.is_unique
    assert df.groupby("Bloc").Seats.sum().to_dict() == {"INDIA": 206, "NDA": 318, "UNALIGNED": 16}
    assert (df.Vacant_adj == 0).all()
    out = capsys.readouterr().out
    assert "Total accounted: 540, Vacant: 3" in out
    assert "Majority threshold (of 543): 272" in out
    assert "Majority threshold (of 540, excl. 3 vacant): 271" in out


def test_party_seat_table_matches_s0_scenario(cwd):
    """Cross-script consistency: S0_Actual_Current in 03 is built from the same blocs."""
    run(cwd, "01_party_seat_data.py")
    df = pd.read_csv(cwd / "party_seats.csv")
    ns = run(cwd, "03_scripted_scenarios.py")
    s0 = dict(ns["scenarios"]["S0_Actual_Current"])
    assert s0["NDA"] == df[df.Bloc == "NDA"].Seats.sum()
    assert s0["INDIA"] == df[df.Bloc == "INDIA"].Seats.sum()
    # the two scripts label the lone independent differently ("IND(other)" vs "IND"): compare seats
    unaligned = sorted(df[df.Bloc == "UNALIGNED"].Seats)
    assert sorted(v for k, v in s0.items() if k not in ("NDA", "INDIA", "Vacant")) == unaligned
    assert s0["Vacant"] == 543 - df.Seats.sum()


# ---------------------------------------------------------------- 02 bloc-level game
def _seats(rows):
    pd.DataFrame(rows, columns=["Party", "Seats", "Bloc"]).to_csv("party_seats.csv", index=False)


def test_bloc_game_nda_majority_makes_nda_the_only_power(cwd, capsys):
    run(cwd, "01_party_seat_data.py")
    run(cwd, "02_bloc_level_game_theory.py")
    b = pd.read_csv("banzhaf_bloc_level.csv")
    assert len(b) == 12 and b.Seats.sum() == 540
    top = b.iloc[0]
    assert (top.Player, top.Seats, top.Swing_Count, top.Banzhaf_Index) == ("NDA", 318, 2048, 1.0)
    assert (b.iloc[1:].Banzhaf_Index == 0).all()
    m = pd.read_csv("minimal_winning_coalitions.csv")
    assert m.to_dict("records") == [{"Coalition": "NDA", "Seats": 318, "Margin": 46, "Num_Parties": 1}]
    out = capsys.readouterr().out
    assert "Total winning coalitions (>=272): 2048 out of 4095 total subsets" in out
    assert "Saved 1 minimal winning coalitions." in out


def test_bloc_game_hung_parliament_exact_indices(cwd):
    # hand-computed: N=250, I=250, A=20, B=20, quota 272 -> 3 minimal winning coalitions
    # (N+I, N+A+B, I+A+B); swings N=4, I=4, A=2, B=2 of 12.
    _seats([("n", 250, "NDA"), ("i", 250, "INDIA"), ("a", 20, "UNALIGNED"), ("b", 20, "UNALIGNED")])
    run(cwd, "02_bloc_level_game_theory.py")
    b = pd.read_csv("banzhaf_bloc_level.csv").set_index("Player")
    assert b.Swing_Count.to_dict() == {"NDA": 4, "INDIA": 4, "a": 2, "b": 2}
    assert b.Banzhaf_Index["NDA"] == pytest.approx(1 / 3) and b.Banzhaf_Index["a"] == pytest.approx(1 / 6)
    m = pd.read_csv("minimal_winning_coalitions.csv")
    # sorted by (Num_Parties, Seats): the 2-party coalition first
    recs = m.to_dict("records")
    # sorted by (Num_Parties, Seats): the 2-party coalition first, then the two 3-party ones
    assert recs[0] == {"Coalition": "NDA + INDIA", "Seats": 500, "Margin": 228, "Num_Parties": 2}
    assert {r["Coalition"] for r in recs[1:]} == {"NDA + a + b", "INDIA + a + b"}
    assert all(r["Seats"] == 290 and r["Margin"] == 18 and r["Num_Parties"] == 3 for r in recs[1:])
    raw = pd.read_csv("minimal_winning_raw.csv")
    assert sorted(raw.seats) == [290, 290, 500]


def test_bloc_game_unaligned_sorted_by_seats(cwd, capsys):
    _seats([("n", 250, "NDA"), ("i", 250, "INDIA"), ("small", 5, "UNALIGNED"), ("big", 30, "UNALIGNED")])
    run(cwd, "02_bloc_level_game_theory.py")
    out = capsys.readouterr().out
    assert out.index("big") < out.index("small")
    assert "NDA (cohesive): 250" in out and "Unaligned total: 35" in out
    assert "Sum check: 538 == 543" in out  # 250+250+35+3 vacant (the script's constant)


# ---------------------------------------------------------------- 03 scripted scenarios
def _reference_power(weights, quota):
    """Independent Banzhaf / MWC computation (swing definition over coalitions containing i)."""
    n = len(weights)
    swings = [0] * n
    mwc = []
    for r in range(1, n + 1):
        for combo in itertools.combinations(range(n), r):
            w = sum(weights[i] for i in combo)
            if w < quota:
                continue
            critical = [i for i in combo if w - weights[i] < quota]
            for i in critical:
                swings[i] += 1
            if len(critical) == len(combo):
                mwc.append((combo, w))
    return swings, mwc


def test_scripted_scenarios_match_reference_implementation(cwd):
    ns = run(cwd, "03_scripted_scenarios.py")
    with open("scenario_results.pkl", "rb") as f:
        res = pickle.load(f)
    assert list(res) == ["S0_Actual_Current", "S1_2024_AsDeclared", "S2_NDA_Falls_Short",
                         "S3_Deep_Hung_Parliament", "S4_NDA_Needs_Swing", "S5_INDIA_Largest_No_Majority"]
    for name, pw in ns["scenarios"].items():
        r = res[name]
        weights = [w for _, w in pw]
        swings, mwc = _reference_power(weights, 272)
        total = sum(swings)
        idx = {p: i for i, (p, _) in enumerate(pw)}
        assert dict(r["banzhaf"]) == pytest.approx({p: swings[idx[p]] / total for p, _ in pw})
        assert len(r["minimal_winning_coalitions"]) == len(mwc)
        assert r["num_winning_coalitions"] == sum(
            1 for k in range(1, len(pw) + 1) for c in itertools.combinations(weights, k) if sum(c) >= 272)
        # banzhaf is sorted by descending index
        vals = [b for _, b in r["banzhaf"]]
        assert vals == sorted(vals, reverse=True)
        # mwcs sorted by (size, -seats); margin = seats - quota
        keys = [(len(m["coalition"]), -m["seats"]) for m in r["minimal_winning_coalitions"]]
        assert keys == sorted(keys)
        assert all(m["margin"] == m["seats"] - 272 for m in r["minimal_winning_coalitions"])


def test_scripted_scenarios_hung_flags(cwd, capsys):
    run(cwd, "03_scripted_scenarios.py")
    with open("scenario_results.pkl", "rb") as f:
        res = pickle.load(f)
    # hung = no single player reaches 272 alone: S0 (NDA 318) and S1 (NDA 293) are not hung
    assert {k: v["is_hung"] for k, v in res.items()} == {
        "S0_Actual_Current": False, "S1_2024_AsDeclared": False, "S2_NDA_Falls_Short": True,
        "S3_Deep_Hung_Parliament": True, "S4_NDA_Needs_Swing": True, "S5_INDIA_Largest_No_Majority": True}
    out = capsys.readouterr().out
    assert "SCENARIO: S2_NDA_Falls_Short  (HUNG: True)" in out
    assert "Saved scenario_results.pkl" in out


def test_scripted_scenarios_exactly_543_seats(cwd):
    ns = run(cwd, "03_scripted_scenarios.py")
    for name, pw in ns["scenarios"].items():
        assert sum(w for _, w in pw) == 543, name


def test_scripted_scenarios_seat_total_assertion_fires(cwd):
    # corrupt one scenario by a single seat: the module-level sanity assert must stop the run
    with pytest.raises(AssertionError, match="S2_NDA_Falls_Short: seats sum to 544, not 543"):
        run(cwd, "03_scripted_scenarios.py", subs=[('("NDA", 255), ("INDIA", 260)', '("NDA", 256), ("INDIA", 260)')])


# ---------------------------------------------------------------- 04 Monte Carlo
SMALL = [("N_SIMULATIONS = 20000", "N_SIMULATIONS = 300")]


def test_monte_carlo_run_accounting(cwd, capsys):
    run(cwd, "04_monte_carlo_simulation.py", subs=SMALL)
    draws = pd.read_csv("monte_carlo_draws.csv")
    assert len(draws) == 300
    parties = [c for c in draws.columns if c != "is_hung"]
    assert (draws[parties].sum(axis=1) == 543).all()
    with open("monte_carlo_summary.pkl", "rb") as f:
        s = pickle.load(f)
    assert s["n_simulations"] == 300
    # every draw is exactly one of: hung, NDA majority, INDIA majority
    assert s["hung_count"] + s["nda_majority_count"] + s["india_majority_count"] == 300
    assert s["hung_count"] == int(draws.is_hung.sum())
    assert s["nda_majority_count"] == int(((~draws.is_hung) & (draws.NDA >= 272)).sum())
    assert s["india_majority_count"] == int(((~draws.is_hung) & (draws.INDIA >= 272)).sum())
    # hung <=> neither bloc reaches the quota
    assert (draws.is_hung == ((draws.NDA < 272) & (draws.INDIA < 272))).all()
    assert len(s["mwc_counts_when_hung"]) == s["hung_count"]
    for p, vals in s["banzhaf_accumulator"].items():
        assert all(0 <= v <= 1 for v in vals)
        assert s["avg_banzhaf"][p] == (pytest.approx(np.mean(vals)) if vals else 0.0)
    out = capsys.readouterr().out
    assert "Total valid simulations: 300" in out
    assert "Saved monte_carlo_draws.csv and monte_carlo_summary.pkl" in out


def test_monte_carlo_is_reproducible(cwd):
    run(cwd, "04_monte_carlo_simulation.py", subs=SMALL)
    first = pd.read_csv("monte_carlo_draws.csv")
    run(cwd, "04_monte_carlo_simulation.py", subs=SMALL)
    pd.testing.assert_frame_equal(first, pd.read_csv("monte_carlo_draws.csv"))


@pytest.fixture
def mc(cwd):
    return run(cwd, "04_monte_carlo_simulation.py", subs=[("N_SIMULATIONS = 20000", "N_SIMULATIONS = 5")])


def test_generate_one_draw_sums_to_total_and_respects_unaligned_caps(mc):
    rng = np.random.default_rng(123)
    for _ in range(300):
        d = mc["generate_one_draw"](rng)
        assert sum(d.values()) == 543
        for p, (lo, hi) in mc["party_ranges"].items():
            if p not in ("NDA", "INDIA"):  # NDA/INDIA absorb any overflow
                assert 0 <= d[p] <= hi


def test_generate_one_draw_overflow_goes_to_nda_and_india(mc):
    ranges = {"NDA": (1, 1), "INDIA": (1, 1), "A": (2, 2)}
    mc["party_ranges"] = ranges
    mc["players"] = list(ranges)
    mc["n_players"] = 3
    # raw (1,1,2) scales x135.75 -> A would get 271 but is capped at 2; the 269 overflow is
    # split 134 to NDA and 135 to INDIA (odd remainder goes to INDIA).
    assert mc["generate_one_draw"](np.random.default_rng(0)) == {"NDA": 270, "INDIA": 271, "A": 2}


def test_generate_one_draw_all_zero_returns_none(mc):
    ranges = {"NDA": (0, 0), "INDIA": (0, 0)}
    mc["party_ranges"] = ranges
    mc["players"] = list(ranges)
    mc["n_players"] = 2
    assert mc["generate_one_draw"](np.random.default_rng(0)) is None


def test_analyze_skips_enumeration_for_large_hung_games_and_majorities(mc):
    big = [(f"p{i}", 1) for i in range(15)]  # hung, but 15 players > 14 -> not tractable
    r = mc["analyze"](big)
    assert r["is_hung"] and r["num_mwc"] is None and r["banzhaf"] is None
    r = mc["analyze"]([("NDA", 272), ("INDIA", 200), ("x", 71)])  # NDA has a majority: trivial
    assert not r["is_hung"] and r["num_mwc"] is None and r["banzhaf"] is None
    r = mc["analyze"]([("NDA", 271), ("INDIA", 271), ("x", 1), ("zero", 0)])
    assert r["is_hung"] and r["num_mwc"] == 3 and "zero" not in r["banzhaf"]
    assert r["banzhaf"]["x"] == pytest.approx(1 / 3)  # N, I and x are symmetric (2 swings each of 6)
