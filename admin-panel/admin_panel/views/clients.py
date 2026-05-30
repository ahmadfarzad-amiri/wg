from admin_panel.components.client_rows import add_client_form, client_rows
from admin_panel.components.list_search import CLIENT_FILTERS, CLIENT_SORTS, list_controls
from admin_panel.components.notice import notice
from admin_panel.components.table import data_table
from admin_panel.db.panel_queries import assigned_client_names, users_by_client


def body(clients, msg=""):
    rows, cards = client_rows(clients, assigned_client_names(), users_by_client())
    table = data_table(
        ["نام", "IP", "وضعیت", "مصرف", "آخرین اتصال", "Endpoint", "محدودیت"],
        rows,
        cards,
        empty="هنوز کلاینتی ثبت نشده",
        table_class="table-clients",
    )
    return f"""
<h1>کلاینت‌ها</h1>
<p class="subtitle">مدیریت کانفیگ‌های WireGuard</p>
{notice(msg, role="alert")}

<section class="card add-client-card">
  <h3>افزودن کلاینت</h3>
  <p class="hint add-client-intro">نام یکتا، مدت اشتراک، سقف حجم و محدودیت دستگاه را مشخص کنید.</p>
  {add_client_form()}
</section>

<section class="card card-spaced list-filterable">
  <div class="list-section-head">
    <h3>همه کلاینت‌ها</h3>
    {list_controls(
        search_placeholder="جستجو در کلاینت‌ها…",
        filters=CLIENT_FILTERS,
        sorts=CLIENT_SORTS,
    )}
  </div>
  {table}
  <p class="list-search-empty" data-list-search-empty hidden>نتیجه‌ای برای جستجو پیدا نشد.</p>
</section>
"""
