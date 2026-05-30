import secrets
import time

from admin_panel.config import BASE, SESSION_HOURS, admin_url
from admin_panel.db import session_db


def _secure_attrs():
    import os

    if os.environ.get("WG_HTTPS", "").strip() in ("1", "true", "yes"):
        return "; Secure"
    return ""


def is_logged_in(handler):
    from admin_panel.server import security

    security.purge_expired_sessions()
    from http.cookies import SimpleCookie

    cookie = SimpleCookie(handler.headers.get("Cookie", ""))
    token = cookie.get("admin_session")
    if not token:
        return False
    con = session_db()
    row = con.execute(
        "SELECT token FROM sessions WHERE token=? AND expires_at>?",
        (token.value, int(time.time())),
    ).fetchone()
    con.close()
    return bool(row)


def set_session(handler):
    token = secrets.token_urlsafe(32)
    expires = int(time.time()) + SESSION_HOURS * 3600
    con = session_db()
    con.execute(
        "INSERT INTO sessions(token, expires_at) VALUES(?, ?)",
        (token, expires),
    )
    con.commit()
    con.close()
    handler.send_response(302)
    handler.send_header("Location", admin_url("/"))
    handler.send_header(
        "Set-Cookie",
        f"admin_session={token}; HttpOnly; SameSite=Strict; Path={BASE}; "
        f"Max-Age={SESSION_HOURS * 3600}{_secure_attrs()}",
    )
    handler.end_headers()


def clear_session(handler):
    from http.cookies import SimpleCookie

    cookie = SimpleCookie(handler.headers.get("Cookie", ""))
    token = cookie.get("admin_session")
    if token:
        con = session_db()
        con.execute("DELETE FROM sessions WHERE token=?", (token.value,))
        con.commit()
        con.close()
    handler.send_response(302)
    handler.send_header("Location", admin_url("/login"))
    handler.send_header(
        "Set-Cookie",
        f"admin_session=deleted; HttpOnly; SameSite=Strict; Path={BASE}; Max-Age=0{_secure_attrs()}",
    )
    handler.end_headers()


def require_login(handler):
    if not is_logged_in(handler):
        redirect_login(handler)
        return False
    return True


def redirect_login(handler):
    handler.send_response(302)
    handler.send_header("Location", admin_url("/login"))
    handler.end_headers()
