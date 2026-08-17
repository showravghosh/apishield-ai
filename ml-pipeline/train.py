import os
import json
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report,
)
from sklearn.preprocessing import label_binarize
from catboost import CatBoostClassifier
import joblib

DATA = "processed/dataset_processed.csv"
MODEL_DIR = "models"
os.makedirs(MODEL_DIR, exist_ok=True)


def false_positive_rate(cm, labels, normal_label="normal"):
    idx = labels.index(normal_label)
    tn = cm[idx, idx]
    fp = cm[idx, :].sum() - tn
    return fp / (fp + tn) if (fp + tn) > 0 else 0.0


def evaluate(name, model, X_test, y_test, labels, proba=None):
    preds = model.predict(X_test)
    preds = np.array(preds).ravel()
    acc = accuracy_score(y_test, preds)
    prec = precision_score(y_test, preds, average="macro", zero_division=0)
    rec = recall_score(y_test, preds, average="macro", zero_division=0)
    f1 = f1_score(y_test, preds, average="macro", zero_division=0)

    auc = None
    if proba is not None:
        y_bin = label_binarize(y_test, classes=labels)
        try:
            auc = roc_auc_score(y_bin, proba, average="macro", multi_class="ovr")
        except Exception:
            auc = None

    cm = confusion_matrix(y_test, preds, labels=labels)
    fpr = false_positive_rate(cm, labels)

    print("\n" + "=" * 55)
    print(f"MODEL: {name}")
    print("=" * 55)
    print(f"Accuracy       : {acc:.4f}")
    print(f"Precision(macro): {prec:.4f}")
    print(f"Recall(macro)  : {rec:.4f}")
    print(f"F1(macro)      : {f1:.4f}")
    if auc is not None:
        print(f"ROC-AUC(macro) : {auc:.4f}")
    print(f"False Pos Rate : {fpr:.4f}")
    print("\nPer-class report:")
    print(classification_report(y_test, preds, labels=labels, zero_division=0))
    print("Confusion matrix (rows=true, cols=pred):")
    print("labels:", labels)
    print(cm)
    return f1


def main():
    df = pd.read_csv(DATA)
    with open("processed/feature_columns.json") as f:
        feature_cols = json.load(f)

    X = df[feature_cols]
    y = df["label"]
    labels = sorted(y.unique().tolist())

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print("Train:", len(X_train), "Test:", len(X_test))

    # Random Forest
    rf = RandomForestClassifier(
        n_estimators=300, max_depth=None, class_weight="balanced",
        random_state=42, n_jobs=-1,
    )
    rf.fit(X_train, y_train)
    rf_f1 = evaluate("Random Forest", rf, X_test, y_test, labels,
                     proba=rf.predict_proba(X_test))

    # CatBoost
    cb = CatBoostClassifier(
        iterations=400, depth=8, learning_rate=0.1,
        loss_function="MultiClass", auto_class_weights="Balanced",
        random_seed=42, verbose=False,
    )
    cb.fit(X_train, y_train)
    cb_f1 = evaluate("CatBoost", cb, X_test, y_test, labels,
                     proba=cb.predict_proba(X_test))

    # Save both + mark best
    joblib.dump(rf, os.path.join(MODEL_DIR, "random_forest.pkl"))
    cb.save_model(os.path.join(MODEL_DIR, "catboost.cbm"))

    best = "CatBoost" if cb_f1 >= rf_f1 else "Random Forest"
    with open(os.path.join(MODEL_DIR, "summary.json"), "w") as f:
        json.dump({
            "random_forest_f1_macro": rf_f1,
            "catboost_f1_macro": cb_f1,
            "best_model": best,
            "labels": labels,
        }, f, indent=2)

    print("\n" + "=" * 55)
    print(f"BEST MODEL: {best}")
    print("Models saved to", MODEL_DIR)
    print("=" * 55)


if __name__ == "__main__":
    main()
