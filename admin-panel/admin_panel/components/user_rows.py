import html
import time

from admin_panel.components.action_menu import action_menu
from admin_panel.config import admin_url
from admin_panel.core.i18n import t, tf
from admin_panel.core.labels import badge_user_status, label_user_status
from admin_panel.core.statuses import UserStatus


def _format_registered(created_at):
    try:
        ts = int(created_at or 0)
    except (TypeError, ValueError):
        return "—"
    if ts <= 0:
        return "—"
    return time.strftime("%Y-%m-%d", time.localtime(ts))


def _config_chips(username, configs):
    if not configs:
        return f'<span class="user-chip user-chip--empty">{html.escape(t("user.no_configs"))}</span>'
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


def _user_action_menu(u, *, can_reject, can_disable, can_enable, show_enable_in_menu):
    prefix = {"username": u["username"]}
    return action_menu(
        admin_url("/user-action"),
        prefix,
        [
            ({}, "reject", t("user.reject"), can_reject, True),
            ({}, "disable", t("user.disable"), can_disable),
            ({}, "enable", t("user.enable"), can_enable and show_enable_in_menu),
        ],
        aria_label=t("user.more_actions"),
    )


def _user_toolbar(u, *, can_approve, can_enable, needs_client, approve_attr, approve_client_field, form_id):
    username_esc = html.escape(u["username"])
    primary = ""

    if can_approve and not needs_client:
        primary = f"""
<form class="inline-form user-quick-form" method="post" action="{admin_url("/user-action")}">
  <input type="hidden" name="action" value="approve">
  <input type="hidden" name="username" value="{username_esc}">
  {approve_client_field}
  <button type="submit" class="btn btn-sm user-primary-action" {approve_attr}>{html.escape(t("user.approve"))}</button>
</form>
"""
    elif can_enable:
        primary = f"""
<form class="inline-form user-quick-form" method="post" action="{admin_url("/user-action")}">
  <input type="hidden" name="username" value="{username_esc}">
  <input type="hidden" name="action" value="enable">
  <button type="submit" class="btn btn-sm user-primary-action">{html.escape(t("user.enable"))}</button>
</form>
"""
    elif can_approve and needs_client:
        primary = (
            f'<button type="button" class="btn btn-sm user-primary-action user-open-manage" '
            f'data-manage-for="{form_id}">{html.escape(t("user.approve_with_config"))}</button>'
        )

    show_enable_in_menu = can_enable and can_approve and not needs_client
    menu = _user_action_menu(
        u,
        can_reject=u["status"] == UserStatus.PENDING,
        can_disable=u["status"] == UserStatus.APPROVED,
        can_enable=can_enable,
        show_enable_in_menu=show_enable_in_menu,
    )
    solo = " user-toolbar--solo" if not menu else ""

    return f'<div class="user-toolbar{solo}">{primary}{menu}</div>'


def _user_manage_panel(
    u,
    *,
    form_id,
    can_approve,
    can_assign_more,
    needs_client,
    approve_attr,
    approve_input,
    approve_client_field,
    approve_client_input,
    approve_label,
    configs,
):
    username_esc = html.escape(u["username"])

    approve_section = ""
    if can_approve or needs_client or u["status"] in (UserStatus.PENDING, UserStatus.REJECTED, UserStatus.DISABLED):
        approve_section = f"""
<div class="user-manage-section">
  <span class="user-manage-label">{html.escape(t("user.approve"))}</span>
  <form id="{form_id}" class="inline-form user-approve-form" method="post" action="{admin_url("/user-action")}">
    <input type="hidden" name="action" value="approve">
    <input type="hidden" name="username" value="{username_esc}">
    {approve_client_field}
    <div class="user-manage-row">
      {approve_client_input}
      <button type="submit" class="btn btn-sm" {approve_attr}>{html.escape(approve_label)}</button>
    </div>
  </form>
</div>
"""

    assign_section = ""
    if can_assign_more:
        assign_section = f"""
<div class="user-manage-section">
  <span class="user-manage-label">{html.escape(t("user.add_config"))}</span>
  <form class="inline-form user-assign-config-form" method="post" action="{admin_url("/user-action")}">
    <input type="hidden" name="username" value="{username_esc}">
    <input type="hidden" name="action" value="assign-config">
    <div class="user-manage-row">
      <input name="client" class="field-input user-client-input" placeholder="{html.escape(t("user.client_name_placeholder"))}" required autocomplete="off">
      <button type="submit" class="btn btn-sm">{html.escape(t("user.add_config"))}</button>
    </div>
  </form>
</div>
"""

    password_section = f"""
<div class="user-manage-section">
  <span class="user-manage-label">{html.escape(t("user.change_password"))}</span>
  <form class="user-password-form inline-form" method="post" action="{admin_url("/user-action")}">
    <input type="hidden" name="username" value="{username_esc}">
    <input type="hidden" name="action" value="change-password">
    <div class="user-manage-row">
      <input type="password" name="new_password" placeholder="{html.escape(t("user.new_password"))}" class="field-input user-password-input" minlength="6" required autocomplete="new-password">
      <button type="submit" class="btn btn-sm dark">{html.escape(t("user.change_password"))}</button>
    </div>
  </form>
</div>
"""

    config_hint = ""
    if configs:
        config_hint = f'<p class="user-manage-hint muted">{html.escape(t("col.config"))}: {len(configs)}</p>'

    return f"""
<details class="user-manage panel-expand" id="{form_id}">
  <summary>{html.escape(t("user.manage"))}</summary>
  <div class="panel-expand-body user-manage-body">
    {config_hint}
    {approve_section}
    {assign_section}
    {password_section}
  </div>
</details>
"""


def _user_item(u):
    status = u["status"]
    username = u["username"]
    username_esc = html.escape(username)
    configs = u.get("configs") or []

    needs_client = not configs and not u.get("client_name")
    can_approve = status in (UserStatus.PENDING, UserStatus.REJECTED) or (
        status == UserStatus.DISABLED and needs_client
    )
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

    badge = badge_user_status(status)
    form_id = f"user-manage-{u['id']}"
    chips_html = _config_chips(username, configs)

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
            f'<input name="client" placeholder="{html.escape(t("user.client_name_hint"))}" '
            f'class="field-input user-client-input" {approve_input} {req} autocomplete="off">'
        )

    toolbar = _user_toolbar(
        u,
        can_approve=can_approve,
        can_enable=can_enable,
        needs_client=needs_client,
        approve_attr=approve_attr,
        approve_client_field=approve_client_field,
        form_id=form_id,
    )
    manage_panel = _user_manage_panel(
        u,
        form_id=form_id,
        can_approve=can_approve,
        can_assign_more=can_assign_more,
        needs_client=needs_client,
        approve_attr=approve_attr,
        approve_input=approve_input,
        approve_client_field=approve_client_field,
        approve_client_input=approve_client_input,
        approve_label=approve_label,
        configs=configs,
    )

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

    return f"""
<div class="user-item" data-list-item data-list-primary data-status="{sort_status}" data-sort-id="{u['id']}" data-sort-name="{sort_name}" data-sort-client="{sort_client}" data-sort-created="{created_at}" data-search="{search_text}">
  <div class="user-field user-field-name" data-label="{html.escape(t("col.user"))}">
    <span class="user-item-name">{username_esc}</span>
    <span class="user-item-meta">#{u['id']} · {html.escape(registered)}</span>
  </div>
  <div class="user-field user-field-status" data-label="{html.escape(t("col.status"))}">
    <span class="badge {badge}">{html.escape(status_label)}</span>
  </div>
  <div class="user-field user-field-configs" data-label="{html.escape(t("col.config"))}">
    {chips_html}
  </div>
  <div class="user-field user-field-actions" data-label="{html.escape(t("col.actions"))}">
    {toolbar}
  </div>
  {manage_panel}
</div>
"""


def user_list(users):
    if not users:
        return f"""
<div class="user-list" data-list-items data-list-kind="users">
  <div class="user-list-empty" data-list-static-empty>{html.escape(t("empty.no_users"))}</div>
</div>
"""

    items = "".join(_user_item(u) for u in users)
    return f"""
<div class="user-list-wrap">
<div class="user-list" data-list-items data-list-kind="users">
  <div class="user-list-head">
    <div>{html.escape(t("col.user"))}</div>
    <div>{html.escape(t("col.status"))}</div>
    <div>{html.escape(t("col.config"))}</div>
    <div>{html.escape(t("col.actions"))}</div>
  </div>
  <div class="user-list-body" data-list-body>
    {items}
  </div>
</div>
</div>
"""


def user_rows(users):
    return user_list(users)
