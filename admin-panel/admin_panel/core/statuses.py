"""Re-export shared status constants for admin panel code."""
from wg_common.statuses import ClientState, RequestStatus, UserStatus

__all__ = ["ClientState", "RequestStatus", "UserStatus"]
