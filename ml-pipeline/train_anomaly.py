import os
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split
import joblib

DATA = "processed/dataset_processed.csv"
MODEL_DIR = "models"
RES_DIR = "results"
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(RES_DIR, exist_ok=True)
sns.set_theme(style="whitegrid")


def main():
    df = pd.read_csv(DATA)
    with open("processed/feature_columns.json") as f:
        feature_cols = json.load(f)

    normal = df[df["label"] == "normal"]
    attack = df[df["label"] != "normal"]

    Xn_train, Xn_test = train_test_split(
        normal[feature_cols], test_size=0.3, random_state=42)

    model = IsolationForest(n_estimators=300, random_state=42, n_jobs=-1)
    model.fit(Xn_train)

    sn = model.score_samples(Xn_test)

    results = {}
    for fpr in [0.05, 0.10]:
        thr = np.percentile(sn, fpr * 100)
        row = {}
        for lab in sorted(attack["label"].unique()):
            sub = attack[attack["label"] == lab][feature_cols]
            sc = model.score_samples(sub)
            row[lab] = round(float(np.mean(sc < thr)), 3)
        all_atk = model.score_samples(attack[feature_cols])
        row["OVERALL"] = round(float(np.mean(all_atk < thr)), 3)
        results[f"FPR_{int(fpr*100)}pct"] = row

    print("Isolation Forest (trained on NORMAL only) - zero-day detection")
    for k, row in results.items():
        print("\n" + k)
        for lab, v in row.items():
            print(f"  {lab:15s} {v*100:.1f}%")

    row10 = results["FPR_10pct"]
    plot_labels = [k for k in row10 if k != "OVERALL"]
    plt.figure(figsize=(8, 5))
    sns.barplot(x=plot_labels, y=[row10[k] * 100 for k in plot_labels],
                hue=plot_labels, palette="rocket", legend=False)
    plt.title("Zero-day Detection Rate by Attack (10% FPR)", fontweight="bold")
    plt.ylabel("Detection rate (%)"); plt.ylim(0, 100)
    plt.tight_layout()
    plt.savefig(os.path.join(RES_DIR, "anomaly_detection_rate.png"), dpi=150)
    plt.close()

    joblib.dump(model, os.path.join(MODEL_DIR, "isolation_forest.pkl"))
    with open(os.path.join(RES_DIR, "anomaly_summary.json"), "w") as f:
        json.dump(results, f, indent=2)
    print("\nSaved model + chart.")


if __name__ == "__main__":
    main()
