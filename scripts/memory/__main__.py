#!/usr/bin/env python3
"""Unified entry point for scripts/memory commands.

Usage:
    python -m scripts.memory <command> [args...]
    python -m scripts.memory --help

Commands:
    sync        Build and optionally sync the deterministic Neo4j repo graph
    query       Query deterministic Neo4j memory ownership, neighbors, and analysis shortcuts
    smoke-mcp   Run a framed stdio smoke check against the neo4j-memory MCP wrapper
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

COMMANDS: dict[str, str] = {
    "sync": "sync.py",
    "query": "query.py",
    "smoke-mcp": "mcp_smoke.py",
}

_DIR = Path(__file__).parent


def _run_script(name: str, argv: list[str]) -> int:
    script = _DIR / name
    result = subprocess.run([sys.executable, str(script), *argv], check=False)
    return result.returncode


def _print_help() -> None:
    print(__doc__ or "", end="")


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]

    if not args or args[0] in ("--help", "-h"):
        _print_help()
        return 0

    cmd, rest = args[0], args[1:]
    if cmd in COMMANDS:
        return _run_script(COMMANDS[cmd], rest)

    print(f"Unknown command: {cmd}", file=sys.stderr)
    print(f"Available: {', '.join(sorted(COMMANDS))}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
