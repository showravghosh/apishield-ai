import sys
import random
import time
import requests

from config import BASE_URL, new_session_id, base_headers
import common

COMMON_PASSWORDS = [
    "123456", "password", "12345678", "qwerty", "abc123", "111111",
    "letmein", "admin", "welcome", "monkey", "dragon", "master",
    "login", "passw0rd", "iloveyou",
]
TARGETS = ["admin", "alice", "bob"]


def bf_session():
    sid = new_session_id()
    ip = common.make_ip()
    target = random.choice(TARGETS)
    for _ in range(random.randint(4, 12)):
        h = base_headers("brute_force", sid, ip=ip)
        pw = random.choice(COMMON_PASSWORDS)
        if random.random() < 0.1:
            pw = "password123"
        requests.post(f"{BASE_URL}/login",
                      json={"username": target, "password": pw}, headers=h)
        time.sleep(random.uniform(0.05, 0.4))


def run(n):
    print(f"Generating {n} brute force sessions...")
    for i in range(n):
        bf_session()
    print("Brute force traffic complete.")


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 20)
