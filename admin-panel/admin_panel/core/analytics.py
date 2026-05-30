"""Dashboard metrics and analytics aggregation."""
import time

from admin_panel.core.labels import label_action, label_request_status, label_user_status
from admin_panel.core.wireguard import all_client_meta, build_wg_snapshot, human_bytes, human_duration
from admin_panel.db import panel_db


def _status_from_meta(meta, transfers, endpoints, handshakes):
    pub = meta.get("PUBLIC_KEY", "")
    rx = tx = current_total = 0
    if pub in transfers and len(transfers[pub]) >= 2:
        rx = int(transfers[pub][0])
        tx = int(transfers[pub][1])
        current_total = rx + tx

    used_base = int(meta.get("USED_BYTES", "0") or 0)
    last_total = int(meta.get("LAST_TOTAL", "0") or 0)
    used_now = used_base + max(0, current_total - last_total)

    hs = 0
    if pub in handshakes and handshakes[pub]:
        hs = int(handshakes[pub][0])

    now = int(time.time())
    diff = now - hs if hs else 999999999
    active = hs > 0 and diff <= 120

    limit_bytes = int(meta.get("LIMIT_BYTES", "0") or 0)
    expires_at = int(meta.get("EXPIRES_AT", "0") or 0)
    expired = expires_at > 0 and now >= expires_at
    over_limit = limit_bytes > 0 and used_now >= limit_bytes
    disabled = meta.get("DISABLED", "0") == "1"

    days_left = None
    if expires_at > 0 and not expired:
        days_left = max(0, (expires_at - now) // 86400)

    state_key = "offline"
    if disabled:
        state_key = "disabled"
    elif expired:
        state_key = "expired"
    elif over_limit:
        state_key = "over_limit"
    elif active:
        state_key = "active"

    return {
        "name": meta.get("NAME", ""),
        "active": active,
        "disabled": disabled,
        "expired": expired,
        "over_limit": over_limit,
        "state_key": state_key,
        "used_bytes": used_now,
        "rx_bytes": rx,
        "tx_bytes": tx,
        "limit_bytes": limit_bytes,
        "expires_at": expires_at,
        "days_left": days_left,
        "last": "هرگز" if not hs else human_duration(diff),
    }


def _fetch_user_stats():
    stats = {
        "total": 0,
        "pending": 0,
        "approved": 0,
        "disabled": 0,
        "rejected": 0,
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
        pass
    return stats


def _fetch_request_stats():
    stats = {"pending": 0, "total": 0, "today": 0, "week": 0}
    recent = []
    now = int(time.time())
    day_ago = now - 86400
    week_ago = now - 7 * 86400
    try:
        con = panel_db()
        stats["pending"] = con.execute(
            "SELECT COUNT(*) FROM requests WHERE status='pending'"
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
        pass
    return stats, recent


def dashboard_metrics():
    meta_list = all_client_meta()
    snapshot = build_wg_snapshot()
    transfers = snapshot["transfers"]
    endpoints = snapshot["endpoints"]
    handshakes = snapshot["handshakes"]

    clients = [
        _status_from_meta(m, transfers, endpoints, handshakes) for m in meta_list
    ]

    total = len(clients)
    active = sum(1 for c in clients if c["state_key"] == "active")
    disabled = sum(1 for c in clients if c["state_key"] == "disabled")
    expired = sum(1 for c in clients if c["state_key"] == "expired")
    over_limit = sum(1 for c in clients if c["state_key"] == "over_limit")
    offline = sum(1 for c in clients if c["state_key"] == "offline")
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
        ("active", "آنلاین", active, "ok"),
        ("offline", "آفلاین", offline, "bad"),
        ("disabled", "غیرفعال", disabled, "warn"),
        ("expired", "منقضی", expired, "warn"),
        ("over_limit", "اتمام حجم", over_limit, "warn"),
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
            "pending_users": user_stats["pending"],
            "pending_requests": request_stats["pending"],
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
