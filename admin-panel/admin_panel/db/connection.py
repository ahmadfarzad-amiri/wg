"""Database access."""
import sqlite3

from admin_panel.config import DB_PATH, SESSION_FILE


def session_db():
    con = sqlite3.connect(SESSION_FILE)
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
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con
