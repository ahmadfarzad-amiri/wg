import html

from client_panel.components.locale_bar import locale_version_bar
from client_panel.components.notice import notice
from client_panel.core.i18n import t


def body(msg="", show_config_actions=False, config_count=1):
    toast_variant = "success" if msg and show_config_actions else "info"
    config_actions = ""
    if show_config_actions:
        zip_label = (
            t("settings.download_all_zip")
            if config_count > 1
            else t("settings.download")
        )
        zip_href = "/configs.zip" if config_count > 1 else "/config"
        config_actions = f"""
<section class="card card-spaced config-download-card">
  <h3>{html.escape(t("settings.new_config"))}</h3>
  <p class="hint">{html.escape(t("settings.new_config_hint"))}</p>
  <div class="settings-actions config-actions">
    <a class="btn" href="{zip_href}">{html.escape(zip_label)}</a>
    <button type="button" class="btn dark" data-qr-open>{html.escape(t("settings.show_qr"))}</button>
  </div>
</section>
"""
    return f"""
<h1>{html.escape(t("settings.title"))}</h1>
<p class="subtitle">{html.escape(t("settings.subtitle"))}</p>

{config_actions}

{locale_version_bar("/settings")}

<section class="card">
  <h3>{html.escape(t("settings.change_password"))}</h3>
  <p class="hint">{html.escape(t("settings.change_hint"))}</p>
  {notice(msg, variant=toast_variant)}
  <form method="post" action="/settings/password" class="form-stack">
    <label for="old_password">{html.escape(t("settings.old_password"))}</label>
    <input id="old_password" name="old_password" type="password" autocomplete="current-password" required>
    <label for="new_password">{html.escape(t("settings.new_password"))}</label>
    <input id="new_password" name="new_password" type="password" autocomplete="new-password" required minlength="6">
    <label for="confirm_password">{html.escape(t("settings.confirm_password"))}</label>
    <input id="confirm_password" name="confirm_password" type="password" autocomplete="new-password" required>
    <button type="submit">{html.escape(t("settings.submit"))}</button>
  </form>
</section>

<section class="card card-spaced">
  <h3>{html.escape(t("settings.account"))}</h3>
  <div class="settings-actions">
    <form method="post" action="/logout">
      <button type="submit" class="bad">{html.escape(t("settings.logout"))}</button>
    </form>
  </div>
</section>
"""
