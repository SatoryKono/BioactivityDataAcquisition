"""Checkpoint Manager for ETL Pipelines."""

from __future__ import annotations

from typing import cast

from bioetl.application.core.batch_runtime_failure_policy import (
    OPERATION_ERRORS as _RF005_OPERATION_ERRORS,
)
from bioetl.application.core.lifecycle._checkpoint_legacy import CheckpointManager
from bioetl.application.core.lifecycle._checkpoint_types import (
    CheckpointCompatibilityService,
)
from bioetl.application.core.lifecycle.checkpoint_runtime import (
    CheckpointCompatibilityPolicy,
    enrich_metadata_with_execution_identity,
    handle_incompatible_checkpoint,
    resolve_current_metadata,
    resolve_incompatible_checkpoint_disposition,
    validate_compatibility_policy,
)
from bioetl.domain.medallion import LoadingStrategy
from bioetl.domain.ports import CheckpointPort, LoggerPort, MetricsPort
from bioetl.domain.types import JsonDict, RunID
from bioetl.domain.types.checkpoint_compatibility_result import (
    CheckpointCompatibilityResult,
)
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata

_OPERATION_ERRORS = _RF005_OPERATION_ERRORS


class CheckpointManagerService:
    """Framework-agnostic checkpoint persistence and resume management."""

    def __init__(
        self,
        checkpoint_port: CheckpointPort,
        logger: LoggerPort,
        pipeline_name: str,
        run_id: RunID,
        resume: bool,
        *,
        loading_strategy: LoadingStrategy | None = None,
        metrics: MetricsPort | None = None,
        checkpoint_compatibility_service: CheckpointCompatibilityService | None = None,
        current_metadata: CheckpointMetadata | None = None,
        compatibility_policy: CheckpointCompatibilityPolicy = "soft_fail",
    ) -> None:
        """Initialize checkpoint management with explicit collaborators."""
        self._checkpoint = checkpoint_port
        self._logger = logger
        self._pipeline_name = pipeline_name
        self._run_id = run_id
        self._resume = resume
        self._loading_strategy = loading_strategy
        self._metrics = metrics
        self._compatibility_service = checkpoint_compatibility_service
        self._current_metadata = current_metadata
        self._compatibility_policy = validate_compatibility_policy(compatibility_policy)

    def _emit_checkpoint_load_status(self, status: str) -> None:
        """Emit bounded checkpoint load outcomes for runtime resume decisions."""
        if self._metrics is None:
            return
        self._metrics.increment_counter(
            "bioetl_checkpoint_load_events_total",
            1,
            {
                "pipeline": self._pipeline_name,
                "status": status,
            },
        )

    @property
    def current_metadata(self) -> CheckpointMetadata | None:
        """Return execution identity metadata used for compatibility checks."""
        return self._current_metadata

    def _resume_blocked_by_loading_strategy(self) -> bool:
        """Return whether the configured strategy forbids checkpoint resume."""
        return bool(
            self._resume
            and self._loading_strategy is not None
            and not self._loading_strategy.allows_checkpoint_resume
        )

    async def _load_checkpoint_data(self) -> tuple[RunID, JsonDict] | None:
        """Load raw checkpoint data and emit failure metrics on transport errors."""
        try:
            return await self._checkpoint.load(self._pipeline_name)
        except _OPERATION_ERRORS:
            self._emit_checkpoint_load_status("failed")
            raise

    def _resolve_checkpoint_metadata(
        self, checkpoint_data: tuple[RunID, JsonDict]
    ) -> CheckpointMetadata:
        """Convert persisted legacy checkpoint payload into typed metadata."""
        _, legacy_metadata = checkpoint_data
        return CheckpointMetadata.from_legacy_metadata(legacy_metadata)

    def _validate_loaded_checkpoint(
        self,
        checkpoint_metadata: CheckpointMetadata,
        *,
        current_metadata: CheckpointMetadata | None,
    ) -> tuple[CheckpointMetadata | None, bool]:
        """Validate a loaded checkpoint against runtime execution identity."""
        effective_current_metadata = resolve_current_metadata(
            current_metadata,
            default_metadata=self._current_metadata,
        )
        if effective_current_metadata is None or self._compatibility_service is None:
            return checkpoint_metadata, False
        compatibility_result = cast(
            CheckpointCompatibilityService,
            self._compatibility_service,
        ).validate_checkpoint_compatibility(
            effective_current_metadata,
            checkpoint_metadata,
        )
        if compatibility_result.compatible:
            self._logger.info(
                "Checkpoint compatibility validation passed.",
                pipeline=self._pipeline_name,
                messages=compatibility_result.messages,
            )
            return checkpoint_metadata, False
        return (
            self._handle_incompatible_checkpoint_result(
                checkpoint_metadata=checkpoint_metadata,
                current_metadata=effective_current_metadata,
                compatibility_result=compatibility_result,
            ),
            True,
        )

    def _handle_incompatible_checkpoint_result(
        self,
        *,
        checkpoint_metadata: CheckpointMetadata,
        current_metadata: CheckpointMetadata,
        compatibility_result: CheckpointCompatibilityResult,
    ) -> CheckpointMetadata | None:
        """Apply the configured disposition for an incompatible checkpoint."""
        disposition = resolve_incompatible_checkpoint_disposition(
            compatibility_policy=self._compatibility_policy,
            execution_identity_compatible=(
                compatibility_result.execution_identity_compatible
            ),
        )
        try:
            result = handle_incompatible_checkpoint(
                logger=self._logger,
                pipeline_name=self._pipeline_name,
                compatibility_policy=self._compatibility_policy,
                current_metadata=current_metadata,
                checkpoint_metadata=checkpoint_metadata,
                execution_identity_compatible=(
                    compatibility_result.execution_identity_compatible
                ),
                messages=compatibility_result.messages,
            )
        except _OPERATION_ERRORS:
            self._emit_checkpoint_load_status(
                "incompatible_hard_fail"
                if disposition == "hard_fail_raised"
                else "incompatible"
            )
            raise
        if result is None:
            self._emit_checkpoint_load_status(
                "observe_blocked_identity"
                if disposition == "observe_blocked_identity"
                else "incompatible"
            )
            return None
        self._emit_checkpoint_load_status(
            "observe_loaded_degraded"
            if disposition == "observe_loaded_degraded"
            else "loaded"
        )
        return result

    async def load_checkpoint(
        self,
        current_metadata: CheckpointMetadata | None = None,
    ) -> CheckpointMetadata | None:
        """Load a checkpoint when resume is enabled and policy allows it."""
        if self._resume_blocked_by_loading_strategy():
            self._emit_checkpoint_load_status("blocked")
            self._logger.warning(
                "Checkpoint resume blocked for full_scan_only pipeline. "
                "Each run performs a full scan; deduplication via content_hash on Silver. "
                "See ADR-031 for details.",
                pipeline=self._pipeline_name,
                loading_strategy=self._loading_strategy.value,
                resume_requested=True,
            )
            return None

        if not self._resume:
            return None

        checkpoint_data = await self._load_checkpoint_data()
        if checkpoint_data is None:
            self._emit_checkpoint_load_status("missing")
            return None

        checkpoint_metadata = self._resolve_checkpoint_metadata(checkpoint_data)
        compatible_checkpoint, status_already_emitted = (
            self._validate_loaded_checkpoint(
                checkpoint_metadata,
                current_metadata=current_metadata,
            )
        )
        if compatible_checkpoint is None:
            return None

        self._logger.info(
            "Found compatible checkpoint",
            metadata=compatible_checkpoint.to_dict(),
        )
        if not status_already_emitted:
            self._emit_checkpoint_load_status("loaded")
        return compatible_checkpoint

    async def save_checkpoint(self, metadata: CheckpointMetadata | int) -> None:
        """Save checkpoint metadata, accepting the legacy integer shorthand."""
        if isinstance(metadata, int):
            metadata = CheckpointMetadata(records_processed=metadata)
        metadata = enrich_metadata_with_execution_identity(
            metadata, identity=self._current_metadata
        )
        await self._checkpoint.save(
            pipeline=self._pipeline_name,
            run_id=self._run_id,
            metadata=metadata.to_dict(),
        )

    async def delete_checkpoint(self) -> None:
        """Delete checkpoint after successful run."""
        await self._checkpoint.delete(self._pipeline_name)

    async def list_all(self) -> list[str]:
        """List all pipelines that currently have checkpoints."""
        return await self._checkpoint.list_all()


__all__ = ["CheckpointManager", "CheckpointManagerService"]
