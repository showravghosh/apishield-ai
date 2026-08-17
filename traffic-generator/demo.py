import time
import requests
from config import base_headers, new_session_id, fake, SEED_USERS

GW = "http://localhost:9000"


def show(label, r):
    d = r.headers.get("x-apishield-decision", "?")
    p = r.headers.get("x-apishield-predicted", r.json().get("attack_type", "") if r.status_code != 200 else "normal")
    print(f"  [{r.status_code}] {label:38s} -> {d:10s} ({p})")
    time.sleep(0.4)


def banner(t):
    print("\n" + "=" * 60)
    print(" " + t)
    print("=" * 60)
    time.sleep(1)


banner("1. NORMAL TRAFFIC (should be ALLOWED)")
for _ in range(5):
    ip = fake.ipv4_public()
    h = base_headers("demo", new_session_id(), ip=ip)
    show("normal user browsing /products", requests.get(f"{GW}/products", headers=h))

banner("2. SQL INJECTION (should be BLOCKED)")
for q in ["' OR 1=1--", "'/**/UnIoN/**/SeLeCT/**/NULL--", "admin'--"]:
    ip = fake.ipv4_public()
    h = base_headers("demo", new_session_id(), ip=ip)
    show(f"SQLi: {q}", requests.get(f"{GW}/search", params={"q": q}, headers=h))

banner("3. API FLOODING (rate attack, should get BLOCKED)")
ip = fake.ipv4_public()
for i in range(15):
    h = base_headers("demo", new_session_id(), ip=ip)
    r = requests.get(f"{GW}/products", headers=h)
    if i % 3 == 0 or r.status_code != 200:
        show(f"flood request #{i+1}", r)

banner("4. TOKEN REPLAY (same token, many IPs, should get BLOCKED)")
h = base_headers("demo", new_session_id(), ip=fake.ipv4_public())
tok = requests.post(f"{GW}/login", json=SEED_USERS[0], headers=h).json().get("access_token", "")
for i in range(6):
    h = base_headers("demo", new_session_id(), ip=fake.ipv4_public())
    h["Authorization"] = f"Bearer {tok}"
    show(f"replay from new IP #{i+1}", requests.get(f"{GW}/products", headers=h))

banner("DEMO COMPLETE - check the dashboard!")
