#!/usr/bin/env python3
"""Compatibility wrapper for agent-canonical quality exemptions checker.

Canonical script:
- docs/00-project/ai/agents/scripts/architecture-techdebt-automation.py
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


def _canonical_script() -> Path:
    repo_root = Path(__file__).resolve().parents[3]
    return (
        repo_root
        / "docs"
        / "00-project"
        / "ai"
        / "agents"
        / "scripts"
        / "architecture-techdebt-automation.py"
    )


def main(argv: list[str] | None = None) -> int:
    """Run the canonical quality-exemptions checker with forwarded arguments."""
    script = _canonical_script()
    if not script.exists():
        sys.stderr.write(f"ERROR: canonical script not found: {script}\n")
        return 2

    original_argv = sys.argv
    sys.argv = [str(script), *(argv or [])]
    try:
        runpy.run_path(str(script), run_name="__main__")
    except SystemExit as exc:
        if isinstance(exc.code, int):
            return exc.code
        return 0 if exc.code is None else 1
    finally:
        sys.argv = original_argv
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
