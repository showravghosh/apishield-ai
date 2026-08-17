import sys
import random
import requests

from config import BASE_URL, new_session_id, base_headers
import common


def flood_session():
    sid = new_session_id()
    ip = common.make_ip()
    burst = random.randint(30, 80)
    for _ in range(burst):
        h = base_headers("api_flooding", sid, ip=ip)
        if random.random() < 0.5:
            requests.get(f"{BASE_URL}/search", params={"q": "phone"}, headers=h)
        else:
            requests.get(f"{BASE_URL}/products", headers=h)


def run(n):
    print(f"Generating {n} flooding sessions...")
    for i in range(n):
        flood_session()
    print("Flooding traffic complete.")


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 10)
