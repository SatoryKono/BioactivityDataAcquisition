"""Internal support protocol/context types for composite runner."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from bioetl.application.composite.checkpoint import (
    CompositeCheckpointService,
    CompositeCheckpointState,
)
from bioetl.application.composite.fsm_helper import FSMStateHelperService
from bioetl.application.composite.lifecycle_observer_service import (
    CompositeLifecycleObserverService,
)
from bioetl.application.composite.preflight_validator import (
    CompositePreflightValidationService,
)
from bioetl.application.composite.runner_pkg.runner_result_types import (
    CompositeResultBuildContext,
    _PreparedCompositeResultContext,
)
from bioetl.application.composite.runtime_models import (
    CompositeExecutionContext,
    CompositeRuntimeConfig,
)
from bioetl.domain.composite import CompositeConfig, EnricherConfig
from bioetl.domain.composite.result import CompositeResult, EnrichmentResult
from bioetl.domain.ports import (
    ClockPort,
    ExecutionMetricsRunnerPort,
    LoggerPort,
    MetricsPort,
    TracingPort,
)


class _CompositeRunnerSupportHostProtocol(Protocol):
    _config: CompositeConfig
    _runtime: CompositeRuntimeConfig
    _seed_runner_factory: Callable[[], ExecutionMetricsRunnerPort]
    _checkpoint_manager: CompositeCheckpointService
    _logger: LoggerPort
    _metrics: MetricsPort | None
    _tracing: TracingPort | None
    _observer: CompositeLifecycleObserverService
    _run_id_str: str
    _clock: ClockPort | None
    _start_time: float | None
    _started_at: datetime | None
    _original_run_id: str | None
    _preflight_validator: CompositePreflightValidationService | None
    _fsm: FSMStateHelperService

    def _build_correlation_log_context(
        self,
        **extra: object,
    ) -> dict[str, object]: ...

    def _get_preflight_skip_reason(self) -> str | None: ...

    def _should_run_enricher(
        self,
        enricher: EnricherConfig,
        state: CompositeCheckpointState,
    ) -> bool: ...

    def _get_required_enricher_failure(
        self,
        enrichment_results: dict[str, EnrichmentResult],
    ) -> str | None: ...

    def _prepare_preflight_validation_context(
        self,
    ) -> _PreparedPreflightValidationContext | None: ...

    def _prepare_composite_result_context(
        self,
        artifacts: CompositeExecutionContext,
    ) -> _PreparedCompositeResultContext: ...

    def _create_result_build_request(
        self,
        artifacts: CompositeExecutionContext,
    ) -> CompositeResultBuildContext: ...

    def _log_composite_completion(
        self,
        context: _PreparedCompositeResultContext,
    ) -> None: ...

    def _finalize_composite_result(
        self,
        context: _PreparedCompositeResultContext,
    ) -> CompositeResult: ...


@dataclass(frozen=True, slots=True)
class _PreparedPreflightValidationContext:
    """Resolved runtime data for preflight validation execution."""

    validator: CompositePreflightValidationService
    field_count: int
