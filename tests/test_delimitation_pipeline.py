"""Characterisation tests for the refactored scripts/delimitation-optimization stages
(03 placement, 04 coalition sensitivity, 06 Monte Carlo with women).

All inputs are small synthetic constituency / state rows built here; nothing is read from
the committed data and nothing touches the network. `main()` runs write only to tmp_path."""
import importlib.util

import numpy as np
import pandas as pd
import pytest

from _history import ROOT

DO = ROOT / "scripts" / "delimitation-optimization"


def _import(name):
    spec = importlib.util.spec_from_file_location("do_" + name[:2], DO / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PLACE = _import("03_placement_optimizer")
COAL = _import("04_coalition_sensitivity")
MC = _import("06_monte_carlo_with_women")


def synthetic_constituencies():
    rows = []
    for state, n in (("State_A", 9), ("State_B", 3)):
        for i in range(n):
            rows.append({
                "State": state, "Constituency": f"{state}_C{i}",
                "Const_Type": ("GEN", "SC", "ST")[i % 3],
                "Predicted_Woman_Win_Prob": 0.1 * (i + 1),
                "Predicted_Gender_Gap": -0.01 * (i + 1),
            })
    return pd.DataFrame(rows)


# ---- 03 placement ----------------------------------------------------------------------
def test_build_state_strategies_picks_top_third_by_win_probability():
    df = PLACE.build_state_strategies(synthetic_constituencies())
    a = df.set_index("State").loc["State_A"]
    assert a.Total_Seats == 9 and a.Reserved_Seats_Target == 3        # ceil(9 * 0.33)
    assert a.Representation_Score == pytest.approx(0.9 + 0.8 + 0.7)   # three best
    assert a.Top_Const_Names.startswith("State_A_C8")
    assert df.set_index("State").loc["State_B", "Reserved_Seats_Target"] == 1
    assert list(df.State) == ["State_A", "State_B"]                   # sorted by score desc
    assert (df.Swing_Proxy == df.Avg_Gender_Gap.abs()).all()


def test_build_scenarios_adds_objective_columns_without_mutating_input():
    strat = PLACE.build_state_strategies(synthetic_constituencies())
    before = strat.copy()
    s1, s2, s3 = PLACE.build_scenarios(strat)
    pd.testing.assert_frame_equal(strat, before)
    assert (s1.Objective_Score == s1.Representation_Score).all()
    assert (s2.Objective_Score == s2.Reserved_Seats_Target).all()
    assert (s3.Objective_Score == s3.Swing_Proxy * s3.Representation_Score).all()
    assert set(s3.Strategy) == {"Coalition-Leverage"}


def test_split_rotation_cycles_partitions_states():
    states = [f"S{i}" for i in range(10)]
    c1, c2, c3 = PLACE.split_rotation_cycles(states)
    assert (len(c1), len(c2), len(c3)) == (3, 3, 4)
    assert c1 + c2 + c3 == states


# ---- 04 coalition sensitivity ------------------------------------------------------------
def placement_rows():
    return pd.DataFrame({"State": ["Big", "Small"], "Total_Seats": [100, 10],
                         "Representation_Score": [30.4, 2.0]})


def test_banzhaf_state_four_players_sums_to_one():
    idx, total = COAL.compute_banzhaf_state(35, 35, 0, 30)
    assert total == 100
    assert sum(idx.values()) == pytest.approx(1.0)
    assert idx["NDA"] == idx["INDIA"]


def test_estimate_state_shifts_proxy_assumptions():
    out = COAL.estimate_state_shifts(placement_rows()).set_index("State")
    assert out.loc["Big", "Women_Reserved_Seats_Est"] == 30            # round(30.4)
    assert out.loc["Big", "Total_Seats"] == 100
    assert set(out.Women_Is_Pivotal) <= {"Yes", "No"}
    assert (out.NDA_Power_Change == out.NDA_Banzhaf_After - out.NDA_Banzhaf_Before).all()


def test_estimate_displacement_uses_80_percent_rate():
    women = pd.DataFrame({"State": ["Big"], "Women_Incumbents": [7], "Women_Candidates": [50]})
    out = COAL.estimate_displacement(placement_rows(), women).set_index("State")
    assert out.loc["Big", "Estimated_Displaced_Incumbents"] == 24      # round(30 * 0.8)
    assert out.loc["Big", "Current_Women_Incumbents"] == 7
    assert out.loc["Small", "Current_Women_Incumbents"] == 0           # state absent from table
    assert (out.Displacement_Rate == COAL.DISPLACEMENT_RATE).all()


def test_hung_risk_is_high_by_construction_at_35_percent():
    out = COAL.assess_hung_risk(placement_rows())
    assert list(out.Hung_Parliament_Risk) == ["High", "High"]          # documented in ASSUMPTIONS.md
    assert (out.NDA_Seats_Est == out.INDIA_Seats_Est).all()
    assert (out.Quota == out.Quota.astype(int)).all()


# ---- 06 Monte Carlo ----------------------------------------------------------------------
def test_monte_carlo_constants_are_consistent():
    b = MC.BASELINE_MC
    assert b["NDA_Majority_Prob"] + b["INDIA_Majority_Prob"] + b["Hung_Parliament_Prob"] == pytest.approx(1.0)
    assert MC.QUOTA == MC.LOK_SABHA_SEATS // 2 + 1


def test_classify_scenario_kingmaker_and_seat_conservation():
    r = MC.classify_scenario(255, 260, 31, 272)
    assert r["Outcome_Pre"] == "Hung"
    assert r["Outcome_Post"] == "NDA + Women (Kingmakers)"  # checked before INDIA when both could reach quota
    assert r["NDA_Post"] + r["INDIA_Post"] + r["Other_Post"] + r["Women"] == 543


# ---- end-to-end main() on synthetic inputs, outputs in tmp_path ---------------------------
@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    proc, out = tmp_path / "processed", tmp_path / "output"
    proc.mkdir(), out.mkdir()
    for mod in (PLACE, COAL, MC):
        monkeypatch.setattr(mod, "DATA_PROCESSED", proc)
        monkeypatch.setattr(mod, "OUTPUT_DIR", out)
    synthetic_constituencies().to_csv(proc / "constituency_win_potential.csv", index=False)
    return proc, out


def test_pipeline_main_functions_write_expected_files(sandbox, capsys):
    proc, out = sandbox
    PLACE.main()
    assert (proc / "reserved_seat_placement_representation_first.csv").exists()
    assert (out / "placement_optimization_summary.txt").exists()
    pd.DataFrame({"State": ["State_A", "State_B"], "Women_Incumbents": [1, 0],
                  "Women_Candidates": [5, 2]}).to_csv(proc / "women_candidacy_by_state.csv", index=False)
    COAL.main()
    shifts = pd.read_csv(proc / "coalition_sensitivity_state_level.csv")
    assert len(shifts) == 2 and np.isfinite(shifts.Women_Banzhaf_Index).all()
    assert "COALITION SENSITIVITY ANALYSIS SUMMARY" in (out / "coalition_sensitivity_summary.txt").read_text()
    MC.main()
    res = pd.read_csv(proc / "monte_carlo_women_impact_scenarios.csv")
    assert list(res.Scenario)[:2] == ["S0_Actual_Current", "S1_2024_Declared"] and len(res) == 6
    summ = pd.read_csv(proc / "monte_carlo_summary.csv").iloc[0]
    assert summ.Post_Women_NDA_Majority_Prob == pytest.approx(0.5158 * 0.95)
    assert "=== Phase 5 Complete ===" in capsys.readouterr().out
