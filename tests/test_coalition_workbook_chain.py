"""The coalition workbook is built by a chain of scripts (05 README -> 06 scenarios -> 07 MWC ->
08 Banzhaf -> 09 dashboard -> 10 Monte Carlo -> 11 reorder -> 12 dashboard MC block), each
loading and re-saving coalition_model.xlsx. The chain is run once, on the real scenario script
output and a 300-draw Monte Carlo, and the resulting sheets are checked against the pickles."""
import os
import pickle

import pytest
from openpyxl import load_workbook

from _runscript import run_script

CG = "coalition-game-theory/scripts"
ORDER = ["S0_Actual_Current", "S1_2024_AsDeclared", "S2_NDA_Falls_Short",
         "S3_Deep_Hung_Parliament", "S4_NDA_Needs_Swing", "S5_INDIA_Largest_No_Majority"]


@pytest.fixture(scope="module")
def chain(tmp_path_factory):
    d = tmp_path_factory.mktemp("coalition_chain")
    old = os.getcwd()
    os.chdir(d)
    try:
        fake = d / "_runner.py"
        run_script(f"{CG}/03_scripted_scenarios.py", fake)
        run_script(f"{CG}/04_monte_carlo_simulation.py", fake, subs=[("N_SIMULATIONS = 20000", "N_SIMULATIONS = 300")])
        for name in ("05_build_workbook_readme", "06_build_scenarios_sheet", "07_build_mwc_sheet",
                     "08_build_banzhaf_sheet", "09_build_dashboard", "10_build_montecarlo_sheet",
                     "11_reorder_sheets", "12_insert_mc_into_dashboard"):
            run_script(f"{CG}/{name}.py", fake)
        with open("scenario_results.pkl", "rb") as f:
            res = pickle.load(f)
        with open("monte_carlo_summary.pkl", "rb") as f:
            mc = pickle.load(f)
        wb = load_workbook("coalition_model.xlsx")
    finally:
        os.chdir(old)
    return wb, res, mc


def test_sheet_order_after_reorder(chain):
    wb, _, _ = chain
    assert wb.sheetnames == ["Dashboard", "Monte Carlo Simulation", "README", "Scenarios",
                             "Minimal Winning Coalitions", "Banzhaf Power Index"]


def test_scenarios_sheet_matches_pickle(chain):
    wb, res, _ = chain
    ws = wb["Scenarios"]
    assert [ws.cell(4, c).value for c in range(1, 8)][0] == "Party / Bloc"
    seen = {}
    r = 5
    while ws.cell(r, 1).value != "TOTAL":
        seen[ws.cell(r, 1).value] = [ws.cell(r, 2 + j).value for j in range(6)]
        r += 1
    for j, s in enumerate(ORDER):
        for party, seats in res[s]["players"]:
            assert seen[party][j] == seats
    # a party absent from a scenario (or with 0 seats) is left blank, not 0
    assert seen["BJD_revival"][:3] == [None, None, None] and seen["BJD_revival"][3] == 15
    assert [ws.cell(r, 2 + j).value for j in range(6)] == [
        "=SUM(B5:B%d)" % (r - 1), "=SUM(C5:C%d)" % (r - 1), "=SUM(D5:D%d)" % (r - 1),
        "=SUM(E5:E%d)" % (r - 1), "=SUM(F5:F%d)" % (r - 1), "=SUM(G5:G%d)" % (r - 1)]
    assert [ws.cell(r + 1, 2 + j).value for j in range(6)] == [
        "Single bloc has majority", "Single bloc has majority"] + ["HUNG PARLIAMENT"] * 4


def test_mwc_sheet_lists_every_coalition_up_to_twenty(chain):
    wb, res, _ = chain
    ws = wb["Minimal Winning Coalitions"]
    rows = [[ws.cell(r, c).value for c in range(1, 6)] for r in range(1, ws.max_row + 1)]
    listed = [r for r in rows if isinstance(r[0], int)]
    expected = sum(min(20, len(res[s]["minimal_winning_coalitions"])) for s in ORDER)
    assert len(listed) == expected
    # S0: exactly NDA alone, margin 46
    assert [r for r in rows if r[1] == "NDA"][0] == [1, "NDA", 318, 46, 1]
    # truncation notes mention the exact remainder
    notes = [r[0] for r in rows if isinstance(r[0], str) and r[0].startswith("... plus")]
    assert notes == [f"... plus {len(res[s]['minimal_winning_coalitions']) - 20} more minimal winning coalitions "
                     "(showing 20 smallest/most efficient)" for s in ORDER if len(res[s]["minimal_winning_coalitions"]) > 20]
    # every displayed margin is seats - 272 and parties-needed counts the ' + ' separators
    for r in listed:
        assert r[3] == r[2] - 272 and r[4] == r[1].count(" + ") + 1


def test_banzhaf_sheet_matches_pickle_to_three_decimals(chain):
    wb, res, _ = chain
    ws = wb["Banzhaf Power Index"]
    table = {}
    r = 5
    while ws.cell(r, 1).value:
        table[ws.cell(r, 1).value] = [ws.cell(r, 2 + j).value for j in range(6)]
        r += 1
    assert list(table)[:2] == ["NDA", "INDIA"]  # NDA and INDIA always lead the table
    for j, s in enumerate(ORDER):
        for party, b in res[s]["banzhaf"]:
            assert table[party][j] == pytest.approx(b, abs=6e-4)
    assert table["NDA"][:2] == [1, 1]


def test_dashboard_scenario_table_and_mc_block(chain):
    wb, res, mc = chain
    ws = wb["Dashboard"]
    for i, s in enumerate(ORDER):
        r = 6 + i
        pw = dict(res[s]["players"])
        nda, india = pw["NDA"], pw["INDIA"]
        largest = "NDA" if nda >= india else "INDIA"
        outcome = "HUNG PARLIAMENT" if res[s]["is_hung"] else f"{largest} has outright majority"
        assert [ws.cell(r, c).value for c in range(2, 7)] == [
            nda, india, largest, outcome, len(res[s]["minimal_winning_coalitions"])]
    n = mc["n_simulations"]
    assert ws["A12"].value == f"Monte Carlo Check: Across {n:,} Randomized Permutations"
    assert (ws["A14"].value, ws["C14"].value, ws["E14"].value) == pytest.approx(
        (mc["nda_majority_count"] / n, mc["india_majority_count"] / n, mc["hung_count"] / n))
    assert ws["A14"].number_format == "0.0%"
    assert ws["A13"].value == "NDA Outright Majority" and ws["E13"].value == "Hung Parliament"


def test_monte_carlo_sheet_histogram_and_banzhaf_table(chain):
    wb, _, mc = chain
    ws = wb["Monte Carlo Simulation"]
    n = mc["n_simulations"]
    assert ws["A1"].value == f"Monte Carlo Simulation: {n:,} Randomized Seat Distributions"
    shares = (ws["A5"].value, ws["D5"].value, ws["G5"].value)
    assert shares == pytest.approx((mc["nda_majority_count"] / n, mc["india_majority_count"] / n, mc["hung_count"] / n))
    bins = [(ws.cell(r, 1).value, ws.cell(r, 2).value, ws.cell(r, 3).value) for r in range(12, 27)]
    assert all(b[0].count("-") == 1 for b in bins)
    assert sum(b[1] for b in bins) == n  # every draw falls in a 10-seat band
    for _, cnt, frac in bins:
        assert frac == pytest.approx(cnt / n)
    rows = [(ws.cell(r, 1).value, ws.cell(r, 2).value, ws.cell(r, 3).value) for r in range(32, 44)]
    assert [x[1] for x in rows] == sorted((x[1] for x in rows), reverse=True)
    for party, avg, appeared in rows:
        assert avg == pytest.approx(mc["avg_banzhaf"][party], abs=6e-5)
        assert appeared == len(mc["banzhaf_accumulator"][party])


def test_readme_gains_monte_carlo_notes_once(chain):
    wb, _, _ = chain
    ws = wb["README"]
    texts = [ws.cell(r, 1).value for r in range(1, ws.max_row + 1)]
    assert texts.count("Monte Carlo randomization (NEW)") == 1
    row = texts.index("Monte Carlo randomization (NEW)") + 1
    assert row + 10 == ws.max_row  # the 11 appended lines are the last ones
    assert texts[row - 2] is None  # one blank spacer row precedes them
