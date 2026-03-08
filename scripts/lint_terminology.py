#!/usr/bin/env python3
"""Thin facade for the canonical terminology linter implementation.

Canonical script:
- src/tools/scripts/lint_terminology.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _canonical_script_path() -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    return repo_root / "src" / "tools" / "scripts" / "lint_terminology.py"


def main(argv: list[str] | None = None) -> int:
    script = _canonical_script_path()
    args = sys.argv[1:] if argv is None else argv
    cmd = [sys.executable, str(script), *args]
    result = subprocess.run(cmd, check=False)
    return int(result.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
