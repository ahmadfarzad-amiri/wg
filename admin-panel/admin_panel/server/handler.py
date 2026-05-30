"""HTTP request routing."""
import os

from http.server import BaseHTTPRequestHandler

from admin_panel.actions import active_action, auth, client, password, request, tool, user
from admin_panel.components.layout import page
from admin_panel.config import CLIENT_DIR
from admin_panel.core.shell import safe_name
from admin_panel.core.analytics import dashboard_metrics
from admin_panel.core.wireguard import active_list_hint, all_client_status
from admin_panel.db import panel_db
from admin_panel.server import responses, session
from admin_panel.views import (
    active,
    clients,
    dashboard,
    login,
    requests,
    settings,
    tools,
    users,
)


class Handler(BaseHTTPRequestHandler):
    def send_html(self, content, code=200):
        responses.send_html(self, content, code)

    def redirect(self, path):
        responses.redirect(self, path)

    def post_data(self):
        return responses.post_data(self)

    def render_login(self, msg=""):
        self.send_html(page("ورود", login.body(msg), auth=True))

    def do_GET(self):
        path = responses.clean_path(self)

        if path.startswith("/static/"):
            responses.serve_static(self)
            return

        if path == "/login":
            self.render_login()
            return

        if not session.require_login(self):
            return

        if path == "/":
            self._dashboard()
        elif path == "/clients":
            self.send_html(page("کلاینت‌ها", clients.body(all_client_status()), "clients"))
        elif path == "/users":
            self._users()
        elif path == "/requests":
            self._requests()
        elif path == "/active":
            online = [c for c in all_client_status() if c["active"]]
            self.send_html(
                page(
                    "آنلاین",
                    active.body(online, wg_hint=active_list_hint()),
                    "active",
                )
            )
        elif path == "/tools":
            self.send_html(page("ابزارها", tools.body(), "tools"))
        elif path == "/settings":
            self.send_html(page("تنظیمات", settings.body(), "settings"))
        elif path.startswith("/config/"):
            self._download_config(path.split("/config/", 1)[1])
        else:
            self.send_html(page("پیدا نشد", "<h1>صفحه پیدا نشد</h1>"), 404)

    def do_POST(self):
        path = responses.clean_path(self)

        if path == "/login":
            auth.handle_login(self, self.post_data())
            return

        if not session.require_login(self):
            return

        if path == "/logout":
            auth.handle_logout(self)
            return

        data = self.post_data()

        if path == "/client-action":
            client.handle(self, data)
        elif path == "/user-action":
            user.handle(self, data)
        elif path == "/request-action":
            request.handle(self, data)
        elif path == "/tool-action":
            tool.handle(self, data)
        elif path == "/active-action":
            active_action.handle(self, data)
        elif path == "/settings/password":
            password.handle_change_password(self, data)
        else:
            self.send_html(page("پیدا نشد", "<h1>صفحه پیدا نشد</h1>"), 404)

    def _dashboard(self):
        self.send_html(
            page("داشبورد", dashboard.body(dashboard_metrics()), "dashboard")
        )

    def _users(self):
        try:
            con = panel_db()
            rows = con.execute(
                """
                SELECT id, username, status, COALESCE(client_name, '') AS client_name, created_at
                FROM users ORDER BY id DESC
                """
            ).fetchall()
            con.close()
        except Exception:
            rows = []
        self.send_html(page("کاربران", users.body(rows), "users"))

    def _requests(self):
        try:
            con = panel_db()
            rows = con.execute(
                """
                SELECT requests.id, users.username, users.client_name,
                       requests.action, requests.status, requests.created_at
                FROM requests JOIN users ON users.id = requests.user_id
                ORDER BY requests.id DESC
                """
            ).fetchall()
            con.close()
        except Exception:
            rows = []
        self.send_html(page("درخواست‌ها", requests.body(rows), "requests"))

    def _download_config(self, client_name):
        client_name = safe_name(client_name)
        path = os.path.join(CLIENT_DIR, f"{client_name}.conf")
        if not os.path.exists(path):
            self.send_html(page("پیدا نشد", "<h1>فایل کانفیگ پیدا نشد</h1>"), 404)
            return
        with open(path, "rb") as f:
            raw = f.read()
        responses.send_config_file(self, client_name, raw)
