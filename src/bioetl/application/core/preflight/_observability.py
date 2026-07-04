"""Private observer emission helpers owned by the preflight package."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from bioetl.domain.types import HealthStatus

if TYPE_CHECKING:
    from bioetl.domain.types import HealthReport


class _PreflightObservabilityHostProtocol(Protocol):
    _runtime: object
    _observer: object


def emit_preflight_health_results(
    host: _PreflightObservabilityHostProtocol,
    report: HealthReport | None,
    *,
    runner_stage: str,
) -> None:
    """Emit component-level preflight health results through PipelineObserver."""
    if report is None:
        return
    health_check_mode = getattr(host._runtime, "health_check_mode", "strict")
    for result in report.results:
        host._observer.emit_health_check_result(
            component=result.component,
            healthy=result.status != HealthStatus.UNHEALTHY,
            duration_ms=result.duration_seconds * 1000.0,
            provider=result.provider,
            latency_ms=result.latency_ms,
            health_check_mode=health_check_mode,
            fallback_reason=result.probe_fallback_reason,
            health_status=result.status.value,
            runner_stage=runner_stage,
        )
