"""Checkpoint Manager for ETL Pipelines.

This module is framework-agnostic and handles checkpoint persistence
for pipeline run tracking.

Supports loading_strategy (ADR-031) which controls offset-based resume behavior
for entities where API offset pagination is unreliable (e.g., publications).
"""

from __future__ import annotations

from typing import Any, Literal, cast

from bioetl.domain.medallion import LoadingStrategy
from bioetl.domain.ports import CheckpointPort, LoggerPort
from bioetl.domain.types import RunID
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata

CheckpointCompatibilityPolicy = Literal["observe", "soft_fail", "hard_fail"]


class CheckpointManagerService:
    """Framework-agnostic checkpoint management.

    Handles checkpoint persistence for pipeline run tracking with support
    for loading_strategy (ADR-031) which disables checkpoint-based resume
    for entities with unreliable offset pagination.
    """

    def __init__(
        self,
        checkpoint_port: CheckpointPort,
        logger: LoggerPort,
        pipeline_name: str,
        run_id: RunID,
        resume: bool,
        *,
        loading_strategy: LoadingStrategy | None = None,
        checkpoint_compatibility_service: object | None = None,
        current_metadata: CheckpointMetadata | None = None,
        compatibility_policy: CheckpointCompatibilityPolicy = "soft_fail",
    ) -> None:
        """Initialize checkpoint manager.

        Args:
            checkpoint_port: Port for checkpoint operations.
            logger: Logger instance.
            pipeline_name: Name of the pipeline.
            run_id: Unique identifier for the pipeline run.
            resume: Whether to resume from previous checkpoint.
            loading_strategy: Loading strategy (ADR-031).
                FULL_SCAN_ONLY disables checkpoint resume.
            checkpoint_compatibility_service: Optional service for DQ compatibility validation.
            current_metadata: Optional current execution identity metadata.
            compatibility_policy: Incompatible checkpoint handling mode
                (`observe`, `soft_fail`, `hard_fail`).

        """
        self._checkpoint = checkpoint_port
        self._logger = logger
        self._pipeline_name = pipeline_name
        self._run_id = run_id
        self._resume = resume
        self._loading_strategy = loading_strategy
        self._compatibility_service = checkpoint_compatibility_service
        self._current_metadata = current_metadata
        self._compatibility_policy = self._validate_compatibility_policy(
            compatibility_policy
        )

    @staticmethod
    def _validate_compatibility_policy(
        policy: CheckpointCompatibilityPolicy,
    ) -> CheckpointCompatibilityPolicy:
        allowed: tuple[CheckpointCompatibilityPolicy, ...] = (
            "observe",
            "soft_fail",
            "hard_fail",
        )
        if policy not in allowed:
            raise ValueError(
                f"Unsupported checkpoint compatibility policy: {policy!r}. "
                f"Expected one of {allowed}."
            )
        return policy

    @property
    def current_metadata(self) -> CheckpointMetadata | None:
        """Return current execution identity metadata used for compatibility checks."""
        return self._current_metadata

    def _resolve_current_metadata(
        self,
        current_metadata: CheckpointMetadata | None,
    ) -> CheckpointMetadata | None:
        return (
            current_metadata if current_metadata is not None else self._current_metadata
        )

    def _enrich_metadata_with_execution_identity(
        self,
        metadata: CheckpointMetadata,
    ) -> CheckpointMetadata:
        """Fill missing execution identity fields from current metadata."""
        identity = self._current_metadata
        if identity is None:
            return metadata
        return CheckpointMetadata(
            records_processed=metadata.records_processed,
            dq_contract_compatibility_hash=(
                metadata.dq_contract_compatibility_hash
                if metadata.dq_contract_compatibility_hash is not None
                else identity.dq_contract_compatibility_hash
            ),
            dq_policy_hash=(
                metadata.dq_policy_hash
                if metadata.dq_policy_hash is not None
                else identity.dq_policy_hash
            ),
            dq_rule_bundle_version=(
                metadata.dq_rule_bundle_version
                if metadata.dq_rule_bundle_version is not None
                else identity.dq_rule_bundle_version
            ),
            pipeline_version=(
                metadata.pipeline_version
                if metadata.pipeline_version is not None
                else identity.pipeline_version
            ),
            effective_config_hash=(
                metadata.effective_config_hash
                if metadata.effective_config_hash is not None
                else identity.effective_config_hash
            ),
            effective_config_artifact_id=(
                metadata.effective_config_artifact_id
                if metadata.effective_config_artifact_id is not None
                else identity.effective_config_artifact_id
            ),
            execution_fingerprint=(
                metadata.execution_fingerprint
                if metadata.execution_fingerprint is not None
                else identity.execution_fingerprint
            ),
            run_context=metadata.run_context
            if metadata.run_context is not None
            else identity.run_context,
        )

    def _handle_incompatible_checkpoint(
        self,
        *,
        checkpoint_metadata: CheckpointMetadata,
        messages: list[str],
    ) -> CheckpointMetadata | None:
        """Handle incompatible checkpoint according to configured policy."""
        payload = {
            "pipeline": self._pipeline_name,
            "compatibility_policy": self._compatibility_policy,
            "messages": messages,
            "checkpoint_metadata": checkpoint_metadata.to_dict(),
        }
        if self._compatibility_policy == "observe":
            self._logger.warning(
                "Checkpoint compatibility mismatch observed; resume continues.",
                extra=payload,
            )
            return checkpoint_metadata
        if self._compatibility_policy == "soft_fail":
            self._logger.warning(
                "Checkpoint compatibility mismatch; resume blocked by soft_fail policy.",
                extra=payload,
            )
            return None
        raise ValueError(
            "Checkpoint compatibility mismatch and hard_fail policy is enabled: "
            + "; ".join(messages)
        )

    async def load_checkpoint(
        self,
        current_metadata: CheckpointMetadata | None = None,
    ) -> CheckpointMetadata | None:
        """Load checkpoint if resuming.

        When loading_strategy is FULL_SCAN_ONLY (ADR-030, ADR-031), checkpoint loading
        is blocked and a warning is logged. This ensures each run performs a full scan
        of the data source, with deduplication handled on Silver layer via content_hash.

        Args:
            current_metadata: Optional current run metadata for compatibility validation.

        Returns:
            CheckpointMetadata if resume is enabled, compatible, and checkpoint exists,
            None if resume is disabled, loading_strategy forbids resume, incompatible, or no checkpoint.

        """
        # Block resume for FULL_SCAN_ONLY loading strategy (ADR-030, ADR-031)
        if (
            self._resume
            and self._loading_strategy is not None
            and not self._loading_strategy.allows_checkpoint_resume
        ):
            self._logger.warning(
                "Checkpoint resume blocked for full_scan_only pipeline. "
                "Each run performs a full scan; deduplication via content_hash on Silver. "
                "See ADR-031 for details.",
                extra={
                    "pipeline": self._pipeline_name,
                    "loading_strategy": self._loading_strategy.value,
                    "resume_requested": True,
                },
            )
            return None

        if self._resume:
            checkpoint_data = await self._checkpoint.load(self._pipeline_name)
            if checkpoint_data:
                _, legacy_metadata = checkpoint_data

                # Convert legacy metadata to new format
                checkpoint_metadata = CheckpointMetadata.from_legacy_metadata(
                    legacy_metadata
                )

                # Validate compatibility if current metadata is provided
                effective_current_metadata = self._resolve_current_metadata(
                    current_metadata
                )
                if effective_current_metadata and self._compatibility_service:
                    compatibility_result = cast(
                        "Any",  # Any: optional compatibility service is duck-typed
                        self._compatibility_service,
                    ).validate_checkpoint_compatibility(
                        effective_current_metadata, checkpoint_metadata
                    )

                    if not compatibility_result.compatible:
                        return self._handle_incompatible_checkpoint(
                            checkpoint_metadata=checkpoint_metadata,
                            messages=compatibility_result.messages,
                        )
                    else:
                        self._logger.info(
                            "Checkpoint compatibility validation passed.",
                            extra={
                                "pipeline": self._pipeline_name,
                                "messages": compatibility_result.messages,
                            },
                        )

                self._logger.info(
                    "Found compatible checkpoint",
                    extra={"metadata": checkpoint_metadata.to_dict()},
                )
                return checkpoint_metadata
        return None

    async def save_checkpoint(self, metadata: CheckpointMetadata | int) -> None:
        """Save checkpoint with extended metadata.

        Args:
            metadata: Checkpoint metadata (CheckpointMetadata) or legacy records_processed (int)

        """
        if isinstance(metadata, int):
            # Legacy API compatibility - convert int to CheckpointMetadata
            metadata = CheckpointMetadata(records_processed=metadata)
        metadata = self._enrich_metadata_with_execution_identity(metadata)

        await self._checkpoint.save(
            pipeline=self._pipeline_name,
            run_id=self._run_id,
            metadata=metadata.to_dict(),
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


# Compatibility alias retained for legacy imports; new code should use
# CheckpointManagerService directly.
CheckpointManager = CheckpointManagerService

__all__ = ["CheckpointManager", "CheckpointManagerService"]
