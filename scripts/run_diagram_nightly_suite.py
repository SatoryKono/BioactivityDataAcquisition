#!/usr/bin/env python3
"""Deprecated wrapper; use scripts/diagrams counterpart."""
from __future__ import annotations

from pathlib import Path
import runpy
import sys

_CURRENT = Path(__file__).resolve()
_TARGET = _CURRENT.parent / "diagrams" / _CURRENT.name

if __name__ == "__main__":
    print(f"[DEPRECATED] Use scripts/diagrams/{_CURRENT.name}", file=sys.stderr)
    runpy.run_path(str(_TARGET), run_name="__main__")
