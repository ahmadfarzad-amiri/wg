import html

from client_panel.core.i18n import t


def qr_modal_html():
    return f"""
<div id="qr-modal" class="modal" hidden aria-hidden="true">
  <div class="modal-backdrop" data-qr-close tabindex="-1"></div>
  <div class="modal-dialog" role="dialog" aria-modal="true" aria-labelledby="qr-modal-title">
    <button type="button" class="modal-close" data-qr-close aria-label="{html.escape(t("modal.close"))}">&times;</button>
    <h2 id="qr-modal-title">{html.escape(t("modal.qr_title"))}</h2>
    <p class="modal-subtitle">{html.escape(t("modal.qr_subtitle"))}</p>
    <div class="qrbox" id="qr-modal-body">
      <p class="modal-loading">{html.escape(t("modal.qr_loading"))}</p>
    </div>
    <p id="qr-modal-error" class="modal-error" hidden></p>
  </div>
</div>
"""
