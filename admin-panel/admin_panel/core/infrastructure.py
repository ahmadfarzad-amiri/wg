"""Read current entry/exit infrastructure settings from the host (when accessible)."""
import os
import re

from wg_common.entry_mode import is_standalone_entry


def _data_dir():
    return os.environ.get("WG_DATA_DIR", "/etc/wireguard")


def _read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except OSError:
        return ""


def _parse_env_file(path):
    data = {}
    for line in _read_text(path).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def _parse_tunnel_peer(conf_text):
    public_key = ""
    endpoint = ""
    in_peer = False
    for raw in conf_text.splitlines():
        line = raw.strip()
        if line == "[Peer]":
            in_peer = True
            continue
        if line.startswith("[") and line.endswith("]"):
            in_peer = False
            continue
        if not in_peer:
            continue
        if line.startswith("PublicKey") and "=" in line:
            public_key = line.split("=", 1)[1].strip()
        elif line.startswith("Endpoint") and "=" in line:
            endpoint = line.split("=", 1)[1].strip()
    host = ""
    port = ""
    if endpoint:
        if endpoint.startswith("["):
            match = re.match(r"^\[([^\]]+)\]:(\d+)$", endpoint)
            if match:
                host, port = match.group(1), match.group(2)
        elif ":" in endpoint:
            host, _, port = endpoint.rpartition(":")
        else:
            host = endpoint
    return public_key, host, port


def get_infrastructure_state():
    """Return current entry endpoint and exit tunnel settings, if readable."""
    base = _data_dir()
    env = _parse_env_file(os.path.join(base, "entry-server.env"))

    entry_endpoint = (env.get("WG_ENDPOINT") or "").strip()
    ep_file = _read_text(os.path.join(base, "wg-endpoint")).strip()
    if not entry_endpoint and ep_file:
        entry_endpoint = ep_file.splitlines()[0].strip()

    entry_old_ip = (env.get("WG_ENTRY_PUBLIC_IP") or "").strip()
    if not entry_old_ip and entry_endpoint:
        entry_old_ip = entry_endpoint.split(":")[0].strip()

    exit_ip = (env.get("WG_EXIT_IP") or "").strip()
    exit_port = (env.get("WG_EXIT_TUNNEL_PORT") or "").strip()
    exit_pub = (env.get("WG_EXIT_TUNNEL_PUB") or "").strip()

    tunnel_path = os.path.join(base, "wg-tunnel.conf")
    if os.path.isfile(tunnel_path):
        pub, tip, tport = _parse_tunnel_peer(_read_text(tunnel_path))
        if pub:
            exit_pub = exit_pub or pub
        if tip:
            exit_ip = exit_ip or tip
        if tport:
            exit_port = tport

    if not exit_port:
        exit_port = "51821"

    mode = (env.get("WG_ENTRY_MODE") or "").strip().lower()
    if mode == "standalone":
        standalone = True
    elif mode == "twohop":
        standalone = False
    else:
        standalone = not (exit_ip and exit_pub) or is_standalone_entry()
        mode = "standalone" if standalone else "twohop"

    return {
        "entry_endpoint": entry_endpoint,
        "entry_old_ip": entry_old_ip,
        "exit_ip": exit_ip,
        "exit_tunnel_pub": exit_pub,
        "exit_tunnel_port": exit_port,
        "entry_mode": mode if mode in ("standalone", "twohop") else (
            "standalone" if standalone else "twohop"
        ),
        "standalone": standalone,
    }
