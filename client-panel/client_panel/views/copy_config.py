import html

from client_panel.core.i18n import t


def body(config_text):
    return f"""
<h1>{html.escape(t("page.copy_config"))}</h1>
<p class="subtitle">{html.escape(t("copy.subtitle"))}</p>
<section class="card">
<textarea id="cfg" readonly class="config-textarea">{html.escape(config_text)}</textarea>
<div class="actions actions-center">
  <button type="button" id="copy-btn">{html.escape(t("status.copy"))}</button>
  <a class="btn dark" href="/config">{html.escape(t("btn.download"))}</a>
  <a class="btn dark" href="/">{html.escape(t("btn.back"))}</a>
</div>
</section>
"""
