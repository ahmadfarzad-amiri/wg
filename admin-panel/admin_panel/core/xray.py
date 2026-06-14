"""Xray protocol state reader and client manager."""
import base64
import glob
import json
import logging
import os
import re
import subprocess

log = logging.getLogger(__name__)

DEPLOY_DIR = os.environ.get("WG_DEPLOY_DIR", "/opt/wg/deploy")

_XRAY_BIN = "/usr/local/bin/xray"
_SECRETS_FILE = "/etc/xray/server-secrets.env"
_CLIENTS_DIR = "/etc/xray/clients"
_CONFIG_FILE = "/etc/xray/config.json"


def _safe_name(name):
    name = re.sub(r"[^A-Za-z0-9_]", "_", name)
    return name[:64]


def _load_file(path):
    """Parse a simple KEY=VALUE env file into a dict."""
    result = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                result[k.strip()] = v.strip()
    except OSError:
        pass
    return result


def is_installed():
    """Return True if the Xray binary exists."""
    return os.path.isfile(_XRAY_BIN) and os.access(_XRAY_BIN, os.X_OK)


def is_running():
    """Return True if the xray systemd service is active."""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "xray"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() == "active"
    except Exception:
        return False


def load_secrets():
    """Load /etc/xray/server-secrets.env and return a dict."""
    return _load_file(_SECRETS_FILE)


def _build_links(name, uuid, secrets):
    """Build share-link dict for a client given its name, UUID, and server secrets."""
    server_ip = secrets.get("XRAY_SERVER_IP", "")
    pub = secrets.get("XRAY_REALITY_PUB", "")
    sid = secrets.get("XRAY_REALITY_SHORT_ID", "")
    sni = secrets.get("XRAY_REALITY_SNI", "")
    ss_pass = secrets.get("XRAY_SS_PASSWORD", "")
    ws_domain = secrets.get("XRAY_WS_DOMAIN", "").strip()

    links = {}

    # VLESS + Reality
    links["reality"] = (
        f"vless://{uuid}@{server_ip}:443"
        f"?encryption=none&flow=xtls-rprx-vision&security=reality"
        f"&sni={sni}&fp=chrome&pbk={pub}&sid={sid}"
        f"&type=tcp&headerType=none#{name}-reality"
    )

    # VLESS + WebSocket + TLS (only if WS domain is configured)
    if ws_domain:
        links["ws"] = (
            f"vless://{uuid}@{ws_domain}:443"
            f"?encryption=none&security=tls&sni={ws_domain}"
            f"&type=ws&path=%2Fvless#{name}-ws"
        )

    # Shadowsocks 2022
    method_pass = f"2022-blake3-aes-256-gcm:{ss_pass}"
    encoded = base64.b64encode(method_pass.encode()).decode()
    links["ss"] = f"ss://{encoded}@{server_ip}:8388#{name}-ss"

    return links


def list_clients():
    """Return list of dicts: {name, uuid, links} from /etc/xray/clients/*.env."""
    secrets = load_secrets()
    clients = []
    pattern = os.path.join(_CLIENTS_DIR, "*.env")
    for path in sorted(glob.glob(pattern)):
        data = _load_file(path)
        name = data.get("CLIENT_NAME", "")
        uuid = data.get("CLIENT_UUID", "")
        if not name or not uuid:
            continue
        links = _build_links(name, uuid, secrets)
        clients.append({"name": name, "uuid": uuid, "links": links})
    return clients


def get_client(name):
    """Return a single client dict {name, uuid, links} or None."""
    safe = _safe_name(name)
    path = os.path.join(_CLIENTS_DIR, f"{safe}.env")
    data = _load_file(path)
    uuid = data.get("CLIENT_UUID", "")
    if not uuid:
        return None
    secrets = load_secrets()
    links = _build_links(safe, uuid, secrets)
    return {"name": safe, "uuid": uuid, "links": links}


def add_client(name):
    """
    Run xray-client-add.sh to create a new Xray client.
    Returns (True, links_dict) on success or (False, error_str) on failure.
    """
    safe = _safe_name(name)
    script = os.path.join(DEPLOY_DIR, "xray-client-add.sh")
    try:
        result = subprocess.run(
            ["bash", script, safe],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "unknown error").strip()
            log.error("xray-client-add.sh failed for %s: %s", safe, err)
            return False, err
    except subprocess.TimeoutExpired:
        log.error("xray-client-add.sh timed out for %s", safe)
        return False, "command timed out"
    except Exception as exc:
        log.error("xray-client-add.sh error for %s: %s", safe, exc)
        return False, str(exc)

    # Read the freshly-written client file to get the UUID and build links
    client = get_client(safe)
    if not client:
        return False, "client file not written"
    return True, client["links"]


def delete_client(name):
    """
    Remove an Xray client:
    - Remove UUID from /etc/xray/config.json inbounds
    - Delete /etc/xray/clients/{name}.env
    - Reload the xray service
    Returns True on success, False on failure.
    """
    safe = _safe_name(name)
    client_file = os.path.join(_CLIENTS_DIR, f"{safe}.env")

    # Read the UUID first so we can scrub it from config.json
    data = _load_file(client_file)
    uuid = data.get("CLIENT_UUID", "")

    # Patch config.json — remove client from all inbounds
    if uuid and os.path.isfile(_CONFIG_FILE):
        try:
            with open(_CONFIG_FILE) as f:
                cfg = json.load(f)
            changed = False
            for ib in cfg.get("inbounds", []):
                settings = ib.get("settings", {})
                clients = settings.get("clients", [])
                new_clients = [c for c in clients if c.get("id") != uuid and c.get("email") != safe]
                if len(new_clients) != len(clients):
                    settings["clients"] = new_clients
                    changed = True
            if changed:
                with open(_CONFIG_FILE, "w") as f:
                    json.dump(cfg, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            log.error("Failed to patch xray config.json while deleting %s: %s", safe, exc)
            return False

    # Delete the client env file
    try:
        if os.path.isfile(client_file):
            os.unlink(client_file)
    except Exception as exc:
        log.error("Failed to delete client file %s: %s", client_file, exc)
        return False

    # Reload xray service
    try:
        subprocess.run(
            ["systemctl", "reload", "xray"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        try:
            subprocess.run(
                ["systemctl", "restart", "xray"],
                capture_output=True,
                text=True,
                timeout=15,
            )
        except Exception as exc:
            log.warning("Failed to reload xray after deleting %s: %s", safe, exc)

    return True
