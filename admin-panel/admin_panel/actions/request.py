from admin_panel.core.audit import log_admin_action
from admin_panel.core.client_ops import (
    _client_action_applied,
    run_client_action,
    run_client_renew,
)
from admin_panel.core.i18n import t, tf
from admin_panel.core.labels import label_action
from admin_panel.core.shell import tail_message
from admin_panel.core.statuses import RequestStatus
from admin_panel.core.wireguard import find_client_status
from admin_panel.db import panel_db
from admin_panel.config import DEFAULT_DAYS, DEFAULT_LIMIT, DEFAULT_SINGLE


def _mark_request(rid, status):
    con = panel_db()
    cur = con.execute(
        "UPDATE requests SET status=?, processed_at=strftime('%s','now') WHERE id=?",
        (status, rid),
    )
    con.commit()
    con.close()
    return cur.rowcount > 0


def _approve_request(rid):
    try:
        con = panel_db()
        row = con.execute(
            """
            SELECT users.username, COALESCE(users.client_name, '') AS client_name, requests.action
            FROM requests JOIN users ON users.id = requests.user_id
            WHERE requests.id=? AND requests.status=?
            """,
            (rid, RequestStatus.PENDING),
        ).fetchone()
        con.close()
    except Exception as e:
        return tf("msg.read_request_error", err=e)

    if not row:
        return t("msg.pending_request_not_found")

    username = row["username"]
    client = row["client_name"]
    req_action = row["action"]

    if not client:
        return t("msg.user_no_client")

    if req_action == "enable":
        status = find_client_status(client)
        if status and (status.get("expired") or status.get("over_limit")):
            return tf("msg.client_expired_renew_first", client=client)
        if status and not status.get("disabled"):
            return tf("msg.client_already_active_short", client=client)
        out = run_client_action("enable", client)
        ok = _client_action_applied("enable", client) or "Enabled client" in (out or "")
    elif req_action == "renew":
        out = run_client_renew(
            client,
            days=DEFAULT_DAYS,
            limit=DEFAULT_LIMIT,
            single=DEFAULT_SINGLE,
        )
        ok = "Renewed client" in (out or "") or "تمدید شد" in (out or "")
    else:
        return tf("msg.unknown_action_detail", action=req_action)

    if not ok:
        text = (out or "").strip()
        if text.startswith("ERROR") or text:
            return tail_message(text)
        return tf("msg.process_request_error", client=client)

    try:
        if not _mark_request(rid, RequestStatus.APPROVED):
            return t("msg.request_not_found")
    except Exception as e:
        return tf("msg.update_request_error", err=e)

    action_label = label_action(req_action)
    log_admin_action(f"approve_request_{req_action}", f"#{rid} {username} ({client})")
    return tf(
        "msg.request_approved",
        id=rid,
        action=action_label,
        user=username,
    )


def handle(handler, data):
    action = data.get("action", "")
    rid = data.get("id", "")

    if not rid.isdigit():
        handler.flash("/requests", t("msg.invalid_request_id"))
        return

    try:
        con = panel_db()
        row = con.execute("SELECT status FROM requests WHERE id=?", (rid,)).fetchone()
        con.close()
    except Exception:
        row = None

    if not row:
        handler.flash("/requests", t("msg.request_not_found"))
        return

    if row["status"] != RequestStatus.PENDING:
        handler.flash("/requests", t("msg.request_already_processed"))
        return

    if action == "approve":
        out = _approve_request(rid)
    elif action == "reject":
        try:
            if not _mark_request(rid, RequestStatus.REJECTED):
                out = t("msg.request_not_found")
            else:
                log_admin_action("reject_request", f"#{rid}")
                out = tf("msg.request_rejected", id=rid)
        except Exception as e:
            out = tf("msg.reject_request_error", err=e)
    else:
        out = t("msg.unknown_action")

    handler.flash("/requests", tail_message(out))
