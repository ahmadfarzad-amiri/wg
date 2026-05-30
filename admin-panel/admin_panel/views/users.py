from admin_panel.components.list_search import USER_FILTERS, USER_SORTS, list_controls
from admin_panel.components.notice import notice
from admin_panel.components.user_rows import user_rows


def body(users, msg=""):
    listing = user_rows(users)
    return f"""
<h1>کاربران</h1>
<p class="subtitle">نام کلاینت را وارد کنید: اگر وجود داشته باشد اختصاص می‌یابد، در غیر این صورت ساخته می‌شود.</p>
{notice(msg, role="alert")}

<section class="card card-users list-filterable">
  <div class="list-section-head">
    {list_controls(
        search_placeholder="جستجو در کاربران…",
        filters=USER_FILTERS,
        sorts=USER_SORTS,
    )}
  </div>
  {listing}
  <p class="list-search-empty" data-list-search-empty hidden>نتیجه‌ای برای جستجو پیدا نشد.</p>
</section>
"""
