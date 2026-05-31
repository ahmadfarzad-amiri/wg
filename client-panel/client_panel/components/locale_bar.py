import html

from client_panel.config import VERSION
from client_panel.core.i18n import lang_toggle_html, t


def locale_version_bar(next_path="/"):
    version = f"{html.escape(t('version'))} {html.escape(VERSION)}"
    return f"""<div class="locale-bar">
  <span class="locale-bar-version">{version}</span>
  {lang_toggle_html(next_path)}
</div>"""
