#!/usr/bin/env python3
"""Canonical unified pipeline config validator entrypoint.

Purpose:
- Expose schema/config validation under scripts/schema.

Inputs:
- Verbose/strict/skip flags from CLI.

Outputs:
- Validation diagnostics and exit status.

Caller:
- py-config-bot automation, CI checks, local validation.
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
        / "py-config-bot-2.py"
    )


if __name__ == "__main__":
    script = _legacy_script()
    if not script.exists():
        sys.stderr.write(f"ERROR: legacy script not found: {script}\n")
        raise SystemExit(2)
    runpy.run_path(str(script), run_name="__main__")
