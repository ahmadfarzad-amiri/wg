import html
import time

from admin_panel.config import admin_url
from admin_panel.core.i18n import t, tf
from admin_panel.core.labels import badge_user_status, label_user_status
from admin_panel.core.statuses import UserStatus


def _config_chips(username, configs):
    if not configs:
        return f'<span class="muted">{html.escape(t("user.no_configs"))}</span>'
    chips = []
    for cfg in configs:
        name = html.escape(cfg["client_name"])
        chips.append(
            f'<span class="user-config-chip">'
            f'<span class="user-config-chip__name">{name}</span>'
            f'<form class="inline-form user-config-chip__remove" method="post" action="{admin_url("/user-action")}">'
            f'<input type="hidden" name="username" value="{html.escape(username)}">'
            f'<input type="hidden" name="action" value="unassign-config">'
            f'<input type="hidden" name="client" value="{name}">'
            f'<button type="submit" class="chip-remove" aria-label="{html.escape(t("user.unassign_config"))}" '
            f'data-confirm="{html.escape(t("user.unassign_confirm"), quote=True)}">×</button>'
            f"</form></span>"
        )
    return f'<div class="user-config-chips">{"".join(chips)}</div>'


def _format_registered(created_at):
    try:
        ts = int(created_at or 0)
    except (TypeError, ValueError):
        return "—"
    if ts <= 0:
        return "—"
    return time.strftime("%Y-%m-%d", time.localtime(ts))


def user_rows(users):
    items = ""
    for u in users:
        status = u["status"]
        username = u["username"]
        username_esc = html.escape(username)
        configs = u.get("configs") or []

        needs_client = not configs and not u.get("client_name")
        can_approve = status in (UserStatus.PENDING, UserStatus.REJECTED) or (
            status == UserStatus.DISABLED and needs_client
        )
        can_reject = status == UserStatus.PENDING
        can_disable = status == UserStatus.APPROVED
        can_enable = status == UserStatus.DISABLED and not needs_client
        can_assign_more = status == UserStatus.APPROVED
        approve_label = (
            t("user.approve_with_config")
            if needs_client
            and status in (UserStatus.PENDING, UserStatus.REJECTED, UserStatus.DISABLED)
            else t("user.approve")
        )

        if can_approve:
            approve_attr = ""
            approve_input = ""
        elif status == UserStatus.DISABLED:
            approve_attr = f'disabled title="{html.escape(t("user.title_client_assigned"), quote=True)}"'
            approve_input = "disabled"
        else:
            approve_attr = f'disabled title="{html.escape(t("user.title_already_approved"), quote=True)}"'
            approve_input = "disabled"
        reject_attr = "" if can_reject else f'disabled title="{html.escape(t("user.title_pending_only"), quote=True)}"'
        disable_attr = "" if can_disable else f'disabled title="{html.escape(t("user.title_approved_only"), quote=True)}"'
        enable_attr = (
            ""
            if can_enable
            else (
                f'disabled title="{html.escape(t("user.title_assign_client_first"), quote=True)}"'
                if status == UserStatus.DISABLED
                else f'disabled title="{html.escape(t("user.title_disabled_only"), quote=True)}"'
            )
        )

        badge = badge_user_status(status)
        form_id = f"user-approve-{u['id']}"

        chips_html = _config_chips(username, configs)

        assign_form = ""
        if can_assign_more:
            assign_form = f"""
<form class="inline-form user-assign-config-form" method="post" action="{admin_url("/user-action")}">
  <input type="hidden" name="username" value="{username_esc}">
  <input type="hidden" name="action" value="assign-config">
  <input name="client" class="input-inline user-client-input" placeholder="{html.escape(t("user.client_name_placeholder"))}" required autocomplete="off">
  <button type="submit" class="btn-sm">{html.escape(t("user.add_config"))}</button>
</form>
"""

        client_cell = f"""
<div class="user-configs-cell">
  {chips_html}
  {assign_form}
</div>
"""

        if u.get("client_name") and not configs:
            approve_client_field = (
                f'<input type="hidden" name="client" value="{html.escape(u["client_name"])}">'
            )
        elif needs_client:
            approve_client_field = ""
        else:
            approve_client_field = (
                f'<input type="hidden" name="client" value="{html.escape(configs[0]["client_name"])}">'
                if configs
                else ""
            )

        approve_client_input = ""
        if needs_client:
            req = "required" if can_approve else ""
            approve_client_input = (
                f'<input name="client" form="{form_id}" placeholder="{html.escape(t("user.client_name_hint"))}" '
                f'class="input-inline user-client-input" {approve_input} {req}>'
            )

        primary_actions = f"""
<div class="user-action-buttons user-action-primary">
  <form id="{form_id}" class="inline-form user-approve-form" method="post" action="{admin_url("/user-action")}">
    <input type="hidden" name="action" value="approve">
    <input type="hidden" name="username" value="{username_esc}">
    {approve_client_field}
    {approve_client_input}
    <button type="submit" class="btn-sm" {approve_attr}>{html.escape(approve_label)}</button>
  </form>
  <form class="inline-form" method="post" action="{admin_url("/user-action")}">
    <input type="hidden" name="username" value="{username_esc}">
    <input type="hidden" name="action" value="reject">
    <button type="submit" class="bad btn-sm" {reject_attr}>{html.escape(t("user.reject"))}</button>
  </form>
  <form class="inline-form" method="post" action="{admin_url("/user-action")}">
    <input type="hidden" name="username" value="{username_esc}">
    <input type="hidden" name="action" value="disable">
    <button type="submit" class="dark btn-sm" {disable_attr}>{html.escape(t("user.disable"))}</button>
  </form>
  <form class="inline-form" method="post" action="{admin_url("/user-action")}">
    <input type="hidden" name="username" value="{username_esc}">
    <input type="hidden" name="action" value="enable">
    <button type="submit" class="btn-sm" {enable_attr}>{html.escape(t("user.enable"))}</button>
  </form>
</div>
"""

        more_actions = f"""
<details class="user-more-actions">
  <summary>{html.escape(t("user.more_actions"))}</summary>
  <form class="user-password-form inline-form" method="post" action="{admin_url("/user-action")}">
    <input type="hidden" name="username" value="{username_esc}">
    <input type="hidden" name="action" value="change-password">
    <input type="password" name="new_password" placeholder="{html.escape(t("user.new_password"))}" class="input-inline user-password-input" minlength="6" required autocomplete="new-password">
    <button type="submit" class="dark btn-sm">{html.escape(t("user.change_password"))}</button>
  </form>
</details>
"""

        actions = primary_actions + more_actions

        status_label = label_user_status(status)
        config_names = [c["client_name"] for c in configs] or ([u["client_name"]] if u.get("client_name") else [])
        client_name_raw = " ".join(config_names)
        created_at = int(u["created_at"] or 0)
        registered = _format_registered(created_at)
        sort_name = html.escape(username.lower())
        sort_client = html.escape(client_name_raw.lower())
        sort_status = html.escape(status)
        search_text = html.escape(
            " ".join([str(u["id"]), username, client_name_raw, status, status_label, registered]).lower()
        )

        items += f"""
<div class="user-item" data-list-item data-list-primary data-status="{sort_status}" data-sort-id="{u['id']}" data-sort-name="{sort_name}" data-sort-client="{sort_client}" data-sort-created="{created_at}" data-search="{search_text}">
  <div class="user-field user-field-id" data-label="{html.escape(t("col.id"))}">{u['id']}</div>
  <div class="user-field user-field-name" data-label="{html.escape(t("col.user"))}">{username_esc}</div>
  <div class="user-field user-field-status" data-label="{html.escape(t("col.status"))}"><span class="badge {badge}">{html.escape(status_label)}</span></div>
  <div class="user-field user-field-registered" data-label="{html.escape(t("col.registered"))}">{html.escape(registered)}</div>
  <div class="user-field user-field-client user-field-configs" data-label="{html.escape(t("col.config"))}">{client_cell}</div>
  <div class="user-field user-field-actions" data-label="{html.escape(t("col.actions"))}">{actions}</div>
</div>
"""

    if not items:
        items = f'<div class="user-list-empty" data-list-static-empty>{html.escape(t("empty.no_users"))}</div>'

    return f"""
<div class="user-list" data-list-items data-list-kind="users">
  <div class="user-list-head">
    <div>{html.escape(t("col.id"))}</div>
    <div>{html.escape(t("col.user"))}</div>
    <div>{html.escape(t("col.status"))}</div>
    <div>{html.escape(t("col.registered"))}</div>
    <div>{html.escape(t("col.config"))}</div>
    <div>{html.escape(t("col.actions"))}</div>
  </div>
  <div class="user-list-body" data-list-body>
    {items}
  </div>
</div>
"""
