#!/usr/bin/env python3
"""Canonical terminology lint entrypoint.

Purpose:
- Stabilize script discovery under scripts/qa.

Inputs:
- Paths and strict flags passed via CLI.

Outputs:
- Terminology lint diagnostics and non-zero exit on violations.

Caller:
- Developer local checks, quality automation.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


def _legacy_script() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "src" / "tools" / "scripts" / "lint_terminology.py"


if __name__ == "__main__":
    script = _legacy_script()
    if not script.exists():
        sys.stderr.write(f"ERROR: legacy script not found: {script}\n")
        raise SystemExit(2)
    runpy.run_path(str(script), run_name="__main__")
