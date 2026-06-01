#!/usr/bin/env python3
"""WireGuard admin panel entry point."""
from admin_panel.bootstrap import install_paths

install_paths()

from admin_panel.main import run

if __name__ == "__main__":
    run()
