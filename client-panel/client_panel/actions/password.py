import subprocess

from client_panel.config import ROTATE_KEYS_CMD
from client_panel.core.auth import hash_password, verify_password
from client_panel.db import db


def handle_change_password(handler, user, data):
    oldp = data.get("old_password", "")
    newp = data.get("new_password", "")
    confp = data.get("confirm_password", "")

    if not verify_password(oldp, user["password_hash"], user["salt"]):
        handler.render_settings("رمز فعلی اشتباه است.")
        return
    if len(newp) < 6:
        handler.render_settings("رمز جدید باید حداقل ۶ کاراکتر باشد.")
        return
    if newp != confp:
        handler.render_settings("تکرار رمز جدید درست نیست.")
        return
    if user["status"] != "approved" or not user["client_name"]:
        handler.render_settings(
            "برای تغییر کلید کانفیگ، ابتدا حساب باید تایید و کانفیگ اختصاص داده شود."
        )
        return

    ph, salt = hash_password(newp)
    con = db()
    con.execute(
        "UPDATE users SET password_hash=?, salt=? WHERE id=?",
        (ph, salt, user["id"]),
    )
    con.commit()
    con.close()

    subprocess.run([ROTATE_KEYS_CMD, user["client_name"]], text=True)

    handler.render_settings(
        "رمز تغییر کرد و کلیدهای VPN عوض شد. کانفیگ جدید را دانلود و در WireGuard وارد کنید."
    )
