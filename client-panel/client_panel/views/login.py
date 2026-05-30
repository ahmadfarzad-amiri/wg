import html

from client_panel.components.auth_card import auth_card
from client_panel.core.i18n import t


def body(msg=""):
    notice = f'<div class="notice" role="alert">{html.escape(msg)}</div>' if msg else ""
    form = f"""
{notice}
<form method="post" action="/login" class="form-stack">
  <label for="username">{html.escape(t("auth.username"))}</label>
  <input id="username" name="username" autocomplete="username" required>
  <label for="password">{html.escape(t("auth.password"))}</label>
  <input id="password" name="password" type="password" autocomplete="current-password" required>
  <button type="submit" class="btn-block">{html.escape(t("auth.login_btn"))}</button>
</form>
"""
    return auth_card(
        t("auth.welcome"),
        t("auth.login_sub"),
        form,
        "/register",
        t("auth.register_link"),
    )
