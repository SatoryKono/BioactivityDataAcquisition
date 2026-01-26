"""Checkpoint Manager for ETL Pipelines.

This module is framework-agnostic and handles checkpoint persistence
for pipeline run tracking.

Supports force_full_scan mode (ADR-030) and loading_strategy (ADR-031) which
control offset-based resume behavior for entities where API offset pagination
is unreliable (e.g., publications).
"""

from __future__ import annotations

from typing import Any

from bioetl.domain.medallion import LoadingStrategy
from bioetl.domain.ports import CheckpointPort, LoggerPort
from bioetl.domain.types import RunID


class CheckpointManager:
    """Framework-agnostic checkpoint management.

    Handles checkpoint persistence for pipeline run tracking with support
    for force_full_scan mode (ADR-030) and loading_strategy (ADR-031) which
    disable checkpoint-based resume for entities with unreliable offset pagination.
    """

    def __init__(
        self,
        checkpoint_port: CheckpointPort,
        logger: LoggerPort,
        pipeline_name: str,
        run_id: RunID,
        resume: bool,
        *,
        force_full_scan: bool = False,
        loading_strategy: LoadingStrategy | None = None,
    ) -> None:
        """Initialize checkpoint manager.

        Args:
            checkpoint_port: Port for checkpoint operations.
            logger: Logger instance.
            pipeline_name: Name of the pipeline.
            run_id: Unique identifier for the pipeline run.
            resume: Whether to resume from previous checkpoint.
            force_full_scan: If True, checkpoint resume is disabled and each run
                performs a full scan. Used for entities with unreliable offset
                pagination (e.g., publications). Deduplication is handled on
                Silver layer via content_hash. See ADR-030.
            loading_strategy: Explicit loading strategy (ADR-031). Takes precedence
                over force_full_scan if provided. FULL_SCAN_ONLY disables resume.

        """
        self._checkpoint = checkpoint_port
        self._logger = logger
        self._pipeline_name = pipeline_name
        self._run_id = run_id
        self._resume = resume
        self._force_full_scan = force_full_scan
        # Resolve loading_strategy: explicit value takes precedence
        if loading_strategy is not None:
            self._loading_strategy = loading_strategy
        else:
            self._loading_strategy = LoadingStrategy.from_force_full_scan(force_full_scan)

    async def load_checkpoint(self) -> dict[str, Any] | None:
        """Load checkpoint if resuming.

        When loading_strategy is FULL_SCAN_ONLY (ADR-030, ADR-031), checkpoint loading
        is blocked and a warning is logged. This ensures each run performs a full scan
        of the data source, with deduplication handled on Silver layer via content_hash.

        Returns:
            Checkpoint metadata dict if resume is enabled and checkpoint exists,
            None if resume is disabled, loading_strategy forbids resume, or no checkpoint.

        """
        # Block resume for FULL_SCAN_ONLY loading strategy (ADR-030, ADR-031)
        if self._resume and not self._loading_strategy.allows_checkpoint_resume:
            self._logger.warning(
                "Checkpoint resume blocked for full_scan_only pipeline. "
                "Each run performs a full scan; deduplication via content_hash on Silver. "
                "See ADR-030 and ADR-031 for details.",
                extra={
                    "pipeline": self._pipeline_name,
                    "loading_strategy": self._loading_strategy.value,
                    "force_full_scan": self._force_full_scan,
                    "resume_requested": True,
                },
            )
            return None

        if self._resume:
            checkpoint_data = await self._checkpoint.load(self._pipeline_name)
            if checkpoint_data:
                _, metadata = checkpoint_data
                self._logger.info(
                    "Found previous checkpoint",
                    extra={"metadata": metadata},
                )
                return metadata
        return None

    async def save_checkpoint(self, records_processed: int) -> None:
        """Save checkpoint.

        Args:
            records_processed: Count of records processed so far

        """
        await self._checkpoint.save(
            pipeline=self._pipeline_name,
            run_id=self._run_id,
            metadata={"records_processed": records_processed},
        )

    async def delete_checkpoint(self) -> None:
        """Delete checkpoint after successful run."""
        await self._checkpoint.delete(self._pipeline_name)

    async def list_all(self) -> list[str]:
        """List all pipelines that have checkpoints.

        Delegates to CheckpointPort.list_all() for CLI inspection.

        Returns:
            List of pipeline names with existing checkpoints.

        """
        return await self._checkpoint.list_all()
