#!/usr/bin/env python3
"""Unified entry point for Codex setup/check scripts.

Usage:
    python -m scripts.ai.codex <command> [args...]
    python -m scripts.ai.codex --help

Commands:
    setup-mcp       Configure Codex/Copilot MCP integration
    setup-agents    Sync Codex agents into CODEX_HOME
    setup-skills    Sync Codex skills into CODEX_HOME
    check-skills    Validate the canonical AI skills docs layout
    check-mirror    Verify/sync docs skill mirror from .codex/skills
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PYTHON_COMMANDS: dict[str, str] = {
    "setup-mcp": "setup_mcp.py",
}

SHELL_COMMANDS: dict[str, str] = {
    "setup-agents": "setup_agents.sh",
    "setup-skills": "setup_skills.sh",
    "check-skills": "check_skills_layout.sh",
    "check-mirror": "check_skills_mirror.sh",
}

_DIR = Path(__file__).parent


def _run_python(script_name: str, argv: list[str]) -> int:
    return subprocess.run(
        [sys.executable, str(_DIR / script_name), *argv],
        check=False,
    ).returncode


def _run_shell(script_name: str, argv: list[str]) -> int:
    return subprocess.run(
        ["bash", str(_DIR / script_name), *argv],
        check=False,
    ).returncode


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args or args[0] in {"-h", "--help"}:
        print(__doc__ or "", end="")
        return 0

    command, rest = args[0], args[1:]
    if command in PYTHON_COMMANDS:
        return _run_python(PYTHON_COMMANDS[command], rest)
    if command in SHELL_COMMANDS:
        return _run_shell(SHELL_COMMANDS[command], rest)

    available = sorted([*PYTHON_COMMANDS, *SHELL_COMMANDS])
    print(f"Unknown command: {command}", file=sys.stderr)
    print(f"Available: {', '.join(available)}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
