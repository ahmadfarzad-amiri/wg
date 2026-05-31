"""HTTP request routing."""
import html
import json
import os
import re
import time
import urllib.parse

from http.server import BaseHTTPRequestHandler

from client_panel.actions import auth as auth_actions
from client_panel.actions import password as password_actions
from client_panel.actions import requests as request_actions
from client_panel.components.layout import page
from client_panel.config import CLIENT_DIR
from client_panel.core import i18n
from client_panel.core.i18n import t
from client_panel.core.wireguard import status_for_client
from client_panel.db import db
from client_panel.server import responses, security, session
from client_panel.views import copy_config, dashboard, login, register, settings, support


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
        security.flash_redirect(self, path, message)

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
        i18n.begin_request(self)
        self.send_html(page(t("auth.welcome"), login.body(msg), auth=True, next_path="/login"))

    def render_register(self, msg=""):
        i18n.begin_request(self)
        self.send_html(
            page(t("auth.register_title"), register.body(msg), auth=True, next_path="/register")
        )

    def render_settings(self, msg="", show_config_actions=False):
        i18n.begin_request(self)
        user = self.current_user()
        self.send_html(
            page(
                t("page.settings"),
                settings.body(msg, show_config_actions),
                user,
                "settings",
                next_path="/settings",
            )
        )

    def _set_lang(self):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        lang = (params.get("lang") or [""])[0]
        nxt = (params.get("next") or ["/"])[0]
        if not nxt.startswith("/"):
            nxt = "/"
        if lang not in ("fa", "en"):
            lang = "fa"
        self.send_response(302)
        i18n.set_lang_cookie(self, lang)
        self.send_header("Location", nxt)
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/static/"):
            responses.serve_static(self)
            return

        path_only = self.path.split("?", 1)[0]
        if path_only == "/set-lang":
            self._set_lang()
            return

        i18n.begin_request(self)
        user = self.current_user()
        if path_only == "/login":
            self.render_login(security.notice_from_query(self))
            return
        if path_only == "/register":
            self.render_register()
            return
        if path_only == "/health":
            self._health()
            return
        if not user:
            self.redirect("/login")
            return

        if path_only == "/":
            if user["status"] == "pending":
                self.send_html(
                    page(t("page.pending"), dashboard.body_pending(), user, next_path="/")
                )
                return
            if user["status"] != "approved":
                self.send_html(
                    page(t("page.inactive"), dashboard.body_inactive(), user, next_path="/")
                )
                return
            s = status_for_client(user["client_name"])
            if not s:
                self.send_html(
                    page(t("page.no_config"), dashboard.body_no_config(), user, next_path="/")
                )
                return
            self.send_html(
                page(t("page.dashboard"), dashboard.body(user, s), user, "dashboard", next_path="/")
            )
            return

        if path_only == "/support":
            con = db()
            rows = con.execute(
                "SELECT id,action,status,created_at FROM requests WHERE user_id=? ORDER BY id DESC",
                (user["id"],),
            ).fetchall()
            con.close()
            s = status_for_client(user["client_name"]) if user["client_name"] else None
            self.send_html(
                page(t("page.support"), support.body(user, rows, s), user, "support", next_path="/support")
            )
            return

        if path_only == "/settings":
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            show_cfg = "newconfig" in params
            self.render_settings(security.notice_from_query(self), show_config_actions=show_cfg)
            return

        if path_only == "/config-text":
            config_text, err = responses.get_user_config_text(user)
            if err:
                self.send_html(page(t("page.error"), f"<h1>{html.escape(err)}</h1>", user), 403)
                return
            self.send_plain(config_text)
            return

        if path_only == "/config-qr.svg":
            qr, err = responses.build_qr_svg(user)
            if err:
                self.send_response(403)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(err.encode("utf-8"))
                return
            self.send_svg(qr)
            return

        if path_only == "/config-qr":
            self.redirect("/?qr=1")
            return

        if path_only == "/copy-config":
            config_text, err = responses.get_user_config_text(user)
            if err:
                self.send_html(page(t("page.error"), f"<h1>{html.escape(err)}</h1>", user), 403)
                return
            self.send_html(page(t("page.copy_config"), copy_config.body(config_text), user))
            return

        if path_only == "/config":
            if user["status"] != "approved" or not user["client_name"]:
                self.send_html(
                    page(
                        t("page.error"),
                        f"<h1>{html.escape(t('error.config_not_assigned'))}</h1>",
                        user,
                    ),
                    403,
                )
                return
            try:
                responses._ensure_valid_client_config(user["client_name"])
            except ValueError as exc:
                self.send_html(
                    page(t("page.error"), f"<h1>{html.escape(str(exc))}</h1>", user), 404
                )
                return
            conf_path = os.path.join(CLIENT_DIR, f"{user['client_name']}.conf")
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

        self.send_html(page(t("page.not_found"), f"<h1>{html.escape(t('page.not_found'))}</h1>", user), 404)

    def _health(self):
        import shutil
        import subprocess

        from client_panel.config import DB_PATH, WG_IF

        wg_ok = bool(shutil.which("wg"))
        if wg_ok:
            try:
                out = subprocess.check_output(
                    ["wg", "show", WG_IF],
                    text=True,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                ).strip()
                wg_ok = bool(out)
            except Exception:
                wg_ok = False
        db_ok = os.path.isfile(DB_PATH)
        payload = {
            "ok": wg_ok and db_ok,
            "wg": wg_ok,
            "db": db_ok,
        }
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(200 if payload["ok"] else 503)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        path_only = self.path.split("?", 1)[0]
        i18n.begin_request(self)
        data = self.post_data()
        if not security.validate_csrf(self, data):
            self.send_html(page(t("page.error"), f"<h1>{html.escape(t('csrf_error'))}</h1>"), 403)
            return

        if path_only == "/register":
            auth_actions.handle_register(self, data)
            return
        if path_only == "/login":
            auth_actions.handle_login(self, data)
            return

        user = self.current_user()
        if not user:
            self.redirect("/login")
            return

        if path_only == "/logout":
            auth_actions.handle_logout(self)
            return
        if path_only == "/request":
            request_actions.handle_request(self, user, data)
            return
        if path_only == "/settings/password":
            password_actions.handle_change_password(self, user, data)
            return

        self.send_html(page(t("page.not_found"), f"<h1>{html.escape(t('page.not_found'))}</h1>", user), 404)
