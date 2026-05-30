from admin_panel.components.list_search import REQUEST_FILTERS, REQUEST_SORTS, list_controls
from admin_panel.components.notice import notice
from admin_panel.components.request_rows import request_list


def body(items, msg=""):
    listing = request_list(items)
    return f"""
<h1>درخواست‌ها</h1>
<p class="subtitle">تمدید و فعال‌سازی در انتظار بررسی</p>
{notice(msg, role="alert")}

<section class="card card-requests list-filterable">
  <div class="list-section-head">
    {list_controls(
        search_placeholder="جستجو در درخواست‌ها…",
        filters=REQUEST_FILTERS,
        sorts=REQUEST_SORTS,
    )}
  </div>
  {listing}
  <p class="list-search-empty" data-list-search-empty hidden>نتیجه‌ای برای جستجو پیدا نشد.</p>
</section>
"""
