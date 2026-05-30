from admin_panel.components.layout import page
from admin_panel.core.auth import verify_admin
from admin_panel.core.i18n import t
from admin_panel.server import security, session
from admin_panel.views import login


def handle_login(handler, data):
    username = data.get("username", "")
    blocked = security.check_login_rate_limit(handler, username)
    if blocked:
        handler.send_html(page(t("auth.login_title"), login.body(blocked), auth=True), 429)
        return
    if verify_admin(username, data.get("password", "")):
        security.clear_login_attempts(handler, username)
        session.set_session(handler)
        return
    security.record_login_failure(handler, username)
    handler.send_html(
        page(t("auth.login_title"), login.body(t("auth.bad_credentials")), auth=True),
        403,
    )


def handle_logout(handler):
    session.clear_session(handler)
