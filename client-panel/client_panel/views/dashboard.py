import html

from client_panel.components.status import client_status_section
from client_panel.core.i18n import t


def _config_item_row(s):
    return f"""
<article class="config-item card-inset">
  <div class="config-item__head">
    <h4 class="config-item__name">{html.escape(s['client_name'])}</h4>
    <span class="badge vpn-badge">{html.escape(s['vpn_mode_text'])}</span>
    <span class="badge {s['badge']}">{html.escape(s['state'])}</span>
  </div>
  <div class="config-item__grid grid">
    <div class="item"><div class="label">{html.escape(t("dashboard.vpn_address"))}</div><div class="value">{html.escape(s['ip'])}</div></div>
    <div class="item"><div class="label">{html.escape(t("dashboard.last_handshake"))}</div><div class="value">{html.escape(s['handshake'])}</div></div>
    <div class="item"><div class="label">{html.escape(t("dashboard.usage_pct"))}</div><div class="value">{html.escape(s['percent'])}%</div></div>
    <div class="item"><div class="label">{html.escape(t("dashboard.days_left"))}</div><div class="value">{html.escape(s['days_left'])}</div></div>
  </div>
  <div class="config-item__actions">
    <a class="btn btn-sm" href="/config?client={html.escape(s['client_name'], quote=True)}">{html.escape(t("dashboard.download_one"))}</a>
  </div>
</article>
"""


def config_list_section(statuses):
    if not statuses:
        return ""
    items = "".join(_config_item_row(s) for s in statuses)
    return f"""
<section class="card card-spaced">
  <h3>{html.escape(t("dashboard.your_configs"))}</h3>
  <p class="hint">{html.escape(t("dashboard.your_configs_hint"))}</p>
  <div class="config-list">{items}</div>
</section>
"""


def body(user, primary, all_statuses):
    s = primary
    expiry_bar = 0 if s["days_left"] == t("unlimited") else s.get("expiry_percent", 0)
    multi = len(all_statuses) > 1

    return f"""
<h1>{html.escape(t("page.dashboard"))}</h1>
<p class="subtitle">{html.escape(t("dashboard.subtitle"))}</p>

<div class="grid">
  <section class="card">
    <h3>{html.escape(t("dashboard.data_usage"))} <span class="badge {s['badge']}">{html.escape(s['state'])}</span></h3>
    <p class="hint">{html.escape(t("dashboard.primary_config"))}: <strong>{html.escape(s['client_name'])}</strong></p>
    <div class="label">{html.escape(t("dashboard.usage_pct"))}</div>
    <div class="progress" role="progressbar" aria-valuenow="{s['percent']}" aria-valuemin="0" aria-valuemax="100">
      <div class="bar" style="width:{s['percent']}%"></div>
    </div>
    <div class="statrow">
      <div class="item"><div class="label">{html.escape(t("dashboard.remaining"))}</div><div class="value">{html.escape(s['remaining'])}</div></div>
      <div class="item"><div class="label">{html.escape(t("dashboard.used"))}</div><div class="value">{html.escape(s['used'])}</div></div>
      <div class="item"><div class="label">{html.escape(t("dashboard.limit"))}</div><div class="value">{html.escape(s['limit'])}</div></div>
    </div>
  </section>

  <section class="card">
    <h3>{html.escape(t("dashboard.subscription_period"))} <span class="badge {s['badge']}">{html.escape(s['state'])}</span></h3>
    <div class="label">{html.escape(t("dashboard.time_remaining"))}</div>
    <div class="progress" role="progressbar" aria-valuenow="{expiry_bar}" aria-valuemin="0" aria-valuemax="100">
      <div class="bar bar-cyan" style="width:{expiry_bar}%"></div>
    </div>
    <div class="statrow">
      <div class="item"><div class="label">{html.escape(t("dashboard.expiry_date"))}</div><div class="value">{html.escape(s['expires'])}</div></div>
      <div class="item"><div class="label">{html.escape(t("dashboard.days_left"))}</div><div class="value">{html.escape(s['days_left'])}</div></div>
      <div class="item"><div class="label">{html.escape(t("dashboard.status"))}</div><div class="value">{html.escape(s['state'])}</div></div>
    </div>
  </section>
</div>

{config_list_section(all_statuses) if multi else ""}

<section class="card card-spaced">
  <h3>{html.escape(t("dashboard.connection_details"))}</h3>
  <div class="grid">
    <div class="item"><div class="label">{html.escape(t("dashboard.config_name"))}</div><div class="value">{html.escape(s['client_name'])}</div></div>
    <div class="item"><div class="label">{html.escape(t("dashboard.vpn_mode"))}</div><div class="value">{html.escape(s['vpn_mode_text'])}</div></div>
    <div class="item"><div class="label">{html.escape(t("dashboard.vpn_address"))}</div><div class="value">{html.escape(s['ip'])}</div></div>
    <div class="item"><div class="label">{html.escape(t("dashboard.last_handshake"))}</div><div class="value">{html.escape(s['handshake'])}</div></div>
    <div class="item"><div class="label">{html.escape(t("dashboard.endpoint"))}</div><div class="value">{html.escape(s['endpoint'])}</div></div>
    <div class="item item-wide"><div class="label">{html.escape(t("dashboard.device_limit"))}</div><div class="value">{html.escape(s['single_text'])}</div></div>
    <div class="item"><div class="label">{html.escape(t("dashboard.disable_reason"))}</div><div class="value">{html.escape(s['disabled_reason'])}</div></div>
  </div>
</section>

{client_status_section(s)}
"""


def body_pending():
    return f"""
<h1>{html.escape(t("page.dashboard"))}</h1>
<p class="subtitle">{html.escape(t("dashboard.pending_sub"))}</p>
<div class="notice">{html.escape(t("dashboard.pending"))}</div>
"""


def body_inactive():
    return f"<h1>{html.escape(t('page.dashboard'))}</h1><div class='notice'>{html.escape(t('dashboard.inactive'))}</div>"


def body_no_config():
    return f"<h1>{html.escape(t('page.dashboard'))}</h1><div class='notice'>{html.escape(t('dashboard.no_config'))}</div>"
