#!/usr/bin/env python3
"""Unified entry point for MCP operational scripts.

Usage:
    python -m scripts.ai.mcp <command> [args...]
    python -m scripts.ai.mcp --help

Commands:
    smoke-sonarqube     Run the readiness-aware SonarQube MCP smoke test
    smoke-neo4j-memory  Run the framed stdio Neo4j memory MCP smoke test
    check               Run the general MCP registration and wrapper audit
    check-neo4j-memory  Run the Neo4j memory MCP + backend verification
    test-env-loading    Run the repo env loader smoke check for MCP wrappers
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PYTHON_COMMANDS: dict[str, str] = {
    "smoke-sonarqube": "sonarqube_mcp_smoke.py",
    "smoke-neo4j-memory": "neo4j_memory_mcp_smoke.py",
}

SHELL_COMMANDS: dict[str, str] = {
    "check": "check.sh",
    "check-neo4j-memory": "check_neo4j_memory.sh",
    "test-env-loading": "test_env_loading.sh",
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
