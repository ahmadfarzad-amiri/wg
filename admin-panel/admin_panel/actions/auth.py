from admin_panel.core.auth import verify_admin
from admin_panel.core.i18n import t
from admin_panel.server import security, session


def handle_login(handler, data):
    username = data.get("username", "")
    blocked = security.check_login_rate_limit(handler, username)
    if blocked:
        handler.render_login(blocked, variant="error")
        return
    if verify_admin(username, data.get("password", "")):
        security.clear_login_attempts(handler, username)
        session.set_session(handler)
        return
    security.record_login_failure(handler, username)
    handler.render_login(t("auth.bad_credentials"), variant="error")


def handle_logout(handler):
    session.clear_session(handler)
