import html

from admin_panel.config import VERSION
from admin_panel.core.i18n import lang_toggle_html, t


def locale_version_bar(next_path="/"):
    version = (
        f"{html.escape(t('admin_label'))} · "
        f"{html.escape(t('version'))} {html.escape(VERSION)}"
    )
    return f"""<div class="locale-bar">
  <span class="locale-bar-version">{version}</span>
  <div class="locale-bar-controls">{lang_toggle_html(next_path)}</div>
</div>"""
