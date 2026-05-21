"""Resume-anchor compatibility validation for composite checkpoint loading."""

from __future__ import annotations

from bioetl.application.composite.checkpoint._anchor_context import (
    ExpectedCheckpointContext,
)
from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
from bioetl.domain.exceptions import CheckpointConflictError
from bioetl.domain.ports import LoggerPort


def _anchor_mismatch(
    *,
    state_value: str,
    expected_value: str,
    anchor_name: str,
) -> str | None:
    if not expected_value:
        return None
    if not state_value:
        return f"checkpoint missing {anchor_name} anchor"
    if state_value != expected_value:
        return f"{anchor_name} {state_value!r} != {expected_value!r}"
    return None


def _composite_run_identity_mismatch(
    *,
    state: CompositeCheckpointState,
    expected_composite_run_identity: str,
) -> str | None:
    if not expected_composite_run_identity:
        return None
    if not state.composite_run_identity:
        return "checkpoint missing composite_run_identity anchor"
    if state.composite_run_identity != expected_composite_run_identity:
        return (
            "composite_run_identity "
            f"{state.composite_run_identity!r} != {expected_composite_run_identity!r}"
        )
    return None


def _resume_anchor_mismatches(
    *,
    state: CompositeCheckpointState,
    anchors: ExpectedCheckpointContext,
) -> list[str]:
    return [
        mismatch
        for mismatch in (
            _anchor_mismatch(
                state_value=state.contract_ref,
                expected_value=anchors.contract_ref,
                anchor_name="contract_ref",
            ),
            _anchor_mismatch(
                state_value=state.contract_version,
                expected_value=anchors.contract_version,
                anchor_name="contract_version",
            ),
            _anchor_mismatch(
                state_value=state.effective_config_hash,
                expected_value=anchors.effective_config_hash,
                anchor_name="effective_config_hash",
            ),
            _anchor_mismatch(
                state_value=state.effective_config_artifact_id,
                expected_value=anchors.effective_config_artifact_id,
                anchor_name="effective_config_artifact_id",
            ),
            _anchor_mismatch(
                state_value=state.execution_fingerprint,
                expected_value=anchors.execution_fingerprint,
                anchor_name="execution_fingerprint",
            ),
            _anchor_mismatch(
                state_value=state.dq_contract_compatibility_hash,
                expected_value=anchors.dq_contract_compatibility_hash,
                anchor_name="dq_contract_compatibility_hash",
            ),
            _anchor_mismatch(
                state_value=state.input_snapshot_fingerprint,
                expected_value=anchors.input_snapshot_fingerprint,
                anchor_name="input_snapshot_fingerprint",
            ),
            _anchor_mismatch(
                state_value=state.manifest_id,
                expected_value=anchors.manifest_id,
                anchor_name="manifest_id",
            ),
            _composite_run_identity_mismatch(
                state=state,
                expected_composite_run_identity=anchors.composite_run_identity,
            ),
        )
        if mismatch is not None
    ]


def validate_resume_compatibility(
    *,
    state: CompositeCheckpointState,
    anchors: ExpectedCheckpointContext,
    logger: LoggerPort,
    composite_name: str,
) -> None:
    """Raise when persisted checkpoint anchors conflict with the current runtime."""
    mismatches = _resume_anchor_mismatches(state=state, anchors=anchors)
    if not mismatches:
        return

    detail = "; ".join(mismatches)
    logger.error(
        "Checkpoint incompatible with current runtime anchors",
        composite=composite_name,
        checkpoint_run_id=state.run_id,
        expected_contract_ref=anchors.contract_ref,
        expected_contract_version=anchors.contract_version,
        expected_effective_config_hash=anchors.effective_config_hash,
        expected_effective_config_artifact_id=anchors.effective_config_artifact_id,
        expected_execution_fingerprint=anchors.execution_fingerprint,
        expected_dq_contract_compatibility_hash=(
            anchors.dq_contract_compatibility_hash
        ),
        expected_input_snapshot_fingerprint=anchors.input_snapshot_fingerprint,
        expected_composite_run_identity=anchors.composite_run_identity,
        checkpoint_contract_ref=state.contract_ref,
        checkpoint_contract_version=state.contract_version,
        checkpoint_effective_config_hash=state.effective_config_hash,
        checkpoint_effective_config_artifact_id=state.effective_config_artifact_id,
        checkpoint_execution_fingerprint=state.execution_fingerprint,
        checkpoint_dq_contract_compatibility_hash=(
            state.dq_contract_compatibility_hash
        ),
        checkpoint_input_snapshot_fingerprint=state.input_snapshot_fingerprint,
        checkpoint_composite_run_identity=state.composite_run_identity,
        reason_code="checkpoint_resume_incompatible",
        incompatibility=detail,
    )
    raise CheckpointConflictError(composite_name, detail)


__all__ = ["validate_resume_compatibility"]
