(function () {
  "use strict";

  var i18n = window.__I18N || {};
  var listLocale = i18n.locale || document.documentElement.lang || "fa";

  function formatListMeta(visible, total) {
    var template = i18n.listMeta || "{visible} of {total}";
    return template.replace("{visible}", visible).replace("{total}", total);
  }

  function normalizeSearch(value) {
    return (value || "")
      .trim()
      .toLowerCase()
      .replace(/\u200c/g, "")
      .replace(/\s+/g, " ");
  }

  function setItemVisible(item, visible) {
    if (!item) {
      return;
    }
    item.hidden = !visible;
    item.classList.toggle("is-list-hidden", !visible);
  }

  function itemMatchesSearch(item, query) {
    if (!query) {
      return true;
    }
    var hay = normalizeSearch(item.getAttribute("data-search") || "");
    if (!hay) {
      hay = normalizeSearch(item.textContent || "");
    }
    return hay.indexOf(query) !== -1;
  }

  function itemMatchesStatus(item, statusFilter) {
    if (!statusFilter) {
      return true;
    }
    if (statusFilter === "unassigned") {
      return (item.getAttribute("data-assigned") || "0") === "0";
    }
    if (statusFilter === "fresh") {
      return (item.getAttribute("data-fresh") || "0") === "1";
    }
    if (statusFilter === "idle") {
      return (item.getAttribute("data-idle") || "0") === "1";
    }
    return (item.getAttribute("data-status") || "") === statusFilter;
  }

  function parseSort(sortValue) {
    var parts = (sortValue || "default").split("-");
    if (parts.length < 2) {
      return { field: "default", dir: "asc" };
    }
    return {
      field: parts.slice(0, -1).join("-"),
      dir: parts[parts.length - 1],
    };
  }

  function sortValue(item, field) {
    if (field === "default") {
      return "";
    }
    if (field === "id") {
      var idNum = parseInt(item.getAttribute("data-sort-id") || "0", 10);
      return isNaN(idNum) ? 0 : idNum;
    }
    if (field === "created") {
      var createdNum = parseInt(item.getAttribute("data-sort-created") || "0", 10);
      return isNaN(createdNum) ? 0 : createdNum;
    }
    if (field === "ip") {
      return item.getAttribute("data-sort-ip") || "";
    }
    if (field === "client") {
      return item.getAttribute("data-sort-client") || "";
    }
    if (field === "status") {
      return item.getAttribute("data-status") || "";
    }
    if (field === "action") {
      return item.getAttribute("data-sort-action") || "";
    }
    if (field === "last" || field === "rx" || field === "tx" || field === "duration") {
      var n = parseInt(item.getAttribute("data-sort-" + field) || "0", 10);
      return isNaN(n) ? 0 : n;
    }
    return item.getAttribute("data-sort-name") || "";
  }

  function compareItems(a, b, sortValueStr) {
    var sort = parseSort(sortValueStr);
    if (sort.field === "default") {
      return 0;
    }

    var av = sortValue(a, sort.field);
    var bv = sortValue(b, sort.field);
    var cmp;

    if (typeof av === "number" && typeof bv === "number") {
      cmp = av - bv;
    } else {
      cmp = String(av).localeCompare(String(bv), listLocale, { numeric: true, sensitivity: "base" });
    }

    return sort.dir === "desc" ? -cmp : cmp;
  }

  function reorderItems(container, selector, sortValueStr) {
    if (!container) {
      return;
    }
    var items = Array.prototype.slice.call(container.querySelectorAll(selector));
    if (!items.length) {
      return;
    }
    items.sort(function (a, b) {
      return compareItems(a, b, sortValueStr);
    });
    items.forEach(function (item) {
      container.appendChild(item);
    });
  }

  function reorderClientDesktop(tbody, sortValueStr) {
    if (!tbody) {
      return;
    }
    var detailsRows = Array.prototype.slice.call(
      tbody.querySelectorAll("tr.client-row-details[data-list-primary]")
    );
    detailsRows.sort(function (a, b) {
      return compareItems(a, b, sortValueStr);
    });
    detailsRows.forEach(function (details) {
      var actions = details.nextElementSibling;
      tbody.appendChild(details);
      if (actions && actions.classList.contains("client-row-actions")) {
        tbody.appendChild(actions);
      }
    });
  }

  function applyList(root) {
    var searchInput = root.querySelector("[data-list-search]");
    var filterSelect = root.querySelector("[data-list-filter]");
    var sortSelect = root.querySelector("[data-list-sort]");
    var listHost = root.querySelector("[data-list-items]");
    var emptyEl = root.querySelector("[data-list-search-empty]");
    var metaEl = root.querySelector("[data-list-search-meta]");
    var listHead =
      root.querySelector(".client-list-head") ||
      root.querySelector(".user-list-head") ||
      root.querySelector(".request-list-head") ||
      root.querySelector(".active-list-head");

    if (!listHost) {
      return;
    }

    var q = normalizeSearch(searchInput ? searchInput.value : "");
    var statusFilter = filterSelect ? filterSelect.value : "";
    var sortValueStr = sortSelect ? sortSelect.value : "default";
    var kind = listHost.getAttribute("data-list-kind") || "default";

    if (kind === "clients") {
      reorderItems(listHost.querySelector(".client-list-body"), "[data-list-primary]", sortValueStr);
    } else if (kind === "users") {
      reorderItems(listHost.querySelector("[data-list-body]"), "[data-list-primary]", sortValueStr);
    } else if (kind === "requests") {
      reorderItems(listHost.querySelector(".request-list-body"), "[data-list-primary]", sortValueStr);
      reorderItems(listHost.querySelector(".mobile-cards"), "[data-list-primary]", sortValueStr);
    } else if (kind === "active") {
      reorderItems(listHost.querySelector(".active-list-body"), "[data-list-primary]", sortValueStr);
      reorderItems(listHost.querySelector(".mobile-cards"), "[data-list-primary]", sortValueStr);
    }

    var primaryItems = listHost.querySelectorAll("[data-list-primary]");
    var visible = 0;
    var total = primaryItems.length;
    var hasActiveFilter = !!q || !!statusFilter;

    primaryItems.forEach(function (item) {
      var match = itemMatchesSearch(item, q) && itemMatchesStatus(item, statusFilter);
      setItemVisible(item, match);

      if (match) {
        visible += 1;
      }
    });

    if (listHead) {
      listHead.hidden = hasActiveFilter && visible === 0 && total > 0;
    }

    if (emptyEl) {
      emptyEl.hidden = !hasActiveFilter || visible > 0 || total === 0;
    }

    if (metaEl) {
      if (hasActiveFilter && total > 0) {
        metaEl.hidden = false;
        metaEl.textContent = formatListMeta(visible, total);
      } else {
        metaEl.hidden = true;
        metaEl.textContent = "";
      }
    }
  }

  document.addEventListener("click", function (e) {
    document.querySelectorAll(".action-menu[open]").forEach(function (menu) {
      if (!menu.contains(e.target)) {
        menu.removeAttribute("open");
      }
    });
  });

  document.querySelectorAll(".action-menu").forEach(function (menu) {
    menu.addEventListener("toggle", function () {
      if (!menu.open) {
        return;
      }
      document.querySelectorAll(".action-menu[open]").forEach(function (other) {
        if (other !== menu) {
          other.removeAttribute("open");
        }
      });
    });
  });

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

  document.querySelectorAll(".list-filterable").forEach(function (root) {
    var searchInput = root.querySelector("[data-list-search]");
    var filterSelect = root.querySelector("[data-list-filter]");
    var sortSelect = root.querySelector("[data-list-sort]");

    function refresh() {
      applyList(root);
    }

    if (searchInput) {
      searchInput.addEventListener("input", refresh);
      searchInput.addEventListener("search", refresh);
    }
    if (filterSelect) {
      filterSelect.addEventListener("change", refresh);
    }
    if (sortSelect) {
      sortSelect.addEventListener("change", refresh);
    }
    refresh();
  });

  document.addEventListener("click", function (e) {
    var openBtn = e.target.closest(".user-open-manage");
    if (!openBtn) {
      return;
    }
    var panelId = openBtn.getAttribute("data-manage-for");
    if (!panelId) {
      return;
    }
    var panel = document.getElementById(panelId);
    if (panel && panel.tagName === "DETAILS") {
      panel.open = true;
      panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  });
})();

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
    var root = ensureToastRoot();
    var toast = document.createElement("div");
    toast.className = "toast toast--" + (variant || "info");
    toast.setAttribute("role", "alert");

    var text = document.createElement("span");
    text.className = "toast-text";
    text.textContent = message;

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
    root.appendChild(toast);

    requestAnimationFrame(function () {
      toast.classList.add("toast--show");
    });

    setTimeout(dismiss, 5000);
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
})();
