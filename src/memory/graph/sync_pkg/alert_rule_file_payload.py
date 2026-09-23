"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import _rel_path
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.create_workflow_job_surface import (
    _link_reusable_job_workflow,
)
from memory.graph.sync_pkg.graph_contexts import WorkflowJobContext
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.mapping_io import _read_yaml

__all__ = [
    "_add_alert_rules_artifact",
    "_add_alert_surface_node",
    "_alert_rule_file_payload",
    "_alert_rule_groups",
    "_link_workflow_job_reusable_target",
]


def _alert_rule_file_payload(rules_path: Path) -> dict[str, object]:
    return _read_yaml(rules_path)


def _add_alert_rules_artifact(
    snapshot: GraphSnapshot,
    root: Path,
    rules_path: Path,
    today: str,
) -> NodeKey:
    relative_path = _rel_path(root, rules_path)
    return snapshot.add_node(
        "config_artifact",
        relative_path,
        summary=f"Prometheus alert rules file `{rules_path.name}`.",
        source_path=relative_path,
        source_kind="prometheus_rules",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )


def _link_workflow_job_reusable_target(
    snapshot: GraphSnapshot,
    workflow_nodes: dict[str, NodeKey],
    workflow_name_by_relative_path: dict[str, str],
    job_context: WorkflowJobContext,
    reusable_workflow_ref: object,
) -> None:
    if isinstance(reusable_workflow_ref, str):
        _link_reusable_job_workflow(
            snapshot,
            workflow_nodes,
            workflow_name_by_relative_path,
            job_context,
            reusable_workflow_ref,
        )


def _alert_rule_groups(
    payload: dict[str, object],
) -> tuple[dict[str, object], ...]:
    groups = payload.get("groups")
    if not isinstance(groups, list):
        return ()
    return tuple(group for group in groups if isinstance(group, dict))


def _add_alert_surface_node(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    rules_path: Path,
    artifact: NodeKey,
    group_name: str,
    alert_name: str,
    annotations: dict[str, object],
    labels: dict[str, object],
) -> NodeKey:
    alert = snapshot.add_node(
        "alert_surface",
        alert_name,
        summary=str(annotations.get("summary", f"Prometheus alert `{alert_name}`.")),
        source_path=_rel_path(root, rules_path),
        source_kind="prometheus_alert_rule",
        group=group_name,
        severity=labels.get("severity"),
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(project, "HAS_ALERT", alert, provenance="impact_alerts")
    snapshot.add_relation(alert, "BACKED_BY", artifact, provenance="impact_alerts")
    return alert
