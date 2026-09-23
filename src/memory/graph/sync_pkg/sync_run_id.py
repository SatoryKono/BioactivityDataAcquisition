"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from memory.graph.sync_pkg._core_models import (
    JsonValue,
    NodeKey,
    SnapshotSelection,
    SyncApplyOptions,
)
from memory.graph.sync_pkg.apply_anchors import _ensure_targeted_apply_prerequisites
from memory.graph.sync_pkg.apply_groups import (
    _apply_snapshot_statement_groups,
    _delete_managed_wave_if_requested,
    _prune_managed_graph_if_requested,
    _resolved_sync_apply_options,
    _selection_from_legacy_kwargs,
    _statement_groups,
    _verification_sync_run,
)
from memory.graph.sync_pkg.apply_verify import (
    _retry_critical_analysis_groups,
    _verify_expected_group_counts,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.snapshot_filters import _filtered_snapshot
from memory.graph.sync_pkg.transport import Neo4jHttpClient, resolve_neo4j_connection

__all__ = [
    "_append_missing_relation_issues",
    "_append_support_issue",
    "_has_required_relation",
    "_missing_node_support_names",
    "_sync_run_id",
    "_verify_sync_snapshot",
    "sync_snapshot",
]


def _sync_run_id() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _verify_sync_snapshot(
    client: Neo4jHttpClient,
    *,
    targeted_mode: bool,
    prune_stale: bool,
    sync_run: str,
    batch_size: int,
    node_groups: dict[str, list[dict[str, JsonValue]]],
    relation_groups: dict[str, list[dict[str, JsonValue]]],
    analysis_node_groups: dict[str, list[dict[str, JsonValue]]],
    analysis_relation_groups: dict[str, list[dict[str, JsonValue]]],
) -> None:
    verification_sync_run = _verification_sync_run(
        targeted_mode,
        prune_stale,
        sync_run,
    )
    _retry_critical_analysis_groups(
        client,
        analysis_node_groups,
        analysis_relation_groups,
        batch_size,
        sync_run=verification_sync_run,
    )
    _verify_expected_group_counts(
        client,
        analysis_node_groups if targeted_mode else {},
        analysis_relation_groups if targeted_mode else {},
        strict_analysis=not targeted_mode,
        sync_run=verification_sync_run,
    )
    if targeted_mode:
        _verify_expected_group_counts(
            client,
            node_groups,
            relation_groups,
            strict_analysis=False,
            sync_run=verification_sync_run,
        )


def sync_snapshot(
    snapshot: GraphSnapshot,
    root: Path,
    http_uri: str | None,
    options: SyncApplyOptions | int | None = None,
    selection: SnapshotSelection | None = None,
    **legacy_kwargs: object,
) -> None:
    resolved_options = _resolved_sync_apply_options(options, legacy_kwargs)
    if selection is None:
        selection = _selection_from_legacy_kwargs(legacy_kwargs)
    base_uri, username, password, database = resolve_neo4j_connection(root, http_uri)
    client = Neo4jHttpClient(base_uri, username, password, database)
    sync_run = _sync_run_id()
    snapshot = _filtered_snapshot(snapshot, selection=selection)
    targeted_mode = selection.targeted_mode()
    if targeted_mode:
        _ensure_targeted_apply_prerequisites(
            client,
            snapshot,
            mode_description=selection.mode_description(),
        )
    (
        managed_labels,
        node_groups,
        relation_groups,
        core_node_groups,
        analysis_node_groups,
        core_relation_groups,
        analysis_relation_groups,
    ) = _statement_groups(
        snapshot,
        sync_run,
    )
    _delete_managed_wave_if_requested(client, managed_labels, resolved_options)
    _apply_snapshot_statement_groups(
        client,
        snapshot,
        options=resolved_options,
        relation_groups=relation_groups,
        core_node_groups=core_node_groups,
        analysis_node_groups=analysis_node_groups,
        core_relation_groups=core_relation_groups,
        analysis_relation_groups=analysis_relation_groups,
    )
    _verify_sync_snapshot(
        client,
        targeted_mode=targeted_mode,
        prune_stale=resolved_options.prune_stale,
        sync_run=sync_run,
        batch_size=resolved_options.batch_size,
        node_groups=node_groups,
        relation_groups=relation_groups,
        analysis_node_groups=analysis_node_groups,
        analysis_relation_groups=analysis_relation_groups,
    )
    _prune_managed_graph_if_requested(
        client,
        resolved_options,
        sync_run,
        managed_labels,
    )


def _has_required_relation(
    relation_keys: set[tuple[str, str, str, str]],
    *,
    source_labels: set[str],
    relation_type: str,
    target_labels: set[str] | None = None,
) -> bool:
    for source_label, _, current_relation_type, target_label in relation_keys:
        if source_label not in source_labels or current_relation_type != relation_type:
            continue
        if target_labels is None or target_label in target_labels:
            return True
    return False


def _append_missing_relation_issues(
    issues: list[str],
    relation_keys: set[tuple[str, str, str, str]],
    requirements: tuple[tuple[str, set[str], str, set[str] | None], ...],
) -> None:
    for message, source_labels, relation_type, target_labels in requirements:
        if _has_required_relation(
            relation_keys,
            source_labels=source_labels,
            relation_type=relation_type,
            target_labels=target_labels,
        ):
            continue
        issues.append(message)


def _missing_node_support_names(
    snapshot: GraphSnapshot,
    label: str,
    is_supported: Callable[[NodeKey], bool],
) -> list[str]:
    return sorted(
        key.name
        for key in (
            node.key for node in snapshot.nodes.values() if node.key.label == label
        )
        if not is_supported(key)
    )


def _append_support_issue(issues: list[str], prefix: str, names: list[str]) -> None:
    if names:
        issues.append(f"{prefix}: {', '.join(names[:10])}")
