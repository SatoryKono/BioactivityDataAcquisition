"""Construction helper for serialized composite checkpoint state."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.composite.checkpoint.state_parsing import (
    parse_dependency_results,
    parse_enrichment_results,
    parse_optional_string,
    parse_seed_result,
    parse_state,
    parse_timestamp,
)
from bioetl.domain.normalization import normalize_runtime_anchor_payload
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.application.composite.checkpoint.state import CompositeCheckpointState


def _legacy_cv_flags(data: JsonDict) -> tuple[bool, bool, bool]:
    """Read legacy migration flags from explicit markers and retired enum values."""
    state_value = data.get("state")
    is_completed = state_value == "cross_validation_completed"
    is_running = state_value == "cross_validation_running"
    return (
        bool(data.get("merge_completed", False) or is_completed),
        data.get("legacy_cv_completion_pending") is True or is_completed,
        data.get("legacy_cv_resume_blocked") is True or is_running,
    )


def build_checkpoint_state(
    state_type: type[CompositeCheckpointState],
    data: JsonDict,
) -> CompositeCheckpointState:
    """Build a checkpoint state from its persisted dictionary representation."""
    normalized_anchors = normalize_runtime_anchor_payload(
        {
            "effective_config_hash": data.get("effective_config_hash"),
            "effective_config_artifact_id": data.get("effective_config_artifact_id"),
            "execution_fingerprint": data.get("execution_fingerprint"),
            "dq_contract_compatibility_hash": data.get(
                "dq_contract_compatibility_hash"
            ),
            "input_snapshot_fingerprint": data.get("input_snapshot_fingerprint"),
            "contract_ref": data.get("contract_ref"),
            "contract_version": data.get("contract_version"),
            "manifest_id": data.get("manifest_id"),
            "composite_run_identity": data.get("composite_run_identity"),
        }
    )
    merge_completed, completion_pending, resume_blocked = _legacy_cv_flags(data)
    return state_type(
        composite_name=data["composite_name"],
        run_id=data["run_id"],
        state=parse_state(data.get("state")),
        seed_completed=data.get("seed_completed", False),
        seed_result=parse_seed_result(data.get("seed_result")),
        completed_dependencies=frozenset(data.get("completed_dependencies", [])),
        dependency_results=parse_dependency_results(data.get("dependency_results")),
        completed_enrichers=frozenset(data.get("completed_enrichers", [])),
        enrichment_results=parse_enrichment_results(data.get("enrichment_results")),
        merge_completed=merge_completed,
        merge_result=data.get("merge_result"),
        legacy_cv_completion_pending=completion_pending,
        legacy_cv_resume_blocked=resume_blocked,
        checkpoint_schema_version=data.get("checkpoint_schema_version", "1.0.0"),
        effective_config_hash=normalized_anchors["effective_config_hash"] or "",
        effective_config_artifact_id=(
            normalized_anchors["effective_config_artifact_id"] or ""
        ),
        execution_fingerprint=normalized_anchors["execution_fingerprint"] or "",
        dq_contract_compatibility_hash=(
            normalized_anchors["dq_contract_compatibility_hash"] or ""
        ),
        input_snapshot_fingerprint=(
            normalized_anchors["input_snapshot_fingerprint"] or ""
        ),
        contract_ref=normalized_anchors["contract_ref"] or "",
        contract_version=normalized_anchors["contract_version"] or "",
        manifest_id=normalized_anchors["manifest_id"] or "",
        composite_run_identity=normalized_anchors["composite_run_identity"] or "",
        last_event_id=parse_optional_string(data.get("last_event_id")),
        last_event_occurred_at=parse_timestamp(data.get("last_event_occurred_at")),
        created_at=parse_timestamp(data.get("created_at")),
        updated_at=parse_timestamp(data.get("updated_at")),
    )
