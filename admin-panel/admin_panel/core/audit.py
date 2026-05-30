"""Admin action audit log."""
import os
import sqlite3
import time

from admin_panel.config import SESSION_FILE


def _audit_path():
    return os.environ.get("WG_ADMIN_AUDIT_FILE", SESSION_FILE.replace(".db", "-audit.db"))


def _db():
    path = _audit_path()
    con = sqlite3.connect(path)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            detail TEXT,
            created_at INTEGER NOT NULL
        )
        """
    )
    return con


def log_admin_action(action, detail=""):
    try:
        con = _db()
        con.execute(
            "INSERT INTO audit_log(action, detail, created_at) VALUES(?,?,?)",
            (action, detail or "", int(time.time())),
        )
        con.commit()
        con.close()
    except Exception:
        pass


def recent_audit(limit=20):
    try:
        con = _db()
        rows = con.execute(
            "SELECT action, detail, created_at FROM audit_log ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        con.close()
        return rows
    except Exception:
        return []
