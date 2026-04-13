"""Resume-compatibility checks for composite checkpoints."""

from __future__ import annotations

from bioetl.application.composite.checkpoint._anchor_context import (
    ExpectedCheckpointContext,
)
from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
from bioetl.domain.exceptions import CheckpointConflictError
from bioetl.domain.ports import LoggerPort


def _contract_ref_mismatch(
    *,
    state: CompositeCheckpointState,
    expected_contract_ref: str,
    logger: LoggerPort,
    composite_name: str,
) -> str | None:
    if not expected_contract_ref:
        return None
    if state.contract_ref:
        if state.contract_ref != expected_contract_ref:
            return f"contract_ref {state.contract_ref!r} != {expected_contract_ref!r}"
        return None

    logger.warning(
        "Checkpoint missing contract_ref anchor; compatibility check is partial",
        composite=composite_name,
        reason_code="checkpoint_anchor_missing_contract_ref",
    )
    return None


def _contract_version_mismatch(
    *,
    state: CompositeCheckpointState,
    expected_contract_version: str,
    logger: LoggerPort,
    composite_name: str,
) -> str | None:
    if not expected_contract_version:
        return None
    if state.contract_ref:
        if (
            state.contract_version
            and state.contract_version != expected_contract_version
        ):
            return (
                f"contract_version {state.contract_version!r} "
                f"!= {expected_contract_version!r}"
            )
        return None
    if not state.contract_version:
        logger.warning(
            "Checkpoint missing contract_version anchor; compatibility check is partial",
            composite=composite_name,
            reason_code="checkpoint_anchor_missing_contract_version",
        )
    return None


def _effective_hash_mismatch(
    *,
    state: CompositeCheckpointState,
    expected_effective_config_hash: str,
    logger: LoggerPort,
    composite_name: str,
) -> str | None:
    if not expected_effective_config_hash:
        return None
    if state.effective_config_hash:
        if state.effective_config_hash != expected_effective_config_hash:
            return (
                f"effective_config_hash {state.effective_config_hash!r} "
                f"!= {expected_effective_config_hash!r}"
            )
        return None

    logger.warning(
        "Checkpoint missing effective_config_hash anchor; compatibility check is partial",
        composite=composite_name,
        reason_code="checkpoint_anchor_missing_effective_config_hash",
    )
    return None


def _manifest_id_mismatch(
    *,
    state: CompositeCheckpointState,
    expected_manifest_id: str,
    logger: LoggerPort,
    composite_name: str,
) -> str | None:
    if not expected_manifest_id:
        return None
    if state.manifest_id:
        if state.manifest_id != expected_manifest_id:
            return f"manifest_id {state.manifest_id!r} != {expected_manifest_id!r}"
        return None

    logger.warning(
        "Checkpoint missing manifest_id anchor; compatibility check is partial",
        composite=composite_name,
        reason_code="checkpoint_anchor_missing_manifest_id",
    )
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


def validate_resume_compatibility(
    *,
    state: CompositeCheckpointState,
    anchors: ExpectedCheckpointContext,
    logger: LoggerPort,
    composite_name: str,
) -> None:
    """Raise when persisted checkpoint anchors conflict with the current runtime."""
    mismatches = [
        mismatch
        for mismatch in (
            _contract_ref_mismatch(
                state=state,
                expected_contract_ref=anchors.contract_ref,
                logger=logger,
                composite_name=composite_name,
            ),
            _contract_version_mismatch(
                state=state,
                expected_contract_version=anchors.contract_version,
                logger=logger,
                composite_name=composite_name,
            ),
            _effective_hash_mismatch(
                state=state,
                expected_effective_config_hash=anchors.effective_config_hash,
                logger=logger,
                composite_name=composite_name,
            ),
            _manifest_id_mismatch(
                state=state,
                expected_manifest_id=anchors.manifest_id,
                logger=logger,
                composite_name=composite_name,
            ),
            _composite_run_identity_mismatch(
                state=state,
                expected_composite_run_identity=anchors.composite_run_identity,
            ),
        )
        if mismatch is not None
    ]
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
        expected_composite_run_identity=anchors.composite_run_identity,
        checkpoint_contract_ref=state.contract_ref,
        checkpoint_contract_version=state.contract_version,
        checkpoint_effective_config_hash=state.effective_config_hash,
        checkpoint_composite_run_identity=state.composite_run_identity,
        reason_code="checkpoint_resume_incompatible",
        incompatibility=detail,
    )
    raise CheckpointConflictError(composite_name, detail)
