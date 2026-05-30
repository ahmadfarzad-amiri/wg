import html

from admin_panel.components.notice import notice
from admin_panel.config import admin_url
from admin_panel.core.auth import admin_username
from admin_panel.core.i18n import t


def body(msg=""):
    username = admin_username()
    return f"""
<h1>{html.escape(t("settings.title"))}</h1>
<p class="subtitle">{html.escape(t("settings.subtitle"))}</p>

<div class="settings-grid">
  <section class="card">
    <h3>{html.escape(t("settings.change_password"))}</h3>
    {notice(msg, role="alert")}
    <form method="post" action="{admin_url("/settings/password")}" class="form-stack">
      <label>{html.escape(t("settings.admin_username"))}</label>
      <input value="{html.escape(username)}" disabled>
      <label for="old_password">{html.escape(t("settings.old_password"))}</label>
      <input id="old_password" name="old_password" type="password" autocomplete="current-password" required>
      <label for="new_password">{html.escape(t("settings.new_password"))}</label>
      <input id="new_password" name="new_password" type="password" autocomplete="new-password" required minlength="8">
      <label for="confirm_password">{html.escape(t("settings.confirm_password"))}</label>
      <input id="confirm_password" name="confirm_password" type="password" autocomplete="new-password" required>
      <button type="submit">{html.escape(t("settings.submit"))}</button>
    </form>
  </section>

  <section class="card">
    <h3>{html.escape(t("settings.session"))}</h3>
    <p class="hint">{html.escape(t("settings.logout_hint"))}</p>
    <form method="post" action="{admin_url("/logout")}" class="form-stack">
      <button type="submit" class="bad">{html.escape(t("settings.logout_btn"))}</button>
    </form>
  </section>
</div>
"""
