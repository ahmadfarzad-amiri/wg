from admin_panel.components.list_search import list_controls, request_filters, request_sorts
from admin_panel.components.notice import notice
from admin_panel.components.request_rows import request_list
from admin_panel.core.i18n import t


def body(items, msg="", variant="info"):
    listing = request_list(items)
    return f"""
<h1>{t("requests.title")}</h1>
<p class="subtitle">{t("requests.subtitle")}</p>
<p class="hint page-glossary">{t("glossary.requests")}</p>
{notice(msg, variant=variant)}

<div class="page-stack">
<section class="card card-requests list-filterable">
  <div class="list-section-head">
    <h3>{t("requests.list_title")}</h3>
    {list_controls(
        search_placeholder=t("list.search_requests"),
        filters=request_filters(),
        sorts=request_sorts(),
    )}
  </div>
  {listing}
  <p class="list-search-empty" data-list-search-empty hidden>{t("empty.no_results")}</p>
</section>
</div>
"""
