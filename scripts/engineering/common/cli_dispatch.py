#!/usr/bin/env python3
"""Shared CLI dispatch helpers for repository script routers."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class CommandSpec:
    """Describe how a router command should be executed."""

    runner: str
    target: str
    prefix_args: tuple[str, ...] = ()


def module_command(module_name: str, *prefix_args: str) -> CommandSpec:
    """Dispatch to a Python module via ``python -m``."""
    return CommandSpec("module", module_name, tuple(prefix_args))


def python_command(script_name: str, *prefix_args: str) -> CommandSpec:
    """Dispatch to a Python script relative to the router directory."""
    return CommandSpec("python", script_name, tuple(prefix_args))


def shell_command(script_name: str, *prefix_args: str) -> CommandSpec:
    """Dispatch to a shell script relative to the router directory."""
    return CommandSpec("shell", script_name, tuple(prefix_args))


def run_command(
    spec: CommandSpec,
    argv: list[str],
    *,
    base_dir: Path | None = None,
) -> int:
    """Execute a command spec and return its process exit code."""
    command: list[str]

    if spec.runner == "module":
        command = [sys.executable, "-m", spec.target, *spec.prefix_args, *argv]
    elif spec.runner == "python":
        if base_dir is None:
            raise ValueError("base_dir is required for python command specs")
        command = [
            sys.executable,
            str((base_dir / spec.target).resolve()),
            *spec.prefix_args,
            *argv,
        ]
    elif spec.runner == "shell":
        if base_dir is None:
            raise ValueError("base_dir is required for shell command specs")
        command = [
            "bash",
            str((base_dir / spec.target).resolve()),
            *spec.prefix_args,
            *argv,
        ]
    else:  # pragma: no cover - defensive guard for invalid local usage
        raise ValueError(f"Unsupported command runner: {spec.runner}")

    return subprocess.run(command, check=False).returncode


def print_help(help_text: str) -> None:
    """Print router help text without adding extra newlines."""
    print(help_text, end="")


def print_unknown_command(
    command_name: str,
    available: Mapping[str, CommandSpec],
    *,
    extra_available: tuple[str, ...] = (),
    sort_available: bool = False,
) -> int:
    """Print a consistent unknown-command message and return exit code 2."""
    names = [*available.keys(), *extra_available]
    if sort_available:
        names = sorted(names)
    print(f"Unknown command: {command_name}", file=sys.stderr)
    print(f"Available: {', '.join(names)}", file=sys.stderr)
    return 2


def dispatch_cli(
    argv: list[str] | None,
    *,
    help_text: str,
    commands: Mapping[str, CommandSpec],
    base_dir: Path | None = None,
    extra_available: tuple[str, ...] = (),
    sort_available: bool = False,
) -> int:
    """Run a standard router main function."""
    args = argv if argv is not None else sys.argv[1:]

    if not args or args[0] in {"--help", "-h"}:
        print_help(help_text)
        return 0

    command_name, rest = args[0], args[1:]
    spec = commands.get(command_name)
    if spec is None:
        return print_unknown_command(
            command_name,
            commands,
            extra_available=extra_available,
            sort_available=sort_available,
        )

    return run_command(spec, rest, base_dir=base_dir)
