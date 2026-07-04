#!/usr/bin/env python3
"""Unified entry point for scripts/engineering/dev/ commands.

Usage:
    python -m scripts.engineering.dev <command> [args...]
    python -m scripts.engineering.dev --help

Commands:
    setup              Legacy compatibility command; exits with guidance
    setup --quick      Legacy quick-mode command; exits with guidance
    setup --ci         Legacy CI-mode command; exits with guidance
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
    module_command,
    print_help,
    print_unknown_command,
    python_command,
    shell_command,
)

_PYTHON_COMMANDS = {
    "install-deps": "install_deps.py",
    "migrate-deprecated-names": "python/migrate_deprecated_names.py",
    "probe-quality": "quality_gate_probe.py",
    "run-tests": "run_tests.py",
    "mock-metrics": "metrics_mock_server.py",
    "mock-quarantine": "quarantine_explorer_mock_server.py",
}
COMMAND_SPECS = {
    name: python_command(script) for name, script in _PYTHON_COMMANDS.items()
}
COMMAND_SPECS["setup-mcp"] = module_command("scripts.ai.codex.setup_mcp")

SHELL_COMMANDS = {
    "pretest-guardrails": "pretest_guardrails.sh",
    "pytest-sharded": "run_pytest_sharded.sh",
}
SHELL_COMMAND_SPECS = {
    name: shell_command(script) for name, script in SHELL_COMMANDS.items()
}

_DIR = Path(__file__).parent


def _handle_legacy_setup_command(rest: list[str]) -> int:
    """Hard-fail the retired legacy setup command with actionable guidance."""
    if rest and rest[0] not in {"--quick", "--ci"}:
        return print_unknown_command(
            "setup",
            {**COMMAND_SPECS, **SHELL_COMMAND_SPECS},
            extra_available=("test-changed",),
            sort_available=True,
        )
    print(
        "The legacy `python -m scripts.engineering.dev setup` command is retired. "
        "Use `make install` for project bootstrap or "
        "`python -m scripts.engineering.dev setup-mcp` for MCP setup.",
        file=sys.stderr,
    )
    return 2


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]

    if not args or args[0] in ("--help", "-h"):
        print_help(__doc__ or "")
        return 0

    cmd, rest = args[0], args[1:]

    if cmd == "setup":
        return _handle_legacy_setup_command(rest)

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
