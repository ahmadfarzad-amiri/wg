#!/usr/bin/env python3
"""WireGuard admin panel entry point."""
import sys
from pathlib import Path

_install_root = Path(__file__).resolve().parent.parent
_admin_dir = Path(__file__).resolve().parent
_client_panel_dir = _install_root / "client-panel"
for _p in (str(_admin_dir), str(_client_panel_dir)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from admin_panel.bootstrap import install_paths

    install_paths()
except ImportError:
    pass

from admin_panel.main import run

if __name__ == "__main__":
    run()
