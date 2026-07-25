import html

from client_panel.components.notice import notice
from client_panel.core.i18n import t


def _setup_guide():
    """Render a per-platform WireGuard setup guide card."""
    platforms = [
        ("iOS", t("setup.ios_apps"),   t("setup.ios_steps")),
        ("Android", t("setup.android_apps"), t("setup.android_steps")),
        ("Windows", t("setup.windows_apps"), t("setup.windows_steps")),
        ("macOS",   t("setup.macos_apps"),   t("setup.macos_steps")),
        ("Linux",   t("setup.linux_apps"),   t("setup.linux_steps")),
    ]
    tabs = ""
    panels = ""
    for idx, (name, apps, steps) in enumerate(platforms):
        checked = " checked" if idx == 0 else ""
        tab_id = f"platform-{name.lower()}"
        tabs += (
            f'<input type="radio" id="{tab_id}" name="platform-tabs" class="platform-radio"{checked}>'
            f'<label class="platform-tab" for="{tab_id}">{html.escape(name)}</label>'
        )
        panels += f"""
<div class="platform-panel" id="panel-{html.escape(name.lower())}">
  <p class="hint">{html.escape(apps)}</p>
  <ol class="setup-steps">{
    "".join(f"<li>{html.escape(s.strip())}</li>" for s in steps.split("|") if s.strip())
  }</ol>
</div>
"""
    return f"""
<section class="card setup-guide-card">
  <h3>{html.escape(t("setup.title"))}</h3>
  <div class="platform-tabs">
    {tabs}
    <div class="platform-panels">{panels}</div>
  </div>
</section>
"""


def _vpn_config_card(config_count=1):
    zip_label = (
        t("settings.download_all_zip") if config_count > 1 else t("settings.download")
    )
    zip_href = "/configs.zip" if config_count > 1 else "/config"
    return f"""
<section class="card config-download-card">
  <h3>{html.escape(t("settings.vpn_config"))}</h3>
  <p class="hint">{html.escape(t("settings.vpn_config_hint"))}</p>
  <div class="settings-actions config-actions">
    <a class="btn" href="{zip_href}">{html.escape(zip_label)}</a>
    <button type="button" class="btn dark" data-qr-open>{html.escape(t("settings.show_qr"))}</button>
  </div>
</section>
"""


def body(msg="", show_config_actions=False, config_count=1, has_vpn_config=False, variant="info"):
    toast_variant = variant or ("warn" if msg and show_config_actions else "info")
    config_actions = ""
    if show_config_actions:
        config_actions = f"""
<section class="card config-download-card">
  <h3>{html.escape(t("settings.new_config"))}</h3>
  <p class="hint">{html.escape(t("settings.new_config_hint"))}</p>
  <div class="settings-actions config-actions btn-pair">
    <a class="btn" href="{'/configs.zip' if config_count > 1 else '/config'}">{html.escape(t("settings.download_all_zip") if config_count > 1 else t("settings.download"))}</a>
    <button type="button" class="btn dark" data-qr-open>{html.escape(t("settings.show_qr"))}</button>
  </div>
</section>
"""
    elif has_vpn_config:
        config_actions = _vpn_config_card(config_count)

    return f"""
<h1>{html.escape(t("settings.title"))}</h1>
<p class="subtitle">{html.escape(t("settings.subtitle"))}</p>

<div class="page-stack">
{config_actions}

{_setup_guide()}

<div class="settings-grid">
<section class="card">
  <h3>{html.escape(t("settings.change_password"))}</h3>
  <p class="hint">{html.escape(t("settings.change_hint"))}</p>
  {notice(msg, variant=toast_variant)}
  <form method="post" action="/settings/password" class="form-stack">
    <div class="field">
      <label class="field-label" for="old_password">{html.escape(t("settings.old_password"))}</label>
      <input class="field-input" id="old_password" name="old_password" type="password" autocomplete="current-password" required>
    </div>
    <div class="field">
      <label class="field-label" for="new_password">{html.escape(t("settings.new_password"))}</label>
      <input class="field-input" id="new_password" name="new_password" type="password" autocomplete="new-password" required minlength="6">
    </div>
    <div class="field">
      <label class="field-label" for="confirm_password">{html.escape(t("settings.confirm_password"))}</label>
      <input class="field-input" id="confirm_password" name="confirm_password" type="password" autocomplete="new-password" required>
    </div>
    <p class="field-hint">{html.escape(t("settings.submit_hint"))}</p>
    <button type="submit" class="btn btn-block">{html.escape(t("settings.submit"))}</button>
  </form>
</section>

<section class="card">
  <h3>{html.escape(t("settings.account"))}</h3>
  <p class="hint">{html.escape(t("settings.logout_hint"))}</p>
  <form method="post" action="/logout" class="form-stack">
    <button type="submit" class="btn bad btn-block">{html.escape(t("settings.logout"))}</button>
  </form>
</section>
</div>
</div>
"""
