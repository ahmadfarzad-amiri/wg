"""Pure WireGuard client status computation (no i18n)."""
import time

from wg_common.statuses import ClientState

HANDSHAKE_ACTIVE_SECONDS = 120


def transfer_totals(meta, transfers):
    pub = meta.get("PUBLIC_KEY", "")
    rx = tx = 0
    if pub in transfers and len(transfers[pub]) >= 2:
        rx = int(transfers[pub][0])
        tx = int(transfers[pub][1])
    return rx, tx, rx + tx


def used_bytes_now(meta, transfers):
    _, _, current_total = transfer_totals(meta, transfers)
    used_base = int(meta.get("USED_BYTES", "0") or 0)
    last_total = int(meta.get("LAST_TOTAL", "0") or 0)
    return used_base + max(0, current_total - last_total)


def handshake_info(meta, handshakes, now=None):
    now = int(now or time.time())
    pub = meta.get("PUBLIC_KEY", "")
    hs = 0
    if pub in handshakes and handshakes[pub]:
        hs = int(handshakes[pub][0])
    diff = now - hs if hs else 999_999_999
    active = hs > 0 and diff <= HANDSHAKE_ACTIVE_SECONDS
    return hs, diff, active


def _reason_hints(meta):
    reason = (meta.get("DISABLED_REASON", "") or "").lower()
    expired = "expired" in reason or "expire" in reason
    over_limit = (
        "data limit" in reason
        or "limit reached" in reason
        or "over data" in reason
        or "quota" in reason
    )
    return expired, over_limit


def compute_state_key(meta, used_now, *, active, now=None, use_reason_hints=False):
    """Return (state_key, expired, over_limit, disabled)."""
    now = int(now or time.time())
    limit_bytes = int(meta.get("LIMIT_BYTES", "0") or 0)
    expires_at = int(meta.get("EXPIRES_AT", "0") or 0)
    disabled = meta.get("DISABLED", "0") == "1"

    expired = expires_at > 0 and now >= expires_at
    over_limit = limit_bytes > 0 and used_now >= limit_bytes

    if use_reason_hints:
        reason_expired, reason_over = _reason_hints(meta)
        expired = expired or reason_expired
        over_limit = over_limit or reason_over
        if expired:
            return ClientState.EXPIRED, True, over_limit, disabled
        if over_limit:
            return ClientState.OVER_LIMIT, expired, True, disabled
        if disabled:
            return ClientState.DISABLED, expired, over_limit, True
        return ClientState.ACTIVE, expired, over_limit, disabled

    if disabled:
        return ClientState.DISABLED, expired, over_limit, True
    if expired:
        return ClientState.EXPIRED, True, over_limit, disabled
    if over_limit:
        return ClientState.OVER_LIMIT, expired, True, disabled
    if active:
        return ClientState.ACTIVE, expired, over_limit, disabled
    return ClientState.OFFLINE, expired, over_limit, disabled


def evaluate_client_meta(meta, transfers, handshakes, *, use_reason_hints=False, now=None):
    now = int(now or time.time())
    used_now = used_bytes_now(meta, transfers)
    rx, tx, _ = transfer_totals(meta, transfers)
    hs, diff, active = handshake_info(meta, handshakes, now=now)
    state_key, expired, over_limit, disabled = compute_state_key(
        meta,
        used_now,
        active=active,
        now=now,
        use_reason_hints=use_reason_hints,
    )
    limit_bytes = int(meta.get("LIMIT_BYTES", "0") or 0)
    expires_at = int(meta.get("EXPIRES_AT", "0") or 0)
    return {
        "used_now": used_now,
        "rx_bytes": rx,
        "tx_bytes": tx,
        "handshake_epoch": hs,
        "handshake_age": diff,
        "active": active,
        "state_key": state_key,
        "expired": expired,
        "over_limit": over_limit,
        "disabled": disabled,
        "limit_bytes": limit_bytes,
        "expires_at": expires_at,
    }
