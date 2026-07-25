"""Resolve the shared release version for panels (env or GitHub latest)."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

_GITHUB_OWNER = os.environ.get("GITHUB_OWNER", "ahmadfarzad-amiri")
_GITHUB_REPO = os.environ.get("GITHUB_REPO_NAME", "wg")
_TIMEOUT = float(os.environ.get("WG_VERSION_RESOLVE_TIMEOUT", "5"))


def _strip_v(tag: str) -> str:
    tag = (tag or "").strip()
    if tag.startswith("v") or tag.startswith("V"):
        return tag[1:]
    return tag


def _http_json(url: str) -> object | None:
    try:
        req = urllib.request.Request(
            url,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "wg-panels"},
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return None


def latest_github_version(
    owner: str = _GITHUB_OWNER,
    repo: str = _GITHUB_REPO,
) -> str:
    """Return latest release/tag semver without leading v, or empty string."""
    data = _http_json(f"https://api.github.com/repos/{owner}/{repo}/releases/latest")
    if isinstance(data, dict):
        tag = _strip_v(str(data.get("tag_name") or ""))
        if tag:
            return tag

    data = _http_json(f"https://api.github.com/repos/{owner}/{repo}/tags?per_page=1")
    if isinstance(data, list) and data:
        tag = _strip_v(str(data[0].get("name") or ""))
        if tag:
            return tag
    return ""


def resolve_version() -> str:
    """WG_VERSION env if set, else latest GitHub tag, else 'unknown'."""
    env = _strip_v(os.environ.get("WG_VERSION", ""))
    if env:
        return env
    return latest_github_version() or "unknown"
