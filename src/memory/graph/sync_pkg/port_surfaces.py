"""Port-surface catalog extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

import ast
from pathlib import Path

from memory.graph.sync_pkg._core_ast import (
    _imported_symbols,
    _parse_python_ast,
    _protocol_class_names,
)
from memory.graph.sync_pkg._core_convert import _is_ignored_repo_path, _rel_path
from memory.graph.sync_pkg._core_models import NodeKey, PortSurfaceDescriptor
from memory.graph.sync_pkg.python_paths import INIT_PY, _python_surface_name

__all__ = [
    "PORTS_MODULE_PREFIX",
    "_build_port_surface_catalog",
    "_imported_port_surfaces",
    "_imported_port_surfaces_for_node",
    "_imported_port_surfaces_from_import",
    "_imported_port_surfaces_from_import_from",
    "_merge_port_init_exports",
    "_propagate_port_init_exports",
    "_register_port_protocol_descriptors",
    "_resolve_python_module_surface",
    "_seed_port_surface_catalog",
]

PORTS_MODULE_PREFIX = "bioetl.domain.ports"


def _build_port_surface_catalog(
    root: Path,
) -> tuple[list[PortSurfaceDescriptor], dict[str, set[str]], dict[str, dict[str, str]]]:
    ports_root = root / "src" / "bioetl" / "domain" / "ports"
    if not ports_root.is_dir():
        return [], {}, {}

    descriptors: list[PortSurfaceDescriptor] = []
    module_surfaces: dict[str, set[str]] = {}
    symbol_index: dict[str, dict[str, str]] = {}
    init_paths: list[tuple[str, Path]] = []

    for port_path in sorted(ports_root.rglob("*.py")):
        _seed_port_surface_catalog(
            root,
            port_path,
            descriptors,
            module_surfaces,
            symbol_index,
            init_paths,
        )

    _propagate_port_init_exports(init_paths, module_surfaces, symbol_index)

    return descriptors, module_surfaces, symbol_index


def _seed_port_surface_catalog(
    root: Path,
    port_path: Path,
    descriptors: list[PortSurfaceDescriptor],
    module_surfaces: dict[str, set[str]],
    symbol_index: dict[str, dict[str, str]],
    init_paths: list[tuple[str, Path]],
) -> None:
    if _is_ignored_repo_path(port_path) or "noop" in port_path.parts:
        return
    relative_path = _rel_path(root, port_path)
    module_name = _python_surface_name(relative_path)
    if port_path.name == INIT_PY:
        init_paths.append((module_name, port_path))
    _register_port_protocol_descriptors(
        port_path,
        relative_path,
        module_name,
        descriptors,
        module_surfaces,
        symbol_index,
    )


def _register_port_protocol_descriptors(
    port_path: Path,
    relative_path: str,
    module_name: str,
    descriptors: list[PortSurfaceDescriptor],
    module_surfaces: dict[str, set[str]],
    symbol_index: dict[str, dict[str, str]],
) -> None:
    for class_name in _protocol_class_names(port_path):
        surface_name = f"{module_name}.{class_name}"
        descriptors.append(
            PortSurfaceDescriptor(
                surface_name=surface_name,
                class_name=class_name,
                module_name=module_name,
                source_path=relative_path,
            )
        )
        module_surfaces.setdefault(module_name, set()).add(surface_name)
        symbol_index.setdefault(module_name, {})[class_name] = surface_name


def _propagate_port_init_exports(
    init_paths: list[tuple[str, Path]],
    module_surfaces: dict[str, set[str]],
    symbol_index: dict[str, dict[str, str]],
) -> None:
    changed = True
    while changed:
        changed = False
        for module_name, init_path in init_paths:
            if _merge_port_init_exports(
                module_name, init_path, module_surfaces, symbol_index
            ):
                changed = True


def _merge_port_init_exports(
    module_name: str,
    init_path: Path,
    module_surfaces: dict[str, set[str]],
    symbol_index: dict[str, dict[str, str]],
) -> bool:
    changed = False
    exported_surfaces = module_surfaces.setdefault(module_name, set())
    exported_symbols = symbol_index.setdefault(module_name, {})
    for imported_module, imported_name, alias_name in _imported_symbols(init_path):
        if not imported_module.startswith(PORTS_MODULE_PREFIX):
            continue
        target = symbol_index.get(imported_module, {}).get(imported_name)
        if target is None:
            continue
        if exported_symbols.get(alias_name) != target:
            exported_symbols[alias_name] = target
            changed = True
        if target not in exported_surfaces:
            exported_surfaces.add(target)
            changed = True
    return changed


def _imported_port_surfaces(
    path: Path,
    port_module_surfaces: dict[str, set[str]],
    port_symbol_index: dict[str, dict[str, str]],
) -> set[str]:
    tree = _parse_python_ast(path)
    if tree is None:
        return set()

    imported: set[str] = set()
    for node in ast.walk(tree):
        imported.update(
            _imported_port_surfaces_for_node(
                node,
                port_module_surfaces=port_module_surfaces,
                port_symbol_index=port_symbol_index,
            )
        )
    return imported


def _imported_port_surfaces_for_node(
    node: ast.AST,
    *,
    port_module_surfaces: dict[str, set[str]],
    port_symbol_index: dict[str, dict[str, str]],
) -> set[str]:
    if isinstance(node, ast.Import):
        return _imported_port_surfaces_from_import(node, port_module_surfaces)
    if isinstance(node, ast.ImportFrom) and node.module is not None:
        return _imported_port_surfaces_from_import_from(
            node,
            port_module_surfaces=port_module_surfaces,
            port_symbol_index=port_symbol_index,
        )
    return set()


def _imported_port_surfaces_from_import(
    node: ast.Import,
    port_module_surfaces: dict[str, set[str]],
) -> set[str]:
    imported: set[str] = set()
    for alias in node.names:
        if alias.name.startswith(PORTS_MODULE_PREFIX):
            imported.update(port_module_surfaces.get(alias.name, set()))
    return imported


def _imported_port_surfaces_from_import_from(
    node: ast.ImportFrom,
    *,
    port_module_surfaces: dict[str, set[str]],
    port_symbol_index: dict[str, dict[str, str]],
) -> set[str]:
    if node.module is None or not node.module.startswith(PORTS_MODULE_PREFIX):
        return set()
    if any(alias.name == "*" for alias in node.names):
        return set(port_module_surfaces.get(node.module, set()))
    imported: set[str] = set()
    symbol_targets = port_symbol_index.get(node.module, {})
    for alias in node.names:
        target = symbol_targets.get(alias.name)
        if target is not None:
            imported.add(target)
    return imported


def _resolve_python_module_surface(root: Path, module_name: str) -> NodeKey | None:
    relative_py = Path("src") / Path(*module_name.split("."))
    file_candidate = root / relative_py.with_suffix(".py")
    if file_candidate.is_file():
        return NodeKey("module_surface", _rel_path(root, file_candidate))
    init_candidate = root / relative_py / INIT_PY
    if init_candidate.is_file():
        return NodeKey("module_surface", _rel_path(root, init_candidate))
    return None
