"""Shared helpers for the assumption tests: load the TCPD-derived Lok Sabha data that is
committed in this repo (1999-2019, PC level) and implement the swing / seat-conversion
variants the assumption tests compare. Everything here is read-only and offline."""
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
VSM = ROOT / "vote-share-modeling" / "data"
BLOCS = ["V_NDA", "V_INDIA", "V_Other"]
YEARS = [1999, 2004, 2009, 2014, 2019]

# Same bloc map as vote-share-modeling/scripts/02_feature_engineering_discrete.py and
# 10_build_continuous_vote_share.py (current-alliance membership applied to all years).
from _scriptload import load as _load  # noqa: E402

PARTY_TO_BLOC = _load("vote-share-modeling/scripts/02_feature_engineering_discrete.py")["PARTY_TO_BLOC"]


@lru_cache(maxsize=None)
def pc_shares():
    """PC-year bloc vote shares (V_NDA, V_INDIA, V_Other) -- vote_share_continuous.csv."""
    return pd.read_csv(VSM / "vote_share_continuous.csv")


@lru_cache(maxsize=None)
def winners():
    w = pd.read_csv(VSM / "ga_pc_level_winners.csv")
    w["Bloc"] = w["Party"].map(PARTY_TO_BLOC).fillna("Other")
    return w


def bloc_seats(year):
    """Seats won per bloc in `year`, by the winning candidate's party bloc."""
    return winners().query("Year == @year")["Bloc"].value_counts().to_dict()


def paired(y0, y1):
    """PCs present in both elections (same State_Name + PC_No), shares for both years."""
    v = pc_shares()
    a = v[v.Year == y0].set_index(["State_Name", "PC_No"])[BLOCS]
    b = v[v.Year == y1].set_index(["State_Name", "PC_No"])[BLOCS]
    idx = a.index.intersection(b.index)
    return a.loc[idx], b.loc[idx]


def _renorm(x):
    x = x.clip(lower=0)
    return x.div(x.sum(axis=1), axis=0)


def swing_predict(v0, v1, method, level="state"):
    """Predict year-1 PC shares from year-0 shares using the REALISED aggregate swing
    (oracle swing), so only the vote->seat conversion rule is being tested.

    method: "uniform" (additive: v0 + d) or "proportional" (multiplicative: v0 * r).
    level:  "state" (swing measured per state) or "national".
    """
    if level == "state":
        g0 = v0.groupby(level="State_Name").transform("mean")
        g1 = v1.groupby(level="State_Name").transform("mean")
    else:
        g0 = pd.DataFrame(np.tile(v0.mean().values, (len(v0), 1)), index=v0.index, columns=BLOCS)
        g1 = pd.DataFrame(np.tile(v1.mean().values, (len(v1), 1)), index=v1.index, columns=BLOCS)
    if method == "uniform":
        pred = v0 + (g1 - g0)
    elif method == "proportional":
        pred = v0 * (g1 / g0.where(g0 > 0)).fillna(1.0)
    else:
        raise ValueError(method)
    return _renorm(pred)


def seats_from_shares(v):
    """FPTP on the three blocs: winner = argmax share."""
    return v.idxmax(axis=1).value_counts().reindex(BLOCS, fill_value=0)


def swing_seat_error(y0, y1, method, level="state"):
    """Total absolute seat error summed over the three blocs, plus PC-winner accuracy,
    against the bloc-argmax of the realised year-1 shares."""
    v0, v1 = paired(y0, y1)
    pred = swing_predict(v0, v1, method, level)
    err = int((seats_from_shares(pred) - seats_from_shares(v1)).abs().sum())
    acc = float((pred.idxmax(axis=1) == v1.idxmax(axis=1)).mean())
    return err, acc


def state_swings(y0, y1, col="V_NDA"):
    v0, v1 = paired(y0, y1)
    return (v1[col] - v0[col]).groupby(level="State_Name").mean()


def implied_dirichlet_concentration(min_pcs=5):
    """Method-of-moments Dirichlet concentration from WITHIN state-year dispersion of
    V_NDA: Var = m(1-m)/(c+1)  =>  c = m(1-m)/Var - 1.  Returns per-state-year values."""
    v = pc_shares()
    out = []
    for (_, _), g in v.groupby(["State_Name", "Year"]):
        if len(g) < min_pcs:
            continue
        m, var = g["V_NDA"].mean(), g["V_NDA"].var(ddof=1)
        if var > 0 and 0.05 < m < 0.95:
            out.append(m * (1 - m) / var - 1)
    return np.array(out)


def simulate_seats(rng, state_means, state_seats, n_sims, conc=18.0,
                   national_sd=0.0, state_sd=0.0, n_seats=None):
    """Seat-conversion engine of seat-bias-analysis/scripts/01 (Dirichlet per seat around a
    state mean, FPTP argmax over 3 blocs, alpha clipped at 0.3), vectorised and extended
    with an optional correlated swing: each simulation draws ONE national NDA-vs-INDIA
    shock (sd `national_sd`) plus independent per-state shocks (sd `state_sd`), added to
    NDA and subtracted from INDIA before the per-seat Dirichlet draw.
    With national_sd = state_sd = 0 this is exactly the original (independent) model.
    n_seats=None keeps each state's real seat count; an integer reproduces the scripts'
    random seat-to-state assignment for a house of that size.
    Returns an (n_sims, 3) array of seat counts [NDA, INDIA, Other]."""
    state_means = np.asarray(state_means, float)
    state_seats = np.asarray(state_seats, int)
    seat_state = np.repeat(np.arange(len(state_seats)), state_seats)
    out = np.empty((n_sims, 3), int)
    for s in range(n_sims):
        m = state_means
        if national_sd or state_sd:
            shock = rng.normal(0, national_sd) + rng.normal(0, state_sd, len(m))
            m = m.copy()
            m[:, 0] = m[:, 0] + shock
            m[:, 1] = m[:, 1] - shock
            m = np.clip(m, 0.005, None)
            m = m / m.sum(axis=1, keepdims=True)
        if n_seats is not None:  # the scripts' way: each seat assigned to a state at random
            seat_state = rng.choice(len(state_seats), size=n_seats, p=state_seats / state_seats.sum())
        alpha = np.clip(m[seat_state] * conc, 0.3, None)
        g = rng.standard_gamma(alpha)
        winners_ = np.argmax(g, axis=1)  # argmax of g == argmax of g / g.sum()
        out[s] = np.bincount(winners_, minlength=3)
    return out


def state_mean_shares(year):
    """Per-state mean bloc vote shares and PC counts for `year` (vote_share_continuous)."""
    v = pc_shares().query("Year == @year")
    g = v.groupby("State_Name")
    return g[BLOCS].mean(), g.size()
