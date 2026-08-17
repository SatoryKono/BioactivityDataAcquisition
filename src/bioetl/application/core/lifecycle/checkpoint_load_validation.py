"""Checkpoint load compatibility validation helpers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from bioetl.application.core.lifecycle._checkpoint_types import (
    CheckpointCompatibilityService,
)
from bioetl.application.core.lifecycle.checkpoint_runtime import (
    CheckpointCompatibilityPolicy,
    handle_incompatible_checkpoint,
    handle_missing_compatibility_context,
    resolve_current_metadata,
    resolve_incompatible_checkpoint_disposition,
    strict_checkpoint_resume_required,
)
from bioetl.application.core.lifecycle.checkpoint_runtime import (
    resolve_missing_compatibility_context_disposition as resolve_missing_disposition,
)
from bioetl.domain.ports import LoggerPort
from bioetl.domain.types import JsonDict, RunID
from bioetl.domain.types.checkpoint_compatibility_result import (
    CheckpointCompatibilityResult,
)
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata

OperationErrors = type[BaseException] | tuple[type[BaseException], ...]


class CheckpointValidationProtocol(Protocol):
    """Internal service attributes required by checkpoint validation helpers."""

    _logger: LoggerPort
    _pipeline_name: str
    _compatibility_policy: CheckpointCompatibilityPolicy
    _compatibility_service: CheckpointCompatibilityService | None
    _current_metadata: CheckpointMetadata | None

    @property
    def _operation_errors(self) -> OperationErrors: ...
    def _emit_checkpoint_load_status(self, status: str) -> None: ...


def resolve_checkpoint_metadata(
    checkpoint_data: tuple[RunID, JsonDict],
) -> CheckpointMetadata:
    """Convert persisted legacy checkpoint payload into typed metadata."""
    _, legacy_metadata = checkpoint_data
    return CheckpointMetadata.from_legacy_metadata(legacy_metadata)


def _handle_missing_compatibility_context_result(
    *,
    logger: LoggerPort,
    pipeline_name: str,
    compatibility_policy: CheckpointCompatibilityPolicy,
    checkpoint_metadata: CheckpointMetadata,
    current_metadata: CheckpointMetadata | None,
    service_available: bool,
    operation_errors: OperationErrors,
    emit_checkpoint_load_status: Callable[[str], None],
) -> CheckpointMetadata | None:
    """Apply the configured disposition when resume validation is unavailable."""
    mode = resolve_missing_disposition(compatibility_policy=compatibility_policy)
    try:
        result = handle_missing_compatibility_context(
            logger=logger,
            pipeline_name=pipeline_name,
            compatibility_policy=compatibility_policy,
            current_metadata=current_metadata,
            checkpoint_metadata=checkpoint_metadata,
            service_available=service_available,
        )
    except operation_errors:
        emit_checkpoint_load_status(
            "missing_compatibility_context_hard_fail"
            if mode == "missing_context_hard_fail_raised"
            else "missing_compatibility_context"
        )
        raise
    if result is None:
        emit_checkpoint_load_status("missing_compatibility_context")
        return None
    emit_checkpoint_load_status("loaded")
    return result


def validate_loaded_checkpoint(
    host: CheckpointValidationProtocol,
    checkpoint_metadata: CheckpointMetadata,
    *,
    current_metadata: CheckpointMetadata | None,
) -> tuple[CheckpointMetadata | None, bool]:
    """Validate a loaded checkpoint against runtime execution identity."""
    current = resolve_current_metadata(
        current_metadata, default_metadata=host._current_metadata
    )
    missing_context: list[str] = []
    if current is None:
        missing_context.append("current_metadata")
    if host._compatibility_service is None:
        missing_context.append("checkpoint_compatibility_service")
    if missing_context:
        return (
            _handle_missing_compatibility_context_result(
                logger=host._logger,
                pipeline_name=host._pipeline_name,
                compatibility_policy=host._compatibility_policy,
                checkpoint_metadata=checkpoint_metadata,
                current_metadata=current,
                service_available=host._compatibility_service is not None,
                operation_errors=host._operation_errors,
                emit_checkpoint_load_status=host._emit_checkpoint_load_status,
            ),
            True,
        )
    assert current is not None
    assert host._compatibility_service is not None
    result = host._compatibility_service.validate_checkpoint_compatibility(
        current,
        checkpoint_metadata,
    )
    if result.compatible:
        host._logger.info(
            "Checkpoint compatibility validation passed.",
            pipeline=host._pipeline_name,
            messages=list(result.messages),
        )
        return checkpoint_metadata, False
    return (
        handle_incompatible_checkpoint_result(
            host=host,
            checkpoint_metadata=checkpoint_metadata,
            current_metadata=current,
            result=result,
        ),
        True,
    )


def handle_incompatible_checkpoint_result(
    *,
    host: CheckpointValidationProtocol,
    checkpoint_metadata: CheckpointMetadata,
    current_metadata: CheckpointMetadata,
    result: CheckpointCompatibilityResult,
) -> CheckpointMetadata | None:
    """Apply the configured disposition for an incompatible checkpoint."""
    mode = resolve_incompatible_checkpoint_disposition(
        compatibility_policy=host._compatibility_policy,
        execution_identity_compatible=result.execution_identity_compatible,
        identity_continuity_proven=result.identity_continuity_proven,
        strict_persistence_required=strict_checkpoint_resume_required(
            current_metadata=current_metadata,
            checkpoint_metadata=checkpoint_metadata,
        ),
    )
    try:
        loaded = handle_incompatible_checkpoint(
            logger=host._logger,
            pipeline_name=host._pipeline_name,
            compatibility_policy=host._compatibility_policy,
            current_metadata=current_metadata,
            checkpoint_metadata=checkpoint_metadata,
            execution_identity_compatible=result.execution_identity_compatible,
            identity_continuity_proven=result.identity_continuity_proven,
            messages=list(result.messages),
        )
    except host._operation_errors:
        status = (
            "incompatible_hard_fail" if mode == "hard_fail_raised" else "incompatible"
        )
        host._emit_checkpoint_load_status(status)
        raise
    if loaded is None:
        status = mode if mode == "observe_blocked_identity" else "incompatible"
        host._emit_checkpoint_load_status(status)
        return None
    status = mode if mode == "observe_loaded_degraded" else "loaded"
    host._emit_checkpoint_load_status(status)
    return loaded


__all__ = [
    "resolve_checkpoint_metadata",
    "validate_loaded_checkpoint",
]
