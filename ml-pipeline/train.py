import os
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report, roc_curve, auc,
)
from sklearn.preprocessing import label_binarize
from catboost import CatBoostClassifier
import joblib

DATA = "processed/dataset_processed.csv"
MODEL_DIR = "models"
RES_DIR = "results"
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(RES_DIR, exist_ok=True)
sns.set_theme(style="whitegrid")


def fpr_from_cm(cm, labels, normal="normal"):
    i = labels.index(normal)
    tn = cm[i, i]; fp = cm[i, :].sum() - tn
    return fp / (fp + tn) if (fp + tn) > 0 else 0.0


def plot_cm(cm, labels, title, path):
    plt.figure(figsize=(7, 6))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=labels, yticklabels=labels, cbar=True)
    plt.title(title, fontsize=13, fontweight="bold")
    plt.ylabel("True label"); plt.xlabel("Predicted label")
    plt.tight_layout(); plt.savefig(path, dpi=150); plt.close()


def plot_feature_importance(names, importances, title, path):
    order = np.argsort(importances)
    plt.figure(figsize=(8, 6))
    sns.barplot(x=np.array(importances)[order], y=np.array(names)[order],
                palette="viridis")
    plt.title(title, fontsize=13, fontweight="bold")
    plt.xlabel("Importance")
    plt.tight_layout(); plt.savefig(path, dpi=150); plt.close()


def plot_roc(y_test, proba, labels, title, path):
    y_bin = label_binarize(y_test, classes=labels)
    plt.figure(figsize=(7, 6))
    for i, lab in enumerate(labels):
        fpr, tpr, _ = roc_curve(y_bin[:, i], proba[:, i])
        plt.plot(fpr, tpr, label=f"{lab} (AUC={auc(fpr, tpr):.3f})", linewidth=2)
    plt.plot([0, 1], [0, 1], "k--", alpha=0.4)
    plt.title(title, fontsize=13, fontweight="bold")
    plt.xlabel("False Positive Rate"); plt.ylabel("True Positive Rate")
    plt.legend(loc="lower right", fontsize=9)
    plt.tight_layout(); plt.savefig(path, dpi=150); plt.close()


def plot_metric_comparison(metrics, path):
    df = pd.DataFrame(metrics).T
    df.plot(kind="bar", figsize=(9, 6), colormap="Set2")
    plt.title("Model Comparison", fontsize=13, fontweight="bold")
    plt.ylabel("Score"); plt.ylim(0, 1.05); plt.xticks(rotation=0)
    plt.legend(loc="lower right"); plt.tight_layout()
    plt.savefig(path, dpi=150); plt.close()


def evaluate(name, model, X_test, y_test, labels, proba):
    preds = np.array(model.predict(X_test)).ravel()
    acc = accuracy_score(y_test, preds)
    prec = precision_score(y_test, preds, average="macro", zero_division=0)
    rec = recall_score(y_test, preds, average="macro", zero_division=0)
    f1 = f1_score(y_test, preds, average="macro", zero_division=0)
    y_bin = label_binarize(y_test, classes=labels)
    try:
        aucv = roc_auc_score(y_bin, proba, average="macro", multi_class="ovr")
    except Exception:
        aucv = 0.0
    cm = confusion_matrix(y_test, preds, labels=labels)
    fpr = fpr_from_cm(cm, labels)

    print("\n" + "=" * 55)
    print("MODEL:", name)
    print("=" * 55)
    print(f"Accuracy {acc:.4f} | Precision {prec:.4f} | Recall {rec:.4f} "
          f"| F1 {f1:.4f} | ROC-AUC {aucv:.4f} | FPR {fpr:.4f}")
    print(classification_report(y_test, preds, labels=labels, zero_division=0))

    tag = name.lower().replace(" ", "_")
    plot_cm(cm, labels, f"Confusion Matrix - {name}",
            os.path.join(RES_DIR, f"confusion_matrix_{tag}.png"))
    plot_roc(y_test, proba, labels, f"ROC Curves - {name}",
             os.path.join(RES_DIR, f"roc_{tag}.png"))
    return {"accuracy": acc, "precision": prec, "recall": rec,
            "f1": f1, "roc_auc": aucv, "fpr": fpr}


def main():
    df = pd.read_csv(DATA)
    with open("processed/feature_columns.json") as f:
        feature_cols = json.load(f)
    X = df[feature_cols]; y = df["label"]
    labels = sorted(y.unique().tolist())
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y)
    print("Train:", len(X_tr), "Test:", len(X_te))

    rf = RandomForestClassifier(n_estimators=300, class_weight="balanced",
                                random_state=42, n_jobs=-1)
    rf.fit(X_tr, y_tr)
    rf_m = evaluate("Random Forest", rf, X_te, y_te, labels, rf.predict_proba(X_te))
    plot_feature_importance(feature_cols, rf.feature_importances_,
                            "Feature Importance - Random Forest",
                            os.path.join(RES_DIR, "feature_importance.png"))

    cb = CatBoostClassifier(iterations=400, depth=8, learning_rate=0.1,
                            loss_function="MultiClass", auto_class_weights="Balanced",
                            random_seed=42, verbose=False)
    cb.fit(X_tr, y_tr)
    cb_m = evaluate("CatBoost", cb, X_te, y_te, labels, cb.predict_proba(X_te))

    joblib.dump(rf, os.path.join(MODEL_DIR, "random_forest.pkl"))
    cb.save_model(os.path.join(MODEL_DIR, "catboost.cbm"))

    metrics = {"Random Forest": rf_m, "CatBoost": cb_m}
    plot_metric_comparison(metrics, os.path.join(RES_DIR, "model_comparison.png"))
    with open(os.path.join(RES_DIR, "summary.json"), "w") as f:
        json.dump({"metrics": metrics,
                   "best_model": "CatBoost" if cb_m["f1"] >= rf_m["f1"] else "Random Forest",
                   "labels": labels}, f, indent=2)

    print("\nCharts + summary saved to", RES_DIR)


if __name__ == "__main__":
    main()
