"""Runtime checkpoint service for ETL pipelines."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.application.core.batch_runtime_failure_policy import (
    OPERATION_ERRORS as SHARED_OPERATION_ERRORS,
)
from bioetl.application.core.lifecycle._checkpoint_types import (
    CheckpointCompatibilityService,
)
from bioetl.application.core.lifecycle.checkpoint_load_validation import (
    resolve_checkpoint_metadata,
    validate_loaded_checkpoint,
)
from bioetl.application.core.lifecycle.checkpoint_runtime import (
    CheckpointCompatibilityPolicy,
    enrich_metadata_with_execution_identity,
    validate_compatibility_policy,
)
from bioetl.application.core.lifecycle.checkpoint_saved_at import (
    metadata_with_checkpoint_saved_at,
    set_checkpoint_saved_at,
)
from bioetl.domain.medallion import LoadingStrategy
from bioetl.domain.ports import CheckpointPort, ClockPort, LoggerPort, MetricsPort
from bioetl.domain.types import JsonDict, RunID
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata

_OPERATION_ERRORS = SHARED_OPERATION_ERRORS


@dataclass(frozen=True, slots=True)
class CheckpointRuntimeIdentityInfo:
    """Identity and resume policy bag for :class:`CheckpointRuntimeService`."""

    pipeline_name: str
    run_id: RunID
    resume: bool
    resume_run_id: RunID | None = None
    resume_manifest_id: str | None = None
    loading_strategy: LoadingStrategy | None = None
    current_metadata: CheckpointMetadata | None = None
    compatibility_policy: CheckpointCompatibilityPolicy = "soft_fail"


# Backward-compatible public alias retained for existing composition callers.
CheckpointRuntimeIdentity = CheckpointRuntimeIdentityInfo


class CheckpointRuntimeService:
    """Framework-agnostic checkpoint persistence and resume management."""

    _operation_errors = _OPERATION_ERRORS

    def __init__(
        self,
        checkpoint_port: CheckpointPort,
        logger: LoggerPort,
        identity: CheckpointRuntimeIdentity,
        *,
        metrics: MetricsPort | None = None,
        clock: ClockPort | None = None,
        checkpoint_compatibility_service: CheckpointCompatibilityService | None = None,
    ) -> None:
        """Initialize checkpoint management with explicit collaborators."""
        self._checkpoint = checkpoint_port
        self._logger = logger
        self._pipeline_name = identity.pipeline_name
        self._run_id = identity.run_id
        self._resume = identity.resume
        self._resume_run_id = identity.resume_run_id
        self._resume_manifest_id = identity.resume_manifest_id
        self._loading_strategy = identity.loading_strategy
        self._metrics = metrics
        self._clock = clock
        self._compatibility_service = checkpoint_compatibility_service
        self._current_metadata = identity.current_metadata
        self._compatibility_policy = validate_compatibility_policy(
            identity.compatibility_policy
        )

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
            if self._resume_manifest_id is not None:
                return await self._checkpoint.load_for_manifest_id(
                    self._resume_manifest_id
                )
            if self._resume_run_id is not None:
                return await self._checkpoint.load_for_run(
                    self._pipeline_name,
                    self._resume_run_id,
                )
            return await self._checkpoint.load(self._pipeline_name)
        except _OPERATION_ERRORS:
            self._emit_checkpoint_load_status("failed")
            raise

    async def load_checkpoint(
        self,
        current_metadata: CheckpointMetadata | None = None,
    ) -> CheckpointMetadata | None:
        """Load a checkpoint when resume is enabled and policy allows it."""
        if self._resume_blocked_by_loading_strategy():
            loading_strategy = self._loading_strategy
            assert loading_strategy is not None
            self._emit_checkpoint_load_status("blocked")
            self._logger.warning(
                "Checkpoint resume blocked for full_scan_only pipeline. "
                "Each run performs a full scan; deduplication via content_hash on Silver. "
                "See ADR-031 for details.",
                pipeline=self._pipeline_name,
                loading_strategy=loading_strategy.value,
                resume_requested=True,
            )
            return None

        if not self._resume:
            return None

        checkpoint_data = await self._load_checkpoint_data()
        if checkpoint_data is None:
            self._emit_checkpoint_load_status("missing")
            return None

        _, raw_metadata = checkpoint_data
        set_checkpoint_saved_at(
            self._metrics,
            pipeline_name=self._pipeline_name,
            checkpoint_saved_at_epoch_seconds=raw_metadata.get(
                "checkpoint_saved_at_epoch_seconds"
            ),
        )
        checkpoint_metadata = resolve_checkpoint_metadata(checkpoint_data)
        compatible_checkpoint, status_already_emitted = validate_loaded_checkpoint(
            self,
            checkpoint_metadata,
            current_metadata=current_metadata,
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
        metadata_payload = metadata_with_checkpoint_saved_at(
            metadata, clock=self._clock
        )
        await self._checkpoint.save(
            pipeline=self._pipeline_name,
            run_id=self._run_id,
            metadata=metadata_payload,
        )
        set_checkpoint_saved_at(
            self._metrics,
            pipeline_name=self._pipeline_name,
            checkpoint_saved_at_epoch_seconds=metadata_payload.get(
                "checkpoint_saved_at_epoch_seconds"
            ),
        )

    async def delete_checkpoint(self) -> None:
        """Delete checkpoint after successful run."""
        await self._checkpoint.delete(self._pipeline_name)

    async def list_all(self) -> list[str]:
        """List all pipelines that currently have checkpoints."""
        return await self._checkpoint.list_all()


__all__ = [
    "CheckpointRuntimeIdentity",
    "CheckpointRuntimeService",
]
