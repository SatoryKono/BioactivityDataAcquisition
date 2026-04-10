"""Support helpers for composite checkpoint service orchestration."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
from bioetl.domain.exceptions import BioETLError, CheckpointConflictError, StorageError
from bioetl.domain.normalization import normalize_runtime_anchor_payload

if TYPE_CHECKING:
    from bioetl.domain.ports import CompositeCheckpointPort, LoggerPort, MetricsPort

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
class ExpectedCheckpointContext:
    """Expected runtime anchors used to validate checkpoint resume safety."""

    effective_config_hash: str = ""
    contract_ref: str = ""
    contract_version: str = ""
    manifest_id: str = ""
    composite_run_identity: str = ""


def create_expected_checkpoint_context(
    *,
    effective_config_hash: str | None,
    contract_ref: str | None,
    contract_version: str | None,
    manifest_id: str | None,
    composite_run_identity: str,
) -> ExpectedCheckpointContext:
    """Normalize nullable runtime anchors into a comparable checkpoint context."""
    normalized = normalize_runtime_anchor_payload(
        {
            "effective_config_hash": effective_config_hash,
            "contract_ref": contract_ref,
            "contract_version": contract_version,
            "manifest_id": manifest_id,
            "composite_run_identity": composite_run_identity,
        }
    )
    return ExpectedCheckpointContext(
        effective_config_hash=normalized["effective_config_hash"] or "",
        contract_ref=normalized["contract_ref"] or "",
        contract_version=normalized["contract_version"] or "",
        manifest_id=normalized["manifest_id"] or "",
        composite_run_identity=normalized["composite_run_identity"] or "",
    )


def latest_checkpoint_filename(
    *,
    storage: CompositeCheckpointPort,
    glob_pattern: str,
) -> str | None:
    """Return the newest checkpoint filename matching the storage glob."""
    matches = storage.list_glob(glob_pattern)
    return matches[0] if matches else None


def warn_if_checkpoint_exists_with_progress(
    *,
    storage: CompositeCheckpointPort,
    logger: LoggerPort,
    composite_name: str,
    glob_pattern: str,
) -> None:
    """Warn when an existing resumable checkpoint would be overwritten."""
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
    """Warn when resume targets a checkpoint older than the configured threshold."""
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
    """Resolve the explicit or latest available checkpoint filename for resume."""
    if storage.exists(checkpoint_filename):
        return checkpoint_filename
    return latest_checkpoint_filename(storage=storage, glob_pattern=glob_pattern)


def _coalesce_expected_anchor(current: str, expected: str) -> str:
    """Prefer the persisted checkpoint anchor and fall back to the runtime one."""
    return current or expected


def _build_merged_anchor_payload(
    *,
    state: CompositeCheckpointState,
    anchors: ExpectedCheckpointContext,
) -> dict[str, str]:
    """Return the raw anchor payload before normalization."""
    return {
        "effective_config_hash": _coalesce_expected_anchor(
            state.effective_config_hash,
            anchors.effective_config_hash,
        ),
        "contract_ref": _coalesce_expected_anchor(
            state.contract_ref,
            anchors.contract_ref,
        ),
        "contract_version": _coalesce_expected_anchor(
            state.contract_version,
            anchors.contract_version,
        ),
        "manifest_id": _coalesce_expected_anchor(
            state.manifest_id,
            anchors.manifest_id,
        ),
        "composite_run_identity": _coalesce_expected_anchor(
            state.composite_run_identity,
            anchors.composite_run_identity,
        ),
    }


def merge_expected_anchors(
    state: CompositeCheckpointState,
    anchors: ExpectedCheckpointContext,
) -> CompositeCheckpointState:
    """Fill empty checkpoint anchors with the expected runtime anchor values."""
    merged = normalize_runtime_anchor_payload(
        _build_merged_anchor_payload(state=state, anchors=anchors)
    )
    return replace(
        state,
        effective_config_hash=merged["effective_config_hash"] or "",
        contract_ref=merged["contract_ref"] or "",
        contract_version=merged["contract_version"] or "",
        manifest_id=merged["manifest_id"] or "",
        composite_run_identity=merged["composite_run_identity"] or "",
    )


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
    metrics: MetricsPort | None = None,
) -> CompositeCheckpointState | None:
    """Load and parse one checkpoint state from storage if it exists."""
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
            last_event_id=state.last_event_id,
            last_event_occurred_at=(
                state.last_event_occurred_at.isoformat()
                if state.last_event_occurred_at is not None
                else None
            ),
        )
        if metrics is not None:
            metrics.increment_counter(
                "checkpoint_load_events_total",
                1,
                {
                    "pipeline": composite_name,
                    "status": "loaded",
                },
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
        if metrics is not None:
            metrics.increment_counter(
                "checkpoint_load_events_total",
                1,
                {
                    "pipeline": composite_name,
                    "status": "failed",
                },
            )
    except BioETLError as error:
        logger.warning(
            "Failed to load checkpoint",
            composite=composite_name,
            error=str(error),
            error_type=type(error).__name__,
            reason_code="unexpected_bioetl_error",
        )
        if metrics is not None:
            metrics.increment_counter(
                "checkpoint_load_events_total",
                1,
                {
                    "pipeline": composite_name,
                    "status": "failed",
                },
            )
    return None


def fresh_checkpoint_state(
    *,
    composite_name: str,
    run_id: str,
    anchors: ExpectedCheckpointContext,
) -> CompositeCheckpointState:
    """Create a fresh checkpoint state for a new composite execution."""
    return CompositeCheckpointState(
        composite_name=composite_name,
        run_id=run_id,
        effective_config_hash=anchors.effective_config_hash,
        contract_ref=anchors.contract_ref,
        contract_version=anchors.contract_version,
        manifest_id=anchors.manifest_id,
        composite_run_identity=anchors.composite_run_identity,
        last_event_id=None,
        last_event_occurred_at=None,
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
