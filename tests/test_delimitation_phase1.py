"""Characterisation tests for the straight-line delimitation stages 01 (women candidacy),
02 (electability model), 05a (Lok Sabha analysis) and 05b (Lok Sabha placement).

Each stage is executed end to end against small synthetic TCPD-shaped frames in a fake repo
tree under tmp_path (see _runscript.py); outputs are read back from tmp_path."""
import gzip
import pickle
import shutil

import numpy as np
import pandas as pd
import pytest

from _runscript import ROOT, run_script

DO = "scripts/delimitation-optimization"


@pytest.fixture
def tree(tmp_path):
    d = tmp_path / "scripts" / "delimitation-optimization"
    d.mkdir(parents=True)
    shutil.copy(ROOT / DO / "sexcode.py", d / "sexcode.py")
    (tmp_path / "data" / "raw").mkdir(parents=True)
    (tmp_path / "data" / "processed").mkdir(parents=True)
    (tmp_path / "coalition-game-theory" / "output").mkdir(parents=True)

    class T:
        root = tmp_path
        raw = tmp_path / "data" / "raw"
        out = tmp_path / "data" / "processed"
        summary_dir = tmp_path / "coalition-game-theory" / "output"

        def fake(self, script):
            # Only the *directory* matters (scripts derive REPO_ROOT from it). The basename must
            # differ from the script's own: coverage then attributes the exec'd code to the repo file.
            return d / "_runner.py"

        def write_gz(self, name, df):
            with gzip.open(self.raw / name, "wt") as f:
                df.to_csv(f, index=False)

    return T()


# ---------------------------------------------------------------- 01 parse women candidacy
def _ae_small():
    rows = [
        # State, Constituency, Sex, Position, Incumbent, Electors, Turnout
        ("S1", "C1", "F", 1, True, 1000, 70.0),
        ("S1", "C1", "M", 2, False, 1000, 70.0),
        ("S1", "C1", "M", 3, False, 1000, 70.0),
        ("S1", "C1", None, 4, False, 1000, 70.0),
        ("S1", "C2", "M", 1, True, 2000, 60.0),
        ("S1", "C2", "F", 2, False, 2000, 60.0),
        ("S1", "C2", "FEMALE", 3, False, 2000, 60.0),
        ("S2", "C1", "M", 1, True, 3000, 50.0),
        ("S2", "C1", "M", 2, False, 3000, 50.0),
        ("S2", "C2", "M", 1, False, 4000, 40.0),
        ("S2", "C2", "M", 2, False, 4000, 40.0),
    ]
    return pd.DataFrame(rows, columns=["State_Name", "Constituency_Name", "Sex", "Position",
                                       "Incumbent", "Electors", "Turnout_Percentage"]).assign(Year=2019)


def test_parse_women_candidacy_state_and_constituency_tables(tree, capsys):
    tree.write_gz("TCPD_AE_All_States_2026-6-29.csv.gz", _ae_small())
    run_script(f"{DO}/01_parse_women_candidacy.py", tree.fake("01_parse_women_candidacy.py"))

    st = pd.read_csv(tree.out / "women_candidacy_by_state.csv").set_index("State")
    s1, s2 = st.loc["S1"], st.loc["S2"]
    # S1: 7 candidates, 3 women ('F', 'F', 'FEMALE'); 1 woman winner; 1 woman incumbent
    assert (s1.Total_Candidates, s1.Women_Candidates, s1.Women_Winners, s1.Women_Incumbents) == (7, 3, 1, 1)
    assert s1.Women_Candidacy_Pct == pytest.approx(300 / 7)
    assert s1.Women_Win_Pct == pytest.approx(100 / 3)
    assert s1.Women_Incumbent_Pct == pytest.approx(100 / 3)
    assert s1.Overall_Win_Pct == pytest.approx(200 / 7)
    assert s1.Win_Rate_Gap == pytest.approx(100 / 3 - 200 / 7)
    # S2 has no women: every women-rate is exactly 0 (no division by zero), gap = -overall
    assert (s2.Women_Candidates, s2.Women_Candidacy_Pct, s2.Women_Win_Pct, s2.Women_Incumbent_Pct) == (0, 0, 0, 0)
    assert s2.Overall_Win_Pct == pytest.approx(50.0)
    assert s2.Win_Rate_Gap == pytest.approx(-50.0)
    # sorted by Women_Win_Pct descending
    assert list(st.index) == ["S1", "S2"]

    ct = pd.read_csv(tree.out / "women_candidacy_by_constituency.csv")
    got = {(r.State, r.Constituency): (r.Women_Candidates, bool(r.Women_Won), r.Total_Candidates,
                                       r.Electors, r.Turnout_Pct) for r in ct.itertuples()}
    assert got == {
        ("S1", "C1"): (1, True, 4, 1000, 70.0),
        ("S1", "C2"): (2, False, 3, 2000, 60.0),
        ("S2", "C1"): (0, False, 2, 3000, 50.0),
        ("S2", "C2"): (0, False, 2, 4000, 40.0),
    }
    c11 = ct[(ct.State == "S1") & (ct.Constituency == "C1")].iloc[0]
    assert c11.Women_Candidacy_Pct == pytest.approx(25.0)


def test_parse_women_candidacy_summary_file(tree, capsys):
    tree.write_gz("TCPD_AE_All_States_2026-6-29.csv.gz", _ae_small())
    run_script(f"{DO}/01_parse_women_candidacy.py", tree.fake("01_parse_women_candidacy.py"))
    s = pd.read_csv(tree.out / "women_candidacy_summary.csv").iloc[0]
    assert s.Total_Assembly_Elections_Candidates == 11
    assert s.Total_Women_Candidates == 3
    assert s.Women_Candidacy_Rate_Pct == pytest.approx(300 / 11)
    assert s.Total_Women_Winners == 1
    assert s.Overall_Women_Win_Rate_Pct == pytest.approx(100 / 3)
    assert s.Constituencies_With_Women_Winners == 1
    assert s.Total_Constituencies == 4
    assert s.States_Analyzed == 2
    out = capsys.readouterr().out
    # *_Pct keys print with a percent sign, the others with thousands separators
    assert "Women_Candidacy_Rate_Pct: 27.3%" in out
    assert "Total_Women_Candidates: 3" in out
    assert "Phase 1 complete" in out


# ---------------------------------------------------------------- 02 electability model
def _ae_model():
    rng = np.random.default_rng(0)
    rows = []
    # A, B: 6 constituencies x 6 candidates, one winner per constituency, mixed sex/incumbency
    for state in ("A", "B"):
        for c in range(6):
            for k in range(6):
                rows.append((state, f"{state}c{c}", "F" if (k + c) % 3 == 0 else "M",
                             k + 1, bool((k + c) % 2 == 0) if k < 5 else None,
                             "SC" if c == 0 else (None if c == 1 else "GEN"),
                             float(60 + rng.integers(0, 10)) if k < 5 else np.nan,
                             "BJP" if k == 0 else ("INC" if k == 1 else "ZZZ")))
    # TINY: 6 rows -> state fit skipped (<20 rows) but constituency kept (>=5 rows)
    for k in range(6):
        rows.append(("TINY", "Tc0", "F" if k == 0 else "M", k + 1, False, "GEN", 55.0, "BJP"))
    # ONECLASS: 24 rows, nobody wins -> per-state logistic fit raises -> that state is skipped
    for c in range(6):
        for k in range(4):
            rows.append(("ONECLASS", f"Oc{c}", "F" if k == 0 else "M", k + 2, False, "GEN", 50.0, "INC"))
    # a constituency with <5 rows is ignored in Model 3
    rows.append(("A", "lonely", "M", 1, False, "GEN", 60.0, "BJP"))
    return pd.DataFrame(rows, columns=["State_Name", "Constituency_Name", "Sex", "Position", "Incumbent",
                                       "Constituency_Type", "Turnout_Percentage", "Party"])


def test_fit_electability_model_outputs(tree, capsys):
    tree.write_gz("TCPD_AE_All_States_2026-6-29.csv.gz", _ae_model())
    run_script(f"{DO}/02_fit_electability_model.py", tree.fake("02_fit_electability_model.py"))
    err = capsys.readouterr().err

    pen = pd.read_csv(tree.out / "state_gender_penalties.csv")
    # TINY (<20 rows) is skipped silently; ONECLASS fails the fit and is reported on stderr
    assert sorted(pen.State) == ["A", "B"]
    assert "skipping ONECLASS" in err and "skipping TINY" not in err
    # sorted ascending by the empirical gap
    assert list(pen.Empirical_Gap_Pct) == sorted(pen.Empirical_Gap_Pct)
    a = pen.set_index("State").loc["A"]
    assert a.Total_Candidates == 37 and a.Women_Candidates == 12
    # empirical win rates: women are k in {0,..}: recompute by brute force
    df = _ae_model()
    da = df[df.State_Name == "A"]
    exp_w = ((da.Sex == "F") & (da.Position == 1)).sum() / (da.Sex == "F").sum() * 100
    exp_m = ((da.Sex == "M") & (da.Position == 1)).sum() / (da.Sex == "M").sum() * 100
    assert a.Women_Win_Rate_Pct == pytest.approx(exp_w)
    assert a.Men_Win_Rate_Pct == pytest.approx(exp_m)
    assert a.Empirical_Gap_Pct == pytest.approx(exp_w - exp_m)

    pot = pd.read_csv(tree.out / "constituency_win_potential.csv")
    # one row per constituency with >=5 candidates: 12 (A,B) + 1 (TINY); the 4-row ONECLASS
    # constituencies and the 1-row 'lonely' one are dropped
    assert len(pot) == 13 and not ({"lonely", "Oc0"} & set(pot.Constituency))
    assert pot.Predicted_Gender_Gap.eq(pot.Predicted_Man_Win_Prob - pot.Predicted_Woman_Win_Prob).all()
    np.testing.assert_allclose(pot.Potential_Score,
                               (1 - pot.Predicted_Gender_Gap) * pot.Predicted_Woman_Win_Prob * 100)
    row = pot[pot.Constituency == "Tc0"].iloc[0]
    assert (row.Women_Fielded, row.Total_Candidates, row.Const_Type) == (1, 6, "GEN")
    assert row.Empirical_Women_Win_Rate == 1.0 and row.Empirical_Men_Win_Rate == 0.0  # the one woman won
    assert pot[pot.Constituency == "Ac0"].iloc[0].Const_Type == "SC"
    assert pot[pot.Constituency == "Ac1"].iloc[0].Const_Type == "GEN"  # NaN type -> GEN

    # pickled model carries the encoders and feature names
    with open(tree.out / "electability_model.pkl", "rb") as f:
        bundle = pickle.load(f)
    assert bundle["feature_names"] == ["Female", "Incumbent", "Const_Type", "Turnout", "Bloc", "State"]
    assert list(bundle["le_bloc"].classes_) == ["INDIA", "NDA", "Other"]
    assert list(bundle["le_const"].classes_) == ["GEN", "SC"]
    assert bundle["log_reg"].coef_.shape == (1, 6)


def test_fit_electability_model_missing_turnout_filled_with_median(tree):
    df = _ae_model()
    tree.write_gz("TCPD_AE_All_States_2026-6-29.csv.gz", df)
    ns = run_script(f"{DO}/02_fit_electability_model.py", tree.fake("02_fit_electability_model.py"))
    med = df["Turnout_Percentage"].median()
    filled = ns["df"].loc[df["Turnout_Percentage"].isna().to_numpy(), "Turnout_Normalized"]
    assert len(filled) > 0 and (filled == med).all()
    # bloc map: BJP -> NDA, INC -> INDIA, everything else Other (BJD is in both sets: NDA wins)
    assert set(ns["df"].groupby("Party")["Bloc"].first().to_dict().items()) == {
        ("BJP", "NDA"), ("INC", "INDIA"), ("ZZZ", "Other")}
