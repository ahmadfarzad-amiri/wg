"""PBKDF2 password hashing shared by admin user management and client panel."""
import hashlib
import hmac
import secrets

PBKDF2_ITERATIONS = 300_000


def _derive(password, salt, iterations):
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), iterations
    ).hex()


def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    return _derive(password, salt, PBKDF2_ITERATIONS), salt


def verify_password(password, stored_hash, salt):
    if not stored_hash or not salt:
        return False
    return hmac.compare_digest(
        _derive(password, salt, PBKDF2_ITERATIONS), stored_hash
    )
