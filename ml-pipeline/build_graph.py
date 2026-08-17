import os
import re
import json
import collections
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

RAW = "../traffic-generator/dataset/traffic_logs.csv"
OUT = "graph"
os.makedirs(OUT, exist_ok=True)


def target_id(path):
    m = re.match(r"/users/(\d+)", str(path))
    return int(m.group(1)) if m else None


def main():
    df = pd.read_csv(RAW)
    df["tid"] = df["endpoint"].apply(target_id)
    u = df[df["tid"].notna()].copy()
    u["tid"] = u["tid"].astype(int)

    accessors, acc_feats, acc_labels, acc_targets = [], [], [], []
    for sid, g in u.groupby("session_id", sort=False):
        targets = sorted(set(g["tid"].tolist()))
        acc_feats.append([len(g), len(targets),
                          int((g["status_code"] == 404).sum()),
                          int((g["status_code"] == 200).sum())])
        acc_labels.append(1 if (g["label"] == "bola").any() else 0)
        acc_targets.append(targets)
        accessors.append(sid)

    A = len(accessors)
    all_tids = sorted(set(t for ts in acc_targets for t in ts))
    tid_index = {t: A + i for i, t in enumerate(all_tids)}
    R = len(all_tids)
    N = A + R

    x = np.zeros((N, 4), dtype=np.float32)
    for i in range(A):
        x[i] = acc_feats[i]
    deg = collections.Counter()
    edges = []
    for i in range(A):
        for t in acc_targets[i]:
            j = tid_index[t]
            edges.append((i, j)); edges.append((j, i))
            deg[t] += 1
    for t in all_tids:
        x[tid_index[t]] = [deg[t], 0, 0, 0]

    x = StandardScaler().fit_transform(x).astype(np.float32)
    edge_index = np.array(edges, dtype=np.int64).T

    y = np.full(N, -1, dtype=np.int64)
    for i in range(A):
        y[i] = acc_labels[i]

    idx = np.arange(A)
    tr, te = train_test_split(idx, test_size=0.3, random_state=42, stratify=acc_labels)
    train_mask = np.zeros(N, dtype=bool); train_mask[tr] = True
    test_mask = np.zeros(N, dtype=bool); test_mask[te] = True

    np.savez_compressed(os.path.join(OUT, "graph.npz"),
                        x=x, edge_index=edge_index, y=y,
                        train_mask=train_mask, test_mask=test_mask)
    with open(os.path.join(OUT, "meta.json"), "w") as f:
        json.dump({"n_nodes": int(N), "n_accessors": int(A), "n_resources": int(R),
                   "n_edges": int(edge_index.shape[1]),
                   "labels": dict(collections.Counter(acc_labels))}, f, indent=2)
    print("Accessors:", A, "Resources:", R, "Edges:", edge_index.shape[1])
    print("Labels (0=normal,1=bola):", dict(collections.Counter(acc_labels)))


if __name__ == "__main__":
    main()
