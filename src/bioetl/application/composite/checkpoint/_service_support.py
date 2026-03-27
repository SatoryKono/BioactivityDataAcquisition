"""Support helpers for composite checkpoint service orchestration."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
from bioetl.domain.exceptions import BioETLError, CheckpointConflictError, StorageError

if TYPE_CHECKING:
    from bioetl.domain.ports import CompositeCheckpointPort, LoggerPort

CHECKPOINT_READ_ERRORS = (
    json.JSONDecodeError,
    OSError,
    TypeError,
    ValueError,
    StorageError,
)
CHECKPOINT_WRITE_ERRORS = (
    OSError,
    TypeError,
    ValueError,
    StorageError,
)


@dataclass(frozen=True, slots=True)
class ExpectedCheckpointAnchors:
    effective_config_hash: str = ""
    contract_ref: str = ""
    contract_version: str = ""
    composite_run_identity: str = ""


def latest_checkpoint_filename(
    *,
    storage: CompositeCheckpointPort,
    glob_pattern: str,
) -> str | None:
    matches = storage.list_glob(glob_pattern)
    return matches[0] if matches else None


def warn_if_checkpoint_exists_with_progress(
    *,
    storage: CompositeCheckpointPort,
    logger: LoggerPort,
    composite_name: str,
    glob_pattern: str,
) -> None:
    latest = latest_checkpoint_filename(storage=storage, glob_pattern=glob_pattern)
    if latest is None or not storage.exists(latest):
        return

    try:
        content = storage.read(latest)
        if content is None:
            return
        state = CompositeCheckpointState.from_dict(json.loads(content))
        if state.is_resumable:
            logger.warning(
                "Existing checkpoint with progress will be overwritten",
                composite=composite_name,
                checkpoint_path=latest,
                checkpoint_state=state.state.value,
                seed_completed=state.seed_completed,
                completed_enrichers=len(state.completed_enrichers),
                hint="Use --resume flag to continue from previous progress",
            )
    except CHECKPOINT_READ_ERRORS as error:
        logger.debug(
            "Checkpoint exists but cannot be parsed, will be overwritten",
            composite=composite_name,
            checkpoint_path=latest,
            error=str(error),
            error_type=type(error).__name__,
            reason_code="checkpoint_read_failed",
        )
    except BioETLError as error:
        logger.warning(
            "Checkpoint pre-check failed with domain error",
            composite=composite_name,
            checkpoint_path=latest,
            error=str(error),
            error_type=type(error).__name__,
            reason_code="unexpected_bioetl_error",
        )


def warn_if_checkpoint_stale(
    *,
    logger: LoggerPort,
    composite_name: str,
    stale_threshold_hours: float,
    state: CompositeCheckpointState,
) -> None:
    if stale_threshold_hours <= 0:
        return
    ref_time = state.updated_at or state.created_at
    if ref_time is None:
        return

    age = datetime.now(tz=UTC) - ref_time
    if age.total_seconds() <= stale_threshold_hours * 3600:
        return

    logger.warning(
        "Resuming from stale checkpoint",
        composite=composite_name,
        checkpoint_age_hours=round(age.total_seconds() / 3600, 1),
        threshold_hours=stale_threshold_hours,
        checkpoint_updated_at=ref_time.isoformat(),
        checkpoint_state=state.state.value,
        reason_code="stale_checkpoint_resume",
        hint="Seed data may have been overwritten since this checkpoint was saved",
    )


def resolve_resume_checkpoint_filename(
    *,
    storage: CompositeCheckpointPort,
    checkpoint_filename: str,
    glob_pattern: str,
) -> str | None:
    if storage.exists(checkpoint_filename):
        return checkpoint_filename
    return latest_checkpoint_filename(storage=storage, glob_pattern=glob_pattern)


def merge_expected_anchors(
    state: CompositeCheckpointState,
    anchors: ExpectedCheckpointAnchors,
) -> CompositeCheckpointState:
    return replace(
        state,
        effective_config_hash=(
            state.effective_config_hash or anchors.effective_config_hash
        ),
        contract_ref=(state.contract_ref or anchors.contract_ref),
        contract_version=(anchors.contract_version or state.contract_version),
        composite_run_identity=(
            state.composite_run_identity or anchors.composite_run_identity
        ),
    )


def validate_resume_compatibility(
    *,
    state: CompositeCheckpointState,
    anchors: ExpectedCheckpointAnchors,
    logger: LoggerPort,
    composite_name: str,
) -> None:
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
        checkpoint_contract_ref=state.contract_ref,
        checkpoint_contract_version=state.contract_version,
        checkpoint_effective_config_hash=state.effective_config_hash,
        reason_code="checkpoint_resume_incompatible",
        incompatibility=detail,
    )
    raise CheckpointConflictError(composite_name, detail)


def load_checkpoint_state(
    *,
    storage: CompositeCheckpointPort,
    logger: LoggerPort,
    composite_name: str,
    filename: str,
) -> CompositeCheckpointState | None:
    try:
        content = storage.read(filename)
        if content is None:
            return None
        data = json.loads(content)
        state = CompositeCheckpointState.from_dict(data)
        raw_state = data.get("state")
        if raw_state is not None and state.state.value != raw_state:
            logger.warning(
                "Checkpoint state value corrupted, using default",
                composite=composite_name,
                raw_state=raw_state,
                parsed_state=state.state.value,
            )
        logger.info(
            "Loaded checkpoint",
            composite=composite_name,
            checkpoint_path=filename,
            state=state.state.value,
            seed_completed=state.seed_completed,
            completed_enrichers=list(state.completed_enrichers),
        )
        return state
    except CHECKPOINT_READ_ERRORS as error:
        logger.warning(
            "Failed to load checkpoint",
            composite=composite_name,
            error=str(error),
            error_type=type(error).__name__,
            reason_code="checkpoint_load_failed",
        )
    except BioETLError as error:
        logger.warning(
            "Failed to load checkpoint",
            composite=composite_name,
            error=str(error),
            error_type=type(error).__name__,
            reason_code="unexpected_bioetl_error",
        )
    return None


def fresh_checkpoint_state(
    *,
    composite_name: str,
    run_id: str,
    anchors: ExpectedCheckpointAnchors,
) -> CompositeCheckpointState:
    return CompositeCheckpointState(
        composite_name=composite_name,
        run_id=run_id,
        effective_config_hash=anchors.effective_config_hash,
        contract_ref=anchors.contract_ref,
        contract_version=anchors.contract_version or "1.0.0",
        composite_run_identity=anchors.composite_run_identity,
        created_at=datetime.now(tz=UTC),
    )


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
