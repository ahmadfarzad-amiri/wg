"""Admin password change."""
from admin_panel.core.auth import admin_username, set_admin_password, verify_admin


def handle_change_password(handler, data):
    old = data.get("old_password", "")
    new = data.get("new_password", "")
    confirm = data.get("confirm_password", "")

    if new != confirm:
        handler.flash("/settings", "رمز جدید و تکرار آن یکسان نیست")
        return

    username = admin_username()
    if not verify_admin(username, old):
        handler.flash("/settings", "رمز فعلی اشتباه است")
        return

    try:
        set_admin_password(username, new)
    except ValueError as e:
        handler.flash("/settings", str(e))
        return

    handler.flash("/settings", "رمز عبور با موفقیت تغییر کرد")
