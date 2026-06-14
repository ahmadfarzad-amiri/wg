"""HTTP request routing."""
import html
import json
import os
import re

from http.server import BaseHTTPRequestHandler

from admin_panel.actions import active_action, auth, client as client_action, password, request, tool, user
from admin_panel.components.layout import page
from admin_panel.config import CLIENT_DIR, admin_url, strip_admin_base
from admin_panel.core import i18n
from admin_panel.core.i18n import t, tf
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
        i18n.begin_request(self)
        self.send_html(
            page(t("auth.login_title"), login.body(msg), auth=True, next_path="/login")
        )

    def _set_lang(self):
        import urllib.parse

        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        lang = (params.get("lang") or [""])[0]
        nxt = (params.get("next") or ["/"])[0]
        if not nxt.startswith("/"):
            nxt = "/"
        if lang not in ("fa", "en"):
            lang = "fa"
        nxt = strip_admin_base(nxt)
        self.send_response(302)
        i18n.set_lang_cookie(self, lang)
        self.send_header("Location", admin_url(nxt))
        self.end_headers()

    def do_GET(self):
        path = responses.clean_path(self)

        if path.startswith("/static/"):
            responses.serve_static(self)
            return

        if path == "/set-lang":
            self._set_lang()
            return

        i18n.begin_request(self)

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
                    t("nav.clients"),
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
                    t("nav.active"),
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
                page(t("nav.tools"), tools.body(security.notice_from_query(self)), "tools")
            )
        elif path == "/settings":
            self.send_html(
                page(t("nav.settings"), settings.body(security.notice_from_query(self)), "settings")
            )
        elif path.startswith("/config/"):
            self._download_config(path.split("/config/", 1)[1])
        elif path.startswith("/config-qr/"):
            self._serve_config_qr(path.split("/config-qr/", 1)[1])
        else:
            self.send_html(page(t("page.not_found"), f"<h1>{html.escape(t('page.not_found'))}</h1>"), 404)

    def do_POST(self):
        path = responses.clean_path(self)
        i18n.begin_request(self)
        data = self.post_data()

        if not security.validate_csrf(self, data):
            self.send_html(page(t("page.error"), f"<h1>{html.escape(t('csrf_error'))}</h1>"), 403)
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
            client_action.handle(self, data)
        elif path == "/client-bulk":
            client_action.handle_bulk(self, data)
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
            self.send_html(page(t("page.not_found"), f"<h1>{html.escape(t('page.not_found'))}</h1>"), 404)

    def _dashboard(self):
        self.send_html(
            page(
                t("nav.dashboard"),
                dashboard.body(dashboard_metrics()),
                "dashboard",
                extra_head='<meta http-equiv="refresh" content="60">',
            )
        )

    def _health(self):
        import shutil
        import subprocess

        from admin_panel.config import DB_PATH, WG_IF

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
        payload = {"ok": wg_ok and db_ok, "wg": wg_ok, "db": db_ok}
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(200 if payload["ok"] else 503)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _users(self):
        from admin_panel.actions.user import _fetch_users
        from admin_panel.config import DB_PATH

        msg = security.notice_from_query(self)
        users_data = []
        if not os.path.isfile(DB_PATH):
            msg = msg or t("error.db_not_found_users")
        else:
            try:
                users_data = _fetch_users()
            except Exception as exc:
                msg = msg or tf("error.db_read", err=exc)
        self.send_html(page(t("nav.users"), users.body(users_data, msg), "users"))

    def _requests(self):
        from admin_panel.config import DB_PATH

        db_err = ""
        rows = []
        if not os.path.isfile(DB_PATH):
            db_err = t("error.db_not_found_requests")
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
                db_err = tf("error.db_read", err=exc)
        self.send_html(
            page(
                t("nav.requests"),
                requests.body(rows, db_err or security.notice_from_query(self)),
                "requests",
            )
        )

    def _download_config(self, client_name):
        client_name = safe_name(client_name)
        path = os.path.join(CLIENT_DIR, f"{client_name}.conf")
        if not os.path.exists(path):
            self.send_html(
                page(
                    t("page.config_not_found"),
                    f"<h1>{html.escape(t('page.config_file_not_found'))}</h1>",
                ),
                404,
            )
            return
        with open(path, "rb") as f:
            raw = f.read()
        responses.send_config_file(self, client_name, raw)

    def _serve_config_qr(self, client_name):
        """Serve a QR code PNG for a client config — for admin QR button."""
        import shutil
        import subprocess
        import tempfile

        client_name = safe_name(client_name)
        conf_path = os.path.join(CLIENT_DIR, f"{client_name}.conf")

        if not os.path.exists(conf_path):
            self.send_html(
                page(
                    t("page.config_not_found"),
                    f"<h1>{html.escape(t('page.config_file_not_found'))}</h1>",
                ),
                404,
            )
            return

        if not shutil.which("qrencode"):
            self.send_html(
                page("QR", "<h1>qrencode not installed on server.</h1><p>Install: <code>apt install qrencode</code></p>"),
                503,
            )
            return

        tmp_path = None
        try:
            with open(conf_path, "rb") as f:
                conf_data = f.read()
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name

            subprocess.check_call(
                ["qrencode", "-o", tmp_path, "-t", "PNG", "-s", "6", "--level=M"],
                input=conf_data,
                timeout=10,
            )
            with open(tmp_path, "rb") as f:
                png_data = f.read()

            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(png_data)))
            self.send_header("Cache-Control", "no-store")
            security.apply_security_headers(self)
            self.end_headers()
            self.wfile.write(png_data)
        except Exception as exc:
            self.send_html(
                page("QR Error", f"<h1>Failed to generate QR</h1><p>{html.escape(str(exc))}</p>"),
                500,
            )
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
