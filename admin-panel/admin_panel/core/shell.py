"""Shell command helpers."""
import re
import subprocess

DEFAULT_TIMEOUT = 8
CLIENT_CMD_TIMEOUT = 60

_SECRET_LINE_RE = re.compile(
    r"(?im)^\s*(PrivateKey|PresharedKey|Password|Secret|Token)\s*=.*$"
)
_SUMMARY_PREFIXES = (
    "Created client",
    "Updated client",
    "Removed client",
    "Disabled client",
    "Enabled client",
    "Renewed client",
    "Client IP",
    "Limit:",
    "Expires:",
    "VPN mode:",
    "Used:",
    "Disabled:",
    "Reason:",
    "Single-device mode:",
    "Single:",
    "Config file:",
    "New config file:",
    "Synced VPN",
    "Set VPN mode",
    "Approved ",
    "Rejected ",
    "Imported",
    "IMPORTED:",
    "ERROR:",
    "WARNING:",
)


def run(cmd, timeout=DEFAULT_TIMEOUT):
    try:
        return subprocess.check_output(
            cmd, text=True, stderr=subprocess.STDOUT, timeout=timeout
        ).strip()
    except subprocess.CalledProcessError as e:
        return e.output.strip()
    except Exception as e:
        return str(e)


def safe_name(value):
    return re.sub(r"[^A-Za-z0-9_.-]", "_", (value or "").strip())


def _looks_like_wg_config(text):
    return "PrivateKey" in text or ("[Interface]" in text and "[Peer]" in text)


def _summary_lines(text):
    keep = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("["):
            break
        if _SECRET_LINE_RE.match(s):
            continue
        if any(s.startswith(prefix) for prefix in _SUMMARY_PREFIXES):
            keep.append(s)
    return keep


def sanitize_user_message(output, *, limit=280, fallback=""):
    """Return shell output safe for toasts: no secrets, no full config dumps."""
    text = _SECRET_LINE_RE.sub(
        lambda m: f"{m.group(1)} = [redacted]", (output or "").strip()
    )
    if not text:
        return fallback or ""

    if _looks_like_wg_config(text):
        keep = _summary_lines(text)
        if keep:
            text = "\n".join(keep)
        elif fallback:
            return fallback
        else:
            first = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
            text = first

    if len(text) > limit:
        text = text[: max(0, limit - 1)].rstrip() + "…"
    return text


def tail_message(output, limit=1000):
    """Legacy helper: sanitize CLI output for user-facing flash/toast messages."""
    return sanitize_user_message(output, limit=min(limit, 400))
