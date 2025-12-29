"""Architecture test: no logging.getLogger in infrastructure layer.

REQ-ARCH-033: Infrastructure layer components MUST use LoggerPort
for structured logging to guarantee run_id inclusion in all log entries.

Components that use logging.getLogger() instead of LoggerPort may produce
logs without proper context (run_id, pipeline_name), making debugging
and log correlation difficult.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

INFRASTRUCTURE_DIR = Path("src/bioetl/infrastructure")

# Allowed exemptions (should be empty for new code)
# logging.py is allowed since it creates the structlog-based logger implementation
ALLOWED_FILES: set[str] = {
    "bioetl/infrastructure/observability/logging.py",  # Implements LoggerPort
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
        # Skip allowed files (normalize path separators)
        rel_path_str = str(rel_path).replace("\\", "/")
        if rel_path_str in allowed:
            continue

        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            continue

        for node in ast.walk(tree):
            # Check for: import logging
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "logging":
                        # Check if logging.getLogger is called later in the file
                        if "logging.getLogger" in source:
                            violations.append(
                                f"{rel_path}:{node.lineno}: import logging with getLogger usage"
                            )

            # Check for: from logging import getLogger
            elif isinstance(node, ast.ImportFrom):
                if node.module == "logging":
                    for alias in node.names:
                        if alias.name == "getLogger":
                            violations.append(
                                f"{rel_path}:{node.lineno}: from logging import getLogger"
                            )

    return violations


def _check_getlogger_calls(directory: Path, allowed: set[str] | None = None) -> list[str]:
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
        rel_path_str = str(rel_path).replace("\\", "/")
        if rel_path_str in allowed:
            continue

        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check for logging.getLogger()
                if isinstance(node.func, ast.Attribute):
                    if (
                        isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "logging"
                        and node.func.attr == "getLogger"
                    ):
                        violations.append(
                            f"{rel_path}:{node.lineno}: logging.getLogger() call"
                        )
                # Check for direct getLogger() call
                elif isinstance(node.func, ast.Name) and node.func.id == "getLogger":
                    violations.append(
                        f"{rel_path}:{node.lineno}: getLogger() call"
                    )

    return violations


class TestNoLoggingGetLoggerInInfrastructure:
    """Test that infrastructure layer does not use logging.getLogger."""

    def test_no_logging_getlogger_imports(self) -> None:
        """Infrastructure layer MUST NOT use logging.getLogger.

        REQ-ARCH-033: Use LoggerPort injection instead of logging.getLogger()
        to ensure all logs include run_id and other context fields.
        """
        violations = _check_logging_getlogger_imports(
            INFRASTRUCTURE_DIR, ALLOWED_FILES
        )

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
    check_fn: callable, check_name: str
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
