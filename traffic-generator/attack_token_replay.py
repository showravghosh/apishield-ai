import sys
import random
import requests

from config import BASE_URL, SEED_USERS, new_session_id, base_headers
import common


def replay_session():
    user = random.choice(SEED_USERS)
    sid = new_session_id()
    origin_ip = common.make_ip()
    token, uid = common.login(user, "normal", sid, origin_ip)
    if not token:
        return
    auth = {"Authorization": f"Bearer {token}"}
    for _ in range(random.randint(5, 12)):
        ip = common.make_ip()
        h = base_headers("token_replay", sid, ip=ip)
        h.update(auth)
        choice = random.choice(["products", "cart", "user"])
        if choice == "cart":
            requests.get(f"{BASE_URL}/cart", headers=h)
        elif choice == "user":
            requests.get(f"{BASE_URL}/users/{uid}", headers=h)
        else:
            requests.get(f"{BASE_URL}/products", headers=h)


def run(n):
    print(f"Generating {n} token replay sessions...")
    for i in range(n):
        replay_session()
    print("Token replay traffic complete.")


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 20)
