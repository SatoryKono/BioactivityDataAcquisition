"""Shared command dispatcher for script package entrypoints."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path


def _print_available_commands(commands: Mapping[str, str]) -> None:
    print(f"Available: {', '.join(commands)}", file=sys.stderr)


def _run_script(base_dir: Path, script_name: str, argv: Sequence[str]) -> int:
    result = subprocess.run(
        [sys.executable, str(base_dir / script_name), *argv],
        check=False,
    )
    return result.returncode


def dispatch_script_command(
    *,
    doc: str | None,
    commands: Mapping[str, str],
    base_dir: Path,
    argv: list[str] | None = None,
) -> int:
    """Dispatch one ``python -m scripts.<package>`` command."""
    args = argv if argv is not None else sys.argv[1:]
    if not args or args[0] in ("--help", "-h"):
        print(doc or "", end="")
        return 0

    command_name, rest = args[0], args[1:]
    script_name = commands.get(command_name)
    if script_name is None:
        print(f"Unknown command: {command_name}", file=sys.stderr)
        _print_available_commands(commands)
        return 2

    return _run_script(base_dir, script_name, rest)
