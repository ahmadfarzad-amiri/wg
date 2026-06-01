import html

from admin_panel.core.i18n import t
from admin_panel.core.labels import label_client_status, label_request_status, label_user_status
from admin_panel.core.statuses import ClientState, RequestStatus, UserStatus


def client_filters():
    return [
        ("", t("filter.all_statuses")),
        (ClientState.ACTIVE, label_client_status(ClientState.ACTIVE)),
        (ClientState.OFFLINE, label_client_status(ClientState.OFFLINE)),
        (ClientState.DISABLED, label_client_status(ClientState.DISABLED)),
        (ClientState.EXPIRED, label_client_status(ClientState.EXPIRED)),
        (ClientState.OVER_LIMIT, label_client_status(ClientState.OVER_LIMIT)),
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
        (UserStatus.PENDING, label_user_status(UserStatus.PENDING)),
        (UserStatus.APPROVED, label_user_status(UserStatus.APPROVED)),
        (UserStatus.DISABLED, label_user_status(UserStatus.DISABLED)),
        (UserStatus.REJECTED, label_user_status(UserStatus.REJECTED)),
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
        (RequestStatus.PENDING, label_request_status(RequestStatus.PENDING)),
        (RequestStatus.APPROVED, label_request_status(RequestStatus.APPROVED)),
        (RequestStatus.REJECTED, label_request_status(RequestStatus.REJECTED)),
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


def list_controls(*, search_placeholder=None, filters=None, sorts=None, default_filter=""):
    filters = filters or [("", t("filter.all"))]
    sorts = sorts or [("default", t("sort.default"))]
    if search_placeholder is None:
        search_placeholder = t("list.search")

    search_ph = html.escape(search_placeholder)
    filter_opts = "".join(
        f'<option value="{html.escape(value)}"{" selected" if value == default_filter else ""}>'
        f"{html.escape(label)}</option>"
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
  <div class="list-search list-search-field">
    <input type="search" class="list-search-input" data-list-search placeholder="{search_ph}" aria-label="{search_ph}" autocomplete="off" enterkeyhint="search">
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
