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
            f"<code class='ltr-value'>{html.escape(state['entry_endpoint'])}</code>"
        )
    if state.get("exit_ip"):
        exit_ep = f"{state['exit_ip']}:{state.get('exit_tunnel_port') or '51821'}"
        parts.append(
            f"{html.escape(t('tools.current_exit'))}: "
            f"<code class='ltr-value'>{html.escape(exit_ep)}</code>"
        )
    if not parts:
        return ""
    return (
        f'<p class="hint infra-current-summary">{html.escape(t("tools.current_values"))}: '
        f'{" · ".join(parts)}</p>'
    )


def body(msg="", variant="info"):
    from admin_panel.core.audit import recent_audit
    from admin_panel.core.infrastructure import get_infrastructure_state

    import html
    import time

    infra = get_infrastructure_state()
    infra_summary = _infra_current_summary(infra)

    audit_rows = recent_audit(50)
    if audit_rows:
        items = []
        for row in audit_rows:
            if len(row) == 5:
                actor, ip, action, detail, created_at = row
            else:
                actor, ip = "", ""
                action, detail, created_at = row[0], row[1], row[2]
            when = time.strftime("%Y-%m-%d %H:%M", time.localtime(created_at))
            actor_badge = (
                f' <span class="audit-actor">{html.escape(actor)}</span>' if actor else ""
            )
            ip_badge = (
                f' <span class="audit-ip muted">{html.escape(ip)}</span>' if ip else ""
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
    else:
        audit_html = f"""
<section class="card">
  <h3>{html.escape(t("tools.audit_recent"))}</h3>
  <p class="hint">{html.escape(t("tools.audit_empty"))}</p>
</section>
"""

    return f"""
<h1>{html.escape(t("tools.title"))}</h1>
<p class="subtitle">{html.escape(t("tools.subtitle"))}</p>
{notice(msg, variant=variant)}

<div class="page-stack">
<section class="card">
  <h3>{html.escape(t("tools.infrastructure"))}</h3>
  <p class="hint">{html.escape(t("tools.infrastructure_hint"))}</p>
  {infra_summary}
  <form class="form-stack infra-form" method="post" action="{admin_url("/tool-action")}">
    <input type="hidden" name="action" value="change-entry">
    <h4>{html.escape(t("tools.change_entry"))}</h4>
    <div class="field">
      <label class="field-label" for="new_endpoint">{html.escape(t("tools.new_endpoint"))}</label>
      <input id="new_endpoint" name="new_endpoint" class="field-input ltr-value" value="{_field_value(infra, "entry_endpoint")}" placeholder="198.51.100.10:51820" required>
    </div>
    <div class="field">
      <label class="field-label" for="old_ip">{html.escape(t("tools.old_ip"))}</label>
      <input id="old_ip" name="old_ip" class="field-input ltr-value" value="{_field_value(infra, "entry_old_ip")}" placeholder="198.51.100.20">
    </div>
    <button type="submit" class="btn" data-confirm="{html.escape(t("tools.change_entry_confirm"), quote=True)}">{html.escape(t("tools.change_entry_btn"))}</button>
  </form>
  <form class="form-stack infra-form" method="post" action="{admin_url("/tool-action")}">
    <input type="hidden" name="action" value="change-exit">
    <h4>{html.escape(t("tools.change_exit"))}</h4>
    <div class="field">
      <label class="field-label" for="exit_ip">{html.escape(t("tools.exit_ip"))}</label>
      <input id="exit_ip" name="exit_ip" class="field-input ltr-value" value="{_field_value(infra, "exit_ip")}" placeholder="203.0.113.50" required>
    </div>
    <div class="field">
      <label class="field-label" for="exit_tunnel_pub">{html.escape(t("tools.exit_tunnel_pub"))}</label>
      <input id="exit_tunnel_pub" name="exit_tunnel_pub" class="field-input ltr-value" value="{_field_value(infra, "exit_tunnel_pub")}" required>
    </div>
    <div class="field">
      <label class="field-label" for="exit_tunnel_port">{html.escape(t("tools.exit_tunnel_port"))}</label>
      <input id="exit_tunnel_port" name="exit_tunnel_port" class="field-input ltr-value" value="{_field_value(infra, "exit_tunnel_port")}">
    </div>
    <button type="submit" class="btn dark" data-confirm="{html.escape(t("tools.change_exit_confirm"), quote=True)}">{html.escape(t("tools.change_exit_btn"))}</button>
  </form>
</section>

<section class="card">
  <h3>{html.escape(t("tools.maintenance"))}</h3>
  <p class="hint">{html.escape(t("tools.maintenance_hint"))}</p>
  <div class="tools-action-grid actions">
    <form class="inline-form" method="post" action="{admin_url("/tool-action")}">
      <input type="hidden" name="action" value="enforce">
      <button type="submit" class="btn" data-confirm="{html.escape(t("tools.enforce_confirm"), quote=True)}">{html.escape(t("tools.enforce_btn"))}</button>
    </form>
    <form class="inline-form" method="post" action="{admin_url("/tool-action")}">
      <input type="hidden" name="action" value="restart-panel">
      <button type="submit" class="btn dark" data-confirm="{html.escape(t("tools.restart_confirm"), quote=True)}">{html.escape(t("tools.restart_btn"))}</button>
    </form>
    <form class="inline-form" method="post" action="{admin_url("/tool-action")}">
      <input type="hidden" name="action" value="import-existing">
      <button type="submit" class="btn dark" data-confirm="{html.escape(t("tools.import_confirm"), quote=True)}">{html.escape(t("tools.import_btn"))}</button>
    </form>
  </div>
</section>
{audit_html}
</div>
"""
