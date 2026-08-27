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
"""Guard the remaining architectural import edges from the matrix.

These tests cover edges that were historically verified only indirectly via
ad-hoc reviews or specialized boundary tests. The goal here is to keep the
clean-architecture matrix explicit and CI-enforced for production imports.

Covered edges:
- domain -> composition
- domain -> interfaces
- application -> infrastructure
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
        "infrastructure",
        ("bioetl.infrastructure",),
        "REQ-ARCH-MATRIX-003",
    ),
    (
        "application",
        "composition",
        ("bioetl.composition",),
        "REQ-ARCH-MATRIX-004",
    ),
    (
        "application",
        "interfaces",
        ("bioetl.interfaces",),
        "REQ-ARCH-MATRIX-005",
    ),
    (
        "composition",
        "interfaces",
        ("bioetl.interfaces",),
        "REQ-ARCH-MATRIX-006",
    ),
)


# TYPE_CHECKING imports are handled structurally below and do not belong here.
# Keep this map explicit so sanctioned production exceptions stay visible.
SANCTIONED_EDGE_EXCEPTIONS: dict[tuple[str, str], set[str]] = {}

INFRASTRUCTURE_ALLOWED_DOMAIN_IMPORT_PREFIXES = (
    "bioetl.domain.behavior",
    "bioetl.domain.composite",
    "bioetl.domain.config",
    "bioetl.domain.constants",
    "bioetl.domain.contracts",
    "bioetl.domain.control_plane",
    "bioetl.domain.deterministic_identity",
    "bioetl.domain.entities",
    "bioetl.domain.error_classifier",
    "bioetl.domain.exceptions",
    "bioetl.domain.filtering",
    "bioetl.domain.lineage",
    "bioetl.domain.locking",
    "bioetl.domain.mapping",
    "bioetl.domain.medallion",
    "bioetl.domain.mixin_host",
    "bioetl.domain.models",
    "bioetl.domain.normalization",
    "bioetl.domain.observability_contract",
    "bioetl.domain.ports",
    "bioetl.domain.registry",
    "bioetl.domain.resilience",
    "bioetl.domain.run_reports",
    "bioetl.domain.schemas",
    "bioetl.domain.serialization",
    "bioetl.domain.transformations",
    "bioetl.domain.types",
    "bioetl.domain.value_objects",
    "bioetl.domain.version",
    "bioetl.domain.workflow",
)


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


def _parent_map(tree: ast.Module) -> dict[ast.AST, ast.AST]:
    return {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }


def _matches_forbidden_prefix(
    module_name: str,
    forbidden_prefixes: tuple[str, ...],
) -> bool:
    return any(
        module_name == prefix or module_name.startswith(prefix + ".")
        for prefix in forbidden_prefixes
    )


def _import_violations(
    *,
    py_file: Path,
    node: ast.Import,
    forbidden_prefixes: tuple[str, ...],
    sanctioned_exceptions: set[str],
) -> list[str]:
    rel_path = py_file.as_posix()
    violations: list[str] = []
    for alias in node.names:
        module_name = alias.name
        if module_name in sanctioned_exceptions:
            continue
        if _matches_forbidden_prefix(module_name, forbidden_prefixes):
            violations.append(f"{rel_path}:{node.lineno} imports {module_name}")
    return violations


def _import_from_violation(
    *,
    py_file: Path,
    node: ast.ImportFrom,
    importer_module: str,
    forbidden_prefixes: tuple[str, ...],
    sanctioned_exceptions: set[str],
) -> str | None:
    resolved_module = _resolve_relative_module(
        importer_module=importer_module,
        module=node.module,
        level=node.level,
    )
    if not resolved_module or resolved_module in sanctioned_exceptions:
        return None
    if _matches_forbidden_prefix(resolved_module, forbidden_prefixes):
        return f"{py_file.as_posix()}:{node.lineno} imports from {resolved_module}"
    return None


def _node_edge_violations(
    *,
    node: ast.AST,
    rel_path: Path,
    importer_module: str,
    forbidden_prefixes: tuple[str, ...],
    sanctioned_exceptions: set[str],
) -> list[str]:
    if isinstance(node, ast.Import):
        return _import_violations(
            py_file=rel_path,
            node=node,
            forbidden_prefixes=forbidden_prefixes,
            sanctioned_exceptions=sanctioned_exceptions,
        )
    if isinstance(node, ast.ImportFrom):
        violation = _import_from_violation(
            py_file=rel_path,
            node=node,
            importer_module=importer_module,
            forbidden_prefixes=forbidden_prefixes,
            sanctioned_exceptions=sanctioned_exceptions,
        )
        return [violation] if violation is not None else []
    return []


def _imported_module_names(
    *,
    node: ast.AST,
    importer_module: str,
) -> list[str]:
    """Return absolute imported module names for import nodes."""
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom):
        resolved = _resolve_relative_module(
            importer_module=importer_module,
            module=node.module,
            level=node.level,
        )
        return [resolved] if resolved else []
    return []


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
        parents = _parent_map(tree)
        importer_module = _module_name_for_path(src_dir, py_file)
        rel_path = py_file.relative_to(src_dir)

        for node in ast.walk(tree):
            if _is_inside_type_checking(node, parents):
                continue
            violations.extend(
                _node_edge_violations(
                    node=node,
                    rel_path=rel_path,
                    importer_module=importer_module,
                    forbidden_prefixes=forbidden_prefixes,
                    sanctioned_exceptions=sanctioned_exceptions,
                )
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


@pytest.mark.architecture
def test_infrastructure_domain_import_scope_is_explicit(
    src_dir: Path,
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """Keep Infrastructure -> Domain imports within the documented policy."""
    violations: list[str] = []

    for py_file, tree in _iter_layer_modules(
        src_dir=src_dir,
        source_ast_cache=source_ast_cache,
        layer_name="infrastructure",
    ):
        parents = _parent_map(tree)
        importer_module = _module_name_for_path(src_dir, py_file)
        rel_path = py_file.relative_to(src_dir)
        for node in ast.walk(tree):
            if _is_inside_type_checking(node, parents):
                continue
            for module_name in _imported_module_names(
                node=node,
                importer_module=importer_module,
            ):
                if not _matches_forbidden_prefix(module_name, ("bioetl.domain",)):
                    continue
                if not _matches_forbidden_prefix(
                    module_name,
                    INFRASTRUCTURE_ALLOWED_DOMAIN_IMPORT_PREFIXES,
                ):
                    violations.append(
                        f"{rel_path.as_posix()}:{getattr(node, 'lineno', '?')} imports {module_name}"
                    )

    assert not violations, (
        "Infrastructure -> Domain imports must stay within the explicit "
        "contract/value-object policy.\n"
        + "\n".join(f"  - {violation}" for violation in violations[:100])
    )
