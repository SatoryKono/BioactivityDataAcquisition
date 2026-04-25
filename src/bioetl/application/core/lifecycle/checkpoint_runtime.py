"""Pure runtime helpers for checkpoint manager compatibility handling."""

from __future__ import annotations

from typing import Literal

from bioetl.domain.ports import LoggerPort
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata

CheckpointCompatibilityPolicy = Literal[
    "observe", "legacy_observe", "soft_fail", "hard_fail"
]
CheckpointCompatibilityDisposition = Literal[
    "observe_blocked_identity",
    "legacy_observe_loaded_degraded",
    "observe_loaded_degraded",
    "soft_fail_blocked",
    "hard_fail_raised",
]


def validate_compatibility_policy(
    policy: CheckpointCompatibilityPolicy,
) -> CheckpointCompatibilityPolicy:
    """Validate supported checkpoint compatibility handling modes."""
    allowed: tuple[CheckpointCompatibilityPolicy, ...] = (
        "observe",
        "legacy_observe",
        "soft_fail",
        "hard_fail",
    )
    if policy not in allowed:
        raise ValueError(
            f"Unsupported checkpoint compatibility policy: {policy!r}. "
            f"Expected one of {allowed}."
        )
    return policy


def resolve_current_metadata(
    current_metadata: CheckpointMetadata | None,
    *,
    default_metadata: CheckpointMetadata | None,
) -> CheckpointMetadata | None:
    """Return explicit metadata when provided, otherwise fall back to default."""
    return current_metadata if current_metadata is not None else default_metadata


def _prefer_identity_value(
    current_value: str | None,
    identity_value: str | None,
) -> str | None:
    """Prefer persisted execution identity, then fall back to current identity."""
    return current_value if current_value is not None else identity_value


def _prefer_identity_flag(
    current_value: bool | None,
    identity_value: bool | None,
) -> bool | None:
    """Prefer persisted boolean identity flag, then fall back to current identity."""
    return current_value if current_value is not None else identity_value


def _prefer_identity_sequence(
    current_value: tuple[str, ...],
    identity_value: tuple[str, ...],
) -> tuple[str, ...]:
    """Prefer persisted non-empty tuple values, otherwise use identity fallback."""
    return current_value if current_value else identity_value


def enrich_metadata_with_execution_identity(
    metadata: CheckpointMetadata,
    *,
    identity: CheckpointMetadata | None,
) -> CheckpointMetadata:
    """Fill checkpoint metadata gaps from current execution identity."""
    if identity is None:
        return metadata
    return CheckpointMetadata(
        records_processed=metadata.records_processed,
        dq_contract_compatibility_hash=_prefer_identity_value(
            metadata.dq_contract_compatibility_hash,
            identity.dq_contract_compatibility_hash,
        ),
        dq_policy_hash=_prefer_identity_value(
            metadata.dq_policy_hash,
            identity.dq_policy_hash,
        ),
        dq_rule_bundle_version=_prefer_identity_value(
            metadata.dq_rule_bundle_version,
            identity.dq_rule_bundle_version,
        ),
        pipeline_name=_prefer_identity_value(
            metadata.pipeline_name,
            identity.pipeline_name,
        ),
        run_type=_prefer_identity_value(
            metadata.run_type,
            identity.run_type,
        ),
        pipeline_version=_prefer_identity_value(
            metadata.pipeline_version,
            identity.pipeline_version,
        ),
        effective_config_hash=_prefer_identity_value(
            metadata.effective_config_hash,
            identity.effective_config_hash,
        ),
        effective_config_artifact_id=_prefer_identity_value(
            metadata.effective_config_artifact_id,
            identity.effective_config_artifact_id,
        ),
        execution_fingerprint=_prefer_identity_value(
            metadata.execution_fingerprint,
            identity.execution_fingerprint,
        ),
        composite_run_identity=_prefer_identity_value(
            metadata.composite_run_identity,
            identity.composite_run_identity,
        ),
        manifest_id=_prefer_identity_value(
            metadata.manifest_id,
            identity.manifest_id,
        ),
        contract_ref=_prefer_identity_value(
            metadata.contract_ref,
            identity.contract_ref,
        ),
        contract_version=_prefer_identity_value(
            metadata.contract_version,
            identity.contract_version,
        ),
        exact_replay=_prefer_identity_flag(
            metadata.exact_replay,
            identity.exact_replay,
        ),
        input_snapshot_ids=_prefer_identity_sequence(
            metadata.input_snapshot_ids,
            identity.input_snapshot_ids,
        ),
        input_snapshot_fingerprint=_prefer_identity_value(
            metadata.input_snapshot_fingerprint,
            identity.input_snapshot_fingerprint,
        ),
        memory_decision_trace=(
            metadata.memory_decision_trace or identity.memory_decision_trace
        ),
        run_context=metadata.run_context or identity.run_context,
    )


def handle_incompatible_checkpoint(
    *,
    logger: LoggerPort,
    pipeline_name: str,
    compatibility_policy: CheckpointCompatibilityPolicy,
    current_metadata: CheckpointMetadata | None,
    checkpoint_metadata: CheckpointMetadata,
    execution_identity_compatible: bool,
    identity_continuity_proven: bool,
    messages: list[str],
) -> CheckpointMetadata | None:
    """Apply configured policy to an incompatible checkpoint."""
    disposition = resolve_incompatible_checkpoint_disposition(
        compatibility_policy=compatibility_policy,
        execution_identity_compatible=execution_identity_compatible,
        identity_continuity_proven=identity_continuity_proven,
    )
    forced_resume_rejection = disposition == "observe_blocked_identity"
    degraded_resume_loaded = disposition in {
        "observe_loaded_degraded",
        "legacy_observe_loaded_degraded",
    }
    payload = {
        "pipeline": pipeline_name,
        "compatibility_policy": compatibility_policy,
        "compatibility_disposition": disposition,
        "resume_rejected": not degraded_resume_loaded or forced_resume_rejection,
        "execution_identity_compatible": execution_identity_compatible,
        "identity_continuity_proven": identity_continuity_proven,
        "identity_mismatch_forces_rejection": forced_resume_rejection,
        "messages": messages,
        "checkpoint_metadata": checkpoint_metadata.to_dict(),
        "current_identity": _checkpoint_identity_payload(current_metadata),
        "checkpoint_identity": _checkpoint_identity_payload(checkpoint_metadata),
    }
    if disposition == "observe_blocked_identity":
        logger.warning(
            "Checkpoint execution identity mismatch observed; resume blocked "
            "despite observe policy (resume blocked despite degraded observe policy).",
            **payload,
        )
        return None
    if disposition == "legacy_observe_loaded_degraded":
        logger.warning(
            "Checkpoint compatibility mismatch observed; legacy degraded resume continues.",
            **payload,
        )
        return checkpoint_metadata
    if disposition == "observe_loaded_degraded":
        logger.warning(
            "Checkpoint non-identity compatibility mismatch observed; resume continues.",
            **payload,
        )
        return checkpoint_metadata
    if disposition == "soft_fail_blocked":
        logger.warning(
            "Checkpoint compatibility mismatch; resume blocked by soft_fail policy.",
            **payload,
        )
        return None
    raise ValueError(
        "Checkpoint compatibility mismatch and hard_fail policy is enabled: "
        + "; ".join(messages)
    )


def _checkpoint_identity_payload(
    metadata: CheckpointMetadata | None,
) -> dict[str, object | None]:
    """Return the compact identity anchors most useful for resume forensics."""
    if metadata is None:
        return {
            "composite_run_identity": None,
            "execution_fingerprint": None,
            "manifest_id": None,
            "effective_config_hash": None,
            "contract_ref": None,
            "contract_version": None,
            "exact_replay": None,
            "input_snapshot_ids": [],
        }
    return {
        "composite_run_identity": metadata.composite_run_identity,
        "execution_fingerprint": metadata.execution_fingerprint,
        "manifest_id": metadata.manifest_id,
        "effective_config_hash": metadata.effective_config_hash,
        "contract_ref": metadata.contract_ref,
        "contract_version": metadata.contract_version,
        "exact_replay": metadata.exact_replay,
        "input_snapshot_ids": list(metadata.input_snapshot_ids),
    }


def resolve_incompatible_checkpoint_disposition(
    *,
    compatibility_policy: CheckpointCompatibilityPolicy,
    execution_identity_compatible: bool,
    identity_continuity_proven: bool = True,
) -> CheckpointCompatibilityDisposition:
    """Return the bounded incompatibility disposition for telemetry and logging."""
    if compatibility_policy == "observe":
        if not identity_continuity_proven or not execution_identity_compatible:
            return "observe_blocked_identity"
        return "observe_loaded_degraded"
    if compatibility_policy == "legacy_observe":
        if not identity_continuity_proven:
            return "observe_blocked_identity"
        if execution_identity_compatible:
            return "legacy_observe_loaded_degraded"
        return "observe_blocked_identity"
    if compatibility_policy == "soft_fail":
        return "soft_fail_blocked"
    return "hard_fail_raised"


__all__ = [
    "CheckpointCompatibilityDisposition",
    "CheckpointCompatibilityPolicy",
    "enrich_metadata_with_execution_identity",
    "handle_incompatible_checkpoint",
    "resolve_current_metadata",
    "resolve_incompatible_checkpoint_disposition",
    "validate_compatibility_policy",
]
