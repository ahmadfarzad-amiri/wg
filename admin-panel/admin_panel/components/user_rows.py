import html

from admin_panel.config import admin_url
from admin_panel.core.i18n import t
from admin_panel.core.labels import badge_user_status, label_user_status


def user_rows(users):
    items = ""
    for u in users:
        status = u["status"]
        username = html.escape(u["username"])

        needs_client = not u["client_name"]
        can_approve = status in ("pending", "rejected") or (status == "disabled" and needs_client)
        can_reject = status == "pending"
        can_disable = status == "approved"
        can_enable = status == "disabled" and not needs_client
        approve_label = t("user.assign") if status == "disabled" and needs_client else t("user.approve")

        if can_approve:
            approve_attr = ""
            approve_input = ""
        elif status == "disabled":
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
                if status == "disabled"
                else f'disabled title="{html.escape(t("user.title_disabled_only"), quote=True)}"'
            )
        )

        badge = badge_user_status(status)
        form_id = f"user-approve-{u['id']}"

        client_name_esc = html.escape(u["client_name"]) if u["client_name"] else ""
        if u["client_name"]:
            client_cell = client_name_esc
            approve_client_field = f'<input type="hidden" name="client" value="{client_name_esc}">'
        else:
            client_cell = (
                f'<input name="client" form="{form_id}" placeholder="{html.escape(t("user.client_name_placeholder"))}" '
                f'class="input-inline user-client-input" {approve_input}>'
            )
            approve_client_field = ""

        actions = f"""
<div class="user-action-buttons">
  <form id="{form_id}" class="inline-form user-approve-form" method="post" action="{admin_url("/user-action")}">
    <input type="hidden" name="action" value="approve">
    <input type="hidden" name="username" value="{username}">
    {approve_client_field}
    <button type="submit" class="btn-sm" {approve_attr}>{html.escape(approve_label)}</button>
  </form>
  <form class="inline-form" method="post" action="{admin_url("/user-action")}">
    <input type="hidden" name="username" value="{username}">
    <input type="hidden" name="action" value="reject">
    <button type="submit" class="bad btn-sm" {reject_attr}>{html.escape(t("user.reject"))}</button>
  </form>
  <form class="inline-form" method="post" action="{admin_url("/user-action")}">
    <input type="hidden" name="username" value="{username}">
    <input type="hidden" name="action" value="disable">
    <button type="submit" class="dark btn-sm" {disable_attr}>{html.escape(t("user.disable"))}</button>
  </form>
  <form class="inline-form" method="post" action="{admin_url("/user-action")}">
    <input type="hidden" name="username" value="{username}">
    <input type="hidden" name="action" value="enable">
    <button type="submit" class="btn-sm" {enable_attr}>{html.escape(t("user.enable"))}</button>
  </form>
  <form class="user-password-form inline-form" method="post" action="{admin_url("/user-action")}">
    <input type="hidden" name="username" value="{username}">
    <input type="hidden" name="action" value="change-password">
    <input type="password" name="new_password" placeholder="{html.escape(t("user.new_password"))}" class="input-inline user-password-input" minlength="6" required autocomplete="new-password">
    <button type="submit" class="dark btn-sm">{html.escape(t("user.change_password"))}</button>
  </form>
</div>
"""

        status_label = label_user_status(status)
        client_name_raw = u["client_name"] or ""
        created_at = int(u["created_at"] or 0)
        sort_name = html.escape(u["username"].lower())
        sort_client = html.escape(client_name_raw.lower())
        sort_status = html.escape(status)
        search_text = html.escape(
            " ".join(
                [
                    str(u["id"]),
                    u["username"],
                    client_name_raw,
                    status,
                    status_label,
                ]
            ).lower()
        )

        items += f"""
<div class="user-item" data-list-item data-list-primary data-status="{sort_status}" data-sort-id="{u['id']}" data-sort-name="{sort_name}" data-sort-client="{sort_client}" data-sort-created="{created_at}" data-search="{search_text}">
  <div class="user-field user-field-id" data-label="{html.escape(t("col.id"))}">{u['id']}</div>
  <div class="user-field user-field-name" data-label="{html.escape(t("col.user"))}">{username}</div>
  <div class="user-field user-field-status" data-label="{html.escape(t("col.status"))}"><span class="badge {badge}">{html.escape(status_label)}</span></div>
  <div class="user-field user-field-client" data-label="{html.escape(t("col.client"))}">{client_cell}</div>
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
    <div>{html.escape(t("col.client"))}</div>
    <div>{html.escape(t("col.actions"))}</div>
  </div>
  <div class="user-list-body" data-list-body>
    {items}
  </div>
</div>
"""
