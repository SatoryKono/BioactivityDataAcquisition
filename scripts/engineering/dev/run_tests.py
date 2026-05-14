#!/usr/bin/env python3
"""Canonical test runner backend for BioETL developer wrappers.

Public wrappers:
- scripts/engineering/dev/run_tests.sh
- scripts/engineering/dev/run_tests.ps1
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CommandSpec:
    """CLI command mapping to pytest arguments."""

    label: str
    pytest_args: list[str]


TESTS_ROOT = "tests/"
UNIT_TESTS_ROOT = "tests/unit/"
SHORT_TRACEBACK = "--tb=short"


COMMANDS: dict[str, CommandSpec] = {
    "all": CommandSpec("All Tests", [TESTS_ROOT, "-x", "-q"]),
    "unit": CommandSpec("Unit Tests", [UNIT_TESTS_ROOT, "-x", "-q"]),
    "arch": CommandSpec("Architecture Tests", ["tests/architecture/", "-v"]),
    "integration": CommandSpec("Integration Tests", ["tests/integration/", "-x", "-q"]),
    "contract": CommandSpec("Contract Tests", ["tests/contract/", "-v"]),
    "smoke": CommandSpec("Smoke Tests", ["tests/smoke/", "-v"]),
    "security": CommandSpec("Security Tests", ["tests/security/", "-v"]),
    "memory": CommandSpec(
        "Neo4j Memory Tests",
        ["tests/smoke/test_neo4j_memory_mcp_smoke.py", "-m", "memory", "-q"],
    ),
    "cov": CommandSpec(
        "Tests + Coverage",
        [
            TESTS_ROOT,
            "-m",
            "not memory",
            "--cov=src/bioetl",
            "--cov-report=html:reports/coverage/htmlcov",
            "--cov-report=term-missing",
            "--cov-fail-under=85",
            "-q",
        ],
    ),
    "parallel": CommandSpec("All Tests (parallel)", [TESTS_ROOT, "-n", "auto", "-q"]),
    "failed": CommandSpec("Re-run Failed", [TESTS_ROOT, "--lf", "-x", "-v"]),
}
UNIT_QUICK_ARGS = [UNIT_TESTS_ROOT, "-x", "-q"]
SMOKE_QUICK_ARGS = ["tests/smoke/", "-x", "-q"]
FAST_UNIT_FALLBACK_ARGS = [
    UNIT_TESTS_ROOT,
    "-m",
    "not slow and not serial",
    "-n",
    "auto",
    "--dist",
    "loadscope",
    "-q",
    SHORT_TRACEBACK,
]


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _print_info(msg: str) -> None:
    print(f"[INFO] {msg}")


def _print_ok(msg: str) -> None:
    print(f"[OK] {msg}")


def _print_fail(msg: str) -> None:
    print(f"[FAIL] {msg}")


def _usage() -> str:
    return """BioETL Test Runner

Usage:
  python scripts/engineering/dev/run_tests.py <command> [pytest-args...]

Commands:
  all           Run all tests (stop on first failure)
  unit          Unit tests only (tests/unit/)
  arch          Architecture tests (tests/architecture/)
  integration   Integration tests (tests/integration/)
  contract      Contract tests (tests/contract/)
  contract-live Contract tests with live APIs + network enabled
  smoke         Smoke tests (tests/smoke/)
  security      Security tests (tests/security/)
  memory        Dedicated Neo4j project-memory and MCP tests
  cov           All non-memory tests with coverage report (fail-under=85%)
  quick         Unit + smoke (fast feedback loop)
  parallel      All tests via pytest-xdist (-n auto)
  changed       Run tests related to files changed vs a base branch (default: main)
  marker <m>    Run tests by marker, e.g.: marker slow
  failed        Re-run only failed tests from last run
  file <path>   Run a specific test file
  help          Show this message
"""


def _run_pytest(
    label: str,
    pytest_args: list[str],
    extra: list[str],
    env_overrides: dict[str, str] | None = None,
) -> int:
    cmd = [sys.executable, "-m", "pytest", *pytest_args, *extra]
    _print_info(f"Running: {label}")
    _print_info(f"Command: {' '.join(cmd)}")
    env = os.environ.copy()
    if env_overrides is not None:
        env.update(env_overrides)
    completed = subprocess.run(cmd, cwd=_project_root(), env=env, check=False)
    if completed.returncode == 0:
        _print_ok(f"{label} passed")
        if label == "Tests + Coverage":
            _print_ok("HTML report: reports/coverage/htmlcov/index.html")
        return 0

    _print_fail(f"{label} failed")
    return completed.returncode


def _run_contract_live(extra: list[str]) -> int:
    return _run_pytest(
        "Contract Tests (live APIs + network)",
        ["tests/contract/", "--network", "-v"],
        extra,
        env_overrides={
            "BIOETL_LIVE_API_TESTS": "true",
            "BIOETL_NETWORK_TESTS": "true",
        },
    )


def _run_marker(args: list[str]) -> int:
    if not args:
        _print_fail("Usage: marker <marker-name> [pytest-args...]")
        return 1
    marker = args[0]
    extra = args[1:]
    return _run_pytest(f"Marker: {marker}", [TESTS_ROOT, "-m", marker, "-v"], extra)


def _run_file(args: list[str]) -> int:
    if not args:
        _print_fail("Usage: file <path> [pytest-args...]")
        return 1
    file_path = args[0]
    extra = args[1:]
    return _run_pytest(f"File: {file_path}", [file_path, "-v"], extra)


def _run_quick(extra: list[str]) -> int:
    _print_info("Quick check: unit + smoke")
    rc = _run_pytest("Unit Tests", UNIT_QUICK_ARGS, extra)
    if rc != 0:
        return rc
    return _run_pytest("Smoke Tests", SMOKE_QUICK_ARGS, extra)


def _git_changed_python_files(base_branch: str, prefix: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base_branch}...HEAD"],
        cwd=_project_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        _print_fail(
            f"Could not diff against base branch '{base_branch}'. "
            "Falling back to fast unit suite."
        )
        return []
    return [
        line
        for line in result.stdout.splitlines()
        if line.startswith(prefix) and line.endswith(".py")
    ]


def _build_changed_test_keyword_expression(changed_src: list[str]) -> str:
    modules = sorted({Path(path).stem for path in changed_src})
    return " or ".join(modules)


def _run_changed(args: list[str]) -> int:
    base_branch = "main"
    extra = args
    if args and not args[0].startswith("-"):
        base_branch = args[0]
        extra = args[1:]

    env_overrides = {"HYPOTHESIS_PROFILE": "fast"}
    changed_src = _git_changed_python_files(base_branch, "src/bioetl")
    changed_tests = _git_changed_python_files(base_branch, "tests/")

    if not changed_src:
        if not changed_tests:
            _print_info(
                f"No changed Python files found vs '{base_branch}'. "
                "Running fast unit fallback."
            )
            return _run_pytest(
                "Changed fallback: unit tests",
                FAST_UNIT_FALLBACK_ARGS,
                extra,
                env_overrides=env_overrides,
            )

        _print_info("Only test files changed. Running changed test files directly.")
        return _run_pytest(
            "Changed test files",
            [*changed_tests, "-v", SHORT_TRACEBACK],
            extra,
            env_overrides=env_overrides,
        )

    _print_info("Changed source files:")
    for path in changed_src:
        print(f"  {path}")

    keyword_expression = _build_changed_test_keyword_expression(changed_src)
    _print_info(f"Running tests matching: {keyword_expression}")
    rc = _run_pytest(
        "Changed-source keyword tests",
        [
            TESTS_ROOT,
            "-k",
            keyword_expression,
            "-n",
            "auto",
            "--dist",
            "loadscope",
            "-v",
            SHORT_TRACEBACK,
            "--ignore=tests/e2e/",
            "--ignore=tests/benchmarks/",
        ],
        extra,
        env_overrides=env_overrides,
    )
    if rc == 0:
        return 0

    _print_info("Keyword-selected changed tests failed or matched nothing.")
    return _run_pytest(
        "Changed fallback: unit tests",
        FAST_UNIT_FALLBACK_ARGS,
        extra,
        env_overrides=env_overrides,
    )


def _custom_command_handlers() -> dict[str, Callable[[list[str]], int]]:
    return {
        "contract-live": _run_contract_live,
        "marker": _run_marker,
        "file": _run_file,
        "quick": _run_quick,
        "changed": _run_changed,
    }


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"help", "--help", "-h"}:
        print(_usage())
        return 0

    command = args[0]
    tail = args[1:]

    custom_handler = _custom_command_handlers().get(command)
    if custom_handler is not None:
        return custom_handler(tail)

    spec = COMMANDS.get(command)
    if spec is None:
        _print_fail(f"Unknown command: {command}")
        print(_usage())
        return 1
    return _run_pytest(spec.label, spec.pytest_args, tail)


if __name__ == "__main__":
    raise SystemExit(main())
