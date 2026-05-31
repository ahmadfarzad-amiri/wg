"""Application configuration."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

_DATA = os.environ.get("WG_DATA_DIR", "/etc/wireguard")
_BIN = os.environ.get("WG_BIN_DIR", "/usr/local/bin")


def _data(*parts: str) -> str:
    return os.path.join(_DATA, *parts)


HOST = os.environ.get("WG_ADMIN_HOST", "127.0.0.1")
PORT = int(os.environ.get("WG_ADMIN_PORT", "8090"))
BASE = os.environ.get("WG_ADMIN_BASE", "/admin")

WG_IF = os.environ.get("WG_IF", "wg-clients")
DB_PATH = os.environ.get("WG_DB_PATH", _data("panel.db"))
ADMIN_CONFIG = os.environ.get("WG_ADMIN_CONFIG", _data("admin-panel.json"))
STATE_DIR = os.environ.get("WG_STATE_DIR", _data("client-state"))
CLIENT_DIR = os.environ.get("WG_CLIENT_DIR", _data("clients"))
SESSION_FILE = os.environ.get("WG_ADMIN_SESSION_FILE", _data("admin-sessions.db"))
STATIC_DIR = str(ROOT / "static")

SESSION_HOURS = 24
BRAND = os.environ.get("WG_ADMIN_BRAND", "VPN Access")
VERSION = "1.0.2"

DEFAULT_DAYS = os.environ.get("WG_ADMIN_DEFAULT_DAYS", "30")
DEFAULT_LIMIT = os.environ.get("WG_ADMIN_DEFAULT_LIMIT", "20G")
DEFAULT_SINGLE = os.environ.get("WG_ADMIN_DEFAULT_SINGLE", "--single-ip")

WG_CLIENT = os.environ.get("WG_CLIENT", os.path.join(_BIN, "wg-client"))
WG_CLIENT_SINGLE = os.environ.get(
    "WG_CLIENT_SINGLE", os.path.join(_BIN, "wg-client-single")
)
WG_PANEL_ADMIN = os.environ.get("WG_PANEL_ADMIN", os.path.join(_BIN, "wg-panel-admin"))


def admin_url(path: str) -> str:
    if not path.startswith("/"):
        path = "/" + path
    return BASE + path


def strip_admin_base(path: str) -> str:
    """Return app-relative path (e.g. /clients) without the /admin prefix."""
    if not path.startswith("/"):
        path = "/" + path
    base = BASE.rstrip("/")
    if base and path.startswith(base + "/"):
        return path[len(base) :] or "/"
    if path == base:
        return "/"
    return path
