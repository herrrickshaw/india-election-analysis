"""Minimal-winning-coalition and Banzhaf enumeration in the coalition scripts,
checked against hand-computed textbook games."""
import pytest

from _scriptload import load

S = load("coalition-game-theory/scripts/03_scripted_scenarios.py", "analyze_scenario")
MC = load("coalition-game-theory/scripts/04_monte_carlo_simulation.py", "analyze")
ST = load("scripts/delimitation-optimization/04_coalition_sensitivity.py", "compute_banzhaf_state")


def test_banzhaf_textbook_50_49_1():
    # quota 51. Winning: {A,B}, {A,C}, {A,B,C}. Critical members: A,B in {A,B};
    # A,C in {A,C}; only A in {A,B,C}. Swings A=3, B=1, C=1 -> 0.6/0.2/0.2.
    r = S["analyze_scenario"]("t", [("A", 50), ("B", 49), ("C", 1)], quota=51)
    assert dict(r["banzhaf"]) == pytest.approx({"A": 0.6, "B": 0.2, "C": 0.2})
    mwc = {tuple(m["coalition"]) for m in r["minimal_winning_coalitions"]}
    assert mwc == {("A", "B"), ("A", "C")}
    assert r["is_hung"] and r["num_winning_coalitions"] == 3


def test_dummy_player_has_zero_power_and_dictator_all():
    r = S["analyze_scenario"]("t", [("A", 60), ("B", 30), ("C", 10)], quota=51)
    assert dict(r["banzhaf"]) == pytest.approx({"A": 1.0, "B": 0.0, "C": 0.0})
    assert not r["is_hung"]


def test_symmetric_three_way_split():
    r = S["analyze_scenario"]("t", [("A", 33), ("B", 33), ("C", 33)], quota=50)
    assert dict(r["banzhaf"]) == pytest.approx({"A": 1 / 3, "B": 1 / 3, "C": 1 / 3})
    assert len(r["minimal_winning_coalitions"]) == 3


def test_monte_carlo_analyze_hung_vs_majority():
    hung = MC["analyze"]([("NDA", 260), ("INDIA", 230), ("X", 30), ("Y", 20), ("Z", 0)], quota=272)
    assert hung["is_hung"] and hung["num_mwc"] >= 1
    assert sum(hung["banzhaf"].values()) == pytest.approx(1.0)
    assert "Z" not in hung["banzhaf"]
    maj = MC["analyze"]([("NDA", 300), ("INDIA", 200), ("X", 40)], quota=272)
    assert not maj["is_hung"] and maj["banzhaf"] is None


def test_state_banzhaf_matches_scenario_engine():
    idx, total = ST["compute_banzhaf_state"](50, 49, 1, 0)
    assert total == 100
    assert idx == pytest.approx({"NDA": 0.6, "INDIA": 0.2, "Women": 0.2})
