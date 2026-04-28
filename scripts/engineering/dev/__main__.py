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
    migrate-deprecated-names  Rewrite deprecated import/name usage
    probe-quality      Measure narrow pytest/mypy startup and timeout behavior
    run-tests          Run tests (Python)
    mock-metrics       Start mock metrics server
    mock-quarantine    Start mock quarantine explorer API server
    test-changed       Run tests for changed files only (Python backend)
    setup-mcp          Setup Copilot/Codex MCP integration
"""

from __future__ import annotations

import sys
from pathlib import Path

from scripts.engineering.common.cli_dispatch import (
    dispatch_cli,
    print_help,
    python_command,
    shell_command,
)

COMMAND_SPECS = {
    "install-deps": "install_deps.py",
    "migrate-deprecated-names": "python/migrate_deprecated_names.py",
    "probe-quality": "quality_gate_probe.py",
    "run-tests": "run_tests.py",
    "mock-metrics": "metrics_mock_server.py",
    "mock-quarantine": "quarantine_explorer_mock_server.py",
    "setup-mcp": "setup_copilot_codex_mcp.py",
}
COMMAND_SPECS = {name: python_command(script) for name, script in COMMAND_SPECS.items()}

SHELL_COMMANDS = {
    "setup": "dev_setup.sh",
    "pretest-guardrails": "pretest_guardrails.sh",
    "pytest-sharded": "run_pytest_sharded.sh",
}
SHELL_COMMAND_SPECS = {
    name: shell_command(script) for name, script in SHELL_COMMANDS.items()
}

_DIR = Path(__file__).parent


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]

    if not args or args[0] in ("--help", "-h"):
        print_help(__doc__ or "")
        return 0

    cmd, rest = args[0], args[1:]

    if cmd in COMMAND_SPECS:
        return dispatch_cli(
            [cmd, *rest],
            help_text=__doc__ or "",
            commands=COMMAND_SPECS,
            base_dir=_DIR,
        )

    if cmd == "test-changed":
        return dispatch_cli(
            [cmd, *rest],
            help_text=__doc__ or "",
            commands={"test-changed": python_command("run_tests.py", "changed")},
            base_dir=_DIR,
        )

    if cmd in SHELL_COMMAND_SPECS:
        return dispatch_cli(
            [cmd, *rest],
            help_text=__doc__ or "",
            commands=SHELL_COMMAND_SPECS,
            base_dir=_DIR,
        )

    return dispatch_cli(
        [cmd, *rest],
        help_text=__doc__ or "",
        commands={**COMMAND_SPECS, **SHELL_COMMAND_SPECS},
        base_dir=_DIR,
        sort_available=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
