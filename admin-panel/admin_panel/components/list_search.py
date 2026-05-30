import html

from admin_panel.core.i18n import t
from admin_panel.core.labels import label_client_status, label_request_status, label_user_status


def client_filters():
    return [
        ("", t("filter.all_statuses")),
        ("active", label_client_status("active")),
        ("offline", label_client_status("offline")),
        ("disabled", label_client_status("disabled")),
        ("expired", label_client_status("expired")),
        ("over_limit", label_client_status("over_limit")),
        ("unassigned", t("filter.unassigned")),
    ]


def client_sorts():
    return [
        ("name-asc", t("sort.name_asc")),
        ("name-desc", t("sort.name_desc")),
        ("ip-asc", t("sort.ip")),
        ("status-asc", t("sort.status")),
    ]


def user_filters():
    return [
        ("", t("filter.all_statuses")),
        ("pending", label_user_status("pending")),
        ("approved", label_user_status("approved")),
        ("disabled", label_user_status("disabled")),
        ("rejected", label_user_status("rejected")),
    ]


def user_sorts():
    return [
        ("id-desc", t("sort.newest")),
        ("id-asc", t("sort.oldest")),
        ("name-asc", t("sort.username_asc")),
        ("name-desc", t("sort.username_desc")),
        ("client-asc", t("sort.client_asc")),
        ("status-asc", t("sort.status")),
    ]


def request_filters():
    return [
        ("", t("filter.all_statuses")),
        ("pending", label_request_status("pending")),
        ("approved", label_request_status("approved")),
        ("rejected", label_request_status("rejected")),
    ]


def request_sorts():
    return [
        ("id-desc", t("sort.newest")),
        ("id-asc", t("sort.oldest")),
        ("name-asc", t("sort.username_asc")),
        ("name-desc", t("sort.username_desc")),
        ("client-asc", t("sort.client_asc")),
        ("action-asc", t("sort.subject")),
        ("status-asc", t("sort.status")),
        ("created-desc", t("sort.date_new")),
        ("created-asc", t("sort.date_old")),
    ]


def active_filters():
    return [
        ("", t("filter.all_online")),
        ("fresh", t("filter.fresh")),
        ("idle", t("filter.idle")),
    ]


def active_sorts():
    return [
        ("name-asc", t("sort.name_asc")),
        ("name-desc", t("sort.name_desc")),
        ("ip-asc", t("sort.ip")),
        ("last-asc", t("sort.last_asc")),
        ("last-desc", t("sort.last_desc")),
        ("rx-desc", t("sort.rx_desc")),
        ("tx-desc", t("sort.tx_desc")),
    ]


def list_controls(*, search_placeholder=None, filters=None, sorts=None):
    filters = filters or [("", t("filter.all"))]
    sorts = sorts or [("default", t("sort.default"))]
    if search_placeholder is None:
        search_placeholder = t("list.search")

    search_ph = html.escape(search_placeholder)
    filter_opts = "".join(
        f'<option value="{html.escape(value)}">{html.escape(label)}</option>'
        for value, label in filters
    )
    sort_opts = "".join(
        f'<option value="{html.escape(value)}">{html.escape(label)}</option>'
        for value, label in sorts
    )

    filter_label = html.escape(t("list.filter"))
    sort_label = html.escape(t("list.sort"))

    return f"""
<div class="list-controls">
  <div class="list-search">
    <input type="search" class="list-search-input" data-list-search placeholder="{search_ph}" aria-label="{search_ph}" autocomplete="off">
  </div>
  <label class="list-control">
    <span class="list-control-label">{filter_label}</span>
    <select class="list-control-select" data-list-filter aria-label="{filter_label}">
      {filter_opts}
    </select>
  </label>
  <label class="list-control">
    <span class="list-control-label">{sort_label}</span>
    <select class="list-control-select" data-list-sort aria-label="{sort_label}">
      {sort_opts}
    </select>
  </label>
  <span class="list-search-meta" data-list-search-meta hidden></span>
</div>
"""


def list_search(placeholder=None):
    return list_controls(search_placeholder=placeholder or t("list.search"))
