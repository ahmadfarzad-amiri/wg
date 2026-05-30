"""WireGuard status, formatting, and request eligibility."""
import os
import shlex
import subprocess
import time

from client_panel.config import STATE_DIR, WG_IF


def run(cmd):
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
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
        return "نامحدود"
    return time.strftime("%Y-%m-%d", time.localtime(epoch))


def single_mode_text(mode):
    mode = (mode or "off").strip()
    if mode == "ip":
        return "محدود به یک آدرس اینترنتی؛ اولین IP ثبت می‌شود و اتصال از IP دیگر مجاز نیست."
    if mode == "endpoint":
        return "محدودیت سخت‌گیرانه؛ اتصال فقط از همان IP و پورت اولیه مجاز است."
    return "بدون محدودیت دستگاه؛ قابل استفاده از چند دستگاه یا شبکه."


def human_duration_fa(seconds):
    try:
        seconds = int(seconds)
    except Exception:
        return "نامشخص"
    if seconds < 0:
        seconds = 0
    if seconds < 60:
        return f"{seconds} ثانیه قبل"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} دقیقه قبل"
    hours = minutes // 60
    if hours < 24:
        remaining_minutes = minutes % 60
        if remaining_minutes:
            return f"{hours} ساعت و {remaining_minutes} دقیقه قبل"
        return f"{hours} ساعت قبل"
    days = hours // 24
    if days < 30:
        remaining_hours = hours % 24
        if remaining_hours:
            return f"{days} روز و {remaining_hours} ساعت قبل"
        return f"{days} روز قبل"
    months = days // 30
    if months < 12:
        remaining_days = days % 30
        if remaining_days:
            return f"{months} ماه و {remaining_days} روز قبل"
        return f"{months} ماه قبل"
    years = days // 365
    remaining_months = (days % 365) // 30
    if remaining_months:
        return f"{years} سال و {remaining_months} ماه قبل"
    return f"{years} سال قبل"


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

    endpoint = endpoints.get(pub, ["هیچ‌کدام"])[0] if pub in endpoints else "هیچ‌کدام"

    hs = 0
    if pub in handshakes and handshakes[pub]:
        hs = int(handshakes[pub][0])

    handshake = "هرگز" if hs <= 0 else human_duration_fa(now - hs)

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
        state = "منقضی"
        badge = "warn"
    elif limit_finished_by_usage or limit_finished_by_reason:
        state = "اتمام حجم"
        badge = "warn"
    elif disabled:
        state = "غیرفعال"
        badge = "bad"
    else:
        state = "فعال"
        badge = "ok"

    percent = min(100, int((used_now / limit) * 100)) if limit else 0

    if expires == 0:
        days_left = "نامحدود"
        expiry_percent = 0
    else:
        days_left_num = max(0, int((expires - now) / 86400))
        days_left = str(days_left_num)
        span = max(1, expires - (created or (expires - 86400 * 30)))
        expiry_percent = min(100, max(0, int(((expires - now) / span) * 100)))

    return {
        "client_name": client_name,
        "ip": c.get("IP", ""),
        "state": state,
        "badge": badge,
        "used": human_bytes(used_now),
        "limit": "نامحدود" if limit == 0 else human_bytes(limit),
        "remaining": "نامحدود" if limit == 0 else human_bytes(max(0, limit - used_now)),
        "percent": percent,
        "expires": human_time(expires),
        "days_left": days_left,
        "expiry_percent": expiry_percent,
        "endpoint": endpoint,
        "handshake": handshake,
        "single": c.get("SINGLE_MODE", "off"),
        "single_text": single_mode_text(c.get("SINGLE_MODE", "off")),
        "disabled_reason": c.get("DISABLED_REASON", "") or "ندارد",
    }


def can_request_status(s, action):
    if not s:
        return False, "کانفیگ پیدا نشد."
    state = s.get("state", "")
    if action == "enable":
        if state == "غیرفعال":
            return True, ""
        return False, "کانفیگ شما غیرفعال نیست؛ درخواست فعال‌سازی لازم نیست."
    if action == "renew":
        if state in ["منقضی", "اتمام حجم"]:
            return True, ""
        return False, "اشتراک هنوز منقضی نشده و حجم تمام نشده؛ درخواست تمدید فعال نیست."
    return False, "درخواست نامعتبر است."


def can_request_for_user(user, action):
    if not user:
        return False, "ابتدا وارد شوید."
    if user["status"] != "approved" or not user["client_name"]:
        return False, "حساب شما هنوز تایید یا به کانفیگ متصل نشده است."
    s = status_for_client(user["client_name"])
    return can_request_status(s, action)
