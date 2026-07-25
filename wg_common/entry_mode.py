"""Detect whether the entry server runs standalone (no exit) or two-hop."""
import os


def entry_mode():
    """Return 'standalone' or 'twohop' from env (and inferred exit settings)."""
    mode = (os.environ.get("WG_ENTRY_MODE") or "").strip().lower()
    if mode in ("standalone", "twohop"):
        return mode
    exit_ip = (
        os.environ.get("WG_EXIT_IP")
        or os.environ.get("WG_EXIT_PUBLIC_IP")
        or ""
    ).strip()
    exit_pub = (os.environ.get("WG_EXIT_TUNNEL_PUB") or "").strip()
    if exit_ip and exit_pub:
        return "twohop"
    return "standalone"


def is_standalone_entry():
    return entry_mode() == "standalone"


def default_vpn_mode():
    return "direct" if is_standalone_entry() else "twohop"
