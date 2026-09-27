import os
import sys

DEFAULT_COOKIE_PATH = os.path.expanduser("~/.muse/cookies.txt")
LOCAL_COOKIE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "cookies.txt"))


def get_cookie_path():
    if os.path.exists(LOCAL_COOKIE_PATH):
        return LOCAL_COOKIE_PATH
    if os.path.exists(DEFAULT_COOKIE_PATH):
        return DEFAULT_COOKIE_PATH
    return DEFAULT_COOKIE_PATH


def load_cookies():
    # 1. Check environment variable
    env_cookies = os.environ.get("MUSE_COOKIES")
    if env_cookies and env_cookies.strip():
        return env_cookies.strip()

    # 2. Check local cookies.txt
    if os.path.exists(LOCAL_COOKIE_PATH):
        try:
            with open(LOCAL_COOKIE_PATH, "r", encoding="utf-8") as f:
                c = f.read().strip()
                if c:
                    return c
        except Exception:
            pass

    # 3. Check ~/.muse/cookies.txt
    if os.path.exists(DEFAULT_COOKIE_PATH):
        try:
            with open(DEFAULT_COOKIE_PATH, "r", encoding="utf-8") as f:
                c = f.read().strip()
                if c:
                    return c
        except Exception:
            pass

    return None


def save_cookies(cookie_str, local=False):
    c = cookie_str.strip()
    target_path = LOCAL_COOKIE_PATH if local else DEFAULT_COOKIE_PATH
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(c)
    return target_path


def parse_cookie_list(cookie_raw):
    cookie_list = []
    for part in cookie_raw.split("; "):
        if "=" in part:
            k, v = part.split("=", 1)
            k = k.strip()
            v = v.strip()
            if k:
                cookie_list.append({"name": k, "value": v, "domain": ".muse.ai", "path": "/"})
    return cookie_list
