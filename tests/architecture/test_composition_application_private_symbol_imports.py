"""Guard against composition importing private runtime collaborators from application."""

from __future__ import annotations

import ast
from pathlib import Path


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


def _build_parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    return {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }


def _iter_private_application_symbol_violations(
    *,
    src_dir: Path,
    composition_root: Path,
) -> list[str]:
    violations: list[str] = []
    for py_file in sorted(composition_root.rglob("*.py")):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        parents = _build_parent_map(tree)
        importer_module = _module_name_for_path(src_dir, py_file)
        violations.extend(
            _iter_file_private_symbol_violations(
                py_file=py_file,
                src_dir=src_dir,
                tree=tree,
                parents=parents,
                importer_module=importer_module,
            )
        )
    return violations


def _iter_file_private_symbol_violations(
    *,
    py_file: Path,
    src_dir: Path,
    tree: ast.AST,
    parents: dict[ast.AST, ast.AST],
    importer_module: str,
) -> list[str]:
    rel_path = py_file.relative_to(src_dir).as_posix()
    violations: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if _is_inside_type_checking(node, parents):
            continue
        resolved_module = _resolve_relative_module(
            importer_module=importer_module,
            module=node.module,
            level=node.level,
        )
        if not _is_application_module_target(resolved_module):
            continue
        violations.extend(
            f"{rel_path}:{node.lineno} imports private symbol "
            f"{resolved_module}.{alias.name}"
            for alias in node.names
            if alias.name.startswith("_")
        )
    return violations


def _is_application_module_target(resolved_module: str | None) -> bool:
    return bool(resolved_module and resolved_module.startswith("bioetl.application."))


def test_composition_avoids_private_application_symbol_imports(src_dir: Path) -> None:
    """Composition should depend only on public application-facing collaborators."""
    composition_root = src_dir / "bioetl" / "composition"
    violations = _iter_private_application_symbol_violations(
        src_dir=src_dir,
        composition_root=composition_root,
    )

    assert not violations, (
        "Composition imported private application collaborators:\n"
        + "\n".join(violations[:80])
    )
