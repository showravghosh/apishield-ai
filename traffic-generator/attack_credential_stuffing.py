import sys
import random
import requests

from config import BASE_URL, new_session_id, base_headers, fake, SEED_USERS

LEAKED_PASSWORDS = [
    "123456", "password", "qwerty", "abc123", "letmein",
    "welcome1", "iloveyou", "admin123", "stolenpass", "test123",
]


def run(n):
    print(f"Generating {n} credential stuffing attempts...")
    for i in range(n):
        sid = new_session_id()
        ip = fake.ipv4_public()
        h = base_headers("credential_stuffing", sid, ip=ip)
        if random.random() < 0.05:
            cred = random.choice(SEED_USERS)
        else:
            cred = {"username": fake.user_name(),
                    "password": random.choice(LEAKED_PASSWORDS)}
        requests.post(f"{BASE_URL}/login", json=cred, headers=h)
        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{n} done")
    print("Credential stuffing traffic complete.")


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 100)
