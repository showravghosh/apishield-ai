import random
import time
import requests

from config import BASE_URL, base_headers, SEARCH_TERMS_NORMAL, fake


def make_ip():
    return fake.ipv4_public()


def login(user, label, sid, ip):
    h = base_headers(label, sid, ip=ip)
    r = requests.post(f"{BASE_URL}/login", json=user, headers=h)
    if r.status_code == 200:
        d = r.json()
        return d["access_token"], d["user_id"]
    return None, None


def auth_headers(label, sid, ip, token):
    h = base_headers(label, sid, ip=ip)
    h["Authorization"] = f"Bearer {token}"
    return h


def maybe_failed_login(user, sid, ip):
    if random.random() < 0.15:
        h = base_headers("normal", sid, ip=ip)
        requests.post(f"{BASE_URL}/login",
                      json={"username": user["username"], "password": "wrongpass"},
                      headers=h)
        time.sleep(random.uniform(0.1, 0.3))


def browse_normal(sid, ip, token, uid, rounds=None):
    if rounds is None:
        rounds = random.randint(2, 5)
    for _ in range(rounds):
        action = random.choice(
            ["list", "view", "search", "profile", "cart_add", "cart_view"]
        )
        h = auth_headers("normal", sid, ip, token)
        if action == "list":
            requests.get(f"{BASE_URL}/products", headers=h)
        elif action == "view":
            requests.get(f"{BASE_URL}/products/{random.randint(1, 4)}", headers=h)
        elif action == "search":
            requests.get(f"{BASE_URL}/search",
                         params={"q": random.choice(SEARCH_TERMS_NORMAL)}, headers=h)
        elif action == "profile":
            requests.get(f"{BASE_URL}/users/{uid}", headers=h)
        elif action == "cart_add":
            requests.post(f"{BASE_URL}/cart/add",
                          json={"product_id": random.randint(1, 4),
                                "quantity": random.randint(1, 3)}, headers=h)
        elif action == "cart_view":
            requests.get(f"{BASE_URL}/cart", headers=h)
        time.sleep(random.uniform(0.05, 0.25))
