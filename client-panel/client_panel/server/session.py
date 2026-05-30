import secrets
import time

from client_panel.config import SESSION_DAYS
from client_panel.db import db


def _secure_attrs():
    import os

    if os.environ.get("WG_HTTPS", "").strip() in ("1", "true", "yes"):
        return "; Secure"
    return ""


def current_user(handler):
    from client_panel.server import security

    security.purge_expired_sessions()
    from http.cookies import SimpleCookie

    cookie = SimpleCookie(handler.headers.get("Cookie", ""))
    token = cookie.get("session")
    if not token:
        return None
    con = db()
    row = con.execute(
        """
        SELECT users.* FROM sessions
        JOIN users ON users.id=sessions.user_id
        WHERE sessions.token=? AND sessions.expires_at>?
        """,
        (token.value, int(time.time())),
    ).fetchone()
    con.close()
    return row


def set_session(handler, user_id):
    token = secrets.token_urlsafe(32)
    expires = int(time.time()) + SESSION_DAYS * 86400
    con = db()
    con.execute(
        "INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,?)",
        (token, user_id, expires),
    )
    con.commit()
    con.close()
    handler.send_response(302)
    handler.send_header("Location", "/")
    handler.send_header(
        "Set-Cookie",
        f"session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_DAYS * 86400}{_secure_attrs()}",
    )
    handler.end_headers()
