#!/usr/bin/env python3
"""Unified entry point for scripts/engineering/dev/ commands.

Usage:
    python -m scripts.engineering.dev <command> [args...]
    python -m scripts.engineering.dev --help

Commands:
    setup              Legacy compatibility setup facade (shell)
    setup --quick      Legacy quick-mode guidance facade (shell)
    setup --ci         Legacy CI-mode guidance facade (shell)
    pretest-guardrails Run repository/docs/architecture preflight (shell)
    pytest-sharded     Run the recommended path-based pytest shards (shell)
    install-deps       Install project dependencies
    probe-quality      Measure narrow pytest/mypy startup and timeout behavior
    run-tests          Run tests (Python)
    mock-metrics       Start mock metrics server
    mock-quarantine    Start mock quarantine explorer API server
    test-changed       Run tests for changed files only (Python backend)
    setup-mcp          Setup Copilot/Codex MCP integration
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

COMMANDS: dict[str, str] = {
    "install-deps": "install_deps.py",
    "probe-quality": "quality_gate_probe.py",
    "run-tests": "run_tests.py",
    "mock-metrics": "metrics_mock_server.py",
    "mock-quarantine": "quarantine_explorer_mock_server.py",
    "setup-mcp": "setup_copilot_codex_mcp.py",
}

SHELL_COMMANDS: dict[str, str] = {
    "setup": "dev_setup.sh",
    "pretest-guardrails": "pretest_guardrails.sh",
    "pytest-sharded": "run_pytest_sharded.sh",
}

_DIR = Path(__file__).parent


def _run_script(name: str, argv: list[str]) -> int:
    script = _DIR / name
    result = subprocess.run([sys.executable, str(script), *argv], check=False)
    return result.returncode


def _run_shell(name: str, argv: list[str]) -> int:
    script = _DIR / name
    result = subprocess.run(["bash", str(script), *argv], check=False)
    return result.returncode


def _print_help() -> None:
    print(__doc__ or "", end="")


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]

    if not args or args[0] in ("--help", "-h"):
        _print_help()
        return 0

    cmd, rest = args[0], args[1:]

    if cmd in COMMANDS:
        return _run_script(COMMANDS[cmd], rest)

    if cmd == "test-changed":
        return _run_script("run_tests.py", ["changed", *rest])

    if cmd in SHELL_COMMANDS:
        return _run_shell(SHELL_COMMANDS[cmd], rest)

    all_cmds = sorted([*COMMANDS, *SHELL_COMMANDS])
    print(f"Unknown command: {cmd}", file=sys.stderr)
    print(f"Available: {', '.join(all_cmds)}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
