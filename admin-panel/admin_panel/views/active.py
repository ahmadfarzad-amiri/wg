from admin_panel.components.active_rows import active_list
from admin_panel.components.list_search import active_filters, active_sorts, list_controls
from admin_panel.components.notice import notice, notice_html
from admin_panel.core.i18n import t


def body(clients, msg="", wg_hint=""):
    listing = active_list(clients)
    hint_block = notice_html(wg_hint, css_class="notice notice-hint") if wg_hint else ""
    empty_block = ""
    if not clients and not wg_hint:
        empty_block = notice_html(t("empty.no_online"))
    return f"""
<h1>{t("active.title")}</h1>
<p class="subtitle">{t("active.subtitle")}</p>
{hint_block}
{empty_block}
{notice(msg, role="alert")}

<section class="card card-active list-filterable">
  <div class="list-section-head">
    {list_controls(
        search_placeholder=t("list.search_active"),
        filters=active_filters(),
        sorts=active_sorts(),
    )}
  </div>
  {listing}
  <p class="list-search-empty" data-list-search-empty hidden>{t("empty.no_results")}</p>
</section>
"""
