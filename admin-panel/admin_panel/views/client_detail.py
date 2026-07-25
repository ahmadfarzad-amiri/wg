import html

from admin_panel.components.client_rows import client_update_form, client_detail_actions
from admin_panel.components.notice import notice
from admin_panel.config import admin_url
from admin_panel.core.i18n import t
from admin_panel.core.labels import label_client_status, label_single_mode, label_vpn_mode
from admin_panel.core.statuses import ClientState


def _badge_class(state_key):
    if state_key == ClientState.ACTIVE:
        return "ok"
    if state_key in (ClientState.DISABLED, ClientState.OFFLINE):
        return "bad"
    return "warn"


def body(client, msg="", variant="info", assigned_users=None):
    assigned_users = assigned_users or []
    name = client["name"]
    badge = _badge_class(client["state_key"])
    status = label_client_status(client["state_key"])
    users_html = (
        "<ul class='plain-list'>"
        + "".join(f"<li>{html.escape(u)}</li>" for u in assigned_users)
        + "</ul>"
        if assigned_users
        else f"<p class='hint'>{html.escape(t('client.no_assigned_users'))}</p>"
    )
    from wg_common.entry_mode import is_standalone_entry

    if is_standalone_entry():
        vpn_hint = f"<p class='field-hint'>{html.escape(t('client.vpn_standalone_hint'))}</p>"
    elif client.get("vpn_mode") == "direct":
        vpn_hint = f"<p class='field-hint field-hint--warn'>{html.escape(t('client.vpn_direct_hint'))}</p>"
    else:
        vpn_hint = f"<p class='field-hint'>{html.escape(t('client.vpn_mode_hint'))}</p>"

    return f"""
<p class="back-link"><a class="btn ghost btn-sm" href="{admin_url('/clients')}">{html.escape(t("client.back_to_list"))}</a></p>
<h1>{html.escape(name)}</h1>
<p class="subtitle">{html.escape(t("client.detail_subtitle"))}</p>
{notice(msg, variant=variant)}

<div class="page-stack">
<section class="card">
  <h3>{html.escape(t("client.overview"))}</h3>
  <div class="statrow">
    <div class="item"><div class="label">{html.escape(t("col.status"))}</div><div class="value"><span class="badge {badge}">{html.escape(status)}</span></div></div>
    <div class="item"><div class="label">{html.escape(t("col.usage"))}</div><div class="value">{html.escape(client['used'])} / {html.escape(client['limit'])}</div></div>
    <div class="item"><div class="label">{html.escape(t("col.duration"))}</div><div class="value">{html.escape(client.get('duration') or t('unlimited'))}</div></div>
    <div class="item"><div class="label">{html.escape(t("client.vpn_mode"))}</div><div class="value">{html.escape(label_vpn_mode(client.get('vpn_mode', 'twohop')))}</div></div>
    <div class="item"><div class="label">{html.escape(t("client.device_limit"))}</div><div class="value">{html.escape(label_single_mode(client.get('single', 'off')))}</div></div>
    <div class="item"><div class="label">{html.escape(t("col.ip"))}</div><div class="value ltr-value">{html.escape(client.get('ip') or '—')}</div></div>
  </div>
  {vpn_hint}
  {client_detail_actions(client, assigned_users)}
</section>

<section class="card">
  <h3>{html.escape(t("client.edit_subscription"))}</h3>
  <p class="hint">{html.escape(t("client.edit_hint"))}</p>
  {client_update_form(client)}
</section>

<section class="card">
  <h3>{html.escape(t("client.assigned_users"))}</h3>
  {users_html}
</section>
</div>
"""
