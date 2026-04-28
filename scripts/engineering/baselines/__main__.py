#!/usr/bin/env python3
"""Unified entry point for scripts/engineering/baselines/ commands.

Usage:
    python -m scripts.engineering.baselines <command> [args...]
    python -m scripts.engineering.baselines --help

Commands:
    dq-baseline    Update Data Quality baseline metrics
"""

from __future__ import annotations

from pathlib import Path

from scripts.engineering.common.cli_dispatch import dispatch_cli, python_command

COMMANDS: dict[str, str] = {"dq-baseline": "dq_baseline_update.py"}
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
