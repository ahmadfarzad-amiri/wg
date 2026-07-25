"""Smoke tests for wg_common shared modules."""
import hashlib
import unittest

from wg_common.client_status import compute_state_key, evaluate_client_meta
from wg_common.passwords import PBKDF2_ITERATIONS, hash_password, verify_password
from wg_common.statuses import ClientState, RequestStatus, UserStatus


class StatusConstantsTest(unittest.TestCase):
    def test_user_status_values(self):
        self.assertEqual(UserStatus.PENDING, "pending")
        self.assertIn(UserStatus.APPROVED, UserStatus.ALL)

    def test_client_state_needs_support(self):
        self.assertIn(ClientState.EXPIRED, ClientState.NEEDS_SUPPORT)
        self.assertNotIn(ClientState.ACTIVE, ClientState.NEEDS_SUPPORT)


class PasswordTest(unittest.TestCase):
    def test_hash_and_verify(self):
        stored, salt = hash_password("secret123")
        self.assertTrue(verify_password("secret123", stored, salt))
        self.assertFalse(verify_password("wrong", stored, salt))
        self.assertEqual(PBKDF2_ITERATIONS, 300_000)

    def test_wrong_iteration_count_rejected(self):
        salt = "abc123"
        other = hashlib.pbkdf2_hmac(
            "sha256", b"oldpass", salt.encode(), 250_000
        ).hex()
        self.assertFalse(verify_password("oldpass", other, salt))


class ClientStatusTest(unittest.TestCase):
    def test_active_client(self):
        meta = {
            "PUBLIC_KEY": "pk1",
            "DISABLED": "0",
            "LIMIT_BYTES": "0",
            "EXPIRES_AT": "0",
        }
        transfers = {"pk1": ["100", "200"]}
        handshakes = {"pk1": [str(1_700_000_000)]}
        core = evaluate_client_meta(meta, transfers, handshakes, now=1_700_000_050)
        self.assertEqual(core["state_key"], ClientState.ACTIVE)

    def test_disabled_overrides_active(self):
        meta = {"PUBLIC_KEY": "pk1", "DISABLED": "1", "LIMIT_BYTES": "0", "EXPIRES_AT": "0"}
        state_key, *_ = compute_state_key(meta, 0, active=True)
        self.assertEqual(state_key, ClientState.DISABLED)

    def test_reason_hints_expired(self):
        meta = {
            "PUBLIC_KEY": "pk1",
            "DISABLED": "1",
            "DISABLED_REASON": "subscription expired",
            "LIMIT_BYTES": "0",
            "EXPIRES_AT": "0",
        }
        core = evaluate_client_meta(meta, {}, {}, use_reason_hints=True)
        self.assertEqual(core["state_key"], ClientState.EXPIRED)


class RequestStatusTest(unittest.TestCase):
    def test_request_values(self):
        self.assertEqual(RequestStatus.PENDING, "pending")
        self.assertEqual(RequestStatus.APPROVED, "approved")


if __name__ == "__main__":
    unittest.main()
