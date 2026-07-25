#!/usr/bin/env python3
"""Create or reset /etc/wireguard/admin-panel.json.

Usage:
  sudo python3 set-admin-password.py
  sudo WG_ADMIN_USER=admin WG_ADMIN_PASS='ADMIN_PASSWORD' python3 set-admin-password.py
"""
import getpass
import json
import os
import sys

DATA_DIR = os.environ.get("WG_DATA_DIR", "/etc/wireguard")
ADMIN_CONFIG = os.environ.get("WG_ADMIN_CONFIG", os.path.join(DATA_DIR, "admin-panel.json"))


def _load_paths():
    candidates = [
        os.environ.get("WG_INSTALL_DIR", "/opt/wg"),
        os.path.join(os.path.dirname(__file__), ".."),
    ]
    for root in candidates:
        if not root:
            continue
        admin = os.path.join(root, "admin-panel")
        common = os.path.join(root, "wg_common")
        if os.path.isdir(admin) and os.path.isdir(common):
            sys.path.insert(0, admin)
            sys.path.insert(0, root)
            return root
    return None


def main():
    os.environ.setdefault("WG_DATA_DIR", DATA_DIR)
    root = _load_paths()
    if root is None:
        print("ERROR: admin-panel not found under /opt/wg — install entry server first.", file=sys.stderr)
        return 1

    from admin_panel.core.auth import set_admin_password  # noqa: E402

    env_user = os.environ.get("WG_ADMIN_USER", "").strip()
    env_pass = os.environ.get("WG_ADMIN_PASS", "")

    if env_user and env_pass:
        username = env_user
        password = env_pass
    else:
        username = input("Admin username [admin]: ").strip() or "admin"
        while True:
            password = getpass.getpass("Admin password (min 8 chars): ")
            confirm = getpass.getpass("Confirm password: ")
            if password != confirm:
                print("Passwords do not match.")
                continue
            break

    try:
        set_admin_password(username, password)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Saved admin login for user: {username}")
    print(f"Config: {ADMIN_CONFIG}")
    return 0


def show_admin():
    path = ADMIN_CONFIG
    if not os.path.isfile(path):
        print(f"No admin config at {path}")
        return 1
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    print(f"Admin username: {data.get('username', '(missing)')}")
    print(f"Config file:    {path}")
    print("Password hash is stored; use set-admin-password to reset.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("--show", "show"):
        raise SystemExit(show_admin())
    raise SystemExit(main())
