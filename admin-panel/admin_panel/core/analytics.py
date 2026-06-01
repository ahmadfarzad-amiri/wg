"""Dashboard metrics and analytics aggregation."""
import logging
import time

from admin_panel.core.i18n import human_duration, t
from admin_panel.core.labels import (
    label_action,
    label_client_status,
    label_request_status,
    label_user_status,
)
from admin_panel.core.wireguard import all_client_meta, build_wg_snapshot, human_bytes
from admin_panel.core.statuses import ClientState, RequestStatus, UserStatus
from admin_panel.db import panel_db
from wg_common.client_status import evaluate_client_meta

log = logging.getLogger(__name__)


def _status_from_meta(meta, transfers, handshakes):
    core = evaluate_client_meta(meta, transfers, handshakes)
    expires_at = core["expires_at"]
    days_left = None
    if expires_at > 0 and not core["expired"]:
        days_left = max(0, (expires_at - int(time.time())) // 86400)

    return {
        "name": meta.get("NAME", ""),
        "active": core["active"],
        "disabled": core["disabled"],
        "expired": core["expired"],
        "over_limit": core["over_limit"],
        "state_key": core["state_key"],
        "used_bytes": core["used_now"],
        "rx_bytes": core["rx_bytes"],
        "tx_bytes": core["tx_bytes"],
        "limit_bytes": core["limit_bytes"],
        "expires_at": expires_at,
        "days_left": days_left,
        "last": t("never") if not core["handshake_epoch"] else human_duration(core["handshake_age"]),
    }


def _fetch_user_stats():
    stats = {
        "total": 0,
        UserStatus.PENDING: 0,
        UserStatus.APPROVED: 0,
        UserStatus.DISABLED: 0,
        UserStatus.REJECTED: 0,
    }
    try:
        con = panel_db()
        rows = con.execute(
            "SELECT status, COUNT(*) AS n FROM users GROUP BY status"
        ).fetchall()
        con.close()
        for row in rows:
            stats[row["status"]] = row["n"]
            stats["total"] += row["n"]
    except Exception:
        log.exception("_fetch_user_stats failed")
    return stats


def _fetch_request_stats():
    stats = {RequestStatus.PENDING: 0, "total": 0, "today": 0, "week": 0}
    recent = []
    now = int(time.time())
    day_ago = now - 86400
    week_ago = now - 7 * 86400
    try:
        con = panel_db()
        stats[RequestStatus.PENDING] = con.execute(
            "SELECT COUNT(*) FROM requests WHERE status=?",
            (RequestStatus.PENDING,),
        ).fetchone()[0]
        stats["total"] = con.execute("SELECT COUNT(*) FROM requests").fetchone()[0]
        stats["today"] = con.execute(
            "SELECT COUNT(*) FROM requests WHERE created_at>=?", (day_ago,)
        ).fetchone()[0]
        stats["week"] = con.execute(
            "SELECT COUNT(*) FROM requests WHERE created_at>=?", (week_ago,)
        ).fetchone()[0]
        recent = con.execute(
            """
            SELECT requests.id, users.username, users.client_name,
                   requests.action, requests.status, requests.created_at
            FROM requests JOIN users ON users.id = requests.user_id
            ORDER BY requests.id DESC LIMIT 5
            """
        ).fetchall()
        con.close()
    except Exception:
        log.exception("_fetch_request_stats failed")
    return stats, recent


def dashboard_metrics():
    meta_list = all_client_meta()
    snapshot = build_wg_snapshot()
    transfers = snapshot["transfers"]
    handshakes = snapshot["handshakes"]

    clients = [_status_from_meta(m, transfers, handshakes) for m in meta_list]

    total = len(clients)
    active = sum(1 for c in clients if c["state_key"] == ClientState.ACTIVE)
    disabled = sum(1 for c in clients if c["state_key"] == ClientState.DISABLED)
    expired = sum(1 for c in clients if c["state_key"] == ClientState.EXPIRED)
    over_limit = sum(1 for c in clients if c["state_key"] == ClientState.OVER_LIMIT)
    offline = sum(1 for c in clients if c["state_key"] == ClientState.OFFLINE)
    expiring_soon = sum(
        1
        for c in clients
        if c["days_left"] is not None and c["days_left"] <= 7
    )

    total_used = sum(c["used_bytes"] for c in clients)
    total_rx = sum(c["rx_bytes"] for c in clients)
    total_tx = sum(c["tx_bytes"] for c in clients)
    limited = [c for c in clients if c["limit_bytes"] > 0]
    avg_usage_pct = 0
    if limited:
        avg_usage_pct = round(
            sum(min(100, c["used_bytes"] * 100 // c["limit_bytes"]) for c in limited)
            / len(limited)
        )

    online_pct = round(active * 100 / total) if total else 0

    health = [
        (ClientState.ACTIVE, label_client_status(ClientState.ACTIVE), active, "ok"),
        (ClientState.OFFLINE, label_client_status(ClientState.OFFLINE), offline, "bad"),
        (ClientState.DISABLED, label_client_status(ClientState.DISABLED), disabled, "warn"),
        (ClientState.EXPIRED, label_client_status(ClientState.EXPIRED), expired, "warn"),
        (ClientState.OVER_LIMIT, label_client_status(ClientState.OVER_LIMIT), over_limit, "warn"),
    ]

    top_usage = sorted(clients, key=lambda c: c["used_bytes"], reverse=True)[:5]

    user_stats = _fetch_user_stats()
    request_stats, recent_requests = _fetch_request_stats()

    return {
        "kpis": {
            "total_clients": total,
            "active": active,
            "online_pct": online_pct,
            "disabled": disabled,
            "expired": expired,
            "over_limit": over_limit,
            "expiring_soon": expiring_soon,
            "pending_users": user_stats[UserStatus.PENDING],
            "pending_requests": request_stats[RequestStatus.PENDING],
            "total_users": user_stats["total"],
            "requests_today": request_stats["today"],
            "requests_week": request_stats["week"],
        },
        "traffic": {
            "used": human_bytes(total_used),
            "rx": human_bytes(total_rx),
            "tx": human_bytes(total_tx),
            "avg_usage_pct": avg_usage_pct,
            "limited_count": len(limited),
        },
        "health": health,
        "users": user_stats,
        "top_usage": top_usage,
        "recent_requests": recent_requests,
        "label_action": label_action,
        "label_request_status": label_request_status,
        "label_user_status": label_user_status,
    }
