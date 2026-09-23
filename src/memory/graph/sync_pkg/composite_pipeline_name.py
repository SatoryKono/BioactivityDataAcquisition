"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import _rel_path
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.link_composite_pipeline_dependencies import (
    _link_composite_pipeline_dependencies,
)
from memory.graph.sync_pkg.mapping_io import _read_yaml
from memory.graph.sync_pkg.pipeline_source_config_artifact import (
    _link_pipeline_doc_artifacts,
    _pipeline_doc_artifact_targets,
)

__all__ = [
    "_add_composite_pipeline_surface",
    "_composite_pipeline_name",
]


def _composite_pipeline_name(
    composite_path: Path,
    composite_payload: object,
) -> str:
    composite_name = composite_path.stem
    if isinstance(composite_payload, dict):
        composite_name = str(composite_payload.get("name", composite_name))
    return composite_name


def _add_composite_pipeline_surface(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    composite_path: Path,
    *,
    pipeline_nodes: dict[str, NodeKey],
) -> None:
    payload = _read_yaml(composite_path)
    composite_payload = payload.get("composite")
    composite_name = _composite_pipeline_name(composite_path, composite_payload)
    pipeline = snapshot.add_node(
        "pipeline_surface",
        composite_name,
        summary=f"Composite pipeline `{composite_name}`.",
        source_path=_rel_path(root, composite_path),
        source_kind="composite_pipeline",
        pipeline_kind="composite",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    pipeline_nodes[composite_name] = pipeline
    snapshot.add_relation(
        project, "HAS_PIPELINE", pipeline, provenance="impact_pipelines"
    )
    composite_key = NodeKey("composite_config", composite_name)
    if composite_key in snapshot.nodes:
        snapshot.add_relation(
            pipeline, "BACKED_BY", composite_key, provenance="impact_pipelines"
        )
    config_artifact = NodeKey("config_artifact", _rel_path(root, composite_path))
    if config_artifact in snapshot.nodes:
        snapshot.add_relation(
            pipeline, "DEFINED_BY", config_artifact, provenance="impact_pipelines"
        )
    _link_pipeline_doc_artifacts(
        snapshot,
        pipeline,
        _pipeline_doc_artifact_targets(
            snapshot,
            provider_name="composite",
            entity_name=composite_name.removeprefix("composite_"),
        ),
        provenance="impact_pipeline_docs",
    )
    _link_composite_pipeline_dependencies(
        snapshot, pipeline, composite_payload, pipeline_nodes
    )
