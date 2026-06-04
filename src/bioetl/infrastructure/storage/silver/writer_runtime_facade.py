"""Canonical SilverWriter runtime method facade.

This module owns writer-level orchestration methods that remain part of the
SilverWriter runtime contract while concrete work is delegated to operation
services.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, cast

from bioetl.domain.ports import SilverWriteRequest
from bioetl.domain.types import BronzeRecord
from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.silver.delta_helpers import _DeltaWriteRequest
from bioetl.infrastructure.storage.silver.pipeline_helpers import (
    _SilverWriteExecutionContext,
    _SilverWriteInvocation,
    execute_silver_write_pipeline,
    execute_silver_write_with_tracing,
)
from bioetl.infrastructure.storage.silver.validation_operations import (
    _PreparedSilverWritePayload,
)
from bioetl.infrastructure.storage.silver.writer_metadata_facade import (
    SilverWriterMetadataFacade,
)
from bioetl.infrastructure.storage.silver.writer_runtime_invocation import (
    _coerce_silver_write_invocation,
    _validate_single_target_compat,
    _write_merged_metadata_via_operations,
    _write_single_target_with_historical_trace,
)
from bioetl.infrastructure.storage.silver.writer_runtime_support import (
    _SilverWriterDispatchHost,
    _write_dual_targets,
)
from bioetl.infrastructure.storage.silver.writer_runtime_validation_facade import (
    _SilverWriterRuntimeValidationFacade,
)

if TYPE_CHECKING:
    from bioetl.infrastructure.storage.silver.operations.delta_operations import (
        SilverDeltaOperations,
    )
    from bioetl.infrastructure.storage.silver.operations.merged_operations import (
        SilverMergedOperations,
    )
    from bioetl.infrastructure.storage.silver.operations.postwrite_operations import (
        SilverPostwriteOperations,
    )
    from bioetl.infrastructure.storage.silver.operations.validation_operations import (
        SilverValidationOperations,
    )


class SilverWriterRuntimeFacade(
    SilverWriterMetadataFacade,
    _SilverWriterRuntimeValidationFacade,
):
    """Writer-level Silver orchestration delegated to runtime operation services."""

    _validation: SilverValidationOperations | None
    _delta: SilverDeltaOperations | None
    _postwrite: SilverPostwriteOperations | None
    _merged: SilverMergedOperations | None
    _host: object | None

    if TYPE_CHECKING:

        def _resolve_table_path(self, table_name: str) -> str: ...

        def _should_dual_write(self) -> bool: ...

    async def _write_single_target(
        self,
        *,
        invocation: _SilverWriteInvocation,
        table_name: str | None = None,
        run_id: object | None = None,
        run_type: object | None = None,
        source_batch_id: object | None = None,
        ingestion_ts: object | None = None,
    ) -> SilverWriteResult | None:
        """Execute one physical Silver write target."""
        _validate_single_target_compat(
            invocation=invocation,
            table_name=table_name,
            run_id=run_id,
            run_type=run_type,
            source_batch_id=source_batch_id,
            ingestion_ts=ingestion_ts,
        )
        return await _write_single_target_with_historical_trace(
            self,
            invocation=invocation,
            execute_with_tracing=execute_silver_write_with_tracing,
        )

    async def _write_dual_targets(
        self,
        *,
        invocation: _SilverWriteInvocation,
    ) -> SilverWriteResult | None:
        """Execute all configured Silver contract-version write targets."""
        return await _write_dual_targets(
            cast(_SilverWriterDispatchHost, self), invocation=invocation
        )

    async def _dispatch_write_with_domain_errors(
        self,
        *,
        table_name: str,
        request: _DeltaWriteRequest,
    ) -> None:
        """Dispatch Delta write through runtime services."""
        if self._delta is None:
            raise RuntimeError("Silver Delta operations are required")
        await self._delta._dispatch_write_with_domain_errors(
            table_name=table_name,
            request=request,
        )

    async def _complete_silver_write_pipeline(
        self,
        *,
        ctx: _SilverWriteExecutionContext,
        payload: _PreparedSilverWritePayload,
    ) -> SilverWriteResult | None:
        """Run postwrite finalization through runtime services."""
        if self._postwrite is None:
            raise RuntimeError("Silver postwrite operations are required")
        return await self._postwrite._complete_silver_write_pipeline(
            ctx=ctx,
            payload=payload,
        )

    async def _write_silver_merged_metadata(
        self,
        *,
        table_path: str,
        table_name: str,
        records: list[BronzeRecord],
        primary_keys: list[str],
        completed_at: str | datetime | None = None,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
    ) -> None:
        """Write merged Silver metadata through metadata operations."""
        await _write_merged_metadata_via_operations(
            self,
            table_path=table_path,
            table_name=table_name,
            records=records,
            primary_keys=primary_keys,
            completed_at=completed_at,
            run_id=run_id,
            sources_used=sources_used,
        )

    async def write_silver_merged(
        self,
        table_name: str,
        records: list[BronzeRecord],
        primary_keys: list[str] | None = None,
        *,
        schema: object | None = None,
        completed_at: datetime | None = None,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
        preserve_column_order: bool = False,
    ) -> None:
        """Write merged records to Silver through merged runtime operations."""
        if self._merged is None:
            raise RuntimeError("Silver merged operations are required")
        await self._merged.write_silver_merged(
            table_name=table_name,
            records=records,
            primary_keys=primary_keys,
            schema=schema,
            completed_at=completed_at,
            run_id=run_id,
            sources_used=sources_used,
            preserve_column_order=preserve_column_order,
        )

    async def write_silver(
        self,
        request: SilverWriteRequest | str | None = None,
        *args: object,
        **kwargs: object,
    ) -> SilverWriteResult | None:
        """Write normalized records to Silver layer."""
        invocation = _coerce_silver_write_invocation(
            request,
            args=args,
            kwargs=kwargs,
        )
        if self._should_dual_write():
            return await self._write_dual_targets(invocation=invocation)
        return await self._write_single_target(
            invocation=invocation,
            table_name=invocation.table_name,
            run_id=invocation.run_id,
            run_type=invocation.run_type,
            source_batch_id=invocation.source_batch_id,
            ingestion_ts=invocation.ingestion_ts,
        )

    async def _execute_silver_write_pipeline(
        self,
        *,
        invocation: _SilverWriteInvocation,
        ctx: _SilverWriteExecutionContext,
    ) -> SilverWriteResult | None:
        """Orchestrate the Silver write pipeline stages."""
        return await execute_silver_write_pipeline(
            invocation=invocation,
            ctx=ctx,
            prepare_payload=self._prepare_silver_write_payload,
            dispatch_write=self._dispatch_write_with_domain_errors,
            complete_pipeline=self._complete_silver_write_pipeline,
        )
