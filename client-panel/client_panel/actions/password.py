import subprocess

from http.cookies import SimpleCookie

from client_panel.config import ROTATE_KEYS_CMD
from client_panel.core.auth import hash_password, verify_password
from client_panel.core.i18n import t, tf
from client_panel.core.statuses import UserStatus
from client_panel.core.wireguard import primary_client_for_user
from client_panel.db import db


def handle_change_password(handler, user, data):
    oldp = data.get("old_password", "")
    newp = data.get("new_password", "")
    confp = data.get("confirm_password", "")

    if not verify_password(oldp, user["password_hash"], user["salt"]):
        handler.render_settings(t("password.wrong_old"))
        return
    if len(newp) < 6:
        handler.render_settings(t("password.too_short"))
        return
    if newp != confp:
        handler.render_settings(t("password.mismatch"))
        return
    client_name = primary_client_for_user(user)
    if user["status"] != UserStatus.APPROVED or not client_name:
        handler.render_settings(t("password.not_ready"))
        return

    result = subprocess.run(
        [ROTATE_KEYS_CMD, client_name],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        handler.render_settings(tf("password.rotate_failed", detail=detail).strip())
        return

    ph, salt = hash_password(newp)
    con = db()
    con.execute(
        "UPDATE users SET password_hash=?, salt=? WHERE id=?",
        (ph, salt, user["id"]),
    )
    cookie = SimpleCookie(handler.headers.get("Cookie", ""))
    token = cookie.get("session")
    current = token.value if token else ""
    if current:
        con.execute(
            "DELETE FROM sessions WHERE user_id=? AND token!=?",
            (user["id"], current),
        )
    con.commit()
    con.close()

    handler.flash("/settings?newconfig=1", t("password.success"))
