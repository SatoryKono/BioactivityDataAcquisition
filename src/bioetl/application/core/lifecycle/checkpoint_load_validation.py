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
    resolve_missing_compatibility_context_disposition,
    strict_checkpoint_resume_required,
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
    disposition = resolve_missing_compatibility_context_disposition(
        compatibility_policy=compatibility_policy,
    )
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
            if disposition == "missing_context_hard_fail_raised"
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
    effective_current_metadata = resolve_current_metadata(
        current_metadata,
        default_metadata=host._current_metadata,
    )
    missing_context: list[str] = []
    if effective_current_metadata is None:
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
                current_metadata=effective_current_metadata,
                service_available=host._compatibility_service is not None,
                operation_errors=host._operation_errors,
                emit_checkpoint_load_status=host._emit_checkpoint_load_status,
            ),
            True,
        )
    assert effective_current_metadata is not None
    assert host._compatibility_service is not None
    compatibility_result = (
        host._compatibility_service.validate_checkpoint_compatibility(
            effective_current_metadata,
            checkpoint_metadata,
        )
    )
    if compatibility_result.compatible:
        host._logger.info(
            "Checkpoint compatibility validation passed.",
            pipeline=host._pipeline_name,
            messages=compatibility_result.messages,
        )
        return checkpoint_metadata, False
    return (
        handle_incompatible_checkpoint_result(
            host=host,
            checkpoint_metadata=checkpoint_metadata,
            current_metadata=effective_current_metadata,
            compatibility_result=compatibility_result,
        ),
        True,
    )


def handle_incompatible_checkpoint_result(
    *,
    host: CheckpointValidationProtocol,
    checkpoint_metadata: CheckpointMetadata,
    current_metadata: CheckpointMetadata,
    compatibility_result: CheckpointCompatibilityResult,
) -> CheckpointMetadata | None:
    """Apply the configured disposition for an incompatible checkpoint."""
    disposition = resolve_incompatible_checkpoint_disposition(
        compatibility_policy=host._compatibility_policy,
        execution_identity_compatible=(
            compatibility_result.execution_identity_compatible
        ),
        identity_continuity_proven=compatibility_result.identity_continuity_proven,
        strict_persistence_required=strict_checkpoint_resume_required(
            current_metadata=current_metadata,
            checkpoint_metadata=checkpoint_metadata,
        ),
    )
    try:
        result = handle_incompatible_checkpoint(
            logger=host._logger,
            pipeline_name=host._pipeline_name,
            compatibility_policy=host._compatibility_policy,
            current_metadata=current_metadata,
            checkpoint_metadata=checkpoint_metadata,
            execution_identity_compatible=(
                compatibility_result.execution_identity_compatible
            ),
            identity_continuity_proven=(
                compatibility_result.identity_continuity_proven
            ),
            messages=compatibility_result.messages,
        )
    except host._operation_errors:
        host._emit_checkpoint_load_status(
            "incompatible_hard_fail"
            if disposition == "hard_fail_raised"
            else "incompatible"
        )
        raise
    if result is None:
        host._emit_checkpoint_load_status(
            "observe_blocked_identity"
            if disposition == "observe_blocked_identity"
            else "incompatible"
        )
        return None
    host._emit_checkpoint_load_status(
        "observe_loaded_degraded"
        if disposition == "observe_loaded_degraded"
        else "loaded"
    )
    return result


__all__ = [
    "resolve_checkpoint_metadata",
    "validate_loaded_checkpoint",
]
