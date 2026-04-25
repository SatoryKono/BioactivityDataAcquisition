"""Silver audit and metadata helper mixin."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import TYPE_CHECKING, Any, cast

from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.types import BronzeRecord

if TYPE_CHECKING:
    from bioetl.domain.models.metadata import SilverMetadata
    from bioetl.domain.types import BatchID, RunID, RunType
    from bioetl.infrastructure.storage.silver.metadata_mixin import (
        SilverWriterMetadataMixin,
    )

__all__ = ["SilverWriterAuditMetadataCompatibilityMixin"]


class SilverWriterAuditMetadataCompatibilityMixin:
    """Delegation surface for Silver audit and metadata write helpers."""

    _metadata: object | None

    def _as_metadata_mixin(self) -> SilverWriterMetadataMixin:
        """Treat this compatibility host as a SilverWriterMetadataMixin implementation."""
        return cast("SilverWriterMetadataMixin", self)

    async def _log_silver_audit(
        self,
        table_name: str,
        records: list[BronzeRecord],
        mode: SilverWriteMode,
        *,
        run_id: RunID | None,
        run_type: RunType | None,
        source_batch_id: BatchID | None,
        ingestion_ts: datetime | None,
    ) -> None:
        """Delegate audit logging to the metadata service."""
        if self._metadata:
            await cast(Any, self._metadata)._log_silver_audit(  # Any: _metadata is typed as object and its concrete type is determined at runtime.
                table_name=table_name,
                records=records,
                mode=mode,
                run_id=run_id,
                run_type=run_type,
                source_batch_id=source_batch_id,
                ingestion_ts=ingestion_ts,
            )
            return

        from bioetl.infrastructure.storage.silver.metadata_mixin import (
            SilverWriterMetadataMixin,
        )

        await SilverWriterMetadataMixin._log_silver_audit(
            self._as_metadata_mixin(),
            table_name,
            records,
            mode,
            run_id=run_id,
            run_type=run_type,
            source_batch_id=source_batch_id,
            ingestion_ts=ingestion_ts,
        )
        return

    def _should_skip_silver_metadata_write(
        self,
        *,
        records: list[BronzeRecord],
        table_path: str,
        event_name: str,
    ) -> bool:
        """Delegation seam for metadata write short-circuit checks."""
        from bioetl.infrastructure.storage.silver.metadata_mixin import (
            SilverWriterMetadataMixin,
        )

        return SilverWriterMetadataMixin._should_skip_silver_metadata_write(
            self._as_metadata_mixin(),
            records=records,
            table_path=table_path,
            event_name=event_name,
        )

    async def _write_silver_metadata_file(
        self,
        *,
        table_path: str,
        metadata: SilverMetadata,
        table_name: str,
        provider_name: str,
        entity_name: str,
    ) -> None:
        """Compatibility seam for canonical metadata writer handoff."""
        from bioetl.infrastructure.storage.silver.metadata_mixin import (
            SilverWriterMetadataMixin,
        )

        await SilverWriterMetadataMixin._write_silver_metadata_file(
            self._as_metadata_mixin(),
            table_path=table_path,
            metadata=metadata,
            table_name=table_name,
            provider_name=provider_name,
            entity_name=entity_name,
        )

    async def _maybe_log_silver_audit(
        self,
        *,
        table_name: str,
        records: list[BronzeRecord],
        mode: SilverWriteMode,
        run_id: RunID | None,
        run_type: RunType | None,
        source_batch_id: BatchID | None,
        ingestion_ts: datetime | None,
    ) -> None:
        """Compatibility seam for conditional Silver audit logging."""
        from bioetl.infrastructure.storage.silver.metadata_mixin import (
            SilverWriterMetadataMixin,
        )

        await SilverWriterMetadataMixin._maybe_log_silver_audit(
            self._as_metadata_mixin(),
            table_name=table_name,
            records=records,
            mode=mode,
            run_id=run_id,
            run_type=run_type,
            source_batch_id=source_batch_id,
            ingestion_ts=ingestion_ts,
        )

    async def _write_silver_metadata(
        self,
        request: object = None,
        *args: object,
        **kwargs: object,
    ) -> None:
        """Backward compatibility method for writing Silver metadata."""
        from bioetl.infrastructure.storage.silver.metadata_operations import (
            _coerce_silver_metadata_write_request,
            _SilverMetadataWriteRequest,
        )

        request_input: _SilverMetadataWriteRequest | str | None
        legacy_args: tuple[object, ...]
        if isinstance(request, (_SilverMetadataWriteRequest, str)) or request is None:
            request_input = request
            legacy_args = args
        else:
            request_input = None
            legacy_args = (request, *args)

        resolved_request = _coerce_silver_metadata_write_request(
            request_input,
            args=legacy_args,
            kwargs=kwargs,
        )
        if resolved_request.dq_metrics is None:
            from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics

            resolved_request = replace(
                resolved_request,
                dq_metrics=BatchDQMetrics(
                    total_records=len(resolved_request.records),
                    valid_records=len(resolved_request.records),
                    error_records=0,
                    warning_records=0,
                ),
            )

        from bioetl.infrastructure.storage.silver.metadata_mixin import (
            SilverWriterMetadataMixin,
        )

        await SilverWriterMetadataMixin._write_silver_metadata(
            self._as_metadata_mixin(),
            resolved_request,
        )

    async def _get_delta_version(self, table_path: str) -> int | None:
        """Get the current Delta Lake version for a table."""
        from bioetl.infrastructure.storage.silver.metadata_mixin import (
            SilverWriterMetadataMixin,
        )

        return await SilverWriterMetadataMixin._get_delta_version(
            self._as_metadata_mixin(), table_path
        )
