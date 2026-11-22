"""Edge branches of 04_coalition_sensitivity and 06_monte_carlo_with_women not reached by
test_delimitation_pipeline (INDIA-majority outcomes, empty-state games, kingmaker listing)."""
import pandas as pd
import pytest

from test_delimitation_pipeline import COAL, MC


# ---- 06: classify_scenario outcome ladder
@pytest.mark.parametrize("nda,india,pre,post", [
    (300, 100, "NDA Majority", "NDA Majority"),          # 300-10 = 290 still a majority
    (280, 100, "NDA Majority", "NDA + Women (Kingmakers)"),  # 280-10 = 270 < 272: women are pivotal
    (200, 290, "INDIA Majority", "INDIA Majority"),      # 290-10 = 280
    (200, 280, "INDIA Majority", "INDIA + Women (Kingmakers)"),  # 280-10 = 270; +31 women = 301
    (260, 250, "Hung", "NDA + Women (Kingmakers)"),      # 250 and 240 post; 250+31 = 281 >= 272
])
def test_classify_scenario_outcome_ladder(nda, india, pre, post):
    r = MC.classify_scenario(nda, india)
    assert r["Outcome_Pre"] == pre
    assert r["Outcome_Post"] == post


def test_classify_scenario_hung_without_kingmaker():
    r = MC.classify_scenario(200, 200)  # 190 / 190 post; 190 + 31 = 221 < 272
    assert (r["Outcome_Pre"], r["Outcome_Post"]) == ("Hung", "Hung")
    assert r["NDA_Post"] == 190 and r["INDIA_Post"] == 190


def test_print_scenario_definitions_labels_each_outcome(capsys):
    MC.print_scenario_definitions(quota=240)  # S5 (NDA 235, INDIA 260) becomes an INDIA majority
    out = capsys.readouterr().out
    assert "→ INDIA Majority" in out and "→ NDA Majority" in out


# ---- 04: Banzhaf on empty / degenerate games
def test_banzhaf_single_bloc_holds_all_power():
    idx, total = COAL.compute_banzhaf_state(10, 0, 0, 0)
    assert idx == {"NDA": 1.0} and total == 10


def test_banzhaf_zero_weight_players_are_dropped():
    idx, _ = COAL.compute_banzhaf_state(40, 40, 0, 20)
    assert set(idx) == {"NDA", "INDIA", "Unaligned"}


@pytest.mark.xfail(strict=True, raises=ValueError,
                   reason="04_coalition_sensitivity.py:44 returns a bare {} instead of ({}, total); callers unpack two values")
def test_banzhaf_empty_state_returns_the_same_pair_shape():
    idx, total = COAL.compute_banzhaf_state(0, 0, 0, 0)
    assert idx == {} and total == 0


@pytest.mark.xfail(strict=True, raises=ValueError,
                   reason="04_coalition_sensitivity.py:44 same bare-dict return makes estimate_state_shifts crash on a 0-seat row")
def test_estimate_state_shifts_survives_a_zero_seat_state():
    placement = pd.DataFrame({"State": ["Empty"], "Representation_Score": [0.0], "Total_Seats": [0]})
    out = COAL.estimate_state_shifts(placement)
    assert out.iloc[0].Women_Banzhaf_Index == 0


# ---- 04 main(): kingmaker listing when at least one state has a pivotal women's bloc
def test_main_lists_pivotal_states(tmp_path, monkeypatch, capsys):
    proc, out = tmp_path / "p", tmp_path / "o"
    proc.mkdir(), out.mkdir()
    monkeypatch.setattr(COAL, "DATA_PROCESSED", proc)
    monkeypatch.setattr(COAL, "OUTPUT_DIR", out)
    pd.DataFrame({"State": ["Big"], "Total_Seats": [100], "Representation_Score": [30.4]}).to_csv(
        proc / "reserved_seat_placement_representation_first.csv", index=False)
    pd.DataFrame({"State": ["Big"], "Women_Incumbents": [3], "Women_Candidates": [9]}).to_csv(
        proc / "women_candidacy_by_state.csv", index=False)
    COAL.main()
    text = capsys.readouterr().out
    assert "Total: 1 states out of 1" in text
    assert "Women_Reserved_Seats_Est" in text.split("Kingmakers (Pivotal):")[1]


# ---- 12: digamma inversion safeguards (loaded with the AST helper)
def test_invert_digamma_large_argument_hits_the_upper_clip():
    from _scriptload import load
    inv = load("vote-share-modeling/scripts/12_dirichlet_swing_model.py", "_invert_digamma")["_invert_digamma"]
    assert inv(35.0) == pytest.approx(1e6)  # digamma(x) = 35 needs x ~ e^35: clipped at 1e6
    assert inv(-30.0) == pytest.approx(1 / 30, rel=0.05)  # digamma(x) ~ -1/x near zero


def test_invert_digamma_returns_clipped_value_when_not_converged():
    from _scriptload import load
    inv = load("vote-share-modeling/scripts/12_dirichlet_swing_model.py", "_invert_digamma")["_invert_digamma"]
    one_step = inv(0.3, max_iter=1)
    assert 1e-3 <= one_step <= 1e6 and one_step != pytest.approx(inv(0.3), abs=1e-9)
