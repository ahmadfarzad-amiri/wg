"""Shell command helpers."""
import re
import subprocess


def run(cmd, timeout=8):
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


def tail_message(output, limit=1000):
    text = (output or "").strip()
    if len(text) <= limit:
        return text
    return text[-limit:]
