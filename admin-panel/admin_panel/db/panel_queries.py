"""Read-only panel database queries."""
import logging

from admin_panel.db.connection import panel_db
from wg_common.statuses import UserStatus

log = logging.getLogger(__name__)


def _user_configs_mod():
    from client_panel.db import user_configs

    return user_configs


def assigned_client_names():
    try:
        return _user_configs_mod().all_assigned_client_names()
    except Exception:
        log.exception("assigned_client_names failed")
        return set()


def users_for_client(client_name):
    try:
        m = _user_configs_mod().users_by_client_map()
        return m.get(client_name, [])
    except Exception:
        log.exception("users_for_client failed for %s", client_name)
        return []


def users_by_client():
    try:
        return _user_configs_mod().users_by_client_map()
    except Exception:
        log.exception("users_by_client failed")
        return {}


def configs_for_user_id(user_id):
    try:
        return _user_configs_mod().configs_for_user(user_id)
    except Exception:
        log.exception("configs_for_user_id failed for user_id=%s", user_id)
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
                "UPDATE users SET client_name='', status=? WHERE id=?",
                (UserStatus.DISABLED, uid),
            )
        con.commit()
        con.close()
        return usernames
    except Exception:
        log.exception("detach_users_from_client failed for %s", client_name)
        return []
