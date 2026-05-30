from admin_panel.config import DEFAULT_DAYS, DEFAULT_LIMIT, DEFAULT_SINGLE, WG_CLIENT_SINGLE
from admin_panel.core.audit import log_admin_action
from admin_panel.core.client_ops import (
    client_was_removed,
    ensure_client,
    run_client_action,
    run_client_remove,
    run_client_renew,
)
from admin_panel.core.shell import run, safe_name, tail_message
from admin_panel.core.wireguard import all_client_meta, find_client_status
from admin_panel.db.panel_queries import detach_users_from_client


def handle(handler, data):
    action = data.get("action", "")
    client = safe_name(data.get("client", ""))

    if action == "add":
        if not client:
            _render(handler, "نام کلاینت الزامی است")
            return
        ok, _, out = ensure_client(
            client,
            days=data.get("days", DEFAULT_DAYS),
            limit=data.get("limit", DEFAULT_LIMIT),
            single=data.get("single", DEFAULT_SINGLE),
        )
        if not ok:
            _render(handler, tail_message(out))
            return
        log_admin_action("add_client", client)
        _render(handler, tail_message(out or f"کلاینت «{client}» آماده است"))
        return

    if not client:
        _render(handler, "نام کلاینت الزامی است")
        return

    status = find_client_status(client)
    meta_exists = any(m.get("NAME") == client for m in all_client_meta())

    if action == "set-single":
        mode = data.get("single_mode", "ip")
        if mode not in ("off", "ip", "endpoint"):
            _render(handler, "حالت محدودیت نامعتبر است")
            return
        out = run([WG_CLIENT_SINGLE, client, mode])
        _render(handler, tail_message(out))
        return

    if not meta_exists or not status:
        _render(handler, "کلاینت پیدا نشد")
        return

    if action == "enable":
        if not status["disabled"]:
            _render(handler, "این کلاینت از قبل فعال است")
            return
        out = run_client_action("enable", client)

    elif action == "disable":
        if status["disabled"]:
            _render(handler, "این کلاینت از قبل غیرفعال است")
            return
        out = run_client_action("disable", client, ["disabled from admin panel"])

    elif action == "renew":
        if not (status.get("expired") or status.get("over_limit")):
            _render(handler, "تمدید فقط برای منقضی یا اتمام حجم مجاز است")
            return
        out = run_client_renew(
            client,
            days=DEFAULT_DAYS,
            limit=DEFAULT_LIMIT,
            single=DEFAULT_SINGLE,
        )

    elif action == "remove":
        out = run_client_remove(client)
        if client_was_removed(client):
            detached = detach_users_from_client(client)
            if detached:
                names = "، ".join(detached)
                out = (out or f"کلاینت «{client}» حذف شد.").strip()
                out += f" کاربر(ان) {names} غیرفعال شدند؛ از صفحه کاربران کلاینت جدید اختصاص دهید."

    else:
        out = "عملیات ناشناخته"
        _render(handler, tail_message(out))
        return

    log_admin_action(action, client)
    log_admin_action(action, client)
    _render(handler, tail_message(out))


def _render(handler, msg):
    handler.flash("/clients", msg)
