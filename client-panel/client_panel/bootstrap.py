"""Ensure client panel can import wg_common from the install root."""
import sys
from pathlib import Path


def install_paths():
    client_dir = Path(__file__).resolve().parent.parent
    install_root = client_dir.parent
    for path in (str(install_root), str(client_dir)):
        if path not in sys.path:
            sys.path.insert(0, path)


def require_wg_common():
    install_paths()
    try:
        import wg_common  # noqa: F401
    except ImportError as exc:
        install_root = Path(__file__).resolve().parent.parent.parent
        raise SystemExit(
            f"Missing wg_common package at {install_root / 'wg_common'}. "
            "Run: sudo wg-ops update-panels (or rsync wg_common/ to the install dir)."
        ) from exc
