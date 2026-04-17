#!/usr/bin/env python3
"""Compatibility wrapper for the legacy duplicate function analyzer."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


def _legacy_script() -> Path:
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / "src" / "tools" / "scripts" / "duplicate_function_analyzer.py"


if __name__ == "__main__":
    script = _legacy_script()
    if not script.exists():
        sys.stderr.write(f"ERROR: legacy script not found: {script}\n")
        raise SystemExit(2)
    runpy.run_path(str(script), run_name="__main__")
