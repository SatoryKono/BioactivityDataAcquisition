#!/usr/bin/env python3
"""Unified entry point for scripts/engineering/baselines/ commands.

Usage:
    python -m scripts.engineering.baselines <command> [args...]
    python -m scripts.engineering.baselines --help

Commands:
    dq-baseline    Update Data Quality baseline metrics
"""

from pathlib import Path

from scripts._command_dispatch import dispatch_script_command

COMMANDS: dict[str, str] = {"dq-baseline": "dq_baseline_update.py"}
_DIR = Path(__file__).parent


def main(argv: list[str] | None = None) -> int:
    return dispatch_script_command(
        doc=__doc__,
        commands=COMMANDS,
        base_dir=_DIR,
        argv=argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
