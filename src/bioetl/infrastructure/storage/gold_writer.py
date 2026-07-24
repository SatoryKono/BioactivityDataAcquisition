"""Gold layer writer — RULES.md §2.1.1, REQ-DATA-009/010, REQ-CONTRACT-001."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from deltalake.exceptions import CommitFailedError, TableNotFoundError  # noqa: F401

from bioetl.domain.medallion import GoldWriteMode
from bioetl.domain.ports.noop import _NoOpSpan
from bioetl.domain.types import (
    GoldSchemaPolicyByVersion,
    ScdConfig,
    resolve_gold_contract_version,
)
from bioetl.infrastructure.storage.base_delta_writer import (
    BaseDeltaWriter,
    _clear_delta_tables,
    coerce_null_types_for_delta,  # noqa: F401
)
from bioetl.infrastructure.storage.delta.table_ops import (
    normalize_delta_filesystem_path,
)
from bioetl.infrastructure.storage.gold.io_mixin import GoldWriterIOMixin
from bioetl.infrastructure.storage.gold.metadata_mixin import (
    GoldWriterMetadataMixin,
)
from bioetl.infrastructure.storage.gold.pipeline_helpers import (
    GoldWritePostwriteContext as _GoldWritePostwriteContext,
)
from bioetl.infrastructure.storage.gold.pipeline_helpers import (
    GoldWriteRequest as _GoldWriteRequest,
)
from bioetl.infrastructure.storage.gold.pipeline_helpers import (
    PreparedGoldWriteContext as _PreparedGoldWriteContext,
)
from bioetl.infrastructure.storage.gold.pipeline_helpers import (
    normalize_scd_config as _normalize_scd_config_impl,
)
from bioetl.infrastructure.storage.gold.pipeline_helpers import (
    post_write_gold as _post_write_gold_impl,
)
from bioetl.infrastructure.storage.gold.pipeline_helpers import (
    prepare_gold_write as _prepare_write_gold_impl,
)
from bioetl.infrastructure.storage.gold.pipeline_helpers import (
    set_gold_write_span_attributes as _set_write_span_attributes_impl,
)
from bioetl.infrastructure.storage.gold.validation_mixin import (
    GoldWriterValidationMixin,
)
from bioetl.infrastructure.storage.gold.writer_implementation import (
    _write_dual_targets_impl,
    _write_single_target_impl,
)
from bioetl.infrastructure.storage.gold.writer_request import (
    _build_gold_write_request,
)
from bioetl.infrastructure.storage.gold.writer_runtime import (
    _resolve_runtime_services,
)
from bioetl.infrastructure.storage.gold.writer_schema_helpers import (
    _resolve_active_gold_schema,
)

if TYPE_CHECKING:
    import pyarrow as pa
    from deltalake import DeltaTable as DeltaTableType
    from pandera.polars import DataFrameSchema

    from bioetl.domain.ports import LoggerPort
    from bioetl.domain.types import (
        GoldRecord,
        RunID,
    )
    from bioetl.domain.value_objects.silver_result import SilverWriteResult
    from bioetl.infrastructure.storage.gold.runtime_helpers import (
        GoldWriterRuntimeServices,
    )

__all__ = ["GoldWriteMode", "GoldWriter", "_normalize_scd_config"]


def _normalize_scd_config(
    scd_config: ScdConfig,
    primary_keys: list[str] | None,
) -> ScdConfig:
    """Compatibility wrapper preserving the public helper import path."""
    return _normalize_scd_config_impl(scd_config, primary_keys)


def DeltaTable(
    table_uri: str | Path,
    version: int | None = None,
    storage_options: dict[str, str] | None = None,
    without_files: bool = False,
) -> DeltaTableType:
    """Lazy compatibility seam for tests and Delta write helpers."""
    from deltalake import DeltaTable as _DeltaTable

    return _DeltaTable(
        normalize_delta_filesystem_path(table_uri),
        version=version,
        storage_options=storage_options,
        without_files=without_files,
    )


def write_deltalake(
    table_or_uri: str | Path | DeltaTableType,
    data: pa.Table,
    *,
    partition_by: list[str] | str | None = None,
    mode: Literal["error", "append", "overwrite", "ignore"] = "error",
    schema_mode: Literal["overwrite"] | None = None,
) -> None:
    """Lazy compatibility seam for tests and Delta write helpers."""
    from deltalake import write_deltalake as _write_deltalake

    normalized_table = (
        normalize_delta_filesystem_path(table_or_uri)
        if isinstance(table_or_uri, str | Path)
        else table_or_uri
    )
    _write_deltalake(
        table_or_uri=normalized_table,
        data=data,
        partition_by=partition_by,
        mode=mode,
        schema_mode=schema_mode,
    )


GOLD_WRITE_RETRY_ERRORS = (
    CommitFailedError,
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
    KeyError,
)


class GoldWriter(
    GoldWriterValidationMixin,
    GoldWriterIOMixin,
    GoldWriterMetadataMixin,
    BaseDeltaWriter,
):
    """Gold layer writer: strict Pandera validation, Delta Lake, and SCD2."""

    def _should_dual_write(self) -> bool:
        """Return True when rollout policy requires Gold shadow writes."""
        if self._contract_rollout_policy is None:
            return False
        return (
            self._contract_rollout_policy.mode
            in {
                "dual_write",
                "dual_read_write",
            }
            and len(self._contract_rollout_policy.write_versions) > 1
        )

    def __init__(
        self,
        base_path: str | Path,
        logger: LoggerPort,
        transform_version: str | None = None,
        transform_steps: tuple[str, ...] | None = None,
        runtime_services: GoldWriterRuntimeServices | None = None,
        flat_structure: bool = False,
    ) -> None:
        """Initialize Gold writer with explicit runtime collaborators."""
        super().__init__(base_path, logger, flat_structure=flat_structure)
        services = _resolve_runtime_services(
            runtime_services=runtime_services,
        )
        self.csv_exporter = services.csv_exporter
        self._metrics = services.metrics
        self._audit = services.audit
        self._tracing = services.tracing
        self._metadata_writer = services.metadata_writer
        self._metadata_coordinator = services.metadata_coordinator
        self._lineage_store = services.lineage_store
        self._contract_rollout_policy = services.contract_rollout_policy
        self._transform_version = transform_version
        self._transform_steps = transform_steps or ()

    async def write_gold(
        self,
        table_name: str,
        records: list[GoldRecord],
        schema: object,
        primary_keys: list[str] | None = None,
        mode: str = "overwrite",
        partition_cols: list[str] | None = None,
        scd_config: ScdConfig | None = None,
        *,
        column_order: list[str] | None = None,
        ingestion_ts: datetime | None = None,
        run_id: RunID | None = None,
        silver_refs: list[SilverWriteResult] | None = None,
    ) -> None:
        """Validate and write Gold records, including SCD2 and dual-write flows."""
        span_context = (
            self._tracing.get_tracer(__name__).start_as_current_span("write_gold")
            if self._tracing is not None
            else _NoOpSpan()
        )
        with span_context as span:
            normalized_scd_config = (
                ScdConfig.from_mapping(scd_config, primary_keys=primary_keys)
                if isinstance(scd_config, dict)
                else scd_config
            )
            active_schema = _resolve_active_gold_schema(schema)
            contract_version = (
                schema.active_version
                if isinstance(schema, GoldSchemaPolicyByVersion)
                else resolve_gold_contract_version(active_schema)
            )
            request = _build_gold_write_request(
                table_name=table_name,
                records=records,
                schema=active_schema,
                primary_keys=primary_keys,
                mode=mode,
                partition_cols=partition_cols,
                scd_config=normalized_scd_config,
                column_order=column_order,
                ingestion_ts=ingestion_ts,
                run_id=run_id,
                silver_refs=silver_refs,
                contract_version=contract_version,
            )
            self._set_write_span_attributes(
                span,
                request.table_name,
                request.mode,
                len(request.records),
            )
            if self._should_dual_write() and isinstance(
                schema,
                GoldSchemaPolicyByVersion,
            ):
                await self._write_dual_targets(request=request, schema_policy=schema)
                return
            await self._write_single_target(request=request)

    async def _write_dual_targets(
        self,
        *,
        request: _GoldWriteRequest,
        schema_policy: GoldSchemaPolicyByVersion,
    ) -> None:
        """Compatibility seam for direct test patching and dual-write orchestration."""
        await _write_dual_targets_impl(
            self,
            request=request,
            schema_policy=schema_policy,
        )

    async def _write_single_target(
        self,
        *,
        request: _GoldWriteRequest,
    ) -> None:
        """Compatibility seam for direct test patching and dual-write orchestration."""
        await _write_single_target_impl(
            self,
            request=request,
        )

    async def clear_gold(self, table_name: str, dry_run: bool = False) -> int:
        """Implement ``GoldStoragePort`` clear for rebuild/backfill paths."""
        return await asyncio.to_thread(
            _clear_delta_tables,
            base_path=Path(str(self.base_path)),
            table_path=Path(self._resolve_table_path(table_name)),
            dry_run=dry_run,
        )

    async def _prepare_write_gold(
        self,
        *,
        table_name: str,
        records: list[GoldRecord],
        mode: str,
        schema: DataFrameSchema,
        scd_config: ScdConfig | None,
        ingestion_ts: datetime | None,
        contract_version: str | None = None,
    ) -> _PreparedGoldWriteContext:
        """Run validation and path resolution before a Gold write."""
        return await _prepare_write_gold_impl(
            self,
            table_name=table_name,
            records=records,
            mode=mode,
            schema=schema,
            scd_config=scd_config,
            ingestion_ts=ingestion_ts,
            contract_version=contract_version,
        )

    async def _post_write_gold(
        self,
        context: _GoldWritePostwriteContext,
    ) -> None:
        await _post_write_gold_impl(self, context)

    @staticmethod
    def _set_write_span_attributes(
        span: Any,  # Any: tracing SDK span protocol is runtime-provided
        table_name: str,
        mode: str,
        record_count: int,
    ) -> None:
        """Set standard tracing attributes for a Gold write span."""
        _set_write_span_attributes_impl(span, table_name, mode, record_count)
