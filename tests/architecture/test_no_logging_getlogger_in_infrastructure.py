# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Architecture test: no logging.getLogger in infrastructure layer.

REQ-ARCH-033: Infrastructure layer components MUST use LoggerPort
for structured logging to guarantee run_id inclusion in all log entries.

Components that use logging.getLogger() instead of LoggerPort may produce
logs without proper context (run_id, pipeline_name), making debugging
and log correlation difficult.
"""

from __future__ import annotations

import ast
from collections.abc import Callable
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

INFRASTRUCTURE_DIR = Path("src/bioetl/infrastructure")

# Allowed exemptions (should be empty for new code)
# logging.py is allowed since it creates the structlog-based logger implementation
ALLOWED_FILES: set[str] = {
    "bioetl/infrastructure/observability/logging.py",  # Implements LoggerPort
    "bioetl/infrastructure/observability/logging_config.py",  # Central stdlib/structlog bootstrap
}


def _check_logging_getlogger_imports(
    directory: Path, allowed: set[str] | None = None
) -> list[str]:
    """Check for logging.getLogger usage in a directory.

    Args:
        directory: Directory to scan for Python files.
        allowed: Set of file paths to allow.

    Returns:
        List of violation messages with file path and line number.
    """
    if allowed is None:
        allowed = set()

    violations = []

    if not directory.exists():
        return violations

    for py_file in directory.rglob("*.py"):
        rel_path = py_file.relative_to(Path("src"))
        if _normalize_rel_path(rel_path) in allowed:
            continue

        parsed = _read_source_and_ast(py_file)
        if parsed is None:
            continue
        source, tree = parsed

        violations.extend(
            _iter_logging_import_violations(tree, rel_path, source=source)
        )

    return violations


def _check_getlogger_calls(
    directory: Path, allowed: set[str] | None = None
) -> list[str]:
    """Check for logging.getLogger() or getLogger() calls in source code.

    Args:
        directory: Directory to scan for Python files.
        allowed: Set of file paths to allow.

    Returns:
        List of violation messages with file path and line number.
    """
    if allowed is None:
        allowed = set()

    violations = []

    if not directory.exists():
        return violations

    for py_file in directory.rglob("*.py"):
        rel_path = py_file.relative_to(Path("src"))
        if _normalize_rel_path(rel_path) in allowed:
            continue

        parsed = _read_source_and_ast(py_file)
        if parsed is None:
            continue
        _, tree = parsed

        violations.extend(_iter_getlogger_call_violations(tree, rel_path))

    return violations


def _normalize_rel_path(rel_path: Path) -> str:
    return str(rel_path).replace("\\", "/")


def _read_source_and_ast(py_file: Path) -> tuple[str, ast.Module] | None:
    try:
        source = py_file.read_text(encoding="utf-8")
        return source, ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return None


def _iter_logging_import_violations(
    tree: ast.Module,
    rel_path: Path,
    *,
    source: str,
) -> list[str]:
    violations: list[str] = []
    has_logging_getlogger_usage = "logging.getLogger" in source
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            violations.extend(
                f"{rel_path}:{node.lineno}: import logging with getLogger usage"
                for alias in node.names
                if alias.name == "logging" and has_logging_getlogger_usage
            )
            continue
        if isinstance(node, ast.ImportFrom) and node.module == "logging":
            violations.extend(
                f"{rel_path}:{node.lineno}: from logging import getLogger"
                for alias in node.names
                if alias.name == "getLogger"
            )
    return violations


def _iter_getlogger_call_violations(tree: ast.Module, rel_path: Path) -> list[str]:
    violations: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        message = _get_getlogger_call_message(node)
        if message:
            violations.append(f"{rel_path}:{node.lineno}: {message}")
    return violations


def _get_getlogger_call_message(node: ast.Call) -> str | None:
    if _is_logging_getlogger_call(node):
        return "logging.getLogger() call"
    if isinstance(node.func, ast.Name) and node.func.id == "getLogger":
        return "getLogger() call"
    return None


def _is_logging_getlogger_call(node: ast.Call) -> bool:
    return (
        isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "logging"
        and node.func.attr == "getLogger"
    )


class TestNoLoggingGetLoggerInInfrastructure:
    """Test that infrastructure layer does not use logging.getLogger."""

    def test_no_logging_getlogger_imports(self) -> None:
        """Infrastructure layer MUST NOT use logging.getLogger.

        REQ-ARCH-033: Use LoggerPort injection instead of logging.getLogger()
        to ensure all logs include run_id and other context fields.
        """
        violations = _check_logging_getlogger_imports(INFRASTRUCTURE_DIR, ALLOWED_FILES)

        assert not violations, (
            "logging.getLogger usage found in infrastructure layer:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\nInfrastructure components MUST use LoggerPort injection."
            + "\nInject LoggerPort through constructor and use self._logger instead."
        )

    def test_no_getlogger_calls(self) -> None:
        """Infrastructure layer MUST NOT call getLogger().

        REQ-ARCH-033: All logging must go through LoggerPort for proper
        context binding (run_id, pipeline_name, etc.).
        """
        violations = _check_getlogger_calls(INFRASTRUCTURE_DIR, ALLOWED_FILES)

        assert not violations, (
            "getLogger() calls found in infrastructure layer:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\nUse LoggerPort from bioetl.domain.ports instead."
            + "\nExample: self._logger.info('event', key=value)"
        )


@pytest.mark.parametrize(
    "check_fn,check_name",
    [
        (_check_logging_getlogger_imports, "logging imports"),
        (_check_getlogger_calls, "getLogger calls"),
    ],
)
def test_no_logging_getlogger_parametrized(
    check_fn: Callable[[Path, set[str] | None], list[str]],
    check_name: str,
) -> None:
    """Parametrized test for logging.getLogger detection.

    Args:
        check_fn: Function to check for violations.
        check_name: Name of the check for error messages.
    """
    violations = check_fn(INFRASTRUCTURE_DIR, ALLOWED_FILES)

    assert not violations, (
        f"{check_name} found in infrastructure layer:\n"
        + "\n".join(f"  - {v}" for v in violations)
        + "\n\nInfrastructure MUST use LoggerPort injection."
    )
