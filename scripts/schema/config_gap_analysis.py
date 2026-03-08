#!/usr/bin/env python3
"""Canonical config gap analysis entrypoint.

Purpose:
- Centralize config governance script under scripts/schema.

Inputs:
- Optional output path and flags.

Outputs:
- Gap report over entity/composite config files.

Caller:
- py-config-bot orchestration, local governance checks.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


def _legacy_script() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    return (
        repo_root
        / "docs"
        / "00-project"
        / "ai"
        / "agents"
        / "scripts"
        / "py-config-bot-1.py"
    )


if __name__ == "__main__":
    script = _legacy_script()
    if not script.exists():
        sys.stderr.write(f"ERROR: legacy script not found: {script}\n")
        raise SystemExit(2)
    runpy.run_path(str(script), run_name="__main__")
