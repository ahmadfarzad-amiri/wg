#!/usr/bin/env python3
"""Legacy entry point — delegates to app.py / admin_panel package."""
from admin_panel.bootstrap import install_paths

install_paths()

from admin_panel.main import run

if __name__ == "__main__":
    run()
