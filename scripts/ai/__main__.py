#!/usr/bin/env python3
"""Unified entry point for AI operational scripts.

Usage:
    python -m scripts.ai <surface> [args...]
    python -m scripts.ai --help

Surfaces:
    codex    Codex setup/check tooling
    mcp      MCP operational tooling
"""

from __future__ import annotations

import subprocess
import sys

MODULES: dict[str, str] = {
    "codex": "codex",
    "mcp": "mcp",
}


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

    return subprocess.run(
        [sys.executable, "-m", f"scripts.ai.{MODULES[surface]}", *rest],
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
