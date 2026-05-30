"""Persian labels for admin panel codes."""

CLIENT_STATUS_LABELS = {
    "active": "آنلاین",
    "offline": "آفلاین",
    "disabled": "غیرفعال",
    "expired": "منقضی",
    "over_limit": "اتمام حجم",
}

USER_STATUS_LABELS = {
    "pending": "در انتظار تایید",
    "approved": "تایید شده",
    "disabled": "غیرفعال",
    "rejected": "رد شده",
}

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

REQUEST_STATUS_SHORT = {
    "pending": "معلق",
    "approved": "تایید",
    "rejected": "رد",
    "done": "انجام",
    "processed": "پردازش",
}

ACTION_SHORT = {
    "renew": "تمدید",
    "enable": "فعال‌سازی",
}

SINGLE_MODE_LABELS = {
    "off": "بدون محدودیت",
    "ip": "محدود به IP",
    "endpoint": "محدود به endpoint",
}


def label_client_status(key):
    return CLIENT_STATUS_LABELS.get(key, key)


def label_user_status(status):
    return USER_STATUS_LABELS.get(status, status)


def label_action(action):
    return ACTION_LABELS.get(action, action)


def label_request_status(status):
    return REQUEST_STATUS_LABELS.get(status, status)


def label_request_status_short(status):
    return REQUEST_STATUS_SHORT.get(status, label_request_status(status))


def label_action_short(action):
    return ACTION_SHORT.get(action, label_action(action))


def label_single_mode(mode):
    return SINGLE_MODE_LABELS.get(mode, mode)


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
