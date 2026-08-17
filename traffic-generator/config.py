import random
import uuid
from faker import Faker

fake = Faker()

import os
BASE_URL = os.environ.get("APISHIELD_TARGET", "http://localhost:8000")

COUNTRIES = ["US", "GB", "IN", "BD", "DE", "FR", "BR", "CN", "RU", "NG"]
DEVICES = ["desktop", "mobile", "tablet"]
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) Safari/17.0",
    "Mozilla/5.0 (X11; Linux x86_64) Firefox/121.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0) Mobile Safari",
    "Mozilla/5.0 (Linux; Android 13) Chrome/119.0 Mobile",
]

SEED_USERS = [
    {"username": "alice", "password": "password123"},
    {"username": "bob", "password": "password123"},
]

SEARCH_TERMS_NORMAL = [
    "laptop", "phone", "headphone", "keyboard", "men's shoes",
    "women's bag", "gaming mouse", "4k monitor", "usb-c cable", "o'brien mug",
]


def new_session_id():
    return str(uuid.uuid4())[:8]


def base_headers(label, session_id, ip=None):
    return {
        "X-Label": label,
        "X-Session-Id": session_id,
        "X-Country": random.choice(COUNTRIES),
        "X-Device": random.choice(DEVICES),
        "X-Forwarded-For": ip or fake.ipv4_public(),
        "User-Agent": random.choice(USER_AGENTS),
    }
