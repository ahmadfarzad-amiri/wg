(function () {
  "use strict";

  var i18n = window.__I18N || {};

  function ensureToastRoot() {
    var root = document.getElementById("toast-root");
    if (!root) {
      root = document.createElement("div");
      root.id = "toast-root";
      root.className = "toast-root";
      root.setAttribute("aria-live", "polite");
    }
    document.body.appendChild(root);
    return root;
  }

  function showToast(message, variant) {
    if (!message) {
      return;
    }
    var textValue = String(message).trim();
    if (textValue.length > 280) {
      textValue = textValue.slice(0, 279).replace(/\s+\S*$/, "") + "…";
    }
    var root = ensureToastRoot();
    var existing = root.querySelectorAll(".toast");
    while (existing.length >= 3) {
      existing[0].remove();
      existing = root.querySelectorAll(".toast");
    }
    var toast = document.createElement("div");
    var kind = variant || "info";
    toast.className = "toast toast--" + kind;
    toast.setAttribute("role", kind === "error" ? "alert" : "status");
    root.setAttribute("aria-live", kind === "error" ? "assertive" : "polite");

    var text = document.createElement("span");
    text.className = "toast-text";
    text.textContent = textValue;

    var close = document.createElement("button");
    close.type = "button";
    close.className = "toast-close";
    close.setAttribute("aria-label", i18n.toastDismiss || "Dismiss");
    close.innerHTML = "&times;";

    var dismiss = function () {
      toast.classList.remove("toast--show");
      toast.classList.add("toast--hide");
      setTimeout(function () {
        toast.remove();
      }, 280);
    };

    close.addEventListener("click", dismiss);
    toast.appendChild(text);
    toast.appendChild(close);
    root.insertBefore(toast, root.firstChild);

    requestAnimationFrame(function () {
      toast.classList.add("toast--show");
    });

    var ttl = kind === "error" ? 8000 : kind === "warn" ? 6000 : 4000;
    setTimeout(dismiss, ttl);
  }

  window.showToast = showToast;

  function initToasts() {
    document.querySelectorAll("template.toast-payload").forEach(function (el) {
      showToast(el.content.textContent.trim(), el.getAttribute("data-variant") || "info");
      el.remove();
    });

    try {
      var params = new URLSearchParams(window.location.search);
      if (params.has("notice")) {
        params.delete("notice");
        params.delete("notice_v");
        var qs = params.toString();
        history.replaceState(
          {},
          "",
          window.location.pathname + (qs ? "?" + qs : "") + window.location.hash
        );
      }
    } catch (e) {
      /* ignore */
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initToasts);
  } else {
    initToasts();
  }

  function setButtonLoading(btn, loading) {
    if (!btn) return;
    if (loading) {
      btn.disabled = true;
      btn.classList.add("is-loading");
      btn.setAttribute("aria-busy", "true");
      btn.dataset.prevText = btn.textContent;
      btn.textContent = i18n.pleaseWait || "…";
    } else if (btn.dataset.prevText) {
      btn.disabled = false;
      btn.classList.remove("is-loading");
      btn.removeAttribute("aria-busy");
      btn.textContent = btn.dataset.prevText;
      delete btn.dataset.prevText;
    }
  }

  document.querySelectorAll("form").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      var submitter = e.submitter;
      if (!submitter || submitter.type !== "submit") {
        submitter = form.querySelector('button[type="submit"], input[type="submit"]');
      }
      if (!submitter || submitter.disabled) {
        return;
      }
      var confirmMsg = submitter.getAttribute("data-confirm");
      if (confirmMsg && !window.confirm(confirmMsg)) {
        e.preventDefault();
        return;
      }
      if (form.getAttribute("data-no-loading") === "1") {
        return;
      }
      setButtonLoading(submitter, true);
    });
  });

  function copyFromFetch(btn) {
    setButtonLoading(btn, true);
    var clientName = btn.getAttribute("data-copy-client") || "";
    var url = "/config-text";
    if (clientName) {
      url += "?client=" + encodeURIComponent(clientName);
    }
    return fetch(url, { credentials: "same-origin" })
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
          showToast(i18n.copyOk || "", "success");
        })
        .catch(function () {
          showToast(i18n.copyFailRedirect || "", "error");
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
          showToast(i18n.copyOk || "", "success");
        })
        .catch(function () {
          showToast(i18n.copyFailManual || "", "error");
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

  function openQrModal(clientName) {
    lastFocus = document.activeElement;
    modal.hidden = false;
    modal.setAttribute("aria-hidden", "false");
    document.body.classList.add("modal-open");
    setModalError("");
    if (modalBody) {
      modalBody.innerHTML =
        '<p class="modal-loading">' + (i18n.qrLoading || "") + "</p>";
    }

    var qrUrl = "/config-qr.svg";
    if (clientName) {
      qrUrl += "?client=" + encodeURIComponent(clientName);
    }

    fetch(qrUrl, { credentials: "same-origin" })
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
        showToast(err.message || i18n.qrError || "QR failed", "error");
      });

    var closeBtn = modal.querySelector(".modal-close");
    if (closeBtn) closeBtn.focus();
  }

  document.querySelectorAll("[data-qr-open]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      openQrModal(btn.getAttribute("data-qr-client") || "");
    });
  });

  document.querySelectorAll("[data-qr-close]").forEach(function (el) {
    el.addEventListener("click", closeQrModal);
  });

  document.addEventListener("keydown", function (e) {
    if (!modal.hidden && e.key === "Escape") {
      closeQrModal();
      return;
    }
    if (!modal.hidden && e.key === "Tab") {
      var focusable = modal.querySelectorAll(
        'button,[href],input,select,textarea,[tabindex]:not([tabindex="-1"])'
      );
      if (!focusable.length) return;
      var first = focusable[0];
      var last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  });

  if (window.location.search.indexOf("qr=1") !== -1) {
    openQrModal();
  }

  // ── copy-target buttons (subscription link page) ────────────────────────
  document.querySelectorAll("[data-copy-target]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var targetId = btn.getAttribute("data-copy-target");
      var input = document.getElementById(targetId);
      if (!input) return;
      navigator.clipboard.writeText(input.value)
        .then(function () { showToast(i18n.copyOk || "Copied", "success"); })
        .catch(function () {
          input.select();
          document.execCommand("copy");
        });
    });
  });

  // ── connection test ──────────────────────────────────────────────────────
  var connTestBtn = document.getElementById("conn-test-btn");
  if (connTestBtn) {
    connTestBtn.addEventListener("click", function () {
      var url = connTestBtn.getAttribute("data-test-url") || "/connection-test";
      var results = document.getElementById("conn-test-results");
      setButtonLoading(connTestBtn, true);
      if (results) { results.hidden = true; results.innerHTML = ""; }

      fetch(url, { credentials: "same-origin" })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (!results) return;
          var labels = {
            wg_interface: (i18n.connTest && i18n.connTest.wg_interface) || "WireGuard",
            exit_ping:    (i18n.connTest && i18n.connTest.exit_ping)    || "Exit server",
            dns:          (i18n.connTest && i18n.connTest.dns)          || "DNS",
          };
          var valueLabels = (i18n.connTest && i18n.connTest.values) || {};
          var html = "";
          Object.keys(data).forEach(function (key) {
            var val = data[key];
            var ok = val === "ok" || val === "up";
            var cls = ok ? "ok" : "bad";
            var display = valueLabels[val] || val;
            html += '<div class="item"><span class="badge ' + cls + '">' +
              (labels[key] || key) + ': ' + display + '</span></div>';
          });
          results.innerHTML = html;
          results.hidden = false;
        })
        .catch(function () {
          showToast(i18n.connTestError || "Test failed", "error");
        })
        .finally(function () {
          setButtonLoading(connTestBtn, false);
        });
    });
  }
})();
