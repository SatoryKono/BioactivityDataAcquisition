#!/usr/bin/env python3
"""Generate Gold JSON contracts via canonical schema script entrypoint.

Purpose:
- Provide canonical executable path under scripts/schema.

Inputs:
- CLI args forwarded to legacy generator.

Outputs:
- Regenerated JSON contracts and diff report files.

Caller:
- Makefile contracts-check, schema artifact generation, CI workflows.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


def _legacy_script() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "src" / "tools" / "scripts" / "generate_contracts.py"


if __name__ == "__main__":
    script = _legacy_script()
    if not script.exists():
        sys.stderr.write(f"ERROR: legacy script not found: {script}\n")
        raise SystemExit(2)
    runpy.run_path(str(script), run_name="__main__")
