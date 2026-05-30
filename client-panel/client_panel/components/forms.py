import html

from client_panel.core.i18n import t
from client_panel.core.wireguard import can_request_status


def request_controls(s, include_download=True):
    renew_ok, renew_reason = can_request_status(s, "renew")
    enable_ok, enable_reason = can_request_status(s, "enable")

    renew_disabled = "" if renew_ok else "disabled"
    enable_disabled = "" if enable_ok else "disabled"
    renew_title = "" if renew_ok else f'title="{html.escape(renew_reason)}"'
    enable_title = "" if enable_ok else f'title="{html.escape(enable_reason)}"'

    download = (
        f'<a class="btn" href="/config">{html.escape(t("forms.download_file"))}</a>'
        if include_download
        else ""
    )

    return f"""
<div class="actions actions-center">
  <form method="post" action="/request">
    <input type="hidden" name="action" value="renew">
    <button type="submit" {renew_disabled} {renew_title}>{html.escape(t("status.request_renew"))}</button>
  </form>
  <form method="post" action="/request">
    <input type="hidden" name="action" value="enable">
    <button type="submit" class="dark" {enable_disabled} {enable_title}>{html.escape(t("status.request_enable"))}</button>
  </form>
  {download}
</div>
"""
