from admin_panel.components.layout import page
from admin_panel.core.client_ops import ensure_client, run_client_action
from admin_panel.core.i18n import t, tf
from admin_panel.core.shell import safe_name, tail_message
from admin_panel.core.wireguard import find_client_status
from admin_panel.db import panel_db
from admin_panel.views import users


def _fetch_users():
    try:
        con = panel_db()
        rows = con.execute(
            """
            SELECT id, username, status, COALESCE(client_name, '') AS client_name, created_at
            FROM users ORDER BY id DESC
            """
        ).fetchall()
        con.close()
        return rows
    except Exception:
        return []


def _friendly_error(output, client=""):
    text = (output or "").strip()
    if "Client state not found" in text:
        return tf("msg.client_not_found_hint", client=client)
    if "Run as root" in text:
        return tf("msg.client_needs_root", client=client)
    if "not found" in text.lower() and "wg" in text.lower():
        return t("msg.wg_files_not_found")
    return tail_message(text)


def _approve_user(username, client, *, reassigned=False):
    ok, created, create_out = ensure_client(client)
    if not ok:
        return _friendly_error(create_out, client)

    try:
        con = panel_db()
        other = con.execute(
            "SELECT username FROM users WHERE client_name=? AND username!=? LIMIT 1",
            (client, username),
        ).fetchone()
        if other:
            con.close()
            return tf(
                "msg.client_already_assigned",
                client=client,
                user=other["username"],
            )

        cur = con.execute(
            "UPDATE users SET status='approved', client_name=? WHERE username=?",
            (client, username),
        )
        con.commit()
        con.close()
        if cur.rowcount == 0:
            return t("msg.user_not_found")
    except Exception as e:
        return tf("msg.approve_user_error", err=e)

    if reassigned:
        if created:
            return tf("msg.client_created_assigned", client=client, user=username)
        return tf("msg.client_reassigned", client=client, user=username)

    if created:
        return tf("msg.user_approved_created", user=username, client=client)
    return tf("msg.user_approved_linked", user=username, client=client)


def _reject_user(username):
    try:
        con = panel_db()
        cur = con.execute(
            "UPDATE users SET status='rejected' WHERE username=?",
            (username,),
        )
        con.commit()
        con.close()
        if cur.rowcount == 0:
            return t("msg.user_not_found")
    except Exception as e:
        return tf("msg.reject_user_error", err=e)
    return tf("msg.user_rejected", user=username)


def _disable_user(username):
    try:
        con = panel_db()
        cur = con.execute(
            "UPDATE users SET status='disabled' WHERE username=?",
            (username,),
        )
        con.commit()
        con.close()
        if cur.rowcount == 0:
            return t("msg.user_not_found")
    except Exception as e:
        return tf("msg.disable_user_error", err=e)
    return tf("msg.user_disabled", user=username)


def _enable_user(username):
    client = ""
    try:
        con = panel_db()
        row = con.execute(
            "SELECT COALESCE(client_name, '') AS client_name FROM users WHERE username=?",
            (username,),
        ).fetchone()
        if not row:
            con.close()
            return t("msg.user_not_found")
        client = row["client_name"]
        cur = con.execute(
            "UPDATE users SET status='approved' WHERE username=?",
            (username,),
        )
        con.commit()
        con.close()
        if cur.rowcount == 0:
            return t("msg.user_not_found")
    except Exception as e:
        return tf("msg.enable_user_error", err=e)

    msg = tf("msg.user_enabled", user=username)
    if client:
        status = find_client_status(client)
        if status and status.get("disabled"):
            out = run_client_action("enable", client)
            if out.strip() and "ERROR" not in out:
                msg += tf("msg.client_also_enabled", client=client)
    return msg


def _change_password(username, new_password):
    new_password = (new_password or "").strip()
    if len(new_password) < 6:
        return t("msg.password_min_length")

    from admin_panel.core.user_auth import hash_password

    password_hash, salt = hash_password(new_password)
    try:
        con = panel_db()
        cur = con.execute(
            "UPDATE users SET password_hash=?, salt=? WHERE username=?",
            (password_hash, salt, username),
        )
        con.commit()
        con.close()
        if cur.rowcount == 0:
            return t("msg.user_not_found")
    except Exception as e:
        return tf("msg.change_password_error", err=e)
    return tf("msg.password_changed", user=username)


def _users_page(msg):
    return page(t("nav.users"), users.body(_fetch_users(), msg), "users")


def handle(handler, data):
    action = data.get("action", "")
    username = safe_name(data.get("username", ""))
    client = safe_name(data.get("client", ""))

    if not username:
        handler.send_html(_users_page(t("msg.username_required")))
        return

    try:
        con = panel_db()
        row = con.execute(
            "SELECT status, COALESCE(client_name, '') AS client_name FROM users WHERE username=?",
            (username,),
        ).fetchone()
        con.close()
    except Exception:
        row = None

    if not row:
        handler.send_html(_users_page(t("msg.user_not_found")))
        return

    status = row["status"]
    assigned = row["client_name"]

    if action == "approve":
        if status == "pending":
            if not client:
                client = assigned
            if not client:
                handler.send_html(_users_page(t("msg.client_required_for_approve")))
                return
            out = _approve_user(username, client)
        elif status == "disabled" and not assigned:
            if not client:
                handler.send_html(_users_page(t("msg.client_required_for_assign")))
                return
            out = _approve_user(username, client, reassigned=True)
        elif status == "rejected":
            if not client:
                client = assigned
            if not client:
                handler.send_html(_users_page(t("msg.client_required_for_approve")))
                return
            out = _approve_user(username, client)
        elif status == "approved":
            handler.send_html(_users_page(t("msg.user_already_approved")))
            return
        elif status == "disabled":
            handler.send_html(_users_page(t("msg.use_enable_button")))
            return
        else:
            handler.send_html(_users_page(t("msg.action_not_allowed")))
            return

    elif action == "reject":
        if status != "pending":
            handler.send_html(_users_page(t("msg.only_pending_reject")))
            return
        out = _reject_user(username)

    elif action == "disable":
        if status != "approved":
            handler.send_html(_users_page(t("msg.only_approved_disable")))
            return
        out = _disable_user(username)

    elif action == "enable":
        if status != "disabled":
            handler.send_html(_users_page(t("msg.only_disabled_enable")))
            return
        if not assigned:
            handler.send_html(_users_page(t("msg.assign_client_first")))
            return
        out = _enable_user(username)

    elif action == "change-password":
        out = _change_password(username, data.get("new_password", ""))

    else:
        out = t("msg.unknown_action")

    handler.send_html(_users_page(tail_message(out)))
