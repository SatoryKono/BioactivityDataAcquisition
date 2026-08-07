#!/usr/bin/env python3
"""Unified entry point for scripts/memory/ commands.

Usage:
    python -m scripts.memory <command> [args...]
    python -m scripts.memory --help

Commands:
    query    Query memory systems
    sync     Synchronize memory systems
"""

from __future__ import annotations

from scripts.engineering.common.cli_dispatch import dispatch_cli, module_command

COMMANDS = {
    "query": "scripts.memory.queries.query",
    "sync": "scripts.memory.operations.sync",
}
COMMAND_SPECS = {name: module_command(module) for name, module in COMMANDS.items()}


def main(argv: list[str] | None = None) -> int:
    return dispatch_cli(
        argv,
        help_text=__doc__,
        commands=COMMAND_SPECS,
    )


if __name__ == "__main__":
    raise SystemExit(main())
