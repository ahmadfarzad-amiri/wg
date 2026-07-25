import html

from admin_panel.components.action_menu import action_menu
from admin_panel.config import DEFAULT_DAYS, DEFAULT_LIMIT, DEFAULT_SINGLE, admin_url
from admin_panel.core.i18n import t, tf
from admin_panel.core.labels import label_client_status, label_single_mode, label_vpn_mode
from admin_panel.core.statuses import ClientState
from admin_panel.core.wireguard import human_time


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


def _usage_pct(c):
    limit = int(c.get("limit_bytes") or 0)
    used = int(c.get("used_bytes") or 0)
    if limit <= 0:
        return None
    return min(100, used * 100 // limit)


def _usage_bar(c):
    pct = _usage_pct(c)
    usage = f"{c['used']} / {c['limit']}"
    if pct is None:
        return f"""
<div class="client-usage">
  <span class="client-usage-text">{html.escape(usage)}</span>
</div>
"""
    bar_class = "ok"
    if c.get("over_limit"):
        bar_class = "bad"
    elif pct >= 85:
        bar_class = "warn"
    return f"""
<div class="client-usage">
  <div class="client-usage-bar client-usage-bar--{bar_class}" role="progressbar" aria-valuenow="{pct}" aria-valuemin="0" aria-valuemax="100" title="{html.escape(usage, quote=True)}">
    <span class="client-usage-fill" style="width:{pct}%"></span>
  </div>
  <span class="client-usage-text">{html.escape(usage)}</span>
</div>
"""


def _option_tabs(name, options, selected_value, group_label):
    tabs = ""
    for value, label in options:
        checked = " checked" if selected_value == value else ""
        value_esc = html.escape(value, quote=True)
        tabs += (
            f'<label class="option-tab">'
            f'<input type="radio" name="{html.escape(name)}" value="{value_esc}"{checked}>'
            f"<span>{html.escape(label)}</span></label>"
        )
    return (
        f'<div class="option-tabs" role="radiogroup" aria-label="{html.escape(group_label)}">'
        f"{tabs}</div>"
    )


def client_update_form(c):
    name = html.escape(c["name"])
    vpn_mode = c.get("vpn_mode", "twohop")
    single = c.get("single", "off")
    days_val = html.escape(c.get("update_days") or "", quote=True)
    limit_val = html.escape(c.get("update_limit") or "", quote=True)
    vpn_tabs = _option_tabs(
        "vpn_mode",
        [("twohop", label_vpn_mode("twohop")), ("direct", label_vpn_mode("direct"))],
        vpn_mode,
        t("client.vpn_mode"),
    )
    single_tabs = _option_tabs(
        "single_mode",
        [
            ("off", label_single_mode("off")),
            ("ip", label_single_mode("ip")),
            ("endpoint", label_single_mode("endpoint")),
        ],
        single,
        t("client.device_limit"),
    )

    return f"""
<form class="form-stack client-update-form" method="post" action="{admin_url("/client-action")}">
  <input type="hidden" name="client" value="{name}">
  <input type="hidden" name="action" value="update">
  <div class="form-grid">
    <div class="field">
      <label class="field-label" for="days-{name}">{html.escape(t("client.days"))}</label>
      <input id="days-{name}" name="days" class="field-input" value="{days_val}" inputmode="numeric" autocomplete="off">
    </div>
    <div class="field">
      <label class="field-label" for="limit-{name}">{html.escape(t("client.limit"))}</label>
      <input id="limit-{name}" name="limit" class="field-input" value="{limit_val}" autocomplete="off">
    </div>
    <div class="field field--full">
      <span class="field-label">{html.escape(t("client.vpn_mode"))}</span>
      {vpn_tabs}
      <p class="field-hint field-hint--warn">{html.escape(t("client.vpn_direct_hint"))}</p>
    </div>
    <div class="field field--full">
      <span class="field-label">{html.escape(t("client.device_limit"))}</span>
      {single_tabs}
    </div>
    <label class="field field--full client-reset-usage">
      <span class="field-label">
        <input type="checkbox" name="reset_usage" value="1">
        {html.escape(t("client.reset_usage"))}
      </span>
    </label>
    <div class="field field--full">
      <button type="submit" class="btn">{html.escape(t("client.save_changes"))}</button>
    </div>
  </div>
</form>
"""


def _client_update_form(c):
    return client_update_form(c)


def _client_action_menu(c, assigned_users=None):
    assigned_users = assigned_users or []
    can_enable = c["disabled"]
    can_disable = not c["disabled"]
    can_renew = c.get("expired") or c.get("over_limit")
    remove_confirm = _remove_confirm_message(c["name"], assigned_users)
    url = admin_url("/client-action")
    prefix = {"client": c["name"]}

    return action_menu(
        url,
        prefix,
        [
            ({}, "renew", t("client.renew"), can_renew),
            ({}, "enable", t("client.enable"), can_enable),
            ({}, "disable", t("client.disable"), can_disable),
            ({}, "remove", t("client.remove"), True, True, remove_confirm),
        ],
        aria_label=t("user.more_actions"),
    )


def _client_toolbar(c, assigned_users=None, *, include_edit=True):
    name = c["name"]
    edit = ""
    if include_edit:
        edit = (
            f'<a class="btn btn-sm dark" href="{admin_url("/clients/" + name)}">'
            f"{html.escape(t('client.edit'))}</a>"
        )
    if c["has_config"]:
        download = (
            f'<a class="btn btn-sm client-download" href="{admin_url("/config/" + name)}">'
            f"{html.escape(t('client.download'))}</a>"
        )
        qr_btn = (
            f'<a class="btn btn-sm dark client-qr" href="{admin_url("/config-qr/" + name)}" '
            f'target="_blank" rel="noopener">{html.escape(t("client.qr"))}</a>'
        )
    else:
        download = (
            f'<span class="btn btn-sm client-download is-disabled" title="{html.escape(t("client.download_missing"), quote=True)}">'
            f"{html.escape(t('client.download'))}</span>"
        )
        qr_btn = ""

    return f"""
<div class="client-toolbar">
  {edit}
  {download}
  {qr_btn}
  {_client_action_menu(c, assigned_users)}
</div>
"""


def client_detail_actions(c, assigned_users=None):
    return _client_toolbar(c, assigned_users, include_edit=False)


def _client_item(c, assigned_names, users_by_client_map):
    badge = _badge_class(c["state_key"])
    status = label_client_status(c["state_key"])
    assigned_users = users_by_client_map.get(c["name"], [])
    toolbar = _client_toolbar(c, assigned_users)
    usage_bar = _usage_bar(c)
    vpn_label = html.escape(label_vpn_mode(c.get("vpn_mode", "twohop")))
    device_label = html.escape(label_single_mode(c.get("single", "off")))

    duration = c.get("duration", t("unlimited"))
    expires_title = ""
    if c.get("expires_at"):
        expires_title = f' title="{html.escape(human_time(c["expires_at"]), quote=True)}"'

    sort_name = html.escape(c["name"].lower())
    sort_ip = html.escape(c["ip"])
    state_key = html.escape(c["state_key"])
    assigned = "1" if c["name"] in assigned_names else "0"
    sort_duration = str(c.get("days_left") if c.get("days_left") is not None else 999999)
    usage = f"{c['used']} / {c['limit']}"
    search_text = html.escape(
        " ".join(
            [
                c["name"],
                c["ip"],
                status,
                usage,
                duration,
                vpn_label,
                device_label,
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
    name_esc = html.escape(c["name"])

    return f"""
<div class="client-item" {item_attrs}>
  <div class="client-field client-field-name" data-label="{html.escape(t("col.name"))}">
    <span class="client-item-name">{name_esc}</span>
    <span class="client-item-meta">{ip_hint}</span>
    <span class="client-item-chips">
      <span class="client-chip vpn-badge">{vpn_label}</span>
      <span class="client-chip">{device_label}</span>
    </span>
  </div>
  <div class="client-field client-field-status" data-label="{html.escape(t("col.status"))}">
    <span class="badge {badge}">{html.escape(status)}</span>
  </div>
  <div class="client-field client-field-usage" data-label="{html.escape(t("col.usage"))}">
    {usage_bar}
  </div>
  <div class="client-field client-field-duration" data-label="{html.escape(t("col.duration"))}"{expires_title}>
    {html.escape(duration)}
  </div>
  <div class="client-field client-field-actions" data-label="{html.escape(t("col.actions"))}">
    {toolbar}
  </div>
</div>
"""


def client_list(clients, assigned_names=None, users_by_client_map=None):
    assigned_names = assigned_names or set()
    users_by_client_map = users_by_client_map or {}

    if not clients:
        return f"""
<div class="client-list" data-list-items data-list-kind="clients">
  <div class="client-list-empty" data-list-static-empty>
    <p>{html.escape(t("empty.no_clients"))}</p>
    <p class="hint">{html.escape(t("empty.no_clients_cta"))}</p>
  </div>
</div>
"""

    items = "".join(
        _client_item(c, assigned_names, users_by_client_map) for c in clients
    )
    return f"""
<div class="client-list-wrap">
<div class="client-list" data-list-items data-list-kind="clients">
  <div class="client-list-head">
    <div>{html.escape(t("col.name"))}</div>
    <div>{html.escape(t("col.status"))}</div>
    <div>{html.escape(t("col.usage"))}</div>
    <div>{html.escape(t("col.duration"))}</div>
    <div>{html.escape(t("col.actions"))}</div>
  </div>
  <div class="client-list-body" data-list-body>
    {items}
  </div>
</div>
</div>
"""


def bulk_add_client_form():
    vpn_tabs = _option_tabs(
        "vpn_mode",
        [("twohop", label_vpn_mode("twohop")), ("direct", label_vpn_mode("direct"))],
        "twohop",
        t("client.vpn_mode"),
    )
    return f"""
<form method="post" action="{admin_url("/client-bulk")}" class="add-client-form">
  <div class="add-client-fields">
    <label class="field field-name" style="grid-column:1/-1">
      <span class="field-label">{html.escape(t("clients.bulk_names_label"))}</span>
      <textarea name="names" class="field-input" rows="5"
        placeholder="{html.escape(t('clients.bulk_names_placeholder'), quote=True)}"
        required autocomplete="off"></textarea>
      <span class="field-hint">{html.escape(t("clients.bulk_names_hint"))}</span>
    </label>
    <div class="field field-vpn">
      <span class="field-label">{html.escape(t("client.vpn_mode"))}</span>
      {vpn_tabs}
    </div>
    <label class="field field-days">
      <span class="field-label">{html.escape(t("client.days"))}</span>
      <input name="days" class="field-input" value="{html.escape(DEFAULT_DAYS)}" inputmode="numeric">
    </label>
    <label class="field field-limit">
      <span class="field-label">{html.escape(t("client.limit"))}</span>
      <input name="limit" class="field-input" value="{html.escape(DEFAULT_LIMIT)}" placeholder="20G">
    </label>
    <div class="field field-submit">
      <button type="submit" class="btn btn-sm add-client-submit"
        data-confirm="{html.escape(t('clients.bulk_add_confirm'), quote=True)}">
        {html.escape(t("clients.bulk_add_btn"))}
      </button>
    </div>
  </div>
</form>
"""


def add_client_form():
    single_opts = [
        ("--single-ip", label_single_mode("ip")),
        ("--single-endpoint", label_single_mode("endpoint")),
        ("--no-single", label_single_mode("off")),
    ]
    single_tabs = "".join(
        f'<label class="option-tab">'
        f'<input type="radio" name="single" value="{html.escape(value)}"'
        f'{" checked" if value == DEFAULT_SINGLE else ""}>'
        f"<span>{html.escape(label)}</span></label>"
        for value, label in single_opts
    )
    vpn_tabs = _option_tabs(
        "vpn_mode",
        [("twohop", label_vpn_mode("twohop")), ("direct", label_vpn_mode("direct"))],
        "twohop",
        t("client.vpn_mode"),
    )
    device_limit = html.escape(t("client.device_limit"))
    vpn_mode_label = html.escape(t("client.vpn_mode"))
    return f"""
<form method="post" action="{admin_url("/client-action")}" class="add-client-form">
  <input type="hidden" name="action" value="add">
  <div class="add-client-fields">
    <label class="field field-name">
      <span class="field-label">{html.escape(t("client.name"))}</span>
      <input name="client" class="field-input" placeholder="alice" required autocomplete="off">
    </label>
    <div class="field field-vpn">
      <span class="field-label">{vpn_mode_label}</span>
      {vpn_tabs}
      <span class="field-hint">{html.escape(t("client.vpn_mode_hint"))}</span>
    </div>
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
        {single_tabs}
      </div>
    </div>
    <div class="field field-submit">
      <button type="submit" class="btn btn-sm add-client-submit">{html.escape(t("client.add"))}</button>
    </div>
  </div>
</form>
"""
