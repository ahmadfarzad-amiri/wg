import html


def action_menu_item(action_url, fields, label, *, enabled=True, danger=False, confirm=None):
    """Render one action-menu form item, or nothing when disabled."""
    if not enabled:
        return ""
    hidden = "".join(
        f'<input type="hidden" name="{html.escape(k)}" value="{html.escape(str(v), quote=True)}">'
        for k, v in fields.items()
    )
    confirm_attr = ""
    if confirm:
        confirm_attr = f' data-confirm="{html.escape(confirm, quote=True)}"'
    danger_cls = " action-menu-item--danger" if danger else ""
    return f"""
<form class="action-menu-form" method="post" action="{html.escape(action_url)}">
  {hidden}
  <button type="submit" class="action-menu-item{danger_cls}"{confirm_attr}>{html.escape(label)}</button>
</form>
"""


def action_menu(action_url, fields_prefix, items, *, aria_label=""):
    """Build a ⋯ menu from (extra_fields, action, label, enabled, danger?, confirm?) tuples."""
    body = ""
    for item in items:
        extra, action, label, enabled = item[:4]
        danger = item[4] if len(item) > 4 else False
        confirm = item[5] if len(item) > 5 else None
        merged = dict(fields_prefix)
        merged.update(extra)
        merged["action"] = action
        body += action_menu_item(action_url, merged, label, enabled=enabled, danger=danger, confirm=confirm)
    if not body.strip():
        return ""
    label = html.escape(aria_label)
    return f"""
<details class="action-menu">
  <summary class="action-menu-trigger" aria-label="{label}">⋯</summary>
  <div class="action-menu-panel">{body}</div>
</details>
"""
