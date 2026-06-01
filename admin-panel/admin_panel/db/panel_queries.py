"""Read-only panel database queries."""
from admin_panel.db.connection import panel_db


def _user_configs_mod():
    from client_panel.db import user_configs

    return user_configs


def assigned_client_names():
    try:
        return _user_configs_mod().all_assigned_client_names()
    except Exception:
        return set()


def users_for_client(client_name):
    try:
        m = _user_configs_mod().users_by_client_map()
        return m.get(client_name, [])
    except Exception:
        return []


def users_by_client():
    try:
        return _user_configs_mod().users_by_client_map()
    except Exception:
        return {}


def configs_for_user_id(user_id):
    try:
        return _user_configs_mod().configs_for_user(user_id)
    except Exception:
        return []


def detach_users_from_client(client_name):
    try:
        mod = _user_configs_mod()
        uid = mod.user_id_for_client(client_name)
        if uid is None:
            return []
        con = panel_db()
        rows = con.execute(
            "SELECT username FROM users WHERE id=?", (uid,)
        ).fetchall()
        usernames = [row["username"] for row in rows]
        mod.unassign_config(uid, client_name)
        remaining = mod.client_names_for_user(uid)
        if not remaining:
            con.execute(
                "UPDATE users SET client_name='', status='disabled' WHERE id=?",
                (uid,),
            )
        con.commit()
        con.close()
        return usernames
    except Exception:
        return []
