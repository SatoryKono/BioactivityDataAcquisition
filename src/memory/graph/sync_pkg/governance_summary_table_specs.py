"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import (
    _is_ignored_repo_path,
    _module_dotted_name,
    _rel_path,
)
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.default_batch_size import KNOWN_LAYERS
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.python_paths import INIT_PY, MAIN_PY

__all__ = [
    "_add_layer_topology",
    "_add_runtime_layer_families",
    "_add_runtime_layer_modules",
    "_add_runtime_layer_surface",
    "_governance_summary_table_specs",
    "_runtime_module_family_key",
]


def _governance_summary_table_specs() -> tuple[tuple[str, str], ...]:
    return (
        ("decision", "DEC"),
        ("risk", "RISK"),
    )


def _add_runtime_layer_surface(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    *,
    layer_name: str,
    layer_path: Path,
    today: str,
) -> NodeKey:
    layer = snapshot.add_node(
        "layer_family",
        layer_name,
        summary=f"Top-level runtime layer `{layer_name}`.",
        source_path=_rel_path(root, layer_path),
        source_kind="source_tree",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(project, "CONTAINS", layer, provenance="source_tree")
    return layer


def _add_runtime_layer_families(
    snapshot: GraphSnapshot,
    root: Path,
    layer: NodeKey,
    *,
    layer_name: str,
    layer_path: Path,
    today: str,
) -> None:
    for family_path in sorted(
        path
        for path in layer_path.iterdir()
        if path.is_dir() and not _is_ignored_repo_path(path)
    ):
        family_name = f"{layer_name}/{family_path.name}"
        family = snapshot.add_node(
            "package_family",
            family_name,
            summary=f"Package family `{family_name}`.",
            source_path=_rel_path(root, family_path),
            source_kind="source_tree",
            layer=layer_name,
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        snapshot.add_relation(layer, "CONTAINS", family, provenance="source_tree")


def _runtime_module_family_key(
    layer: NodeKey, *, layer_name: str, relative_path: str
) -> NodeKey:
    parts = Path(relative_path).parts
    if len(parts) >= 5:
        return NodeKey("package_family", f"{layer_name}/{parts[3]}")
    return layer


def _add_runtime_layer_modules(
    snapshot: GraphSnapshot,
    root: Path,
    layer: NodeKey,
    *,
    layer_name: str,
    layer_path: Path,
    today: str,
) -> None:
    for module_path in sorted(layer_path.rglob("*.py")):
        if module_path.name in {INIT_PY, MAIN_PY}:
            continue
        if _is_ignored_repo_path(module_path):
            continue
        relative_path = _rel_path(root, module_path)
        family_key = _runtime_module_family_key(
            layer, layer_name=layer_name, relative_path=relative_path
        )
        module = snapshot.add_node(
            "module_surface",
            relative_path,
            summary=f"Python module `{_module_dotted_name(relative_path)}`.",
            source_path=relative_path,
            source_kind="python_module",
            layer=layer_name,
            module_name=module_path.stem,
            dotted_path=_module_dotted_name(relative_path),
            last_verified=today,
            ingest_wave="repo_sync_v1",
            confidence="high",
        )
        snapshot.add_relation(family_key, "CONTAINS", module, provenance="source_tree")


def _add_layer_topology(
    snapshot: GraphSnapshot, root: Path, project: NodeKey, today: str
) -> None:
    src_root = root / "src" / "bioetl"
    for layer_name in KNOWN_LAYERS:
        layer_path = src_root / layer_name
        if not layer_path.is_dir():
            continue
        layer = _add_runtime_layer_surface(
            snapshot,
            root,
            project,
            layer_name=layer_name,
            layer_path=layer_path,
            today=today,
        )
        _add_runtime_layer_families(
            snapshot,
            root,
            layer,
            layer_name=layer_name,
            layer_path=layer_path,
            today=today,
        )
        _add_runtime_layer_modules(
            snapshot,
            root,
            layer,
            layer_name=layer_name,
            layer_path=layer_path,
            today=today,
        )
