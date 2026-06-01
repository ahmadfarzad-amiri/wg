import html

from client_panel.core.i18n import t


def body(config_text):
    return f"""
<h1>{html.escape(t("page.copy_config"))}</h1>
<p class="subtitle">{html.escape(t("copy.subtitle"))}</p>
<section class="card">
  <h3>{html.escape(t("copy.steps_title"))}</h3>
  <ol class="install-steps">
    <li>{html.escape(t("copy.step1"))}</li>
    <li>{html.escape(t("copy.step2"))}</li>
    <li>{html.escape(t("copy.step3"))}</li>
  </ol>
  <textarea id="cfg" readonly class="config-textarea" aria-label="{html.escape(t("page.copy_config"))}">{html.escape(config_text)}</textarea>
  <div class="copy-toolbar">
    <button type="button" id="copy-btn">{html.escape(t("status.copy"))}</button>
    <a class="btn dark" href="/config">{html.escape(t("btn.download"))}</a>
    <a class="btn dark" href="/">{html.escape(t("btn.back"))}</a>
  </div>
</section>
"""
