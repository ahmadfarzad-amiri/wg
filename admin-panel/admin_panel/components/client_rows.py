import html

from admin_panel.config import DEFAULT_DAYS, DEFAULT_LIMIT, DEFAULT_SINGLE, admin_url
from admin_panel.core.i18n import t, tf
from admin_panel.core.labels import label_client_status, label_single_mode, label_vpn_mode
from admin_panel.core.statuses import ClientState
from admin_panel.core.wireguard import human_time

CLIENT_COLSPAN = 6


def _badge_class(state_key):
    if state_key == ClientState.ACTIVE:
        return "ok"
    if state_key in (ClientState.DISABLED, ClientState.OFFLINE):
        return "bad"
    return "warn"


def _remove_confirm_message(client_name, assigned_users):
    if not assigned_users:
        return t("client.remove_confirm")
    users_text = t("fmt.list_sep").join(html.escape(u) for u in assigned_users)
    name = html.escape(client_name)
    return tf("client.remove_confirm_assigned", name=name, users=users_text)


def _client_update_form(c):
    name = html.escape(c["name"])
    vpn_mode = c.get("vpn_mode", "twohop")
    vpn_selected = {
        m: ("selected" if vpn_mode == m else "") for m in ("twohop", "direct")
    }
    days_val = html.escape(c.get("update_days") or "", quote=True)
    limit_val = html.escape(c.get("update_limit") or "", quote=True)

    return f"""
<form class="inline-form client-update-form" method="post" action="{admin_url("/client-action")}">
  <input type="hidden" name="client" value="{name}">
  <input type="hidden" name="action" value="update">
  <label class="client-update-field">
    <span class="client-update-label">{html.escape(t("client.days"))}</span>
    <input name="days" class="input-inline input-compact" value="{days_val}" inputmode="numeric" autocomplete="off">
  </label>
  <label class="client-update-field">
    <span class="client-update-label">{html.escape(t("client.limit"))}</span>
    <input name="limit" class="input-inline input-compact" value="{limit_val}" autocomplete="off">
  </label>
  <label class="client-update-field">
    <span class="client-update-label">{html.escape(t("client.vpn_mode"))}</span>
    <select name="vpn_mode" class="table-select">
      <option value="twohop" {vpn_selected["twohop"]}>{html.escape(label_vpn_mode("twohop"))}</option>
      <option value="direct" {vpn_selected["direct"]}>{html.escape(label_vpn_mode("direct"))}</option>
    </select>
  </label>
  <label class="client-reset-usage">
    <input type="checkbox" name="reset_usage" value="1">
    <span>{html.escape(t("client.reset_usage"))}</span>
  </label>
  <button type="submit" class="btn-sm">{html.escape(t("client.update"))}</button>
</form>
"""


def _client_action_buttons(c, assigned_users=None):
    name = html.escape(c["name"])
    assigned_users = assigned_users or []
    can_enable = c["disabled"]
    can_disable = not c["disabled"]
    can_renew = c.get("expired") or c.get("over_limit")

    enable_attr = "" if can_enable else "disabled"
    disable_attr = "" if can_disable else "disabled"
    renew_attr = "" if can_renew else "disabled"

    if c["has_config"]:
        download = (
            f'<a class="btn btn-sm" href="{admin_url("/config/" + c["name"])}">'
            f"{html.escape(t('client.download'))}</a>"
        )
    else:
        download = (
            f'<span class="btn btn-sm is-disabled" title="{html.escape(t("client.download_missing"), quote=True)}">'
            f"{html.escape(t('client.download'))}</span>"
        )

    remove_confirm = html.escape(_remove_confirm_message(c["name"], assigned_users), quote=True)

    return f"""
<div class="client-action-buttons">
  {download}
  <form class="inline-form" method="post" action="{admin_url("/client-action")}">
    <input type="hidden" name="client" value="{name}">
    <input type="hidden" name="action" value="renew">
    <button type="submit" class="btn-sm" {renew_attr}>{html.escape(t("client.renew"))}</button>
  </form>
  <form class="inline-form" method="post" action="{admin_url("/client-action")}">
    <input type="hidden" name="client" value="{name}">
    <input type="hidden" name="action" value="enable">
    <button type="submit" class="btn-sm" {enable_attr}>{html.escape(t("client.enable"))}</button>
  </form>
  <form class="inline-form" method="post" action="{admin_url("/client-action")}">
    <input type="hidden" name="client" value="{name}">
    <input type="hidden" name="action" value="disable">
    <button type="submit" class="dark btn-sm" {disable_attr}>{html.escape(t("client.disable"))}</button>
  </form>
  <form class="inline-form" method="post" action="{admin_url("/client-action")}">
    <input type="hidden" name="client" value="{name}">
    <input type="hidden" name="action" value="remove">
    <button type="submit" class="bad btn-sm" data-confirm="{remove_confirm}">{html.escape(t("client.remove"))}</button>
  </form>
</div>
"""


def _client_single_form(c):
    name = html.escape(c["name"])
    selected = {m: ("selected" if c.get("single") == m else "") for m in ("off", "ip", "endpoint")}
    return f"""
<form class="inline-form table-limit-form" method="post" action="{admin_url("/client-action")}">
  <input type="hidden" name="client" value="{name}">
  <input type="hidden" name="action" value="set-single">
  <select name="single_mode" class="table-select" aria-label="{html.escape(t("client.device_limit"))}">
    <option value="off" {selected["off"]}>{html.escape(label_single_mode("off"))}</option>
    <option value="ip" {selected["ip"]}>{html.escape(label_single_mode("ip"))}</option>
    <option value="endpoint" {selected["endpoint"]}>{html.escape(label_single_mode("endpoint"))}</option>
  </select>
  <button type="submit" class="dark btn-sm">{html.escape(t("client.save"))}</button>
</form>
"""


def client_rows(clients, assigned_names=None, users_by_client_map=None):
    rows = ""
    cards = ""
    assigned_names = assigned_names or set()
    users_by_client_map = users_by_client_map or {}
    for c in clients:
        badge = _badge_class(c["state_key"])
        status = label_client_status(c["state_key"])
        assigned_users = users_by_client_map.get(c["name"], [])
        single_form = _client_single_form(c)
        update_form = _client_update_form(c)
        action_buttons = _client_action_buttons(c, assigned_users)
        vpn_badge = html.escape(label_vpn_mode(c.get("vpn_mode", "twohop")))

        usage = f"{c['used']} / {c['limit']}"
        duration = c.get("duration", t("unlimited"))
        expires_title = ""
        if c.get("expires_at"):
            expires_title = f' title="{html.escape(human_time(c["expires_at"]), quote=True)}"'

        sort_name = html.escape(c["name"].lower())
        sort_ip = html.escape(c["ip"])
        state_key = html.escape(c["state_key"])
        assigned = "1" if c["name"] in assigned_names else "0"
        sort_duration = str(c.get("days_left") if c.get("days_left") is not None else 999999)
        search_text = html.escape(
            " ".join(
                [
                    c["name"],
                    c["ip"],
                    status,
                    usage,
                    duration,
                    c["last"],
                    c["endpoint"],
                    c["state_key"],
                ]
            ).lower()
        )
        item_attrs = (
            f'data-list-item data-list-primary data-status="{state_key}" data-assigned="{assigned}" '
            f'data-sort-name="{sort_name}" data-sort-ip="{sort_ip}" data-sort-duration="{sort_duration}" '
            f'data-search="{search_text}"'
        )
        ip_hint = html.escape(c["ip"])
        rows += f"""
<tr class="client-row client-row-details" {item_attrs}>
  <td class="col-name" title="{html.escape(c['name'])} · {ip_hint}">
    <span class="client-name">{html.escape(c['name'])}</span>
    <span class="client-name-meta">{ip_hint}</span>
  </td>
  <td class="col-status"><span class="badge {badge}">{html.escape(status)}</span></td>
  <td class="col-usage" title="{html.escape(usage)}">{html.escape(usage)}</td>
  <td class="col-duration"{expires_title}>{html.escape(duration)}</td>
  <td class="col-limit">{single_form}</td>
  <td class="col-actions">{action_buttons}</td>
</tr>
<tr class="client-row client-row-actions" data-list-actions-row>
  <td colspan="{CLIENT_COLSPAN}">
    <details class="client-edit-details">
      <summary>{html.escape(t("client.edit_subscription"))}</summary>
      <div class="client-row-actions-inner">{update_form}</div>
    </details>
  </td>
</tr>
"""

        cards += f"""
<div class="rowcard" {item_attrs}>
  <div class="rowcard-title">{html.escape(c['name'])} <span class="badge {badge}">{html.escape(status)}</span></div>
  <div class="rowline"><div class="rowlabel">{html.escape(t("col.ip"))}</div><div class="rowvalue">{html.escape(c['ip'])}</div></div>
  <div class="rowline"><div class="rowlabel">{html.escape(t("col.usage"))}</div><div class="rowvalue">{html.escape(c['used'])} / {html.escape(c['limit'])}</div></div>
  <div class="rowline"><div class="rowlabel">{html.escape(t("col.duration"))}</div><div class="rowvalue"{expires_title}>{html.escape(duration)}</div></div>
  <div class="rowline"><div class="rowlabel">{html.escape(t("client.device_limit"))}</div><div class="rowvalue">{single_form}</div></div>
  <details class="client-edit-details">
    <summary>{html.escape(t("client.edit_subscription"))}</summary>
    <div class="rowline rowline-update"><div class="rowvalue">{update_form}</div></div>
  </details>
  <div class="rowactions">{action_buttons}</div>
</div>
"""
    return rows, cards


def add_client_form():
    single_opts = [
        ("--single-ip", label_single_mode("ip")),
        ("--single-endpoint", label_single_mode("endpoint")),
        ("--no-single", label_single_mode("off")),
    ]
    tabs = "".join(
        f'<label class="option-tab">'
        f'<input type="radio" name="single" value="{html.escape(value)}"'
        f'{" checked" if value == DEFAULT_SINGLE else ""}>'
        f"<span>{html.escape(label)}</span></label>"
        for value, label in single_opts
    )
    device_limit = html.escape(t("client.device_limit"))
    vpn_mode_label = html.escape(t("client.vpn_mode"))
    return f"""
<form method="post" action="{admin_url("/client-action")}" class="add-client-form">
  <input type="hidden" name="action" value="add">
  <div class="add-client-fields">
    <label class="field field-name">
      <span class="field-label">{html.escape(t("client.name"))}</span>
      <input name="client" class="field-input" placeholder="farzad_" required autocomplete="off">
    </label>
    <label class="field field-vpn">
      <span class="field-label">{vpn_mode_label}</span>
      <select name="vpn_mode" class="field-input">
        <option value="twohop" selected>{html.escape(label_vpn_mode("twohop"))}</option>
        <option value="direct">{html.escape(label_vpn_mode("direct"))}</option>
      </select>
      <span class="field-hint">{html.escape(t("client.vpn_mode_hint"))}</span>
    </label>
    <label class="field field-days">
      <span class="field-label">{html.escape(t("client.days"))}</span>
      <input name="days" class="field-input" value="{html.escape(DEFAULT_DAYS)}" inputmode="numeric">
    </label>
    <label class="field field-limit">
      <span class="field-label">{html.escape(t("client.limit"))}</span>
      <input name="limit" class="field-input" value="{html.escape(DEFAULT_LIMIT)}" placeholder="20G">
    </label>
    <div class="field field-single">
      <span class="field-label">{device_limit}</span>
      <div class="option-tabs" role="radiogroup" aria-label="{device_limit}">
        {tabs}
      </div>
    </div>
    <div class="field field-submit">
      <button type="submit" class="btn btn-sm add-client-submit">{html.escape(t("client.add"))}</button>
    </div>
  </div>
</form>
"""
