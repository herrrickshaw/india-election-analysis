"""
Secondary check: does a model trained on the MOST RECENT prior election (2014) predict
the NEXT one (2019) better than a model trained on a distant, different-regime era
(1999/2004)? This directly tests whether the original failure was about model quality
or about regime change / recency.
"""
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix
import lightgbm as lgb

FEATURE_COLS = ["Bloc_Retained", "Has_Prev_Result", "Prev_Margin_Pct", "N_Candidates_PC", "Effective_N_Parties"]

def prepare_xy(df, feature_cols, target_col="Bloc"):
    X = df[feature_cols].copy()
    for c in feature_cols:
        X[c] = pd.to_numeric(X[c], errors="coerce")
    X = X.fillna(X.median(numeric_only=True))
    y = df[target_col].copy()
    return X, y

df = pd.read_csv("ga_features.csv")

# RECENT-DATA SPLIT: train on 2009+2014, test on 2019 (same regime era)
train_df = df[df["Year"].isin([2009, 2014])]
test_df = df[df["Year"] == 2019]

X_train, y_train = prepare_xy(train_df, FEATURE_COLS)
X_test, y_test = prepare_xy(test_df, FEATURE_COLS)

le = LabelEncoder()
y_train_enc = le.fit_transform(y_train)
y_test_enc = le.transform(y_test)

majority_class = pd.Series(y_train_enc).mode()[0]
baseline_acc = accuracy_score(y_test_enc, [majority_class]*len(y_test_enc))
print(f"Majority-class baseline (train on 2009+2014, test on 2019): {baseline_acc:.3f}")

models = {
    "Logistic Regression": LogisticRegression(max_iter=1000),
    "Random Forest": RandomForestClassifier(n_estimators=300, max_depth=6, random_state=42, n_jobs=-1),
    "LightGBM": lgb.LGBMClassifier(n_estimators=300, max_depth=5, learning_rate=0.05, random_state=42, verbosity=-1),
}
scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s = scaler.transform(X_test)

results_recent = {}
for name, model in models.items():
    if name == "Logistic Regression":
        model.fit(X_train_s, y_train_enc)
        pred = model.predict(X_test_s)
    else:
        model.fit(X_train, y_train_enc)
        pred = model.predict(X_test)
    acc = accuracy_score(y_test_enc, pred)
    f1 = f1_score(y_test_enc, pred, average="macro")
    results_recent[name] = {"test_accuracy": acc, "test_macro_f1": f1}
    print(f"{name}: test_acc={acc:.3f}  macro_f1={f1:.3f}")

import pickle
with open("recent_split_results.pkl", "wb") as f:
    pickle.dump({"baseline_acc": baseline_acc, "results": results_recent}, f)
print("\nSaved recent_split_results.pkl")
