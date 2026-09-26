"""Per-enricher execution collaborators for EnrichmentCoordinatorService."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import polars as pl

from bioetl.application.runtime_timestamps import (
    capture_runtime_timing_anchor,
    derive_completion_timestamp,
)
from bioetl.domain.composite import EnricherConfig
from bioetl.domain.composite.result import EnrichmentResult
from bioetl.domain.ports import ClockPort, ExecutionMetricsRunnerPort, LoggerPort

__all__ = [
    "EnricherExecutionContext",
    "complete_enricher_execution",
    "handle_enricher_execution_error",
    "handle_enricher_timeout",
    "log_enricher_start",
    "run_enricher_with_timeout",
    "start_enricher_execution",
]


@dataclass(frozen=True, slots=True)
class EnricherExecutionContext:
    """Per-enricher execution context shared across policy branches."""

    enricher: EnricherConfig
    records_input: int
    started_at: datetime
    started_monotonic_at: float


class _CoordinatorExecutionHost(Protocol):
    """Minimal host surface required for enricher execution helpers."""

    _logger: LoggerPort
    _clock: ClockPort

    def _build_enricher_result(
        self,
        *,
        enricher: EnricherConfig,
        runner: ExecutionMetricsRunnerPort,
        records_input: int,
        started_at: datetime,
        completed_at: datetime,
        duration: float,
    ) -> EnrichmentResult: ...

    def _build_timeout_result(
        self,
        enricher: EnricherConfig,
        records_input: int,
        started_at: datetime,
        completed_at: datetime,
        duration: float,
    ) -> EnrichmentResult: ...

    def _handle_enricher_error(
        self,
        error: Exception,
        enricher: EnricherConfig,
        records_input: int,
        started_at: datetime,
        completed_at: datetime,
        duration: float,
        *,
        reason_code: str | None = None,
    ) -> EnrichmentResult: ...


def log_enricher_start(
    logger: LoggerPort,
    enricher: EnricherConfig,
    records_input: int,
) -> None:
    """Emit the structured start log for one enricher."""
    logger.info(
        "Starting enricher",
        enricher=enricher.pipeline,
        records_input=records_input,
        timeout_seconds=enricher.timeout_seconds,
    )


def start_enricher_execution(
    host: _CoordinatorExecutionHost,
    enricher: EnricherConfig,
    keys: pl.DataFrame,
) -> EnricherExecutionContext:
    """Create the canonical execution context and start log for one enricher."""
    started_at, started_monotonic_at = capture_runtime_timing_anchor(clock=host._clock)
    execution_context = EnricherExecutionContext(
        enricher=enricher,
        records_input=len(keys),
        started_at=started_at,
        started_monotonic_at=started_monotonic_at,
    )
    log_enricher_start(host._logger, enricher, execution_context.records_input)
    return execution_context


def complete_enricher_execution(
    host: _CoordinatorExecutionHost,
    *,
    execution_context: EnricherExecutionContext,
    runner: ExecutionMetricsRunnerPort,
    completed_at: datetime,
    duration: float,
) -> EnrichmentResult:
    """Map a successful enricher execution into the canonical result shape."""
    return host._build_enricher_result(
        enricher=execution_context.enricher,
        runner=runner,
        records_input=execution_context.records_input,
        started_at=execution_context.started_at,
        completed_at=completed_at,
        duration=duration,
    )


def handle_enricher_timeout(
    host: _CoordinatorExecutionHost,
    execution_context: EnricherExecutionContext,
    error: TimeoutError,
) -> EnrichmentResult:
    """Apply timeout policy, re-raising for required enrichers only."""
    enricher = execution_context.enricher
    completed_at, duration = derive_completion_timestamp(
        started_at=execution_context.started_at,
        started_monotonic=execution_context.started_monotonic_at,
    )
    if enricher.required:
        host._logger.error(
            "Required enricher timed out",
            enricher=enricher.pipeline,
            timeout_seconds=enricher.timeout_seconds,
            duration_seconds=duration,
        )
        raise TimeoutError(
            f"Required enricher timed out: {enricher.pipeline}"
        ) from error
    return host._build_timeout_result(
        enricher,
        execution_context.records_input,
        execution_context.started_at,
        completed_at,
        duration,
    )


def handle_enricher_execution_error(
    host: _CoordinatorExecutionHost,
    error: Exception,
    *,
    execution_context: EnricherExecutionContext,
    reason_code: str | None = None,
) -> EnrichmentResult:
    """Apply canonical error mapping for enricher execution failures."""
    return host._handle_enricher_error(
        error,
        execution_context.enricher,
        execution_context.records_input,
        execution_context.started_at,
        *derive_completion_timestamp(
            started_at=execution_context.started_at,
            started_monotonic=execution_context.started_monotonic_at,
        ),
        reason_code=reason_code,
    )


async def run_enricher_with_timeout(
    *,
    enricher: EnricherConfig,
    keys: pl.DataFrame,
    runner_factory: Callable[[str, pl.DataFrame], ExecutionMetricsRunnerPort],
    started_at: datetime,
    started_monotonic_at: float,
) -> tuple[ExecutionMetricsRunnerPort, datetime, float]:
    """Run one enricher under its configured timeout and capture completion timing."""
    async with asyncio.timeout(enricher.timeout_seconds):
        runner = runner_factory(enricher.pipeline, keys)
        await runner.run()
    completed_at, duration = derive_completion_timestamp(
        started_at=started_at,
        started_monotonic=started_monotonic_at,
    )
    return runner, completed_at, duration
