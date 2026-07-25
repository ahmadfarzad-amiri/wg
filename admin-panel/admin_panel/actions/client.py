from admin_panel.config import DEFAULT_DAYS, DEFAULT_LIMIT, DEFAULT_SINGLE, WG_CLIENT, WG_CLIENT_SINGLE
from admin_panel.core.audit import log_admin_action
from admin_panel.core.client_ops import (
    client_action_applied,
    client_was_removed,
    ensure_client,
    run_client_action,
    run_client_remove,
    run_client_renew,
)
from admin_panel.core.i18n import t, tf
from admin_panel.core.shell import CLIENT_CMD_TIMEOUT, run, safe_name, tail_message
from admin_panel.core.wireguard import all_client_meta, find_client_status
from admin_panel.db.panel_queries import detach_users_from_client
from wg_common.entry_mode import default_vpn_mode, is_standalone_entry


def _audit(handler, action, detail=""):
    from admin_panel.server import security, session
    log_admin_action(action, detail, actor=session.admin_actor(), ip=security.client_ip(handler))


def _try_add_xray_client(name):
    """Silently attempt to create an Xray client. No-op if Xray is not installed."""
    try:
        from admin_panel.core import xray as xcore
        if not xcore.is_installed():
            return
        xcore.add_client(name)
    except Exception:
        import logging
        logging.getLogger(__name__).warning(
            "xray auto-create failed for %s", name, exc_info=True
        )


def _resolve_vpn_mode(raw):
    mode = (raw or default_vpn_mode()).strip().lower()
    if mode not in ("direct", "twohop"):
        mode = default_vpn_mode()
    if mode == "twohop" and is_standalone_entry():
        mode = "direct"
    return mode


def handle_bulk(handler, data):
    """Create multiple clients from a newline-separated name list."""
    raw = data.get("names", "")
    names = [safe_name(n.strip()) for n in raw.replace(",", "\n").splitlines()]
    names = [n for n in names if n]

    if not names:
        _render(handler, t("msg.bulk_names_required"), variant="error")
        return
    if len(names) > 50:
        _render(handler, t("msg.bulk_too_many"), variant="error")
        return

    vpn_mode = _resolve_vpn_mode(data.get("vpn_mode"))

    days = data.get("days") or DEFAULT_DAYS
    limit = data.get("limit") or DEFAULT_LIMIT
    single = data.get("single") or DEFAULT_SINGLE

    created = []
    skipped = []
    failed = []

    for name in names:
        ok, was_new, out = ensure_client(
            name, days=days, limit=limit, single=single, vpn_mode=vpn_mode
        )
        if ok and was_new:
            created.append(name)
            _audit(handler, "bulk_add_client", name)
            _try_add_xray_client(name)
        elif ok and not was_new:
            skipped.append(name)
        else:
            failed.append(name)

    parts = []
    if created:
        parts.append(tf("msg.bulk_created", n=len(created), names=", ".join(created)))
    if skipped:
        parts.append(tf("msg.bulk_skipped", n=len(skipped), names=", ".join(skipped)))
    if failed:
        parts.append(tf("msg.bulk_failed", n=len(failed), names=", ".join(failed)))

    _render(
        handler,
        " ".join(parts) or t("msg.bulk_nothing"),
        variant="error" if failed and not created else ("warn" if failed or skipped else "success"),
    )


def handle(handler, data):
    action = data.get("action", "")
    client = safe_name(data.get("client", ""))

    if action == "add":
        if not client:
            _render(handler, t("msg.client_name_required"), variant="error")
            return
        vpn_mode = _resolve_vpn_mode(data.get("vpn_mode"))
        ok, _, out = ensure_client(
            client,
            days=data.get("days", DEFAULT_DAYS),
            limit=data.get("limit", DEFAULT_LIMIT),
            single=data.get("single", DEFAULT_SINGLE),
            vpn_mode=vpn_mode,
        )
        if not ok:
            _render(handler, tail_message(out) or t("msg.unknown_action"), variant="error")
            return
        _audit(handler, "add_client", client)
        _try_add_xray_client(client)
        # Stay on the clients list with an explicit success toast.
        _render(
            handler,
            tf("msg.client_ready", name=client),
            variant="success",
        )
        return

    if not client:
        _render(handler, t("msg.client_name_required"), variant="error")
        return

    status = find_client_status(client)
    meta_exists = any(m.get("NAME") == client for m in all_client_meta())

    if action == "update":
        if not meta_exists:
            _render(handler, t("msg.client_not_found"), variant="error")
            return
        cmd = [WG_CLIENT, "update", client]
        days = (data.get("days") or "").strip()
        limit = (data.get("limit") or "").strip()
        vpn_mode = (data.get("vpn_mode") or "").strip().lower()
        single_mode = (data.get("single_mode") or "").strip()
        if days:
            if not days.isdigit():
                _render(handler, t("msg.invalid_days"), variant="error", client=client)
                return
            cmd.extend(["--days", days])
        if limit:
            cmd.extend(["--limit", limit])
        if vpn_mode:
            if vpn_mode not in ("direct", "twohop"):
                _render(handler, t("msg.invalid_vpn_mode"), variant="error", client=client)
                return
            if vpn_mode == "twohop" and is_standalone_entry():
                _render(handler, t("msg.twohop_needs_exit"), variant="error", client=client)
                return
            cmd.extend(["--vpn-mode", vpn_mode])
        if data.get("reset_usage"):
            cmd.append("--reset-usage")
        messages = []
        if len(cmd) > 3:
            messages.append(run(cmd, timeout=CLIENT_CMD_TIMEOUT))
        if single_mode:
            if single_mode not in ("off", "ip", "endpoint"):
                _render(handler, t("msg.invalid_single_mode"), variant="error", client=client)
                return
            current_single = (status.get("single") or "off") if status else None
            if single_mode != current_single:
                messages.append(run([WG_CLIENT_SINGLE, client, single_mode]))
        if not messages:
            _render(handler, t("msg.update_nothing"), variant="info", client=client)
            return
        _audit(handler, "update", client)
        combined = "\n".join(m for m in messages if m)
        _render(
            handler,
            tail_message(combined) or tf("msg.client_ready", name=client),
            variant="success",
            client=client,
        )
        return

    if not meta_exists or not status:
        _render(handler, t("msg.client_not_found"), variant="error")
        return

    if action == "enable":
        if not status["disabled"]:
            _render(handler, t("msg.client_already_active"), variant="info", client=client)
            return
        out = run_client_action("enable", client)

    elif action == "disable":
        if status["disabled"]:
            _render(handler, t("msg.client_already_disabled"), variant="info", client=client)
            return
        out = run_client_action("disable", client, ["disabled from admin panel"])

    elif action == "renew":
        if not (status.get("expired") or status.get("over_limit")):
            _render(handler, t("msg.renew_only_expired"), variant="error", client=client)
            return
        out = run_client_renew(
            client,
            days=DEFAULT_DAYS,
            limit=DEFAULT_LIMIT,
            single=DEFAULT_SINGLE,
        )

    elif action == "remove":
        out = run_client_remove(client)
        removed = client_was_removed(client) or "Removed client:" in (out or "")
        if removed:
            detached = detach_users_from_client(client)
            msg = tail_message(out) or tf("msg.client_removed", name=client)
            if detached:
                names = t("fmt.list_sep").join(detached)
                msg = f"{msg}{tf('msg.users_deactivated', names=names)}"
            _audit(handler, action, client)
            _render(handler, msg, variant="success")
        else:
            _audit(handler, action, client)
            _render(
                handler,
                tail_message(out) or t("msg.client_not_found"),
                variant="error",
            )
        return

    else:
        out = t("msg.unknown_action")
        _render(handler, tail_message(out), variant="error")
        return

    _audit(handler, action, client)
    applied = True
    lower = (out or "").lower()
    if action in ("enable", "disable"):
        applied = client_action_applied(action, client)
    elif action == "renew":
        applied = "renewed client:" in lower and not any(
            x in lower for x in ("error:", "failed", "not found", "die")
        )
        if not applied and client_action_applied("enable", client):
            # Renew may have succeeded even if banner text was truncated.
            applied = "error:" not in lower and "not found" not in lower
    _render(
        handler,
        tail_message(out) or tf("msg.client_ready", name=client),
        variant="success" if applied else "error",
        client=client,
    )


def _render(handler, msg, *, path="/clients", variant="info", client=""):
    if client and path == "/clients":
        path = f"/clients/{client}"
    handler.flash(path, msg, variant=variant)
