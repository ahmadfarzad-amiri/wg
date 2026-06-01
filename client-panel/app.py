#!/usr/bin/env python3
"""WireGuard client panel entry point."""
import sys
from pathlib import Path

_install_root = Path(__file__).resolve().parent.parent
_client_dir = Path(__file__).resolve().parent
for _p in (str(_install_root), str(_client_dir)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from client_panel.bootstrap import install_paths, require_wg_common

    install_paths()
    require_wg_common()
except ImportError:
    pass

from client_panel.main import run

if __name__ == "__main__":
    run()
