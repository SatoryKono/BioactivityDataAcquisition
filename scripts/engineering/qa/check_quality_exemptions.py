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
    script = _canonical_script()
    if not script.exists():
        sys.stderr.write(f"ERROR: canonical script not found: {script}\n")
        return 2

    import importlib.util
    spec = importlib.util.spec_from_file_location("__main__", str(script))
    if spec is None or spec.loader is None:
        sys.stderr.write(f"ERROR: failed to load spec from {script}\n")
        return 2
    module = importlib.util.module_from_spec(spec)
    sys.modules["__main__"] = module
    try:
        spec.loader.exec_module(module)
        if hasattr(module, "main"):
            return module.main(argv)
        else:
            sys.stderr.write(f"ERROR: {script} does not expose a callable main()\n")
            return 2
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1

if __name__ == "__main__":
    raise SystemExit(main())
