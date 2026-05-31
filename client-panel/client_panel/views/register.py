import html

from client_panel.components.auth_card import auth_card
from client_panel.components.notice import notice
from client_panel.core.i18n import t


def body(msg=""):
    hint = t("auth.register_hint")
    form = f"""
{notice(msg)}
<form method="post" action="/register" class="form-stack">
  <label for="reg-username">{html.escape(t("auth.username"))}</label>
  <input id="reg-username" name="username" autocomplete="username" required minlength="3">
  <label for="reg-password">{html.escape(t("auth.password"))}</label>
  <input id="reg-password" name="password" type="password" autocomplete="new-password" required minlength="6">
  <p class="hint">{html.escape(hint)}</p>
  <button type="submit" class="btn-block">{html.escape(t("auth.register_btn"))}</button>
</form>
"""
    return auth_card(
        t("auth.register_title"),
        t("auth.register_sub"),
        form,
        "/login",
        t("auth.login_link"),
    )
