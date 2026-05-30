from admin_panel.components.layout import page
from admin_panel.core.auth import verify_admin
from admin_panel.server import session
from admin_panel.views import login


def handle_login(handler, data):
    if verify_admin(data.get("username", ""), data.get("password", "")):
        session.set_session(handler)
        return
    handler.send_html(page("ورود", login.body("نام کاربری یا رمز عبور اشتباه است"), auth=True), 403)


def handle_logout(handler):
    session.clear_session(handler)
