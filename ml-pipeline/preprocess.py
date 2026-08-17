import os
import re
from urllib.parse import unquote_plus
import json
from collections import deque
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, StandardScaler
import joblib

RAW_CSV = "../traffic-generator/dataset/traffic_logs.csv"
OUT_DIR = "processed"
WINDOW_SEC = 10.0
os.makedirs(OUT_DIR, exist_ok=True)

SQL_KEYWORDS = ["select", "union", "drop", "or ", "'", "--", "#", "=", ";", "sleep"]


def normalize_endpoint(path):
    return re.sub(r"/\d+", "/{id}", str(path))


def target_user(path):
    m = re.match(r"/users/(\d+)", str(path))
    return m.group(1) if m else None


def body_features(body):
    b = unquote_plus(str(body)).lower()
    length = len(b)
    special = sum(b.count(c) for c in ["'", '"', ";", "-", "=", "#", "(", ")"])
    sql_hits = sum(1 for k in SQL_KEYWORDS if k in b)
    return length, special, sql_hits



def numeric_features(text):
    t = unquote_plus(str(text))
    vals = []
    for x in re.findall(r"-?\d+\.?\d*", t):
        try:
            vals.append(float(x))
        except ValueError:
            pass
    mx = max(vals) if vals else 0.0
    mn = min(vals) if vals else 0.0
    has_neg = 1 if any(v < 0 for v in vals) else 0
    return mx, mn, has_neg, t.count(":")


def main():
    df = pd.read_csv(RAW_CSV)
    print("Raw rows:", len(df))
    df = df.drop_duplicates()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    df["endpoint_norm"] = df["endpoint"].apply(normalize_endpoint)
    df["hour"] = df["timestamp"].dt.hour
    df["is_error"] = (df["status_code"] >= 400).astype(int)
    df["is_login"] = (df["endpoint"] == "/login").astype(int)
    df["target_user"] = df["endpoint"].apply(target_user)

    bl, bs, bh = [], [], []
    mxs, mns, negs, fcs = [], [], [], []
    for b in df["request_body"]:
        l, s, h = body_features(b)
        bl.append(l); bs.append(s); bh.append(h)
        mx, mn, ng, fc = numeric_features(b)
        mxs.append(mx); mns.append(mn); negs.append(ng); fcs.append(fc)
    df["body_len"], df["body_special"], df["body_sql_hits"] = bl, bs, bh
    df["body_max_num"], df["body_min_num"], df["body_has_neg"], df["body_field_count"] = mxs, mns, negs, fcs

    n = len(df)
    ip_req = np.zeros(n); ip_fail = np.zeros(n); ip_uniq_ep = np.zeros(n)
    ip_login = np.zeros(n); ip_users = np.zeros(n)

    state = {}
    ts = df["timestamp"].astype("int64").to_numpy() / 1e9
    ips = df["ip_address"].to_numpy()
    errs = df["is_error"].to_numpy()
    logins = df["is_login"].to_numpy()
    eps = df["endpoint_norm"].to_numpy()
    tus = df["target_user"].to_numpy()

    for i in range(n):
        ip = ips[i]; t = ts[i]
        dq = state.setdefault(ip, deque())
        dq.append((t, errs[i], logins[i], eps[i], tus[i]))
        while dq and t - dq[0][0] > WINDOW_SEC:
            dq.popleft()
        ip_req[i] = len(dq)
        ip_fail[i] = sum(x[1] for x in dq)
        ip_login[i] = sum(x[2] for x in dq)
        ip_uniq_ep[i] = len(set(x[3] for x in dq))
        ip_users[i] = len(set(x[4] for x in dq if x[4] is not None))

    df["ip_req_10s"] = ip_req
    df["ip_fail_10s"] = ip_fail
    df["ip_fail_ratio_10s"] = ip_fail / np.maximum(ip_req, 1)
    df["ip_login_10s"] = ip_login
    df["ip_uniq_ep_10s"] = ip_uniq_ep
    df["ip_distinct_users_10s"] = ip_users
    token_ips = np.zeros(n)
    state_tok = {}
    uids = df["user_id"].astype(str).to_numpy()
    for i in range(n):
        u = uids[i]
        if u in ("anon", "invalid_token", "none", "nan"):
            token_ips[i] = 0
            continue
        tq = state_tok.setdefault(u, deque())
        tq.append((ts[i], ips[i]))
        while tq and ts[i] - tq[0][0] > WINDOW_SEC:
            tq.popleft()
        token_ips[i] = len(set(x[1] for x in tq))
    df["token_ips_10s"] = token_ips

    num_cols = [
        "status_code", "response_time_ms", "request_size", "response_size",
        "hour", "body_len", "body_special", "body_sql_hits", "body_max_num", "body_min_num", "body_has_neg", "body_field_count", "is_error", "is_login",
        "ip_req_10s", "ip_fail_10s", "ip_fail_ratio_10s", "ip_login_10s",
        "ip_uniq_ep_10s", "ip_distinct_users_10s", "token_ips_10s",
    ]
    cat_cols = ["method", "endpoint_norm", "country", "device"]

    encoders = {}
    for c in cat_cols:
        le = LabelEncoder()
        df[c + "_enc"] = le.fit_transform(df[c].astype(str))
        encoders[c] = list(le.classes_)

    df[num_cols] = df[num_cols].fillna(0)
    scaler = StandardScaler()
    df[num_cols] = scaler.fit_transform(df[num_cols])

    feature_cols = num_cols + [c + "_enc" for c in cat_cols]
    df["label_binary"] = (df["label"] != "normal").astype(int)

    out = df[feature_cols + ["label", "label_binary"]].copy()
    out.to_csv(os.path.join(OUT_DIR, "dataset_processed.csv"), index=False)
    joblib.dump(scaler, os.path.join(OUT_DIR, "scaler.pkl"))
    with open(os.path.join(OUT_DIR, "encoders.json"), "w") as f:
        json.dump(encoders, f, indent=2)
    with open(os.path.join(OUT_DIR, "feature_columns.json"), "w") as f:
        json.dump(feature_cols, f, indent=2)

    print("Processed rows:", len(out))
    print("Features:", len(feature_cols))
    print(out["label"].value_counts())


if __name__ == "__main__":
    main()
