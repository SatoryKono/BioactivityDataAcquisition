"""Async quarantine admin methods for QuarantineService."""

from __future__ import annotations

from time import perf_counter
from typing import TYPE_CHECKING, Protocol

from bioetl.application.observability.tracing_operation_helpers import traced_async_operation
from bioetl.application.services._quarantine_models import QuarantineRecord
from bioetl.application.services._quarantine_service_support import (
    _QUARANTINE_OPERATOR_ERRORS,
)
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.domain.ports import LoggerPort, QuarantinePort, TracingPort


class _QuarantineAsyncHost(Protocol):
    """Structural contract required by async quarantine admin helpers."""

    TRACER_NAME: str
    logger: LoggerPort
    quarantine_port: QuarantinePort
    tracer: TracingPort | None

    def _record_operator_metrics(
        self,
        *,
        operation: str,
        status: str,
        duration_seconds: float,
    ) -> None: ...

    def _trace_attributes(
        self,
        *,
        operation: str,
        pipeline: str | None = None,
        **extra: object,
    ) -> dict[str, object]: ...

    def _set_trace_result(
        self,
        span: Span,
        *,
        success: bool,
        **extra: object,
    ) -> None: ...

    async def _inspect_impl(
        self,
        *,
        pipeline: str,
        limit: int,
        error_code: str | None,
        start_time: float,
    ) -> list[QuarantineRecord]: ...

    async def _get_stats_impl(
        self,
        *,
        pipeline: str,
        error_code: str | None,
        start_time: float,
    ) -> JsonDict: ...


class QuarantineServiceAsyncMixin:
    """Async admin operations for QuarantineService."""

    async def inspect(
        self: _QuarantineAsyncHost,
        pipeline: str,
        limit: int = 100,
        error_code: str | None = None,
    ) -> list[QuarantineRecord]:
        """Inspect quarantined records for a pipeline."""
        start_time = perf_counter()
        if self.tracer is None:
            return await self._inspect_impl(
                pipeline=pipeline,
                limit=limit,
                error_code=error_code,
                start_time=start_time,
            )
        async with traced_async_operation(
            self.tracer,
            "quarantine.inspect",
            self._trace_attributes(
                operation="inspect",
                pipeline=pipeline,
                **{
                    "bioetl.limit": limit,
                    "bioetl.has_error_code_filter": error_code is not None,
                },
            ),
            tracer_name=self.TRACER_NAME,
        ) as span:
            records = await self._inspect_impl(
                pipeline=pipeline,
                limit=limit,
                error_code=error_code,
                start_time=start_time,
            )
            self._set_trace_result(
                span,
                success=True,
                **{"bioetl.record_count": len(records)},
            )
            return records

    async def _inspect_impl(
        self: _QuarantineAsyncHost,
        *,
        pipeline: str,
        limit: int,
        error_code: str | None,
        start_time: float,
    ) -> list[QuarantineRecord]:
        """Implement quarantine inspection without tracing concerns."""
        self.logger.debug(
            "Inspecting quarantine",
            pipeline=pipeline,
            limit=limit,
            error_code=error_code,
        )

        try:
            raw_records = await self.quarantine_port.inspect(
                pipeline=pipeline,
                limit=limit,
                error_code=error_code,
            )
        except _QUARANTINE_OPERATOR_ERRORS:
            self._record_operator_metrics(
                operation="inspect",
                status="failed",
                duration_seconds=perf_counter() - start_time,
            )
            raise

        records = [
            QuarantineRecord(
                error_code=rec.get("error_code"),
                payload=rec.get("payload", {}),
                batch_id=rec.get("bronze_batch_id"),
                pipeline=pipeline,
                ingestion_ts=rec.get("ingestion_ts"),
                metadata=rec.get("metadata", {}),
            )
            for rec in raw_records
        ]

        self.logger.info(
            "Inspected quarantine",
            pipeline=pipeline,
            record_count=len(records),
        )
        self._record_operator_metrics(
            operation="inspect",
            status="success",
            duration_seconds=perf_counter() - start_time,
        )
        return records

    async def get_stats(
        self: _QuarantineAsyncHost,
        pipeline: str,
        error_code: str | None = None,
    ) -> JsonDict:
        """Get statistics about quarantined records."""
        start_time = perf_counter()
        if self.tracer is None:
            return await self._get_stats_impl(
                pipeline=pipeline,
                error_code=error_code,
                start_time=start_time,
            )
        async with traced_async_operation(
            self.tracer,
            "quarantine.stats",
            self._trace_attributes(
                operation="stats",
                pipeline=pipeline,
                **{"bioetl.has_error_code_filter": error_code is not None},
            ),
            tracer_name=self.TRACER_NAME,
        ) as span:
            stats = await self._get_stats_impl(
                pipeline=pipeline,
                error_code=error_code,
                start_time=start_time,
            )
            self._set_trace_result(span, success=True)
            return stats

    async def _get_stats_impl(
        self: _QuarantineAsyncHost,
        *,
        pipeline: str,
        error_code: str | None,
        start_time: float,
    ) -> JsonDict:
        """Implement quarantine statistics lookup without tracing concerns."""
        self.logger.debug("Getting quarantine stats", pipeline=pipeline)

        try:
            stats = await self.quarantine_port.get_stats(pipeline, error_code)
        except _QUARANTINE_OPERATOR_ERRORS:
            self._record_operator_metrics(
                operation="stats",
                status="failed",
                duration_seconds=perf_counter() - start_time,
            )
            raise

        self.logger.info(
            "Got quarantine stats",
            pipeline=pipeline,
            stats=stats,
        )
        self._record_operator_metrics(
            operation="stats",
            status="success",
            duration_seconds=perf_counter() - start_time,
        )
        return stats
