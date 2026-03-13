"""Metadata and audit helpers for GoldWriter."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from types import ModuleType
from typing import TYPE_CHECKING, Protocol

from bioetl.domain.medallion import GoldWriteMode
from bioetl.domain.types import RunID
from bioetl.infrastructure.storage.gold_writer_metadata_audit import (
    _build_gold_audit_entry,
    _GoldAuditWriteRequest,
)

if TYPE_CHECKING:
    from pandera.polars import DataFrameSchema

    from bioetl.domain.models.metadata import GoldMetadata
    from bioetl.domain.ports import (
        AuditPort,
        GoldMetadataInput,
        LoggerPort,
        MetadataCoordinatorPort,
        MetadataWriterPort,
    )
    from bioetl.domain.types import GoldRecord, ScdConfig
    from bioetl.domain.value_objects.silver_result import SilverWriteResult


@dataclass(frozen=True, slots=True)
class _GoldMetadataWriteRequest:
    table_path: str
    table_name: str
    records: list[GoldRecord]
    mode: GoldWriteMode
    scd_config: ScdConfig | None
    ingestion_ts: datetime | None
    run_id: RunID | None
    silver_refs: list[SilverWriteResult] | None = None
    gold_schema: object | None = None


@dataclass(frozen=True, slots=True)
class _PreparedGoldMetadataWrite:
    request: _GoldMetadataWriteRequest | _GoldMergedMetadataWriteRequest
    provider_name: str
    entity_name: str
    metadata: GoldMetadata


@dataclass(frozen=True, slots=True)
class _GoldMergedMetadataWriteRequest:
    table_path: str
    table_name: str
    records: list[GoldRecord]
    schema: DataFrameSchema | None = None


class _GoldMetadataWriteHostProtocol(Protocol):
    _metadata_coordinator: MetadataCoordinatorPort | None
    def _resolve_provider_entity(self, table_name: str) -> tuple[str, str]: ...

    def _create_gold_metadata_payload(
        self,
        *,
        table_path: str,
        table_name: str,
        records: list[GoldRecord],
        mode: GoldWriteMode,
        scd_config: ScdConfig | None,
        ingestion_ts: datetime | None,
        run_id: RunID | None,
        silver_refs: list[SilverWriteResult] | None = None,
        gold_schema: object | None = None,
    ) -> GoldMetadata: ...

    def _build_gold_merged_metadata_input(
        self,
        *,
        table_path: str,
        table_name: str,
        records: list[GoldRecord],
        schema: DataFrameSchema | None,
    ) -> GoldMetadataInput: ...

    async def _write_gold_metadata_file(
        self,
        *,
        table_path: str,
        metadata: GoldMetadata,
        table_name: str,
        provider_name: str,
        entity_name: str,
    ) -> None: ...

class _GoldMergedMetadataWriteHostProtocol(_GoldMetadataWriteHostProtocol, Protocol):
    logger: LoggerPort


def _prepare_gold_metadata_write(
    host: _GoldMetadataWriteHostProtocol,
    request: _GoldMetadataWriteRequest,
) -> _PreparedGoldMetadataWrite:
    provider_name, entity_name = host._resolve_provider_entity(request.table_name)
    metadata = host._create_gold_metadata_payload(
        table_path=request.table_path,
        table_name=request.table_name,
        records=request.records,
        mode=request.mode,
        scd_config=request.scd_config,
        ingestion_ts=request.ingestion_ts,
        run_id=request.run_id,
        silver_refs=request.silver_refs,
        gold_schema=request.gold_schema,
    )
    return _PreparedGoldMetadataWrite(
        request=request,
        provider_name=provider_name,
        entity_name=entity_name,
        metadata=metadata,
    )

async def _persist_gold_metadata_write(
    host: _GoldMetadataWriteHostProtocol,
    prepared: _PreparedGoldMetadataWrite,
) -> None:
    await host._write_gold_metadata_file(
        table_path=prepared.request.table_path,
        metadata=prepared.metadata,
        table_name=prepared.request.table_name,
        provider_name=prepared.provider_name,
        entity_name=prepared.entity_name,
    )


def _prepare_gold_merged_metadata_write(
    host: _GoldMetadataWriteHostProtocol,
    request: _GoldMergedMetadataWriteRequest,
) -> _PreparedGoldMetadataWrite:
    from bioetl.infrastructure.storage.metadata_builder import _parse_table_name

    provider_name, entity_name = _parse_table_name(request.table_name)
    assert host._metadata_coordinator is not None
    metadata = host._metadata_coordinator.create_gold_metadata(
        host._build_gold_merged_metadata_input(
            table_path=request.table_path,
            table_name=request.table_name,
            records=request.records,
            schema=request.schema,
        )
    )
    return _PreparedGoldMetadataWrite(
        request=request,
        provider_name=provider_name,
        entity_name=entity_name,
        metadata=metadata,
    )


def _maybe_prepare_gold_merged_metadata_write(
    host: _GoldMergedMetadataWriteHostProtocol,
    request: _GoldMergedMetadataWriteRequest,
) -> _PreparedGoldMetadataWrite | None:
    if not request.records:
        return None
    if host._metadata_coordinator is None:
        host.logger.debug(
            "gold_merged_metadata_skipped",
            reason="MetadataCoordinator not configured",
            table_path=request.table_path,
        )
        return None
    return _prepare_gold_merged_metadata_write(host, request)


class _GoldWriterMergedMetadataInputMixin:
    _transform_version: str | None
    _transform_steps: tuple[str, ...]

    def _build_gold_merged_metadata_input(
        self,
        *,
        table_path: str,
        table_name: str,
        records: list[GoldRecord],
        schema: DataFrameSchema | None,
    ) -> GoldMetadataInput:
        from bioetl.domain.ports import GoldMetadataInput

        return GoldMetadataInput(
            table_path=table_path,
            table_name=table_name,
            records=records,
            mode=GoldWriteMode.OVERWRITE,
            completed_at=self._extract_completed_at(records[0]),
            transform_version=self._transform_version,
            transform_steps=self._transform_steps,
            total_bytes=0,
            partition_count=0,
            schema_validation_enabled=schema is not None,
            schema_validation_strict=True if schema is not None else None,
        )

    @staticmethod
    def _extract_completed_at(first_record: GoldRecord) -> datetime | None:
        completed_at_raw = first_record.get("_lineage_created_at") or first_record.get(
            "_ingestion_ts"
        )
        if isinstance(completed_at_raw, str):
            return datetime.fromisoformat(completed_at_raw)
        if isinstance(completed_at_raw, datetime):
            return completed_at_raw
        return None


class _GoldWriterMetadataPayloadMixin:
    _metadata_coordinator: MetadataCoordinatorPort | None
    _transform_version: str | None
    _transform_steps: tuple[str, ...]

    def _resolve_provider_entity(self, table_name: str) -> tuple[str, str]:
        from bioetl.infrastructure.storage.metadata_builder import _parse_table_name

        return _parse_table_name(table_name)

    def _create_gold_metadata_payload(
        self,
        *,
        table_path: str,
        table_name: str,
        records: list[GoldRecord],
        mode: GoldWriteMode,
        scd_config: ScdConfig | None,
        ingestion_ts: datetime | None,
        run_id: RunID | None,
        silver_refs: list[SilverWriteResult] | None = None,
        gold_schema: object | None = None,
    ) -> GoldMetadata:
        if self._metadata_coordinator is not None:
            return self._create_gold_metadata_via_coordinator(
                table_path=table_path,
                table_name=table_name,
                records=records,
                mode=mode,
                scd_config=scd_config,
                ingestion_ts=ingestion_ts,
                silver_refs=silver_refs,
                gold_schema=gold_schema,
            )
        return self._create_gold_metadata_via_fallback(
            table_name=table_name,
            records=records,
            mode=mode,
            scd_config=scd_config,
            ingestion_ts=ingestion_ts,
            run_id=run_id,
            gold_schema=gold_schema,
        )

    def _create_gold_metadata_via_coordinator(
        self,
        *,
        table_path: str,
        table_name: str,
        records: list[GoldRecord],
        mode: GoldWriteMode,
        scd_config: ScdConfig | None,
        ingestion_ts: datetime | None,
        silver_refs: list[SilverWriteResult] | None,
        gold_schema: object | None,
    ) -> GoldMetadata:
        from bioetl.domain.ports import GoldMetadataInput, SilverRef

        converted_refs = (
            [
                SilverRef(
                    table_name=ref.table_name,
                    table_path=ref.table_path,
                    delta_version=ref.delta_version,
                )
                for ref in silver_refs
            ]
            if silver_refs
            else None
        )
        gold_input = GoldMetadataInput(
            table_path=table_path,
            table_name=table_name,
            records=records,
            mode=mode,
            scd_config=scd_config,
            completed_at=ingestion_ts,
            silver_refs=converted_refs,
            transform_version=self._transform_version,
            transform_steps=self._transform_steps,
            gold_schema=gold_schema,
        )
        assert self._metadata_coordinator is not None
        return self._metadata_coordinator.create_gold_metadata(gold_input)

    def _create_gold_metadata_via_fallback(
        self,
        *,
        table_name: str,
        records: list[GoldRecord],
        mode: GoldWriteMode,
        scd_config: ScdConfig | None,
        ingestion_ts: datetime | None,
        run_id: RunID | None,
        gold_schema: object | None,
    ) -> GoldMetadata:
        from bioetl.infrastructure.storage.metadata_builder import GoldMetadataBuilder

        builder = GoldMetadataBuilder(
            transform_version=self._transform_version,
            transform_steps=self._transform_steps,
        )
        return builder.build_fallback_metadata(
            table_name=table_name,
            records=records,
            mode=mode,
            scd_config=scd_config,
            ingestion_ts=ingestion_ts,
            run_id=run_id,
            gold_schema=gold_schema,
        )


class GoldWriterMetadataMixin(
    _GoldWriterMetadataPayloadMixin,
    _GoldWriterMergedMetadataInputMixin,
):
    logger: LoggerPort
    _audit: AuditPort | None
    _metadata_coordinator: MetadataCoordinatorPort | None
    _metadata_writer: MetadataWriterPort
    _flat_structure: bool
    _transform_version: str | None
    _transform_steps: tuple[str, ...]
    _load_gold_writer_module: Callable[[], ModuleType]
    _run_in_executor: Callable[..., Awaitable[object]]

    async def _log_gold_audit(
        self,
        table_name: str,
        records: list[GoldRecord],
        mode: GoldWriteMode,
        ingestion_ts: datetime | None,
        run_id: RunID | None,
    ) -> None:
        audit_entry = _build_gold_audit_entry(
            self,
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
        module = self._load_gold_writer_module()

        try:
            dt = await self._run_in_executor(lambda: module.DeltaTable(table_path))
            version_fn = getattr(dt, "version", None)
            if not callable(version_fn):
                return None
            version_value = version_fn()
            if isinstance(version_value, int):
                return version_value
            if isinstance(version_value, str) and version_value.strip().isdigit():
                return int(version_value.strip())
            return None
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
        if not records:
            return
        prepared = _prepare_gold_metadata_write(
            self,
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
        await _persist_gold_metadata_write(self, prepared)

    async def _write_gold_metadata_file(
        self,
        *,
        table_path: str,
        metadata: GoldMetadata,
        table_name: str,
        provider_name: str,
        entity_name: str,
    ) -> None:
        await self._metadata_writer.write_gold_metadata(
            table_path,
            metadata,
            table_name=table_name,
            flat_structure=self._flat_structure,
            provider=provider_name,
            entity=entity_name,
        )

    async def _write_gold_merged_metadata(
        self,
        table_path: str,
        table_name: str,
        records: list[GoldRecord],
        schema: DataFrameSchema | None = None,
    ) -> None:
        prepared = _maybe_prepare_gold_merged_metadata_write(
            self,
            _GoldMergedMetadataWriteRequest(
                table_path=table_path,
                table_name=table_name,
                records=records,
                schema=schema,
            ),
        )
        if prepared is None:
            return
        await _persist_gold_metadata_write(self, prepared)


__all__ = ["GoldWriterMetadataMixin"]
