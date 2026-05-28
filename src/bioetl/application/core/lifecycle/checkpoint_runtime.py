"""Pure runtime helpers for checkpoint manager compatibility handling."""

from __future__ import annotations

from dataclasses import replace
from typing import Literal

from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
)
from bioetl.domain.ports import LoggerPort
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata

CheckpointCompatibilityPolicy = Literal["observe", "soft_fail", "hard_fail"]
CheckpointCompatibilityDisposition = Literal[
    "observe_blocked_identity",
    "observe_loaded_degraded",
    "soft_fail_blocked",
    "hard_fail_raised",
]
CheckpointMissingContextDisposition = Literal[
    "missing_context_blocked",
    "missing_context_hard_fail_raised",
]


def validate_compatibility_policy(
    policy: CheckpointCompatibilityPolicy,
) -> CheckpointCompatibilityPolicy:
    """Validate supported checkpoint compatibility handling modes."""
    allowed: tuple[CheckpointCompatibilityPolicy, ...] = (
        "observe",
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


def missing_compatibility_context_messages(
    *,
    current_metadata: CheckpointMetadata | None,
    service_available: bool,
) -> list[str]:
    """Return deterministic reasons why checkpoint compatibility cannot run."""
    messages: list[str] = []
    if current_metadata is None:
        messages.append("Missing current checkpoint metadata for resume validation")
    if not service_available:
        messages.append(
            "Missing checkpoint compatibility service for resume validation"
        )
    return messages or ["Missing checkpoint compatibility context"]


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


def _prefer_identity_sequence[T](
    current_value: tuple[T, ...],
    identity_value: tuple[T, ...],
) -> tuple[T, ...]:
    """Prefer persisted non-empty tuple values, otherwise use identity fallback."""
    return current_value if current_value else identity_value


def _build_core_identity_overrides(
    metadata: CheckpointMetadata,
    identity: CheckpointMetadata,
) -> dict[str, object]:
    """Build core execution-identity overrides for checkpoint enrichment."""
    return {
        "dq_contract_compatibility_hash": _prefer_identity_value(
            metadata.dq_contract_compatibility_hash,
            identity.dq_contract_compatibility_hash,
        ),
        "dq_policy_hash": _prefer_identity_value(
            metadata.dq_policy_hash,
            identity.dq_policy_hash,
        ),
        "dq_rule_bundle_version": _prefer_identity_value(
            metadata.dq_rule_bundle_version,
            identity.dq_rule_bundle_version,
        ),
        "pipeline_name": _prefer_identity_value(
            metadata.pipeline_name,
            identity.pipeline_name,
        ),
        "run_type": _prefer_identity_value(metadata.run_type, identity.run_type),
        "pipeline_version": _prefer_identity_value(
            metadata.pipeline_version,
            identity.pipeline_version,
        ),
        "git_commit": _prefer_identity_value(metadata.git_commit, identity.git_commit),
        "dependency_lock_hash": _prefer_identity_value(
            metadata.dependency_lock_hash,
            identity.dependency_lock_hash,
        ),
        "effective_config_hash": _prefer_identity_value(
            metadata.effective_config_hash,
            identity.effective_config_hash,
        ),
        "effective_config_artifact_id": _prefer_identity_value(
            metadata.effective_config_artifact_id,
            identity.effective_config_artifact_id,
        ),
    }


def _build_replay_identity_overrides(
    metadata: CheckpointMetadata,
    identity: CheckpointMetadata,
) -> dict[str, object]:
    """Build replay and traceability identity overrides for checkpoint enrichment."""
    return {
        "execution_fingerprint": _prefer_identity_value(
            metadata.execution_fingerprint,
            identity.execution_fingerprint,
        ),
        "composite_run_identity": _prefer_identity_value(
            metadata.composite_run_identity,
            identity.composite_run_identity,
        ),
        "manifest_id": _prefer_identity_value(
            metadata.manifest_id,
            identity.manifest_id,
        ),
        "contract_ref": _prefer_identity_value(
            metadata.contract_ref,
            identity.contract_ref,
        ),
        "contract_version": _prefer_identity_value(
            metadata.contract_version,
            identity.contract_version,
        ),
        "normalization_profile_ref": _prefer_identity_value(
            metadata.normalization_profile_ref,
            identity.normalization_profile_ref,
        ),
        "normalization_profile_version": _prefer_identity_value(
            metadata.normalization_profile_version,
            identity.normalization_profile_version,
        ),
        "normalization_profile_hash": _prefer_identity_value(
            metadata.normalization_profile_hash,
            identity.normalization_profile_hash,
        ),
        "exact_replay": _prefer_identity_flag(
            metadata.exact_replay,
            identity.exact_replay,
        ),
        "input_snapshot_refs": _prefer_identity_sequence(
            metadata.input_snapshot_refs,
            identity.input_snapshot_refs,
        ),
        "input_snapshot_ids": _prefer_identity_sequence(
            metadata.input_snapshot_ids,
            identity.input_snapshot_ids,
        ),
        "input_snapshot_fingerprint": _prefer_identity_value(
            metadata.input_snapshot_fingerprint,
            identity.input_snapshot_fingerprint,
        ),
        "silver_filter_compatibility_mode": _prefer_identity_value(
            metadata.silver_filter_compatibility_mode,
            identity.silver_filter_compatibility_mode,
        ),
        "memory_decision_trace": (
            metadata.memory_decision_trace or identity.memory_decision_trace
        ),
        "run_context": metadata.run_context or identity.run_context,
    }


def enrich_metadata_with_execution_identity(
    metadata: CheckpointMetadata,
    *,
    identity: CheckpointMetadata | None,
) -> CheckpointMetadata:
    """Fill checkpoint metadata gaps from current execution identity."""
    if identity is None:
        return metadata
    return replace(
        metadata,
        **_build_core_identity_overrides(metadata, identity),
        **_build_replay_identity_overrides(metadata, identity),
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
        strict_persistence_required=strict_checkpoint_resume_required(
            current_metadata=current_metadata,
            checkpoint_metadata=checkpoint_metadata,
        ),
    )
    forced_resume_rejection = disposition == "observe_blocked_identity"
    degraded_resume_loaded = disposition == "observe_loaded_degraded"
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


def handle_missing_compatibility_context(
    *,
    logger: LoggerPort,
    pipeline_name: str,
    compatibility_policy: CheckpointCompatibilityPolicy,
    current_metadata: CheckpointMetadata | None,
    checkpoint_metadata: CheckpointMetadata,
    service_available: bool,
) -> CheckpointMetadata | None:
    """Apply configured policy when resume compatibility cannot be validated."""
    disposition = resolve_missing_compatibility_context_disposition(
        compatibility_policy=compatibility_policy,
    )
    messages = missing_compatibility_context_messages(
        current_metadata=current_metadata,
        service_available=service_available,
    )
    payload = {
        "pipeline": pipeline_name,
        "compatibility_policy": compatibility_policy,
        "compatibility_disposition": disposition,
        "resume_rejected": True,
        "messages": messages,
        "checkpoint_metadata": checkpoint_metadata.to_dict(),
        "current_identity": _checkpoint_identity_payload(current_metadata),
        "checkpoint_identity": _checkpoint_identity_payload(checkpoint_metadata),
        "compatibility_service_available": service_available,
    }
    if disposition == "missing_context_blocked":
        logger.warning(
            "Checkpoint compatibility context missing; resume blocked.",
            **payload,
        )
        return None
    raise ValueError(
        "Checkpoint resume requires compatibility context and hard_fail policy "
        "is enabled: " + "; ".join(messages)
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
        "required_persistence_profile": metadata.required_persistence_profile,
        "input_snapshot_ids": list(metadata.input_snapshot_ids),
    }


def strict_checkpoint_resume_required(
    *,
    current_metadata: CheckpointMetadata | None,
    checkpoint_metadata: CheckpointMetadata,
) -> bool:
    """Return whether resume must remain fail-closed for strict replay profiles."""
    required_profiles = {
        str(profile or "").strip().lower()
        for profile in (
            None
            if current_metadata is None
            else current_metadata.required_persistence_profile,
            checkpoint_metadata.required_persistence_profile,
        )
        if str(profile or "").strip()
    }
    if required_profiles.intersection(STRICT_PERSISTENCE_PROFILES):
        return True
    return bool(
        checkpoint_metadata.exact_replay
        or (current_metadata.exact_replay if current_metadata is not None else False)
    )


def resolve_incompatible_checkpoint_disposition(
    *,
    compatibility_policy: CheckpointCompatibilityPolicy,
    execution_identity_compatible: bool,
    identity_continuity_proven: bool = True,
    strict_persistence_required: bool = False,
) -> CheckpointCompatibilityDisposition:
    """Return the bounded incompatibility disposition for telemetry and logging."""
    if compatibility_policy == "observe":
        if (
            strict_persistence_required
            or not identity_continuity_proven
            or not execution_identity_compatible
        ):
            return "observe_blocked_identity"
        return "observe_loaded_degraded"
    if compatibility_policy == "soft_fail":
        return "soft_fail_blocked"
    return "hard_fail_raised"


def resolve_missing_compatibility_context_disposition(
    *,
    compatibility_policy: CheckpointCompatibilityPolicy,
) -> CheckpointMissingContextDisposition:
    """Return bounded disposition for missing resume compatibility context."""
    if compatibility_policy == "hard_fail":
        return "missing_context_hard_fail_raised"
    return "missing_context_blocked"


__all__ = [
    "CheckpointCompatibilityDisposition",
    "CheckpointCompatibilityPolicy",
    "CheckpointMissingContextDisposition",
    "enrich_metadata_with_execution_identity",
    "handle_incompatible_checkpoint",
    "handle_missing_compatibility_context",
    "missing_compatibility_context_messages",
    "resolve_current_metadata",
    "resolve_incompatible_checkpoint_disposition",
    "resolve_missing_compatibility_context_disposition",
    "validate_compatibility_policy",
]
