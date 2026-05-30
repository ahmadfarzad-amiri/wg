"""WireGuard client operations via wg-client CLI."""
import os

from admin_panel.config import (
    CLIENT_DIR,
    DEFAULT_DAYS,
    DEFAULT_LIMIT,
    DEFAULT_SINGLE,
    WG_CLIENT,
)
from admin_panel.core.shell import run
from admin_panel.core.wireguard import find_client_meta_by_name


def run_client_action(action, name, extra=None):
    extra = list(extra or [])
    return run([WG_CLIENT, action, name, *extra])


def run_client_renew(name, *, days=None, limit=None, single=None):
    days = str(days or DEFAULT_DAYS)
    limit = str(limit or DEFAULT_LIMIT)
    single = single or DEFAULT_SINGLE
    return run([WG_CLIENT, "renew", name, "--days", days, "--limit", limit, single])


def client_was_removed(name):
    return find_client_meta_by_name(name) is None


def run_client_remove(name):
    output = run([WG_CLIENT, "remove", name])
    if "Removed client" in (output or ""):
        return output
    if find_client_meta_by_name(name) is None:
        conf_path = os.path.join(CLIENT_DIR, f"{name}.conf")
        if not os.path.isfile(conf_path):
            return output or f"کلاینت «{name}» حذف شد."
    return output


def _client_action_applied(action, name):
    """Return True when a wg-client action succeeded for the given client."""
    meta = find_client_meta_by_name(name)
    if not meta:
        return action == "remove"

    if action == "enable":
        return meta.get("DISABLED", "0") != "1"
    if action == "disable":
        return meta.get("DISABLED", "0") == "1"
    if action == "remove":
        return find_client_meta_by_name(name) is None
    return True


def ensure_client(name, *, days=None, limit=None, single=None):
    """Ensure a client exists. Returns (ok, created, output)."""
    if find_client_meta_by_name(name):
        return True, False, ""

    days = str(days or DEFAULT_DAYS)
    limit = str(limit or DEFAULT_LIMIT)
    single = single or DEFAULT_SINGLE

    output = run(
        [
            WG_CLIENT,
            "add",
            name,
            "--days",
            days,
            "--limit",
            limit,
            single,
        ]
    )
    if find_client_meta_by_name(name):
        return True, True, output
    return False, False, output
