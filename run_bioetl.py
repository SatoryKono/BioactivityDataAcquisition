#!/usr/bin/env python
"""Wrapper script to run bioetl CLI with correct path setup."""
import sys
from pathlib import Path

# Remove old paths that might interfere
sys.path = [p for p in sys.path if 'bioactivity_data_acquisition1' not in p.lower()]

# Add src to path at the beginning
src_dir = Path(__file__).parent / "src"
src_str = str(src_dir)
if src_str in sys.path:
    sys.path.remove(src_str)
sys.path.insert(0, src_str)

from bioetl.interfaces.cli.app import app

if __name__ == "__main__":
    app()

