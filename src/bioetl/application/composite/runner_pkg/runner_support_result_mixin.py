# Host attrs/methods provided by concrete composition (PD2 W1).
"""Result-assembly helpers for CompositePipelineRunner."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from bioetl.application.composite.checkpoint import CompositeCheckpointService
from bioetl.application.composite.fsm_helper import FSMStateHelperService
from bioetl.application.composite.lifecycle_observer_service import (
    CompositeLifecycleObserverService,
)
from bioetl.application.composite.preflight_validator import (
    CompositePreflightValidationService,
)
from bioetl.application.composite.runner_pkg.runner_completion_helpers import (
    CompositeResultBuildRequest,
    build_composite_result,
    finalize_composite_result,
    log_composite_completion,
    prepare_composite_result_context,
)
from bioetl.application.composite.runner_pkg.runner_support_flow import (
    build_correlation_log_context,
)
from bioetl.application.composite.runner_pkg.runner_support_policy import (
    build_result_build_request,
)
from bioetl.application.composite.runner_pkg.runner_support_types import (
    _CompositeRunnerSupportHostProtocol,
    _PreparedCompositeResultContext,
)
from bioetl.application.composite.runtime_models import (
    CompositeExecutionContext,
    CompositeRuntimeConfig,
)
from bioetl.domain.composite import CompositeConfig
from bioetl.domain.composite.result import CompositeResult
from bioetl.domain.ports import (
    ClockPort,
    ExecutionMetricsRunnerPort,
    LoggerPort,
    MetricsPort,
    TracingPort,
)

__all__ = ["_CompositeRunnerSupportResultMixin"]


class _CompositeRunnerSupportResultMixin:
    """Correlation context and final result assembly."""

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

    def _build_correlation_log_context(self, **extra: object) -> dict[str, object]:
        """Build a stable correlation envelope for composite critical logs."""
        return dict(build_correlation_log_context(self, **extra))  # pyright: ignore[reportArgumentType]

    def _build_composite_result(
        self: _CompositeRunnerSupportHostProtocol,
        artifacts: CompositeExecutionContext,
    ) -> CompositeResult:
        """Build the final CompositeResult."""
        return build_composite_result(
            request=self._create_result_build_request(artifacts),
            logger=self._logger,
            observer=self._observer,
        )

    def _prepare_composite_result_context(
        self: _CompositeRunnerSupportHostProtocol,
        artifacts: CompositeExecutionContext,
    ) -> _PreparedCompositeResultContext:
        """Resolve completion metadata before final CompositeResult assembly."""
        return prepare_composite_result_context(
            request=self._create_result_build_request(artifacts),
            logger=self._logger,
        )

    def _log_composite_completion(
        self: _CompositeRunnerSupportHostProtocol,
        context: _PreparedCompositeResultContext,
    ) -> None:
        """Emit the canonical completion log payload for composite runs."""
        log_composite_completion(
            request=self._create_result_build_request(context.artifacts),
            context=context,
            observer=self._observer,
        )

    def _finalize_composite_result(
        self: _CompositeRunnerSupportHostProtocol,
        context: _PreparedCompositeResultContext,
    ) -> CompositeResult:
        """Assemble the final CompositeResult from the prepared completion context."""
        return finalize_composite_result(
            request=self._create_result_build_request(context.artifacts),
            context=context,
        )

    def _create_result_build_request(
        self: _CompositeRunnerSupportHostProtocol,
        artifacts: CompositeExecutionContext,
    ) -> CompositeResultBuildRequest:
        """Build an explicit result-assembly request for completion helpers."""
        return build_result_build_request(
            artifacts=artifacts,
            composite_name=self._config.name,
            run_id=self._run_id_str,
            start_time=self._start_time,
            started_at=self._started_at,
            original_run_id=self._original_run_id,
            required_enrichers=self._config.required_enrichers,
            required_dependencies=self._config.required_dependencies,
        )
