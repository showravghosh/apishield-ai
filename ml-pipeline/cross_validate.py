import json
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, accuracy_score
from catboost import CatBoostClassifier
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

df = pd.read_csv("processed/dataset_processed.csv")
feat = json.load(open("processed/feature_columns.json"))
X = df[feat].values
y = df["label"].astype(str).to_numpy(dtype=object)

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)


def run(name, make_model):
    accs, f1s = [], []
    for k, (tr, te) in enumerate(skf.split(X, y)):
        m = make_model()
        m.fit(X[tr], y[tr])
        p = np.array(m.predict(X[te])).ravel()
        accs.append(accuracy_score(y[te], p))
        f1s.append(f1_score(y[te], p, average="macro"))
        print(f"  {name} fold {k+1}: acc {accs[-1]:.4f}  F1 {f1s[-1]:.4f}")
    a, sa = np.mean(accs), np.std(accs)
    f, sf = np.mean(f1s), np.std(f1s)
    print(f"  {name} => Accuracy {a:.4f} +/- {sa:.4f} | F1 {f:.4f} +/- {sf:.4f}\n")
    return f, sf


print("5-fold Stratified Cross-Validation:\n")
rf_f, rf_s = run("RandomForest",
                 lambda: RandomForestClassifier(n_estimators=300, class_weight="balanced",
                                                random_state=42, n_jobs=-1))
cb_f, cb_s = run("CatBoost",
                 lambda: CatBoostClassifier(iterations=400, depth=8, learning_rate=0.1,
                                            loss_function="MultiClass",
                                            auto_class_weights="Balanced",
                                            random_seed=42, verbose=False))

plt.figure(figsize=(6, 5))
names = ["RandomForest", "CatBoost"]
means = [rf_f, cb_f]
errs = [1.96 * rf_s, 1.96 * cb_s]
plt.bar(names, means, yerr=errs, capsize=8, color=["#3b82f6", "#22c55e"])
for i, v in enumerate(means):
    plt.text(i, v, f"{v:.3f}", ha="center", va="bottom", fontweight="bold")
plt.ylabel("Macro F1 (5-fold)"); plt.ylim(0, 1.05)
plt.title("5-Fold Cross-Validation (95% CI)", fontweight="bold")
plt.tight_layout(); plt.savefig("results/cross_validation.png", dpi=150)
print("Saved results/cross_validation.png")
