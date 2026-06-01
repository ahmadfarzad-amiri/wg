"""WireGuard status, formatting, and request eligibility."""
import os
import shlex
import subprocess
import time

from client_panel.config import STATE_DIR, WG_IF
from client_panel.core.i18n import t, tf


def run(cmd, timeout=8):
    try:
        return subprocess.check_output(
            cmd, text=True, stderr=subprocess.DEVNULL, timeout=timeout
        ).strip()
    except Exception:
        return ""


def parse_meta(client_name):
    path = os.path.join(STATE_DIR, f"{client_name}.meta")
    data = {}
    if not os.path.exists(path):
        return data
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


def wg_map(command):
    out = run(["wg", "show", WG_IF, command])
    result = {}
    for line in out.splitlines():
        parts = line.split()
        if parts:
            result[parts[0]] = parts[1:]
    return result


def human_bytes(n):
    try:
        n = int(n)
    except Exception:
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
    except Exception:
        epoch = 0
    if epoch <= 0:
        return t("unlimited")
    return time.strftime("%Y-%m-%d", time.localtime(epoch))


def single_mode_text(mode):
    mode = (mode or "off").strip()
    if mode == "ip":
        return t("single.ip")
    if mode == "endpoint":
        return t("single.endpoint")
    return t("single.off")


def human_duration(seconds):
    try:
        seconds = int(seconds)
    except Exception:
        return t("duration.unknown")
    if seconds < 0:
        seconds = 0
    if seconds < 60:
        return tf("duration.seconds_ago", n=seconds)
    minutes = seconds // 60
    if minutes < 60:
        return tf("duration.minutes_ago", n=minutes)
    hours = minutes // 60
    if hours < 24:
        remaining_minutes = minutes % 60
        if remaining_minutes:
            return tf("duration.hours_minutes_ago", hours=hours, minutes=remaining_minutes)
        return tf("duration.hours_ago", n=hours)
    days = hours // 24
    if days < 30:
        remaining_hours = hours % 24
        if remaining_hours:
            return tf("duration.days_hours_ago", days=days, hours=remaining_hours)
        return tf("duration.days_ago", n=days)
    months = days // 30
    if months < 12:
        remaining_days = days % 30
        if remaining_days:
            return tf("duration.months_days_ago", months=months, days=remaining_days)
        return tf("duration.months_ago", n=months)
    years = days // 365
    remaining_months = (days % 365) // 30
    if remaining_months:
        return tf("duration.years_months_ago", years=years, months=remaining_months)
    return tf("duration.years_ago", n=years)


def status_for_client(client_name):
    c = parse_meta(client_name)
    if not c:
        return None

    pub = c.get("PUBLIC_KEY", "")
    transfers = wg_map("transfer")
    endpoints = wg_map("endpoints")
    handshakes = wg_map("latest-handshakes")

    current_total = 0
    if pub in transfers and len(transfers[pub]) >= 2:
        rx = int(transfers[pub][0])
        tx = int(transfers[pub][1])
        current_total = rx + tx

    used_base = int(c.get("USED_BYTES", "0") or 0)
    last_total = int(c.get("LAST_TOTAL", "0") or 0)
    used_now = used_base + max(0, current_total - last_total)

    limit = int(c.get("LIMIT_BYTES", "0") or 0)
    expires = int(c.get("EXPIRES_AT", "0") or 0)
    created = int(c.get("CREATED_AT", "0") or 0)
    disabled = c.get("DISABLED", "0") == "1"
    now = int(time.time())

    endpoint = endpoints.get(pub, [t("none")])[0] if pub in endpoints else t("none")

    hs = 0
    if pub in handshakes and handshakes[pub]:
        hs = int(handshakes[pub][0])

    handshake = t("never") if hs <= 0 else human_duration(now - hs)

    disabled_reason = (c.get("DISABLED_REASON", "") or "").lower()

    expired_by_time = bool(expires and now >= expires)
    expired_by_reason = "expired" in disabled_reason or "expire" in disabled_reason

    limit_finished_by_usage = bool(limit and used_now >= limit)
    limit_finished_by_reason = (
        "data limit" in disabled_reason
        or "limit reached" in disabled_reason
        or "over data" in disabled_reason
        or "quota" in disabled_reason
    )

    if expired_by_time or expired_by_reason:
        state_key = "expired"
        badge = "warn"
    elif limit_finished_by_usage or limit_finished_by_reason:
        state_key = "over_limit"
        badge = "warn"
    elif disabled:
        state_key = "disabled"
        badge = "bad"
    else:
        state_key = "active"
        badge = "ok"

    if expires == 0:
        days_left = t("unlimited")
        expiry_percent = 0
    else:
        days_left_num = max(0, int((expires - now) / 86400))
        days_left = str(days_left_num)
        span = max(1, expires - (created or (expires - 86400 * 30)))
        expiry_percent = min(100, max(0, int(((expires - now) / span) * 100)))

    percent = min(100, int((used_now / limit) * 100)) if limit else 0

    return {
        "client_name": client_name,
        "ip": c.get("IP", ""),
        "state_key": state_key,
        "state": t(f"state.{state_key}"),
        "badge": badge,
        "used": human_bytes(used_now),
        "limit": t("unlimited") if limit == 0 else human_bytes(limit),
        "remaining": t("unlimited") if limit == 0 else human_bytes(max(0, limit - used_now)),
        "percent": percent,
        "expires": human_time(expires),
        "days_left": days_left,
        "expiry_percent": expiry_percent,
        "endpoint": endpoint,
        "handshake": handshake,
        "single": c.get("SINGLE_MODE", "off"),
        "single_text": single_mode_text(c.get("SINGLE_MODE", "off")),
        "vpn_mode": (c.get("VPN_MODE") or "twohop").lower(),
        "vpn_mode_text": vpn_mode_text(c.get("VPN_MODE", "twohop")),
        "disabled_reason": c.get("DISABLED_REASON", "") or t("disabled_reason.none"),
    }


def vpn_mode_text(mode):
    mode = (mode or "twohop").lower()
    return t(f"vpn.{mode}", mode)


def _user_field(user, key, default=""):
    if not user:
        return default
    if isinstance(user, dict):
        val = user.get(key, default)
    else:
        try:
            val = user[key]
        except (KeyError, IndexError, TypeError):
            val = default
    return default if val is None else val


def assigned_client_names_for_user(user):
    from client_panel.db.user_configs import client_names_for_user

    if not user:
        return []
    names = client_names_for_user(user["id"])
    if names:
        return names
    legacy = _user_field(user, "client_name")
    if legacy:
        return [legacy]
    return []


def primary_client_for_user(user):
    from client_panel.db.user_configs import primary_client_name

    if not user:
        return ""
    return primary_client_name(user["id"], _user_field(user, "client_name"))


def statuses_for_user(user):
    names = assigned_client_names_for_user(user)
    rows = []
    for name in names:
        s = status_for_client(name)
        if s:
            rows.append(s)
    return rows


def can_request_status(s, action):
    if not s:
        return False, t("error.config_not_found")
    state_key = s.get("state_key", "")
    if action == "enable":
        if state_key == "disabled":
            return True, ""
        return False, t("error.enable_not_needed")
    if action == "renew":
        if state_key in ("expired", "over_limit"):
            return True, ""
        return False, t("error.renew_not_needed")
    return False, t("error.invalid_request")


def can_request_for_user(user, action):
    if not user:
        return False, t("error.sign_in_first")
    if user["status"] != "approved":
        return False, t("error.not_approved")
    primary = primary_client_for_user(user)
    if not primary:
        return False, t("error.config_not_assigned")
    s = status_for_client(primary)
    return can_request_status(s, action)
