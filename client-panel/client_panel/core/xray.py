"""Client-panel helper for reading Xray links for the logged-in user."""
import base64
import logging
import os
import re

log = logging.getLogger(__name__)

_SECRETS_FILE = "/etc/xray/server-secrets.env"
_CLIENTS_DIR = "/etc/xray/clients"


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


def get_links_for_client(client_name):
    """
    Return a dict of Xray links for the given WireGuard client name.
    Returns {} if no Xray profile exists for this client.
    """
    safe = _safe_name(client_name)
    client_file = os.path.join(_CLIENTS_DIR, f"{safe}.env")
    data = _load_file(client_file)
    uuid = data.get("CLIENT_UUID", "")
    if not uuid:
        return {}
    secrets = _load_file(_SECRETS_FILE)
    if not secrets:
        return {}
    return _build_links(safe, uuid, secrets)
