"""Client panel user password hashing (delegates to wg_common)."""
from wg_common.passwords import PBKDF2_ITERATIONS, hash_password

__all__ = ["PBKDF2_ITERATIONS", "hash_password"]
