"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from collections.abc import Callable

from memory.graph.sync_pkg._core_models import JsonValue, NodeKey
from memory.graph.sync_pkg.snapshot_required_labels import (
    SNAPSHOT_REQUIRED_LABELS,
    SNAPSHOT_REQUIRED_RELATION_TYPES,
    _support_control_plane_artifact_surface,
    _support_run_instance_surface,
    _support_runtime_evidence_surface,
    _support_runtime_state_surface,
)
from memory.graph.sync_pkg.snapshotrelationindex import (
    _missing_required_population,
    _SnapshotRelationIndex,
)
from memory.graph.sync_pkg.support_storage_surface import (
    _support_cli_command_surface,
    _support_cli_option_surface,
    _support_doc_claim_surface,
    _support_schema_field_surface,
    _support_storage_surface,
    _support_workflow_artifact_surface,
    _support_workflow_call_surface,
    _support_workflow_job_surface,
    _support_workflow_output_surface,
)

__all__ = [
    "_required_population_issues",
    "_snapshot_support_specs",
]


def _snapshot_support_specs() -> tuple[
    tuple[str, str, Callable[[_SnapshotRelationIndex, NodeKey], bool]], ...
]:
    return (
        (
            "runtime evidence surfaces without support links",
            "runtime_evidence_surface",
            _support_runtime_evidence_surface,
        ),
        (
            "control-plane artifacts without runtime/storage links",
            "control_plane_artifact_surface",
            _support_control_plane_artifact_surface,
        ),
        (
            "run instance surfaces without support links",
            "run_instance_surface",
            _support_run_instance_surface,
        ),
        (
            "runtime state surfaces without support links",
            "runtime_state_surface",
            _support_runtime_state_surface,
        ),
        (
            "storage surfaces without ownership or lineage links",
            "storage_surface",
            _support_storage_surface,
        ),
        (
            "schema fields without storage/contract/lineage links",
            "schema_field_surface",
            _support_schema_field_surface,
        ),
        (
            "workflow jobs without workflow parent links",
            "workflow_job_surface",
            _support_workflow_job_surface,
        ),
        (
            "cli command surfaces without runtime/support links",
            "cli_command_surface",
            _support_cli_command_surface,
        ),
        (
            "workflow artifacts without job links",
            "workflow_artifact_surface",
            _support_workflow_artifact_surface,
        ),
        (
            "workflow calls without job/workflow links",
            "workflow_call_surface",
            _support_workflow_call_surface,
        ),
        (
            "workflow outputs without workflow/job links",
            "workflow_output_surface",
            _support_workflow_output_surface,
        ),
        (
            "cli options without command links",
            "cli_option_surface",
            _support_cli_option_surface,
        ),
        (
            "doc claims without doc/target links",
            "doc_claim_surface",
            _support_doc_claim_surface,
        ),
    )


def _required_population_issues(stats: dict[str, JsonValue]) -> list[str]:
    issues: list[str] = []
    issues.extend(
        _missing_required_population(stats["labels"], SNAPSHOT_REQUIRED_LABELS, "label")
    )
    issues.extend(
        _missing_required_population(
            stats["relation_types"], SNAPSHOT_REQUIRED_RELATION_TYPES, "relation"
        )
    )
    return issues
