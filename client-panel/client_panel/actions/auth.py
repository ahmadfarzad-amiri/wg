import logging
import re
import sqlite3
import time

from client_panel.core.auth import hash_password, verify_password
from client_panel.core.i18n import t
from client_panel.core.statuses import UserStatus
from client_panel.db import db
from client_panel.server import security
from client_panel.server.session import _secure_attrs

log = logging.getLogger(__name__)


def handle_register(handler, data):
    username = re.sub(r"[^A-Za-z0-9_.-]", "_", data.get("username", "").strip())
    password = data.get("password", "")
    if len(username) < 3 or len(password) < 6:
        handler.render_register(t("auth.register_invalid"), variant="error")
        return
    ph, salt = hash_password(password)
    con = db()
    try:
        con.execute(
            "INSERT INTO users(username,password_hash,salt,status,created_at) VALUES(?,?,?,?,?)",
            (username, ph, salt, UserStatus.PENDING, int(time.time())),
        )
        con.commit()
    except sqlite3.IntegrityError:
        con.close()
        handler.render_register(t("auth.username_taken"), variant="error")
        return
    con.close()
    handler.flash("/login", t("auth.register_success"), variant="success")


def handle_login(handler, data):
    username = data.get("username", "").strip()
    try:
        blocked = security.check_login_rate_limit(handler, username)
        if blocked:
            handler.render_login(blocked, variant="error")
            return
        con = db()
        user = con.execute(
            "SELECT * FROM users WHERE username=?",
            (username,),
        ).fetchone()
        con.close()
        if not user or not verify_password(
            data.get("password", ""), user["password_hash"], user["salt"]
        ):
            security.record_login_failure(handler, username)
            handler.render_login(t("auth.invalid_credentials"), variant="error")
            return
        security.clear_login_attempts(handler, username)
        handler.set_session(user["id"])
    except Exception:
        log.exception("Login failed for user %r", username)
        handler.render_login(t("auth.invalid_credentials"), variant="error")


def handle_logout(handler):
    from http.cookies import SimpleCookie

    cookie = SimpleCookie(handler.headers.get("Cookie", ""))
    token = cookie.get("session")
    if token:
        con = db()
        con.execute("DELETE FROM sessions WHERE token=?", (token.value,))
        con.commit()
        con.close()
    handler.send_response(302)
    handler.send_header("Location", "/login")
    handler.send_header("Set-Cookie", "session=deleted; HttpOnly; SameSite=Strict; Path=/; Max-Age=0" + _secure_attrs())
    handler.end_headers()
