import html

from client_panel.core.i18n import t


def body(msg="", show_config_actions=False):
    notice = f'<div class="notice" role="alert">{html.escape(msg)}</div>' if msg else ""
    config_actions = ""
    if show_config_actions:
        config_actions = f"""
<section class="card card-spaced">
  <h3>{html.escape(t("settings.new_config"))}</h3>
  <p class="hint">{html.escape(t("settings.new_config_hint"))}</p>
  <div class="settings-actions">
    <a class="btn" href="/config">{html.escape(t("settings.download"))}</a>
    <button type="button" class="btn dark" data-qr-open>{html.escape(t("settings.show_qr"))}</button>
  </div>
</section>
"""
    return f"""
<h1>{html.escape(t("settings.title"))}</h1>
<p class="subtitle">{html.escape(t("settings.subtitle"))}</p>

<section class="card">
  <h3>{html.escape(t("settings.change_password"))}</h3>
  <p class="hint">{html.escape(t("settings.change_hint"))}</p>
  {notice}
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

{config_actions}

<section class="card card-spaced">
  <h3>{html.escape(t("settings.account"))}</h3>
  <div class="settings-actions">
    <form method="post" action="/logout">
      <button type="submit" class="bad">{html.escape(t("settings.logout"))}</button>
    </form>
  </div>
</section>
"""
