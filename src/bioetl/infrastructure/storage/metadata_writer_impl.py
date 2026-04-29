"""Atomic sidecar metadata writer for Bronze, Silver, and Gold layers."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, cast

from bioetl.infrastructure.storage.delta.resilience import (
    DEFAULT_ATOMIC_REPLACE_RETRY_POLICY,
    AdaptiveRetryPolicy,
)
from bioetl.infrastructure.storage.metadata.writer_operations import (
    METADATA_FILENAME,
    _MetadataWriteRequest,
    _prepare_metadata_write_operation,
)

from .metadata_writer_helpers import (
    ArtifactPublicationRecorder,
    _apply_gold_metadata_finalization,
    _apply_silver_metadata_finalization,
    _execute_prepared_metadata_write_operation,
    _load_existing_metadata_model,
    _record_artifact_publication,
    _resolve_existing_metadata_path,
)

__all__ = ["METADATA_FILENAME", "MetadataWriter"]

if TYPE_CHECKING:
    from bioetl.domain.models.metadata import (
        BronzeMetadata,
        GoldMetadata,
        SilverMetadata,
    )
    from bioetl.domain.ports import LoggerPort, MetricsPort


class MetadataWriter:
    """Writer for metadata sidecar files across Bronze/Silver/Gold layers."""

    def __init__(
        self,
        logger: LoggerPort,
        *,
        atomic_replace_retry_policy: AdaptiveRetryPolicy | None = None,
        metrics: MetricsPort | None = None,
    ) -> None:
        """Initialize metadata writer (logger is mandatory per DI rules)."""
        self._logger = logger
        self._metrics = metrics
        self._artifact_recorder: ArtifactPublicationRecorder | None = None
        self._atomic_replace_retry_policy = (
            atomic_replace_retry_policy or DEFAULT_ATOMIC_REPLACE_RETRY_POLICY
        )

    def attach_artifact_recorder(
        self,
        recorder: ArtifactPublicationRecorder | None,
    ) -> None:
        """Attach an optional callback for control-plane artifact publication."""
        self._artifact_recorder = recorder

    def _build_metadata_write_request(
        self,
        *,
        base_path: str | Path,
        metadata: BronzeMetadata | SilverMetadata | GoldMetadata,
        layer: str,
        table_name: str | None = None,
        flat_structure: bool = False,
        provider: str | None = None,
        entity: str | None = None,
    ) -> _MetadataWriteRequest:
        """Build a normalized metadata sidecar request for the canonical write path."""
        return _MetadataWriteRequest(
            base_path=base_path,
            metadata=metadata,
            layer=layer,
            table_name=table_name,
            flat_structure=flat_structure,
            provider=provider,
            entity=entity,
        )

    async def _finalize_existing_layer_metadata(
        self,
        *,
        base_path: str | Path,
        layer: str,
        apply_finalization: Callable[[SilverMetadata | GoldMetadata], None],
        table_name: str | None = None,
        flat_structure: bool = False,
        provider: str | None = None,
        entity: str | None = None,
    ) -> str | None:
        """Load, patch, and atomically rewrite an existing Silver/Gold sidecar."""
        metadata_path = _resolve_existing_metadata_path(
            base_path=base_path,
            layer=layer,
            table_name=table_name,
            flat_structure=flat_structure,
            provider=provider,
            entity=entity,
        )
        existing_metadata = await asyncio.to_thread(
            _load_existing_metadata_model,
            metadata_path,
            layer=layer,
        )
        if existing_metadata is None:
            return None

        apply_finalization(existing_metadata)
        return await self._write_metadata(
            self._build_metadata_write_request(
                base_path=base_path,
                metadata=existing_metadata,
                layer=layer,
                table_name=table_name,
                flat_structure=flat_structure,
                provider=provider,
                entity=entity,
            )
        )

    async def _write_layer_metadata(
        self,
        *,
        base_path: str | Path,
        metadata: BronzeMetadata | SilverMetadata | GoldMetadata,
        layer: str,
        table_name: str | None = None,
        flat_structure: bool = False,
        provider: str | None = None,
        entity: str | None = None,
    ) -> str:
        """Build and execute one normalized metadata write request."""
        metadata_path = await self._write_metadata(
            self._build_metadata_write_request(
                base_path=base_path,
                metadata=metadata,
                layer=layer,
                table_name=table_name,
                flat_structure=flat_structure,
                provider=provider,
                entity=entity,
            )
        )
        _record_artifact_publication(
            recorder=self._artifact_recorder,
            metrics=self._metrics,
            layer=layer,
            base_path=base_path,
            metadata_path=metadata_path,
            metadata=metadata,
        )
        return metadata_path

    async def write_bronze_metadata(
        self,
        base_path: str | Path,
        metadata: BronzeMetadata,
        *,
        provider: str | None = None,
        entity: str | None = None,
    ) -> str:
        """Write Bronze layer metadata sidecar file.

        Args:
            base_path: Base path where Bronze data is stored.
                      Metadata will be written to {base_path}/{provider}_{entity}_metadata.yaml
                      or {base_path}/_metadata.yaml if provider/entity not provided.
            metadata: Bronze metadata model with lineage and source info.
            provider: Provider name (e.g., 'chembl') for filename generation.
            entity: Entity type (e.g., 'activity') for filename generation.

        Returns:
            Absolute path to the written metadata file.
        """
        return await self._write_layer_metadata(
            base_path=base_path,
            metadata=metadata,
            layer="bronze",
            provider=provider,
            entity=entity,
        )

    async def write_silver_metadata(
        self,
        base_path: str | Path,
        metadata: SilverMetadata,
        *,
        table_name: str | None = None,
        flat_structure: bool = False,
        provider: str | None = None,
        entity: str | None = None,
    ) -> str:
        """Write Silver layer metadata sidecar file.

        Args:
            base_path: Base path where Silver Delta table is stored.
                      Metadata will be written to {base_path}/{provider}_{entity}_metadata.yaml
                      or {base_path}/_metadata.yaml if provider/entity not provided.
            metadata: Silver metadata model with lineage, DQ metrics, and Delta info.
            table_name: Table name for flat_structure naming pattern (deprecated).
            flat_structure: If True and provider/entity provided, uses new naming.
            provider: Provider name (e.g., 'chembl') for filename generation.
            entity: Entity type (e.g., 'activity') for filename generation.

        Returns:
            Absolute path to the written metadata file.
        """
        return await self._write_layer_metadata(
            base_path=base_path,
            metadata=metadata,
            layer="silver",
            table_name=table_name,
            flat_structure=flat_structure,
            provider=provider,
            entity=entity,
        )

    async def finalize_silver_metadata(
        self,
        base_path: str | Path,
        *,
        table_name: str | None = None,
        flat_structure: bool = False,
        provider: str | None = None,
        entity: str | None = None,
        dq_report_path: str | None = None,
        completed_at: datetime | None = None,
        delta_version_after: int | None = None,
    ) -> str | None:
        """Finalize an existing Silver sidecar in place without republishing artifacts."""

        def apply_finalization(metadata: SilverMetadata | GoldMetadata) -> None:
            _apply_silver_metadata_finalization(
                metadata=cast("SilverMetadata", metadata),
                dq_report_path=dq_report_path,
                completed_at=completed_at,
                delta_version_after=delta_version_after,
            )

        return await self._finalize_existing_layer_metadata(
            base_path=base_path,
            layer="silver",
            table_name=table_name,
            flat_structure=flat_structure,
            provider=provider,
            entity=entity,
            apply_finalization=apply_finalization,
        )

    async def write_gold_metadata(
        self,
        base_path: str | Path,
        metadata: GoldMetadata,
        *,
        table_name: str | None = None,
        flat_structure: bool = False,
        provider: str | None = None,
        entity: str | None = None,
    ) -> str:
        """Write Gold layer metadata sidecar file.

        Args:
            base_path: Base path where Gold Delta/Parquet table is stored.
                      Metadata will be written to {base_path}/{provider}_{entity}_metadata.yaml
                      or {base_path}/_metadata.yaml if provider/entity not provided.
            metadata: Gold metadata model with lineage, schema contract, and SCD info.
            table_name: Table name for flat_structure naming pattern (deprecated).
            flat_structure: If True and provider/entity provided, uses new naming.
            provider: Provider name (e.g., 'chembl') for filename generation.
            entity: Entity type (e.g., 'activity') for filename generation.

        Returns:
            Absolute path to the written metadata file.
        """
        return await self._write_layer_metadata(
            base_path=base_path,
            metadata=metadata,
            layer="gold",
            table_name=table_name,
            flat_structure=flat_structure,
            provider=provider,
            entity=entity,
        )

    async def finalize_gold_metadata(
        self,
        base_path: str | Path,
        *,
        table_name: str | None = None,
        flat_structure: bool = False,
        provider: str | None = None,
        entity: str | None = None,
        dq_report_path: str | None = None,
        completed_at: datetime | None = None,
    ) -> str | None:
        """Finalize an existing Gold sidecar in place without republishing artifacts."""

        def apply_finalization(metadata: SilverMetadata | GoldMetadata) -> None:
            _apply_gold_metadata_finalization(
                metadata=cast("GoldMetadata", metadata),
                dq_report_path=dq_report_path,
                completed_at=completed_at,
            )

        return await self._finalize_existing_layer_metadata(
            base_path=base_path,
            layer="gold",
            table_name=table_name,
            flat_structure=flat_structure,
            provider=provider,
            entity=entity,
            apply_finalization=apply_finalization,
        )

    async def _write_metadata(self, request: _MetadataWriteRequest) -> str:
        """Write sidecar metadata for Bronze/Silver/Gold layers and return file path."""
        operation = _prepare_metadata_write_operation(request)
        return await _execute_prepared_metadata_write_operation(
            logger=self._logger,
            metrics=self._metrics,
            retry_policy=self._atomic_replace_retry_policy,
            operation=operation,
            metadata=request.metadata,
        )

    async def aclose(self) -> None:
        """Release any resources held by the metadata writer."""
