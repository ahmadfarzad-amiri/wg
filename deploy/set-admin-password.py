#!/usr/bin/env python3
"""Create or reset /etc/wireguard/admin-panel.json."""
import getpass
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "admin-panel"))

from admin_panel.core.auth import set_admin_password  # noqa: E402


def main():
    os.environ.setdefault("WG_DATA_DIR", "/etc/wireguard")
    username = input("Admin username [admin]: ").strip() or "admin"
    while True:
        password = getpass.getpass("Admin password (min 8 chars): ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Passwords do not match.")
            continue
        try:
            set_admin_password(username, password)
            print(f"Saved admin login for user: {username}")
            return
        except ValueError as exc:
            print(exc)


if __name__ == "__main__":
    main()
