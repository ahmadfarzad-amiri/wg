"""Password hashing and verification."""
import hashlib
import hmac
import secrets


def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 250000)
    return dk.hex(), salt


def verify_password(password, stored_hash, salt):
    h, _ = hash_password(password, salt)
    return hmac.compare_digest(h, stored_hash)
