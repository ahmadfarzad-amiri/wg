"""Client panel user password hashing (same algorithm as client-panel)."""
import hashlib
import secrets


def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 250000)
    return dk.hex(), salt
