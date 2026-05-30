#!/usr/bin/env python3
"""Legacy entry point — delegates to app.py / admin_panel package."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from admin_panel.main import run

if __name__ == "__main__":
    run()
