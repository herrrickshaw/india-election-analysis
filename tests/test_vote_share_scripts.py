"""Characterisation tests for the vote-share-modeling data-prep scripts: 01 PC roll-up,
02 feature engineering, 05 AE bloc trend, 10 continuous bloc vote share. Scripts read relative
paths, so each runs with the working directory switched to tmp_path."""
import numpy as np
import pandas as pd
import pytest

from _runscript import run_script
from _scriptload import load

VS = "vote-share-modeling/scripts"


@pytest.fixture
def cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def run(cwd, name, **kw):
    return run_script(f"{VS}/{name}", cwd / "_runner.py", **kw)


# ---------------------------------------------------------------- 01 roll-up
def _ga_segments():
    cols = ["State_Name", "Year", "PC_No", "PC_Name", "Constituency_No", "Party", "Candidate", "Sex", "Votes"]
    rows = [
        # PC 1: X wins on the SUM across segments although Y leads in segment 1
        ("S", 2019, 1, "Gopalganj", 1, "BJP", "X", "M", 100),
        ("S", 2019, 1, "Gopalganj (SC)", 2, "BJP", "X", "M", 50),
        ("S", 2019, 1, "Gopalganj", 1, "INC", "Y", "F", 120),
        ("S", 2019, 1, "Gopalganj", 2, "INC", "Y", "F", 20),
        ("S", 2019, 1, "Gopalganj", 1, "IND", "Z", None, 5),
        ("S", 2019, 1, "Gopalganj", 1, "NOTA", "NOTA", None, 500),
        # PC 2: single candidate, no runner-up
        ("S", 2019, 2, "Solo", 1, "BJP", "W", "M", 10),
        # PC 3: exact tie
        ("T", 2014, 7, "Tie", 1, "INC", "B", "M", 40),
        ("T", 2014, 7, "Tie", 1, "BJP", "A", "M", 40),
    ]
    return pd.DataFrame(rows, columns=cols)


@pytest.fixture
def rolled(cwd, capsys):
    _ga_segments().to_csv("TCPD_GA_All_States_2026-6-29_csv", index=False)
    run(cwd, "01_rollup_ga_to_pc_level.py")
    w = pd.read_csv("ga_pc_level_winners.csv").set_index(["State_Name", "PC_No"])
    a = pd.read_csv("ga_pc_level_all_candidates.csv")
    return w, a, capsys.readouterr().out


def test_rollup_sums_votes_across_segments_and_picks_pc_winner(rolled):
    w, a, _ = rolled
    x = w.loc[("S", 1)]
    assert (x.Candidate, x.Party, x.Total_Votes, x.N_Segments) == ("X", "BJP", 150, 2)
    assert x.PC_Total_Votes == 295  # 150 + 140 + 5; NOTA's 500 is excluded
    assert (x.RunnerUp_Party, x.RunnerUp_Votes, x.Margin_Votes) == ("INC", 140, 10)
    assert x.Margin_Pct == pytest.approx(10 / 295 * 100)
    assert x.PC_Position == 1 and x.N_Candidates_PC == 3
    # PC_Name is a display label taken from the first occurrence; PC_No is the identity
    assert x.PC_Name == "Gopalganj"
    assert not (a.Party == "NOTA").any()
    y = a[(a.Candidate == "Y")].iloc[0]
    assert y.PC_Position == 2 and y.PC_Vote_Share == pytest.approx(140 / 295 * 100)


def test_rollup_effective_number_of_parties(rolled):
    w, _, _ = rolled
    shares = np.array([150, 140, 5]) / 295
    assert w.loc[("S", 1)].Effective_N_Parties == pytest.approx(1 / (shares ** 2).sum())
    assert w.loc[("S", 2)].Effective_N_Parties == pytest.approx(1.0)


def test_rollup_single_candidate_pc_has_no_runner_up(rolled):
    w, _, _ = rolled
    solo = w.loc[("S", 2)]
    assert solo.Total_Votes == 10 and solo.Margin_Pct != solo.Margin_Pct  # NaN
    assert solo.N_Candidates_PC == 1 and solo.PC_Vote_Share == 100


def test_rollup_tie_goes_to_first_in_party_candidate_order(rolled):
    w, _, _ = rolled
    t = w.loc[("T", 7)]
    assert t.Candidate == "A" and t.Margin_Votes == 0  # BJP sorts before INC; documented tie rule


def test_rollup_reports_counts(rolled):
    _, _, out = rolled
    assert "Excluding 1 NOTA rows before rollup" in out
    assert "Rolled up to candidate-level (within PC): 6 rows" in out
    assert "Total PC-year winner rows: 3" in out
    assert "Duplicate (State,Year,PC_No) winner rows remaining: 0" in out


def test_rollup_zero_vote_pc_has_undefined_enp(cwd):
    cols = ["State_Name", "Year", "PC_No", "PC_Name", "Constituency_No", "Party", "Candidate", "Sex", "Votes"]
    pd.DataFrame([("S", 2019, 9, "Void", 1, "BJP", "A", "M", 0), ("S", 2019, 9, "Void", 1, "INC", "B", "F", 0)],
                 columns=cols).to_csv("TCPD_GA_All_States_2026-6-29_csv", index=False)
    run(cwd, "01_rollup_ga_to_pc_level.py")
    w = pd.read_csv("ga_pc_level_winners.csv")
    assert len(w) == 1 and np.isnan(w.Effective_N_Parties.iloc[0])


def test_rollup_keeps_candidates_with_missing_sex(rolled):
    _, a, _ = rolled
    assert "Z" in set(a.Candidate)  # groupby(dropna=False): a NaN Sex must not drop the candidate


# ---------------------------------------------------------------- 02 feature engineering
FE = load(f"{VS}/02_feature_engineering_discrete.py", "map_bloc", "build_features")


def _winners():
    rows = [  # State_Name, PC_No, Year, Party, Margin_Pct
        ("S", 1, 1999, "BJP", 10.0), ("S", 1, 2004, "BJP", 5.0), ("S", 1, 2009, "INC", 2.0),
        ("S", 1, 2014, "INC", 20.0), ("S", 1, 2019, "BJP", 8.0), ("S", 1, 1996, "XYZ", 1.0),
        ("S", 2, 2004, "BSP", 3.0), ("S", 2, 2009, "AIMIM", 4.0),
        ("T", 1, 2009, "BJP", 6.0),
    ]
    return pd.DataFrame(rows, columns=["State_Name", "PC_No", "Year", "Party", "Margin_Pct"])


def test_build_features_incumbent_retention_and_previous_margin():
    f = FE["build_features"](_winners())
    g = f.set_index(["State_Name", "PC_No", "Year"])
    assert g.loc[("S", 1, 1999), "Prev_Bloc"] == "Other"  # 1996 XYZ maps to Other
    assert g.loc[("S", 1, 1999), "Has_Prev_Result"] == 1 and g.loc[("S", 1, 1999), "Bloc_Retained"] == 0
    assert g.loc[("S", 1, 1996), "Has_Prev_Result"] == 0 and np.isnan(g.loc[("S", 1, 1996), "Prev_Margin_Pct"])
    assert g.loc[("S", 1, 2004), "Bloc_Retained"] == 1 and g.loc[("S", 1, 2004), "Prev_Margin_Pct"] == 10.0
    assert g.loc[("S", 1, 2009), "Bloc_Retained"] == 0 and g.loc[("S", 1, 2009), "Prev_Margin_Pct"] == 5.0
    # BSP -> AIMIM: both Other, so the (Other) bloc is retained
    assert g.loc[("S", 2, 2009), "Bloc_Retained"] == 1
    # previous result is looked up per (State, PC), never across states
    assert g.loc[("T", 1, 2009), "Has_Prev_Result"] == 0


def test_build_features_chronological_split_boundaries():
    f = FE["build_features"](_winners())
    split = f.groupby("Year")["split"].first().to_dict()
    assert split == {1996: "unused", 1999: "train", 2004: "train", 2009: "validation",
                     2014: "test", 2019: "test"}
    assert f["Bloc"].tolist().count("NDA") == 4  # BJP in 1999, 2004, 2019 (S/1) and 2009 (T/1)


def test_build_features_does_not_mutate_input():
    w = _winners()
    before = w.copy()
    FE["build_features"](w)
    pd.testing.assert_frame_equal(w, before)


def test_build_features_output_sorted_by_state_pc_year():
    f = FE["build_features"](_winners().sample(frac=1, random_state=3))
    keys = list(zip(f.State_Name, f.PC_No, f.Year))
    assert keys == sorted(keys)


# ---------------------------------------------------------------- 05 AE bloc trend
def test_ae_trend_counts_winners_by_bloc_and_share(cwd, capsys):
    rows = [  # Year, State_Name, Party, Position
        (1970, "A", "BJS", 1), (1970, "A", "INC(I)", 1), (1970, "A", "INC", 1), (1970, "A", "JNP", 1),
        (1970, "A", "BJP", 2),  # runner-up: ignored
        (1980, "A", "INC", 1), (1980, "B", "INC", 1),  # a year with only INDIA winners
    ]
    pd.DataFrame(rows, columns=["Year", "State_Name", "Party", "Position"]).to_csv(
        "TCPD_AE_All_States_2026-6-29_csv", index=False)
    run(cwd, "05_ae_long_term_trend.py")
    t = pd.read_csv("ae_national_bloc_trend.csv").set_index("Year")
    assert t.loc[1970, ["NDA", "INDIA", "Other", "Total"]].tolist() == [1, 2, 1, 4]
    assert t.loc[1970, "NDA_Share"] == 0.25 and t.loc[1970, "INDIA_Share"] == 0.5
    # missing bloc columns are created as zero
    assert t.loc[1980, ["NDA", "INDIA", "Other", "Total"]].tolist() == [0, 2, 0, 2]
    assert t.loc[1980, "INDIA_Share"] == 1.0 and t.loc[1980, "Other_Share"] == 0.0
    assert "Total AE winner rows: 6" in capsys.readouterr().out


def test_ae_trend_creates_zero_columns_for_blocs_with_no_winners(cwd):
    pd.DataFrame([(1990, "A", "INC", 1)], columns=["Year", "State_Name", "Party", "Position"]).to_csv(
        "TCPD_AE_All_States_2026-6-29_csv", index=False)
    run(cwd, "05_ae_long_term_trend.py")
    t = pd.read_csv("ae_national_bloc_trend.csv").iloc[0]
    assert (t.NDA, t.Other, t.NDA_Share, t.Other_Share) == (0, 0, 0.0, 0.0) and t.INDIA_Share == 1.0


def test_ae_trend_bloc_map_cases():
    ns = load(f"{VS}/05_ae_long_term_trend.py", "map_bloc")
    m = ns["map_bloc"]
    assert (m("BJS"), m("JNS"), m("INC(O)"), m("JD"), m("never-heard-of")) == ("NDA", "NDA", "INDIA", "Other", "Other")


# ---------------------------------------------------------------- 10 continuous vote share
def _candidates():
    cols = ["State_Name", "Year", "PC_No", "PC_Name", "Party", "Total_Votes"]
    rows = [
        ("S", 2019, 1, "P1", "BJP", 50), ("S", 2019, 1, "P1", "INC", 30), ("S", 2019, 1, "P1", "BSP", 8),
        ("S", 2019, 1, "P1", "XYZ", 2), ("S", 2019, 1, "P1", "NOTA", 10),
        ("S", 2019, 2, "P2", "BJP", 100), ("S", 2019, 2, "P2", "TDP", 100),
    ]
    return pd.DataFrame(rows, columns=cols)


def test_continuous_vote_share_pivots_blocs(cwd, capsys):
    _candidates().to_csv("ga_pc_level_all_candidates.csv", index=False)
    run(cwd, "10_build_continuous_vote_share.py")
    w = pd.read_csv("vote_share_continuous.csv").set_index("PC_No")
    # NOTA dropped (denominator 90, not 100); unmapped parties (XYZ) count as Other with BSP
    assert w.loc[1, ["V_NDA", "V_INDIA", "V_Other"]].tolist() == pytest.approx([50 / 90, 30 / 90, 10 / 90])
    assert w.loc[1, "V_sum_check"] == pytest.approx(1.0)
    # PC 2: TDP and BJP are both NDA; no INDIA/Other votes -> zero fill, not NaN
    assert w.loc[2, ["V_NDA", "V_INDIA", "V_Other"]].tolist() == pytest.approx([1.0, 0.0, 0.0])
    assert "Total PC-year rows: 2" in capsys.readouterr().out


def test_continuous_vote_share_adds_missing_bloc_columns(cwd):
    df = _candidates()
    df = df[df.Party.isin(["BJP", "TDP"])]
    df.to_csv("ga_pc_level_all_candidates.csv", index=False)
    run(cwd, "10_build_continuous_vote_share.py")
    w = pd.read_csv("vote_share_continuous.csv")
    assert (w.V_INDIA == 0).all() and (w.V_Other == 0).all() and (w.V_NDA == 1).all()


def test_continuous_vote_share_matches_committed_data_invariants():
    """The committed output should satisfy what the script promises: shares sum to ~1."""
    from _history import pc_shares
    d = pc_shares()
    assert np.allclose(d[["V_NDA", "V_INDIA", "V_Other"]].sum(axis=1), 1.0, atol=1e-6)
