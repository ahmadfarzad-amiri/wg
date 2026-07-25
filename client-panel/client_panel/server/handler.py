"""HTTP request routing."""
import html
import json
import logging
import os
import re
import time
import urllib.parse

from http.server import BaseHTTPRequestHandler

log = logging.getLogger(__name__)

from client_panel.actions import auth as auth_actions
from client_panel.actions import password as password_actions
from client_panel.actions import requests as request_actions
from client_panel.components.layout import page
from client_panel.config import CLIENT_DIR
from client_panel.core import i18n
from client_panel.core.i18n import t
from client_panel.core.statuses import UserStatus
from client_panel.core.wireguard import (
    assigned_client_names_for_user,
    primary_client_for_user,
    statuses_for_user,
    status_for_client,
)
from client_panel.db import db
from client_panel.server import responses, security, session
from client_panel.views import copy_config, dashboard, login, register, settings, support


def _sub_link_page(sub_url):
    import html as _html
    url_esc = _html.escape(sub_url, quote=True)
    url_disp = _html.escape(sub_url)
    return f"""
<h1>{_html.escape(t("sub.title"))}</h1>
<p class="subtitle">{_html.escape(t("sub.hint"))}</p>
<div class="page-stack">
<section class="card">
  <h3>{_html.escape(t("sub.your_link"))}</h3>
  <p class="hint">{_html.escape(t("sub.link_hint"))}</p>
  <div class="copy-block">
    <input type="text" class="field-input copy-input" value="{url_esc}" readonly id="sub-url-input">
    <button type="button" class="btn btn-sm" data-copy-target="sub-url-input">{_html.escape(t("sub.copy"))}</button>
  </div>
  <p class="hint warn-text">{_html.escape(t("sub.security_warning"))}</p>
</section>
<section class="card">
  <h3>{_html.escape(t("sub.rotate_title"))}</h3>
  <p class="hint">{_html.escape(t("sub.rotate_hint"))}</p>
  <form method="post" action="/request">
    <input type="hidden" name="action" value="rotate-sub-token">
    <button type="submit" class="btn dark" data-confirm="{_html.escape(t("sub.rotate_confirm"), quote=True)}">{_html.escape(t("sub.rotate_btn"))}</button>
  </form>
</section>
</div>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        log.info("%s - %s", self.address_string(), fmt % args)

    def handle(self):
        try:
            super().handle()
        except Exception:
            log.exception("Unhandled client panel error on %s", self.path)
            try:
                if not self.wfile.closed:
                    self.send_error(500, "Internal Server Error")
            except Exception:
                pass

    def send_html(self, content, code=200):
        content = re.sub(
            r'(<form[^>]*method="post"[^>]*>)',
            lambda m: m.group(1) + "\n" + security.csrf_field(self),
            content,
            flags=re.I,
        )
        responses.send_html(self, content, code)

    def flash(self, path, message, variant="info"):
        security.flash_redirect(self, path, message, variant=variant)

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

    def render_login(self, msg="", variant="info"):
        i18n.begin_request(self)
        self.send_html(
            page(
                t("auth.welcome"),
                login.body(msg, variant=variant),
                auth=True,
                next_path="/login",
            )
        )

    def render_register(self, msg="", variant="error"):
        i18n.begin_request(self)
        self.send_html(
            page(
                t("auth.register_title"),
                register.body(msg, variant=variant),
                auth=True,
                next_path="/register",
            )
        )

    def render_settings(self, msg="", show_config_actions=False, variant="info"):
        i18n.begin_request(self)
        user = self.current_user()
        n_configs = len(assigned_client_names_for_user(user)) if user else 0
        has_vpn = bool(user and user.get("status") == UserStatus.APPROVED and n_configs > 0)
        if show_config_actions and msg:
            variant = "warn"
        self.send_html(
            page(
                t("page.settings"),
                settings.body(
                    msg,
                    show_config_actions,
                    config_count=max(1, n_configs),
                    has_vpn_config=has_vpn,
                    variant=variant,
                ),
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
            msg, variant = security.notice_payload_from_query(self)
            self.render_login(msg, variant=variant or "info")
            return
        if path_only == "/register":
            self.render_register()
            return
        if path_only == "/health":
            self._health()
            return
        # Unauthenticated subscription endpoint for app imports
        if path_only.startswith("/sub/"):
            self._serve_subscription(path_only[5:])
            return
        if not user:
            self.redirect("/login")
            return

        if path_only == "/":
            if user["status"] == UserStatus.PENDING:
                self.send_html(
                    page(t("page.pending"), dashboard.body_pending(), user, next_path="/")
                )
                return
            if user["status"] != UserStatus.APPROVED:
                self.send_html(
                    page(t("page.inactive"), dashboard.body_inactive(), user, next_path="/")
                )
                return
            names = assigned_client_names_for_user(user)
            if not names:
                self.send_html(
                    page(t("page.no_config"), dashboard.body_no_config(), user, next_path="/")
                )
                return
            all_statuses = statuses_for_user(user)
            primary_name = primary_client_for_user(user)
            s = status_for_client(primary_name)
            if not s:
                self.send_html(
                    page(t("page.no_config"), dashboard.body_no_config(), user, next_path="/")
                )
                return
            self.send_html(
                page(
                    t("page.dashboard"),
                    dashboard.body(user, s, all_statuses),
                    user,
                    "dashboard",
                    next_path="/",
                )
            )
            return

        if path_only == "/support":
            con = db()
            rows = con.execute(
                "SELECT id,action,status,created_at FROM requests WHERE user_id=? ORDER BY id DESC",
                (user["id"],),
            ).fetchall()
            con.close()
            primary = primary_client_for_user(user)
            s = status_for_client(primary) if primary else None
            msg, variant = security.notice_payload_from_query(self)
            self.send_html(
                page(
                    t("page.support"),
                    support.body(user, rows, s, msg=msg, variant=variant),
                    user,
                    "support",
                    next_path="/support",
                )
            )
            return

        if path_only == "/settings":
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            show_cfg = "newconfig" in params
            msg, variant = security.notice_payload_from_query(self)
            self.render_settings(msg, show_config_actions=show_cfg, variant=variant)
            return

        if path_only == "/configs.zip":
            if user["status"] != UserStatus.APPROVED:
                self.send_html(
                    page(
                        t("page.error"),
                        f"<h1>{html.escape(t('error.config_not_assigned'))}</h1>",
                        user,
                    ),
                    403,
                )
                return
            raw, err = responses.build_configs_zip(user)
            if err:
                self.send_html(page(t("page.error"), f"<h1>{html.escape(err)}</h1>", user), 403)
                return
            safe_user = "".join(
                c if c.isalnum() or c in "._-" else "_" for c in user["username"]
            )
            responses.send_zip(self, raw, f"{safe_user}-wireguard-configs.zip")
            return

        if path_only == "/config-text":
            params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            client_q = (params.get("client") or [None])[0]
            config_text, err = responses.get_user_config_text(user, client_name=client_q)
            if err:
                self.send_html(page(t("page.error"), f"<h1>{html.escape(err)}</h1>", user), 403)
                return
            self.send_plain(config_text)
            return

        if path_only == "/config-qr.svg":
            params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            client_q = (params.get("client") or [None])[0]
            qr, err = responses.build_qr_svg(user, client_name=client_q)
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

        if path_only == "/sub-link":
            self._serve_sub_link(user)
            return

        if path_only == "/connection-test":
            self._serve_connection_test(user)
            return

        if path_only == "/copy-config":
            config_text, err = responses.get_user_config_text(user)
            if err:
                self.send_html(page(t("page.error"), f"<h1>{html.escape(err)}</h1>", user), 403)
                return
            self.send_html(page(t("page.copy_config"), copy_config.body(config_text), user))
            return

        if path_only == "/config":
            if user["status"] != UserStatus.APPROVED:
                self.send_html(
                    page(
                        t("page.error"),
                        f"<h1>{html.escape(t('error.config_not_assigned'))}</h1>",
                        user,
                    ),
                    403,
                )
                return
            params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            client_q = (params.get("client") or [None])[0]
            client_name = (client_q or "").strip() or primary_client_for_user(user)
            if not client_name:
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
                responses._ensure_valid_client_config(client_name)
            except ValueError as exc:
                self.send_html(
                    page(t("page.error"), f"<h1>{html.escape(str(exc))}</h1>", user), 404
                )
                return
            conf_path = os.path.join(CLIENT_DIR, f"{client_name}.conf")
            raw = open(conf_path, "rb").read()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header(
                "Content-Disposition",
                f'attachment; filename="{client_name}.conf"',
            )
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return

        self.send_html(page(t("page.not_found"), f"<h1>{html.escape(t('page.not_found'))}</h1>", user), 404)

    def _serve_sub_link(self, user):
        """Redirect to subscription info page with the user's token displayed."""
        from client_panel.core.subscription import get_or_create_sub_token
        from client_panel.core.statuses import UserStatus

        if user["status"] != UserStatus.APPROVED:
            self.send_html(
                page(t("page.error"), f"<h1>{html.escape(t('error.config_not_assigned'))}</h1>", user), 403
            )
            return
        token = get_or_create_sub_token(user["id"])
        # Build the absolute URL using the Host header so it works behind any domain/port.
        host = self.headers.get("Host", "")
        scheme = "https" if responses._is_https(self) else "http"
        sub_url = f"{scheme}://{host}/sub/{token}"
        self.send_html(
            page(
                t("page.sub_link"),
                _sub_link_page(sub_url),
                user,
                next_path="/sub-link",
            )
        )

    def _serve_subscription(self, token):
        """Return the WireGuard config(s) for the subscription token — no login required."""
        from client_panel.core.subscription import user_by_sub_token
        from client_panel.core.statuses import UserStatus

        token = token.strip()
        user = user_by_sub_token(token)
        if not user or user["status"] != UserStatus.APPROVED:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Not found\n")
            return

        config_text, err = responses.get_user_config_text(user)
        if err or not config_text:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Config not available\n")
            return

        raw = config_text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _serve_connection_test(self, user):
        """Run a quick server-side diagnostic and return JSON results."""
        import shutil
        import subprocess as sp

        from client_panel.config import WG_IF

        results = {}

        # WireGuard interface check
        if shutil.which("wg"):
            try:
                out = sp.check_output(
                    ["wg", "show", WG_IF], text=True, stderr=sp.DEVNULL, timeout=5
                ).strip()
                results["wg_interface"] = "up" if out else "down"
            except Exception:
                results["wg_interface"] = "down"
        else:
            results["wg_interface"] = "not_installed"

        # Exit server reachability via the tunnel IP (10.200.0.1 is exit side)
        exit_ip = os.environ.get("WG_EXIT_IP", "10.200.0.1")
        try:
            ret = sp.call(
                ["ping", "-c", "1", "-W", "3", exit_ip],
                stdout=sp.DEVNULL, stderr=sp.DEVNULL, timeout=6,
            )
            results["exit_ping"] = "ok" if ret == 0 else "unreachable"
        except Exception:
            results["exit_ping"] = "error"

        # DNS resolution check via the tunnel
        try:
            import socket
            socket.setdefaulttimeout(5)
            socket.getaddrinfo("google.com", 80)
            results["dns"] = "ok"
        except Exception:
            results["dns"] = "fail"

        payload = json.dumps(results).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

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
