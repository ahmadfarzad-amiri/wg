"""HTTP request routing."""
import json
import os
import re

from http.server import BaseHTTPRequestHandler

from admin_panel.actions import active_action, auth, client, password, request, tool, user
from admin_panel.components.layout import page
from admin_panel.config import CLIENT_DIR
from admin_panel.core.shell import safe_name
from admin_panel.core.analytics import dashboard_metrics
from admin_panel.core.wireguard import active_list_hint, all_client_status, build_wg_snapshot
from admin_panel.db import panel_db
from admin_panel.server import responses, security, session
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
        content = re.sub(
            r'(<form[^>]*method="post"[^>]*>)',
            lambda m: m.group(1) + "\n" + security.csrf_field(self),
            content,
            flags=re.I,
        )
        responses.send_html(self, content, code)

    def flash(self, path, message):
        responses.flash_redirect(self, path, message)

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
            self.render_login(security.notice_from_query(self))
            return

        if path == "/health":
            self._health()
            return

        if not session.require_login(self):
            return

        if path == "/":
            self._dashboard()
        elif path == "/clients":
            snap = build_wg_snapshot()
            self.send_html(
                page(
                    "کلاینت‌ها",
                    clients.body(all_client_status(snap), security.notice_from_query(self)),
                    "clients",
                )
            )
        elif path == "/users":
            self._users()
        elif path == "/requests":
            self._requests()
        elif path == "/active":
            snap = build_wg_snapshot()
            online = [c for c in all_client_status(snap) if c["active"]]
            self.send_html(
                page(
                    "آنلاین",
                    active.body(
                        online,
                        security.notice_from_query(self),
                        wg_hint=active_list_hint(),
                    ),
                    "active",
                    extra_head='<meta http-equiv="refresh" content="45">',
                )
            )
        elif path == "/tools":
            self.send_html(
                page("ابزارها", tools.body(security.notice_from_query(self)), "tools")
            )
        elif path == "/settings":
            self.send_html(
                page("تنظیمات", settings.body(security.notice_from_query(self)), "settings")
            )
        elif path.startswith("/config/"):
            self._download_config(path.split("/config/", 1)[1])
        else:
            self.send_html(page("پیدا نشد", "<h1>صفحه پیدا نشد</h1>"), 404)

    def do_POST(self):
        path = responses.clean_path(self)
        data = self.post_data()

        if not security.validate_csrf(self, data):
            self.send_html(page("خطا", "<h1>درخواست نامعتبر (CSRF)</h1>"), 403)
            return

        if path == "/login":
            auth.handle_login(self, data)
            return

        if not session.require_login(self):
            return

        if path == "/logout":
            auth.handle_logout(self)
            return

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
            page(
                "داشبورد",
                dashboard.body(dashboard_metrics()),
                "dashboard",
                extra_head='<meta http-equiv="refresh" content="60">',
            )
        )

    def _health(self):
        import shutil

        from admin_panel.config import DB_PATH, WG_IF

        wg_ok = bool(shutil.which("wg"))
        if wg_ok:
            try:
                wg_ok = os.popen(f"wg show {WG_IF} 2>/dev/null").read().strip() != ""
            except Exception:
                wg_ok = False
        db_ok = os.path.isfile(DB_PATH)
        payload = {"ok": wg_ok and db_ok, "wg": wg_ok, "db": db_ok}
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(200 if payload["ok"] else 503)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _users(self):
        from admin_panel.config import DB_PATH

        db_err = ""
        rows = []
        if not os.path.isfile(DB_PATH):
            db_err = "پایگاه داده panel.db پیدا نشد — کاربران نمایش داده نمی‌شوند."
        else:
            try:
                con = panel_db()
                rows = con.execute(
                    """
                    SELECT id, username, status, COALESCE(client_name, '') AS client_name, created_at
                    FROM users ORDER BY id DESC
                    """
                ).fetchall()
                con.close()
            except Exception as exc:
                db_err = f"خطا در خواندن پایگاه داده: {exc}"
        self.send_html(
            page("کاربران", users.body(rows, db_err or security.notice_from_query(self)), "users")
        )

    def _requests(self):
        from admin_panel.config import DB_PATH

        db_err = ""
        rows = []
        if not os.path.isfile(DB_PATH):
            db_err = "پایگاه داده panel.db پیدا نشد — درخواست‌ها نمایش داده نمی‌شوند."
        else:
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
            except Exception as exc:
                db_err = f"خطا در خواندن پایگاه داده: {exc}"
        self.send_html(
            page(
                "درخواست‌ها",
                requests.body(rows, db_err or security.notice_from_query(self)),
                "requests",
            )
        )

    def _download_config(self, client_name):
        client_name = safe_name(client_name)
        path = os.path.join(CLIENT_DIR, f"{client_name}.conf")
        if not os.path.exists(path):
            self.send_html(page("پیدا نشد", "<h1>فایل کانفیگ پیدا نشد</h1>"), 404)
            return
        with open(path, "rb") as f:
            raw = f.read()
        responses.send_config_file(self, client_name, raw)
