"""Boundary and tie cases (>= vs >, first vs last row, exact thresholds) that the broader
end-to-end tests do not pin down. Each test names the line it guards."""
import gzip
import pickle
import shutil

import numpy as np
import pandas as pd
import pytest
from openpyxl import Workbook, load_workbook

from _runscript import ROOT, run_script
from _scriptload import load

DO = "scripts/delimitation-optimization"
CG = "coalition-game-theory/scripts"
SB = "coalition-game-theory/seat-bias-analysis/scripts"
VS = "vote-share-modeling/scripts"


@pytest.fixture
def tree(tmp_path):
    d = tmp_path / "scripts" / "delimitation-optimization"
    d.mkdir(parents=True)
    shutil.copy(ROOT / DO / "sexcode.py", d / "sexcode.py")
    for sub in ("data/raw", "data/processed", "coalition-game-theory/output"):
        (tmp_path / sub).mkdir(parents=True)

    class T:
        root = tmp_path
        out = tmp_path / "data" / "processed"
        summary_dir = tmp_path / "coalition-game-theory" / "output"
        fake = d / "_runner.py"

        def gz(self, name, df):
            with gzip.open(tmp_path / "data" / "raw" / name, "wt") as f:
                df.to_csv(f, index=False)

    return T()


@pytest.fixture
def cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


# ---------------------------------------------------------------- 01 parse women candidacy
def test_women_winner_means_position_one_and_electors_come_from_first_row(tree):
    df = pd.DataFrame([
        ("S", "C", "M", 1, False, 1000, 70.0),
        ("S", "C", "F", 2, False, 1500, 71.0),  # a runner-up woman is NOT a winner
        ("S", "C", "F", 3, False, 1600, 72.0),
    ], columns=["State_Name", "Constituency_Name", "Sex", "Position", "Incumbent", "Electors",
                "Turnout_Percentage"]).assign(Year=2019)
    tree.gz("TCPD_AE_All_States_2026-6-29.csv.gz", df)
    run_script(f"{DO}/01_parse_women_candidacy.py", tree.fake)
    st = pd.read_csv(tree.out / "women_candidacy_by_state.csv").iloc[0]
    assert (st.Women_Candidates, st.Women_Winners, st.Women_Win_Pct) == (2, 0, 0)
    c = pd.read_csv(tree.out / "women_candidacy_by_constituency.csv").iloc[0]
    assert (c.Electors, c.Turnout_Pct, bool(c.Women_Won)) == (1000, 70.0, False)


# ---------------------------------------------------------------- 02 electability model
def _model_frame():
    from test_delimitation_phase1 import _ae_model
    rows = []
    for c in range(4):  # exactly 20 rows in one state, exactly 5 per constituency
        for k in range(5):
            rows.append(("TWENTY", f"Wc{c}", "F" if k == 1 else "M", k + 1, k % 2 == 0, "GEN", 60.0 + k, "INC"))
    extra = pd.DataFrame(rows, columns=["State_Name", "Constituency_Name", "Sex", "Position", "Incumbent",
                                        "Constituency_Type", "Turnout_Percentage", "Party"])
    return pd.concat([_ae_model(), extra], ignore_index=True)


@pytest.fixture
def fitted(tree):
    df = _model_frame()
    tree.gz("TCPD_AE_All_States_2026-6-29.csv.gz", df)
    ns = run_script(f"{DO}/02_fit_electability_model.py", tree.fake)
    return tree, df, ns


def test_exactly_twenty_rows_and_exactly_five_per_constituency_are_kept(fitted):
    tree, _, _ = fitted
    pen = pd.read_csv(tree.out / "state_gender_penalties.csv")
    assert "TWENTY" in set(pen.State)  # skip rule is `< 20`, so 20 rows is modelled
    pot = pd.read_csv(tree.out / "constituency_win_potential.csv")
    assert {"Wc0", "Wc1", "Wc2", "Wc3"} <= set(pot.Constituency)  # skip rule is `< 5`


def test_missing_incumbency_is_treated_as_not_incumbent(fitted):
    _, df, ns = fitted
    missing = df["Incumbent"].isna().to_numpy()
    assert missing.any() and (ns["df"].loc[missing, "Incumbent"] == 0).all()


def test_predicted_woman_probability_uses_a_female_incumbent_row(fitted):
    tree, _, ns = fitted
    pot = pd.read_csv(tree.out / "constituency_win_potential.csv").set_index("Constituency")
    model, le_state = ns["log_reg"], ns["le_state"]
    # Tc0: GEN (enc 0), turnout 55, all BJP -> NDA (enc 1), state TINY
    x = np.array([[1, 1, 0, 55.0, 1, le_state.transform(["TINY"])[0]]])
    xm = x.copy()
    xm[0, 0] = 0
    assert pot.loc["Tc0", "Predicted_Woman_Win_Prob"] == pytest.approx(model.predict_proba(x)[0][1])
    assert pot.loc["Tc0", "Predicted_Man_Win_Prob"] == pytest.approx(model.predict_proba(xm)[0][1])


# ---------------------------------------------------------------- 05a Lok Sabha analysis
def _ga_two_winners_in_a_state():
    rows = [(2014, "A", "F", 1, "BJP"), (2014, "A", "M", 1, "INC"), (2014, "A", "M", 2, "BJP"),
            (2014, "B", "M", 1, "BJP"), (2014, "B", "F", 2, "INC"), (2019, "B", "F", 1, "INC")]
    return pd.DataFrame(rows, columns=["Year", "State_Name", "Sex", "Position", "Party"])


def test_lok_sabha_console_win_rate_is_women_winners_over_women_candidates(tree, capsys):
    tree.gz("TCPD_GA_All_States_2026-6-29.csv.gz", _ga_two_winners_in_a_state())
    run_script(f"{DO}/05_lok_sabha_analysis.py", tree.fake)
    out = capsys.readouterr().out
    assert "Women winners: 2 (66.7%)" in out  # 2 of the 3 women won
    assert "Overall win rate: 66.7%" in out  # 4 winners of 6 candidates


def test_current_women_counts_every_winner_not_only_women_characterisation_of_a_bug(tree, capsys):
    """Documents today's behaviour of line 133 (see the strict xfail for the intended one):
    4 winners overall (3 are men) -> '4 current women', shortfall 180 - 4."""
    tree.gz("TCPD_GA_All_States_2026-6-29.csv.gz", _ga_two_winners_in_a_state())
    run_script(f"{DO}/05_lok_sabha_analysis.py", tree.fake)
    assert "Current women MPs (18th, 2024 implied): 4" in capsys.readouterr().out
    assert pd.read_csv(tree.out / "lok_sabha_summary.csv").iloc[0].LS_Women_Shortfall == 176


# ---------------------------------------------------------------- 05b exact majority thresholds
@pytest.mark.parametrize("nda,india,expected", [
    (273, 234, "→ NDA remains majority-capable post-reservation"),        # 273-1 = 272 = quota
    (100, 273, "→ INDIA becomes majority-capable post-reservation"),      # 273-1 = 272
    (269, 234, "→ NDA + Women block could form majority (women as kingmakers)"),   # 268 + 4 = 272
    (100, 269, "→ INDIA + Women block could form majority (women as kingmakers)"),  # 268 + 4 = 272
    (268, 234, "→ Hung parliament likely (significant coalition complexity)"),     # 267 + 4 = 271
])
def test_placement_thresholds_are_inclusive(tree, capsys, nda, india, expected):
    pd.DataFrame([("Uttar_Pradesh", 10.0, 100, -2.0), ("Bihar", 0.0, 50, -1.0), ("Ladakh", 100.0, 5, 0.0)],
                 columns=["State", "Women_Win_Rate_Pct", "Women_Candidates", "Empirical_Gap_Pct"]
                 ).to_csv(tree.out / "state_gender_penalties.csv", index=False)
    subs = [("nda_seats_current = 292  # NDA alliance", f"nda_seats_current = {nda}  # NDA alliance"),
            ("india_seats_current = 234  # INDIA alliance", f"india_seats_current = {india}  # INDIA alliance")]
    run_script(f"{DO}/05_lok_sabha_placement.py", tree.fake, subs=subs)
    out = capsys.readouterr().out
    # UP 27 reserved * 10% -> 3, Bihar 0, Ladakh 1 -> 4 women, 1 off each bloc
    assert "Women block: 4 seats" in out
    assert expected in out


# ---------------------------------------------------------------- coalition quota boundaries
def test_bloc_game_exact_quota_counts_as_winning(cwd):
    pd.DataFrame([("n", 272, "NDA"), ("i", 200, "INDIA"), ("a", 68, "UNALIGNED")],
                 columns=["Party", "Seats", "Bloc"]).to_csv("party_seats.csv", index=False)
    run_script(f"{CG}/02_bloc_level_game_theory.py", cwd / "_runner.py")
    m = pd.read_csv("minimal_winning_coalitions.csv")
    # 272 seats exactly is a majority; INDIA + a = 268 is not
    assert m.to_dict("records") == [{"Coalition": "NDA", "Seats": 272, "Margin": 0, "Num_Parties": 1}]
    b = pd.read_csv("banzhaf_bloc_level.csv").set_index("Player")
    assert b.Banzhaf_Index.to_dict() == {"NDA": 1.0, "INDIA": 0.0, "a": 0.0}
    assert b.Swing_Count["NDA"] == 4


def test_scenario_with_exactly_272_seats_is_not_hung():
    ns = load(f"{CG}/03_scripted_scenarios.py", "analyze_scenario")
    r = ns["analyze_scenario"]("x", [("A", 272), ("B", 271)])
    assert r["is_hung"] is False
    assert [m["margin"] for m in r["minimal_winning_coalitions"]] == [0]
    assert ns["analyze_scenario"]("x", [("A", 271), ("B", 272)])["is_hung"] is False
    assert ns["analyze_scenario"]("x", [("A", 271), ("B", 271), ("C", 1)])["is_hung"] is True


# ---------------------------------------------------------------- seat-bias majority at exactly the quota
def _states(cwd):
    pd.DataFrame([("A", 10, 9, 1, 0)], columns=["State", "Seats_2024", "NDA_2024", "INDIA_2024", "Other_2024"]
                 ).to_csv(cwd / "state_2024_bloc_results.csv", index=False)
    pd.DataFrame([("A", 1000)], columns=["State", "Census2011_Pop"]).to_csv(cwd / "state_data_raw.csv", index=False)


def test_sweep_counts_a_majority_of_exactly_the_quota(cwd):
    _states(cwd)
    subs = [("/home/claude/coalition_model/state_2024_bloc_results.csv", str(cwd / "state_2024_bloc_results.csv")),
            ("/home/claude/election_analysis/state_data_raw.csv", str(cwd / "state_data_raw.csv")),
            ("N_SIMULATIONS = 1500", "N_SIMULATIONS = 30"),
            ("SEAT_TOTALS = sorted(set(list(range(534, 1001, 10)) + [850, 1000]))", "SEAT_TOTALS = [1]")]
    run_script(f"{SB}/01_seat_bias_sweep_534_to_1000.py", cwd / "_runner.py", subs=subs)
    r = pd.read_csv("seat_bias_sweep_v2_to1000.csv").iloc[0]
    assert r.quota == 1  # one seat: NDA's single seat IS the quota
    assert r.pct_nda_majority > 0.5


def test_counterfactual_counts_a_majority_of_exactly_the_quota(cwd):
    _states(cwd)
    subs = [("/home/claude/election_analysis/state_data_raw.csv", str(cwd / "state_data_raw.csv")),
            ("N_SIMULATIONS = 1500", "N_SIMULATIONS = 30"),
            ("SEAT_TOTALS = sorted(set(list(range(534, 1001, 20)) + [543, 850, 1000]))", "SEAT_TOTALS = [1]")]
    run_script(f"{SB}/05_counterfactual_scenario_generator.py", cwd / "_runner.py", subs=subs)
    r = pd.read_csv("gan_scenario_results.csv").set_index("scenario")
    assert (r.quota == 1).all()
    assert (r.pct_tracked_majority > 0).all()  # a lone seat is a majority for whoever wins it


# ---------------------------------------------------------------- DSMM lower clip
def test_method_of_moments_clips_overdispersed_concentration_to_one():
    mom = load(f"{VS}/12_dirichlet_swing_model.py", "method_of_moments_dirichlet")["method_of_moments_dirichlet"]
    X = np.array([[0.9, 0.05, 0.05], [0.05, 0.9, 0.05]] * 10)
    # moment-matched alpha0 would be ~0.39 (< 1): it is floored at 1, so alpha == the mean vector
    assert mom(X) == pytest.approx([0.475, 0.475, 0.05], abs=1e-6)


# ---------------------------------------------------------------- 04 recency: which years train / test
def _recency_features():
    patterns = {1999: ["INDIA", "INDIA", "NDA", "Other"], 2004: ["INDIA", "INDIA", "NDA", "Other"],
                2009: ["NDA", "NDA", "INDIA", "Other"], 2014: ["NDA", "NDA", "INDIA", "Other"],
                2019: ["INDIA", "INDIA", "NDA", "Other", "Other"]}
    rows = []
    for year, pat in patterns.items():
        for i in range(60):
            rows.append(dict(Year=year, Bloc=pat[i % len(pat)], Bloc_Retained=i % 2, Has_Prev_Result=1,
                             Prev_Margin_Pct=float(i), N_Candidates_PC=5 + i % 3, Effective_N_Parties=2.0 + i % 2,
                             split="x"))
    return pd.DataFrame(rows)


def test_recency_baseline_is_majority_of_2009_2014_scored_on_2019(cwd, monkeypatch):
    import sys
    import types
    from sklearn.ensemble import GradientBoostingClassifier

    class LGBMClassifier(GradientBoostingClassifier):
        def __init__(self, n_estimators=100, max_depth=3, learning_rate=0.1, random_state=None, verbosity=-1):
            super().__init__(n_estimators=n_estimators, max_depth=max_depth, learning_rate=learning_rate,
                             random_state=random_state)
            self.verbosity = verbosity

    mod = types.ModuleType("lightgbm")
    mod.LGBMClassifier = LGBMClassifier
    monkeypatch.setitem(sys.modules, "lightgbm", mod)
    _recency_features().to_csv("ga_features.csv", index=False)
    run_script(f"{VS}/04_recency_sensitivity_check.py", cwd / "_runner.py")
    with open("recent_split_results.pkl", "rb") as f:
        r = pickle.load(f)
    # train 2009+2014 is NDA-heavy (60 of 120) -> always predict NDA; 2019 has 12 NDA of 60
    assert r["baseline_acc"] == pytest.approx(12 / 60)


# ---------------------------------------------------------------- 07 MWC sheet display cap
@pytest.mark.parametrize("n,note", [(20, None), (21, "... plus 1 more minimal winning coalitions (showing 20 smallest/most efficient)")])
def test_mwc_sheet_cap_is_exactly_twenty(cwd, n, note):
    names = ["S0_Actual_Current", "S1_2024_AsDeclared", "S2_NDA_Falls_Short",
             "S3_Deep_Hung_Parliament", "S4_NDA_Needs_Swing", "S5_INDIA_Largest_No_Majority"]
    mwc = [{"coalition": [f"P{i}", "Q"], "seats": 272 + i, "margin": i} for i in range(n)]
    res = {s: {"minimal_winning_coalitions": mwc if s == names[2] else []} for s in names}
    with open("scenario_results.pkl", "wb") as f:
        pickle.dump(res, f)
    Workbook().save("coalition_model.xlsx")
    run_script(f"{CG}/07_build_mwc_sheet.py", cwd / "_runner.py")
    ws = load_workbook("coalition_model.xlsx")["Minimal Winning Coalitions"]
    col = [ws.cell(r, 1).value for r in range(1, ws.max_row + 1)]
    assert sum(isinstance(v, int) for v in col) == 20
    assert [v for v in col if isinstance(v, str) and v.startswith("... plus")] == ([note] if note else [])
