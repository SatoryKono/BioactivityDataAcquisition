"""Phase 2 guards for architecture P1 tails."""

from __future__ import annotations

import ast
from pathlib import Path


CRITICAL_MODULES = (
    "src/bioetl/application/core/idmapping_data_source.py",
    "src/bioetl/infrastructure/adapters/uniprot/idmapping_client.py",
)


def _load_tree(path: str) -> ast.AST:
    """Load Python AST for a file path."""
    source = Path(path).read_text(encoding="utf-8")
    return ast.parse(source, filename=path)


def _has_exception_name(node: ast.expr) -> bool:
    """Return True when expression includes Exception type."""
    if isinstance(node, ast.Name):
        return node.id == "Exception"
    if isinstance(node, ast.Tuple):
        return any(_has_exception_name(element) for element in node.elts)
    return False


def test_critical_modules_have_no_broad_exception_handlers() -> None:
    """Critical modules should not use except Exception or bare except."""
    violations: list[str] = []
    for path in CRITICAL_MODULES:
        tree = _load_tree(path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            if node.type is None:
                violations.append(f"{path}:{node.lineno} uses bare except")
                continue
            if _has_exception_name(node.type):
                violations.append(f"{path}:{node.lineno} catches Exception")

    assert not violations, "Broad exception handlers found:\n" + "\n".join(violations)


def test_idmapping_data_source_has_no_direct_file_io_imports() -> None:
    """Application-layer ID mapping source must not import file I/O modules."""
    path = "src/bioetl/application/core/idmapping_data_source.py"
    tree = _load_tree(path)
    forbidden_imports = {"csv", "pathlib"}
    violations: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                if name.name in forbidden_imports:
                    violations.append(f"{path}:{node.lineno} imports {name.name}")
        elif isinstance(node, ast.ImportFrom) and node.module in forbidden_imports:
            violations.append(f"{path}:{node.lineno} imports from {node.module}")

    assert not violations, "Direct file I/O imports found:\n" + "\n".join(violations)
