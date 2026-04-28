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

from pathlib import Path

from scripts.engineering.common.cli_dispatch import dispatch_cli, python_command

COMMANDS = {
    "cleanup": "cleanup_project.py",
    "cleanup-audit": "cleanup_consolidate.py",
    "audit-structure": "audit_structure.py",
    "ast-inventory": "ast_inventory.py",
    "debug-pandera": "debug_pandera.py",
    "debug-storage": "debug_storage_health.py",
    "inspect-vcr": "_tmp_inspect_vcr.py",
}
COMMAND_SPECS = {name: python_command(script) for name, script in COMMANDS.items()}

_DIR = Path(__file__).parent


def main(argv: list[str] | None = None) -> int:
    return dispatch_cli(
        argv,
        help_text=__doc__ or "",
        commands=COMMAND_SPECS,
        base_dir=_DIR,
    )


if __name__ == "__main__":
    raise SystemExit(main())
