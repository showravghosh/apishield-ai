import os
import re
from urllib.parse import unquote_plus
import json
import time
import csv
import base64
from collections import deque
from datetime import datetime, timezone

import numpy as np
import joblib
import httpx
from fastapi import FastAPI, Request, Response
from catboost import CatBoostClassifier

ART = os.path.join(os.path.dirname(__file__), "artifacts")
BACKEND = "http://localhost:8000"
WINDOW_SEC = 10.0
DECISION_LOG = os.path.join(os.path.dirname(__file__), "gateway_decisions.csv")

BLOCK_THRESHOLD = 0.85
RATELIMIT_THRESHOLD = 0.55

SQL_KEYWORDS = ["select", "union", "drop", "or ", "'", "--", "#", "=", ";", "sleep"]

model = CatBoostClassifier()
model.load_model(os.path.join(ART, "model.cbm"))
scaler = joblib.load(os.path.join(ART, "scaler.pkl"))
with open(os.path.join(ART, "encoders.json")) as f:
    encoders = json.load(f)
with open(os.path.join(ART, "feature_columns.json")) as f:
    cfg = json.load(f)

NUM_COLS = cfg["num_cols"]
CAT_COLS = cfg["cat_cols"]
LABELS = cfg["labels"]
NORMAL_IDX = LABELS.index("normal")

state = {}
token_state = {}

app = FastAPI(title="APIShield AI Gateway")

DEC_FIELDS = ["timestamp", "ip", "method", "endpoint", "predicted", "risk", "decision"]
if not os.path.exists(DECISION_LOG):
    with open(DECISION_LOG, "w", newline="") as f:
        csv.DictWriter(f, fieldnames=DEC_FIELDS).writeheader()


def normalize_endpoint(path):
    return re.sub(r"/\d+", "/{id}", str(path))


def target_user(path):
    m = re.match(r"/users/(\d+)", str(path))
    return m.group(1) if m else None


def body_features(text):
    b = unquote_plus(str(text)).lower()
    return len(b), sum(b.count(c) for c in ["'", '"', ";", "-", "=", "#", "(", ")"]), \
        sum(1 for k in SQL_KEYWORDS if k in b)


def enc(col, val):
    classes = encoders[col]
    return classes.index(val) if val in classes else len(classes)


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


def token_subject(auth_header):
    if not auth_header or not auth_header.lower().startswith("bearer "):
        return None
    token = auth_header.split(" ", 1)[1]
    try:
        part = token.split(".")[1]
        part += "=" * (-len(part) % 4)
        return json.loads(base64.urlsafe_b64decode(part)).get("sub")
    except Exception:
        return None


def extract(request, body_bytes):
    now = time.time()
    path = request.url.path
    query = request.url.query
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
    ep_norm = normalize_endpoint(path)
    is_login = 1 if path == "/login" else 0
    tuser = target_user(path)

    body_text = body_bytes.decode("utf-8", "ignore") + " " + query
    body_len, body_special, body_sql = body_features(body_text)
    body_mx, body_mn, body_neg, body_fc = numeric_features(body_text)
    request_size = len(body_bytes)
    hour = datetime.now(timezone.utc).hour

    dq = state.setdefault(ip, deque())
    while dq and now - dq[0][0] > WINDOW_SEC:
        dq.popleft()

    ip_req = len(dq) + 1
    ip_fail = sum(x[1] for x in dq)
    ip_login = sum(x[2] for x in dq) + is_login
    eps = set(x[3] for x in dq); eps.add(ep_norm)
    ip_uniq_ep = len(eps)
    users = set(x[4] for x in dq if x[4] is not None)
    if tuser:
        users.add(tuser)
    ip_users = len(users)
    ip_fail_ratio = ip_fail / max(ip_req, 1)
    subject = token_subject(request.headers.get("authorization", ""))
    if subject:
        tq = token_state.setdefault(subject, deque())
        while tq and now - tq[0][0] > WINDOW_SEC:
            tq.popleft()
        tq.append((now, ip))
        token_ips = len(set(x[1] for x in tq))
    else:
        token_ips = 0

    feats = {
        "request_size": request_size, "hour": hour, "body_len": body_len,
        "body_special": body_special, "body_sql_hits": body_sql, "body_max_num": body_mx, "body_min_num": body_mn, "body_has_neg": body_neg, "body_field_count": body_fc, "is_login": is_login,
        "ip_req_10s": ip_req, "ip_fail_10s": ip_fail, "ip_fail_ratio_10s": ip_fail_ratio,
        "ip_login_10s": ip_login, "ip_uniq_ep_10s": ip_uniq_ep,
        "ip_distinct_users_10s": ip_users, "token_ips_10s": token_ips,
        "method": request.method, "endpoint_norm": ep_norm,
        "country": request.headers.get("x-country", "unknown"),
        "device": request.headers.get("x-device", "unknown"),
    }
    meta = {"ip": ip, "ep_norm": ep_norm, "is_login": is_login, "tuser": tuser, "dq": dq, "now": now}
    return feats, meta


def score(feats):
    num_vec = np.array([[feats[c] for c in NUM_COLS]], dtype=float)
    num_scaled = scaler.transform(num_vec)[0]
    cat_vec = [enc(c, feats[c]) for c in CAT_COLS]
    x = np.concatenate([num_scaled, cat_vec]).reshape(1, -1)
    proba = model.predict_proba(x)[0]
    pred_idx = int(np.argmax(proba))
    risk = float(1.0 - proba[NORMAL_IDX])
    return LABELS[pred_idx], risk


def decide(pred, risk):
    if pred != "normal" and risk >= BLOCK_THRESHOLD:
        return "BLOCK"
    if pred != "normal" and risk >= RATELIMIT_THRESHOLD:
        return "RATE_LIMIT"
    return "ALLOW"


def log_decision(meta, method, pred, risk, decision):
    with open(DECISION_LOG, "a", newline="") as f:
        csv.DictWriter(f, fieldnames=DEC_FIELDS).writerow({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ip": meta["ip"], "method": method, "endpoint": meta["ep_norm"],
            "predicted": pred, "risk": round(risk, 3), "decision": decision,
        })


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(path: str, request: Request):
    body_bytes = await request.body()
    feats, meta = extract(request, body_bytes)
    pred, risk = score(feats)
    _guards = {
        "api_flooding": feats["ip_req_10s"] >= 8,
        "bola": feats["ip_distinct_users_10s"] >= 3,
        "brute_force": feats["ip_fail_10s"] >= 3,
        "token_replay": feats["token_ips_10s"] >= 4,
        "credential_stuffing": feats["ip_login_10s"] >= 3,
    }
    if pred in _guards and not _guards[pred]:
        pred = "normal"
        risk = min(risk, 0.3)
    decision = decide(pred, risk)
    if feats["body_sql_hits"] >= 3:
        pred = "sql_injection"
        risk = max(risk, 0.95)
        decision = "BLOCK"
    if feats["token_ips_10s"] >= 5:
        pred = "token_replay"
        risk = max(risk, 0.95)
        decision = "BLOCK"
    log_decision(meta, request.method, pred, risk, decision)

    if decision == "BLOCK":
        meta["dq"].append((meta["now"], 1, meta["is_login"], meta["ep_norm"], meta["tuser"]))
        return Response(
            content=json.dumps({"error": "Request blocked by APIShield AI",
                                "attack_type": pred, "risk_score": round(risk, 3)}),
            status_code=403, media_type="application/json",
            headers={"X-APIShield-Decision": decision, "X-APIShield-Risk": str(round(risk, 3))})

    if decision == "RATE_LIMIT":
        meta["dq"].append((meta["now"], 1, meta["is_login"], meta["ep_norm"], meta["tuser"]))
        return Response(
            content=json.dumps({"error": "Rate limited by APIShield AI",
                                "attack_type": pred, "risk_score": round(risk, 3)}),
            status_code=429, media_type="application/json",
            headers={"X-APIShield-Decision": decision, "X-APIShield-Risk": str(round(risk, 3))})

    url = BACKEND + request.url.path
    if request.url.query:
        url += "?" + request.url.query
    fwd_headers = {k: v for k, v in request.headers.items()
                   if k.lower() not in ("host", "content-length")
                   and not (k.lower() == "authorization" and v.strip().lower() in ("", "bearer"))}
    async with httpx.AsyncClient() as client:
        r = await client.request(request.method, url, content=body_bytes,
                                 headers=fwd_headers, timeout=30.0)

    is_err = 1 if r.status_code >= 400 else 0
    meta["dq"].append((meta["now"], is_err, meta["is_login"], meta["ep_norm"], meta["tuser"]))

    return Response(content=r.content, status_code=r.status_code,
                    media_type=r.headers.get("content-type"),
                    headers={"X-APIShield-Decision": decision,
                             "X-APIShield-Risk": str(round(risk, 3)),
                             "X-APIShield-Predicted": pred, "X-APIShield-Tok": str(int(feats["token_ips_10s"]))})
