"""Effective number of parties and bloc mapping in the vote-share pipeline."""
import pandas as pd
import pytest

from _scriptload import load

R = load("vote-share-modeling/scripts/01_rollup_ga_to_pc_level.py", "enp")
F = load("vote-share-modeling/scripts/02_feature_engineering_discrete.py", "map_bloc")


def test_enp_laakso_taagepera():
    assert R["enp"](pd.DataFrame({"PC_Vote_Share": [50.0, 50.0]})) == pytest.approx(2.0)
    assert R["enp"](pd.DataFrame({"PC_Vote_Share": [40.0, 30.0, 20.0, 10.0]})) == pytest.approx(1 / 0.30)
    assert R["enp"](pd.DataFrame({"PC_Vote_Share": [100.0, None]})) == pytest.approx(1.0)


def test_map_bloc_defaults_unknown_to_other():
    assert F["map_bloc"]("BJP") == "NDA"
    assert F["map_bloc"]("INC") == "INDIA"
    assert F["map_bloc"]("XYZ") == "Other"
