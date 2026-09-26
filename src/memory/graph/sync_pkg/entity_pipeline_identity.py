"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import _rel_path
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.mapping_io import _read_yaml
from memory.graph.sync_pkg.pipeline_source_config_artifact import (
    _link_pipeline_doc_artifacts,
    _pipeline_doc_artifact_targets,
    _pipeline_source_config_artifact,
)

__all__ = [
    "_add_entity_pipeline_surface",
    "_entity_pipeline_identity",
    "_link_entity_pipeline_dependencies",
]


def _entity_pipeline_identity(
    entity_path: Path,
    payload: dict[str, object],
) -> tuple[str, str, str, str]:
    provider_name = str(payload.get("provider", entity_path.parent.name))
    entity_name = str(payload.get("entity", entity_path.stem))
    pipeline_payload = payload.get("pipeline")
    pipeline_name = f"{provider_name}_{entity_name}"
    pipeline_summary = f"Entity pipeline `{pipeline_name}`."
    if isinstance(pipeline_payload, dict):
        pipeline_name = str(pipeline_payload.get("pipeline_name", pipeline_name))
        pipeline_summary = str(pipeline_payload.get("description", pipeline_summary))
    return provider_name, entity_name, pipeline_name, pipeline_summary


def _link_entity_pipeline_dependencies(
    snapshot: GraphSnapshot,
    pipeline: NodeKey,
    *,
    pipeline_name: str,
    provider_name: str,
    entity_name: str,
    contract_nodes: dict[str, NodeKey],
    adapter_nodes: dict[str, NodeKey],
) -> None:
    entity_key = NodeKey("entity_config", pipeline_name)
    if entity_key in snapshot.nodes:
        snapshot.add_relation(
            pipeline, "BACKED_BY", entity_key, provenance="impact_pipelines"
        )
    provider_key = NodeKey("provider_surface", provider_name)
    if provider_key in snapshot.nodes:
        snapshot.add_relation(
            pipeline, "DEPENDS_ON", provider_key, provenance="impact_pipelines"
        )
    adapter_key = adapter_nodes.get(provider_name)
    if adapter_key is not None:
        snapshot.add_relation(
            pipeline, "DEPENDS_ON", adapter_key, provenance="impact_pipelines"
        )
    contract_key = contract_nodes.get(f"{provider_name}.{entity_name}")
    if contract_key is not None:
        snapshot.add_relation(
            pipeline, "DEPENDS_ON", contract_key, provenance="impact_pipelines"
        )
    config_artifact = _pipeline_source_config_artifact(snapshot, pipeline)
    if config_artifact in snapshot.nodes:
        snapshot.add_relation(
            pipeline, "DEFINED_BY", config_artifact, provenance="impact_pipelines"
        )
    _link_pipeline_doc_artifacts(
        snapshot,
        pipeline,
        _pipeline_doc_artifact_targets(
            snapshot,
            provider_name=provider_name,
            entity_name=entity_name,
        ),
        provenance="impact_pipeline_docs",
    )


def _add_entity_pipeline_surface(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    entity_path: Path,
    *,
    contract_nodes: dict[str, NodeKey],
    adapter_nodes: dict[str, NodeKey],
    pipeline_nodes: dict[str, NodeKey],
) -> None:
    payload = _read_yaml(entity_path)
    provider_name, entity_name, pipeline_name, pipeline_summary = (
        _entity_pipeline_identity(
            entity_path,
            payload,
        )
    )
    pipeline = snapshot.add_node(
        "pipeline_surface",
        pipeline_name,
        summary=pipeline_summary,
        source_path=_rel_path(root, entity_path),
        source_kind="entity_pipeline",
        pipeline_kind="entity",
        provider=provider_name,
        entity=entity_name,
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    pipeline_nodes[pipeline_name] = pipeline
    snapshot.add_relation(
        project, "HAS_PIPELINE", pipeline, provenance="impact_pipelines"
    )
    _link_entity_pipeline_dependencies(
        snapshot,
        pipeline,
        pipeline_name=pipeline_name,
        provider_name=provider_name,
        entity_name=entity_name,
        contract_nodes=contract_nodes,
        adapter_nodes=adapter_nodes,
    )
