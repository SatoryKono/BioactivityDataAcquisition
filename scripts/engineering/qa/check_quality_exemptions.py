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


def main(argv: list[str] | None = None) -> int:
    script = _canonical_script()
    if not script.exists():
        import sys

        sys.stderr.write(f"ERROR: canonical script not found: {script}\n")
        return 2
    # Load and execute the canonical script's main function
    module_dict = runpy.run_path(
        str(script), run_name="scripts.engineering.qa.check_quality_exemptions"
    )
    if "main" in module_dict:
        import sys

        # the main in the target script expects sys.argv to be set appropriately if argv is None,
        # but to be safe, we just let it use sys.argv or pass argv if supported.
        # Actually it's probably better to just patch sys.argv and call it
        old_argv = sys.argv
        if argv is not None:
            sys.argv = [str(script)] + argv
        try:
            return module_dict["main"]()
        finally:
            sys.argv = old_argv
    else:
        # If it doesn't have a main, just running it might have executed the logic if it was run_name="__main__",
        # but we ran it as not __main__ so it shouldn't have.
        # Let's run it as __main__ if no main is found.
        try:
            runpy.run_path(str(script), run_name="__main__")
            return 0
        except SystemExit as e:
            return e.code or 0
