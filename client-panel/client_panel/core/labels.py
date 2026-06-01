"""Localized labels for internal codes."""
from client_panel.core.i18n import t
from client_panel.core.statuses import RequestStatus


def label_action(action):
    return t(f"action.{action}", action)


def label_request_status(status):
    return t(f"request.{status}", status)


def badge_request_status(status):
    if status == RequestStatus.PENDING:
        return "warn"
    if status == RequestStatus.REJECTED:
        return "bad"
    return "ok"
