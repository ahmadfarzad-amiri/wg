"""WireGuard client metadata and live status."""
import os
import shlex
import shutil
import time

from admin_panel.config import CLIENT_DIR, STATE_DIR, WG_IF
from admin_panel.core.i18n import human_duration, t, tf
from admin_panel.core.shell import run


def parse_meta_file(path):
    data = {}
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or "=" not in line:
                continue
            k, v = line.split("=", 1)
            try:
                parts = shlex.split(v)
                data[k] = parts[0] if parts else ""
            except Exception:
                data[k] = v.strip().strip("'\"")
    return data


def all_client_meta():
    rows = []
    if not os.path.isdir(STATE_DIR):
        return rows
    for fn in sorted(os.listdir(STATE_DIR)):
        if not fn.endswith(".meta"):
            continue
        path = os.path.join(STATE_DIR, fn)
        try:
            data = parse_meta_file(path)
            if data.get("NAME"):
                rows.append(data)
        except OSError:
            pass
    return rows


def _wg_cmd(*args):
    ssh_target = os.environ.get("WG_EXIT_SSH", "")
    ssh_key = os.environ.get("WG_EXIT_SSH_KEY", "")
    if ssh_target:
        cmd = ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new"]
        if ssh_key:
            cmd.extend(["-i", ssh_key])
        cmd.append(ssh_target)
        cmd.extend(["wg", *args])
        return cmd
    return ["wg", *args]


def wg_map(command):
    if not wg_interface_up():
        return {}
    out = run(_wg_cmd("show", WG_IF, command))
    result = {}
    for line in out.splitlines():
        parts = line.split()
        if parts:
            result[parts[0]] = parts[1:]
    return result


def wg_interface_up():
    if not shutil.which("wg") and not os.environ.get("WG_EXIT_SSH"):
        return False
    out = run(_wg_cmd("show", WG_IF))
    text = (out or "").lower()
    if not text.strip():
        return False
    if "unable to access interface" in text:
        return False
    if "no such file" in text:
        return False
    return True


def active_list_hint():
    if not shutil.which("wg"):
        return t("wg.tools_not_installed")
    if not wg_interface_up():
        return t("wg.interface_down")
    return ""


def human_bytes(n):
    try:
        n = int(n)
    except (TypeError, ValueError):
        n = 0
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(n)
    for u in units:
        if size < 1024 or u == units[-1]:
            return f"{int(size)} {u}" if u == "B" else f"{size:.2f} {u}"
        size /= 1024


def wg_map(command):
    if not wg_interface_up():
        return {}
    out = run(_wg_cmd("show", WG_IF, command))
    result = {}
    for line in out.splitlines():
        parts = line.split()
        if parts:
            result[parts[0]] = parts[1:]
    return result


def build_wg_snapshot():
    """Fetch transfer/endpoints/handshakes once for batch status reads."""
    return {
        "transfers": wg_map("transfer"),
        "endpoints": wg_map("endpoints"),
        "handshakes": wg_map("latest-handshakes"),
    }


def client_status(meta, snapshot=None):
    pub = meta.get("PUBLIC_KEY", "")
    if snapshot is None:
        transfers = wg_map("transfer")
        endpoints = wg_map("endpoints")
        handshakes = wg_map("latest-handshakes")
    else:
        transfers = snapshot["transfers"]
        endpoints = snapshot["endpoints"]
        handshakes = snapshot["handshakes"]

    rx = tx = current_total = 0
    if pub in transfers and len(transfers[pub]) >= 2:
        rx = int(transfers[pub][0])
        tx = int(transfers[pub][1])
        current_total = rx + tx

    used_base = int(meta.get("USED_BYTES", "0") or 0)
    last_total = int(meta.get("LAST_TOTAL", "0") or 0)
    used_now = used_base + max(0, current_total - last_total)

    hs = 0
    if pub in handshakes and handshakes[pub]:
        hs = int(handshakes[pub][0])

    now = int(time.time())
    diff = now - hs if hs else 999999999
    active = hs > 0 and diff <= 120

    limit_bytes = int(meta.get("LIMIT_BYTES", "0") or 0)
    expires_at = int(meta.get("EXPIRES_AT", "0") or 0)
    expired = expires_at > 0 and now >= expires_at
    over_limit = limit_bytes > 0 and used_now >= limit_bytes

    limit_raw = int(meta.get("LIMIT_BYTES", "0") or 0)
    state_key = "offline"
    if meta.get("DISABLED", "0") == "1":
        state_key = "disabled"
    elif expired:
        state_key = "expired"
    elif over_limit:
        state_key = "over_limit"
    elif active:
        state_key = "active"

    return {
        "name": meta.get("NAME", ""),
        "ip": meta.get("IP", ""),
        "public_key": pub,
        "used": human_bytes(used_now),
        "limit": t("unlimited") if limit_raw == 0 else human_bytes(limit_raw),
        "disabled": meta.get("DISABLED", "0") == "1",
        "reason": meta.get("DISABLED_REASON", "") or "—",
        "single": meta.get("SINGLE_MODE", "off"),
        "endpoint": endpoints.get(pub, ["none"])[0] if pub in endpoints else "none",
        "last": t("never") if not hs else human_duration(diff),
        "active": active,
        "rx": human_bytes(rx),
        "tx": human_bytes(tx),
        "expired": expired,
        "over_limit": over_limit,
        "state_key": state_key,
        "has_config": os.path.exists(
            os.path.join(CLIENT_DIR, f"{meta.get('NAME', '')}.conf")
        ),
        "handshake_age": diff if hs else 999999999,
        "rx_bytes": rx,
        "tx_bytes": tx,
    }


def all_client_status(snapshot=None):
    if snapshot is None:
        snapshot = build_wg_snapshot()
    return [client_status(m, snapshot) for m in all_client_meta()]


def find_client_status(client_name, snapshot=None):
    if snapshot is None:
        snapshot = build_wg_snapshot()
    for meta in all_client_meta():
        if meta.get("NAME") == client_name:
            return client_status(meta, snapshot)
    return None


def find_client_meta_by_name(client_name):
    for meta in all_client_meta():
        if meta.get("NAME") == client_name:
            return meta
    return None


def live_disconnect_client(client_name):
    meta = find_client_meta_by_name(client_name)
    if not meta:
        return t("msg.client_not_found")

    public_key = meta.get("PUBLIC_KEY", "")
    ip = meta.get("IP", "")

    if not public_key or not ip:
        return t("msg.no_pubkey")

    out1 = run(_wg_cmd("set", WG_IF, "peer", public_key, "remove"))
    time.sleep(1)
    out2 = run(_wg_cmd("set", WG_IF, "peer", public_key, "allowed-ips", f"{ip}/32"))

    details = f"{out1} {out2}".strip()
    return tf("msg.disconnect_success", name=client_name, details=details)
