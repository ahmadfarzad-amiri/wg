"""Application entry point."""
import os
from http.server import ThreadingHTTPServer

from client_panel.config import DB_PATH, HOST, PORT, REQ_DIR
from client_panel.db import db
from client_panel.server import Handler


def run():
    try:
        os.makedirs(REQ_DIR, exist_ok=True)
    except OSError:
        pass
    db().close()
    if os.path.exists(DB_PATH):
        os.chmod(DB_PATH, 0o600)
    print(f"Starting client panel on {HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    run()
