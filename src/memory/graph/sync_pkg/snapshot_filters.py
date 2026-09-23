"""Snapshot shard filtering extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_convert import _as_iterable
from memory.graph.sync_pkg._core_models import NodeKey, SnapshotSelection
from memory.graph.sync_pkg.apply_groups import (
    ANALYSIS_NODE_LABELS,
    ANALYSIS_RELATION_TYPES,
)
from memory.graph.sync_pkg.graph_snapshot import GraphRelation, GraphSnapshot
from memory.graph.sync_pkg.shard_filters import (
    DOCS_DRIFT_FILTER,
    RUNTIME_EVIDENCE_LAYER_FILTER,
    STORAGE_LAYER_FILTER,
    WORKFLOW_GRAPH_FILTER,
    ShardFilter,
    ShardFilterSpec,
)

__all__ = [
    "COMPLEXITY_NODE_LABELS",
    "COMPLEXITY_RELATION_TYPES",
    "RETIREMENT_NODE_LABELS",
    "RETIREMENT_RELATION_TYPES",
    "RelationKey",
    "_allowed_analysis_relation_types",
    "_build_allowed_labels",
    "_filtered_snapshot",
    "_include_analysis_relation",
    "_include_filtered_relation",
    "_include_shard_filtered_relation",
    "_include_shard_relation_nodes",
    "_relation_matches_shard_filters",
    "_resolved_snapshot_selection",
    "_seed_filtered_nodes",
    "_selected_shard_filters",
]

type RelationKey = tuple[NodeKey, str, NodeKey]

RETIREMENT_NODE_LABELS: tuple[str, ...] = ("retirement_candidate",)
RETIREMENT_RELATION_TYPES: tuple[str, ...] = ("CANDIDATE_FOR_REMOVAL",)
COMPLEXITY_NODE_LABELS: tuple[str, ...] = ("complexity_candidate",)
COMPLEXITY_RELATION_TYPES: tuple[str, ...] = (
    "HAS_COMPLEXITY_SIGNAL",
    "CANDIDATE_FOR_SIMPLIFICATION",
    "JUSTIFIED_BY_RUNTIME",
    "BLOCKED_BY_VARIANCE",
)


def _selected_shard_filters(
    selection: SnapshotSelection,
) -> tuple[ShardFilterSpec, ...]:
    selected: list[ShardFilterSpec] = []
    if selection.only_storage_layer:
        selected.append(STORAGE_LAYER_FILTER)
    if selection.only_runtime_evidence_layer:
        selected.append(RUNTIME_EVIDENCE_LAYER_FILTER)
    if selection.only_workflow_graph:
        selected.append(WORKFLOW_GRAPH_FILTER)
    if selection.only_docs_drift:
        selected.append(DOCS_DRIFT_FILTER)
    return tuple(selected)


def _allowed_analysis_relation_types(
    selection: SnapshotSelection,
) -> set[str]:
    allowed: set[str] = set()
    if selection.only_analysis_layer:
        allowed.update(ANALYSIS_RELATION_TYPES)
    if selection.only_retirement_layer:
        allowed.update(RETIREMENT_RELATION_TYPES)
    if selection.only_complexity_layer:
        allowed.update(COMPLEXITY_RELATION_TYPES)
    return allowed or set(ANALYSIS_RELATION_TYPES)


def _build_allowed_labels(
    selection: SnapshotSelection,
    shard_filters: tuple[ShardFilterSpec, ...],
) -> set[str]:
    allowed_labels = set(selection.only_labels)
    for shard_labels, _ in shard_filters:
        allowed_labels.update(shard_labels)
    if selection.only_analysis_layer:
        allowed_labels.update(ANALYSIS_NODE_LABELS)
    if selection.only_retirement_layer:
        allowed_labels.update(RETIREMENT_NODE_LABELS)
    if selection.only_complexity_layer:
        allowed_labels.update(COMPLEXITY_NODE_LABELS)
    return allowed_labels


def _relation_matches_shard_filters(
    relation: GraphRelation, shard_filters: tuple[ShardFilterSpec, ...]
) -> bool:
    for _, relation_specs in shard_filters:
        for relation_type, source_labels, target_labels in relation_specs:
            if (
                relation.relation_type == relation_type
                and relation.source.label in source_labels
                and relation.target.label in target_labels
            ):
                return True
    return False


def _include_analysis_relation(
    filtered: GraphSnapshot,
    rel_key: tuple[NodeKey, str, NodeKey],
    relation: GraphRelation,
    *,
    allowed_labels: set[str],
    allowed_analysis_relation_types: set[str],
    label_scoped_only: bool,
    selection: SnapshotSelection,
) -> bool:
    if relation.relation_type not in ANALYSIS_RELATION_TYPES:
        return False
    if relation.relation_type not in allowed_analysis_relation_types:
        return True
    if label_scoped_only:
        if (
            relation.source.label in allowed_labels
            and relation.target.label in allowed_labels
        ):
            filtered.relations[rel_key] = relation
        return True
    if (
        selection.only_analysis_layer
        or relation.source.label in allowed_labels
        or relation.target.label in allowed_labels
    ):
        filtered.relations[rel_key] = relation
    return True


def _seed_filtered_nodes(
    filtered: GraphSnapshot,
    snapshot: GraphSnapshot,
    allowed_labels: set[str],
    *,
    has_shard_filters: bool,
) -> None:
    if has_shard_filters:
        return
    for key, node in snapshot.nodes.items():
        if key.label in allowed_labels:
            filtered.nodes[key] = node


def _include_shard_relation_nodes(
    filtered: GraphSnapshot, snapshot: GraphSnapshot, relation: GraphRelation
) -> None:
    if relation.source in snapshot.nodes:
        filtered.nodes.setdefault(relation.source, snapshot.nodes[relation.source])
    if relation.target in snapshot.nodes:
        filtered.nodes.setdefault(relation.target, snapshot.nodes[relation.target])


def _filtered_snapshot(
    snapshot: GraphSnapshot,
    selection: SnapshotSelection | None = None,
    **legacy_selection: object,
) -> GraphSnapshot:
    selection = _resolved_snapshot_selection(selection, legacy_selection)
    shard_filters = _selected_shard_filters(selection)
    allowed_labels = _build_allowed_labels(
        selection,
        shard_filters,
    )
    if not allowed_labels:
        return snapshot

    label_scoped_only = (
        bool(selection.only_labels) and not selection.has_targeted_filters()
    )
    filtered = GraphSnapshot()
    allowed_analysis_relation_types = _allowed_analysis_relation_types(selection)
    has_shard_filters = bool(shard_filters)
    _seed_filtered_nodes(
        filtered, snapshot, allowed_labels, has_shard_filters=has_shard_filters
    )

    for rel_key, relation in snapshot.relations.items():
        _include_filtered_relation(
            filtered,
            snapshot,
            rel_key,
            relation,
            allowed_labels=allowed_labels,
            allowed_analysis_relation_types=allowed_analysis_relation_types,
            label_scoped_only=label_scoped_only,
            selection=selection,
            has_shard_filters=has_shard_filters,
            shard_filters=shard_filters,
        )
    return filtered


def _resolved_snapshot_selection(
    selection: SnapshotSelection | None,
    legacy_selection: dict[str, object],
) -> SnapshotSelection:
    if selection is not None:
        return selection
    return SnapshotSelection(
        only_labels=tuple(
            str(item) for item in _as_iterable(legacy_selection.get("only_labels"))
        ),
        only_analysis_layer=bool(legacy_selection.get("only_analysis_layer", False)),
        only_retirement_layer=bool(
            legacy_selection.get("only_retirement_layer", False)
        ),
        only_complexity_layer=bool(
            legacy_selection.get("only_complexity_layer", False)
        ),
        only_storage_layer=bool(legacy_selection.get("only_storage_layer", False)),
        only_runtime_evidence_layer=bool(
            legacy_selection.get("only_runtime_evidence_layer", False)
        ),
        only_workflow_graph=bool(legacy_selection.get("only_workflow_graph", False)),
        only_docs_drift=bool(legacy_selection.get("only_docs_drift", False)),
    )


def _include_filtered_relation(
    filtered: GraphSnapshot,
    snapshot: GraphSnapshot,
    rel_key: RelationKey,
    relation: GraphRelation,
    *,
    allowed_labels: set[str],
    allowed_analysis_relation_types: set[str],
    label_scoped_only: bool,
    selection: SnapshotSelection,
    has_shard_filters: bool,
    shard_filters: tuple[ShardFilter, ...],
) -> None:
    if _include_analysis_relation(
        filtered,
        rel_key,
        relation,
        allowed_labels=allowed_labels,
        allowed_analysis_relation_types=allowed_analysis_relation_types,
        label_scoped_only=label_scoped_only,
        selection=selection,
    ):
        return
    if has_shard_filters:
        _include_shard_filtered_relation(
            filtered, snapshot, rel_key, relation, shard_filters
        )
        return
    if (
        relation.source.label in allowed_labels
        and relation.target.label in allowed_labels
    ):
        filtered.relations[rel_key] = relation


def _include_shard_filtered_relation(
    filtered: GraphSnapshot,
    snapshot: GraphSnapshot,
    rel_key: RelationKey,
    relation: GraphRelation,
    shard_filters: tuple[ShardFilter, ...],
) -> None:
    if _relation_matches_shard_filters(relation, shard_filters):
        _include_shard_relation_nodes(filtered, snapshot, relation)
        filtered.relations[rel_key] = relation
