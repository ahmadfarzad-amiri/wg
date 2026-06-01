from admin_panel.components.layout import page
from admin_panel.core.client_ops import ensure_client, run_client_action
from admin_panel.core.i18n import t, tf
from admin_panel.core.shell import safe_name, tail_message
from admin_panel.core.wireguard import find_client_status
from admin_panel.db.panel_queries import configs_for_user_id
from admin_panel.views import users


def _fetch_users():
    try:
        from client_panel.db.user_configs import configs_for_user

        con_users = __import__(
            "admin_panel.db.connection", fromlist=["panel_db"]
        ).panel_db()
        rows = con_users.execute(
            """
            SELECT id, username, status, COALESCE(client_name, '') AS client_name, created_at
            FROM users ORDER BY id DESC
            """
        ).fetchall()
        con_users.close()
        result = []
        from admin_panel.core.wireguard import find_client_meta_by_name

        for row in rows:
            u = dict(row)
            configs = configs_for_user(u["id"])
            for cfg in configs:
                meta = find_client_meta_by_name(cfg["client_name"])
                cfg["vpn_mode"] = (
                    (meta.get("VPN_MODE") or "twohop").lower() if meta else "twohop"
                )
            u["configs"] = configs
            result.append(u)
        return result
    except Exception:
        return []


def _friendly_error(output, client=""):
    text = (output or "").strip()
    if "Client state not found" in text:
        return tf("msg.client_not_found_hint", client=client)
    if "Run as root" in text:
        return tf("msg.client_needs_root", client=client)
    if "timed out" in text.lower():
        return tf("msg.client_cmd_timeout", client=client)
    if "not found" in text.lower() and "wg" in text.lower():
        return t("msg.wg_files_not_found")
    return tail_message(text)


def _user_row(con, username):
    return con.execute(
        "SELECT id, username, status, COALESCE(client_name, '') AS client_name FROM users WHERE username=?",
        (username,),
    ).fetchone()


def _approve_user(username, client, *, reassigned=False):
    from client_panel.db import user_configs

    ok, _, create_out = ensure_client(client)
    if not ok:
        return _friendly_error(create_out, client)

    try:
        con = __import__(
            "admin_panel.db.connection", fromlist=["panel_db"]
        ).panel_db()
        row = _user_row(con, username)
        if not row:
            con.close()
            return t("msg.user_not_found")

        other_user = user_configs.username_for_client(client)
        if other_user and other_user != username:
            con.close()
            return tf(
                "msg.client_already_assigned",
                client=client,
                user=other_user,
            )

        ok_assign, err = user_configs.assign_config(row["id"], client)
        if not ok_assign:
            con.close()
            if err == "assigned_other":
                other = user_configs.username_for_client(client) or "?"
                return tf(
                    "msg.client_already_assigned",
                    client=client,
                    user=other,
                )
            return t("msg.assign_config_failed")

        con.execute(
            "UPDATE users SET status='approved', client_name=? WHERE username=?",
            (user_configs.primary_client_name(row["id"], client), username),
        )
        con.commit()
        con.close()
    except Exception as e:
        return tf("msg.approve_user_error", err=e)

    if reassigned:
        if create_out and "Created client" in create_out:
            return tf("msg.client_created_assigned", client=client, user=username)
        return tf("msg.client_reassigned", client=client, user=username)

    if create_out and "Created client" in create_out:
        return tf("msg.user_approved_created", user=username, client=client)
    return tf("msg.user_approved_linked", user=username, client=client)


def _reject_user(username):
    try:
        con = __import__(
            "admin_panel.db.connection", fromlist=["panel_db"]
        ).panel_db()
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
        con = __import__(
            "admin_panel.db.connection", fromlist=["panel_db"]
        ).panel_db()
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
    from client_panel.db.user_configs import client_names_for_user, primary_client_name

    try:
        con = __import__(
            "admin_panel.db.connection", fromlist=["panel_db"]
        ).panel_db()
        row = _user_row(con, username)
        if not row:
            con.close()
            return t("msg.user_not_found")
        names = client_names_for_user(row["id"])
        if not names and not row["client_name"]:
            con.close()
            return t("msg.assign_client_first")
        primary = primary_client_name(row["id"], row["client_name"])
        cur = con.execute(
            "UPDATE users SET status='approved', client_name=? WHERE username=?",
            (primary, username),
        )
        con.commit()
        con.close()
        if cur.rowcount == 0:
            return t("msg.user_not_found")
    except Exception as e:
        return tf("msg.enable_user_error", err=e)

    msg = tf("msg.user_enabled", user=username)
    for client in names or ([row["client_name"]] if row["client_name"] else []):
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
        con = __import__(
            "admin_panel.db.connection", fromlist=["panel_db"]
        ).panel_db()
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
    from client_panel.db import user_configs

    action = data.get("action", "")
    username = safe_name(data.get("username", ""))
    client = safe_name(data.get("client", ""))

    if not username:
        handler.send_html(_users_page(t("msg.username_required")))
        return

    try:
        con = __import__(
            "admin_panel.db.connection", fromlist=["panel_db"]
        ).panel_db()
        row = _user_row(con, username)
        con.close()
    except Exception:
        row = None

    if not row:
        handler.send_html(_users_page(t("msg.user_not_found")))
        return

    status = row["status"]
    user_id = row["id"]
    assigned_configs = configs_for_user_id(user_id)
    has_configs = bool(assigned_configs) or bool(row["client_name"])

    if action == "assign-config":
        if status != "approved":
            handler.send_html(_users_page(t("msg.only_approved_assign_config")))
            return
        if not client:
            handler.send_html(_users_page(t("msg.client_required_for_assign")))
            return
        other = user_configs.username_for_client(client)
        if other and other != username:
            handler.send_html(
                _users_page(
                    tf("msg.client_already_assigned", client=client, user=other)
                )
            )
            return
        ok, err = user_configs.assign_config(user_id, client)
        if not ok:
            handler.send_html(_users_page(t("msg.assign_config_failed")))
            return
        try:
            con = __import__(
                "admin_panel.db.connection", fromlist=["panel_db"]
            ).panel_db()
            con.execute(
                "UPDATE users SET client_name=? WHERE id=?",
                (user_configs.primary_client_name(user_id, client), user_id),
            )
            con.commit()
            con.close()
        except Exception:
            pass
        handler.send_html(
            _users_page(tf("msg.config_assigned", client=client, user=username))
        )
        return

    if action == "unassign-config":
        if not client:
            handler.send_html(_users_page(t("msg.client_name_required")))
            return
        user_configs.unassign_config(user_id, client)
        try:
            con = __import__(
                "admin_panel.db.connection", fromlist=["panel_db"]
            ).panel_db()
            primary = user_configs.primary_client_name(user_id, "")
            con.execute(
                "UPDATE users SET client_name=? WHERE id=?",
                (primary, user_id),
            )
            con.commit()
            con.close()
        except Exception:
            pass
        handler.send_html(
            _users_page(tf("msg.config_unassigned", client=client, user=username))
        )
        return

    if action == "approve":
        if status == "pending":
            if not client:
                client = row["client_name"]
            if not client:
                handler.send_html(_users_page(t("msg.client_required_for_approve")))
                return
            out = _approve_user(username, client)
        elif status == "disabled" and not has_configs:
            if not client:
                handler.send_html(_users_page(t("msg.client_required_for_assign")))
                return
            out = _approve_user(username, client, reassigned=True)
        elif status == "rejected":
            if not client:
                client = row["client_name"]
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
        if not has_configs:
            handler.send_html(_users_page(t("msg.assign_client_first")))
            return
        out = _enable_user(username)

    elif action == "change-password":
        out = _change_password(username, data.get("new_password", ""))

    else:
        out = t("msg.unknown_action")

    handler.send_html(_users_page(tail_message(out)))
