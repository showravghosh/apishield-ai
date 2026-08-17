import sys
import random
import time
import requests

from config import BASE_URL, SEED_USERS, new_session_id
import common


def bola_session():
    user = random.choice(SEED_USERS)
    sid = new_session_id()
    ip = common.make_ip()
    token, uid = common.login(user, "normal", sid, ip)
    if not token:
        return
    common.browse_normal(sid, ip, token, uid, rounds=random.randint(1, 3))
    for _ in range(random.randint(4, 10)):
        victim = random.randint(1, 50)
        if victim == uid:
            victim += 1
        h = common.auth_headers("bola", sid, ip, token)
        requests.get(f"{BASE_URL}/users/{victim}", headers=h)
        time.sleep(random.uniform(0.02, 0.1))


def run(n):
    print(f"Generating {n} BOLA sessions...")
    for i in range(n):
        bola_session()
    print("BOLA traffic complete.")


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 20)
