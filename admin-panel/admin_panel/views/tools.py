from admin_panel.components.notice import notice
from admin_panel.config import admin_url
from admin_panel.core.i18n import t


def _field_value(state, key):
    import html

    return html.escape(state.get(key) or "", quote=True)


def _infra_current_summary(state):
    import html

    parts = []
    if state.get("entry_endpoint"):
        parts.append(
            f"{html.escape(t('tools.current_entry'))}: "
            f"<code>{html.escape(state['entry_endpoint'])}</code>"
        )
    if state.get("exit_ip"):
        exit_ep = f"{state['exit_ip']}:{state.get('exit_tunnel_port') or '51821'}"
        parts.append(
            f"{html.escape(t('tools.current_exit'))}: <code>{html.escape(exit_ep)}</code>"
        )
    if not parts:
        return ""
    return (
        f'<p class="hint infra-current-summary">{html.escape(t("tools.current_values"))}: '
        f'{" · ".join(parts)}</p>'
    )


def body(msg=""):
    from admin_panel.core.audit import recent_audit
    from admin_panel.core.infrastructure import get_infrastructure_state

    import html
    import time

    infra = get_infrastructure_state()
    infra_summary = _infra_current_summary(infra)

    audit_rows = recent_audit(20)
    audit_html = ""
    if audit_rows:
        items = []
        for row in audit_rows:
            # Support both old (3-col) and new (5-col) schema rows gracefully
            if len(row) == 5:
                actor, ip, action, detail, created_at = row
            else:
                actor, ip = "", ""
                action, detail, created_at = row[0], row[1], row[2]
            when = time.strftime("%Y-%m-%d %H:%M", time.localtime(created_at))
            actor_badge = (
                f' <span class="audit-actor">{html.escape(actor)}</span>'
                if actor else ""
            )
            ip_badge = (
                f' <span class="audit-ip muted">{html.escape(ip)}</span>'
                if ip else ""
            )
            items.append(
                f"<li><code>{html.escape(action)}</code> — {html.escape(detail or '')}"
                f"{actor_badge}{ip_badge} "
                f"<span class='muted'>({when})</span></li>"
            )
        audit_html = f"""
<section class="card">
  <h3>{html.escape(t("tools.audit_recent"))}</h3>
  <ul class="audit-list">{''.join(items)}</ul>
</section>
"""
    return f"""
<h1>{html.escape(t("tools.title"))}</h1>
<p class="subtitle">{html.escape(t("tools.subtitle"))}</p>
{notice(msg, role="alert")}

<div class="page-stack">
<section class="card">
  <h3>{html.escape(t("tools.infrastructure"))}</h3>
  <p class="hint">{html.escape(t("tools.infrastructure_hint"))}</p>
  {infra_summary}
  <form class="form-stack infra-form" method="post" action="{admin_url("/tool-action")}">
    <input type="hidden" name="action" value="change-entry">
    <h4>{html.escape(t("tools.change_entry"))}</h4>
    <label>{html.escape(t("tools.new_endpoint"))}</label>
    <input name="new_endpoint" class="field-input" value="{_field_value(infra, "entry_endpoint")}" placeholder="198.51.100.10:51820" required>
    <label>{html.escape(t("tools.old_ip"))}</label>
    <input name="old_ip" class="field-input" value="{_field_value(infra, "entry_old_ip")}" placeholder="216.147.121.53">
    <button type="submit" class="btn" data-confirm="{html.escape(t("tools.change_entry_confirm"), quote=True)}">{html.escape(t("tools.change_entry_btn"))}</button>
  </form>
  <form class="form-stack infra-form" method="post" action="{admin_url("/tool-action")}">
    <input type="hidden" name="action" value="change-exit">
    <h4>{html.escape(t("tools.change_exit"))}</h4>
    <label>{html.escape(t("tools.exit_ip"))}</label>
    <input name="exit_ip" class="field-input" value="{_field_value(infra, "exit_ip")}" placeholder="203.0.113.50" required>
    <label>{html.escape(t("tools.exit_tunnel_pub"))}</label>
    <input name="exit_tunnel_pub" class="field-input" value="{_field_value(infra, "exit_tunnel_pub")}" required>
    <label>{html.escape(t("tools.exit_tunnel_port"))}</label>
    <input name="exit_tunnel_port" class="field-input" value="{_field_value(infra, "exit_tunnel_port")}">
    <button type="submit" class="btn dark" data-confirm="{html.escape(t("tools.change_exit_confirm"), quote=True)}">{html.escape(t("tools.change_exit_btn"))}</button>
  </form>
</section>

<section class="card">
  <h3>{html.escape(t("tools.maintenance"))}</h3>
  <p class="hint">{html.escape(t("tools.maintenance_hint"))}</p>
  <div class="tools-action-grid">
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
</div>
"""
