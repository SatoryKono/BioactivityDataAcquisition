#!/usr/bin/env python3
"""Unified entry point for AI operational scripts.

Usage:
    python -m scripts.ai <surface> [args...]
    python -m scripts.ai --help

Surfaces:
    codex    Codex setup/check tooling
    mcp      MCP operational tooling
    vibe     Vibe launch tooling
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_DIR = Path(__file__).parent


def _codex_command(rest: list[str]) -> list[str]:
    if os.name == "nt":
        launcher = _DIR / "codex" / "run-codex.ps1"
        return [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(launcher),
            *rest,
        ]
    return ["bash", str((_DIR / "codex" / "run-codex.sh").resolve()), *rest]


def _module_command(surface: str, rest: list[str]) -> list[str]:
    return [sys.executable, "-m", f"scripts.ai.{surface}", *rest]


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args or args[0] in {"-h", "--help"}:
        print(__doc__ or "", end="")
        return 0

    surface, rest = args[0], args[1:]
    if surface not in MODULES:
        available = ", ".join(sorted(MODULES))
        print(f"Unknown surface: {surface}", file=sys.stderr)
        print(f"Available: {available}", file=sys.stderr)
        return 2

    if surface == "codex":
        command = _codex_command(rest)
    else:
        command = _module_command(surface, rest)

    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
