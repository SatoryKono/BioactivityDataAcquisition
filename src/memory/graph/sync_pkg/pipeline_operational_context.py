"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import JsonValue
from memory.graph.sync_pkg.fast_analysis_scope import _fast_analysis_scope
from memory.graph.sync_pkg.fast_analysis_snapshot_counts import (
    _fast_analysis_live_counts,
    _fast_analysis_live_summary,
    _fast_analysis_snapshot_counts,
    _fast_audit_snapshot_payload,
)
from memory.graph.sync_pkg.governance_target_groups import (
    _pipeline_dashboard_targets,
    _pipeline_operational_section,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.pipeline_dashboard_config import PipelineOperationalContext
from memory.graph.sync_pkg.pipeline_operational_targets_config import (
    _pipeline_operational_targets_config,
)
from memory.graph.sync_pkg.relation_requirement_keys import _audit_report_payload
from memory.graph.sync_pkg.transport import Neo4jHttpClient, resolve_neo4j_connection

__all__ = [
    "_pipeline_operational_context",
    "build_fast_analysis_audit_report",
]


def _pipeline_operational_context(
    memory_mapping: dict[str, object],
) -> PipelineOperationalContext:
    pipeline_ops = _pipeline_operational_section(memory_mapping)
    runtime_paths, validation_gates = _pipeline_operational_targets_config(pipeline_ops)
    common_dashboards, entity_dashboards, composite_dashboards = (
        _pipeline_dashboard_targets(pipeline_ops)
    )
    return PipelineOperationalContext(
        runtime_paths=runtime_paths,
        validation_gates=validation_gates,
        common_dashboards=common_dashboards,
        entity_dashboards=entity_dashboards,
        composite_dashboards=composite_dashboards,
    )


def build_fast_analysis_audit_report(
    snapshot: GraphSnapshot,
    root: Path,
    http_uri: str | None,
) -> dict[str, JsonValue]:
    base_uri, username, password, database = resolve_neo4j_connection(root, http_uri)
    client = Neo4jHttpClient(base_uri, username, password, database)
    snapshot_stats = snapshot.stats()
    active_labels, active_relation_types = _fast_analysis_scope(snapshot_stats)
    snapshot_label_counts, snapshot_relation_counts = _fast_analysis_snapshot_counts(
        snapshot_stats,
        active_labels,
        active_relation_types,
    )
    live_managed_label_counts, live_managed_relation_counts = (
        _fast_analysis_live_counts(
            client,
            active_labels,
            active_relation_types,
        )
    )
    live_summary = _fast_analysis_live_summary(
        live_managed_label_counts,
        live_managed_relation_counts,
    )
    return _audit_report_payload(
        snapshot_payload=_fast_audit_snapshot_payload(
            snapshot_label_counts, snapshot_relation_counts
        ),
        managed_labels=list(active_labels),
        live_summary=live_summary,
        snapshot_label_counts=snapshot_label_counts,
        live_managed_label_counts=live_managed_label_counts,
        snapshot_relation_counts=snapshot_relation_counts,
        live_managed_relation_counts=live_managed_relation_counts,
    )
