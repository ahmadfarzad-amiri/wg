"""Admin password change."""
from admin_panel.core.auth import admin_username, set_admin_password, verify_admin
from admin_panel.core.i18n import t


def handle_change_password(handler, data):
    old = data.get("old_password", "")
    new = data.get("new_password", "")
    confirm = data.get("confirm_password", "")

    if new != confirm:
        handler.flash("/settings", t("msg.password_mismatch"), variant="error")
        return

    username = admin_username()
    if not verify_admin(username, old):
        handler.flash("/settings", t("msg.old_password_wrong"), variant="error")
        return

    try:
        set_admin_password(username, new)
    except ValueError as e:
        handler.flash("/settings", str(e), variant="error")
        return

    handler.flash("/settings", t("msg.admin_password_changed"), variant="success")
