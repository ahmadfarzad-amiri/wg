"""Localized labels for internal codes."""
from client_panel.core.i18n import t


def label_action(action):
    return t(f"action.{action}", action)


def label_request_status(status):
    return t(f"request.{status}", status)


def badge_request_status(status):
    if status == "pending":
        return "warn"
    if status == "rejected":
        return "bad"
    return "ok"
