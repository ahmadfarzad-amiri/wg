import html

from admin_panel.config import DEFAULT_DAYS, DEFAULT_LIMIT, DEFAULT_SINGLE, admin_url
from admin_panel.core.i18n import t, tf
from admin_panel.core.labels import label_client_status, label_single_mode, label_vpn_mode


def _badge_class(state_key):
    if state_key == "active":
        return "ok"
    if state_key in ("disabled", "offline"):
        return "bad"
    return "warn"


def _remove_confirm_message(client_name, assigned_users):
    if not assigned_users:
        return t("client.remove_confirm")
    users_text = t("fmt.list_sep").join(html.escape(u) for u in assigned_users)
    name = html.escape(client_name)
    return tf("client.remove_confirm_assigned", name=name, users=users_text)


def _client_actions(c, assigned_users=None):
    name = html.escape(c["name"])
    assigned_users = assigned_users or []
    can_enable = c["disabled"]
    can_disable = not c["disabled"]
    can_renew = c.get("expired") or c.get("over_limit")

    enable_attr = "" if can_enable else f'disabled title="{html.escape(t("client.title_already_active"), quote=True)}"'
    disable_attr = "" if can_disable else f'disabled title="{html.escape(t("client.title_already_disabled"), quote=True)}"'
    renew_attr = (
        ""
        if can_renew
        else f'disabled title="{html.escape(t("client.title_renew_only"), quote=True)}"'
    )

    if c["has_config"]:
        config_btn = (
            f'<a class="btn dark btn-sm" href="{admin_url("/config/" + c["name"])}">'
            f"{html.escape(t('client.download'))}</a>"
        )
    else:
        config_btn = (
            f'<button class="dark btn-sm" disabled title="{html.escape(t("client.download_missing"), quote=True)}">'
            f"{html.escape(t('client.download'))}</button>"
        )

    selected = {m: ("selected" if c.get("single") == m else "") for m in ("off", "ip", "endpoint")}
    vpn_selected = {
        m: ("selected" if c.get("vpn_mode", "twohop") == m else "")
        for m in ("twohop", "direct")
    }

    update_form = f"""
<form class="inline-form client-update-form" method="post" action="{admin_url("/client-action")}">
  <input type="hidden" name="client" value="{name}">
  <input type="hidden" name="action" value="update">
  <input name="days" class="input-inline input-compact" placeholder="{html.escape(t("client.days"))}" inputmode="numeric" autocomplete="off">
  <input name="limit" class="input-inline input-compact" placeholder="{html.escape(t("client.limit"))}" autocomplete="off">
  <select name="vpn_mode" class="table-select">
    <option value="">{html.escape(t("client.vpn_unchanged"))}</option>
    <option value="twohop" {vpn_selected["twohop"]}>{html.escape(label_vpn_mode("twohop"))}</option>
    <option value="direct" {vpn_selected["direct"]}>{html.escape(label_vpn_mode("direct"))}</option>
  </select>
  <label class="client-reset-usage">
    <input type="checkbox" name="reset_usage" value="1">
    <span>{html.escape(t("client.reset_usage"))}</span>
  </label>
  <button type="submit" class="btn-sm">{html.escape(t("client.update"))}</button>
</form>
"""

    single_form = f"""
<form class="inline-form table-limit-form" method="post" action="{admin_url("/client-action")}">
  <input type="hidden" name="client" value="{name}">
  <input type="hidden" name="action" value="set-single">
  <select name="single_mode" class="table-select">
    <option value="off" {selected["off"]}>{html.escape(label_single_mode("off"))}</option>
    <option value="ip" {selected["ip"]}>{html.escape(label_single_mode("ip"))}</option>
    <option value="endpoint" {selected["endpoint"]}>{html.escape(label_single_mode("endpoint"))}</option>
  </select>
  <button type="submit" class="dark btn-sm">{html.escape(t("client.save"))}</button>
</form>
"""

    remove_confirm = html.escape(_remove_confirm_message(c["name"], assigned_users), quote=True)

    buttons = f"""
<div class="client-update-wrap">{update_form}</div>
<div class="actions actions-compact">
  {config_btn}
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
    <input type="hidden" name="action" value="renew">
    <button type="submit" class="dark btn-sm" {renew_attr}>{html.escape(t("client.renew"))}</button>
  </form>
  <form class="inline-form" method="post" action="{admin_url("/client-action")}">
    <input type="hidden" name="client" value="{name}">
    <input type="hidden" name="action" value="remove">
    <button type="submit" class="bad btn-sm" data-confirm="{remove_confirm}">{html.escape(t("client.remove"))}</button>
  </form>
</div>
"""
    return single_form, buttons


def client_rows(clients, assigned_names=None, users_by_client_map=None):
    rows = ""
    cards = ""
    assigned_names = assigned_names or set()
    users_by_client_map = users_by_client_map or {}
    for c in clients:
        badge = _badge_class(c["state_key"])
        status = label_client_status(c["state_key"])
        single_form, buttons = _client_actions(
            c, users_by_client_map.get(c["name"], [])
        )
        vpn_badge = html.escape(label_vpn_mode(c.get("vpn_mode", "twohop")))

        usage = f"{c['used']} / {c['limit']}"
        sort_name = html.escape(c["name"].lower())
        sort_ip = html.escape(c["ip"])
        state_key = html.escape(c["state_key"])
        assigned = "1" if c["name"] in assigned_names else "0"
        search_text = html.escape(
            " ".join([c["name"], c["ip"], status, usage, c["last"], c["endpoint"], c["state_key"]]).lower()
        )
        item_attrs = (
            f'data-list-item data-list-primary data-status="{state_key}" data-assigned="{assigned}" '
            f'data-sort-name="{sort_name}" data-sort-ip="{sort_ip}" data-search="{search_text}"'
        )
        rows += f"""
<tr class="client-row client-row-details" {item_attrs}>
  <td class="col-name" title="{html.escape(c['name'])}">{html.escape(c['name'])}</td>
  <td class="col-ip" title="{html.escape(c['ip'])}">{html.escape(c['ip'])}</td>
  <td class="col-vpn" title="{vpn_badge}"><span class="badge vpn-badge">{vpn_badge}</span></td>
  <td class="col-status"><span class="badge {badge}">{html.escape(status)}</span></td>
  <td class="col-usage" title="{html.escape(usage)}">{html.escape(usage)}</td>
  <td class="col-last" title="{html.escape(c['last'])}">{html.escape(c['last'])}</td>
  <td class="col-endpoint" title="{html.escape(c['endpoint'])}">{html.escape(c['endpoint'])}</td>
  <td class="col-limit">{single_form}</td>
</tr>
<tr class="client-row client-row-actions" data-list-actions-row>
  <td colspan="8">
    <div class="client-row-actions-inner">{buttons}</div>
  </td>
</tr>
"""

        cards += f"""
<div class="rowcard" {item_attrs}>
  <div class="rowcard-title">{html.escape(c['name'])} <span class="badge {badge}">{html.escape(status)}</span></div>
  <div class="rowline"><div class="rowlabel">{html.escape(t("col.ip"))}</div><div class="rowvalue">{html.escape(c['ip'])}</div></div>
  <div class="rowline"><div class="rowlabel">{html.escape(t("col.vpn_mode"))}</div><div class="rowvalue"><span class="badge vpn-badge">{vpn_badge}</span></div></div>
  <div class="rowline"><div class="rowlabel">{html.escape(t("col.usage"))}</div><div class="rowvalue">{html.escape(c['used'])} / {html.escape(c['limit'])}</div></div>
  <div class="rowline"><div class="rowlabel">{html.escape(t("col.last_connection"))}</div><div class="rowvalue">{html.escape(c['last'])}</div></div>
  <div class="rowline"><div class="rowlabel">{html.escape(t("col.endpoint"))}</div><div class="rowvalue">{html.escape(c['endpoint'])}</div></div>
  <div class="rowline"><div class="rowlabel">{html.escape(t("client.device_limit"))}</div><div class="rowvalue">{single_form}</div></div>
  <div class="rowactions">{buttons}</div>
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
