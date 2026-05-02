"""Canonical SilverWriter runtime method facade.

This module owns writer-level orchestration methods that remain part of the
SilverWriter runtime contract while concrete work is delegated to operation
services.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Literal

import pyarrow as pa

from bioetl.domain.config import KeyNullabilityRule
from bioetl.domain.medallion import SilverWriteMode, WriteMode
from bioetl.domain.ports import SilverWriteRequest, coerce_silver_write_request
from bioetl.domain.types import BronzeRecord
from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.silver.delta_helpers import _DeltaWriteRequest
from bioetl.infrastructure.storage.silver.operations.validation_operations import (
    _prepare_silver_write_payload_impl,
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
    _write_dual_targets,
    _write_single_target_impl,
)

if TYPE_CHECKING:
    from bioetl.domain.value_objects import silver_result as silver_result_types


async def _write_single_target(
    writer: SilverWriterRuntimeFacade,
    *,
    invocation: _SilverWriteInvocation,
) -> silver_result_types.SilverWriteResult | None:
    """Execute one physical Silver write target with the historical trace name."""
    return await _write_single_target_impl(
        writer,
        invocation=invocation,
        execute_with_tracing=execute_silver_write_with_tracing,
        module_name="bioetl.infrastructure.storage.silver_writer",
    )


class SilverWriterRuntimeFacade(SilverWriterMetadataFacade):
    """Writer-level Silver orchestration delegated to runtime operation services."""

    def _enforce_write_policy(self, mode: SilverWriteMode, table_name: str) -> None:
        """Delegate Silver write-mode enforcement to the validation service."""
        if self._validation is None:
            raise RuntimeError("Silver validation operations are required")
        self._validation._enforce_write_policy(mode, table_name)

    def _sync_validate_and_build_arrow(
        self,
        request: _SilverWritePreparationRequest,
    ) -> _ValidatedSilverWriteContext:
        """Delegate arrow validation and building to the validation service."""
        if self._validation is None:
            raise RuntimeError("Silver validation operations are required")
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
            self,
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
            raise RuntimeError("Silver validation operations are required")
        return self._validation._validate_write_mode(mode)

    def _to_policy_write_mode(self, mode: SilverWriteMode) -> WriteMode:
        """Delegate write mode policy conversion to the validation service."""
        if self._validation is None:
            raise RuntimeError("Silver validation operations are required")
        return self._validation._to_policy_write_mode(mode)

    def _validate_silver_pandera(
        self,
        records: list[BronzeRecord],
        table_name: str,
    ) -> None:
        """Validate Silver records through the validation service."""
        if self._validation is None:
            raise RuntimeError("Silver validation operations are required")
        self._validation._validate_silver_pandera(records, table_name)

    async def _check_schema_drift(
        self,
        table_name: str,
        records: list[BronzeRecord],
        on_schema_mismatch: Literal["error", "evolve", "ignore"],
    ) -> None:
        """Check schema drift through the validation service."""
        if self._validation is None:
            raise RuntimeError("Silver validation operations are required")
        await self._validation._check_schema_drift(
            table_name, records, on_schema_mismatch
        )

    async def _write_single_target(
        self,
        *,
        invocation: _SilverWriteInvocation,
    ) -> SilverWriteResult | None:
        """Execute one physical Silver write target."""
        return await _write_single_target(self, invocation=invocation)

    async def _write_dual_targets(
        self,
        *,
        invocation: _SilverWriteInvocation,
    ) -> SilverWriteResult | None:
        """Execute all configured Silver contract-version write targets."""
        return await _write_dual_targets(self, invocation=invocation)

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
            raise RuntimeError("Silver metadata operations are required")
        resolved_completed_at = (
            datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
            if isinstance(completed_at, str)
            else completed_at
        )
        await self._metadata._write_silver_merged_metadata(
            table_path=table_path,
            table_name=table_name,
            records=records,
            primary_keys=primary_keys,
            completed_at=resolved_completed_at,
            run_id=run_id,
            sources_used=sources_used,
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
        return await self._write_single_target(invocation=invocation)

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
