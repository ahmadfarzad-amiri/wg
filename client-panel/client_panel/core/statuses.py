"""Re-export shared status constants for client panel code."""
from wg_common.statuses import ClientState, RequestStatus, UserStatus

__all__ = ["ClientState", "RequestStatus", "UserStatus"]
