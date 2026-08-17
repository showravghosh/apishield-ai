import json
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report,
)

DATA = "processed/dataset_processed.csv"

LEAKY = [
    "sess_req_count", "sess_fail_ratio", "sess_unique_endpoints",
    "sess_duration", "sess_req_per_sec", "ip_req_count", "ip_unique_sessions",
]


def main():
    df = pd.read_csv(DATA)
    with open("processed/feature_columns.json") as f:
        feature_cols = json.load(f)

    kept = [c for c in feature_cols if c not in LEAKY]
    print("Dropped leaky features:", LEAKY)
    print("Kept features:", kept)

    X = df[kept]
    y = df["label"]
    labels = sorted(y.unique().tolist())

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    rf = RandomForestClassifier(
        n_estimators=300, class_weight="balanced", random_state=42, n_jobs=-1
    )
    rf.fit(X_train, y_train)
    preds = rf.predict(X_test)

    print("\n" + "=" * 55)
    print("Random Forest (leaky features removed)")
    print("=" * 55)
    print(f"Accuracy       : {accuracy_score(y_test, preds):.4f}")
    print(f"Precision(macro): {precision_score(y_test, preds, average='macro', zero_division=0):.4f}")
    print(f"Recall(macro)  : {recall_score(y_test, preds, average='macro', zero_division=0):.4f}")
    print(f"F1(macro)      : {f1_score(y_test, preds, average='macro', zero_division=0):.4f}")
    print("\nPer-class report:")
    print(classification_report(y_test, preds, labels=labels, zero_division=0))
    print("Confusion matrix (rows=true, cols=pred):")
    print("labels:", labels)
    print(confusion_matrix(y_test, preds, labels=labels))

    print("\nFeature importance:")
    imp = sorted(zip(kept, rf.feature_importances_), key=lambda x: -x[1])
    for name, val in imp:
        print(f"  {name:20s} {val:.4f}")


if __name__ == "__main__":
    main()
