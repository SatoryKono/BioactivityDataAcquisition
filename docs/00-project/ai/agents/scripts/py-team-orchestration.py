#!/usr/bin/env python3
"""Thin facade for the canonical terminology linter implementation.

Canonical script:
- src/tools/scripts/engineering/qa/lint_terminology.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _canonical_script_path() -> Path:
    current = Path(__file__).resolve()
    repo_root = next(
        (
            parent
            for parent in current.parents
            if (parent / "src" / "tools" / "scripts" / "lint_terminology.py").exists()
        ),
        current.parents[0],
    )
    return repo_root / "src" / "tools" / "scripts" / "lint_terminology.py"


def main(argv: list[str] | None = None) -> int:
    from scripts.engineering.common.repo_paths import ensure_safe_cli_argv

    script = _canonical_script_path()
    args = sys.argv[1:] if argv is None else argv
    cmd = ensure_safe_cli_argv([sys.executable, str(script), *[str(a) for a in args]])
    result = subprocess.run(  # NOSONAR - argv via ensure_safe_cli_argv
        cmd, check=False
    )
    return int(result.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
