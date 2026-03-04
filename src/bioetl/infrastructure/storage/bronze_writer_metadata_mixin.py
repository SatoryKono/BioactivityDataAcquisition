"""Metadata builders for BronzeWriter."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, cast

from bioetl.domain.types import BatchID, RunID, RunType

if TYPE_CHECKING:
    from bioetl.domain.models.metadata import BronzeMetadata, SourceMetadata


class BronzeWriterMetadataMixin:
    """Mixin with bronze metadata construction helpers."""

    def _build_bronze_metadata(
        self,
        run_id: RunID,
        run_type: RunType,
        effective_ts: datetime,
        provider: str,
        entity: str,
        batch_id: BatchID,
    ) -> dict[str, str]:
        """Build metadata dict for lineage tracking."""
        return {
            "run_id": str(run_id),
            "run_type": run_type.value,
            "ingestion_ts": effective_ts.isoformat(),
            "provider": provider,
            "entity": entity,
            "batch_id": str(batch_id),
        }

    def _build_full_bronze_metadata(
        self,
        run_id: RunID,
        run_type: RunType,
        provider: str,
        entity: str,
        batch_id: BatchID,
        record_count: int,
        compressed_size: int,
        output_path: str,
        started_at: datetime,
        completed_at: datetime,
        duration_seconds: float,
        source_metadata: SourceMetadata | None = None,
    ) -> BronzeMetadata:
        """Build rich BronzeMetadata for sidecar file."""
        import platform
        import socket

        from bioetl import __version__
        from bioetl.domain.models.metadata import (
            BaseOutputMetadata,
            BronzeMetadata,
            BronzeOutputExt,
            EnvironmentMetadata,
            FileOutputMetadata,
            PipelineMetadata,
            RuntimeMetadata,
            RunTypeEnum,
        )
        from bioetl.domain.models.metadata import SourceMetadata as SourceMetadataModel

        run_type_map = {
            RunType.INCREMENTAL: RunTypeEnum.INCREMENTAL,
            RunType.BACKFILL: RunTypeEnum.BACKFILL,
            RunType.REBUILD: RunTypeEnum.REBUILD,
        }

        resolved_source = (
            source_metadata
            if source_metadata is not None
            else SourceMetadataModel(type="api")
        )

        file_metadata = FileOutputMetadata(
            path=output_path,
            size_bytes=compressed_size,
            record_count=record_count,
        )

        return BronzeMetadata(
            runtime=RuntimeMetadata(
                run_id=str(run_id),
                run_type=run_type_map.get(run_type, RunTypeEnum.INCREMENTAL),
                started_at_utc=started_at,
                completed_at_utc=completed_at,
                duration_seconds=duration_seconds,
            ),
            pipeline=PipelineMetadata(
                name=f"{provider}_{entity}",
                provider=provider,
                entity=entity,
            ),
            source=cast(Any, resolved_source),  # Any: type narrowing cast
            output=BaseOutputMetadata(
                record_count=record_count,
                total_bytes=compressed_size,
                write_started_at=started_at,
                write_completed_at=completed_at,
            ),
            output_ext=BronzeOutputExt(
                files=[file_metadata],
            ),
            environment=EnvironmentMetadata(
                hostname=socket.gethostname(),
                python_version=platform.python_version(),
                bioetl_version=__version__,
            ),
        )



__all__ = ["BronzeWriterMetadataMixin"]
