"""Pure normalization helpers for preflight health aggregation."""

from __future__ import annotations

from bioetl.domain.types import ComponentHealthResult, HealthStatus


def build_component_result(
    *,
    component: str,
    status: HealthStatus,
    duration_seconds: float,
    error_message: str | None = None,
    provider: str | None = None,
    latency_ms: float | None = None,
    probe_fallback_reason: str | None = None,
) -> ComponentHealthResult:
    """Create a component health result with shared field wiring."""
    return ComponentHealthResult(
        component=component,
        status=status,
        duration_seconds=duration_seconds,
        error_message=error_message,
        provider=provider,
        latency_ms=latency_ms,
        probe_fallback_reason=probe_fallback_reason,
    )

def build_parallel_exception_result(exception: BaseException) -> ComponentHealthResult:
    """Convert gather exceptions into synthetic unhealthy component results."""
    return build_component_result(
        component="unknown",
        status=HealthStatus.UNHEALTHY,
        duration_seconds=0.0,
        error_message=str(exception),
    )

def normalize_data_source_status(
    *,
    health_check_mode: str,
    status: HealthStatus,
) -> HealthStatus:
    """Downgrade data-source UNHEALTHY to DEGRADED in probe mode."""
    if health_check_mode == "probe" and status == HealthStatus.UNHEALTHY:
        return HealthStatus.DEGRADED
    return status

def normalize_data_source_error(
    *,
    health_check_mode: str,
    status: HealthStatus,
    error_message: str | None,
) -> str | None:
    """Attach deterministic probe fallback marker when UNHEALTHY is downgraded."""
    if health_check_mode != "probe" or status != HealthStatus.UNHEALTHY:
        return error_message
    detail = error_message or "data_source reported UNHEALTHY in health probe"
    return f"probe_mode_fallback: {detail}"

def resolve_probe_fallback_reason(
    *,
    health_check_mode: str,
    status: HealthStatus,
) -> str | None:
    """Return the fallback reason for probe-mode status downgrades."""
    if health_check_mode == "probe" and status == HealthStatus.UNHEALTHY:
        return "status_downgrade"
    return None

def build_data_source_exception_result(
    *,
    health_check_mode: str,
    duration_seconds: float,
    exception_message: str,
) -> ComponentHealthResult:
    """Convert data-source health exceptions into normalized component results."""
    probe_mode = health_check_mode == "probe"
    return build_component_result(
        component="data_source",
        status=HealthStatus.DEGRADED if probe_mode else HealthStatus.UNHEALTHY,
        duration_seconds=duration_seconds,
        error_message=(
            f"probe_mode_fallback: {exception_message}"
            if probe_mode
            else exception_message
        ),
        probe_fallback_reason="exception" if probe_mode else None,
    )

__all__ = [
    "build_component_result",
    "build_data_source_exception_result",
    "build_parallel_exception_result",
    "normalize_data_source_error",
    "normalize_data_source_status",
    "resolve_probe_fallback_reason",
]
