"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import _as_iterable, _rel_path
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.composite_dependency_target import _link_config_artifact
from memory.graph.sync_pkg.default_batch_size import YAML_FILE_GLOB
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.mapping_io import _read_yaml
from memory.graph.sync_pkg.provider_config_properties import _provider_config_properties

__all__ = [
    "_add_provider_surface",
    "_provider_config_paths",
]


def _provider_config_paths(providers_root: Path) -> tuple[Path, ...]:
    return tuple(sorted(providers_root.glob(YAML_FILE_GLOB)))


def _add_provider_surface(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    provider_path: Path,
    *,
    provider_nodes: dict[str, NodeKey],
) -> None:
    payload = _read_yaml(provider_path)
    provider_name = str(payload.get("provider", provider_path.stem))
    auth_type, pagination = _provider_config_properties(payload.get("source", {}))
    provider = snapshot.add_node(
        "provider_surface",
        provider_name,
        summary=f"Provider surface for `{provider_name}`.",
        source_path=_rel_path(root, provider_path),
        source_kind="provider_config",
        auth_type=auth_type,
        pagination_strategy=pagination,
        entity_count=len(_as_iterable(payload.get("entities"))) or None,
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    provider_nodes[provider_name] = provider
    snapshot.add_relation(
        project, "HAS_PROVIDER", provider, provenance="provider_config"
    )
    _link_config_artifact(
        snapshot,
        provider,
        path=_rel_path(root, provider_path),
        summary=f"Provider config for `{provider_name}`.",
        source_kind="provider_config",
        today=today,
        provenance="provider_config",
    )
