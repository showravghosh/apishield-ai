import sys
import random

from config import SEED_USERS, new_session_id
import common


def normal_session():
    user = random.choice(SEED_USERS)
    sid = new_session_id()
    ip = common.make_ip()
    common.maybe_failed_login(user, sid, ip)
    token, uid = common.login(user, "normal", sid, ip)
    if not token:
        return
    common.browse_normal(sid, ip, token, uid, rounds=random.randint(3, 8))


def run(n):
    print(f"Generating {n} normal sessions...")
    for i in range(n):
        normal_session()
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{n} done")
    print("Normal traffic complete.")


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 100)
