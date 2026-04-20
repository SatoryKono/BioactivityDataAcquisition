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

    docstrings: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        # Module, class, and function docstrings
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ) and (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            docstring = node.body[0].value.value
            lineno = node.body[0].lineno
            docstrings.append((lineno, docstring))

    return docstrings


def _check_print_in_docstrings(directory: Path) -> list[str]:
    """Check for print() in docstring examples in a directory.

    Args:
        directory: Directory to scan for Python files.

    Returns:
        List of violation messages with file path and line number.
    """
    violations = []

    if not directory.exists():
        return violations

    for py_file in directory.rglob("*.py"):
        rel_path = py_file.relative_to(Path("src"))

        try:
            source = py_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        for lineno, docstring in _extract_docstrings(source):
            # Check if docstring contains Example: section with print()
            if ">>>" in docstring and PRINT_PATTERN.search(docstring):
                # Find which line in docstring has print
                for i, line in enumerate(docstring.splitlines()):
                    if PRINT_PATTERN.search(line):
                        violations.append(
                            f"{rel_path}:{lineno + i}: print() in docstring example"
                        )

    return violations


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
