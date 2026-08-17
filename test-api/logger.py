import csv
import os
import time
from datetime import datetime, timezone

from jose import jwt, JWTError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

import models
from database import SessionLocal
from auth import SECRET_KEY, ALGORITHM

CSV_DIR = os.path.join(os.path.dirname(__file__), "..", "traffic-generator", "dataset")
CSV_PATH = os.path.join(CSV_DIR, "traffic_logs.csv")

CSV_FIELDS = [
    "timestamp", "session_id", "user_id", "method", "endpoint",
    "status_code", "response_time_ms", "request_size", "response_size",
    "ip_address", "user_agent", "country", "device", "request_body", "label",
]


def _ensure_csv():
    os.makedirs(CSV_DIR, exist_ok=True)
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="") as f:
            csv.DictWriter(f, fieldnames=CSV_FIELDS).writeheader()


def _user_from_token(auth_header: str) -> str:
    if not auth_header or not auth_header.lower().startswith("bearer "):
        return "anon"
    token = auth_header.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub", "anon")
    except JWTError:
        return "invalid_token"


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        body_bytes = await request.body()
        start = time.perf_counter()

        response = await call_next(request)

        elapsed_ms = (time.perf_counter() - start) * 1000

        resp_body = b""
        async for chunk in response.body_iterator:
            resp_body += chunk
        new_response = StarletteResponse(
            content=resp_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )

        h = request.headers
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": h.get("x-session-id", "none"),
            "user_id": _user_from_token(h.get("authorization", "")),
            "method": request.method,
            "endpoint": request.url.path,
            "status_code": response.status_code,
            "response_time_ms": round(elapsed_ms, 2),
            "request_size": len(body_bytes),
            "response_size": len(resp_body),
            "ip_address": request.client.host if request.client else "unknown",
            "user_agent": h.get("user-agent", "unknown")[:300],
            "country": h.get("x-country", "unknown"),
            "device": h.get("x-device", "unknown"),
            "request_body": (body_bytes.decode("utf-8", "ignore") + " " + request.url.query)[:500],
            "label": h.get("x-label", "normal"),
        }

        if not request.url.path.startswith(("/docs", "/openapi", "/redoc", "/favicon")):
            _write_db(record)
            _write_csv(record)

        return new_response


def _write_db(record):
    db = SessionLocal()
    try:
        log = models.RequestLog(
            timestamp=datetime.fromisoformat(record["timestamp"]),
            session_id=record["session_id"],
            user_id=record["user_id"],
            method=record["method"],
            endpoint=record["endpoint"],
            status_code=record["status_code"],
            response_time_ms=record["response_time_ms"],
            request_size=record["request_size"],
            response_size=record["response_size"],
            ip_address=record["ip_address"],
            user_agent=record["user_agent"],
            country=record["country"],
            device=record["device"],
            request_body=record["request_body"],
            label=record["label"],
        )
        db.add(log)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _write_csv(record):
    _ensure_csv()
    with open(CSV_PATH, "a", newline="") as f:
        csv.DictWriter(f, fieldnames=CSV_FIELDS).writerow(record)
