"""Security helpers: CSRF, rate limiting, response headers."""
import html
import hmac
import os
import secrets
import sqlite3
import time
import urllib.parse
from http.cookies import SimpleCookie

from admin_panel.config import SESSION_FILE


def client_ip(handler):
    forwarded = handler.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return handler.client_address[0]


def is_secure(handler):
    if os.environ.get("WG_HTTPS", "").strip() in ("1", "true", "yes"):
        return True
    if handler.headers.get("X-Forwarded-Proto", "").lower() == "https":
        return True
    return False


def secure_cookie_attrs():
    return "; Secure" if os.environ.get("WG_HTTPS", "").strip() in ("1", "true", "yes") else ""


def apply_security_headers(handler):
    handler.send_header("X-Frame-Options", "DENY")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.send_header(
        "Content-Security-Policy",
        "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self' data:; font-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'",
    )


def _rate_db():
    con = sqlite3.connect(SESSION_FILE)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS login_attempts (
            key TEXT PRIMARY KEY,
            failures INTEGER NOT NULL DEFAULT 0,
            blocked_until INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    return con


def purge_expired_sessions():
    con = sqlite3.connect(SESSION_FILE)
    con.execute("DELETE FROM sessions WHERE expires_at <= ?", (int(time.time()),))
    con.commit()
    con.close()


def check_login_rate_limit(handler, username):
    key = f"{client_ip(handler)}:{username.strip().lower()}"
    now = int(time.time())
    con = _rate_db()
    row = con.execute(
        "SELECT failures, blocked_until FROM login_attempts WHERE key=?",
        (key,),
    ).fetchone()
    if row and row[1] > now:
        con.close()
        wait = row[1] - now
        return f"تلاش‌های زیاد. {wait} ثانیه صبر کنید."
    con.close()
    return None


def record_login_failure(handler, username):
    key = f"{client_ip(handler)}:{username.strip().lower()}"
    now = int(time.time())
    con = _rate_db()
    row = con.execute(
        "SELECT failures FROM login_attempts WHERE key=?",
        (key,),
    ).fetchone()
    failures = (row[0] if row else 0) + 1
    blocked_until = now + min(300, 5 * failures) if failures >= 5 else 0
    con.execute(
        """
        INSERT INTO login_attempts(key, failures, blocked_until) VALUES(?,?,?)
        ON CONFLICT(key) DO UPDATE SET failures=excluded.failures, blocked_until=excluded.blocked_until
        """,
        (key, failures, blocked_until),
    )
    con.commit()
    con.close()


def clear_login_attempts(handler, username):
    key = f"{client_ip(handler)}:{username.strip().lower()}"
    con = _rate_db()
    con.execute("DELETE FROM login_attempts WHERE key=?", (key,))
    con.commit()
    con.close()


def get_csrf_token(handler):
    cookie = SimpleCookie(handler.headers.get("Cookie", ""))
    token = cookie.get("wg_csrf")
    if token and token.value:
        return token.value
    return secrets.token_urlsafe(24)


def csrf_field(handler):
    token = get_csrf_token(handler)
    return f'<input type="hidden" name="csrf_token" value="{html.escape(token)}">'


def set_csrf_cookie(handler, token):
    attrs = f"HttpOnly; SameSite=Strict; Path=/; Max-Age=86400{secure_cookie_attrs()}"
    handler.send_header("Set-Cookie", f"wg_csrf={token}; {attrs}")


def validate_csrf(handler, data):
    form_token = data.get("csrf_token", "")
    cookie = SimpleCookie(handler.headers.get("Cookie", ""))
    cookie_token = cookie.get("wg_csrf")
    if not form_token or not cookie_token:
        return False
    return hmac.compare_digest(form_token, cookie_token.value)


def flash_redirect(handler, path, message):
    notice = urllib.parse.quote(message or "")
    sep = "&" if "?" in path else "?"
    handler.send_response(302)
    handler.send_header("Location", f"{path}{sep}notice={notice}")
    handler.end_headers()


def notice_from_query(handler):
    parsed = urllib.parse.urlparse(handler.path)
    params = urllib.parse.parse_qs(parsed.query)
    values = params.get("notice", [])
    if not values:
        return ""
    return urllib.parse.unquote(values[0])
