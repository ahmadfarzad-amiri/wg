"""Ensure admin panel can import wg_common and client_panel DB helpers."""
import sys
from pathlib import Path


def install_paths():
    admin_dir = Path(__file__).resolve().parent.parent
    install_root = admin_dir.parent
    client_panel_dir = install_root / "client-panel"
    for path in (str(install_root), str(admin_dir), str(client_panel_dir)):
        if path not in sys.path:
            sys.path.insert(0, path)
