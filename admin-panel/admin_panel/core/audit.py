"""Admin action audit log."""
import logging
import os
import sqlite3
import time

from admin_panel.config import SESSION_FILE

log = logging.getLogger(__name__)


def _audit_path():
    return os.environ.get("WG_ADMIN_AUDIT_FILE", SESSION_FILE.replace(".db", "-audit.db"))


def _db():
    path = _audit_path()
    con = sqlite3.connect(path)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=3000")
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor TEXT NOT NULL DEFAULT '',
            ip TEXT NOT NULL DEFAULT '',
            action TEXT NOT NULL,
            detail TEXT,
            created_at INTEGER NOT NULL
        )
        """
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at DESC)"
    )
    return con


def log_admin_action(action, detail="", *, actor="", ip=""):
    """Record an admin action.

    actor: admin username performing the action
    ip: client IP of the admin request
    """
    try:
        con = _db()
        con.execute(
            "INSERT INTO audit_log(actor, ip, action, detail, created_at) VALUES(?,?,?,?,?)",
            (actor or "", ip or "", action, detail or "", int(time.time())),
        )
        con.commit()
        con.close()
    except Exception:
        log.exception("log_admin_action failed for action=%s", action)


def recent_audit(limit=50):
    try:
        con = _db()
        rows = con.execute(
            "SELECT actor, ip, action, detail, created_at FROM audit_log ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        con.close()
        return rows
    except Exception:
        log.exception("recent_audit failed")
        return []
