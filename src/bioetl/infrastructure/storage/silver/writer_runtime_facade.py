"""Canonical SilverWriter runtime method facade.

This module owns writer-level orchestration methods that remain part of the
SilverWriter runtime contract while concrete work is delegated to operation
services.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Literal, cast

import pyarrow as pa

from bioetl.domain.config import KeyNullabilityRule
from bioetl.domain.medallion import SilverWriteMode, WriteMode
from bioetl.domain.ports import SilverWriteRequest, coerce_silver_write_request
from bioetl.domain.types import BronzeRecord
from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.silver.delta_helpers import _DeltaWriteRequest
from bioetl.infrastructure.storage.silver.metadata_operations import (
    _execute_silver_metadata_write,
    _prepare_silver_merged_metadata_write,
    _SilverMetadataWriteHostProtocol,
)
from bioetl.infrastructure.storage.silver.metadata_request_models import (
    _build_silver_merged_metadata_write_request,
)
from bioetl.infrastructure.storage.silver.operations.validation_operations import (
    _prepare_silver_write_payload_impl,
    _SilverPayloadPreparationHostProtocol,
)
from bioetl.infrastructure.storage.silver.pipeline_helpers import (
    _SilverWriteExecutionContext,
    _SilverWriteInvocation,
    execute_silver_write_pipeline,
    execute_silver_write_with_tracing,
)
from bioetl.infrastructure.storage.silver.validation_operations import (
    _PreparedSilverWritePayload,
    _SilverWritePreparationRequest,
    _ValidatedSilverWriteContext,
)
from bioetl.infrastructure.storage.silver.writer_metadata_facade import (
    SilverWriterMetadataFacade,
)
from bioetl.infrastructure.storage.silver.writer_runtime_support import (
    _SilverWriterDispatchHost,
    _write_dual_targets,
    _write_single_target_impl,
)

if TYPE_CHECKING:
    from bioetl.domain.value_objects import silver_result as silver_result_types
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

_SILVER_VALIDATION_OPERATIONS_REQUIRED = (
    "Silver validation operations are required"
)
_SILVER_METADATA_OPERATIONS_REQUIRED = "Silver metadata operations are required"


async def _write_single_target(
    writer: SilverWriterRuntimeFacade,
    *,
    invocation: _SilverWriteInvocation,
) -> silver_result_types.SilverWriteResult | None:
    """Execute one physical Silver write target with the historical trace name."""
    return await _write_single_target_impl(
        cast(_SilverWriterDispatchHost, writer),
        invocation=invocation,
        execute_with_tracing=execute_silver_write_with_tracing,
        module_name="bioetl.infrastructure.storage.silver_writer",
    )


class SilverWriterRuntimeFacade(SilverWriterMetadataFacade):
    """Writer-level Silver orchestration delegated to runtime operation services."""

    _validation: SilverValidationOperations | None
    _delta: SilverDeltaOperations | None
    _postwrite: SilverPostwriteOperations | None
    _merged: SilverMergedOperations | None
    _host: object | None

    if TYPE_CHECKING:

        def _resolve_table_path(self, table_name: str) -> str: ...

        def _should_dual_write(self) -> bool: ...

    def _enforce_write_policy(self, mode: SilverWriteMode, table_name: str) -> None:
        """Delegate Silver write-mode enforcement to the validation service."""
        if self._validation is None:
            raise RuntimeError(_SILVER_VALIDATION_OPERATIONS_REQUIRED)
        self._validation._enforce_write_policy(mode, table_name)

    def _sync_validate_and_build_arrow(
        self,
        request: _SilverWritePreparationRequest,
    ) -> _ValidatedSilverWriteContext:
        """Delegate arrow validation and building to the validation service."""
        if self._validation is None:
            raise RuntimeError(_SILVER_VALIDATION_OPERATIONS_REQUIRED)
        return self._validation._sync_validate_and_build_arrow(request)

    async def _prepare_silver_write_payload(
        self,
        *,
        table_name: str,
        records: list[BronzeRecord],
        primary_keys: list[str],
        schema: pa.Schema,
        mode: str,
        on_schema_mismatch: Literal["error", "evolve", "ignore"],
        column_order: list[str] | None,
        partition_cols: list[str] | None,
        key_nullability_rules: list[KeyNullabilityRule] | None,
    ) -> _PreparedSilverWritePayload:
        """Prepare a validated Silver payload through the validation service."""
        return await _prepare_silver_write_payload_impl(
            cast(_SilverPayloadPreparationHostProtocol, self),
            table_name=table_name,
            records=records,
            primary_keys=primary_keys,
            schema=schema,
            mode=mode,
            on_schema_mismatch=on_schema_mismatch,
            column_order=column_order,
            partition_cols=partition_cols,
            key_nullability_rules=key_nullability_rules,
        )

    def _validate_write_mode(self, mode: str) -> SilverWriteMode:
        """Delegate write mode validation to the validation service."""
        if self._validation is None:
            raise RuntimeError(_SILVER_VALIDATION_OPERATIONS_REQUIRED)
        return self._validation._validate_write_mode(mode)

    def _to_policy_write_mode(self, mode: SilverWriteMode) -> WriteMode:
        """Delegate write mode policy conversion to the validation service."""
        if self._validation is None:
            raise RuntimeError(_SILVER_VALIDATION_OPERATIONS_REQUIRED)
        return self._validation._to_policy_write_mode(mode)

    def _validate_silver_pandera(
        self,
        records: list[BronzeRecord],
        table_name: str,
    ) -> None:
        """Validate Silver records through the validation service."""
        if self._validation is None:
            raise RuntimeError(_SILVER_VALIDATION_OPERATIONS_REQUIRED)
        self._validation._validate_silver_pandera(records, table_name)

    async def _check_schema_drift(
        self,
        table_name: str,
        records: list[BronzeRecord],
        on_schema_mismatch: Literal["error", "evolve", "ignore"],
    ) -> None:
        """Check schema drift through the validation service."""
        if self._validation is None:
            raise RuntimeError(_SILVER_VALIDATION_OPERATIONS_REQUIRED)
        await self._validation._check_schema_drift(
            table_name, records, on_schema_mismatch
        )

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
        if table_name is not None and table_name != invocation.table_name:
            raise TypeError("table_name does not match invocation.table_name")
        if run_id is not None and run_id != invocation.run_id:
            raise TypeError("run_id does not match invocation.run_id")
        if run_type is not None and run_type != invocation.run_type:
            raise TypeError("run_type does not match invocation.run_type")
        if (
            source_batch_id is not None
            and source_batch_id != invocation.source_batch_id
        ):
            raise TypeError("source_batch_id does not match invocation.source_batch_id")
        if ingestion_ts is not None and ingestion_ts != invocation.ingestion_ts:
            raise TypeError("ingestion_ts does not match invocation.ingestion_ts")
        return await _write_single_target(self, invocation=invocation)

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
        if self._metadata is None:
            raise RuntimeError(_SILVER_METADATA_OPERATIONS_REQUIRED)
        resolved_completed_at = (
            datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
            if isinstance(completed_at, str)
            else completed_at
        )
        if self._should_skip_silver_metadata_write(records=records):
            return
        await _execute_silver_metadata_write(
            cast(_SilverMetadataWriteHostProtocol, self),
            request=_build_silver_merged_metadata_write_request(
                table_path=table_path,
                table_name=table_name,
                records=records,
                primary_keys=primary_keys,
                completed_at=resolved_completed_at,
                run_id=run_id,
                sources_used=sources_used,
            ),
            prepare=_prepare_silver_merged_metadata_write,
        )

    async def write_silver_merged(
        self,
        table_name: str,
        records: list[BronzeRecord],
        primary_keys: list[str] | None = None,
        *,
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
        write_request = coerce_silver_write_request(request, args=args, kwargs=kwargs)
        invocation = _SilverWriteInvocation(
            table_name=write_request.table_name,
            records=write_request.records,
            primary_keys=write_request.primary_keys,
            schema=write_request.schema,
            mode=write_request.mode,
            partition_cols=write_request.partition_cols,
            on_schema_mismatch=write_request.on_schema_mismatch,
            column_order=write_request.column_order,
            bronze_refs=write_request.bronze_refs,
            key_nullability_rules=write_request.key_nullability_rules,
            run_id=write_request.run_id,
            run_type=write_request.run_type,
            source_batch_id=write_request.source_batch_id,
            ingestion_ts=write_request.ingestion_ts,
            quarantined_count=write_request.quarantined_count,
            validation_errors=write_request.validation_errors,
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
