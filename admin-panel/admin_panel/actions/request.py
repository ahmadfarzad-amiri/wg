from admin_panel.components.layout import page
from admin_panel.config import DEFAULT_DAYS, DEFAULT_LIMIT, DEFAULT_SINGLE
from admin_panel.core.client_ops import run_client_action, run_client_renew
from admin_panel.core.shell import tail_message
from admin_panel.db import panel_db
from admin_panel.views import requests


def _fetch_requests():
    try:
        con = panel_db()
        rows = con.execute(
            """
            SELECT requests.id, users.username, users.client_name,
                   requests.action, requests.status, requests.created_at
            FROM requests JOIN users ON users.id = requests.user_id
            ORDER BY requests.id DESC
            """
        ).fetchall()
        con.close()
        return rows
    except Exception:
        return []


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
        out = run_client_action("enable", client)
        from admin_panel.core.client_ops import _client_action_applied

        ok = _client_action_applied("enable", client)
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
    return f"درخواست #{rid} ({action_label}) برای «{username}» تایید شد."


def handle(handler, data):
    action = data.get("action", "")
    rid = data.get("id", "")

    if not rid.isdigit():
        handler.send_html(
            page("درخواست‌ها", requests.body(_fetch_requests(), "شناسه درخواست نامعتبر"), "requests")
        )
        return

    try:
        con = panel_db()
        row = con.execute("SELECT status FROM requests WHERE id=?", (rid,)).fetchone()
        con.close()
    except Exception:
        row = None

    if not row:
        handler.send_html(
            page("درخواست‌ها", requests.body(_fetch_requests(), "درخواست پیدا نشد"), "requests")
        )
        return

    if row["status"] != "pending":
        handler.send_html(
            page("درخواست‌ها", requests.body(_fetch_requests(), "این درخواست قبلاً پردازش شده"), "requests")
        )
        return

    if action == "approve":
        out = _approve_request(rid)
    elif action == "reject":
        try:
            if not _mark_request(rid, "rejected"):
                out = "درخواست پیدا نشد"
            else:
                out = f"درخواست #{rid} رد شد."
        except Exception as e:
            out = f"خطا در رد درخواست: {e}"
    else:
        out = "عملیات ناشناخته"

    handler.send_html(
        page("درخواست‌ها", requests.body(_fetch_requests(), tail_message(out)), "requests")
    )
