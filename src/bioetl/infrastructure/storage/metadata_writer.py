"""Atomic sidecar metadata writer for Bronze, Silver, and Gold layers."""

from __future__ import annotations

__all__ = ["METADATA_FILENAME", "MetadataWriter"]

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.infrastructure.storage import metadata_writer_operations as _operations
from bioetl.infrastructure.storage._atomic import AtomicWriteError, atomic_write_text
from bioetl.infrastructure.storage.metadata_writer_operations import (
    METADATA_FILENAME,
    _build_retry_callback,
    _emit_atomic_write_final_telemetry,
    _MetadataWriteRequest,
    _MetadataWriteRetryState,
    _MetadataWriteTelemetryContext,
    _prepare_metadata_write_operation,
    _PreparedMetadataWrite,
    _PreparedMetadataWriteOperation,
)
from bioetl.infrastructure.storage.write_resilience import (
    DEFAULT_ATOMIC_REPLACE_RETRY_POLICY,
    AdaptiveRetryPolicy,
)

if TYPE_CHECKING:
    from bioetl.domain.models.metadata import (
        BronzeMetadata,
        GoldMetadata,
        SilverMetadata,
    )
    from bioetl.domain.ports import LoggerPort, MetricsPort


_get_metadata_filename = _operations._get_metadata_filename


async def _execute_atomic_metadata_write(
    *,
    logger: LoggerPort,
    metrics: MetricsPort | None,
    prepared_write: _PreparedMetadataWrite,
    retry_policy: AdaptiveRetryPolicy,
    context: _MetadataWriteTelemetryContext,
) -> int:
    """Write prepared metadata atomically and emit retry/final telemetry."""
    retry_state = _MetadataWriteRetryState()
    on_retry = _build_retry_callback(
        logger=logger,
        metrics=metrics,
        context=context,
        retry_state=retry_state,
    )

    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(
            None,
            lambda: atomic_write_text(
                prepared_write.metadata_path,
                prepared_write.yaml_content,
                retry_policy=retry_policy,
                on_retry=on_retry,
            ),
        )
    except AtomicWriteError as exc:
        _emit_atomic_write_final_telemetry(
            logger=logger,
            metrics=metrics,
            context=context,
            retry_state=retry_state,
            status="failed",
            final_reason=exc.reason or "atomic_write_error",
        )
        raise

    _emit_atomic_write_final_telemetry(
        logger=logger,
        metrics=metrics,
        context=context,
        retry_state=retry_state,
        status="succeeded",
        final_reason=(
            "success_after_retry"
            if retry_state.count > 0
            else "success_without_retry"
        ),
    )
    return retry_state.count


def _finalize_metadata_write_operation(
    *,
    logger: LoggerPort,
    operation: _PreparedMetadataWriteOperation,
) -> str:
    """Emit final write log and return the resolved metadata sidecar path."""
    logger.info(
        "metadata_written",
        layer=operation.telemetry_context.layer,
        path=str(operation.prepared_write.metadata_path),
        run_id=operation.run_id,
    )
    return str(operation.prepared_write.metadata_path.resolve())


async def _execute_prepared_metadata_write_operation(
    *,
    logger: LoggerPort,
    metrics: MetricsPort | None,
    retry_policy: AdaptiveRetryPolicy,
    operation: _PreparedMetadataWriteOperation,
) -> str:
    """Execute one prepared metadata write operation end-to-end."""
    await _execute_atomic_metadata_write(
        logger=logger,
        metrics=metrics,
        prepared_write=operation.prepared_write,
        retry_policy=retry_policy,
        context=operation.telemetry_context,
    )
    return _finalize_metadata_write_operation(logger=logger, operation=operation)


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
        self._atomic_replace_retry_policy = (
            atomic_replace_retry_policy or DEFAULT_ATOMIC_REPLACE_RETRY_POLICY
        )

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
        return await self._write_metadata(
            _MetadataWriteRequest(
                base_path=base_path,
                metadata=metadata,
                layer="bronze",
                provider=provider,
                entity=entity,
            )
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
        return await self._write_metadata(
            _MetadataWriteRequest(
                base_path=base_path,
                metadata=metadata,
                layer="silver",
                table_name=table_name,
                flat_structure=flat_structure,
                provider=provider,
                entity=entity,
            )
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
        return await self._write_metadata(
            _MetadataWriteRequest(
                base_path=base_path,
                metadata=metadata,
                layer="gold",
                table_name=table_name,
                flat_structure=flat_structure,
                provider=provider,
                entity=entity,
            )
        )

    async def _write_metadata(self, request: _MetadataWriteRequest) -> str:
        """Write sidecar metadata for Bronze/Silver/Gold layers and return file path."""
        operation = _prepare_metadata_write_operation(request)
        return await _execute_prepared_metadata_write_operation(
            logger=self._logger,
            metrics=self._metrics,
            retry_policy=self._atomic_replace_retry_policy,
            operation=operation,
        )

    async def aclose(self) -> None:
        """Release any resources held by the metadata writer."""
