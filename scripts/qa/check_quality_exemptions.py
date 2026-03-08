#!/usr/bin/env python3
"""Canonical quality exemptions gate entrypoint.

Purpose:
- Centralize quality exemption validation under scripts/qa.

Inputs:
- Registry/scorecard/mode flags from CLI.

Outputs:
- Registry/scorecard gate diagnostics and exit code.

Caller:
- CI governance checks and manual quality audits.
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
        / "architecture-techdebt-automation.py"
    )


if __name__ == "__main__":
    script = _legacy_script()
    if not script.exists():
        sys.stderr.write(f"ERROR: legacy script not found: {script}\n")
        raise SystemExit(2)
    runpy.run_path(str(script), run_name="__main__")
