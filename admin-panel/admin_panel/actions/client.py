from admin_panel.config import DEFAULT_DAYS, DEFAULT_LIMIT, DEFAULT_SINGLE, WG_CLIENT, WG_CLIENT_SINGLE
from admin_panel.core.audit import log_admin_action
from admin_panel.core.client_ops import (
    client_was_removed,
    ensure_client,
    run_client_action,
    run_client_remove,
    run_client_renew,
)
from admin_panel.core.i18n import t, tf
from admin_panel.core.shell import run, safe_name, tail_message
from admin_panel.core.wireguard import all_client_meta, find_client_status
from admin_panel.db.panel_queries import detach_users_from_client


def handle(handler, data):
    action = data.get("action", "")
    client = safe_name(data.get("client", ""))

    if action == "add":
        if not client:
            _render(handler, t("msg.client_name_required"))
            return
        vpn_mode = (data.get("vpn_mode") or "twohop").strip().lower()
        if vpn_mode not in ("direct", "twohop"):
            vpn_mode = "twohop"
        ok, _, out = ensure_client(
            client,
            days=data.get("days", DEFAULT_DAYS),
            limit=data.get("limit", DEFAULT_LIMIT),
            single=data.get("single", DEFAULT_SINGLE),
            vpn_mode=vpn_mode,
        )
        if not ok:
            _render(handler, tail_message(out))
            return
        log_admin_action("add_client", client)
        _render(handler, tail_message(out or tf("msg.client_ready", name=client)))
        return

    if not client:
        _render(handler, t("msg.client_name_required"))
        return

    status = find_client_status(client)
    meta_exists = any(m.get("NAME") == client for m in all_client_meta())

    if action == "set-single":
        mode = data.get("single_mode", "ip")
        if mode not in ("off", "ip", "endpoint"):
            _render(handler, t("msg.invalid_single_mode"))
            return
        out = run([WG_CLIENT_SINGLE, client, mode])
        _render(handler, tail_message(out))
        return

    if action == "set-vpn-mode":
        mode = (data.get("vpn_mode") or "twohop").strip().lower()
        if mode not in ("direct", "twohop"):
            _render(handler, t("msg.invalid_vpn_mode"))
            return
        out = run([WG_CLIENT, "set-mode", client, mode])
        _render(handler, tail_message(out))
        return

    if not meta_exists or not status:
        _render(handler, t("msg.client_not_found"))
        return

    if action == "enable":
        if not status["disabled"]:
            _render(handler, t("msg.client_already_active"))
            return
        out = run_client_action("enable", client)

    elif action == "disable":
        if status["disabled"]:
            _render(handler, t("msg.client_already_disabled"))
            return
        out = run_client_action("disable", client, ["disabled from admin panel"])

    elif action == "renew":
        if not (status.get("expired") or status.get("over_limit")):
            _render(handler, t("msg.renew_only_expired"))
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
                names = t("fmt.list_sep").join(detached)
                out = (out or tf("msg.client_removed", name=client)).strip()
                out += tf("msg.users_deactivated", names=names)

    else:
        out = t("msg.unknown_action")
        _render(handler, tail_message(out))
        return

    log_admin_action(action, client)
    _render(handler, tail_message(out))


def _render(handler, msg):
    handler.flash("/clients", msg)
