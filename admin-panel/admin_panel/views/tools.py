from admin_panel.components.notice import notice
from admin_panel.config import admin_url
from admin_panel.core.i18n import t


def body(msg=""):
    from admin_panel.core.audit import recent_audit
    import html
    import time

    audit_rows = recent_audit(10)
    audit_html = ""
    if audit_rows:
        items = []
        for action, detail, created_at in audit_rows:
            when = time.strftime("%Y-%m-%d %H:%M", time.localtime(created_at))
            items.append(
                f"<li><code>{html.escape(action)}</code> — {html.escape(detail or '')} "
                f"<span class='muted'>({when})</span></li>"
            )
        audit_html = f"""
<section class="card card-spaced">
  <h3>{html.escape(t("tools.audit_recent"))}</h3>
  <ul class="audit-list">{''.join(items)}</ul>
</section>
"""
    return f"""
<h1>{html.escape(t("tools.title"))}</h1>
<p class="subtitle">{html.escape(t("tools.subtitle"))}</p>
{notice(msg, role="alert")}

<section class="card card-spaced">
  <h3>{html.escape(t("tools.infrastructure"))}</h3>
  <p class="hint">{html.escape(t("tools.infrastructure_hint"))}</p>
  <form class="form-stack infra-form" method="post" action="{admin_url("/tool-action")}">
    <input type="hidden" name="action" value="change-entry">
    <h4>{html.escape(t("tools.change_entry"))}</h4>
    <label>{html.escape(t("tools.new_endpoint"))}</label>
    <input name="new_endpoint" class="field-input" placeholder="198.51.100.10:51820" required>
    <label>{html.escape(t("tools.old_ip"))}</label>
    <input name="old_ip" class="field-input" placeholder="216.147.121.53">
    <button type="submit" class="btn" data-confirm="{html.escape(t("tools.change_entry_confirm"), quote=True)}">{html.escape(t("tools.change_entry_btn"))}</button>
  </form>
  <form class="form-stack infra-form" method="post" action="{admin_url("/tool-action")}">
    <input type="hidden" name="action" value="change-exit">
    <h4>{html.escape(t("tools.change_exit"))}</h4>
    <label>{html.escape(t("tools.exit_ip"))}</label>
    <input name="exit_ip" class="field-input" placeholder="203.0.113.50" required>
    <label>{html.escape(t("tools.exit_tunnel_pub"))}</label>
    <input name="exit_tunnel_pub" class="field-input" required>
    <label>{html.escape(t("tools.exit_tunnel_port"))}</label>
    <input name="exit_tunnel_port" class="field-input" value="51821">
    <button type="submit" class="btn dark" data-confirm="{html.escape(t("tools.change_exit_confirm"), quote=True)}">{html.escape(t("tools.change_exit_btn"))}</button>
  </form>
</section>

<section class="card">
  <h3>{html.escape(t("tools.maintenance"))}</h3>
  <div class="actions">
    <form class="inline-form" method="post" action="{admin_url("/tool-action")}">
      <input type="hidden" name="action" value="enforce">
      <button type="submit" data-confirm="{html.escape(t("tools.enforce_confirm"), quote=True)}">{html.escape(t("tools.enforce_btn"))}</button>
    </form>
    <form class="inline-form" method="post" action="{admin_url("/tool-action")}">
      <input type="hidden" name="action" value="restart-panel">
      <button type="submit" class="dark" data-confirm="{html.escape(t("tools.restart_confirm"), quote=True)}">{html.escape(t("tools.restart_btn"))}</button>
    </form>
    <form class="inline-form" method="post" action="{admin_url("/tool-action")}">
      <input type="hidden" name="action" value="import-existing">
      <button type="submit" class="dark" data-confirm="{html.escape(t("tools.import_confirm"), quote=True)}">{html.escape(t("tools.import_btn"))}</button>
    </form>
  </div>
</section>
{audit_html}
"""
