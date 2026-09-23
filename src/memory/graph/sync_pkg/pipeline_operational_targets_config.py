"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import JsonValue, NodeKey
from memory.graph.sync_pkg.apply_groups import DEFAULT_LEGACY_PRUNE_LABELS
from memory.graph.sync_pkg.complexity_marker_buckets import _configured_node_keys
from memory.graph.sync_pkg.default_batch_size import (
    DEFAULT_PIPELINE_RUNTIME_PATHS,
    DEFAULT_PIPELINE_VALIDATION_GATES,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.live_queries import (
    _audit_live_summary,
    _live_managed_relation_rows,
    _live_orphan_rows,
    _live_repo_label_rows,
    _live_unmanaged_repo_rows,
    _managed_label_counts_from_rows,
    _managed_relation_counts_from_rows,
    _row_int_total,
    _snapshot_count_map,
)
from memory.graph.sync_pkg.pipeline_dashboard_config import (
    PipelineOperationalContext,
    _link_pipeline_operational_targets,
    _pipeline_kind_dashboards,
)
from memory.graph.sync_pkg.relation_requirement_keys import _audit_report_payload
from memory.graph.sync_pkg.transport import Neo4jHttpClient, resolve_neo4j_connection

__all__ = [
    "_link_pipeline_operational_for_pipeline",
    "_pipeline_operational_targets_config",
    "_sorted_pipeline_nodes",
    "build_audit_report",
]


def _pipeline_operational_targets_config(
    pipeline_ops: dict[str, object],
) -> tuple[list[NodeKey], list[NodeKey]]:
    runtime_paths = _configured_node_keys(
        "execution_path",
        pipeline_ops.get("runtime_paths"),
        DEFAULT_PIPELINE_RUNTIME_PATHS,
    )
    validation_gates = _configured_node_keys(
        "quality_gate",
        pipeline_ops.get("validation_gates"),
        DEFAULT_PIPELINE_VALIDATION_GATES,
    )
    return runtime_paths, validation_gates


def _sorted_pipeline_nodes(pipeline_nodes: dict[str, NodeKey]) -> list[NodeKey]:
    return sorted(pipeline_nodes.values(), key=lambda node: node.name)


def _link_pipeline_operational_for_pipeline(
    snapshot: GraphSnapshot,
    pipeline: NodeKey,
    *,
    operational_context: PipelineOperationalContext,
) -> None:
    pipeline_props = snapshot.nodes[pipeline].properties
    pipeline_kind = pipeline_props.get("pipeline_kind")
    _link_pipeline_operational_targets(
        snapshot,
        pipeline,
        runtime_paths=operational_context.runtime_paths,
        validation_gates=operational_context.validation_gates,
        common_dashboards=operational_context.common_dashboards,
        kind_dashboards=_pipeline_kind_dashboards(
            pipeline_kind,
            entity_dashboards=operational_context.entity_dashboards,
            composite_dashboards=operational_context.composite_dashboards,
        ),
    )


def build_audit_report(
    snapshot: GraphSnapshot,
    root: Path,
    http_uri: str | None,
) -> dict[str, JsonValue]:
    base_uri, username, password, database = resolve_neo4j_connection(root, http_uri)
    client = Neo4jHttpClient(base_uri, username, password, database)
    managed_labels = sorted(
        {node.key.label for node in snapshot.nodes.values()}
        | set(DEFAULT_LEGACY_PRUNE_LABELS)
    )
    snapshot_relation_types = sorted(
        {relation.relation_type for relation in snapshot.relations.values()}
    )
    snapshot_stats = snapshot.stats()
    live_label_rows = _live_repo_label_rows(client, managed_labels)
    live_relation_rows = _live_managed_relation_rows(client, snapshot_relation_types)
    orphan_rows = _live_orphan_rows(client, managed_labels)
    unmanaged_rows = _live_unmanaged_repo_rows(client, managed_labels)

    live_managed_label_counts = _managed_label_counts_from_rows(live_label_rows)
    live_managed_relation_counts = _managed_relation_counts_from_rows(
        live_relation_rows
    )
    managed_node_total = _row_int_total(live_label_rows, "managed")
    unmanaged_repo_node_total = _row_int_total(unmanaged_rows, "count")
    managed_relation_total = sum(live_managed_relation_counts.values())
    live_summary = _audit_live_summary(
        managed_node_total=managed_node_total,
        managed_relation_total=managed_relation_total,
        unmanaged_repo_node_total=unmanaged_repo_node_total,
        label_summary=live_label_rows,
        managed_relation_summary=live_relation_rows,
        orphan_summary=orphan_rows,
        unmanaged_summary=unmanaged_rows,
    )
    return _audit_report_payload(
        snapshot_payload=snapshot_stats,
        managed_labels=managed_labels,
        live_summary=live_summary,
        snapshot_label_counts=_snapshot_count_map(snapshot_stats, "labels"),
        live_managed_label_counts=live_managed_label_counts,
        snapshot_relation_counts=_snapshot_count_map(snapshot_stats, "relation_types"),
        live_managed_relation_counts=live_managed_relation_counts,
    )
