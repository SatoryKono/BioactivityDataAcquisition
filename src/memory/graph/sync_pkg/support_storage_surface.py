"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.snapshotrelationindex import (
    _has_inbound_relation,
    _has_outbound_relation,
    _SnapshotRelationIndex,
)

__all__ = [
    "_support_cli_command_surface",
    "_support_cli_option_surface",
    "_support_doc_claim_surface",
    "_support_schema_field_surface",
    "_support_storage_surface",
    "_support_workflow_artifact_surface",
    "_support_workflow_call_surface",
    "_support_workflow_job_surface",
    "_support_workflow_output_surface",
]


def _support_storage_surface(
    relation_index: _SnapshotRelationIndex, key: NodeKey
) -> bool:
    return _has_inbound_relation(
        relation_index,
        key,
        {"WRITES_TO", "DEPENDS_ON", "DEFINED_BY"},
        source_labels={
            "pipeline_surface",
            "entity_config",
            "runtime_evidence_surface",
            "storage_surface",
        },
    ) or _has_outbound_relation(
        relation_index,
        key,
        {"PROMOTES_TO", "DEFINED_BY"},
    )


def _support_schema_field_surface(
    relation_index: _SnapshotRelationIndex, key: NodeKey
) -> bool:
    return _has_inbound_relation(
        relation_index,
        key,
        {"HAS_SCHEMA_FIELD"},
        source_labels={"storage_surface", "contract_surface"},
    ) and _has_outbound_relation(
        relation_index,
        key,
        {"DEFINED_BY", "PROMOTES_FIELD_TO", "DERIVES_FIELD_FROM"},
    )


def _support_workflow_job_surface(
    relation_index: _SnapshotRelationIndex, key: NodeKey
) -> bool:
    return _has_inbound_relation(
        relation_index, key, {"CONTAINS"}, source_labels={"workflow_surface"}
    )


def _support_cli_command_surface(
    relation_index: _SnapshotRelationIndex, key: NodeKey
) -> bool:
    return _has_outbound_relation(
        relation_index,
        key,
        {"RUNS_VIA", "EXECUTES_GATE", "DEPENDS_ON"},
    ) or _has_inbound_relation(
        relation_index,
        key,
        {"HAS_CLI_COMMAND"},
        source_labels={"project"},
    )


def _support_workflow_artifact_surface(
    relation_index: _SnapshotRelationIndex, key: NodeKey
) -> bool:
    return _has_inbound_relation(
        relation_index,
        key,
        {"PUBLISHES_ARTIFACT", "DEPENDS_ON"},
        source_labels={"workflow_job_surface"},
    )


def _support_workflow_call_surface(
    relation_index: _SnapshotRelationIndex, key: NodeKey
) -> bool:
    return _has_inbound_relation(
        relation_index,
        key,
        {"CALLS_WORKFLOW"},
        source_labels={"workflow_surface", "workflow_job_surface"},
    ) or _has_outbound_relation(
        relation_index,
        key,
        {"DEPENDS_ON"},
        target_labels={"workflow_surface"},
    )


def _support_workflow_output_surface(
    relation_index: _SnapshotRelationIndex, key: NodeKey
) -> bool:
    return _has_inbound_relation(
        relation_index,
        key,
        {"EMITS_OUTPUT"},
        source_labels={"workflow_surface", "workflow_job_surface"},
    )


def _support_cli_option_surface(
    relation_index: _SnapshotRelationIndex, key: NodeKey
) -> bool:
    return _has_inbound_relation(
        relation_index,
        key,
        {"ACCEPTS_OPTION"},
        source_labels={"cli_command_surface"},
    )


def _support_doc_claim_surface(
    relation_index: _SnapshotRelationIndex, key: NodeKey
) -> bool:
    return _has_inbound_relation(
        relation_index,
        key,
        {"ASSERTS"},
        source_labels={"doc_source_surface", "doc_artifact", "policy_surface"},
    ) or _has_outbound_relation(
        relation_index,
        key,
        {"ASSERTS_ABOUT"},
    )
