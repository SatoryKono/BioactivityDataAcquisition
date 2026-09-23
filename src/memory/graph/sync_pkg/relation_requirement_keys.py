"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from collections.abc import Callable

from memory.graph.sync_pkg._core_models import JsonValue, NodeKey
from memory.graph.sync_pkg.graph_snapshot import (
    GraphRelation,
    GraphSnapshot,
    snapshot_orphans,
)
from memory.graph.sync_pkg.live_queries import _build_diff_entries
from memory.graph.sync_pkg.neo4j_statements import (
    DEFAULT_INGEST_WAVE,
    DEFAULT_MANAGED_BY,
)
from memory.graph.sync_pkg.snapshot_relation_requirements import (
    SNAPSHOT_RELATION_REQUIREMENTS,
)
from memory.graph.sync_pkg.snapshot_support_specs import (
    _required_population_issues,
    _snapshot_support_specs,
)
from memory.graph.sync_pkg.snapshotrelationindex import (
    _build_snapshot_relation_index,
    _port_and_contract_metadata_issues,
    _SnapshotRelationIndex,
)
from memory.graph.sync_pkg.sync_run_id import (
    _append_missing_relation_issues,
    _append_support_issue,
    _missing_node_support_names,
    _sync_run_id,
)

__all__ = [
    "_append_path_issue",
    "_append_snapshot_support_issues",
    "_audit_report_payload",
    "_bind_support_predicate",
    "_excluded_file_structure_paths",
    "_format_orphan_nodes",
    "_ignored_runtime_paths",
    "_orphan_node_issues",
    "_path_leak_issues",
    "_relation_requirement_keys",
    "_sampled_sorted_unique",
    "_support_and_relation_issues",
    "snapshot_invariant_issues",
]


def _relation_requirement_keys(
    relations: tuple[GraphRelation, ...],
) -> set[tuple[str, str, str, str]]:
    return {
        (rel.source.label, rel.source.name, rel.relation_type, rel.target.label)
        for rel in relations
    }


def _bind_support_predicate(
    predicate: Callable[[_SnapshotRelationIndex, NodeKey], bool],
    relation_index: _SnapshotRelationIndex,
) -> Callable[[NodeKey], bool]:
    def _is_supported(key: NodeKey) -> bool:
        return predicate(relation_index, key)

    return _is_supported


def _append_snapshot_support_issues(
    issues: list[str],
    snapshot: GraphSnapshot,
    relations: tuple[GraphRelation, ...],
) -> None:
    relation_index = _build_snapshot_relation_index(relations)
    for prefix, label, predicate in _snapshot_support_specs():
        _append_support_issue(
            issues,
            prefix,
            _missing_node_support_names(
                snapshot, label, _bind_support_predicate(predicate, relation_index)
            ),
        )


def _support_and_relation_issues(
    snapshot: GraphSnapshot,
    relations: tuple[GraphRelation, ...],
) -> list[str]:
    issues: list[str] = []
    relation_keys = _relation_requirement_keys(relations)
    _append_missing_relation_issues(
        issues, relation_keys, SNAPSHOT_RELATION_REQUIREMENTS
    )
    _append_snapshot_support_issues(issues, snapshot, relations)
    return issues


def _ignored_runtime_paths(snapshot: GraphSnapshot) -> list[str]:
    return [
        node.key.name
        for node in snapshot.nodes.values()
        if "__pycache__" in node.key.name
        or "__pycache__" in str(node.properties.get("source_path", ""))
    ]


def _excluded_file_structure_paths(snapshot: GraphSnapshot) -> list[str]:
    return [
        node.key.name
        for node in snapshot.nodes.values()
        if node.key.label in {"directory_surface", "file_surface"}
        and (
            node.key.name.startswith("docs/site")
            or node.key.name.startswith("docs/site/")
            or node.key.name.startswith("docs/99-archive")
            or node.key.name.startswith("docs/exports")
            or node.key.name.startswith("docs/reports/generated")
            or node.key.name.startswith("docs/02-architecture/generated")
            or node.key.name.startswith("docs/02-architecture/diagrams/bundles")
            or node.key.name.startswith("scripts/archive")
            or "/png" in node.key.name
            or "/svg" in node.key.name
        )
    ]


def _sampled_sorted_unique(values: list[str], limit: int) -> list[str]:
    return sorted(set(values))[:limit]


def _append_path_issue(
    issues: list[str],
    prefix: str,
    paths: list[str],
    *,
    limit: int,
) -> None:
    if paths:
        issues.append(f"{prefix}: {_sampled_sorted_unique(paths, limit)}")


def _path_leak_issues(snapshot: GraphSnapshot) -> list[str]:
    issues: list[str] = []
    _append_path_issue(
        issues,
        "ignored runtime paths leaked into snapshot",
        _ignored_runtime_paths(snapshot),
        limit=5,
    )
    excluded_paths = _excluded_file_structure_paths(snapshot)
    if excluded_paths:
        issues.append(
            "excluded file-structure paths leaked into snapshot: "
            + ", ".join(_sampled_sorted_unique(excluded_paths, 10))
        )
    return issues


def _format_orphan_nodes(orphan_nodes: list[NodeKey], limit: int) -> str:
    return ", ".join(f"{node.label}:{node.name}" for node in orphan_nodes[:limit])


def _orphan_node_issues(snapshot: GraphSnapshot) -> list[str]:
    orphan_nodes = snapshot_orphans(snapshot)
    if not orphan_nodes:
        return []
    return ["snapshot contains orphan nodes: " + _format_orphan_nodes(orphan_nodes, 10)]


def snapshot_invariant_issues(snapshot: GraphSnapshot) -> list[str]:
    stats = snapshot.stats()
    relations = tuple(snapshot.relations.values())
    return (
        _required_population_issues(stats)
        + _port_and_contract_metadata_issues(snapshot)
        + _support_and_relation_issues(snapshot, relations)
        + _path_leak_issues(snapshot)
        + _orphan_node_issues(snapshot)
    )


def _audit_report_payload(
    *,
    snapshot_payload: dict[str, JsonValue],
    managed_labels: list[str],
    live_summary: dict[str, JsonValue],
    snapshot_label_counts: dict[str, int],
    live_managed_label_counts: dict[str, int],
    snapshot_relation_counts: dict[str, int],
    live_managed_relation_counts: dict[str, int],
) -> dict[str, JsonValue]:
    return {
        "generated_at": _sync_run_id(),
        "managed_by": DEFAULT_MANAGED_BY,
        "ingest_wave": DEFAULT_INGEST_WAVE,
        "snapshot": snapshot_payload,
        "managed_labels": managed_labels,
        "live": live_summary,
        "diff": {
            "labels": _build_diff_entries(
                snapshot_label_counts, live_managed_label_counts
            ),
            "relation_types": _build_diff_entries(
                snapshot_relation_counts, live_managed_relation_counts
            ),
        },
    }
