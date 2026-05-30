from admin_panel.components.layout import page
from admin_panel.core.auth import admin_username, set_admin_password, verify_admin
from admin_panel.views import settings


def handle_change_password(handler, data):
    old = data.get("old_password", "")
    new = data.get("new_password", "")
    confirm = data.get("confirm_password", "")

    if new != confirm:
        handler.send_html(
            page("تنظیمات", settings.body("رمز جدید و تکرار آن یکسان نیست"), "settings")
        )
        return

    username = admin_username()
    if not verify_admin(username, old):
        handler.send_html(
            page("تنظیمات", settings.body("رمز فعلی اشتباه است"), "settings")
        )
        return

    try:
        set_admin_password(username, new)
    except ValueError as e:
        handler.send_html(page("تنظیمات", settings.body(str(e)), "settings"))
        return

    handler.send_html(
        page("تنظیمات", settings.body("رمز عبور با موفقیت تغییر کرد"), "settings")
    )
