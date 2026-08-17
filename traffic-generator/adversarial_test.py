import time
import requests
from config import base_headers, new_session_id, fake, SEED_USERS

GW = "http://localhost:9000"


def blocked(code):
    return code in (403, 429)


def test_sqli():
    std = ["' OR 1=1--", "admin'--", "' UNION SELECT NULL,NULL--",
           "' OR 'x'='x", "'; DROP TABLE users--"]
    eva = ["' oR/**/1=1-- -", "'/**/UnIoN/**/SeLeCT/**/NULL--",
           "%2527 OR 1=1", "' || '1'='1", "' oR 1 like 1-- -"]

    def run(payloads):
        b = 0
        for p in payloads * 4:
            h = base_headers("test", new_session_id(), ip=fake.ipv4_public())
            r = requests.get(f"{GW}/search", params={"q": p}, headers=h)
            b += blocked(r.status_code)
        return b / (len(payloads) * 4)
    return run(std), run(eva)


def test_flooding():
    def burst(n, delay):
        ip = fake.ipv4_public(); b = 0
        for _ in range(n):
            h = base_headers("test", new_session_id(), ip=ip)
            r = requests.get(f"{GW}/products", headers=h)
            b += blocked(r.status_code)
            if delay:
                time.sleep(delay)
        return b / n
    return burst(40, 0), burst(40, 1.2)


def test_token_replay():
    def get_tok(user):
        h = base_headers("test", new_session_id(), ip=fake.ipv4_public())
        r = requests.post(f"{GW}/login", json=user, headers=h)
        return r.json().get("access_token", "")

    def replay(tok, n_ips):
        b = 0
        for _ in range(n_ips):
            h = base_headers("test", new_session_id(), ip=fake.ipv4_public())
            h["Authorization"] = f"Bearer {tok}"
            r = requests.get(f"{GW}/products", headers=h)
            b += blocked(r.status_code)
        return b / n_ips

    std = replay(get_tok(SEED_USERS[0]), 12)
    time.sleep(11)
    eva = replay(get_tok(SEED_USERS[1]), 4)
    return std, eva


print("Adversarial / Evasion Test (detection rate: standard vs evasive)\n")
for name, fn in [("SQL Injection", test_sqli),
                 ("API Flooding", test_flooding),
                 ("Token Replay", test_token_replay)]:
    s, e = fn()
    print(f"  {name:15s}  standard {s*100:5.1f}%   evasive {e*100:5.1f}%")
print("\n(High standard + lower evasive = attacker can partially evade -> honest limitation)")
