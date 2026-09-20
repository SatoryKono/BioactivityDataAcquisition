# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Health-check emission helpers for the pipeline observer."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast

from bioetl.application.observability.observer_contract import LifecyclePhase
from bioetl.domain.events import PipelineEvent
from bioetl.domain.types import HealthStatus

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort


class _ObserverHealthEmissionMixin:
    """Health-check and preflight emission helpers for the pipeline observer."""

    pipeline_name: str = cast(Any, None)  # Any: host attr default (PD6)
    _metrics: MetricsPort = cast(Any, None)  # Any: host attr default (PD6)
    PROBE_MODE_FALLBACK_COUNTER = "bioetl_probe_mode_fallback_total"
    emit_event: Callable[..., None] = cast(Any, None)  # Any: host attr default (PD6)

    def emit_health_check_result(
        self,
        component: str,
        healthy: bool,
        duration_ms: float | None = None,
        *,
        provider: str | None = None,
        latency_ms: float | None = None,
        health_check_mode: str | None = None,
        fallback_reason: str | None = None,
        health_status: str | HealthStatus | None = None,
        **extra: Any,  # Any: observer events forward arbitrary structured diagnostics to emit_event.
    ) -> None:
        """Emit health check result for a component."""
        resolved_status = self._resolve_health_status(
            health_status=health_status,
            healthy=healthy,
        )
        self.emit_event(
            PipelineEvent.HEALTH_CHECK_COMPLETED,
            LifecyclePhase.PREFLIGHT,
            level="info" if healthy else "warning",
            component=component,
            healthy=healthy,
            duration_ms=duration_ms,
            health_status=resolved_status.value,
            provider=provider,
            health_check_mode=health_check_mode,
            fallback_reason=fallback_reason,
            **extra,
        )

        self._metrics.set_gauge(
            "bioetl_pipeline_health_check_passed",
            1.0 if healthy else 0.0,
            {"pipeline": self.pipeline_name, "component": component},
        )
        metric_value = float(resolved_status.to_metric_value())
        self._metrics.set_gauge(
            "bioetl_health_check_status",
            metric_value,
            {"component": component},
        )
        self._emit_provider_health_gauge(
            provider=provider,
            metric_value=metric_value,
            fallback_reason=fallback_reason,
        )
        self._emit_mode_health_gauge(
            health_check_mode=health_check_mode,
            metric_value=metric_value,
            component=component,
        )
        self._observe_health_latency(
            provider=provider,
            health_check_mode=health_check_mode,
            latency_ms=latency_ms,
            duration_ms=duration_ms,
        )
        self._increment_probe_fallback_counter(
            fallback_reason=fallback_reason,
            component=component,
        )

    def _emit_provider_health_gauge(
        self,
        *,
        provider: str | None,
        metric_value: float,
        fallback_reason: str | None,
    ) -> None:
        """Emit the provider health gauge unless the fallback is excluded."""
        if (
            provider is not None
            and fallback_reason != "cached_bronze_api_not_exercised"
        ):
            self._metrics.set_gauge(
                "bioetl_provider_health_status",
                metric_value,
                {"provider": provider},
            )

    def _emit_mode_health_gauge(
        self,
        *,
        health_check_mode: str | None,
        metric_value: float,
        component: str,
    ) -> None:
        """Emit the health-check mode gauge when a mode is reported."""
        if health_check_mode is not None:
            self._metrics.set_gauge(
                "bioetl_health_check_mode_status",
                metric_value,
                {"component": component, "mode": health_check_mode},
            )

    def _observe_health_latency(
        self,
        *,
        provider: str | None,
        health_check_mode: str | None,
        latency_ms: float | None,
        duration_ms: float | None,
    ) -> None:
        """Observe health-check latency histograms when inputs allow."""
        observed_latency_ms = latency_ms if latency_ms is not None else duration_ms
        if provider is not None and observed_latency_ms is not None:
            latency_seconds = observed_latency_ms / 1000.0
            self._metrics.observe_histogram(
                "bioetl_health_check_latency_seconds",
                latency_seconds,
                {"provider": provider},
            )
            if health_check_mode is not None:
                self._metrics.observe_histogram(
                    "bioetl_health_check_mode_latency_seconds",
                    latency_seconds,
                    {"provider": provider, "mode": health_check_mode},
                )

    def _increment_probe_fallback_counter(
        self,
        *,
        fallback_reason: str | None,
        component: str,
    ) -> None:
        """Count probe-mode fallbacks excluding the cached-bronze exemption."""
        if (
            fallback_reason is not None
            and fallback_reason != "cached_bronze_api_not_exercised"
        ):
            self._metrics.increment_counter(
                self.PROBE_MODE_FALLBACK_COUNTER,
                1,
                {
                    "pipeline": self.pipeline_name,
                    "component": component,
                    "reason": fallback_reason,
                },
            )

    def emit_health_check_summary(
        self,
        *,
        validated: bool,
        duration_seconds: float,
        overall_status: str,
        components_checked: int,
        **extra: Any,  # Any: summary emissions allow caller-defined observability payload fragments.
    ) -> None:
        """Emit summary preflight health observability through the observer contract."""
        self.emit_event(
            PipelineEvent.HEALTH_CHECK_SUMMARY_RECORDED,
            LifecyclePhase.PREFLIGHT,
            level="info" if validated else "warning",
            validated=validated,
            overall_status=overall_status,
            components_checked=components_checked,
            duration_seconds=round(duration_seconds, 4),
            **extra,
        )

        self._metrics.set_gauge(
            "bioetl_infrastructure_validated",
            1.0 if validated else 0.0,
            {"pipeline": self.pipeline_name},
        )
        self._metrics.observe_histogram(
            "bioetl_health_check_duration_seconds",
            duration_seconds,
            {"pipeline": self.pipeline_name},
        )

    @staticmethod
    def _resolve_health_status(
        *,
        health_status: str | HealthStatus | None,
        healthy: bool,
    ) -> HealthStatus:
        """Resolve explicit health statuses into the canonical enum."""
        if isinstance(health_status, HealthStatus):
            return health_status
        if isinstance(health_status, str):
            try:
                return HealthStatus(health_status.upper())
            except ValueError:
                pass
        return HealthStatus.HEALTHY if healthy else HealthStatus.UNHEALTHY
