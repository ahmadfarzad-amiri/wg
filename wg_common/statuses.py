"""Status string constants shared by admin and client panels."""


class UserStatus:
    """Values stored in users.status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISABLED = "disabled"

    ALL = (PENDING, APPROVED, REJECTED, DISABLED)


class RequestStatus:
    """Values stored in requests.status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

    ALL = (PENDING, APPROVED, REJECTED)


class ClientState:
    """WireGuard client lifecycle states (derived from .meta + wg show)."""

    OFFLINE = "offline"
    ACTIVE = "active"
    DISABLED = "disabled"
    EXPIRED = "expired"
    OVER_LIMIT = "over_limit"

    ALL = (OFFLINE, ACTIVE, DISABLED, EXPIRED, OVER_LIMIT)

    NEEDS_SUPPORT = (EXPIRED, OVER_LIMIT, DISABLED)
