"""Architecture tests for context/ports import direction.

Prevents import cycles between ``bioetl.domain.context`` and
``bioetl.domain.ports*`` modules.
"""

from __future__ import annotations

import ast
from pathlib import Path


def _collect_imported_modules(file_path: Path) -> set[str]:
    """Collect imported module names from a Python file."""
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    imports: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.add(node.module)

    return imports


def test_context_uses_leaf_port_import_for_logger(src_dir: Path) -> None:
    """domain.context must not import from the ports re-export package."""
    context_file = src_dir / "bioetl" / "domain" / "context.py"
    imports = _collect_imported_modules(context_file)

    assert "bioetl.domain.ports" not in imports, (
        "domain.context must use leaf port modules (e.g. "
        "bioetl.domain.ports.observability), not bioetl.domain.ports."
    )


def test_ports_modules_do_not_import_domain_context(src_dir: Path) -> None:
    """Leaf ports modules must not depend on domain.context."""
    ports_dir = src_dir / "bioetl" / "domain" / "ports"
    violations: list[str] = []

    for py_file in ports_dir.glob("*.py"):
        imports = _collect_imported_modules(py_file)
        if "bioetl.domain.context" in imports:
            violations.append(str(py_file.relative_to(src_dir)))

    assert not violations, (
        "Ports modules must not import domain.context to avoid context↔ports cycles: "
        + ", ".join(sorted(violations))
    )
