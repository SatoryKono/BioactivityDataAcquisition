#!/usr/bin/env python3
"""Unified entry point for scripts/engineering/diagnostics/ commands.

Usage:
    python -m scripts.engineering.diagnostics <command> [args...]
    python -m scripts.engineering.diagnostics --help

Commands:
    cleanup            Clean caches, build artifacts, and temp files
    cleanup-audit      Consolidated cleanup and quality audit
    audit-structure    Validate project structure against file policy
    ast-inventory      AST-based code inventory
    debug-pandera      Debug Pandera schema validation
    debug-storage      Debug storage health checks
    inspect-vcr        Temporary VCR cassette inspector
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

COMMANDS: dict[str, str] = {
    "cleanup": "cleanup_project.py",
    "cleanup-audit": "cleanup_consolidate.py",
    "audit-structure": "audit_structure.py",
    "ast-inventory": "ast_inventory.py",
    "debug-pandera": "debug_pandera.py",
    "debug-storage": "debug_storage_health.py",
    "inspect-vcr": "_tmp_inspect_vcr.py",
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

    if cmd not in COMMANDS:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        print(f"Available: {', '.join(COMMANDS)}", file=sys.stderr)
        return 2

    return _run_script(COMMANDS[cmd], rest)


if __name__ == "__main__":
    raise SystemExit(main())
