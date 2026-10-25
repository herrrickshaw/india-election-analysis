"""TCPD codes candidate sex as 'M' / 'F' / 'O' (some exports spell out 'FEMALE').
Comparing against 'FEMALE' alone silently drops almost every woman candidate."""
import pandas as pd

FEMALE_CODES = {"F", "FEMALE"}


def is_female(sex):
    """Boolean Series: True where the TCPD Sex value denotes a woman candidate."""
    return pd.Series(sex).astype("string").str.strip().str.upper().isin(FEMALE_CODES).fillna(False).astype(bool)
