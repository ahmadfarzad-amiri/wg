"""Persian labels for internal codes."""

ACTION_LABELS = {
    "renew": "تمدید اشتراک",
    "enable": "فعال‌سازی",
}

REQUEST_STATUS_LABELS = {
    "pending": "در انتظار بررسی",
    "approved": "تایید شده",
    "rejected": "رد شده",
    "done": "انجام شده",
    "processed": "پردازش شده",
}


def label_action(action):
    return ACTION_LABELS.get(action, action)


def label_request_status(status):
    return REQUEST_STATUS_LABELS.get(status, status)


def badge_request_status(status):
    if status == "pending":
        return "warn"
    if status == "rejected":
        return "bad"
    return "ok"
