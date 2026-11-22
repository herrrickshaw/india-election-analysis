"""The openpyxl report builders (election-data 03-06, seat-bias 02-04/06-09, vote-share 06-09/13-16,
delimitation 02/02b). Each family is a chain: a script creates a workbook, later scripts load and
extend it. Chains run in tmp_path on synthetic inputs and the sheets are checked against those
inputs (sheet order, table values, derived KPI text, formulas) -- not styling."""
import os
import pickle
import shutil
import sys
import types

import numpy as np
import pandas as pd
import pytest
from openpyxl import Workbook, load_workbook

from _runscript import ROOT, run_script

ED = "election-data-analysis/scripts"
SB = "coalition-game-theory/seat-bias-analysis/scripts"
VS = "vote-share-modeling/scripts"
DO = "scripts/delimitation-optimization"


def vals(ws):
    """All non-empty cell values of a sheet, row-major."""
    return [c.value for row in ws.iter_rows() for c in row if c.value is not None]


def row_of(ws, text, col=1):
    for r in range(1, ws.max_row + 1):
        if ws.cell(r, col).value == text:
            return r
    raise AssertionError(f"{text!r} not found in column {col} of {ws.title}")


@pytest.fixture
def cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def run(cwd, rel, subs=()):
    return run_script(rel, cwd / "_runner.py", subs=subs)


# ================================================================ election-data chain
@pytest.fixture
def election(cwd):
    for n in ("01_build_state_data", "02_build_national_trend", "03_build_workbook_sheets1-2",
              "04_build_national_trend_sheet", "05_build_growth_delimitation_sheet", "06_build_dashboard"):
        run(cwd, f"{ED}/{n}.py")
    return load_workbook("election_analysis.xlsx"), pd.read_csv("state_data_raw.csv")


def test_election_workbook_sheet_order(election):
    wb, _ = election
    assert wb.sheetnames == ["Dashboard", "README", "State-wise LS Data", "National Trend",
                             "Growth & Delimitation"]


def test_state_sheet_rows_sorted_states_first_by_seats(election):
    wb, df = election
    ws = wb["State-wise LS Data"]
    rows = [(ws.cell(r, 1).value, ws.cell(r, 2).value, ws.cell(r, 3).value) for r in range(3, 39)]
    assert len(rows) == 36 and rows[0] == ("Uttar Pradesh", 80, 154344580)
    states = [r for r in rows if r[0] not in ("Andaman and Nicobar Islands", "Chandigarh",
                                               "Dadra and Nagar Haveli and Daman and Diu", "Ladakh", "Lakshadweep")]
    # states (with an assembly) come first, ordered by LS seats descending; the five UTs follow
    assert [r[0] for r in rows[:31]] == [r[0] for r in states]
    assert [r[1] for r in rows[:31]] == sorted([r[1] for r in rows[:31]], reverse=True)
    assert {r[0]: r[2] for r in rows} == df.set_index("State").Electors_2024.to_dict()
    # UTs without an assembly show an em dash instead of a ratio
    last = [ws.cell(38, c).value for c in range(7, 10)]
    assert last == ["—", "—", "—"]
    assert ws["D3"].value == '=IF(C3="","",C3/B3)'
    assert ws["B39"].value == "=SUM(B3:B38)" and ws["D39"].value == "=C39/B39"


def test_dashboard_kpi_cells_point_at_the_right_rows(election):
    wb, _ = election
    sw = wb["State-wise LS Data"]
    d = wb["Dashboard"]
    assert d["A5"].value == "='State-wise LS Data'!D39" and sw["A39"].value == "ALL-INDIA TOTAL / AVERAGE"
    assert d["E5"].value == "='State-wise LS Data'!B39"
    # the "highest state" KPI is hard-wired to row 21 and labelled Delhi
    assert "(Delhi)" in d["C4"].value
    assert d["C5"].value == "='State-wise LS Data'!D21" and sw["A21"].value == "Delhi"
    assert d["G5"].value == "='National Trend'!B9"


def test_dashboard_top_and_bottom_ten(election):
    wb, df = election
    d = wb["Dashboard"]
    avg = (df.Electors_2024 / df.LS_Seats_2024)
    ranked = pd.Series(avg.values, index=df.State).sort_values(ascending=False)
    top = [(d.cell(r, 1).value, d.cell(r, 2).value) for r in range(10, 20)]
    bottom = [(d.cell(r, 4).value, d.cell(r, 5).value) for r in range(10, 20)]
    assert [t[0] for t in top] == list(ranked.index[:10])
    assert [t[1] for t in top] == pytest.approx(list(ranked.values[:10]), abs=1)
    assert [b[0] for b in bottom] == list(ranked.index[-10:][::-1])  # ascending: smallest first
    assert [b[1] for b in bottom] == pytest.approx(sorted(ranked.values[-10:]), abs=1)


def test_national_trend_sheet_formulas_and_growth(election):
    wb, _ = election
    ws = wb["National Trend"]
    assert [ws.cell(r, 1).value for r in (4, 5, 6)] == [2014, 2019, 2024]
    assert [ws.cell(r, 5).value for r in (4, 5, 6)] == [543, 542, 543]
    assert ws["F4"].value == "=B4/E4"
    assert ws["B8"].value == "=(B6-B4)/B4" and ws["B9"].value == "=(F6-F4)/F4"
    assert ws["B10"].value == "=E6-E4"


def test_growth_sheet_covers_states_only_and_uses_population_per_seat(election):
    wb, df = election
    ws = wb["Growth & Delimitation"]
    names = [ws.cell(r, 1).value for r in range(5, 36)]
    assert len(names) == 31 and "Ladakh" not in names and "Lakshadweep" not in names
    assert ws["A5"].value == "Uttar Pradesh" and ws["C5"].value == 199812341
    assert ws["D5"].value == "=C5/B5" and ws["F5"].value == "=D5/E5*100"
    assert ws["E5"].value == "=SUM($C$5:$C$35)/SUM($B$5:$B$35)"
    assert ">110" in ws["G5"].value and "<90" in ws["G5"].value


# ================================================================ seat-bias chain
def _sweep_csv(path, totals=(534, 543, 850, 1000)):
    rows = []
    for i, t in enumerate(totals):
        rows.append(dict(total_seats=t, quota=t // 2 + 1, nda_seat_share=0.60 + i * 0.01, nda_vote_share=0.5,
                         india_seat_share=0.3, india_vote_share=0.4, other_seat_share=0.1 - i * 0.01,
                         other_vote_share=0.1, seat_bonus_leader=0.10 + i * 0.01,
                         bonus_std_across_elections=0.05 - i * 0.005, gallagher_index=9.0 - i,
                         pct_nda_majority=0.90 + i * 0.02))
    pd.DataFrame(rows).to_csv(path, index=False)


def _gan_csv(path, totals=(534, 543, 850, 1000)):
    rows = []
    for sc, tb, m in [("S0_NDA_Real", "NDA", 11.1), ("S1_INDIA_Mirror", "INDIA", 11.1), ("S2_Tossup", "NDA", 0.0),
                      ("S3_INDIA_Small", "INDIA", 3.0), ("S4_NDA_Small", "NDA", 3.0)]:
        for t in totals:
            rows.append(dict(scenario=sc, tracked_bloc=tb, target_margin_pp=m, total_seats=t, quota=t // 2 + 1,
                             tracked_seat_share=0.6, tracked_vote_share=0.5, mean_bonus=0.1, bonus_std=0.02,
                             pct_tracked_majority=0.5 + t / 4000))
    pd.DataFrame(rows).to_csv(path, index=False)


@pytest.fixture
def seatbias(cwd):
    _sweep_csv(cwd / "sweep.csv")
    _gan_csv(cwd / "gan.csv")
    Workbook().save("seat_bias_analysis.xlsx")  # the base workbook is produced outside this repo
    sweep = ("/home/claude/coalition_model/seat_bias_sweep_v2_to1000.csv", str(cwd / "sweep.csv"))
    gan = ("/home/claude/coalition_model/gan_scenario_results.csv", str(cwd / "gan.csv"))
    run(cwd, f"{SB}/02_build_direct_answer_sheet.py", [sweep])
    run(cwd, f"{SB}/03_build_full_sweep_sheet.py", [sweep])
    run(cwd, f"{SB}/04_build_methodology_sheet.py")
    run(cwd, f"{SB}/09_build_assumption_audit.py")
    run(cwd, f"{SB}/06_build_symmetry_test_readme.py")
    run(cwd, f"{SB}/07_build_symmetry_test_results.py", [gan])
    run(cwd, f"{SB}/08_build_symmetry_test_chart.py", [gan])
    return load_workbook("seat_bias_analysis.xlsx"), load_workbook("gan_symmetry_test.xlsx")


def test_seat_bias_sheets_are_inserted_at_requested_positions(seatbias):
    sb, gan = seatbias
    assert sb.sheetnames == ["Direct Answer", "Methodology", "Sheet", "Full Sweep Data & Charts", "Assumption Audit"]
    assert gan.sheetnames == ["Symmetry Test Results", "README", "All Scenarios Chart Data"]


def test_direct_answer_kpis_derive_from_the_sweep(seatbias):
    sb, _ = seatbias
    ws = sb["Direct Answer"]
    r = row_of(ws, "Avg winner's bonus,\nALL seat-totals 534-1000") + 2
    assert ws.cell(r, 1).value == "11.50pp\n(flat)"  # mean(0.10, 0.11, 0.12, 0.13) = 0.115
    assert [ws.cell(r, c).value for c in (3, 5, 7)] == ["90.0%", "94.0%", "96.0%"]  # 534, 850, 1000 seats


def test_full_sweep_sheet_one_row_per_seat_total_in_points(seatbias):
    sb, _ = seatbias
    ws = sb["Full Sweep Data & Charts"]
    rows = [[ws.cell(r, c).value for c in range(1, 9)] for r in range(5, 9)]
    assert [r[0] for r in rows] == [534, 543, 850, 1000]
    assert [r[1] for r in rows] == [268, 272, 426, 501]
    assert rows[0][2:4] == [0.6, 0.5]
    # bonus and its volatility are shown in percentage points
    assert rows[0][4] == pytest.approx(10.0) and rows[0][5] == pytest.approx(5.0)
    assert rows[3][7] == pytest.approx(0.96)
    assert len(ws._charts) == 3


def test_symmetry_results_summary_rows(seatbias):
    _, gan = seatbias
    ws = gan["Symmetry Test Results"]
    r = row_of(ws, "Scenario")
    labels = [ws.cell(r + 1 + i, 1).value for i in range(5)]
    assert labels == ["S0: NDA Real (+11.1pp)", "S1: INDIA Mirror (+11.1pp)", "S2: True Tossup (0pp)",
                      "S3: INDIA Small (+3pp)", "S4: NDA Small (+3pp)"]
    first = [ws.cell(r + 1, c).value for c in range(2, 8)]
    # P(majority) at 534 = 0.5 + 534/4000, at 1000 = 0.75; change = difference
    assert first[0] == "NDA" and first[1] == "+11.1pp"
    assert first[2:5] == pytest.approx([0.6335, 0.75, 0.1165])
    assert first[5] == pytest.approx(1.0)  # perfectly increasing in seats
    # margin column: '+x.ypp' for a lead, '0pp (tossup)' for a zero margin
    assert [ws.cell(r + 1 + i, 4 - 1).value for i in range(5)] == ["+11.1pp", "+11.1pp", "0pp (tossup)",
                                                                   "+3.0pp", "+3.0pp"]


def test_symmetry_chart_data_is_pivoted_by_seat_total(seatbias):
    _, gan = seatbias
    ws = gan["All Scenarios Chart Data"]
    assert [ws.cell(4, c).value for c in range(1, 7)] == ["Total Seats", "S0_NDA_Real", "S1_INDIA_Mirror",
                                                          "S2_Tossup", "S3_INDIA_Small", "S4_NDA_Small"]
    assert [ws.cell(r, 1).value for r in range(5, 9)] == [534, 543, 850, 1000]
    assert [ws.cell(r, 2).value for r in range(5, 9)] == pytest.approx([0.6335, 0.63575, 0.7125, 0.75])
    assert len(ws._charts) == 1


# ================================================================ vote-share chain
def _ga_features():
    rng = np.random.default_rng(4)
    rows = []
    blocs = ["NDA", "INDIA", "Other"]
    for year in (1999, 2004, 2009, 2014, 2019):
        split = {1999: "train", 2004: "train", 2009: "validation", 2014: "test", 2019: "test"}[year]
        for i in range(60):
            b = blocs[i % 3]
            rows.append(dict(State_Name="S" + str(i % 4), PC_No=i, PC_Name=f"PC{i}", Year=year, Party="BJP",
                             Bloc=b, Candidate=f"C{i}", Total_Votes=1000 + i, Margin_Pct=float(5 + (i % 3) * 10),
                             N_Candidates_PC=5 + i % 4, Effective_N_Parties=2.0 + (i % 3) * 0.5,
                             Bloc_Retained=int(i % 3 != 2), Has_Prev_Result=0 if year == 1999 else 1,
                             Prev_Margin_Pct=np.nan if year == 1999 else rng.uniform(0, 30), split=split))
    return pd.DataFrame(rows)


@pytest.fixture
def fake_lightgbm(monkeypatch):
    from sklearn.ensemble import GradientBoostingClassifier

    class LGBMClassifier(GradientBoostingClassifier):
        def __init__(self, n_estimators=100, max_depth=3, learning_rate=0.1, random_state=None, verbosity=-1):
            super().__init__(n_estimators=n_estimators, max_depth=max_depth, learning_rate=learning_rate,
                             random_state=random_state)
            self.verbosity = verbosity  # lightgbm-only knob; sklearn's get_params needs the attribute

    mod = types.ModuleType("lightgbm")
    mod.LGBMClassifier = LGBMClassifier
    monkeypatch.setitem(sys.modules, "lightgbm", mod)


def test_prepare_xy_coerces_and_fills_with_column_median(fake_lightgbm, cwd):
    ns = run_script(f"{VS}/03_train_discrete_classifier.py", cwd / "_r.py", name="not_main")
    df = pd.DataFrame({"a": ["1", "x", "5", None], "b": [1.0, 2.0, 3.0, np.nan], "Bloc": list("wxyz")})
    before = df.copy()
    X, y = ns["prepare_xy"](df, ["a", "b"])
    assert X["a"].tolist() == [1.0, 3.0, 5.0, 3.0]  # 'x' -> NaN -> median(1, 5) = 3
    assert X["b"].tolist() == [1.0, 2.0, 3.0, 2.0]
    assert y.tolist() == list("wxyz")
    pd.testing.assert_frame_equal(df, before)  # input untouched


def test_train_discrete_classifier_summary(fake_lightgbm, cwd, capsys):
    _ga_features().to_csv("ga_features.csv", index=False)
    ns = run_script(f"{VS}/03_train_discrete_classifier.py", cwd / "_r.py", name="not_main")
    summary = ns["run"]()
    with open("model_results_real.pkl", "rb") as f:
        saved = pickle.load(f)
    assert saved.keys() == summary.keys()
    assert summary["label_encoder_classes"] == ["INDIA", "NDA", "Other"]
    assert summary["feature_cols"] == ["Bloc_Retained", "Has_Prev_Result", "Prev_Margin_Pct",
                                       "N_Candidates_PC", "Effective_N_Parties"]
    # the three blocs are equally common, so the majority-class baseline is exactly 1/3 (ties -> first class)
    assert summary["baseline_val_acc"] == pytest.approx(1 / 3)
    assert summary["baseline_test_acc"] == pytest.approx(1 / 3)
    assert set(summary["results"]) == {"Logistic Regression", "Random Forest", "LightGBM"}
    for name, r in summary["results"].items():
        cm = np.array(r["test_confusion"])
        assert cm.shape == (3, 3) and cm.sum() == 120  # 2014 + 2019
        assert np.array(r["val_confusion"]).sum() == 60
        assert r["test_accuracy"] == pytest.approx(np.trace(cm) / 120)
        assert 0 <= r["test_macro_f1"] <= 1 and r["classes"] == ["INDIA", "NDA", "Other"]
    out = capsys.readouterr().out
    assert "Train: 120 | Val: 60 | Test: 120" in out and "Saved model_results_real.pkl" in out


def test_recency_check_trains_on_2009_2014_and_tests_2019(fake_lightgbm, cwd, capsys):
    _ga_features().to_csv("ga_features.csv", index=False)
    run(cwd, f"{VS}/04_recency_sensitivity_check.py")
    with open("recent_split_results.pkl", "rb") as f:
        r = pickle.load(f)
    assert r["baseline_acc"] == pytest.approx(1 / 3)
    assert set(r["results"]) == {"Logistic Regression", "Random Forest", "LightGBM"}
    assert all(0 <= v["test_accuracy"] <= 1 for v in r["results"].values())
    # the rule "x -> pattern" is learnable (retained => same bloc as the pattern), so models beat chance
    assert r["results"]["Random Forest"]["test_accuracy"] > r["baseline_acc"]
    out = capsys.readouterr().out
    assert "Majority-class baseline (train on 2009+2014, test on 2019): 0.333" in out
    assert "Saved recent_split_results.pkl" in out


@pytest.fixture
def votechain(cwd, fake_lightgbm):
    _ga_features().to_csv("ga_features.csv", index=False)
    pd.DataFrame({"Year": [1961, 1962], "NDA": [3, 4], "INDIA": [30, 31], "Other": [7, 5], "Total": [40, 40],
                  "NDA_Share": [0.075, 0.1], "INDIA_Share": [0.75, 0.775], "Other_Share": [0.175, 0.125]}
                 ).to_csv("ae_national_bloc_trend.csv", index=False)
    ns = run_script(f"{VS}/03_train_discrete_classifier.py", cwd / "_r.py", name="not_main")
    ns["run"]()
    run(cwd, f"{VS}/04_recency_sensitivity_check.py")
    for n in ("06_build_workbook_readme", "07_build_ae_trend_sheet", "08_build_classifier_results_sheet",
              "09_build_raw_sample_sheet"):
        run(cwd, f"{VS}/{n}.py")
    return load_workbook("election_ml_tcpd_real.xlsx")


def test_classifier_workbook_sheets(votechain):
    wb = votechain
    assert wb.sheetnames == ["README", "Long-Term AE Trend (1961-2023)", "GA Model Results (Real Data)",
                             "Raw PC Winners Sample"]


def test_ae_trend_sheet_rows(votechain):
    ws = votechain["Long-Term AE Trend (1961-2023)"]
    r = row_of(ws, "Year")
    assert [ws.cell(r + 1, c).value for c in range(1, 8)] == [1961, 3, 30, 7, 40, 0.075, 0.75]
    assert [ws.cell(r + 2, c).value for c in range(1, 8)] == [1962, 4, 31, 5, 40, 0.1, 0.775]


def test_raw_sample_sheet_takes_first_forty_pcs_per_year(votechain):
    ws = votechain["Raw PC Winners Sample"]
    r = row_of(ws, "State")
    body = [[ws.cell(rr, c).value for c in range(1, 13)] for rr in range(r + 1, ws.max_row + 1)]
    body = [b for b in body if isinstance(b[1], int)]
    assert len(body) == 5 * 40
    assert sorted({b[1] for b in body}) == [1999, 2004, 2009, 2014, 2019]
    assert [b[1] for b in body] == sorted(b[1] for b in body)  # ordered by year first


def test_classifier_results_sheet_reports_baseline_and_beats_flag(votechain):
    ws = votechain["GA Model Results (Real Data)"]
    text = " ".join(str(v) for v in vals(ws))
    assert "Majority-class baseline: validation 33.3%, test 33.3%" in text
    assert "Logistic Regression" in text and "Random Forest" in text and "LightGBM" in text


@pytest.fixture
def modelchain(cwd):
    # dsmm_results.pkl from the real 12 script on the analytic world used in test_seat_bias_and_election_data
    rows = []
    for year in (1999, 2004, 2009, 2014, 2019):
        for i in range(10):
            sh = [0.6, 0.3, 0.1] if year == 1999 else ([0.5, 0.4, 0.1] if year == 2004 and i % 2 == 0 else
                                                       [0.3, 0.6, 0.1] if year == 2004 else [0.4, 0.5, 0.1])
            rows.append(("S", i, year, *sh, 1.0))
    pd.DataFrame(rows, columns=["State_Name", "PC_No", "Year", "V_NDA", "V_INDIA", "V_Other", "V_sum_check"]
                 ).to_csv("vote_share_continuous.csv", index=False)
    run(cwd, "vote-share-modeling/scripts/12_dirichlet_swing_model.py")
    n = 6
    hier = dict(val_mae=0.11, val_naive_mae=0.09, test_mae=0.12, test_naive_mae=0.08, coverage=0.4231,
                test_pred=np.array([0.2, 0.3, 0.4, 0.5, 0.6, 0.7]), test_lo=np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6]),
                test_hi=np.array([0.3, 0.4, 0.5, 0.6, 0.7, 0.8]),
                # actuals sit exactly on the lower bound (i=2) and the upper bound (i=3): both inside
                test_actual=np.array([0.25, 0.9, 0.3, 0.6, 0.0, 0.7]),
                test_states=["A"] * n, test_years=np.array([2014] * 3 + [2019] * 3), test_pc_names=list("pqrstu"))
    with open("hierarchical_model_results.pkl", "wb") as f:
        pickle.dump(hier, f)
    for n_ in ("13_build_vsm_workbook_readme", "14_build_model_comparison_sheet",
               "15_build_dsmm_diagnostics_sheet", "16_build_calibration_sheet"):
        run(cwd, f"{VS}/{n_}.py")
    return load_workbook("vote_share_models.xlsx"), hier


def test_vote_share_workbook_sheets(modelchain):
    wb, _ = modelchain
    assert wb.sheetnames == ["README", "Model Comparison", "Dirichlet-Swing Diagnostics",
                             "Hierarchical Model Calibration"]


def test_model_comparison_rows_carry_validation_and_test_maes(modelchain):
    wb, hier = modelchain
    ws = wb["Model Comparison"]
    flat = vals(ws)
    for key in ("val_mae", "val_naive_mae", "test_mae", "test_naive_mae"):
        assert any(isinstance(v, float) and v == pytest.approx(hier[key]) for v in flat), key
    assert "Hierarchical Bayes (MrP-style)" in flat and "Dirichlet-Swing Matrix" in flat
    assert "Test (pooled)" in flat


def test_calibration_sheet_flags_which_intervals_cover_the_actual(modelchain):
    wb, hier = modelchain
    ws = wb["Hierarchical Model Calibration"]
    assert "RESULT: 90% credible intervals achieved only 42.3% actual coverage on test" in vals(ws)
    r = row_of(ws, "A", 1)
    table = [[ws.cell(r + i, c).value for c in range(1, 9)] for i in range(6)]
    assert [t[1] for t in table] == [2014] * 3 + [2019] * 3 and [t[2] for t in table] == list("pqrstu")
    assert [t[6] for t in table] == [0.25, 0.9, 0.3, 0.6, 0.0, 0.7]
    inside = [lo <= a <= hi for lo, a, hi in zip(hier["test_lo"], hier["test_actual"], hier["test_hi"])]
    assert inside == [True, False, True, True, False, True]
    assert [t[7] for t in table] == ["Yes", "No", "Yes", "Yes", "No", "Yes"]


def test_dsmm_diagnostics_sheet_shows_mean_transition_matrix(modelchain):
    wb, _ = modelchain
    flat = vals(wb["Dirichlet-Swing Diagnostics"])
    means = [v for v in flat if isinstance(v, float)]
    assert any(v == pytest.approx(0.4, abs=1e-3) for v in means)
    assert any(v == pytest.approx(0.5, abs=1e-3) for v in means)


# ================================================================ delimitation workbooks
@pytest.fixture
def do_tree(tmp_path):
    from test_delimitation_phase1 import _ae_model, _ae_small
    d = tmp_path / "scripts" / "delimitation-optimization"
    d.mkdir(parents=True)
    shutil.copy(ROOT / DO / "sexcode.py", d / "sexcode.py")
    for sub in ("data/raw", "data/processed", "coalition-game-theory/output"):
        (tmp_path / sub).mkdir(parents=True)
    import gzip
    for name, df in (("TCPD_AE_All_States_2026-6-29.csv.gz", _ae_model()),):
        with gzip.open(tmp_path / "data" / "raw" / name, "wt") as f:
            df.to_csv(f, index=False)
    small = _ae_small()
    return tmp_path, d / "_runner.py", small


def test_women_candidacy_workbook(do_tree):
    root, fake, small = do_tree
    import gzip
    with gzip.open(root / "data" / "raw" / "TCPD_AE_All_States_2026-6-29.csv.gz", "wt") as f:
        small.to_csv(f, index=False)
    run_script(f"{DO}/01_parse_women_candidacy.py", fake)
    run_script(f"{DO}/02_build_women_candidacy_workbook.py", fake)
    wb = load_workbook(root / "coalition-game-theory" / "output" / "Women_Candidacy_Analysis.xlsx")
    assert wb.sheetnames == ["Dashboard", "README", "State Summary", "Women Winners", "High Women Candidacy"]
    dash = wb["Dashboard"]
    kv = {dash.cell(r, 1).value: dash.cell(r, 2).value for r in range(4, 12)}
    assert kv["Total Women Candidates"] == "3" and kv["Total Assembly Elections Candidates"] == "11"
    assert kv["Women Candidacy Rate Pct"] == "27.27%"
    assert kv["Constituencies With Women Winners"] == "1" and kv["States Analyzed"] == "2"
    states = wb["State Summary"]
    assert [states.cell(1, c).value for c in range(1, 4)][0] is not None
    assert "S1" in vals(states) and "S2" in vals(states)


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="02_build_women_candidacy_workbook.py:50 hard-codes '0.1%' next to the real counts")
def test_dashboard_finding_percentage_matches_the_counts_beside_it(do_tree):
    root, fake, small = do_tree
    import gzip
    with gzip.open(root / "data" / "raw" / "TCPD_AE_All_States_2026-6-29.csv.gz", "wt") as f:
        small.to_csv(f, index=False)
    run_script(f"{DO}/01_parse_women_candidacy.py", fake)
    run_script(f"{DO}/02_build_women_candidacy_workbook.py", fake)
    wb = load_workbook(root / "coalition-game-theory" / "output" / "Women_Candidacy_Analysis.xlsx")
    finding = wb["Dashboard"]["A13"].value  # "Women comprise only 0.1% ... (3 / 11)"
    assert "(3 / 11)" in finding and f"{100 * 3 / 11:.1f}%" in finding


def test_electability_workbook(do_tree):
    root, fake, _ = do_tree
    run_script(f"{DO}/02_fit_electability_model.py", fake)
    run_script(f"{DO}/02b_build_electability_workbook.py", fake)
    wb = load_workbook(root / "coalition-game-theory" / "output" / "Women_Electability_Model.xlsx")
    assert wb.sheetnames == ["Dashboard", "README", "State Gender Penalties", "High-Potential Constituencies",
                             "Best Representation Potential"]
    pen = pd.read_csv(root / "data" / "processed" / "state_gender_penalties.csv")
    flat = vals(wb["State Gender Penalties"])
    assert set(pen.State) <= set(flat)
    pot = pd.read_csv(root / "data" / "processed" / "constituency_win_potential.csv")
    assert set(pot.nsmallest(5, "Predicted_Gender_Gap").Constituency) & set(vals(wb["High-Potential Constituencies"]))
