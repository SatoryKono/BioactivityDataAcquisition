#!/usr/bin/env python3
"""Compatibility wrapper for canonical quality exemptions checker.

Canonical script:
- scripts/qa/check_quality_exemptions.py
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


def _canonical_script() -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    return repo_root / "scripts" / "qa" / "check_quality_exemptions.py"


if __name__ == "__main__":
    script = _canonical_script()
    if not script.exists():
        sys.stderr.write(f"ERROR: canonical script not found: {script}\n")
        raise SystemExit(2)
    runpy.run_path(str(script), run_name="__main__")
