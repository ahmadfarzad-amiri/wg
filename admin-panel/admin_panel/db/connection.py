"""Database access."""
import sqlite3

from admin_panel.config import DB_PATH, SESSION_FILE


def _configure(con, *, row_factory=False):
    """Apply WAL journal mode and a busy timeout to a new connection.

    WAL lets concurrent readers proceed while a write is in progress on the
    shared panel.db (used by both the client panel and admin panel processes).
    The busy_timeout prevents hard 'database is locked' crashes under load.
    """
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=3000")
    if row_factory:
        con.row_factory = sqlite3.Row
    return con


def session_db():
    con = _configure(sqlite3.connect(SESSION_FILE))
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            expires_at INTEGER NOT NULL
        )
        """
    )
    con.commit()
    return con


def panel_db():
    return _configure(sqlite3.connect(DB_PATH), row_factory=True)
