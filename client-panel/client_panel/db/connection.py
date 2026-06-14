"""SQLite database access."""
import sqlite3

from client_panel.config import DB_PATH


def _configure(con):
    """Apply WAL journal mode and a busy timeout to a new connection.

    WAL lets concurrent readers proceed while a write is in progress on the
    shared panel.db (used by both the client panel and admin panel processes).
    The busy_timeout prevents hard 'database is locked' crashes under load.
    """
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=3000")
    con.row_factory = sqlite3.Row
    return con


def db():
    con = _configure(sqlite3.connect(DB_PATH))
    con.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        client_name TEXT,
        created_at INTEGER NOT NULL
    )
    """)
    con.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        expires_at INTEGER NOT NULL
    )
    """)
    con.execute("""
    CREATE TABLE IF NOT EXISTS requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at INTEGER NOT NULL,
        processed_at INTEGER,
        note TEXT
    )
    """)
    from client_panel.db.user_configs import ensure_user_configs_schema

    ensure_user_configs_schema(con)
    con.commit()
    return con


def raw_db(path):
    """Open an arbitrary SQLite file with WAL + busy timeout."""
    return _configure(sqlite3.connect(path))
