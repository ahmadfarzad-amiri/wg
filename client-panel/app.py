#!/usr/bin/env python3
"""WireGuard client panel entry point."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from client_panel.main import run

if __name__ == "__main__":
    run()
