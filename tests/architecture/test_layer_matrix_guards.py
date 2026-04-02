"""Guard the remaining architectural import edges from the matrix.

These tests cover edges that were historically verified only indirectly via
ad-hoc reviews or specialized boundary tests. The goal here is to keep the
clean-architecture matrix explicit and CI-enforced for production imports.

Covered edges:
- domain -> composition
- domain -> interfaces
- application -> composition
- application -> interfaces
- composition -> interfaces

Allowed exceptions:
- Imports guarded by ``if TYPE_CHECKING:`` remain allowed.
- Additional production exceptions must be listed explicitly in
  ``SANCTIONED_EDGE_EXCEPTIONS`` with a rationale.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable
from pathlib import Path

import pytest


EDGE_DEFINITIONS = (
    (
        "domain",
        "composition",
        ("bioetl.composition",),
        "REQ-ARCH-MATRIX-001",
    ),
    (
        "domain",
        "interfaces",
        ("bioetl.interfaces",),
        "REQ-ARCH-MATRIX-002",
    ),
    (
        "application",
        "composition",
        ("bioetl.composition",),
        "REQ-ARCH-MATRIX-003",
    ),
    (
        "application",
        "interfaces",
        ("bioetl.interfaces",),
        "REQ-ARCH-MATRIX-004",
    ),
    (
        "composition",
        "interfaces",
        ("bioetl.interfaces",),
        "REQ-ARCH-MATRIX-005",
    ),
)


# TYPE_CHECKING imports are handled structurally below and do not belong here.
# Keep this map explicit so sanctioned production exceptions stay visible.
SANCTIONED_EDGE_EXCEPTIONS: dict[tuple[str, str], set[str]] = {}


def _module_name_for_path(src_dir: Path, file_path: Path) -> str:
    rel_parts = file_path.relative_to(src_dir).with_suffix("").parts
    return ".".join(rel_parts)


def _resolve_relative_module(
    *,
    importer_module: str,
    module: str | None,
    level: int,
) -> str | None:
    if level == 0:
        return module

    parent_parts = importer_module.split(".")[:-1]
    if level > len(parent_parts):
        return None

    base_parts = parent_parts[: len(parent_parts) - level + 1]
    if module:
        return ".".join([*base_parts, module])
    return ".".join(base_parts)


def _is_type_checking_guard(test: ast.expr) -> bool:
    if isinstance(test, ast.Name):
        return test.id == "TYPE_CHECKING"
    if isinstance(test, ast.Attribute) and isinstance(test.value, ast.Name):
        return test.value.id == "typing" and test.attr == "TYPE_CHECKING"
    return False


def _is_inside_type_checking(
    node: ast.AST,
    parents: dict[ast.AST, ast.AST],
) -> bool:
    current = node
    while current in parents:
        current = parents[current]
        if isinstance(current, ast.If) and _is_type_checking_guard(current.test):
            return True
    return False


def _iter_layer_modules(
    *,
    src_dir: Path,
    source_ast_cache: dict[Path, ast.Module],
    layer_name: str,
) -> Iterable[tuple[Path, ast.Module]]:
    layer_root = src_dir / "bioetl" / layer_name
    assert layer_root.exists(), f"Layer not found: {layer_root}"
    for path, tree in sorted(source_ast_cache.items()):
        if layer_root in path.parents:
            yield path, tree


def _collect_edge_violations(
    *,
    src_dir: Path,
    source_ast_cache: dict[Path, ast.Module],
    importer_layer: str,
    forbidden_prefixes: tuple[str, ...],
    sanctioned_exceptions: set[str],
) -> list[str]:
    violations: list[str] = []

    for py_file, tree in _iter_layer_modules(
        src_dir=src_dir,
        source_ast_cache=source_ast_cache,
        layer_name=importer_layer,
    ):
        parents = {
            child: parent
            for parent in ast.walk(tree)
            for child in ast.iter_child_nodes(parent)
        }
        importer_module = _module_name_for_path(src_dir, py_file)

        for node in ast.walk(tree):
            if _is_inside_type_checking(node, parents):
                continue

            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name
                    if module_name in sanctioned_exceptions:
                        continue
                    if any(
                        module_name == prefix or module_name.startswith(prefix + ".")
                        for prefix in forbidden_prefixes
                    ):
                        rel_path = py_file.relative_to(src_dir).as_posix()
                        violations.append(
                            f"{rel_path}:{node.lineno} imports {module_name}"
                        )

            if isinstance(node, ast.ImportFrom):
                resolved_module = _resolve_relative_module(
                    importer_module=importer_module,
                    module=node.module,
                    level=node.level,
                )
                if not resolved_module or resolved_module in sanctioned_exceptions:
                    continue
                if any(
                    resolved_module == prefix
                    or resolved_module.startswith(prefix + ".")
                    for prefix in forbidden_prefixes
                ):
                    rel_path = py_file.relative_to(src_dir).as_posix()
                    violations.append(
                        f"{rel_path}:{node.lineno} imports from {resolved_module}"
                    )

    return violations


@pytest.mark.parametrize(
    ("importer_layer", "forbidden_layer", "forbidden_prefixes", "requirement_id"),
    EDGE_DEFINITIONS,
)
def test_layer_matrix_edge_guards(
    src_dir: Path,
    source_ast_cache: dict[Path, ast.Module],
    importer_layer: str,
    forbidden_layer: str,
    forbidden_prefixes: tuple[str, ...],
    requirement_id: str,
) -> None:
    """Enforce remaining import-matrix edges for production code."""
    violations = _collect_edge_violations(
        src_dir=src_dir,
        source_ast_cache=source_ast_cache,
        importer_layer=importer_layer,
        forbidden_prefixes=forbidden_prefixes,
        sanctioned_exceptions=SANCTIONED_EDGE_EXCEPTIONS.get(
            (importer_layer, forbidden_layer),
            set(),
        ),
    )

    assert not violations, (
        f"{requirement_id}: {importer_layer} layer must not import "
        f"{forbidden_layer} layer in production code.\n"
        + "\n".join(f"  - {violation}" for violation in violations[:100])
    )
