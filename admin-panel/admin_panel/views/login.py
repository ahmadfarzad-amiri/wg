import html

from admin_panel.components.auth_card import auth_card
from admin_panel.components.notice import notice
from admin_panel.config import admin_url
from admin_panel.core.i18n import t


def body(msg=""):
    form = f"""
{notice(msg, role="alert")}
<form method="post" action="{admin_url("/login")}" class="form-stack">
  <label for="username">{html.escape(t("auth.username"))}</label>
  <input id="username" name="username" autocomplete="username" required>
  <label for="password">{html.escape(t("auth.password"))}</label>
  <input id="password" name="password" type="password" autocomplete="current-password" required>
  <button type="submit" class="btn-block">{html.escape(t("auth.login_btn"))}</button>
</form>
"""
    return auth_card(
        t("auth.login_title"),
        t("auth.login_sub"),
        form,
    )
