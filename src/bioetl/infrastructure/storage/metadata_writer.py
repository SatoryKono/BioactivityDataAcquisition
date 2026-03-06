"""Metadata writer implementation for Medallion layer sidecar files.

Writes _metadata.yaml files alongside data artifacts in Bronze, Silver,
and Gold layers using atomic write pattern for consistency.

Implements RULES.md 2.3 and 02-user-rules.md 2.4:
- Lineage tracking
- QC information
- Runtime context
"""

from __future__ import annotations

__all__ = ["METADATA_FILENAME", "MetadataWriter"]

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from bioetl.infrastructure.storage._atomic import AtomicWriteError, atomic_write_text
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

# Default metadata sidecar filename (fallback)
METADATA_FILENAME = "_metadata.yaml"


def _get_metadata_filename(provider: str | None, entity: str | None) -> str:
    """Generate metadata filename based on provider and entity.

    Args:
        provider: Provider name (e.g., 'chembl').
        entity: Entity type (e.g., 'activity').

    Returns:
        Filename in format {provider}_{entity}_metadata.yaml if both provided,
        otherwise falls back to _metadata.yaml.
    """
    if provider and entity:
        return f"{provider}_{entity}_metadata.yaml"
    return METADATA_FILENAME


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

    def _emit_retry_telemetry(
        self,
        *,
        layer: str,
        provider: str | None,
        pipeline: str,
        attempt: int,
        delay_seconds: float,
        reason: str,
    ) -> None:
        """Emit telemetry event for metadata atomic-write retry."""
        self._logger.warning(
            "metadata_atomic_replace_retry",
            layer=layer,
            provider=provider,
            pipeline=pipeline,
            attempt=attempt,
            delay_seconds=delay_seconds,
            reason=reason,
        )
        if self._metrics is not None:
            self._metrics.increment_counter(
                "observability_events_total",
                1,
                {
                    "event": "metadata_atomic_replace_retry",
                    "provider": provider or "storage",
                    "pipeline": pipeline,
                    "severity": "warning",
                    "error_type": reason,
                },
            )

    def _emit_final_telemetry(
        self,
        *,
        layer: str,
        provider: str | None,
        pipeline: str,
        retry_count: int,
        status: str,
        final_reason: str,
    ) -> None:
        """Emit telemetry for final metadata write outcome."""
        if status == "failed":
            self._logger.error(
                "metadata_write_failed",
                layer=layer,
                provider=provider,
                pipeline=pipeline,
                retry_count=retry_count,
                final_reason=final_reason,
            )
        else:
            self._logger.info(
                "metadata_write_completed",
                layer=layer,
                provider=provider,
                pipeline=pipeline,
                retry_count=retry_count,
                final_reason=final_reason,
            )
        if self._metrics is not None:
            self._metrics.increment_counter(
                "observability_events_total",
                1,
                {
                    "event": "metadata_write_final",
                    "provider": provider or "storage",
                    "pipeline": pipeline,
                    "severity": "error" if status == "failed" else "info",
                    "error_type": final_reason,
                },
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
            base_path, metadata, "bronze", provider=provider, entity=entity
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
            base_path,
            metadata,
            "silver",
            table_name=table_name,
            flat_structure=flat_structure,
            provider=provider,
            entity=entity,
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
            base_path,
            metadata,
            "gold",
            table_name=table_name,
            flat_structure=flat_structure,
            provider=provider,
            entity=entity,
        )

    async def _write_metadata(
        self,
        base_path: str | Path,
        metadata: BronzeMetadata | SilverMetadata | GoldMetadata,
        layer: str,
        *,
        table_name: str | None = None,
        flat_structure: bool = False,
        provider: str | None = None,
        entity: str | None = None,
    ) -> str:
        """Write sidecar metadata for Bronze/Silver/Gold layers and return file path."""
        path = Path(base_path)

        # Use provider/entity naming if both are provided
        if provider and entity:
            filename = _get_metadata_filename(provider, entity)
            metadata_path = path / filename
        elif flat_structure and table_name:
            # Backward compatibility: use table_name if flat_structure is True
            metadata_path = path / f"{table_name}_metadata.yaml"
        else:
            metadata_path = path / METADATA_FILENAME

        # Serialize to dict with JSON mode for datetime handling
        metadata_dict = metadata.model_dump(mode="json", by_alias=True)

        # Convert to YAML
        yaml_content = yaml.safe_dump(
            metadata_dict,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

        pipeline_label = table_name or (
            f"{provider}.{entity}" if provider and entity else f"{layer}_metadata"
        )
        retry_state = {"count": 0}

        def on_retry(attempt: int, delay_seconds: float, error: OSError) -> None:
            retry_state["count"] = attempt
            self._emit_retry_telemetry(
                layer=layer,
                provider=provider,
                pipeline=pipeline_label,
                attempt=attempt,
                delay_seconds=delay_seconds,
                reason=str(getattr(error, "errno", "os_error")),
            )

        # Write atomically in executor
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(
                None,
                lambda: atomic_write_text(
                    metadata_path,
                    yaml_content,
                    retry_policy=self._atomic_replace_retry_policy,
                    on_retry=on_retry,
                ),
            )
        except AtomicWriteError as exc:
            self._emit_final_telemetry(
                layer=layer,
                provider=provider,
                pipeline=pipeline_label,
                retry_count=retry_state["count"],
                status="failed",
                final_reason=exc.reason or "atomic_write_error",
            )
            raise
        self._emit_final_telemetry(
            layer=layer,
            provider=provider,
            pipeline=pipeline_label,
            retry_count=retry_state["count"],
            status="succeeded",
            final_reason=(
                "success_after_retry"
                if retry_state["count"] > 0
                else "success_without_retry"
            ),
        )

        self._logger.info(
            "metadata_written",
            layer=layer,
            path=str(metadata_path),
            run_id=metadata.runtime.run_id,
        )

        return str(metadata_path.resolve())

    async def aclose(self) -> None:
        """Release any resources held by the metadata writer.

        No resources to release for filesystem-based writer.
        """
