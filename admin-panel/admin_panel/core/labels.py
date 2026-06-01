"""Localized labels for admin panel codes."""
from admin_panel.core.i18n import t


def label_client_status(key):
    return t(f"state.{key}", key)


def label_user_status(status):
    return t(f"user.{status}", status)


def label_action(action):
    return t(f"action.{action}", action)


def label_request_status(status):
    return t(f"request.{status}", status)


def label_request_status_short(status):
    return t(f"request.{status}_short", label_request_status(status))


def label_action_short(action):
    return t(f"action.{action}_short", label_action(action))


def label_single_mode(mode):
    return t(f"single.{mode}", mode)


def label_vpn_mode(mode):
    mode = (mode or "twohop").lower()
    return t(f"vpn.{mode}", mode)


def badge_user_status(status):
    if status == "pending":
        return "warn"
    if status == "approved":
        return "ok"
    return "bad"


def badge_request_status(status):
    if status == "pending":
        return "warn"
    if status == "rejected":
        return "bad"
    return "ok"
