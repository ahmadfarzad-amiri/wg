import html

from client_panel.core.i18n import t
from client_panel.core.wireguard import can_request_status


def request_controls(s, include_download=True):
    renew_ok, renew_reason = can_request_status(s, "renew")
    enable_ok, enable_reason = can_request_status(s, "enable")

    renew_disabled = "" if renew_ok else "disabled"
    enable_disabled = "" if enable_ok else "disabled"
    renew_hint = (
        ""
        if renew_ok
        else f'<p class="field-hint field-hint--warn">{html.escape(renew_reason)}</p>'
    )
    enable_hint = (
        ""
        if enable_ok
        else f'<p class="field-hint field-hint--warn">{html.escape(enable_reason)}</p>'
    )

    download = (
        f'<a class="btn" href="/config">{html.escape(t("forms.download_file"))}</a>'
        if include_download
        else ""
    )

    return f"""
<div class="actions actions-center support-request-actions">
  <form method="post" action="/request" class="support-action-form">
    <input type="hidden" name="action" value="renew">
    <button type="submit" class="btn" {renew_disabled}>{html.escape(t("status.request_renew"))}</button>
    {renew_hint}
  </form>
  <form method="post" action="/request" class="support-action-form">
    <input type="hidden" name="action" value="enable">
    <button type="submit" class="btn dark" {enable_disabled}>{html.escape(t("status.request_enable"))}</button>
    {enable_hint}
  </form>
  {download}
</div>
"""
