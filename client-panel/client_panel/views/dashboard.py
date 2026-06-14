import html

from client_panel.components.status import client_status_section
from client_panel.core.i18n import t
from client_panel.core.xray import get_links_for_client


def _text(val):
    return html.escape("" if val is None else str(val))


def _config_item_row(s):
    return f"""
<article class="config-item card-inset">
  <div class="config-item__head">
    <h4 class="config-item__name">{html.escape(s['client_name'])}</h4>
    <span class="badge {s['badge']}">{html.escape(s['state'])}</span>
  </div>
  <div class="config-item__grid grid">
    <div class="item"><div class="label">{html.escape(t("dashboard.days_left"))}</div><div class="value">{_text(s['days_left'])}</div></div>
    <div class="item"><div class="label">{html.escape(t("dashboard.usage_pct"))}</div><div class="value">{_text(s['percent'])}%</div></div>
    <div class="item"><div class="label">{html.escape(t("dashboard.remaining"))}</div><div class="value">{_text(s['remaining'])}</div></div>
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
<section class="card">
  <h3>{html.escape(t("dashboard.your_configs"))}</h3>
  <p class="hint">{html.escape(t("dashboard.your_configs_hint"))}</p>
  <div class="config-list">{items}</div>
</section>
"""


def _technical_details(s, show_all):
    rows = [
        (t("dashboard.config_name"), s["client_name"]),
        (t("dashboard.vpn_address"), s["ip"]),
    ]
    if show_all:
        rows.extend(
            [
                (t("dashboard.vpn_mode"), s["vpn_mode_text"]),
                (t("dashboard.last_handshake"), s["handshake"]),
                (t("dashboard.disable_reason"), s["disabled_reason"]),
            ]
        )
    rows.append((t("dashboard.device_limit"), s["single_text"]))

    items = "".join(
        f'<div class="item"><div class="label">{html.escape(label)}</div>'
        f'<div class="value">{html.escape(str(val))}</div></div>'
        for label, val in rows
        if val and str(val).lower() not in ("—", "-", "none", "", "n/a")
    )
    return items


_XRAY_PROTO_LABELS = {
    "reality": "dashboard.xray_reality",
    "ws": "dashboard.xray_ws",
    "ss": "dashboard.xray_ss",
}


def xray_protocols_section(client_name):
    """Return an Xray protocols card if the client has an Xray profile, else empty string."""
    try:
        links = get_links_for_client(client_name)
    except Exception:
        return ""
    if not links:
        return ""

    rows = []
    for key, label_key in _XRAY_PROTO_LABELS.items():
        if key not in links:
            continue
        input_id = html.escape(f"xray-{key}", quote=True)
        link_val = html.escape(links[key], quote=True)
        rows.append(
            f'<div class="xray-link-row">'
            f'<span class="xray-link-label">{html.escape(t(label_key))}</span>'
            f'<input class="field-input xray-link-input" type="text" id="{input_id}" '
            f'value="{link_val}" readonly>'
            f'<button type="button" class="btn btn-sm" data-copy-target="{input_id}">'
            f'{html.escape(t("dashboard.xray_copy"))}</button>'
            f'</div>'
        )

    return f"""
<section class="card">
  <h3>{html.escape(t("dashboard.xray_title"))}</h3>
  <p class="hint">{html.escape(t("dashboard.xray_hint"))}</p>
  {"".join(rows)}
  <p class="hint">{html.escape(t("dashboard.xray_apps_hint"))}</p>
</section>
"""


def body(user, primary, all_statuses):
    s = primary
    expiry_bar = 0 if s["days_left"] == t("unlimited") else s.get("expiry_percent", 0)
    multi = len(all_statuses) > 1
    show_technical = s.get("state_key") != "active"

    return f"""
<h1>{html.escape(t("page.dashboard"))}</h1>
<p class="subtitle">{html.escape(t("dashboard.subtitle"))}</p>

<div class="page-stack">
<div class="dashboard-metrics">
  <section class="card">
    <h3>{html.escape(t("dashboard.data_usage"))}</h3>
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
    <h3>{html.escape(t("dashboard.subscription_period"))}</h3>
    <div class="label">{html.escape(t("dashboard.time_remaining"))}</div>
    <div class="progress" role="progressbar" aria-valuenow="{expiry_bar}" aria-valuemin="0" aria-valuemax="100">
      <div class="bar bar-cyan" style="width:{expiry_bar}%"></div>
    </div>
    <div class="statrow">
      <div class="item"><div class="label">{html.escape(t("dashboard.expiry_date"))}</div><div class="value">{html.escape(s['expires'])}</div></div>
      <div class="item"><div class="label">{html.escape(t("dashboard.days_left"))}</div><div class="value">{_text(s['days_left'])}</div></div>
      <div class="item"><div class="label">{html.escape(t("dashboard.status"))}</div><div class="value"><span class="badge {s['badge']}">{html.escape(s['state'])}</span></div></div>
    </div>
  </section>
</div>

{config_list_section(all_statuses) if multi else ""}

<section class="card">
  <h3>{html.escape(t("dashboard.account_info"))}</h3>
  <div class="grid">
    {_technical_details(s, show_technical)}
  </div>
</section>

{client_status_section(s)}

{xray_protocols_section(s['client_name'])}

<section class="card">
  <h3>{html.escape(t("dashboard.tools_title"))}</h3>
  <div class="dashboard-tools-grid">
    <a class="btn btn-sm dark" href="/configs.zip">{html.escape(t("dashboard.download_zip"))}</a>
    <a class="btn btn-sm dark" href="/sub-link">{html.escape(t("dashboard.sub_link"))}</a>
  </div>
</section>
</div>
"""


def body_pending():
    return f"""
<h1>{html.escape(t("page.dashboard"))}</h1>
<p class="subtitle">{html.escape(t("dashboard.pending_sub"))}</p>
<div class="notice notice-wait">{html.escape(t("dashboard.pending"))}</div>
<p class="hint">{html.escape(t("dashboard.pending_hint"))}</p>
"""


def body_inactive():
    return f"""
<h1>{html.escape(t('page.dashboard'))}</h1>
<p class="subtitle">{html.escape(t('dashboard.inactive_sub'))}</p>
<div class="notice">{html.escape(t('dashboard.inactive'))}</div>
"""


def body_no_config():
    return f"""
<h1>{html.escape(t('page.dashboard'))}</h1>
<p class="subtitle">{html.escape(t('dashboard.no_config_sub'))}</p>
<div class="notice">{html.escape(t('dashboard.no_config'))}</div>
"""
