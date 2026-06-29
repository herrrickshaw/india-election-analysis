"""
Hierarchical Bayesian model for continuous vote share V_{p,c}, adapting the core MrP
logic (partial pooling across geographic levels) to our actual data, since we don't have
individual-level survey microdata or census stratification frames as in Cerina & Duch (2021).

Model structure (for NDA vote share, V_NDA):
  V_NDA[c] ~ Normal(mu[c], sigma)
  mu[c] = alpha_national + alpha_state[state(c)] + beta * lag_V_NDA[c]
  alpha_state[s] ~ Normal(0, tau_state)      <- partial-pooling / "borrowing strength"
                                                  step central to MrP: small-N states get
                                                  shrunk toward the national mean
  alpha_national ~ Normal(0.45, 0.15)         <- weakly informative prior
  tau_state ~ HalfNormal(0.1)

This directly addresses the regime-change failure from the earlier discrete classification
attempt: instead of a hard NDA/INDIA/Other LABEL (which flips entirely and unpredictably),
we model continuous vote SHARE, which moves more smoothly and is shrunk toward state-level
patterns -- more robust to a swing year than a classifier's hard boundary.

CHRONOLOGICAL TRAIN/VALIDATION/TEST:
  TRAIN: 1999, 2004  |  VALIDATION: 2009  |  TEST: 2014, 2019
"""
import pandas as pd
import numpy as np
import pymc as pm
import arviz as az
import pickle

df = pd.read_csv("vote_share_continuous.csv")
df = df.sort_values(["State_Name","PC_No","Year"])

df["Lag_V_NDA"] = df.groupby(["State_Name","PC_No"])["V_NDA"].shift(1)
df["Has_Lag"] = df["Lag_V_NDA"].notna().astype(int)

TRAIN_YEARS = [1999, 2004]
VAL_YEARS = [2009]
TEST_YEARS = [2014, 2019]
df["split"] = df["Year"].apply(lambda y: "train" if y in TRAIN_YEARS else ("validation" if y in VAL_YEARS else ("test" if y in TEST_YEARS else "unused")))

model_df = df[df["Has_Lag"] == 1].copy()
print(f"Rows with lag available: {len(model_df)} (out of {len(df)} total)")
print(model_df.groupby("split").size())

train_df = model_df[model_df["split"]=="train"].copy()
val_df = model_df[model_df["split"]=="validation"].copy()
test_df = model_df[model_df["split"]=="test"].copy()

states = sorted(train_df["State_Name"].unique())
state_idx_map = {s: i for i, s in enumerate(states)}
n_states = len(states)
print(f"\nN states in training data: {n_states}")

train_df["state_idx"] = train_df["State_Name"].map(state_idx_map)

print("\nFitting hierarchical Bayesian model (PyMC/NUTS)...")
with pm.Model() as hier_model:
    alpha_national = pm.Normal("alpha_national", mu=0.45, sigma=0.15)
    tau_state = pm.HalfNormal("tau_state", sigma=0.1)
    alpha_state_raw = pm.Normal("alpha_state_raw", mu=0, sigma=1, shape=n_states)
    alpha_state = pm.Deterministic("alpha_state", alpha_state_raw * tau_state)

    beta_lag = pm.Normal("beta_lag", mu=0.5, sigma=0.3)
    sigma = pm.HalfNormal("sigma", sigma=0.15)

    mu = alpha_national + alpha_state[train_df["state_idx"].values] + beta_lag * train_df["Lag_V_NDA"].values
    V_NDA_obs = pm.Normal("V_NDA_obs", mu=mu, sigma=sigma, observed=train_df["V_NDA"].values)

    trace = pm.sample(1000, tune=1000, chains=2, cores=2, random_seed=42, progressbar=True)

print("\nModel fit complete.")
print(az.summary(trace, var_names=["alpha_national", "tau_state", "beta_lag", "sigma"]))

def predict(new_df, trace, state_idx_map, n_states):
    alpha_national_samples = trace.posterior["alpha_national"].values.flatten()
    beta_lag_samples = trace.posterior["beta_lag"].values.flatten()
    alpha_state_samples = trace.posterior["alpha_state"].values.reshape(-1, n_states)

    preds_mean, preds_lower, preds_upper = [], [], []
    for _, row in new_df.iterrows():
        s = row["State_Name"]
        lag = row["Lag_V_NDA"]
        if s in state_idx_map:
            si = state_idx_map[s]
            mu_samples = alpha_national_samples + alpha_state_samples[:, si] + beta_lag_samples * lag
        else:
            mu_samples = alpha_national_samples + beta_lag_samples * lag
        preds_mean.append(np.mean(mu_samples))
        preds_lower.append(np.percentile(mu_samples, 5))
        preds_upper.append(np.percentile(mu_samples, 95))
    return np.array(preds_mean), np.array(preds_lower), np.array(preds_upper)

val_pred, val_lo, val_hi = predict(val_df, trace, state_idx_map, n_states)
test_pred, test_lo, test_hi = predict(test_df, trace, state_idx_map, n_states)

val_mae = np.mean(np.abs(val_df["V_NDA"].values - val_pred))
test_mae = np.mean(np.abs(test_df["V_NDA"].values - test_pred))
val_naive_mae = np.mean(np.abs(val_df["V_NDA"].values - val_df["Lag_V_NDA"].values))
test_naive_mae = np.mean(np.abs(test_df["V_NDA"].values - test_df["Lag_V_NDA"].values))

print(f"\n--- Validation (2009) ---")
print(f"Hierarchical model MAE: {val_mae:.4f}")
print(f"Naive 'no swing' baseline MAE: {val_naive_mae:.4f}")
print(f"\n--- Test (2014, 2019) ---")
print(f"Hierarchical model MAE: {test_mae:.4f}")
print(f"Naive 'no swing' baseline MAE: {test_naive_mae:.4f}")

coverage = np.mean((test_df["V_NDA"].values >= test_lo) & (test_df["V_NDA"].values <= test_hi))
print(f"\n90% credible interval coverage on TEST: {coverage:.1%} (well-calibrated if close to 90%)")

results = {
    "val_mae": val_mae, "test_mae": test_mae,
    "val_naive_mae": val_naive_mae, "test_naive_mae": test_naive_mae,
    "coverage": coverage,
    "val_pred": val_pred, "val_actual": val_df["V_NDA"].values,
    "test_pred": test_pred, "test_actual": test_df["V_NDA"].values,
    "test_lo": test_lo, "test_hi": test_hi,
    "test_states": test_df["State_Name"].values, "test_years": test_df["Year"].values,
    "test_pc_names": test_df["PC_Name"].values,
}
with open("hierarchical_model_results.pkl", "wb") as f:
    pickle.dump(results, f)
trace.to_netcdf("hierarchical_trace.nc")
print("\nSaved hierarchical_model_results.pkl and hierarchical_trace.nc")
