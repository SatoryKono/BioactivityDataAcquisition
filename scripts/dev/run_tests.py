#!/usr/bin/env python3
"""Canonical test runner backend for BioETL developer wrappers.

Public wrappers:
- scripts/dev/run_tests.sh
- scripts/dev/run_tests.ps1
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CommandSpec:
    """CLI command mapping to pytest arguments."""

    label: str
    pytest_args: list[str]


COMMANDS: dict[str, CommandSpec] = {
    "all": CommandSpec("All Tests", ["tests/", "-x", "-q"]),
    "unit": CommandSpec("Unit Tests", ["tests/unit/", "-x", "-q"]),
    "arch": CommandSpec("Architecture Tests", ["tests/architecture/", "-v"]),
    "integration": CommandSpec("Integration Tests", ["tests/integration/", "-x", "-q"]),
    "contract": CommandSpec("Contract Tests", ["tests/contract/", "-v"]),
    "smoke": CommandSpec("Smoke Tests", ["tests/smoke/", "-v"]),
    "security": CommandSpec("Security Tests", ["tests/security/", "-v"]),
    "cov": CommandSpec(
        "Tests + Coverage",
        [
            "tests/",
            "--cov=src/bioetl",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-fail-under=85",
            "-q",
        ],
    ),
    "parallel": CommandSpec("All Tests (parallel)", ["tests/", "-n", "auto", "-q"]),
    "failed": CommandSpec("Re-run Failed", ["tests/", "--lf", "-x", "-v"]),
}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _print_info(msg: str) -> None:
    print(f"[INFO] {msg}")


def _print_ok(msg: str) -> None:
    print(f"[OK] {msg}")


def _print_fail(msg: str) -> None:
    print(f"[FAIL] {msg}")


def _usage() -> str:
    return """BioETL Test Runner

Usage:
  python scripts/dev/run_tests.py <command> [pytest-args...]

Commands:
  all           Run all tests (stop on first failure)
  unit          Unit tests only (tests/unit/)
  arch          Architecture tests (tests/architecture/)
  integration   Integration tests (tests/integration/)
  contract      Contract tests (tests/contract/)
  contract-live Contract tests with live APIs + network enabled
  smoke         Smoke tests (tests/smoke/)
  security      Security tests (tests/security/)
  cov           All tests with coverage report (fail-under=85%)
  quick         Unit + smoke (fast feedback loop)
  parallel      All tests via pytest-xdist (-n auto)
  marker <m>    Run tests by marker, e.g.: marker slow
  failed        Re-run only failed tests from last run
  file <path>   Run a specific test file
  help          Show this message
"""


def _run_pytest(label: str, pytest_args: list[str], extra: list[str]) -> int:
    cmd = [sys.executable, "-m", "pytest", *pytest_args, *extra]
    _print_info(f"Running: {label}")
    _print_info(f"Command: {' '.join(cmd)}")
    completed = subprocess.run(cmd, cwd=_project_root(), check=False)
    if completed.returncode == 0:
        _print_ok(f"{label} passed")
        if label == "Tests + Coverage":
            _print_ok("HTML report: htmlcov/index.html")
        return 0

    _print_fail(f"{label} failed")
    return completed.returncode


def _run_contract_live(extra: list[str]) -> int:
    env = os.environ.copy()
    env["BIOETL_LIVE_API_TESTS"] = "true"
    env["BIOETL_NETWORK_TESTS"] = "true"
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/contract/",
        "--network",
        "-v",
        *extra,
    ]
    _print_info("Running: Contract Tests (live APIs + network)")
    _print_info(f"Command: {' '.join(cmd)}")
    completed = subprocess.run(cmd, cwd=_project_root(), env=env, check=False)
    if completed.returncode == 0:
        _print_ok("Contract Tests (live) passed")
        return 0

    _print_fail("Contract Tests (live) failed")
    return completed.returncode


def _run_marker(args: list[str]) -> int:
    if not args:
        _print_fail("Usage: marker <marker-name> [pytest-args...]")
        return 1
    marker = args[0]
    extra = args[1:]
    return _run_pytest(f"Marker: {marker}", ["tests/", "-m", marker, "-v"], extra)


def _run_file(args: list[str]) -> int:
    if not args:
        _print_fail("Usage: file <path> [pytest-args...]")
        return 1
    file_path = args[0]
    extra = args[1:]
    return _run_pytest(f"File: {file_path}", [file_path, "-v"], extra)


def _run_quick(extra: list[str]) -> int:
    _print_info("Quick check: unit + smoke")
    rc = _run_pytest("Unit Tests", ["tests/unit/", "-x", "-q"], extra)
    if rc != 0:
        return rc
    return _run_pytest("Smoke Tests", ["tests/smoke/", "-x", "-q"], extra)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"help", "--help", "-h"}:
        print(_usage())
        return 0

    command = args[0]
    tail = args[1:]

    if command == "contract-live":
        return _run_contract_live(tail)
    if command == "marker":
        return _run_marker(tail)
    if command == "file":
        return _run_file(tail)
    if command == "quick":
        return _run_quick(tail)

    spec = COMMANDS.get(command)
    if spec is None:
        _print_fail(f"Unknown command: {command}")
        print(_usage())
        return 1
    return _run_pytest(spec.label, spec.pytest_args, tail)


if __name__ == "__main__":
    raise SystemExit(main())
