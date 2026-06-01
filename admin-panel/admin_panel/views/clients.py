from admin_panel.components.client_rows import add_client_form, client_rows
from admin_panel.components.list_search import client_filters, client_sorts, list_controls
from admin_panel.components.notice import notice
from admin_panel.components.table import data_table
from admin_panel.core.i18n import t
from admin_panel.db.panel_queries import assigned_client_names, users_by_client


def body(clients, msg=""):
    rows, cards = client_rows(clients, assigned_client_names(), users_by_client())
    table = data_table(
        [
            t("col.name"),
            t("col.ip"),
            t("col.vpn_mode"),
            t("col.status"),
            t("col.usage"),
            t("col.last_connection"),
            t("col.endpoint"),
            t("col.limit"),
        ],
        rows,
        cards,
        empty=t("empty.no_clients"),
        table_class="table-clients",
    )
    return f"""
<h1>{t("clients.title")}</h1>
<p class="subtitle">{t("clients.subtitle")}</p>
{notice(msg, role="alert")}

<section class="card add-client-card">
  <h3>{t("clients.add_title")}</h3>
  <p class="hint add-client-intro">{t("clients.add_intro")}</p>
  {add_client_form()}
</section>

<section class="card card-spaced list-filterable">
  <div class="list-section-head">
    <h3>{t("clients.all_title")}</h3>
    {list_controls(
        search_placeholder=t("list.search_clients"),
        filters=client_filters(),
        sorts=client_sorts(),
    )}
  </div>
  {table}
  <p class="list-search-empty" data-list-search-empty hidden>{t("empty.no_results")}</p>
</section>
"""
