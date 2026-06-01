"""Architecture test: f-string запрещён в logging calls.

REQ-OBS-001: Structured logging for machine parsing.
f-strings produce unstructured log messages that are hard to parse
and query in log aggregation systems.

Use structlog pattern instead:
    logger.info("event_name", key=value, another_key=another_value)
"""

from __future__ import annotations

import pytest

import ast
from pathlib import Path

pytestmark = pytest.mark.architecture

# Files where f-string in docstrings is acceptable (documentation examples)
ALLOWED_DOCSTRING_FILES: set[str] = {
    "infrastructure/observability/anomaly/__init__.py",  # Usage example in module docstring
}


class FStringLogVisitor(ast.NodeVisitor):
    """AST visitor to find f-strings in logging calls."""

    def __init__(self, filepath: Path) -> None:
        self.filepath = filepath
        self.violations: list[str] = []
        self._in_docstring = False

    def visit_Expr(self, node: ast.Expr) -> None:
        """Track docstrings to exclude them from checks."""
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            # This is a docstring
            self._in_docstring = True
            self.generic_visit(node)
            self._in_docstring = False
        else:
            self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Check logging calls for f-strings."""
        if self._in_docstring:
            self.generic_visit(node)
            return

        # Check for logger.info/warning/error/debug/exception calls
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in ("info", "warning", "error", "debug", "exception"):
                # Check if first positional arg is f-string (JoinedStr)
                if node.args and isinstance(node.args[0], ast.JoinedStr):
                    self.violations.append(
                        f"{self.filepath}:{node.lineno}: "
                        f"f-string in {node.func.attr}() call"
                    )

        self.generic_visit(node)


def test_no_fstring_in_log_calls(src_dir: Path, source_ast_cache: dict) -> None:
    """Logging MUST use structlog pattern, not f-strings.

    REQ-OBS-001: Structured logging for machine parsing.
    f-strings produce unstructured log messages that are difficult to:
    - Parse in log aggregation systems (ELK, Splunk, etc.)
    - Query by specific fields
    - Alert on specific conditions

    Correct pattern:
        logger.info("event_name", key=value, run_id=run_id)

    Incorrect pattern:
        logger.info(f"Event {key} happened for {run_id}")
    """
    violations: list[str] = []

    bioetl_dir = src_dir / "bioetl"
    for py_file, tree in source_ast_cache.items():
        if bioetl_dir not in py_file.parents and py_file != bioetl_dir:
            continue
        relative_path = py_file.relative_to(bioetl_dir)

        # Skip files where docstring examples are allowed
        if str(relative_path) in ALLOWED_DOCSTRING_FILES:
            continue

        visitor = FStringLogVisitor(py_file)
        visitor.visit(tree)
        violations.extend(visitor.violations)

    assert not violations, (
        f"f-strings found in logging calls ({len(violations)} violations):\n"
        + "\n".join(f"  - {v}" for v in violations)
        + "\n\n"
        + "Use structlog pattern instead:\n"
        + '  logger.info("event_name", key=value, run_id=run_id)\n'
        + "\n"
        + "See docs/02-architecture/decisions/ADR-014-deterministic-writes.md"
    )


def test_allowed_docstring_files_still_exist(src_dir: Path) -> None:
    """Ensure allowed exception files still exist.

    If a file is removed, it should be removed from ALLOWED_DOCSTRING_FILES.
    """
    for relative_path in ALLOWED_DOCSTRING_FILES:
        full_path = src_dir / "bioetl" / relative_path
        assert full_path.exists(), (
            f"File {relative_path} is in ALLOWED_DOCSTRING_FILES but doesn't exist. "
            "Remove it from the allowlist."
        )
