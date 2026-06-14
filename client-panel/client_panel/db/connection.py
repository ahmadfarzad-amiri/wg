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
        sub_token TEXT,
        created_at INTEGER NOT NULL
    )
    """)
    # Add sub_token column if upgrading from older schema (idempotent).
    try:
        con.execute("ALTER TABLE users ADD COLUMN sub_token TEXT")
    except Exception:
        pass  # column already exists
    con.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        expires_at INTEGER NOT NULL
    )
    """)
    con.execute(
        "CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at)"
    )
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
    con.execute(
        "CREATE INDEX IF NOT EXISTS idx_requests_user ON requests(user_id)"
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS idx_requests_status ON requests(status)"
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS idx_users_status ON users(status)"
    )
    from client_panel.db.user_configs import ensure_user_configs_schema

    ensure_user_configs_schema(con)
    con.commit()
    return con


def raw_db(path):
    """Open an arbitrary SQLite file with WAL + busy timeout."""
    return _configure(sqlite3.connect(path))
