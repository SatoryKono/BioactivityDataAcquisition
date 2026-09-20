# Host attrs/methods provided by concrete composition (PD2 W1).
"""Support helpers for CompositePipelineRunner."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any, cast

from bioetl.application.composite.checkpoint import CompositeCheckpointService
from bioetl.application.composite.fsm_helper import FSMStateHelperService
from bioetl.application.composite.lifecycle_observer_service import (
    CompositeLifecycleObserverService,
)
from bioetl.application.composite.preflight_validator import (
    CompositePreflightValidationService,
)
from bioetl.application.composite.runner_pkg.runner_observability_mixin import (
    CompositeRunnerObservabilityMixin,
)
from bioetl.application.composite.runner_pkg.runner_support_result_mixin import (
    _CompositeRunnerSupportResultMixin,
)
from bioetl.application.composite.runner_pkg.runner_support_run_mixin import (
    _CompositeRunnerSupportRunMixin,
)
from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.domain.composite import CompositeConfig
from bioetl.domain.ports import (
    ClockPort,
    ExecutionMetricsRunnerPort,
    LoggerPort,
    MetricsPort,
    TracingPort,
)

__all__ = ["CompositeRunnerSupportMixin"]


class CompositeRunnerSupportMixin(
    _CompositeRunnerSupportResultMixin,
    _CompositeRunnerSupportRunMixin,
    CompositeRunnerObservabilityMixin,
):
    """Support helpers composed with observability (ARCH-REF-R2 / #7729)."""

    _config: CompositeConfig = cast(Any, None)  # Any: host attr default (PD3)
    _runtime: CompositeRuntimeConfig = cast(Any, None)  # Any: host attr default (PD3)
    _seed_runner_factory: Callable[[], ExecutionMetricsRunnerPort] = cast(
        Any, None
    )  # Any: host attr default (PD3)
    _checkpoint_manager: CompositeCheckpointService = cast(
        Any, None
    )  # Any: host attr default (PD3)
    _logger: LoggerPort = cast(Any, None)  # Any: host attr default (PD3)
    _metrics: MetricsPort | None = cast(Any, None)  # Any: host attr default (PD3)
    _tracing: TracingPort | None = cast(Any, None)  # Any: host attr default (PD3)
    _observer: CompositeLifecycleObserverService = cast(
        Any, None
    )  # Any: host attr default (PD3)
    _run_id_str: str = cast(Any, None)  # Any: host attr default (PD3)
    _clock: ClockPort | None = cast(Any, None)  # Any: host attr default (PD3)
    _start_time: float | None = cast(Any, None)  # Any: host attr default (PD3)
    _started_at: datetime | None = cast(Any, None)  # Any: host attr default (PD3)
    _original_run_id: str | None = cast(Any, None)  # Any: host attr default (PD3)
    _preflight_validator: CompositePreflightValidationService | None = cast(
        Any, None
    )  # Any: host attr default (PD3)
    _fsm: FSMStateHelperService = cast(Any, None)  # Any: host attr default (PD3)
