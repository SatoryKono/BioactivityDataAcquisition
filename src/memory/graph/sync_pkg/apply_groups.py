"""Apply grouping and prune orchestration extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from memory.graph.sync_pkg._core_convert import (
    _as_iterable,
    _as_mapping,
    _coerce_int,
    _optional_text,
)
from memory.graph.sync_pkg._core_models import (
    JsonValue,
    SnapshotSelection,
    SyncApplyOptions,
)
from memory.graph.sync_pkg.apply_runtime import _execute_grouped_statements
from memory.graph.sync_pkg.neo4j_statements import (
    _delete_managed_wave_nodes_statement,
    _node_statement,
    _prune_legacy_unmanaged_nodes_statement,
    _prune_stale_nodes_statement,
    _prune_stale_relations_statement,
    _relation_statement,
    _reset_managed_relations_statement,
)
from memory.graph.sync_pkg.transport import Neo4jHttpClient

if TYPE_CHECKING:
    from memory.graph.sync_pkg._core import GraphSnapshot

__all__ = [
    "ANALYSIS_NODE_LABELS",
    "ANALYSIS_RELATION_TYPES",
    "DEFAULT_LEGACY_PRUNE_LABELS",
    "_analysis_batch_size",
    "_analysis_node_batch_size",
    "_analysis_relation_batch_size",
    "_apply_snapshot_statement_groups",
    "_delete_managed_wave_batch_size",
    "_delete_managed_wave_if_requested",
    "_execute_prune_stale_statements",
    "_legacy_or_default_batch_size",
    "_node_statement_groups",
    "_partition_groups",
    "_prune_managed_graph_if_requested",
    "_relation_statement_groups",
    "_reset_managed_relations_if_requested",
    "_resolved_sync_apply_options",
    "_selection_from_legacy_kwargs",
    "_statement_groups",
    "_verification_sync_run",
]

ANALYSIS_NODE_LABELS: tuple[str, ...] = (
    "retirement_candidate",
    "complexity_candidate",
)
ANALYSIS_RELATION_TYPES: tuple[str, ...] = (
    "CANDIDATE_FOR_REMOVAL",
    "HAS_COMPLEXITY_SIGNAL",
    "CANDIDATE_FOR_SIMPLIFICATION",
    "JUSTIFIED_BY_RUNTIME",
    "BLOCKED_BY_VARIANCE",
)
DEFAULT_LEGACY_PRUNE_LABELS: tuple[str, ...] = (
    "project",
    "repo_zone",
    "directory_surface",
    "file_surface",
    "doc_source_surface",
    "doc_artifact",
    "decision",
    "risk",
    "policy_surface",
    "layer_family",
    "package_family",
    "module_surface",
    "class_surface",
    "function_surface",
    "method_surface",
    "duplication_cluster",
    "retirement_candidate",
    "complexity_candidate",
    "port_surface",
    "adapter_surface",
    "adapter_impl_surface",
    "pipeline_surface",
    "contract_surface",
    "alert_surface",
    "provider_surface",
    "entity_config",
    "composite_config",
    "config_artifact",
    "dashboard_surface",
    "quality_gate",
    "script_surface",
    "execution_path",
    "test_surface",
    "test_artifact",
    "storage_surface",
    "runtime_evidence_surface",
    "control_plane_artifact_surface",
    "run_instance_surface",
    "runtime_state_surface",
    "schema_field_surface",
    "workflow_surface",
    "workflow_job_surface",
    "workflow_call_surface",
    "workflow_matrix_variant_surface",
    "workflow_output_surface",
    "workflow_action_surface",
    "workflow_artifact_surface",
    "workflow_secret_surface",
    "cli_command_surface",
    "cli_option_surface",
    "doc_claim_surface",
)


def _resolved_sync_apply_options(
    options: SyncApplyOptions | int | None,
    legacy_kwargs: dict[str, object],
) -> SyncApplyOptions:
    if isinstance(options, SyncApplyOptions):
        return options

    resolved_batch_size = _legacy_or_default_batch_size(options, legacy_kwargs)
    if not isinstance(resolved_batch_size, int):
        raise TypeError("sync_snapshot requires batch_size or SyncApplyOptions")
    return SyncApplyOptions(
        batch_size=resolved_batch_size,
        prune_stale=bool(legacy_kwargs.get("prune_stale", False)),
        full_reset_managed_wave=bool(
            legacy_kwargs.get("full_reset_managed_wave", False)
        ),
        prune_legacy_unmanaged=bool(legacy_kwargs.get("prune_legacy_unmanaged", False)),
    )


def _legacy_or_default_batch_size(
    options: SyncApplyOptions | int | None,
    legacy_kwargs: dict[str, object],
) -> object:
    legacy_batch_size = legacy_kwargs.get("batch_size")
    return legacy_batch_size if legacy_batch_size is not None else options


def _selection_from_legacy_kwargs(
    legacy_kwargs: dict[str, object],
) -> SnapshotSelection:
    return SnapshotSelection(
        only_labels=tuple(
            str(item) for item in _as_iterable(legacy_kwargs.get("only_labels"))
        ),
        only_analysis_layer=bool(legacy_kwargs.get("only_analysis_layer", False)),
        only_retirement_layer=bool(legacy_kwargs.get("only_retirement_layer", False)),
        only_complexity_layer=bool(legacy_kwargs.get("only_complexity_layer", False)),
        only_storage_layer=bool(legacy_kwargs.get("only_storage_layer", False)),
        only_runtime_evidence_layer=bool(
            legacy_kwargs.get("only_runtime_evidence_layer", False)
        ),
        only_workflow_graph=bool(legacy_kwargs.get("only_workflow_graph", False)),
        only_docs_drift=bool(legacy_kwargs.get("only_docs_drift", False)),
    )


def _statement_groups(
    snapshot: GraphSnapshot,
    sync_run: str,
) -> tuple[
    list[str],
    dict[str, list[dict[str, JsonValue]]],
    dict[str, list[dict[str, JsonValue]]],
    dict[str, list[dict[str, JsonValue]]],
    dict[str, list[dict[str, JsonValue]]],
    dict[str, list[dict[str, JsonValue]]],
    dict[str, list[dict[str, JsonValue]]],
]:
    managed_labels = sorted(
        {node.key.label for node in snapshot.nodes.values()}
        | set(DEFAULT_LEGACY_PRUNE_LABELS)
    )
    node_groups = _node_statement_groups(snapshot, sync_run)
    relation_groups = _relation_statement_groups(snapshot, sync_run)
    (
        core_node_groups,
        analysis_node_groups,
        core_relation_groups,
        analysis_relation_groups,
    ) = _partition_groups(node_groups, relation_groups)
    return (
        managed_labels,
        node_groups,
        relation_groups,
        core_node_groups,
        analysis_node_groups,
        core_relation_groups,
        analysis_relation_groups,
    )


def _node_statement_groups(
    snapshot: GraphSnapshot,
    sync_run: str,
) -> dict[str, list[dict[str, JsonValue]]]:
    node_groups: dict[str, list[dict[str, JsonValue]]] = {}
    for node in snapshot.nodes.values():
        node_groups.setdefault(node.key.label, []).append(
            _node_statement(node, sync_run)
        )
    return node_groups


def _relation_statement_groups(
    snapshot: GraphSnapshot,
    sync_run: str,
) -> dict[str, list[dict[str, JsonValue]]]:
    relation_groups: dict[str, list[dict[str, JsonValue]]] = {}
    for relation in snapshot.relations.values():
        relation_groups.setdefault(relation.relation_type, []).append(
            _relation_statement(relation, sync_run)
        )
    return relation_groups


def _delete_managed_wave_if_requested(
    client: Neo4jHttpClient,
    managed_labels: list[str],
    options: SyncApplyOptions,
) -> None:
    if not options.full_reset_managed_wave:
        return

    delete_batch_size = _delete_managed_wave_batch_size(options.batch_size)
    for label in managed_labels:
        while True:
            delete_statement = _delete_managed_wave_nodes_statement(
                label, delete_batch_size
            )
            statement_text = _optional_text(delete_statement.get("statement"))
            if statement_text is None:
                raise ValueError("delete statement is missing Cypher text")
            rows = client.query(
                statement_text,
                _as_mapping(delete_statement.get("parameters")),
            )
            deleted = _coerce_int(rows[0]["deleted"]) if rows else 0
            if deleted == 0:
                break


def _delete_managed_wave_batch_size(batch_size: int) -> int:
    return max(1, min(batch_size, 50))


def _analysis_batch_size(
    batch_size: int,
    *,
    reduced_limit: int,
    contains_high_priority: bool,
    high_priority_limit: int,
) -> int:
    if contains_high_priority:
        return max(1, min(batch_size, high_priority_limit))
    return max(1, min(batch_size, reduced_limit))


def _analysis_node_batch_size(
    analysis_node_groups: dict[str, list[dict[str, JsonValue]]],
    batch_size: int,
) -> int:
    # Keep complexity_candidate on its own serial batch; do not force every
    # analysis label down to 1 just because that group is present.
    remaining = {
        name: statements
        for name, statements in analysis_node_groups.items()
        if name != "complexity_candidate"
    }
    if not remaining:
        return 1
    return _analysis_batch_size(
        batch_size,
        reduced_limit=10,
        contains_high_priority="retirement_candidate" in remaining,
        high_priority_limit=5,
    )


def _analysis_relation_batch_size(
    analysis_relation_groups: dict[str, list[dict[str, JsonValue]]],
    batch_size: int,
) -> int:
    return _analysis_batch_size(
        batch_size,
        reduced_limit=5,
        contains_high_priority="CANDIDATE_FOR_REMOVAL" in analysis_relation_groups,
        high_priority_limit=3,
    )


def _verification_sync_run(
    targeted_mode: bool,
    prune_stale: bool,
    sync_run: str,
) -> str | None:
    if targeted_mode or prune_stale:
        return sync_run
    return None


def _prune_managed_graph_if_requested(
    client: Neo4jHttpClient,
    options: SyncApplyOptions,
    sync_run: str,
    managed_labels: list[str],
) -> None:
    if options.prune_stale:
        _execute_prune_stale_statements(client, sync_run)
    if options.prune_legacy_unmanaged:
        client.execute([_prune_legacy_unmanaged_nodes_statement(managed_labels)])


def _execute_prune_stale_statements(
    client: Neo4jHttpClient,
    sync_run: str,
) -> None:
    client.execute([_prune_stale_relations_statement(sync_run)])
    client.execute([_prune_stale_nodes_statement(sync_run)])


def _reset_managed_relations_if_requested(
    client: Neo4jHttpClient,
    snapshot: GraphSnapshot,
    relation_groups: dict[str, list[dict[str, JsonValue]]],
    options: SyncApplyOptions,
) -> None:
    if not options.prune_stale or not relation_groups:
        return
    relation_types = sorted(
        {relation.relation_type for relation in snapshot.relations.values()}
    )
    client.execute([_reset_managed_relations_statement(relation_types)])


def _apply_snapshot_statement_groups(
    client: Neo4jHttpClient,
    snapshot: GraphSnapshot,
    *,
    options: SyncApplyOptions,
    relation_groups: dict[str, list[dict[str, JsonValue]]],
    core_node_groups: dict[str, list[dict[str, JsonValue]]],
    analysis_node_groups: dict[str, list[dict[str, JsonValue]]],
    core_relation_groups: dict[str, list[dict[str, JsonValue]]],
    analysis_relation_groups: dict[str, list[dict[str, JsonValue]]],
) -> None:
    _execute_grouped_statements(
        client, core_node_groups, options.batch_size, "core node"
    )
    complexity_groups = {
        name: statements
        for name, statements in analysis_node_groups.items()
        if name == "complexity_candidate"
    }
    other_analysis_groups = {
        name: statements
        for name, statements in analysis_node_groups.items()
        if name != "complexity_candidate"
    }
    _execute_grouped_statements(
        client,
        other_analysis_groups,
        _analysis_node_batch_size(other_analysis_groups, options.batch_size),
        "analysis node",
    )
    _execute_grouped_statements(
        client,
        complexity_groups,
        1,
        "analysis node",
    )
    _reset_managed_relations_if_requested(client, snapshot, relation_groups, options)
    _execute_grouped_statements(
        client, core_relation_groups, options.batch_size, "core relation"
    )
    _execute_grouped_statements(
        client,
        analysis_relation_groups,
        _analysis_relation_batch_size(analysis_relation_groups, options.batch_size),
        "analysis relation",
    )


def _partition_groups(
    node_groups: dict[str, list[dict[str, JsonValue]]],
    relation_groups: dict[str, list[dict[str, JsonValue]]],
) -> tuple[
    dict[str, list[dict[str, JsonValue]]],
    dict[str, list[dict[str, JsonValue]]],
    dict[str, list[dict[str, JsonValue]]],
    dict[str, list[dict[str, JsonValue]]],
]:
    analysis_node_groups = {
        label: statements
        for label, statements in node_groups.items()
        if label in ANALYSIS_NODE_LABELS
    }
    core_node_groups = {
        label: statements
        for label, statements in node_groups.items()
        if label not in ANALYSIS_NODE_LABELS
    }
    analysis_relation_groups = {
        relation_type: statements
        for relation_type, statements in relation_groups.items()
        if relation_type in ANALYSIS_RELATION_TYPES
    }
    core_relation_groups = {
        relation_type: statements
        for relation_type, statements in relation_groups.items()
        if relation_type not in ANALYSIS_RELATION_TYPES
    }
    return (
        core_node_groups,
        analysis_node_groups,
        core_relation_groups,
        analysis_relation_groups,
    )
