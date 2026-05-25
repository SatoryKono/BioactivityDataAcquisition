#!/usr/bin/env python3
"""Shared CLI dispatch helpers for repository script routers."""

from __future__ import annotations

import importlib
import inspect
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


def _run_module_command_in_process(spec: CommandSpec, argv: list[str]) -> int:
    """Run a module command in-process to avoid nested subprocess transport hangs."""
    module = importlib.import_module(spec.target)
    main = getattr(module, "main", None)
    if not callable(main):
        raise AttributeError(f"{spec.target} does not expose a callable main()")

    forwarded_argv = [*spec.prefix_args, *argv]
    original_argv = sys.argv
    try:
        sys.argv = [spec.target, *forwarded_argv]
        try:
            parameter_count = len(inspect.signature(main).parameters)
        except (TypeError, ValueError):
            parameter_count = 0

        result = main(forwarded_argv) if parameter_count else main()
    except SystemExit as exc:
        code = exc.code
        if code is None:
            return 0
        if isinstance(code, int):
            return code
        print(code, file=sys.stderr)
        return 1
    finally:
        sys.argv = original_argv

    return 0 if result is None else int(result)


def run_command(
    spec: CommandSpec,
    argv: list[str],
    *,
    base_dir: Path | None = None,
) -> int:
    """Execute a command spec and return its process exit code."""
    command: list[str]

    if spec.runner == "module":
        return _run_module_command_in_process(spec, argv)
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
