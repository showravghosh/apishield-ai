import os
import csv
from collections import Counter
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

DECISION_LOG = os.path.join(os.path.dirname(__file__), "..", "gateway", "gateway_decisions.csv")

app = FastAPI(title="APIShield AI Dashboard")

COLORS = {"ALLOW": "#22c55e", "BLOCK": "#ef4444", "RATE_LIMIT": "#f59e0b"}


def read_rows():
    if not os.path.exists(DECISION_LOG):
        return []
    with open(DECISION_LOG) as f:
        return list(csv.DictReader(f))


@app.get("/", response_class=HTMLResponse)
def dashboard():
    rows = read_rows()
    total = len(rows)
    dec = Counter(r["decision"] for r in rows)
    pred = Counter(r["predicted"] for r in rows)
    allowed = dec.get("ALLOW", 0)
    blocked = dec.get("BLOCK", 0)
    limited = dec.get("RATE_LIMIT", 0)

    max_pred = max(pred.values()) if pred else 1
    bars = ""
    for label, count in sorted(pred.items(), key=lambda x: -x[1]):
        pct = int(count / max_pred * 100)
        color = "#22c55e" if label == "normal" else "#ef4444"
        bars += f'''<div class="bar-row">
          <div class="bar-label">{label}</div>
          <div class="bar-track"><div class="bar-fill" style="width:{pct}%;background:{color}">{count}</div></div>
        </div>'''

    recent = rows[-20:][::-1]
    trows = ""
    for r in recent:
        c = COLORS.get(r["decision"], "#888")
        ts = r["timestamp"][11:19] if len(r["timestamp"]) > 19 else r["timestamp"]
        trows += f'''<tr>
          <td>{ts}</td><td>{r["ip"]}</td><td>{r["method"]}</td>
          <td>{r["endpoint"]}</td><td>{r["predicted"]}</td>
          <td>{r["risk"]}</td>
          <td><span class="pill" style="background:{c}">{r["decision"]}</span></td>
        </tr>'''

    return f'''<!doctype html>
<html><head><meta charset="utf-8"><meta http-equiv="refresh" content="3">
<title>APIShield AI Dashboard</title>
<style>
  body{{font-family:system-ui,Arial,sans-serif;background:#0f172a;color:#e2e8f0;margin:0;padding:24px}}
  h1{{margin:0 0 4px}} .sub{{color:#94a3b8;margin-bottom:24px}}
  .cards{{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:28px}}
  .card{{background:#1e293b;border-radius:12px;padding:20px 26px;min-width:140px}}
  .card .n{{font-size:32px;font-weight:700}} .card .l{{color:#94a3b8;font-size:13px}}
  .panel{{background:#1e293b;border-radius:12px;padding:20px 24px;margin-bottom:24px}}
  .bar-row{{display:flex;align-items:center;margin:8px 0}}
  .bar-label{{width:130px;font-size:14px}}
  .bar-track{{flex:1;background:#0f172a;border-radius:6px;overflow:hidden}}
  .bar-fill{{padding:4px 8px;color:#fff;font-size:13px;font-weight:600;border-radius:6px;text-align:right;min-width:24px}}
  table{{width:100%;border-collapse:collapse;font-size:13px}}
  th,td{{text-align:left;padding:8px 10px;border-bottom:1px solid #334155}}
  th{{color:#94a3b8}}
  .pill{{padding:3px 10px;border-radius:20px;color:#fff;font-size:12px;font-weight:600}}
</style></head><body>
  <h1>APIShield AI</h1>
  <div class="sub">Real-time API security dashboard &middot; auto-refresh 3s</div>
  <div class="cards">
    <div class="card"><div class="n">{total}</div><div class="l">Total requests</div></div>
    <div class="card"><div class="n" style="color:#22c55e">{allowed}</div><div class="l">Allowed</div></div>
    <div class="card"><div class="n" style="color:#ef4444">{blocked}</div><div class="l">Blocked</div></div>
    <div class="card"><div class="n" style="color:#f59e0b">{limited}</div><div class="l">Rate limited</div></div>
  </div>
  <div class="panel"><h3>Detected traffic by type</h3>{bars or "<p>No data yet</p>"}</div>
  <div class="panel"><h3>Recent decisions</h3>
    <table><tr><th>Time</th><th>IP</th><th>Method</th><th>Endpoint</th><th>Predicted</th><th>Risk</th><th>Decision</th></tr>
    {trows or "<tr><td colspan=7>No data yet</td></tr>"}</table>
  </div>
</body></html>'''
