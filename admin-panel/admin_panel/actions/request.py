from admin_panel.components.notice import notice
from admin_panel.config import DEFAULT_DAYS, DEFAULT_LIMIT, DEFAULT_SINGLE
from admin_panel.core.audit import log_admin_action
from admin_panel.core.client_ops import (
    _client_action_applied,
    run_client_action,
    run_client_renew,
)
from admin_panel.core.wireguard import find_client_status
from admin_panel.core.shell import tail_message
from admin_panel.db import panel_db


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
            WHERE requests.id=? AND requests.status='pending'
            """,
            (rid,),
        ).fetchone()
        con.close()
    except Exception as e:
        return f"خطا در خواندن درخواست: {e}"

    if not row:
        return "درخواست در انتظار پیدا نشد"

    username = row["username"]
    client = row["client_name"]
    req_action = row["action"]

    if not client:
        return "کاربر کلاینت اختصاص‌داده‌شده ندارد"

    if req_action == "enable":
        status = find_client_status(client)
        if status and (status.get("expired") or status.get("over_limit")):
            return (
                f"کلاینت «{client}» منقضی یا تمام‌شده است؛ "
                "ابتدا تمدید کنید یا از صفحه کلاینت‌ها تمدید را تایید کنید."
            )
        if status and not status.get("disabled"):
            return f"کلاینت «{client}» از قبل فعال است."
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
        return f"عملیات ناشناخته: {req_action}"

    if not ok:
        text = (out or "").strip()
        if text.startswith("ERROR") or text:
            return tail_message(text)
        return f"خطا در پردازش درخواست برای کلاینت «{client}»"

    try:
        if not _mark_request(rid, "approved"):
            return "درخواست پیدا نشد"
    except Exception as e:
        return f"خطا در به‌روزرسانی درخواست: {e}"

    action_label = "فعال‌سازی" if req_action == "enable" else "تمدید"
    log_admin_action(f"approve_request_{req_action}", f"#{rid} {username} ({client})")
    return f"درخواست #{rid} ({action_label}) برای «{username}» تایید شد."


def handle(handler, data):
    action = data.get("action", "")
    rid = data.get("id", "")

    if not rid.isdigit():
        handler.flash("/requests", "شناسه درخواست نامعتبر")
        return

    try:
        con = panel_db()
        row = con.execute("SELECT status FROM requests WHERE id=?", (rid,)).fetchone()
        con.close()
    except Exception:
        row = None

    if not row:
        handler.flash("/requests", "درخواست پیدا نشد")
        return

    if row["status"] != "pending":
        handler.flash("/requests", "این درخواست قبلاً پردازش شده")
        return

    if action == "approve":
        out = _approve_request(rid)
    elif action == "reject":
        try:
            if not _mark_request(rid, "rejected"):
                out = "درخواست پیدا نشد"
            else:
                log_admin_action("reject_request", f"#{rid}")
                out = f"درخواست #{rid} رد شد."
        except Exception as e:
            out = f"خطا در رد درخواست: {e}"
    else:
        out = "عملیات ناشناخته"

    handler.flash("/requests", tail_message(out))
