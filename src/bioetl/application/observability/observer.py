# Host attrs/methods provided by concrete composition.
"""Pipeline Observer Context Manager.

Implements R12/R13: Observability wrapper for pipeline execution.
Handles:
- Distributed Tracing (Span creation)
- Metrics (Counter/Histogram)
- Logging (Structured logs with lifecycle context)

Unified Observability Pattern:
- All lifecycle events are emitted through this single observer
- Services use emit_event() to log structured events with metrics
- This eliminates duplicate logging across runner/preflight/postrun
"""

from __future__ import annotations

__all__ = ["LifecyclePhase", "PipelineObserver", "PipelineObserverParams"]

import time
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from bioetl.application.observability.observer_context_mixin import (
    _ObserverContextManagerMixin,
)
from bioetl.application.observability.observer_contract import (
    LifecyclePhase,
)
from bioetl.application.observability.observer_health_mixin import (
    _ObserverHealthEmissionMixin,
)
from bioetl.application.observability.observer_postrun_mixin import (
    _ObserverPostrunEmissionMixin,
)
from bioetl.domain.events import PipelineEvent
from bioetl.domain.runtime_observability_publication_contract import (
    CANONICAL_DOMAIN_EVENT_EMITTER,
    CANONICAL_LIFECYCLE_EMITTER,
)
from bioetl.domain.types import RunID, RunType

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.domain.aggregates.events import DomainEvent
    from bioetl.domain.ports import ClockPort, LoggerPort, MetricsPort, TracingPort

    class _ObserverEventMixinBase:
        """Typing-only stand-in for skipped observer event mixin imports."""

        @staticmethod
        def _normalize_severity(level: str) -> str: ...

        def _emit_contract_event(
            self,
            event_name: str,
            *,
            severity: str,
            **context: Any,  # Any: event payload keys vary across lifecycle/domain emissions
        ) -> None: ...

else:
    from bioetl.application.observability.observer_event_mixin import (
        _ObserverEventMixin as _ObserverEventMixinBase,
    )

PROBE_MODE_FALLBACK_COUNTER = "bioetl_probe_mode_fallback_total"


@dataclass(frozen=True, slots=True)
class PipelineObserverParams:
    """Identity bag for :class:`PipelineObserver` (ARCH-CONT-04 / #6760)."""

    pipeline_name: str
    run_id: RunID
    run_type: RunType
    manifest_id: str | None = None
    entity: str | None = None
    effective_config_hash: str | None = None
    contract_ref: str | None = None
    contract_version: str | None = None
    composite_run_id: str | None = None


class _ObserverLifecycleEmissionMixin(
    _ObserverHealthEmissionMixin,
    _ObserverPostrunEmissionMixin,
    _ObserverEventMixinBase,
):
    """Structured lifecycle/domain event emission helpers."""

    CANONICAL_LIFECYCLE_EMITTER = CANONICAL_LIFECYCLE_EMITTER
    CANONICAL_DOMAIN_EVENT_EMITTER = CANONICAL_DOMAIN_EVENT_EMITTER
    span: Span | None = None  # Any: host attr default  # Any: host attr default (PD6)
    pipeline_name: str
    _metrics: MetricsPort
    _completed_stage_count: int = 0

    @staticmethod
    def _resolve_domain_event_phase(
        phase_hint: str | None,
        *,
        fallback: LifecyclePhase | None,
    ) -> LifecyclePhase:
        """Resolve domain-event phase hints into canonical lifecycle phases."""
        if fallback is not None:
            return fallback
        if phase_hint is not None:
            try:
                return LifecyclePhase(phase_hint)
            except ValueError:
                pass
        return LifecyclePhase.EXECUTION

    def emit_domain_event(
        self,
        event: DomainEvent,
        *,
        phase: LifecyclePhase | None = None,
    ) -> None:
        """Emit one typed domain event through the runtime observability contract."""
        from bioetl.domain.observability_event_mapping import (
            map_domain_event_to_observability_event,
        )

        envelope = map_domain_event_to_observability_event(event)
        resolved_phase = self._resolve_domain_event_phase(
            envelope.phase_hint,
            fallback=phase,
        )
        self.emit_event(
            envelope.event_name,
            resolved_phase,
            level=envelope.severity,
            event_family=envelope.event_family,
            occurred_at=event.occurred_at.isoformat(),
            **envelope.context,
        )

    def emit_event(
        self,
        event_name: str,
        phase: LifecyclePhase,
        level: str = "info",
        **extra: Any,  # Any: structlog-compatible context kwargs
    ) -> None:
        """Emit a structured lifecycle event through unified observability.

        This is the single source of truth for lifecycle events.
        All events are logged with consistent context and optionally traced.

        Args:
            event_name: Event identifier (e.g., "preflight_started").
            phase: Current lifecycle phase.
            level: Log level ("debug", "info", "warning", "error").
            **extra: Additional context for the event.
        """
        severity = self._normalize_severity(level)
        self._emit_contract_event(
            event_name,
            severity=severity,
            phase=phase.value,
            **extra,
        )

        # Add span event if tracing is active
        if self.span:
            try:
                self.span.set_attribute(f"bioetl.{event_name}", True)
            except (AttributeError, RuntimeError, TypeError, ValueError):
                pass  # Best effort

    def emit_phase_started(
        self,
        phase: LifecyclePhase,
        **extra: Any,  # Any: structlog-compatible context kwargs
    ) -> float:
        """Emit phase start event and return start timestamp.

        Args:
            phase: Lifecycle phase starting.
            **extra: Additional context.

        Returns:
            Start timestamp for duration calculation.
        """
        self.emit_event(PipelineEvent.phase_started(phase.value), phase, **extra)
        return time.monotonic()

    def emit_phase_completed(
        self,
        phase: LifecyclePhase,
        start_time: float,
        success: bool = True,
        **extra: Any,  # Any: structlog-compatible context kwargs
    ) -> None:
        """Emit phase completion event with duration.

        Args:
            phase: Lifecycle phase completed.
            start_time: Timestamp from emit_phase_started().
            success: Whether phase completed successfully.
            **extra: Additional context.
        """
        duration = time.monotonic() - start_time
        status = "success" if success else "failed"

        self.emit_event(
            PipelineEvent.phase_completed(phase.value),
            phase,
            level="info" if success else "error",
            duration_seconds=round(duration, 4),
            status=status,
            **extra,
        )

        if success:
            self._completed_stage_count += 1

        # Record phase duration metric
        self._metrics.observe_histogram(
            "bioetl_phase_duration_seconds",
            duration,
            labels={
                "pipeline": self.pipeline_name,
                "phase": phase.value,
                "status": status,
            },
        )

    @staticmethod
    def _derive_provider_name(pipeline_name: str) -> str:
        """Derive provider name from canonical pipeline naming."""
        if "_" not in pipeline_name:
            return pipeline_name
        provider, _entity = pipeline_name.split("_", 1)
        return provider or pipeline_name

    @staticmethod
    def _derive_entity_name(pipeline_name: str) -> str | None:
        """Derive entity name from canonical pipeline naming."""
        if "_" not in pipeline_name:
            return None
        _provider, entity = pipeline_name.split("_", 1)
        return entity or None


class PipelineObserver(
    _ObserverContextManagerMixin,
    _ObserverLifecycleEmissionMixin,
    AbstractContextManager["PipelineObserver"],
):
    """Observability wrapper for pipeline execution."""

    PROBE_MODE_FALLBACK_COUNTER = PROBE_MODE_FALLBACK_COUNTER

    def __init__(
        self,
        identity: PipelineObserverParams,
        metrics: MetricsPort,
        logger: LoggerPort,
        clock: ClockPort,
        tracer: TracingPort | None = None,
    ) -> None:
        """Initialize observer from an identity bag and explicit collaborators.

        Composition roots must pass :class:`PipelineObserverParams`. Prefer
        :meth:`from_parts` for legacy call sites that still assemble identity
        fields individually (ARCH-CR-06 / #6868).
        """
        self.pipeline_name = identity.pipeline_name
        self.run_id = str(identity.run_id)
        self.run_type = identity.run_type.value
        self.provider_name = self._derive_provider_name(identity.pipeline_name)
        self.manifest_id = identity.manifest_id
        self.entity = identity.entity or self._derive_entity_name(
            identity.pipeline_name
        )
        self.effective_config_hash = identity.effective_config_hash
        self.contract_ref = identity.contract_ref
        self.contract_version = identity.contract_version
        self.composite_run_id = identity.composite_run_id
        self._metrics = metrics
        self._logger = logger
        self._clock = clock
        self._tracer = tracer
        self.start_time: float | None = None
        self.span: Span | None = None
        self._completed_stage_count = 0
        self._terminal_records_processed = 0

    @classmethod
    def from_parts(
        cls,
        *,
        pipeline_name: str,
        run_id: RunID,
        run_type: RunType,
        metrics: MetricsPort,
        logger: LoggerPort,
        clock: ClockPort,
        tracer: TracingPort | None = None,
        manifest_id: str | None = None,
        entity: str | None = None,
        effective_config_hash: str | None = None,
        contract_ref: str | None = None,
        contract_version: str | None = None,
        composite_run_id: str | None = None,
    ) -> PipelineObserver:
        """Compatibility factory for callers that assemble identity fields.

        Prefer constructing :class:`PipelineObserverParams` at composition
        roots; this adapter preserves a bag-compat path without expanding the
        primary constructor arity (ARCH-CR-06 / #6868).
        """
        return cls(
            identity=PipelineObserverParams(
                pipeline_name=pipeline_name,
                run_id=run_id,
                run_type=run_type,
                manifest_id=manifest_id,
                entity=entity,
                effective_config_hash=effective_config_hash,
                contract_ref=contract_ref,
                contract_version=contract_version,
                composite_run_id=composite_run_id,
            ),
            metrics=metrics,
            logger=logger,
            clock=clock,
            tracer=tracer,
        )

    def capture_execution_metrics(
        self,
        metrics_snapshot: dict[str, int],
    ) -> None:
        """Capture final execution metrics for terminal domain-event emission."""
        self._terminal_records_processed = max(
            0,
            metrics_snapshot.get("records_gold", 0),
            metrics_snapshot.get("records_silver", 0),
            metrics_snapshot.get("records_bronze", 0),
            metrics_snapshot.get("records_fetched", 0),
        )
