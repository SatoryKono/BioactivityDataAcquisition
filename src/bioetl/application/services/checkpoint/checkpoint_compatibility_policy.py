"""Checkpoint compatibility policy helpers for resume safety decisions."""

from __future__ import annotations

from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata

DQ_CONTRACTS_COMPATIBLE_MESSAGE = "DQ contracts are compatible"
PIPELINE_VERSIONS_COMPATIBLE_MESSAGE = "Pipeline versions are compatible"
STRICT_REQUIRED_CHECKPOINT_FIELDS: tuple[str, ...] = (
    "execution_fingerprint",
    "manifest_id",
    "effective_config_hash",
    "effective_config_artifact_id",
    "contract_ref",
    "contract_version",
    "dq_contract_compatibility_hash",
    "pipeline_version",
    "git_commit",
    "dependency_lock_hash",
    "normalization_profile_ref",
    "normalization_profile_version",
    "normalization_profile_hash",
    "exact_replay",
)
LENIENT_CANONICAL_RESUME_ANCHORS: tuple[str, ...] = (
    "execution_fingerprint",
    "manifest_id",
    "effective_config_hash",
    "effective_config_artifact_id",
    "contract_ref",
    "contract_version",
    "dq_contract_compatibility_hash",
    "pipeline_version",
    "git_commit",
    "dependency_lock_hash",
    "normalization_profile_ref",
    "normalization_profile_version",
    "normalization_profile_hash",
)


def strict_anchor_policy_requested(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
) -> bool:
    """Return ``True`` when resume validation has enough strict context to fail closed."""
    if bool(current_metadata.exact_replay):
        return True
    return any(
        (
            current_metadata.manifest_id,
            checkpoint_metadata.manifest_id,
            current_metadata.effective_config_artifact_id,
            checkpoint_metadata.effective_config_artifact_id,
            current_metadata.contract_ref,
            checkpoint_metadata.contract_ref,
            current_metadata.contract_version,
            checkpoint_metadata.contract_version,
            current_metadata.git_commit,
            checkpoint_metadata.git_commit,
            current_metadata.dependency_lock_hash,
            checkpoint_metadata.dependency_lock_hash,
            current_metadata.normalization_profile_ref,
            checkpoint_metadata.normalization_profile_ref,
            current_metadata.normalization_profile_version,
            checkpoint_metadata.normalization_profile_version,
            current_metadata.normalization_profile_hash,
            checkpoint_metadata.normalization_profile_hash,
        )
    )


def validate_dq_contract_compatibility(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
    *,
    strict: bool,
) -> tuple[bool, list[str]]:
    messages: list[str] = []
    dq_compatible = True
    if (
        current_metadata.dq_contract_compatibility_hash
        and checkpoint_metadata.dq_contract_compatibility_hash
    ):
        if (
            current_metadata.dq_contract_compatibility_hash
            != checkpoint_metadata.dq_contract_compatibility_hash
        ):
            dq_compatible = False
            messages.append(
                "DQ contract mismatch: "
                f"current={current_metadata.dq_contract_compatibility_hash}, "
                f"checkpoint={checkpoint_metadata.dq_contract_compatibility_hash}"
            )
        else:
            messages.append(DQ_CONTRACTS_COMPATIBLE_MESSAGE)
    elif strict:
        dq_compatible = False
        messages.append(
            "DQ contract compatibility: checkpoint_missing_required_execution_anchor"
        )
    else:
        messages.append(
            "DQ contract compatibility: not enforced (missing contract info)"
        )
    return dq_compatible, messages


def validate_pipeline_version_compatibility(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
    *,
    strict: bool,
) -> tuple[bool, list[str]]:
    messages: list[str] = []
    pipeline_compatible = True
    if current_metadata.pipeline_version and checkpoint_metadata.pipeline_version:
        if current_metadata.pipeline_version != checkpoint_metadata.pipeline_version:
            pipeline_compatible = False
            messages.append(
                "Pipeline version mismatch: "
                f"current={current_metadata.pipeline_version}, "
                f"checkpoint={checkpoint_metadata.pipeline_version}"
            )
        else:
            messages.append(PIPELINE_VERSIONS_COMPATIBLE_MESSAGE)
    elif strict:
        pipeline_compatible = False
        messages.append(
            "Pipeline version compatibility: checkpoint_missing_required_execution_anchor"
        )
    else:
        messages.append(
            "Pipeline version compatibility: not enforced (missing version info)"
        )
    return pipeline_compatible, messages


def validate_required_checkpoint_anchors(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
) -> tuple[bool, list[str]]:
    """Reject strict resume when checkpoint metadata omits required anchors."""
    required_fields = list(STRICT_REQUIRED_CHECKPOINT_FIELDS)
    if bool(current_metadata.exact_replay):
        required_fields.append("input_snapshot_fingerprint")
    missing = checkpoint_metadata.missing_required_anchors(tuple(required_fields))
    if not missing:
        return True, []
    messages = [
        f"checkpoint_missing_required_execution_anchor: {field_name}"
        for field_name in missing
    ]
    if "manifest_id" in missing:
        messages.append("checkpoint_missing_manifest_anchor")
    if "input_snapshot_fingerprint" in missing:
        messages.append("checkpoint_missing_snapshot_anchor")
    return False, messages


def validate_rule_bundle_compatibility(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
) -> list[str]:
    messages: list[str] = []
    if (
        current_metadata.dq_rule_bundle_version
        and checkpoint_metadata.dq_rule_bundle_version
    ):
        if (
            current_metadata.dq_rule_bundle_version
            != checkpoint_metadata.dq_rule_bundle_version
        ):
            messages.append(
                "DQ rule bundle version changed: "
                f"current={current_metadata.dq_rule_bundle_version}, "
                f"checkpoint={checkpoint_metadata.dq_rule_bundle_version}"
            )
        else:
            messages.append("DQ rule bundle versions are compatible")
    return messages


def validate_lenient_dq_compatibility(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
) -> tuple[bool, list[str]]:
    messages: list[str] = []
    if (
        current_metadata.dq_contract_compatibility_hash
        and checkpoint_metadata.dq_contract_compatibility_hash
    ):
        if (
            current_metadata.dq_contract_compatibility_hash
            != checkpoint_metadata.dq_contract_compatibility_hash
        ):
            messages.append(
                "DQ contract changed (lenient mode): "
                f"current={current_metadata.dq_contract_compatibility_hash}, "
                f"checkpoint={checkpoint_metadata.dq_contract_compatibility_hash}"
            )
        else:
            messages.append(DQ_CONTRACTS_COMPATIBLE_MESSAGE)
    else:
        # In lenient mode, missing DQ hashes are considered compatible.
        messages.append(DQ_CONTRACTS_COMPATIBLE_MESSAGE)
    return True, messages


def lenient_pipeline_version_message(
    current_version: str,
    checkpoint_version: str,
) -> tuple[bool, str]:
    current_parts = current_version.split(".")
    checkpoint_parts = checkpoint_version.split(".")
    if current_parts[0] != checkpoint_parts[0]:
        return (
            False,
            "Major pipeline version mismatch: "
            f"current={current_version}, "
            f"checkpoint={checkpoint_version}",
        )
    if len(current_parts) < 2 or len(checkpoint_parts) < 2:
        return True, PIPELINE_VERSIONS_COMPATIBLE_MESSAGE
    if current_parts[1] != checkpoint_parts[1]:
        return (
            True,
            "Minor pipeline version changed (lenient mode): "
            f"current={current_version}, "
            f"checkpoint={checkpoint_version}",
        )
    if (
        len(current_parts) >= 3
        and len(checkpoint_parts) >= 3
        and current_parts[2] != checkpoint_parts[2]
    ):
        return (
            True,
            "Patch pipeline version changed (lenient mode): "
            f"current={current_version}, "
            f"checkpoint={checkpoint_version}",
        )
    return True, PIPELINE_VERSIONS_COMPATIBLE_MESSAGE


def validate_lenient_pipeline_compatibility(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
) -> tuple[bool, list[str]]:
    messages: list[str] = []
    if not (current_metadata.pipeline_version and checkpoint_metadata.pipeline_version):
        return True, messages
    pipeline_compatible, message = lenient_pipeline_version_message(
        current_metadata.pipeline_version,
        checkpoint_metadata.pipeline_version,
    )
    return pipeline_compatible, [message]


def missing_lenient_resume_anchor_pairs(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
) -> tuple[str, ...]:
    """Return canonical anchors not proven on both sides of a lenient resume."""
    missing: list[str] = []
    for field_name in LENIENT_CANONICAL_RESUME_ANCHORS:
        current_value = getattr(current_metadata, field_name, None)
        checkpoint_value = getattr(checkpoint_metadata, field_name, None)
        if current_value and checkpoint_value:
            continue
        missing.append(field_name)
    return tuple(missing)


def lenient_resume_degraded_messages(
    current_metadata: CheckpointMetadata,
    checkpoint_metadata: CheckpointMetadata,
) -> tuple[str, ...]:
    missing = missing_lenient_resume_anchor_pairs(
        current_metadata,
        checkpoint_metadata,
    )
    if not missing:
        return ()
    return (
        "resume_only_degraded: lenient checkpoint resume is operationally "
        "compatible, but canonical execution identity is incomplete; missing "
        f"anchor pairs: {', '.join(missing)}",
    )


__all__ = [
    "DQ_CONTRACTS_COMPATIBLE_MESSAGE",
    "LENIENT_CANONICAL_RESUME_ANCHORS",
    "PIPELINE_VERSIONS_COMPATIBLE_MESSAGE",
    "STRICT_REQUIRED_CHECKPOINT_FIELDS",
    "lenient_pipeline_version_message",
    "lenient_resume_degraded_messages",
    "missing_lenient_resume_anchor_pairs",
    "strict_anchor_policy_requested",
    "validate_dq_contract_compatibility",
    "validate_lenient_dq_compatibility",
    "validate_lenient_pipeline_compatibility",
    "validate_pipeline_version_compatibility",
    "validate_required_checkpoint_anchors",
    "validate_rule_bundle_compatibility",
]
