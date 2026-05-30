(function () {
  "use strict";

  var i18n = window.__I18N || {};

  function showCopyMsg(text) {
    var el = document.getElementById("copy-config-msg");
    if (el) {
      el.textContent = text;
    }
  }

  function setButtonLoading(btn, loading) {
    if (!btn) return;
    if (loading) {
      btn.disabled = true;
      btn.dataset.prevText = btn.textContent;
      btn.textContent = i18n.pleaseWait || "…";
    } else if (btn.dataset.prevText) {
      btn.disabled = false;
      btn.textContent = btn.dataset.prevText;
    }
  }

  function copyFromFetch(btn) {
    setButtonLoading(btn, true);
    return fetch("/config-text", { credentials: "same-origin" })
      .then(function (r) {
        if (!r.ok) throw new Error("fetch failed");
        return r.text();
      })
      .then(function (text) {
        return navigator.clipboard.writeText(text);
      })
      .finally(function () {
        setButtonLoading(btn, false);
      });
  }

  document.querySelectorAll("[data-copy-config]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      copyFromFetch(btn)
        .then(function () {
          showCopyMsg(i18n.copyOk || "");
        })
        .catch(function () {
          showCopyMsg(i18n.copyFailRedirect || "");
          window.location.href = "/copy-config";
        });
    });
  });

  var copyBtn = document.getElementById("copy-btn");
  var cfg = document.getElementById("cfg");
  if (copyBtn && cfg) {
    copyBtn.addEventListener("click", function () {
      navigator.clipboard
        .writeText(cfg.value)
        .then(function () {
          var msg = document.getElementById("copy-msg");
          if (msg) msg.textContent = i18n.copyOk || "";
        })
        .catch(function () {
          var msg = document.getElementById("copy-msg");
          if (msg) msg.textContent = i18n.copyFailManual || "";
        });
    });
  }

  var modal = document.getElementById("qr-modal");
  if (!modal) return;

  var modalBody = document.getElementById("qr-modal-body");
  var modalError = document.getElementById("qr-modal-error");
  var lastFocus = null;

  function setModalError(msg) {
    if (!modalError) return;
    if (msg) {
      modalError.textContent = msg;
      modalError.hidden = false;
    } else {
      modalError.textContent = "";
      modalError.hidden = true;
    }
  }

  function closeQrModal() {
    modal.hidden = true;
    modal.setAttribute("aria-hidden", "true");
    document.body.classList.remove("modal-open");
    if (lastFocus && lastFocus.focus) {
      lastFocus.focus();
    }
  }

  function openQrModal() {
    lastFocus = document.activeElement;
    modal.hidden = false;
    modal.setAttribute("aria-hidden", "false");
    document.body.classList.add("modal-open");
    setModalError("");
    if (modalBody) {
      modalBody.innerHTML =
        '<p class="modal-loading">' + (i18n.qrLoading || "") + "</p>";
    }

    fetch("/config-qr.svg", { credentials: "same-origin" })
      .then(function (r) {
        if (!r.ok) {
          return r.text().then(function (t) {
            throw new Error(t || i18n.qrError || "");
          });
        }
        return r.text();
      })
      .then(function (svg) {
        if (modalBody) {
          modalBody.innerHTML = svg;
        }
      })
      .catch(function (err) {
        if (modalBody) {
          modalBody.innerHTML = "";
        }
        setModalError(err.message || i18n.qrErrorFull || "");
      });

    var closeBtn = modal.querySelector(".modal-close");
    if (closeBtn) closeBtn.focus();
  }

  document.querySelectorAll("[data-qr-open]").forEach(function (btn) {
    btn.addEventListener("click", openQrModal);
  });

  document.querySelectorAll("[data-qr-close]").forEach(function (el) {
    el.addEventListener("click", closeQrModal);
  });

  document.addEventListener("keydown", function (e) {
    if (!modal.hidden && e.key === "Escape") {
      closeQrModal();
    }
  });

  if (window.location.search.indexOf("qr=1") !== -1) {
    openQrModal();
  }
})();
