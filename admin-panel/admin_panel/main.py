"""Application entry point."""
import os

from http.server import ThreadingHTTPServer

from admin_panel.config import ADMIN_CONFIG, HOST, PORT, SESSION_FILE
from admin_panel.db import session_db
from admin_panel.server import Handler


def run():
    if not os.path.exists(ADMIN_CONFIG):
        print("Admin config missing. Run: wg-admin-set-password")
        raise SystemExit(1)
    os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
    session_db().close()
    try:
        from client_panel.db.user_configs import ensure_user_configs_schema

        ensure_user_configs_schema()
    except Exception as exc:
        print(f"Warning: user_configs schema check failed: {exc}")
    print(f"Starting admin panel on {HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
