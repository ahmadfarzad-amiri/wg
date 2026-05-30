def qr_modal_html():
    return """
<div id="qr-modal" class="modal" hidden aria-hidden="true">
  <div class="modal-backdrop" data-qr-close tabindex="-1"></div>
  <div class="modal-dialog" role="dialog" aria-modal="true" aria-labelledby="qr-modal-title">
    <button type="button" class="modal-close" data-qr-close aria-label="بستن">&times;</button>
    <h2 id="qr-modal-title">QR کانفیگ</h2>
    <p class="modal-subtitle">این کد را با اپ WireGuard اسکن کنید.</p>
    <div class="qrbox" id="qr-modal-body">
      <p class="modal-loading">در حال ساخت QR…</p>
    </div>
    <p id="qr-modal-error" class="modal-error" hidden></p>
  </div>
</div>
"""
