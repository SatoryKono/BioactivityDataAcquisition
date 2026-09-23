"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.snapshotrelationindex import (
    _has_inbound_relation,
    _has_outbound_relation,
    _SnapshotRelationIndex,
)

__all__ = [
    "SNAPSHOT_REQUIRED_LABELS",
    "SNAPSHOT_REQUIRED_RELATION_TYPES",
    "_support_control_plane_artifact_surface",
    "_support_run_instance_surface",
    "_support_runtime_evidence_surface",
    "_support_runtime_state_surface",
]

SNAPSHOT_REQUIRED_LABELS = (
    "repo_zone",
    "directory_surface",
    "file_surface",
    "class_surface",
    "function_surface",
    "method_surface",
    "duplication_cluster",
    "complexity_candidate",
    "port_surface",
    "adapter_surface",
    "adapter_impl_surface",
    "pipeline_surface",
    "contract_surface",
    "alert_surface",
    "execution_path",
    "quality_gate",
    "dashboard_surface",
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
SNAPSHOT_REQUIRED_RELATION_TYPES = (
    "BACKS",
    "HOUSES",
    "DECLARES",
    "DEPENDS_ON",
    "GOVERNS",
    "RUNS_VIA",
    "VALIDATED_BY",
    "OBSERVED_BY",
    "TESTED_BY",
    "SAME_SHAPE_AS",
    "CAN_PROMOTE_TO",
    "COVERED_BY_TEST",
    "HAS_COMPLEXITY_SIGNAL",
    "CANDIDATE_FOR_SIMPLIFICATION",
    "DESCRIBES",
    "WRITES_TO",
    "PROMOTES_TO",
    "HAS_RUNTIME_EVIDENCE",
    "HAS_CONTROL_PLANE_ARTIFACT",
    "HAS_RUN_INSTANCE",
    "HAS_RUNTIME_STATE",
    "HAS_WORKFLOW",
    "HAS_CLI_COMMAND",
    "HAS_SCHEMA_FIELD",
    "CALLS_WORKFLOW",
    "HAS_MATRIX_VARIANT",
    "EMITS_OUTPUT",
    "ACCEPTS_OPTION",
    "SIDE_EFFECTS_ON",
    "ASSERTS",
    "ASSERTS_ABOUT",
    "EXECUTES_GATE",
    "EMITS_ARTIFACT",
    "MATERIALIZED_AS",
    "REFERENCES_ARTIFACT",
    "PROMOTES_FIELD_TO",
    "DERIVES_FIELD_FROM",
    "USES_ACTION",
    "PUBLISHES_ARTIFACT",
    "REQUIRES_SECRET",
    "CONSTRAINS",
)


def _support_runtime_evidence_surface(
    relation_index: _SnapshotRelationIndex, key: NodeKey
) -> bool:
    return _has_outbound_relation(
        relation_index, key, {"BACKED_BY", "DESCRIBED_IN", "WRITES_TO"}
    )


def _support_control_plane_artifact_surface(
    relation_index: _SnapshotRelationIndex, key: NodeKey
) -> bool:
    return _has_inbound_relation(
        relation_index,
        key,
        {"EMITS_ARTIFACT"},
        source_labels={"runtime_evidence_surface"},
    ) and _has_outbound_relation(
        relation_index,
        key,
        {"MATERIALIZED_AS"},
        target_labels={"storage_surface"},
    )


def _support_run_instance_surface(
    relation_index: _SnapshotRelationIndex, key: NodeKey
) -> bool:
    return _has_inbound_relation(
        relation_index,
        key,
        {"HAS_RUN_INSTANCE"},
        source_labels={"project"},
    ) and _has_outbound_relation(
        relation_index,
        key,
        {"REFERENCES_ARTIFACT"},
        target_labels={"control_plane_artifact_surface"},
    )


def _support_runtime_state_surface(
    relation_index: _SnapshotRelationIndex, key: NodeKey
) -> bool:
    return (
        _has_inbound_relation(
            relation_index,
            key,
            {"HAS_RUNTIME_STATE"},
            source_labels={"project", "run_instance_surface"},
        )
        and _has_outbound_relation(
            relation_index,
            key,
            {"DEPENDS_ON"},
        )
        and _has_outbound_relation(
            relation_index,
            key,
            {"REFERENCES_ARTIFACT"},
            target_labels={"control_plane_artifact_surface"},
        )
    )
