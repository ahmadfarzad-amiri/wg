"""Admin view for Xray protocol management."""
import html

from admin_panel.components.notice import notice
from admin_panel.config import admin_url
from admin_panel.core.i18n import t


def _badge(text, cls):
    return f'<span class="badge {html.escape(cls)}">{html.escape(text)}</span>'


def _status_section(installed, running, secrets):
    rows = []

    installed_badge = _badge(t("xray.installed"), "ok") if installed else _badge(t("xray.not_installed"), "bad")
    rows.append(
        f'<div class="item"><div class="label">{html.escape(t("xray.installed"))}</div>'
        f'<div class="value">{installed_badge}</div></div>'
    )

    if installed:
        running_badge = _badge(t("xray.running"), "ok") if running else _badge(t("xray.stopped"), "bad")
        rows.append(
            f'<div class="item"><div class="label">{html.escape(t("xray.service"))}</div>'
            f'<div class="value">{running_badge}</div></div>'
        )
        server_ip = html.escape(secrets.get("XRAY_SERVER_IP", "—"))
        rows.append(
            f'<div class="item"><div class="label">{html.escape(t("xray.server_ip"))}</div>'
            f'<div class="value">{server_ip}</div></div>'
        )
        sni = html.escape(secrets.get("XRAY_REALITY_SNI", "—"))
        rows.append(
            f'<div class="item"><div class="label">{html.escape(t("xray.reality_sni"))}</div>'
            f'<div class="value">{sni}</div></div>'
        )

    statrow = f'<div class="statrow">{"".join(rows)}</div>'

    not_installed_hint = ""
    if not installed:
        install_cmd = html.escape(
            "sudo WG_XRAY_REALITY_SNI=www.microsoft.com bash /opt/wg/deploy/install-xray.sh"
        )
        not_installed_hint = (
            f'<p class="hint">{html.escape(t("xray.not_installed_hint"))}</p>'
            f'<pre class="code-block"><code>{install_cmd}</code></pre>'
        )

    return f"""
<section class="card">
  <h3>{html.escape(t("xray.status_title"))}</h3>
  {statrow}
  {not_installed_hint}
</section>
"""


def _link_row(link_id, label, link_value):
    esc_id = html.escape(link_id, quote=True)
    esc_val = html.escape(link_value, quote=True)
    return (
        f'<div class="xray-link-row">'
        f'<span class="xray-link-label">{html.escape(label)}</span>'
        f'<input class="field-input xray-link-input" type="text" id="{esc_id}" '
        f'value="{esc_val}" readonly>'
        f'<button type="button" class="btn btn-sm" data-copy-target="{esc_id}">'
        f'{html.escape(t("xray.copy"))}</button>'
        f'</div>'
    )


def _client_list_section(clients):
    if not clients:
        return f"""
<section class="card">
  <h3>{html.escape(t("xray.clients_title"))}</h3>
  <p class="hint">{html.escape(t("xray.clients_hint"))}</p>
  <p class="muted">{html.escape(t("xray.no_clients"))}</p>
</section>
"""

    _PROTO_LABELS = {
        "reality": "protocol_reality",
        "ws": "protocol_ws",
        "ss": "protocol_ss",
    }

    items = []
    for idx, client in enumerate(clients):
        name = client["name"]
        uuid = client["uuid"]
        links = client.get("links", {})

        uuid_short = html.escape(uuid[:8] + "…" if len(uuid) > 8 else uuid)

        link_rows = []
        for key, label_key in _PROTO_LABELS.items():
            if key not in links:
                continue
            link_id = f"xlink-{idx}-{key}"
            link_rows.append(_link_row(link_id, t(f"xray.{label_key}"), links[key]))

        delete_confirm = html.escape(t("xray.delete_confirm"), quote=True)
        delete_form = (
            f'<form class="inline-form" method="post" action="{admin_url("/xray-action")}">'
            f'<input type="hidden" name="action" value="delete-client">'
            f'<input type="hidden" name="name" value="{html.escape(name, quote=True)}">'
            f'<button type="submit" class="btn btn-sm dark" data-confirm="{delete_confirm}">'
            f'{html.escape(t("xray.delete_btn"))}</button>'
            f'</form>'
        )

        items.append(f"""
<article class="card-inset xray-client-card">
  <div class="xray-client-head">
    <strong>{html.escape(name)}</strong>
    <span class="muted">{uuid_short}</span>
    {delete_form}
  </div>
  <div class="xray-client-links">
    {"".join(link_rows)}
  </div>
</article>""")

    return f"""
<section class="card">
  <h3>{html.escape(t("xray.clients_title"))}</h3>
  <p class="hint">{html.escape(t("xray.clients_hint"))}</p>
  <div class="xray-client-list">
    {"".join(items)}
  </div>
</section>
"""


def _add_client_section():
    return f"""
<section class="card">
  <h3>{html.escape(t("xray.add_title"))}</h3>
  <p class="hint">{html.escape(t("xray.add_hint"))}</p>
  <form class="form-stack" method="post" action="{admin_url("/xray-action")}">
    <input type="hidden" name="action" value="add-client">
    <label>{html.escape(t("xray.client_name_label"))}</label>
    <input name="name" class="field-input"
           placeholder="{html.escape(t("xray.client_name_hint"), quote=True)}"
           required autocomplete="off">
    <button type="submit" class="btn">{html.escape(t("xray.add_btn"))}</button>
  </form>
</section>
"""


def body(msg="", variant="info"):
    from admin_panel.core import xray as xcore

    installed = xcore.is_installed()
    running = xcore.is_running() if installed else False
    secrets = xcore.load_secrets() if installed else {}
    clients = xcore.list_clients() if installed else []

    status_html = _status_section(installed, running, secrets)
    clients_html = _client_list_section(clients) if installed else ""
    add_html = _add_client_section() if installed else ""

    return f"""
<h1>{html.escape(t("xray.title"))}</h1>
<p class="subtitle">{html.escape(t("xray.subtitle"))}</p>
<p class="hint page-glossary">{html.escape(t("xray.glossary"))}</p>
{notice(msg, variant=variant)}

<div class="page-stack">
{status_html}
{clients_html}
{add_html}
</div>
"""
