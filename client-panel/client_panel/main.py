"""Application entry point."""
import logging
import os
from http.server import ThreadingHTTPServer

from client_panel.config import DB_PATH, HOST, PORT, REQ_DIR
from client_panel.db import db
from client_panel.server import Handler

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def run():
    try:
        os.makedirs(REQ_DIR, exist_ok=True)
    except OSError:
        pass
    try:
        db().close()
        if os.path.exists(DB_PATH):
            os.chmod(DB_PATH, 0o600)
    except Exception as exc:
        print(f"Warning: database init failed: {exc}", flush=True)
    print(f"Starting client panel on {HOST}:{PORT}", flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    run()
