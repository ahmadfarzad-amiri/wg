"""WireGuard client metadata and live status."""
import os
import shlex
import shutil
import threading
import time

from admin_panel.config import CLIENT_DIR, STATE_DIR, WG_IF
from admin_panel.core.i18n import human_duration, t, tf
from admin_panel.core.shell import run
from wg_common.client_status import evaluate_client_meta

# ---------------------------------------------------------------------------
# In-process cache for `wg show` output
# Each wg show subcommand (transfer, endpoints, latest-handshakes) is a kernel
# call that takes 20-200 ms depending on peer count.  Caching for 2 seconds
# eliminates the cost for concurrent page loads without staling status data.
# ---------------------------------------------------------------------------
_WG_CACHE_TTL = 2  # seconds
_wg_cache: dict = {}
_wg_cache_lock = threading.Lock()

# Separate short-lived cache for wg_interface_up() so it is not re-checked on
# every wg_map() call (which would triple the kernel-call count per page load).
_WG_UP_CACHE_TTL = 5
_wg_up_cache: dict = {}  # key "up" -> (monotonic_time, bool)
_wg_up_lock = threading.Lock()


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


def _wg_map_uncached(command):
    out = run(_wg_cmd("show", WG_IF, command))
    result = {}
    for line in out.splitlines():
        parts = line.split()
        if parts:
            result[parts[0]] = parts[1:]
    return result


def wg_map(command):
    if not wg_interface_up():
        return {}
    now = time.monotonic()
    with _wg_cache_lock:
        entry = _wg_cache.get(command)
        if entry and now - entry[0] < _WG_CACHE_TTL:
            return entry[1]
    result = _wg_map_uncached(command)
    with _wg_cache_lock:
        _wg_cache[command] = (time.monotonic(), result)
    return result


def _wg_interface_up_uncached():
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


def wg_interface_up():
    now = time.monotonic()
    with _wg_up_lock:
        entry = _wg_up_cache.get("up")
        if entry and now - entry[0] < _WG_UP_CACHE_TTL:
            return entry[1]
    result = _wg_interface_up_uncached()
    with _wg_up_lock:
        _wg_up_cache["up"] = (time.monotonic(), result)
    return result


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


def human_time(epoch):
    try:
        epoch = int(epoch)
    except (TypeError, ValueError):
        epoch = 0
    if epoch <= 0:
        return t("unlimited")
    return time.strftime("%Y-%m-%d", time.localtime(epoch))


def compact_bytes(n):
    """wg-client style limit string (e.g. 20G) for forms."""
    try:
        n = int(n)
    except (TypeError, ValueError):
        return ""
    if n <= 0:
        return ""
    for div, suffix in (
        (1024**4, "T"),
        (1024**3, "G"),
        (1024**2, "M"),
        (1024, "K"),
    ):
        if n >= div:
            val = n / div
            if abs(val - round(val)) < 0.05:
                return f"{int(round(val))}{suffix}"
            text = f"{val:.1f}".rstrip("0").rstrip(".")
            return f"{text}{suffix}"
    return f"{n}B"


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

    core = evaluate_client_meta(meta, transfers, handshakes)
    rx = core["rx_bytes"]
    tx = core["tx_bytes"]
    used_now = core["used_now"]
    hs = core["handshake_epoch"]
    diff = core["handshake_age"]
    active = core["active"]
    expired = core["expired"]
    over_limit = core["over_limit"]
    state_key = core["state_key"]
    limit_raw = core["limit_bytes"]
    expires_at = core["expires_at"]

    days_left_num = None
    if expires_at > 0:
        if expired:
            duration = t("state.expired")
        else:
            days_left_num = max(0, (expires_at - int(time.time())) // 86400)
            duration = tf("duration.days_left", n=days_left_num)
    else:
        duration = t("unlimited")

    return {
        "name": meta.get("NAME", ""),
        "ip": meta.get("IP", ""),
        "public_key": pub,
        "used": human_bytes(used_now),
        "limit": t("unlimited") if limit_raw == 0 else human_bytes(limit_raw),
        "disabled": meta.get("DISABLED", "0") == "1",
        "reason": meta.get("DISABLED_REASON", "") or "—",
        "single": meta.get("SINGLE_MODE", "off"),
        "vpn_mode": (meta.get("VPN_MODE") or "twohop").lower(),
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
        "duration": duration,
        "expires_at": expires_at,
        "days_left": days_left_num,
        "limit_bytes": limit_raw,
        "update_days": str(days_left_num) if days_left_num is not None else "",
        "update_limit": compact_bytes(limit_raw),
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
