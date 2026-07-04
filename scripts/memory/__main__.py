#!/usr/bin/env python3
"""Legacy compatibility entry point for ``python -m scripts.memory``."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

main = importlib.import_module("memory.graph.__main__").main

if __name__ == "__main__":
    raise SystemExit(main())
