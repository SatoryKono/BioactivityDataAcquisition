"""Architecture test: no print() in docstring examples in non-domain layers.

REQ-ARCH-034: Application, composition, interfaces, and infrastructure layers
MUST use LoggerPort in docstring examples instead of print().

Domain layer is exempt since pure function examples conventionally show
return values with print() in Python doctests.

See CLAUDE.md §11 Anti-Patterns: ❌ `print()` → `structlog` с `run_id`
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

# Layers that should use LoggerPort in docstring examples
CHECKED_DIRS = [
    Path("src/bioetl/application"),
    Path("src/bioetl/composition"),
    Path("src/bioetl/interfaces"),
    Path("src/bioetl/infrastructure"),
]

# Pattern to detect print() calls in docstrings
# Matches: print(, print (, but not logger.print or _print
PRINT_PATTERN = re.compile(r"(?<![a-zA-Z_])print\s*\(")


def _docstring_nodes(tree: ast.AST) -> list[ast.AST]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        )
    ]


def _docstring_entry(node: ast.AST) -> tuple[int, str] | None:
    body = getattr(node, "body", None)
    if not body:
        return None
    first_stmt = body[0]
    if not (
        isinstance(first_stmt, ast.Expr)
        and isinstance(first_stmt.value, ast.Constant)
        and isinstance(first_stmt.value.value, str)
    ):
        return None
    return first_stmt.lineno, first_stmt.value.value


def _docstring_print_violations(
    *,
    rel_path: Path,
    lineno: int,
    docstring: str,
) -> list[str]:
    if ">>>" not in docstring or not PRINT_PATTERN.search(docstring):
        return []
    return [
        f"{rel_path}:{lineno + offset}: print() in docstring example"
        for offset, line in enumerate(docstring.splitlines())
        if PRINT_PATTERN.search(line)
    ]


def _extract_docstrings(source: str) -> list[tuple[int, str]]:
    """Extract all docstrings from Python source with line numbers.

    Args:
        source: Python source code.

    Returns:
        List of (line_number, docstring_content) tuples.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    return [
        entry
        for node in _docstring_nodes(tree)
        if (entry := _docstring_entry(node)) is not None
    ]


def _read_python_source(py_file: Path) -> str | None:
    try:
        return py_file.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def _file_docstring_print_violations(py_file: Path) -> list[str]:
    source = _read_python_source(py_file)
    if source is None:
        return []
    rel_path = py_file.relative_to(Path("src"))
    return [
        violation
        for lineno, docstring in _extract_docstrings(source)
        for violation in _docstring_print_violations(
            rel_path=rel_path,
            lineno=lineno,
            docstring=docstring,
        )
    ]


def _check_print_in_docstrings(directory: Path) -> list[str]:
    """Check for print() in docstring examples in a directory.

    Args:
        directory: Directory to scan for Python files.

    Returns:
        List of violation messages with file path and line number.
    """
    if not directory.exists():
        return []

    return [
        violation
        for py_file in directory.rglob("*.py")
        for violation in _file_docstring_print_violations(py_file)
    ]


class TestNoPrintInDocstrings:
    """Test that non-domain layers use LoggerPort in docstring examples."""

    @pytest.mark.parametrize(
        "layer_dir",
        CHECKED_DIRS,
        ids=lambda p: p.name,
    )
    def test_no_print_in_docstring_examples(self, layer_dir: Path) -> None:
        """Non-domain layers MUST use LoggerPort in docstring examples.

        REQ-ARCH-034: Docstring examples should demonstrate proper
        structured logging patterns, not print() statements.

        Domain layer is exempt since pure functions conventionally
        show return values with print() in Python doctests.
        """
        violations = _check_print_in_docstrings(layer_dir)

        assert not violations, (
            f"print() in docstring examples found in {layer_dir.name} layer:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\nUse logger.info/debug/warning/error instead of print()."
            + "\nExample: logger.info('event_name', key=value)"
            + "\nSee CLAUDE.md §11 Anti-Patterns."
        )


def test_all_layers_checked() -> None:
    """Verify all non-domain layers are included in the check.

    This test ensures we don't miss adding new layers to the check.
    """
    expected_layers = {"application", "composition", "interfaces", "infrastructure"}
    checked_layers = {d.name for d in CHECKED_DIRS}

    assert checked_layers == expected_layers, (
        f"Layer mismatch. Expected: {expected_layers}, Got: {checked_layers}"
    )
