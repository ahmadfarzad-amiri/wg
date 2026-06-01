"""Many-to-many assignment of WireGuard client configs to panel users."""
import time

from client_panel.db.connection import db


def _migrate_legacy_assignments(con):
    con.execute(
        """
        INSERT OR IGNORE INTO user_configs (user_id, client_name, sort_order, created_at)
        SELECT id, client_name,
               0,
               COALESCE(created_at, ?)
        FROM users
        WHERE COALESCE(client_name, '') != ''
        """,
        (int(time.time()),),
    )


def ensure_user_configs_schema(con=None):
    own = con is None
    if own:
        con = db()
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS user_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            client_name TEXT NOT NULL,
            label TEXT,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL,
            UNIQUE(user_id, client_name),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_configs_user ON user_configs(user_id)"
    )
    _migrate_legacy_assignments(con)
    if own:
        con.commit()
        con.close()


def configs_for_user(user_id):
    ensure_user_configs_schema()
    con = db()
    rows = con.execute(
        """
        SELECT client_name, COALESCE(label, '') AS label, sort_order
        FROM user_configs
        WHERE user_id=?
        ORDER BY sort_order ASC, id ASC
        """,
        (user_id,),
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]


def client_names_for_user(user_id):
    return [r["client_name"] for r in configs_for_user(user_id)]


def primary_client_name(user_id, fallback=""):
    names = client_names_for_user(user_id)
    if names:
        return names[0]
    return fallback


def sync_primary_client_name(con, user_id):
    primary = primary_client_name(user_id, "")
    con.execute(
        "UPDATE users SET client_name=? WHERE id=?",
        (primary, user_id),
    )


def user_id_for_client(client_name):
    if not client_name:
        return None
    ensure_user_configs_schema()
    con = db()
    row = con.execute(
        "SELECT user_id FROM user_configs WHERE client_name=? LIMIT 1",
        (client_name,),
    ).fetchone()
    con.close()
    return row["user_id"] if row else None


def username_for_client(client_name):
    uid = user_id_for_client(client_name)
    if uid is None:
        return None
    con = db()
    row = con.execute("SELECT username FROM users WHERE id=?", (uid,)).fetchone()
    con.close()
    return row["username"] if row else None


def assign_config(user_id, client_name, label=None):
    client_name = (client_name or "").strip()
    if not client_name:
        return False, "empty_client"
    other = user_id_for_client(client_name)
    if other is not None and other != user_id:
        return False, "assigned_other"
    ensure_user_configs_schema()
    con = db()
    now = int(time.time())
    max_order = con.execute(
        "SELECT COALESCE(MAX(sort_order), -1) FROM user_configs WHERE user_id=?",
        (user_id,),
    ).fetchone()[0]
    con.execute(
        """
        INSERT INTO user_configs (user_id, client_name, label, sort_order, created_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id, client_name) DO UPDATE SET
            label=COALESCE(excluded.label, user_configs.label)
        """,
        (user_id, client_name, label, max_order + 1, now),
    )
    sync_primary_client_name(con, user_id)
    con.commit()
    con.close()
    return True, None


def unassign_config(user_id, client_name):
    ensure_user_configs_schema()
    con = db()
    con.execute(
        "DELETE FROM user_configs WHERE user_id=? AND client_name=?",
        (user_id, client_name),
    )
    sync_primary_client_name(con, user_id)
    con.commit()
    con.close()


def all_assigned_client_names():
    ensure_user_configs_schema()
    con = db()
    rows = con.execute(
        "SELECT DISTINCT client_name FROM user_configs WHERE client_name != ''"
    ).fetchall()
    con.close()
    return {row["client_name"] for row in rows}


def users_by_client_map():
    ensure_user_configs_schema()
    con = db()
    rows = con.execute(
        """
        SELECT u.username, uc.client_name
        FROM user_configs uc
        JOIN users u ON u.id = uc.user_id
        ORDER BY uc.client_name, u.username
        """
    ).fetchall()
    con.close()
    result = {}
    for row in rows:
        result.setdefault(row["client_name"], []).append(row["username"])
    return result
