"""Application configuration."""
import os
from pathlib import Path

from wg_common.version import resolve_version

ROOT = Path(__file__).resolve().parents[2]

_DATA = os.environ.get("WG_DATA_DIR", "/etc/wireguard")
_BIN = os.environ.get("WG_BIN_DIR", "/usr/local/bin")


def _data(*parts: str) -> str:
    return os.path.join(_DATA, *parts)


WG_IF = os.environ.get("WG_IF", "wg-clients")
STATE_DIR = os.environ.get("WG_STATE_DIR", _data("client-state"))
CLIENT_DIR = os.environ.get("WG_CLIENT_DIR", _data("clients"))
DB_PATH = os.environ.get("WG_DB_PATH", _data("panel.db"))
REQ_DIR = os.environ.get("WG_REQ_DIR", _data("client-requests"))
STATIC_DIR = str(ROOT / "static")
HOST = os.environ.get("WG_PANEL_HOST", "0.0.0.0")
PORT = int(os.environ.get("WG_PANEL_PORT", "8088"))
SESSION_DAYS = 14
BRAND = os.environ.get("WG_PANEL_BRAND", "VPN Access")
VERSION = resolve_version()  # WG_VERSION env, else latest GitHub tag
ROTATE_KEYS_CMD = os.environ.get(
    "WG_ROTATE_KEYS_CMD", os.path.join(_BIN, "wg-client-rotate-keys")
)
