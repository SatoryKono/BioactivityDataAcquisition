#!/usr/bin/env python3
"""Shared compatibility wrapper for deprecated diagram entrypoints."""
from __future__ import annotations

from pathlib import Path
import runpy
import sys


def run_deprecated_diagram_wrapper(current_file: str) -> None:
    current = Path(current_file).resolve()
    target = current.parent / "diagrams" / current.name
    if not target.exists():
        print(f"[ERROR] Missing canonical script: {target}", file=sys.stderr)
        raise SystemExit(2)

    print(f"[DEPRECATED] Use scripts/diagrams/{current.name}", file=sys.stderr)
    runpy.run_path(str(target), run_name="__main__")
