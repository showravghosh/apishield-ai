import json
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    confusion_matrix, f1_score, precision_score, recall_score)
from catboost import CatBoostClassifier
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_csv("processed/dataset_processed.csv")
feat = json.load(open("processed/feature_columns.json"))
X = df[feat].values
y = (df["label"] != "normal").astype(int).values

X_tr, X_te, y_tr, y_te = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y)
X_b, X_m, y_b, y_m = train_test_split(
    X_tr, y_tr, test_size=0.4, random_state=42, stratify=y_tr)

cb = CatBoostClassifier(iterations=300, depth=8, verbose=False,
                        random_seed=42, auto_class_weights="Balanced")
cb.fit(X_b, y_b)
sup_p = lambda A: cb.predict_proba(A)[:, 1]

iso = IsolationForest(n_estimators=300, random_state=42, n_jobs=-1)
iso.fit(X_b[y_b == 0])
ano_s = lambda A: -iso.score_samples(A)

meta = LogisticRegression(class_weight="balanced", max_iter=1000)
meta.fit(np.column_stack([sup_p(X_m), ano_s(X_m)]), y_m)

Pte, Ate = sup_p(X_te), ano_s(X_te)
ens = meta.predict(np.column_stack([Pte, Ate]))
sup = (Pte >= 0.5).astype(int)
Am = ano_s(X_m)
best_thr, best_f = 0.0, -1.0
for t in np.percentile(Am, np.arange(50, 100, 1)):
    f = f1_score(y_m, (Am >= t).astype(int))
    if f > best_f:
        best_f, best_thr = f, t
ano = (Ate >= best_thr).astype(int)


def report(name, pred):
    f = f1_score(y_te, pred)
    p = precision_score(y_te, pred, zero_division=0)
    r = recall_score(y_te, pred, zero_division=0)
    print(f"  {name:28s} F1 {f:.4f}  Precision {p:.4f}  Recall {r:.4f}")
    return f


print("Binary attack-vs-normal detection (test set):")
f_s = report("Supervised (CatBoost)", sup)
f_a = report("Anomaly (IsolationForest)", ano)
f_e = report("Ensemble (stacked)", ens)

plt.figure(figsize=(6, 5))
names = ["Supervised", "Anomaly", "Ensemble"]
vals = [f_s, f_a, f_e]
plt.bar(names, vals, color=["#3b82f6", "#f59e0b", "#22c55e"])
for i, v in enumerate(vals):
    plt.text(i, v, f"{v:.3f}", ha="center", va="bottom", fontweight="bold")
plt.ylabel("F1 score"); plt.ylim(0, 1.05)
plt.title("Ensemble vs Individual Detectors", fontweight="bold")
plt.tight_layout(); plt.savefig("results/ensemble_comparison.png", dpi=150); plt.close()

cm = confusion_matrix(y_te, ens)
plt.figure(figsize=(5, 4))
sns.heatmap(cm, annot=True, fmt="d", cmap="Greens",
            xticklabels=["normal", "attack"], yticklabels=["normal", "attack"])
plt.title("Ensemble - Attack Detection", fontweight="bold")
plt.ylabel("True"); plt.xlabel("Predicted")
plt.tight_layout(); plt.savefig("results/ensemble_confusion.png", dpi=150); plt.close()

print("\nSaved results/ensemble_comparison.png + ensemble_confusion.png")
