import sys
import random
import requests

from config import BASE_URL, SEED_USERS, new_session_id
import common


def pt_session():
    user = random.choice(SEED_USERS)
    sid = new_session_id()
    ip = common.make_ip()
    token, uid = common.login(user, "normal", sid, ip)
    if not token:
        return
    common.browse_normal(sid, ip, token, uid, rounds=random.randint(1, 3))
    for _ in range(random.randint(3, 7)):
        h = common.auth_headers("parameter_tampering", sid, ip, token)
        tamper = random.choice([
            {"product_id": random.randint(1, 4), "quantity": random.randint(20, 100)},
            {"product_id": random.randint(1, 4), "quantity": -random.randint(1, 10)},
            {"product_id": random.randint(1, 4), "quantity": random.randint(10000, 999999)},
            {"product_id": random.randint(1, 4), "quantity": 1, "unit_price": random.randint(1, 50)},
            {"product_id": random.randint(5, 20), "quantity": 1},
            {"product_id": random.randint(1, 4), "quantity": 2, "discount": random.randint(10, 90)},
        ])
        requests.post(f"{BASE_URL}/order", json=tamper, headers=h)


def run(n):
    print(f"Generating {n} parameter tampering sessions...")
    for i in range(n):
        pt_session()
    print("Parameter tampering traffic complete.")


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 20)
