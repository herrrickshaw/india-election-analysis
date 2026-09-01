"""
Train/validation/test pipeline on REAL TCPD Lok Sabha PC-level data (1999-2019, rolled
up from AC-segment data). Predicts which BLOC (NDA/INDIA/Other) wins each constituency.
"""
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix, classification_report
import lightgbm as lgb
import pickle

FEATURE_COLS = ["Bloc_Retained", "Has_Prev_Result", "Prev_Margin_Pct", "N_Candidates_PC", "Effective_N_Parties"]

def prepare_xy(df, feature_cols, target_col="Bloc"):
    X = df[feature_cols].copy()
    for c in feature_cols:
        X[c] = pd.to_numeric(X[c], errors="coerce")
    X = X.fillna(X.median(numeric_only=True))
    y = df[target_col].copy()
    return X, y

def run():
    df = pd.read_csv("ga_features.csv")
    train_df = df[df["split"]=="train"]
    val_df = df[df["split"]=="validation"]
    test_df = df[df["split"]=="test"]
    print(f"Train: {len(train_df)} | Val: {len(val_df)} | Test: {len(test_df)}")

    X_train, y_train = prepare_xy(train_df, FEATURE_COLS)
    X_val, y_val = prepare_xy(val_df, FEATURE_COLS)
    X_test, y_test = prepare_xy(test_df, FEATURE_COLS)

    le = LabelEncoder()
    y_train_enc = le.fit_transform(y_train)
    y_val_enc = le.transform(y_val)
    y_test_enc = le.transform(y_test)

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_val_s = scaler.transform(X_val)
    X_test_s = scaler.transform(X_test)

    # Baseline: majority-class predictor (predicts the most common bloc every time) --
    # ESSENTIAL sanity check; any real model must beat this to be useful.
    majority_class = pd.Series(y_train_enc).mode()[0]
    baseline_val_acc = accuracy_score(y_val_enc, [majority_class]*len(y_val_enc))
    baseline_test_acc = accuracy_score(y_test_enc, [majority_class]*len(y_test_enc))
    print(f"\nMAJORITY-CLASS BASELINE: val_acc={baseline_val_acc:.3f}  test_acc={baseline_test_acc:.3f}")
    print("(any model below this is worse than just always guessing the most common bloc)")

    models = {
        "Logistic Regression": LogisticRegression(max_iter=1000),
        "Random Forest": RandomForestClassifier(n_estimators=300, max_depth=6, random_state=42, n_jobs=-1),
        "LightGBM": lgb.LGBMClassifier(n_estimators=300, max_depth=5, learning_rate=0.05, random_state=42, verbosity=-1),
    }

    results = {}
    for name, model in models.items():
        if name == "Logistic Regression":
            model.fit(X_train_s, y_train_enc)
            val_pred = model.predict(X_val_s)
            test_pred = model.predict(X_test_s)
        else:
            model.fit(X_train, y_train_enc)
            val_pred = model.predict(X_val)
            test_pred = model.predict(X_test)

        val_acc = accuracy_score(y_val_enc, val_pred)
        val_f1 = f1_score(y_val_enc, val_pred, average="macro")
        test_acc = accuracy_score(y_test_enc, test_pred)
        test_f1 = f1_score(y_test_enc, test_pred, average="macro")

        results[name] = {
            "val_accuracy": val_acc, "val_macro_f1": val_f1,
            "test_accuracy": test_acc, "test_macro_f1": test_f1,
            "val_confusion": confusion_matrix(y_val_enc, val_pred).tolist(),
            "test_confusion": confusion_matrix(y_test_enc, test_pred).tolist(),
            "classes": le.classes_.tolist(),
        }
        print(f"\n{name}")
        print(f"  Validation: acc={val_acc:.3f}  macro-F1={val_f1:.3f}")
        print(f"  Test:       acc={test_acc:.3f}  macro-F1={test_f1:.3f}")
        print(f"  Test confusion matrix (rows=actual, cols=predicted), classes={list(le.classes_)}:")
        print(confusion_matrix(y_test_enc, test_pred))

    summary = {
        "results": results, "label_encoder_classes": le.classes_.tolist(),
        "baseline_val_acc": baseline_val_acc, "baseline_test_acc": baseline_test_acc,
        "feature_cols": FEATURE_COLS,
    }
    with open("model_results_real.pkl", "wb") as f:
        pickle.dump(summary, f)
    print("\nSaved model_results_real.pkl")
    return summary

if __name__ == "__main__":
    run()
