(function () {
  "use strict";

  document.querySelectorAll("[data-confirm]").forEach(function (btn) {
    btn.addEventListener("click", function (e) {
      var msg = btn.getAttribute("data-confirm") || "ادامه می‌دهید؟";
      if (!window.confirm(msg)) {
        e.preventDefault();
      }
    });
  });

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
    if (field === "last" || field === "rx" || field === "tx") {
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
      cmp = String(av).localeCompare(String(bv), "fa", { numeric: true, sensitivity: "base" });
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
      reorderClientDesktop(listHost.querySelector("[data-list-desktop]"), sortValueStr);
      reorderItems(listHost.querySelector("[data-list-mobile]"), "[data-list-primary]", sortValueStr);
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

      if (kind === "clients") {
        var actions = item.nextElementSibling;
        if (item.tagName === "TR" && actions && actions.classList.contains("client-row-actions")) {
          setItemVisible(actions, match);
        }
      }

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
        metaEl.textContent = visible + " از " + total;
      } else {
        metaEl.hidden = true;
        metaEl.textContent = "";
      }
    }
  }

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
  });
})();
