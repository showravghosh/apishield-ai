import time
import random
import requests
from config import base_headers, new_session_id, fake, SEED_USERS

GW = "http://localhost:9000"


def normal():
    ip = fake.ipv4_public()
    h = base_headers("demo", new_session_id(), ip=ip)
    ep = random.choice(["/products", "/products/1", "/products/2"])
    requests.get(f"{GW}{ep}", headers=h)


def sqli():
    ip = fake.ipv4_public()
    h = base_headers("demo", new_session_id(), ip=ip)
    q = random.choice(["' OR 1=1--", "admin'--", "'/**/UNION/**/SELECT/**/NULL--"])
    requests.get(f"{GW}/search", params={"q": q}, headers=h)


def flooding():
    ip = fake.ipv4_public()
    for _ in range(12):
        h = base_headers("demo", new_session_id(), ip=ip)
        requests.get(f"{GW}/products", headers=h)


def bola():
    ip = fake.ipv4_public()
    h = base_headers("demo", new_session_id(), ip=ip)
    tok = requests.post(f"{GW}/login", json=random.choice(SEED_USERS), headers=h).json().get("access_token", "")
    for v in random.sample(range(1, 25), 8):
        h = base_headers("demo", new_session_id(), ip=ip)
        h["Authorization"] = f"Bearer {tok}"
        requests.get(f"{GW}/users/{v}", headers=h)


def token_replay():
    h = base_headers("demo", new_session_id(), ip=fake.ipv4_public())
    tok = requests.post(f"{GW}/login", json=SEED_USERS[0], headers=h).json().get("access_token", "")
    for _ in range(6):
        h = base_headers("demo", new_session_id(), ip=fake.ipv4_public())
        h["Authorization"] = f"Bearer {tok}"
        requests.get(f"{GW}/products", headers=h)


attacks = [sqli, flooding, bola, token_replay]

print("Live demo running... (Ctrl+C to stop). Watch the dashboard!")
i = 0
while True:
    for _ in range(random.randint(3, 6)):
        normal()
        time.sleep(random.uniform(0.3, 0.8))
    atk = random.choice(attacks)
    print(f"  injecting attack: {atk.__name__}")
    atk()
    time.sleep(random.uniform(1.0, 2.0))
    i += 1
