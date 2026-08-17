import os
import json
import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import shap

os.makedirs("results", exist_ok=True)
df = pd.read_csv("processed/dataset_processed.csv")
feat = json.load(open("processed/feature_columns.json"))
rf = joblib.load("models/random_forest.pkl")
classes = list(rf.classes_)
X = df[feat]

explainer = shap.TreeExplainer(rf)


def to_list(sv, ncls):
    if isinstance(sv, list):
        return sv
    arr = np.asarray(sv)
    if arr.ndim == 3:
        return [arr[:, :, k] for k in range(arr.shape[2])]
    return [arr]


Xs = X.sample(n=min(400, len(X)), random_state=0).reset_index(drop=True)
sv_list = to_list(explainer.shap_values(Xs), len(classes))
mean_abs = np.mean([np.abs(s).mean(axis=0) for s in sv_list], axis=0)
order = np.argsort(mean_abs)[-14:]
plt.figure(figsize=(8, 6))
plt.barh([feat[j] for j in order], mean_abs[order], color="#3b82f6")
plt.title("SHAP global feature importance (Random Forest)", fontweight="bold")
plt.xlabel("mean |SHAP value|")
plt.tight_layout(); plt.savefig("results/shap_summary.png", dpi=150); plt.close()
print("saved results/shap_summary.png")

for lab in ["sql_injection", "bola", "api_flooding", "credential_stuffing", "token_replay"]:
    sub = df[df["label"] == lab]
    if len(sub) == 0:
        continue
    row = sub[feat].iloc[[0]].reset_index(drop=True)
    svr = to_list(explainer.shap_values(row), len(classes))
    c = classes.index(lab)
    contrib = svr[c][0]
    order = np.argsort(np.abs(contrib))[-8:]
    cols = ["#ef4444" if contrib[j] > 0 else "#3b82f6" for j in order]
    plt.figure(figsize=(7, 4))
    plt.barh([feat[j] for j in order], contrib[order], color=cols)
    plt.title(f"Why flagged as '{lab}'", fontweight="bold")
    plt.xlabel("SHAP value  (red -> pushes toward this attack)")
    plt.axvline(0, color="k", lw=0.8)
    plt.tight_layout(); plt.savefig(f"results/shap_{lab}.png", dpi=150); plt.close()
    print(f"saved results/shap_{lab}.png")

print("done")
