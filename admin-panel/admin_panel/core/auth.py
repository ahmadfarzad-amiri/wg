"""Admin authentication."""
import hashlib
import hmac
import json
import os
import secrets

from admin_panel.config import ADMIN_CONFIG
from admin_panel.core.i18n import t


def load_admin():
    with open(ADMIN_CONFIG, "r", encoding="utf-8") as f:
        return json.load(f)


def verify_admin(username, password):
    try:
        data = load_admin()
    except OSError:
        return False
    if username != data.get("username"):
        return False
    salt = data.get("salt", "")
    expected = data.get("password_hash", "")
    got = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 300000
    ).hex()
    return hmac.compare_digest(got, expected)


def set_admin_password(username, password):
    if len(password) < 8:
        raise ValueError(t("msg.admin_password_min_length"))
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 300000
    ).hex()
    data = {
        "username": username,
        "salt": salt,
        "password_hash": password_hash,
    }
    with open(ADMIN_CONFIG, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.chmod(ADMIN_CONFIG, 0o600)


def admin_username():
    try:
        return load_admin().get("username", "admin")
    except OSError:
        return "admin"
