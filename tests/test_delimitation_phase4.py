"""Characterisation tests for the Lok Sabha extension stages 05_lok_sabha_analysis and
05_lok_sabha_placement (straight-line scripts, run end to end on synthetic inputs).

Genuine source bugs found while writing these are recorded as strict xfails that assert the
CORRECT behaviour (see the reason strings)."""
import gzip
import shutil

import pandas as pd
import pytest

from _runscript import ROOT, run_script

DO = "scripts/delimitation-optimization"
ANALYSIS = f"{DO}/05_lok_sabha_analysis.py"
PLACEMENT = f"{DO}/05_lok_sabha_placement.py"


@pytest.fixture
def tree(tmp_path):
    d = tmp_path / "scripts" / "delimitation-optimization"
    d.mkdir(parents=True)
    shutil.copy(ROOT / DO / "sexcode.py", d / "sexcode.py")
    for sub in ("data/raw", "data/processed", "coalition-game-theory/output"):
        (tmp_path / sub).mkdir(parents=True)

    class T:
        raw = tmp_path / "data" / "raw"
        out = tmp_path / "data" / "processed"
        summary_dir = tmp_path / "coalition-game-theory" / "output"
        fake = d / "_runner.py"

    return T()


# ------------------------------------------------------------------ 05a analysis
def _ga():
    rows = [  # Year, State, Sex, Position, Party
        (2014, "A", "F", 1, "BJP"), (2014, "A", "M", 2, "INC"), (2014, "A", "M", 3, "BJP"),
        (2014, "B", "M", 1, "BJP"), (2014, "B", "F", 2, "INC"),
        (2019, "A", "M", 1, "BJP"), (2019, "A", "F", 2, "INC"),
        (2019, "B", "F", 1, "INC"), (2019, "B", "M", 2, "BJP"), (2019, "B", "F", 3, "BJP"),
    ]
    return pd.DataFrame(rows, columns=["Year", "State_Name", "Sex", "Position", "Party"])


@pytest.fixture
def analysed(tree, capsys):
    with gzip.open(tree.raw / "TCPD_GA_All_States_2026-6-29.csv.gz", "wt") as f:
        _ga().to_csv(f, index=False)
    run_script(ANALYSIS, tree.fake)
    return tree, capsys.readouterr().out


def test_lok_sabha_yearly_table(analysed):
    tree, _ = analysed
    y = pd.read_csv(tree.out / "lok_sabha_women_candidacy_by_year.csv").set_index("Year")
    assert y.loc[2014].to_dict() == {"Total_Candidates": 5, "Women_Candidates": 2, "Women_Pct": 40.0,
                                     "Winners": 2, "Women_Winners": 1, "Women_Win_Rate": 50.0}
    r = y.loc[2019]
    assert (r.Total_Candidates, r.Women_Candidates, r.Winners, r.Women_Winners) == (5, 3, 2, 1)
    assert r.Women_Pct == pytest.approx(60.0) and r.Women_Win_Rate == pytest.approx(100 / 3)


def test_lok_sabha_state_table_sorted_by_women_win_rate(analysed):
    tree, _ = analysed
    s = pd.read_csv(tree.out / "lok_sabha_women_candidacy_by_state.csv")
    assert list(s.State) == ["A", "B"]  # 50% before 33.3%
    a, b = s.set_index("State").loc["A"], s.set_index("State").loc["B"]
    assert (a.LS_Seats, a.Women_Candidates, a.Women_Winners) == (2, 2, 1)
    assert a.Women_Candidacy_Pct == pytest.approx(40.0) and a.Women_Win_Rate_Pct == pytest.approx(50.0)
    assert (b.LS_Seats, b.Women_Candidates, b.Women_Winners) == (2, 3, 1)
    assert b.Women_Win_Rate_Pct == pytest.approx(100 / 3)


def test_lok_sabha_console_report(analysed):
    _, out = analysed
    assert "Total Lok Sabha candidates (1999–2019): 10" in out
    assert "Women candidates: 5 (50.00%)" in out
    # latest-election party block: top parties by candidate count, women share of each
    assert "  BJP: 1 / 3 (33.3%)" in out
    assert "  INC: 2 / 2 (100.0%)" in out
    assert "2019 Lok Sabha Election:" in out and "Women candidates: 3 (60.00%)" in out
    assert "Phase 4a Complete" in out


def test_lok_sabha_summary_constants(analysed):
    tree, _ = analysed
    s = pd.read_csv(tree.out / "lok_sabha_summary.csv").iloc[0]
    assert s.Total_LS_Candidates == 10 and s.Total_Women_LS_Candidates == 5
    assert s.LS_Seats_Total == 543
    assert s.LS_Seats_Reserved_33pct == 180  # ceil(543 * 0.33) = ceil(179.19)


# The three "Women_*" summary fields are computed in Part 1 for the whole country and then
# silently overwritten by the Part 2 per-state loop (`women_pct`, `women_winners` and
# `women_win_rate` are re-bound at lines 89/92/93), so the saved summary holds the LAST state's
# (alphabetically) figures. Synthetic data: national 50% / 40% / 2 winners, state B 60% / 33.3% / 1.
@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="05_lok_sabha_analysis.py:89 women_pct is overwritten by the state loop")
def test_summary_candidacy_rate_is_national_not_last_state(analysed):
    tree, _ = analysed
    s = pd.read_csv(tree.out / "lok_sabha_summary.csv").iloc[0]
    assert s.Women_LS_Candidacy_Rate_Pct == pytest.approx(50.0)


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="05_lok_sabha_analysis.py:93 women_win_rate is overwritten by the state loop")
def test_summary_win_rate_is_national_not_last_state(analysed):
    tree, _ = analysed
    s = pd.read_csv(tree.out / "lok_sabha_summary.csv").iloc[0]
    assert s.Women_LS_Win_Rate_Pct == pytest.approx(40.0)


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="05_lok_sabha_analysis.py:92 women_winners is overwritten by the state loop")
def test_summary_women_winner_count_is_national_not_last_state(analysed):
    tree, _ = analysed
    s = pd.read_csv(tree.out / "lok_sabha_summary.csv").iloc[0]
    assert s.Total_Women_LS_Winners == 2


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="05_lok_sabha_analysis.py:133 counts ALL winners, not women winners, as 'current women'")
def test_shortfall_counts_women_winners_only(analysed):
    tree, _ = analysed
    s = pd.read_csv(tree.out / "lok_sabha_summary.csv").iloc[0]
    assert s.LS_Women_Shortfall == 180 - 2


def test_lok_sabha_zero_women_dataset_does_not_divide_by_zero(tree):
    df = _ga().assign(Sex="M")
    with gzip.open(tree.raw / "TCPD_GA_All_States_2026-6-29.csv.gz", "wt") as f:
        df.to_csv(f, index=False)
    run_script(ANALYSIS, tree.fake)
    y = pd.read_csv(tree.out / "lok_sabha_women_candidacy_by_year.csv")
    assert (y.Women_Win_Rate == 0).all() and (y.Women_Pct == 0).all()
    s = pd.read_csv(tree.out / "lok_sabha_women_candidacy_by_state.csv")
    assert (s.Women_Win_Rate_Pct == 0).all()


# ------------------------------------------------------------------ 05b placement
def _penalties(win_rates=None):
    rates = win_rates or {"Uttar_Pradesh": 10.0, "Bihar": 0.0, "Goa": 50.0, "Ladakh": 100.0,
                          "Daman_&_Diu": 20.0}
    rows = [(s, r, 100 + i, -2.0 - i) for i, (s, r) in enumerate(rates.items())]
    return pd.DataFrame(rows, columns=["State", "Women_Win_Rate_Pct", "Women_Candidates", "Empirical_Gap_Pct"])


def _place(tree, subs=(), pen=None):
    (pen if pen is not None else _penalties()).to_csv(tree.out / "state_gender_penalties.csv", index=False)
    run_script(PLACEMENT, tree.fake, subs=subs)
    return pd.read_csv(tree.out / "lok_sabha_placement_strategy.csv").set_index("State")


def test_placement_reserved_seats_and_estimates(tree):
    p = _place(tree)
    # states absent from the penalties file are skipped; the rest sorted by LS seats, descending
    assert list(p.index) == ["Uttar_Pradesh", "Bihar", "Goa", "Ladakh", "Daman_&_Diu"]
    assert p.loc["Uttar_Pradesh", ["LS_Seats", "Reserved_LS_Seats", "Women_Elected_Est_LS"]].tolist() == [80, 27, 3]
    assert p.loc["Bihar", ["Reserved_LS_Seats", "Women_Elected_Est_LS"]].tolist() == [14, 0]
    # a 1-seat state still gets one reserved seat (max(1, ceil(0.33))) and 100% electability elects it
    assert p.loc["Ladakh", ["Reserved_LS_Seats", "Women_Elected_Est_LS"]].tolist() == [1, 1]
    # np.round is half-to-even: 1 reserved seat * 50% = 0.5 rounds to 0, not 1
    assert p.loc["Goa", ["Reserved_LS_Seats", "Women_Elected_Est_LS"]].tolist() == [1, 0]
    assert p.loc["Uttar_Pradesh", "Women_Electability_From_AE"] == 10.0
    assert p.loc["Uttar_Pradesh", "Gender_Gap_AE"] == -2.0
    assert p.loc["Uttar_Pradesh", "AE_Women_Candidates"] == 100
    # displaced incumbents = int(reserved * 0.70), truncated
    assert p["Displaced_Incumbents"].to_dict() == {"Uttar_Pradesh": 18, "Bihar": 9, "Goa": 0, "Ladakh": 0,
                                                   "Daman_&_Diu": 0}


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="05_lok_sabha_placement.py:97 max(1, ...) reserves a seat in a 0-seat state (Daman & Diu)")
def test_zero_seat_state_gets_no_reserved_seat(tree):
    p = _place(tree)
    assert p.loc["Daman_&_Diu", "Reserved_LS_Seats"] == 0


def test_placement_summary_text(tree, capsys):
    _place(tree)
    out = capsys.readouterr().out
    txt = (tree.summary_dir / "lok_sabha_placement_summary.txt").read_text()
    assert txt.strip() in out  # the summary is both printed and written
    assert "- Total seats: 543" in txt
    assert "- Current women: 74 (13.6%)" in txt
    assert "- 33% target: 180 seats" in txt and "- Shortfall: 106 seats" in txt
    assert "- Total reserved seats: 44" in txt  # 27 + 14 + 1 + 1 + 1
    assert "- Estimated women elected: 4" in txt
    assert "- Estimated women %: 0.7%" in txt
    assert "+-70 women" in txt  # 4 - 74 = -70: negative "gain" is printed as-is
    assert "- Estimated displaced MPs: 31 (70% of reserved)" in txt  # round(44 * 0.7) = round(30.8)
    assert "Top affected states: UP (18)" in txt
    # simplified equal carving: 4 women -> 4//3 = 1 off each bloc, the remaining 2 off Others
    assert "- Post-reservation: NDA 291, INDIA 233, Women 4" in txt
    assert "Post-Reservation LS (simplified equal carving):" in out
    assert "  Others: 15 seats" in out and "  Total: 543 seats" in out
    assert "→ NDA remains majority-capable post-reservation" in out
    assert "Top state: Ladakh (100.0%)" in out
    assert "Bottom state (non-zero): Uttar_Pradesh" in out
    assert "Average women's electability (from assembly data): 36.0%" in out


def test_placement_up_displacement_zero_when_up_missing(tree):
    pen = _penalties({"Bihar": 10.0, "Goa": 50.0})
    _place(tree, pen=pen)
    txt = (tree.summary_dir / "lok_sabha_placement_summary.txt").read_text()
    assert "Top affected states: UP (0)," in txt


def test_placement_no_nonzero_electability_prints_na(tree, capsys):
    _place(tree, pen=_penalties({"Bihar": 0.0, "Goa": 0.0}))
    assert "Bottom state (non-zero): N/A" in capsys.readouterr().out


@pytest.mark.parametrize("nda,india,expected", [
    (292, 234, "→ NDA remains majority-capable post-reservation"),
    (200, 340, "→ INDIA becomes majority-capable post-reservation"),
    (272, 234, "→ NDA + Women block could form majority (women as kingmakers)"),
    (100, 272, "→ INDIA + Women block could form majority (women as kingmakers)"),
    (200, 200, "→ Hung parliament likely (significant coalition complexity)"),
])
def test_placement_majority_branches(tree, capsys, nda, india, expected):
    subs = [("nda_seats_current = 292  # NDA alliance", f"nda_seats_current = {nda}  # NDA alliance"),
            ("india_seats_current = 234  # INDIA alliance", f"india_seats_current = {india}  # INDIA alliance")]
    _place(tree, subs=subs)
    out = capsys.readouterr().out
    assert expected in out
    assert sum(1 for line in out.splitlines() if line.startswith("→")) == 1


def test_placement_pivotal_power_line_when_bloc_needs_women(tree):
    # NDA 272 -> 271 after the carving (one short of the 272 quota); with the 4 women it is 275,
    # so the women block is genuinely pivotal.
    subs = [("nda_seats_current = 292  # NDA alliance", "nda_seats_current = 272  # NDA alliance")]
    _place(tree, subs=subs)
    txt = (tree.summary_dir / "lok_sabha_placement_summary.txt").read_text()
    assert 'Women\'s pivotal power: Yes (kingmakers)' in txt


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="05_lok_sabha_placement.py:222 reports women as kingmakers even when NDA alone holds a majority")
def test_not_kingmakers_when_a_bloc_already_has_a_majority(tree):
    _place(tree)  # default: NDA 291 >= 272 after reservation
    txt = (tree.summary_dir / "lok_sabha_placement_summary.txt").read_text()
    assert "Women's pivotal power: No" in txt
