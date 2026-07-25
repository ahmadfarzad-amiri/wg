import html

from client_panel.core.i18n import t, tf
from client_panel.core.statuses import ClientState


def client_status_section(s, *, multi=False):
    state_key = s.get("state_key", "unknown")
    mapping = {
        ClientState.ACTIVE: ("ok", "status.active.title", "status.active.desc"),
        ClientState.EXPIRED: ("warn", "status.expired.title", "status.expired.desc"),
        ClientState.OVER_LIMIT: ("warn", "status.over_limit.title", "status.over_limit.desc"),
        ClientState.DISABLED: ("bad", "status.disabled.title", "status.disabled.desc"),
    }
    box_class, title_key, desc_key = mapping.get(
        state_key,
        ("warn", "status.unknown.title", "status.unknown.desc"),
    )
    title = t(title_key)
    desc = t(desc_key)
    needs_support = state_key in ClientState.NEEDS_SUPPORT
    name = s.get("client_name") or ""
    name_q = html.escape(name, quote=True)
    config_href = f"/config?client={name_q}" if name else "/config"
    config_note = (
        f'<p class="hint">{html.escape(tf("status.primary_config", name=name))}</p>'
        if multi and name
        else ""
    )

    support_link = ""
    if needs_support:
        support_link = f"""
<p class="hint status-support-link">
  <a class="btn btn-sm" href="/support">{html.escape(t("status.go_support"))}</a>
</p>
"""

    return f"""
<section class="card install-card connect-first">
  <h3>{html.escape(t("status.install_title"))}</h3>
  <p class="hint">{html.escape(t("status.install_hint"))}</p>
  {config_note}
  <ol class="install-steps">
    <li>{html.escape(t("status.install_step1"))}</li>
    <li>{html.escape(t("status.install_step2"))}</li>
    <li>{html.escape(t("status.install_step3"))}</li>
  </ol>
  <div class="config-actions">
    <a class="btn" href="{config_href}">{html.escape(t("status.download"))}</a>
    <button type="button" class="btn dark" data-qr-open data-qr-client="{name_q}">{html.escape(t("settings.show_qr"))}</button>
    <button type="button" class="btn dark" data-copy-config data-copy-client="{name_q}">{html.escape(t("status.copy"))}</button>
  </div>
  <span class="downloadhint">{html.escape(t("status.download_hint"))}</span>
</section>

<section class="statusbox {box_class}">
  <h3>{html.escape(title)}</h3>
  <p>{html.escape(desc)}</p>
  {support_link}
</section>
"""
