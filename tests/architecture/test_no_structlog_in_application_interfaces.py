"""Architecture test: structlog только в infrastructure/composition слоях.

REQ-ARCH-032: Application и interfaces слои используют LoggerPort абстракцию.
См. ADR-006 для обоснования.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

APPLICATION_DIR = Path("src/bioetl/application")
INTERFACES_DIR = Path("src/bioetl/interfaces")


def _check_structlog_imports(directory: Path) -> list[str]:
    """Check for direct structlog imports in a directory.

    Args:
        directory: Directory to scan for Python files.

    Returns:
        List of violation messages with file path and line number.
    """
    violations = []

    if not directory.exists():
        return violations

    for py_file in directory.rglob("*.py"):
        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "structlog":
                        rel_path = py_file.relative_to(Path("src"))
                        violations.append(
                            f"{rel_path}:{node.lineno}: import structlog"
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("structlog"):
                    rel_path = py_file.relative_to(Path("src"))
                    violations.append(
                        f"{rel_path}:{node.lineno}: from {node.module} import ..."
                    )

    return violations


class TestNoStructlogInApplicationLayer:
    """Test that application layer does not import structlog directly."""

    def test_no_structlog_in_application_layer(self) -> None:
        """Application layer MUST NOT import structlog directly.

        REQ-ARCH-032: Use LoggerPort abstraction instead.
        See ADR-006 for rationale.
        """
        violations = _check_structlog_imports(APPLICATION_DIR)

        assert not violations, (
            f"Direct structlog imports found in application layer:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\nUse LoggerPort from domain.ports instead. See ADR-006."
        )


class TestNoStructlogInInterfacesLayer:
    """Test that interfaces layer does not import structlog directly."""

    def test_no_structlog_in_interfaces_layer(self) -> None:
        """Interfaces layer MUST NOT import structlog directly.

        REQ-ARCH-032: Use LoggerPort abstraction instead.
        See ADR-006 for rationale.
        """
        violations = _check_structlog_imports(INTERFACES_DIR)

        assert not violations, (
            f"Direct structlog imports found in interfaces layer:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\nUse LoggerPort from domain.ports instead. See ADR-006."
        )


@pytest.mark.parametrize(
    "layer_name,layer_dir",
    [
        ("application", APPLICATION_DIR),
        ("interfaces", INTERFACES_DIR),
    ],
)
def test_no_structlog_parametrized(layer_name: str, layer_dir: Path) -> None:
    """Parametrized test for structlog imports in multiple layers.

    Args:
        layer_name: Name of the layer being tested.
        layer_dir: Directory path of the layer.
    """
    violations = _check_structlog_imports(layer_dir)

    assert not violations, (
        f"Direct structlog imports found in {layer_name} layer:\n"
        + "\n".join(f"  - {v}" for v in violations)
        + f"\n\nThe {layer_name} layer MUST use LoggerPort abstraction. See ADR-006."
    )
