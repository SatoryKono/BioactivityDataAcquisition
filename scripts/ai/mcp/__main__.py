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

from pathlib import Path

from scripts.engineering.common.cli_dispatch import (
    dispatch_cli,
    python_command,
    shell_command,
)

COMMAND_SPECS = {
    "smoke-sonarqube": python_command("sonarqube_mcp_smoke.py"),
    "smoke-neo4j-memory": python_command("neo4j_memory_mcp_smoke.py"),
    "check": shell_command("check.sh"),
    "check-neo4j-memory": shell_command("check_neo4j_memory.sh"),
    "test-env-loading": shell_command("test_env_loading.sh"),
}

_DIR = Path(__file__).parent


def main(argv: list[str] | None = None) -> int:
    return dispatch_cli(
        argv,
        help_text=__doc__ or "",
        commands=COMMAND_SPECS,
        base_dir=_DIR,
        sort_available=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
