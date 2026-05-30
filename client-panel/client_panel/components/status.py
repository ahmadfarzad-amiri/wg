import html

from client_panel.core.i18n import t


def client_status_section(s):
    state_key = s.get("state_key", "unknown")
    mapping = {
        "active": ("ok", "status.active.title", "status.active.desc", False, False),
        "expired": ("warn", "status.expired.title", "status.expired.desc", True, False),
        "over_limit": ("warn", "status.over_limit.title", "status.over_limit.desc", True, False),
        "disabled": ("bad", "status.disabled.title", "status.disabled.desc", False, True),
    }
    box_class, title_key, desc_key, renew_enabled, enable_enabled = mapping.get(
        state_key,
        ("warn", "status.unknown.title", "status.unknown.desc", False, False),
    )
    title = t(title_key)
    desc = t(desc_key)

    renew_disabled = "" if renew_enabled else "disabled"
    enable_disabled = "" if enable_enabled else "disabled"

    return f"""
<section class="statusbox {box_class}">
  <h3>{html.escape(title)}</h3>
  <p>{html.escape(desc)}</p>
  <div class="actions actions-center">
    <form method="post" action="/request">
      <input type="hidden" name="action" value="renew">
      <button type="submit" {renew_disabled}>{html.escape(t("status.request_renew"))}</button>
    </form>
    <form method="post" action="/request">
      <input type="hidden" name="action" value="enable">
      <button type="submit" class="dark" {enable_disabled}>{html.escape(t("status.request_enable"))}</button>
    </form>
  </div>
</section>

<div class="downloadbox">
  <div class="config-actions">
    <a class="btn" href="/config">{html.escape(t("status.download"))}</a>
    <button type="button" class="btn dark" data-qr-open>{html.escape(t("settings.show_qr"))}</button>
    <button type="button" class="btn dark" data-copy-config>{html.escape(t("status.copy"))}</button>
  </div>
  <span id="copy-config-msg" class="copymsg" role="status"></span>
  <span class="downloadhint">{html.escape(t("status.download_hint"))}</span>
</div>
"""
