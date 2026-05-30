from admin_panel.components.active_rows import active_list
from admin_panel.components.list_search import ACTIVE_FILTERS, ACTIVE_SORTS, list_controls
from admin_panel.components.notice import notice, notice_html


def body(clients, msg="", wg_hint=""):
    listing = active_list(clients)
    hint_block = notice_html(wg_hint, css_class="notice notice-hint") if wg_hint else ""
    empty_block = ""
    if not clients and not wg_hint:
        empty_block = notice_html("در حال حاضر کاربر آنلاینی نیست.")
    return f"""
<h1>کاربران آنلاین</h1>
<p class="subtitle">اتصال فعال در ۱۲۰ ثانیه اخیر</p>
{hint_block}
{empty_block}
{notice(msg, role="alert")}

<section class="card card-active list-filterable">
  <div class="list-section-head">
    {list_controls(
        search_placeholder="جستجو در کاربران آنلاین…",
        filters=ACTIVE_FILTERS,
        sorts=ACTIVE_SORTS,
    )}
  </div>
  {listing}
  <p class="list-search-empty" data-list-search-empty hidden>نتیجه‌ای برای جستجو پیدا نشد.</p>
</section>
"""
