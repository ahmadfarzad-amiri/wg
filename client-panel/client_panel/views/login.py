import html

from client_panel.components.auth_card import auth_card
from client_panel.components.notice import notice
from client_panel.core.i18n import t


def body(msg="", variant="info"):
    form = f"""
{notice(msg, variant=variant or "error")}
<form method="post" action="/login" class="form-stack">
  <div class="field">
    <label class="field-label" for="username">{html.escape(t("auth.username"))}</label>
    <input class="field-input" id="username" name="username" autocomplete="username" required>
  </div>
  <div class="field">
    <label class="field-label" for="password">{html.escape(t("auth.password"))}</label>
    <input class="field-input" id="password" name="password" type="password" autocomplete="current-password" required>
  </div>
  <button type="submit" class="btn btn-block">{html.escape(t("auth.login_btn"))}</button>
</form>
"""
    return auth_card(
        t("auth.welcome"),
        t("auth.login_sub"),
        form,
        "/register",
        t("auth.register_link"),
    )
