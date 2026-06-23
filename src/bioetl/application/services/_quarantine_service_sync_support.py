# ruff: noqa: UP049
"""Shared sync helpers for quarantine admin operations."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, Protocol

from bioetl.application.observability.span_helpers import traced_operation

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.domain.ports import LoggerPort, QuarantinePort, TracingPort
    from bioetl.domain.types import JsonDict, QuarantineRecordStatus

__all__ = ["_QuarantineSyncHost", "_run_traced_sync_operation"]


class _QuarantineSyncHost(Protocol):
    """Structural contract required by sync quarantine admin helpers."""

    TRACER_NAME: str
    logger: LoggerPort
    quarantine_port: QuarantinePort
    tracer: TracingPort | None

    def _capture_operator_timing_anchor(self) -> tuple[datetime, float]: ...

    def _derive_operator_completion(
        self,
        *,
        started_at: datetime,
        started_monotonic: float,
    ) -> tuple[datetime, float]: ...

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

    def _mark_as_reprocessed_impl(
        self,
        *,
        records: list[JsonDict],
        started_at: datetime,
        started_monotonic: float,
    ) -> int: ...

    def _update_status_impl(
        self,
        *,
        payload_hash: str,
        new_status: QuarantineRecordStatus,
        started_at: datetime,
        started_monotonic: float,
    ) -> bool: ...

    def _replay_impl(
        self,
        *,
        pipeline: str,
        error_code: str | None,
        max_age_days: int,
        now: datetime,
        started_at: datetime,
        started_monotonic: float,
    ) -> list[JsonDict]: ...

    def _purge_impl(
        self,
        *,
        pipeline: str,
        older_than_days: int,
        now: datetime,
        started_at: datetime,
        started_monotonic: float,
    ) -> int: ...


def _run_traced_sync_operation[_T](
    host: _QuarantineSyncHost,
    *,
    span_name: str,
    operation: str,
    pipeline: str | None,
    trace_attributes: dict[str, object],
    execute: Callable[[datetime, float], _T],
    success_of: Callable[[_T], bool],
    result_extra_of: Callable[[_T], dict[str, object]],
) -> _T:
    """Run one sync quarantine operator with optional tracing."""
    started_at, started_monotonic = host._capture_operator_timing_anchor()
    if host.tracer is None:
        return execute(started_at, started_monotonic)

    with traced_operation(
        host.tracer,
        span_name,
        host._trace_attributes(
            operation=operation,
            pipeline=pipeline,
            **trace_attributes,
        ),
        tracer_name=host.TRACER_NAME,
    ) as span:
        result = execute(started_at, started_monotonic)
        host._set_trace_result(
            span,
            success=success_of(result),
            **result_extra_of(result),
        )
        return result
