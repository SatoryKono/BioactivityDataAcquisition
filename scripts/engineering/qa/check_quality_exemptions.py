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


if __name__ == "__main__":
    script = _canonical_script()
    if not script.exists():
        sys.stderr.write(f"ERROR: canonical script not found: {script}\n")
        raise SystemExit(2)
    runpy.run_path(str(script), run_name="__main__")

def main(args: list[str] | None = None) -> int:
    script = _canonical_script()
    if not script.exists():
        sys.stderr.write(f"ERROR: canonical script not found: {script}\n")
        return 2

    # Save original argv
    original_argv = sys.argv.copy()
    try:
        # Patch sys.argv to pass arguments to runpy correctly
        if args is not None:
            sys.argv = [str(script)] + args
        else:
            sys.argv = [str(script)] + sys.argv[1:]

        globals_dict = runpy.run_path(str(script), run_name="__main__")

        return 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 0
    finally:
        # Restore argv
        sys.argv = original_argv
