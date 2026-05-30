"""HTTP request routing."""
import html
import os

from http.server import BaseHTTPRequestHandler

from client_panel.actions import auth as auth_actions
from client_panel.actions import password as password_actions
from client_panel.actions import requests as request_actions
from client_panel.components.layout import page
from client_panel.config import CLIENT_DIR
from client_panel.core.wireguard import status_for_client
from client_panel.db import db
from client_panel.server import responses, session
from client_panel.views import copy_config, dashboard, login, register, settings, support


class Handler(BaseHTTPRequestHandler):
    def send_html(self, content, code=200):
        responses.send_html(self, content, code)

    def send_plain(self, content, filename=None):
        responses.send_plain(self, content, filename)

    def send_svg(self, content, code=200):
        responses.send_svg(self, content, code)

    def redirect(self, path):
        responses.redirect(self, path)

    def post_data(self):
        return responses.post_data(self)

    def current_user(self):
        return session.current_user(self)

    def set_session(self, user_id):
        session.set_session(self, user_id)

    def render_login(self, msg=""):
        self.send_html(page("ورود", login.body(msg), auth=True))

    def render_register(self, msg=""):
        self.send_html(page("ثبت نام", register.body(msg), auth=True))

    def render_settings(self, msg=""):
        user = self.current_user()
        self.send_html(page("تنظیمات", settings.body(msg), user, "settings"))

    def do_GET(self):
        if self.path.startswith("/static/"):
            responses.serve_static(self)
            return

        user = self.current_user()
        if self.path == "/login":
            self.render_login()
            return
        if self.path == "/register":
            self.render_register()
            return
        if not user:
            self.redirect("/login")
            return

        if self.path == "/":
            if user["status"] == "pending":
                self.send_html(page("در انتظار تایید", dashboard.body_pending(), user))
                return
            if user["status"] != "approved":
                self.send_html(page("غیرفعال", dashboard.body_inactive(), user))
                return
            s = status_for_client(user["client_name"])
            if not s:
                self.send_html(page("بدون کانفیگ", dashboard.body_no_config(), user))
                return
            self.send_html(
                page("نمای کلی", dashboard.body(user, s), user, "dashboard")
            )
            return

        if self.path == "/support":
            con = db()
            rows = con.execute(
                "SELECT id,action,status,created_at FROM requests WHERE user_id=? ORDER BY id DESC",
                (user["id"],),
            ).fetchall()
            con.close()
            s = status_for_client(user["client_name"]) if user["client_name"] else None
            self.send_html(
                page("پشتیبانی", support.body(user, rows, s), user, "support")
            )
            return

        if self.path == "/settings":
            self.render_settings()
            return

        if self.path == "/config-text":
            config_text, err = responses.get_user_config_text(user)
            if err:
                self.send_html(page("خطا", f"<h1>{html.escape(err)}</h1>", user), 403)
                return
            self.send_plain(config_text)
            return

        if self.path == "/config-qr.svg":
            qr, err = responses.build_qr_svg(user)
            if err:
                self.send_response(403)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(err.encode("utf-8"))
                return
            self.send_svg(qr)
            return

        if self.path == "/config-qr":
            self.redirect("/")
            return

        if self.path == "/copy-config":
            config_text, err = responses.get_user_config_text(user)
            if err:
                self.send_html(page("خطا", f"<h1>{html.escape(err)}</h1>", user), 403)
                return
            self.send_html(page("کپی کانفیگ", copy_config.body(config_text), user))
            return

        if self.path == "/config":
            if user["status"] != "approved" or not user["client_name"]:
                self.send_html(
                    page("خطا", "<h1>کانفیگ اختصاص داده نشده</h1>", user), 403
                )
                return
            responses._ensure_valid_client_config(user["client_name"])
            conf_path = os.path.join(CLIENT_DIR, f"{user['client_name']}.conf")
            if not os.path.exists(conf_path):
                self.send_html(
                    page("خطا", "<h1>فایل کانفیگ پیدا نشد</h1>", user), 404
                )
                return
            raw = open(conf_path, "rb").read()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header(
                "Content-Disposition",
                f'attachment; filename="{user["client_name"]}.conf"',
            )
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return

        self.send_html(page("پیدا نشد", "<h1>صفحه پیدا نشد</h1>", user), 404)

    def do_POST(self):
        if self.path == "/register":
            auth_actions.handle_register(self, self.post_data())
            return
        if self.path == "/login":
            auth_actions.handle_login(self, self.post_data())
            return

        user = self.current_user()
        if not user:
            self.redirect("/login")
            return

        if self.path == "/logout":
            auth_actions.handle_logout(self)
            return
        if self.path == "/request":
            request_actions.handle_request(self, user, self.post_data())
            return
        if self.path == "/settings/password":
            password_actions.handle_change_password(self, user, self.post_data())
            return

        self.send_html(page("پیدا نشد", "<h1>صفحه پیدا نشد</h1>", user), 404)
