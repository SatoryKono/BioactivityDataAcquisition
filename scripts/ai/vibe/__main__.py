#!/usr/bin/env python3
"""Unified entry point for Vibe launch tooling.

Usage:
    python -m scripts.ai.vibe [args...]
    python -m scripts.ai.vibe --help
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_DIR = Path(__file__).parent


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    return subprocess.run(
        ["bash", str(_DIR / "launch.sh"), *args],
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
