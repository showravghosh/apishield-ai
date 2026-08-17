import os
import re
import json
from urllib.parse import unquote_plus
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder, StandardScaler

RAW = "../traffic-generator/dataset/traffic_logs.csv"
OUT = "sequences"
MAXLEN = 50
os.makedirs(OUT, exist_ok=True)

SQL_KEYWORDS = ["select", "union", "drop", "or ", "'", "--", "#", "=", ";", "sleep"]


def normalize_endpoint(p):
    return re.sub(r"/\d+", "/{id}", str(p))


def body_feats(b):
    t = unquote_plus(str(b)).lower()
    special = sum(t.count(c) for c in ["'", '"', ";", "-", "=", "#", "(", ")"])
    sqlh = sum(1 for k in SQL_KEYWORDS if k in t)
    nums = [float(x) for x in re.findall(r"-?\d+\.?\d*", t)] or [0.0]
    return len(t), special, sqlh, max(nums), min(nums)


def main():
    df = pd.read_csv(RAW)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    df["endpoint_norm"] = df["endpoint"].apply(normalize_endpoint)
    df["is_login"] = (df["endpoint"] == "/login").astype(int)
    df["is_error"] = (df["status_code"] >= 400).astype(int)
    df["hour"] = df["timestamp"].dt.hour

    bl, bs, bh, bmax, bmin = [], [], [], [], []
    for b in df["request_body"]:
        l, s, h, mx, mn = body_feats(b)
        bl.append(l); bs.append(s); bh.append(h); bmax.append(mx); bmin.append(mn)
    df["body_len"], df["body_special"], df["body_sql_hits"] = bl, bs, bh
    df["body_max_num"], df["body_min_num"] = bmax, bmin

    m_enc = LabelEncoder(); df["method_enc"] = m_enc.fit_transform(df["method"].astype(str))
    e_enc = LabelEncoder(); df["endpoint_enc"] = e_enc.fit_transform(df["endpoint_norm"].astype(str))

    feat_cols = [
        "status_code", "response_time_ms", "request_size", "response_size",
        "is_login", "is_error", "hour", "body_len", "body_special",
        "body_sql_hits", "body_max_num", "body_min_num",
        "method_enc", "endpoint_enc",
    ]
    df[feat_cols] = df[feat_cols].fillna(0)
    scaler = StandardScaler()
    df[feat_cols] = scaler.fit_transform(df[feat_cols])

    F = len(feat_cols)
    X, y, lengths = [], [], []
    for sid, g in df.groupby("session_id", sort=False):
        g = g.sort_values("timestamp")
        labels = g["label"].tolist()
        sess_label = "normal"
        for lb in labels:
            if lb != "normal":
                sess_label = lb
                break
        mat = g[feat_cols].to_numpy(dtype=np.float32)[:MAXLEN]
        length = len(mat)
        if length < MAXLEN:
            pad = np.zeros((MAXLEN - length, F), dtype=np.float32)
            mat = np.vstack([mat, pad])
        X.append(mat); y.append(sess_label); lengths.append(length)

    y_enc = LabelEncoder()
    y_idx = y_enc.fit_transform(y)
    X = np.array(X, dtype=np.float32)
    y_idx = np.array(y_idx, dtype=np.int64)
    lengths = np.array(lengths, dtype=np.int64)

    np.savez_compressed(os.path.join(OUT, "data.npz"),
                        X=X, y=y_idx, lengths=lengths)
    with open(os.path.join(OUT, "meta.json"), "w") as f:
        json.dump({"classes": list(y_enc.classes_), "features": feat_cols,
                   "maxlen": MAXLEN, "n_sessions": len(X)}, f, indent=2)

    print("Sessions:", len(X), "| Seq shape:", X.shape, "| Classes:", list(y_enc.classes_))
    import collections
    print("Per-class sessions:", dict(collections.Counter(y)))


if __name__ == "__main__":
    main()
