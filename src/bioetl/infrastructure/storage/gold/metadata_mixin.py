# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Thin metadata and audit facade for GoldWriter."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, cast

from bioetl.infrastructure.storage.gold.io_helpers import load_gold_writer_module
from bioetl.infrastructure.storage.gold.metadata_audit import (
    _build_gold_audit_entry,
    _GoldAuditWriteRequest,
)

if TYPE_CHECKING:
    from pandera.polars import DataFrameSchema

    from bioetl.domain.medallion import GoldWriteMode
    from bioetl.domain.models.metadata import GoldMetadata
    from bioetl.domain.ports import (
        AuditPort,
        LineageStorePort,
        MetadataCoordinatorPort,
        MetricsPort,
    )
    from bioetl.domain.types import GoldRecord, RunID, ScdConfig
    from bioetl.domain.value_objects.silver_result import SilverWriteResult
    from bioetl.infrastructure.storage.gold.writer_protocols import _GoldMetadataHost


class GoldWriterMetadataMixin:
    """Metadata construction and persistence helpers for GoldWriter.

    Provides the public async helpers ``_write_gold_metadata``,
    ``_write_gold_merged_metadata``, ``_write_gold_metadata_file``,
    ``_get_delta_version``, and ``_log_gold_audit`` that the host class
    calls during the Gold write lifecycle.
    """

    _audit: AuditPort | None = None
    _metadata_coordinator: MetadataCoordinatorPort | None = None
    _lineage_store: LineageStorePort | None = None
    _metrics: MetricsPort | None = None
    _transform_version: str | None = None
    _load_gold_writer_module = staticmethod(load_gold_writer_module)

    async def _log_gold_audit(
        self,
        table_name: str,
        records: list[GoldRecord],
        mode: GoldWriteMode,
        ingestion_ts: datetime | None,
        run_id: RunID | None,
    ) -> None:
        host = cast("_GoldMetadataHost", cast(object, self))
        audit_entry = _build_gold_audit_entry(
            host,
            _GoldAuditWriteRequest(
                table_name=table_name,
                records=records,
                mode=mode,
                ingestion_ts=ingestion_ts,
                run_id=run_id,
            ),
        )
        assert self._audit is not None, (
            "_log_gold_audit called without audit configured"
        )
        await self._audit.log_write(audit_entry)

    async def _get_delta_version(self, table_path: str) -> int | None:
        from bioetl.infrastructure.storage.gold.metadata_operations import (
            _extract_delta_table_version,
        )

        host = cast("_GoldMetadataHost", cast(object, self))
        module = host._load_gold_writer_module()

        try:
            dt = await host._run_in_executor(lambda: module.DeltaTable(table_path))
            return _extract_delta_table_version(dt)
        except module.TableNotFoundError:
            return None

    async def _write_gold_metadata(
        self,
        table_path: str,
        table_name: str,
        records: list[GoldRecord],
        mode: GoldWriteMode,
        scd_config: ScdConfig | None,
        ingestion_ts: datetime | None,
        run_id: RunID | None,
        silver_refs: list[SilverWriteResult] | None = None,
        gold_schema: object | None = None,
    ) -> None:
        from bioetl.domain.ports.noop import NoOpMetadataWriter
        from bioetl.infrastructure.storage.gold.metadata_operations import (
            _GoldMetadataWriteRequest,
            _persist_gold_metadata_write,
            _prepare_gold_metadata_write,
        )

        if not records:
            return
        host = cast("_GoldMetadataHost", cast(object, self))
        if isinstance(host._metadata_writer, NoOpMetadataWriter):
            return
        prepared = _prepare_gold_metadata_write(
            host,
            _GoldMetadataWriteRequest(
                table_path=table_path,
                table_name=table_name,
                records=records,
                mode=mode,
                scd_config=scd_config,
                ingestion_ts=ingestion_ts,
                run_id=run_id,
                silver_refs=silver_refs,
                gold_schema=gold_schema,
            ),
        )
        await _persist_gold_metadata_write(host, prepared)

    async def _write_gold_metadata_file(
        self,
        *,
        table_path: str,
        metadata: GoldMetadata,
        table_name: str,
        provider_name: str,
        entity_name: str,
    ) -> None:
        host = cast("_GoldMetadataHost", cast(object, self))
        await host._metadata_writer.write_gold_metadata(
            table_path,
            metadata,
            table_name=table_name,
            flat_structure=host._flat_structure,
            provider=provider_name,
            entity=entity_name,
        )

    async def _write_gold_merged_metadata(
        self,
        table_path: str,
        table_name: str,
        records: list[GoldRecord],
        completed_at: datetime | None = None,
        run_id: RunID | None = None,
        schema: DataFrameSchema | None = None,
    ) -> None:
        from bioetl.domain.ports.noop import NoOpMetadataWriter
        from bioetl.infrastructure.storage.gold.metadata_operations import (
            _GoldMergedMetadataWriteRequest,
            _maybe_prepare_gold_merged_metadata_write,
            _persist_gold_metadata_write,
        )

        host = cast("_GoldMetadataHost", cast(object, self))
        if isinstance(host._metadata_writer, NoOpMetadataWriter):
            return
        prepared = _maybe_prepare_gold_merged_metadata_write(
            host,
            _GoldMergedMetadataWriteRequest(
                table_path=table_path,
                table_name=table_name,
                records=records,
                completed_at=completed_at,
                run_id=run_id,
                schema=schema,
            ),
        )
        if prepared is None:
            return
        await _persist_gold_metadata_write(host, prepared)


__all__ = ["GoldWriterMetadataMixin"]
