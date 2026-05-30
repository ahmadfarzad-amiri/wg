"""Read-only panel database queries."""
from admin_panel.db.connection import panel_db


def assigned_client_names():
    try:
        con = panel_db()
        rows = con.execute(
            "SELECT DISTINCT client_name FROM users WHERE COALESCE(client_name, '') != ''"
        ).fetchall()
        con.close()
        return {row["client_name"] for row in rows}
    except Exception:
        return set()


def users_for_client(client_name):
    try:
        con = panel_db()
        rows = con.execute(
            "SELECT username FROM users WHERE client_name=? ORDER BY username",
            (client_name,),
        ).fetchall()
        con.close()
        return [row["username"] for row in rows]
    except Exception:
        return []


def users_by_client():
    try:
        con = panel_db()
        rows = con.execute(
            """
            SELECT username, client_name
            FROM users
            WHERE COALESCE(client_name, '') != ''
            ORDER BY username
            """
        ).fetchall()
        con.close()
        result = {}
        for row in rows:
            result.setdefault(row["client_name"], []).append(row["username"])
        return result
    except Exception:
        return {}


def detach_users_from_client(client_name):
    usernames = users_for_client(client_name)
    if not usernames:
        return []

    try:
        con = panel_db()
        con.execute(
            "UPDATE users SET client_name='', status='disabled' WHERE client_name=?",
            (client_name,),
        )
        con.commit()
        con.close()
    except Exception:
        return []

    return usernames
