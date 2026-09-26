"""Persist and rehydrate canonical provider-health CURRENT evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bioetl.domain.ports import ClockPort, HealthCheckResult, HealthMonitorPort
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.http._health_monitor_observability import (
    restore_provider_health_status,
)
from bioetl.infrastructure.control_plane.file_provider_health_evidence import (
    FileProviderHealthEvidenceStore,
    ProviderHealthEvidenceRecord,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import HealthStatePort, LoggerPort, MetricsPort

__all__ = [
    "PersistingProviderHealthMonitor",
    "persist_probe_health_observation",
    "rehydrate_provider_health_evidence",
]

_PROBE_STATUS_VALUES = {"unhealthy": 0, "degraded": 1, "healthy": 2}


@dataclass(slots=True)
class PersistingProviderHealthMonitor:
    """Delegate to ProviderHealthMonitor and persist compact evidence."""

    inner: HealthMonitorPort
    store: FileProviderHealthEvidenceStore
    clock: ClockPort

    def update_from_health_check_result(
        self,
        result: HealthCheckResult,
        logger: LoggerPort | None = None,
    ) -> HealthStatus:
        status = self.inner.update_from_health_check_result(result, logger)
        observed = result.checked_at or self.clock.now()
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=UTC)
        reason = None
        if result.last_error:
            reason = "probe_error"
        self.store.persist(
            ProviderHealthEvidenceRecord(
                provider=result.provider,
                status=status.to_metric_value(),
                observed_at=observed.isoformat(),
                endpoint=_bounded_endpoint(result.endpoint),
                reason=reason,
            )
        )
        return status

    def record_success(self, provider: str) -> HealthStatus:
        return self.inner.record_success(provider)

    def record_error(self, provider: str) -> HealthStatus:
        return self.inner.record_error(provider)

    def get_all_states(self) -> dict[str, HealthStatePort]:
        return dict(self.inner.get_all_states())


def rehydrate_provider_health_evidence(
    metrics: MetricsPort,
    store: FileProviderHealthEvidenceStore,
    *,
    now: datetime,
) -> int:
    """Publish CURRENT gauges from persisted evidence without incrementing counters."""
    published = 0
    current = now
    for record in store.list_all():
        metrics.set_gauge(
            "bioetl_provider_observed_universe",
            1.0,
            {"provider": record.provider},
        )
        observed_unix = record.observed_unix()
        if observed_unix is not None:
            metrics.set_gauge(
                "bioetl_provider_health_observed_timestamp_seconds",
                float(observed_unix),
                {"provider": record.provider},
            )
        # Rehydrate the last valid observation without treating its age as failure.
        if observed_unix is not None and 0 < observed_unix <= current.timestamp():
            restore_provider_health_status(
                metrics=metrics,
                provider=record.provider,
                status=record.status,
            )
        published += 1
    return published


def persist_probe_health_observation(
    *,
    store: FileProviderHealthEvidenceStore,
    metrics: MetricsPort,
    provider: str,
    status_name: str,
    checked_at: datetime | None,
    endpoint: str | None,
    error: str | None,
    now: datetime,
) -> None:
    """Persist one probe result and rehydrate gauges without new counters."""
    status = _PROBE_STATUS_VALUES.get(status_name)
    if status is None or checked_at is None:
        return
    store.persist(
        ProviderHealthEvidenceRecord(
            provider=provider,
            status=status,
            observed_at=checked_at.isoformat(),
            endpoint=_bounded_endpoint(endpoint or ""),
            reason="probe_error" if error else None,
        )
    )
    rehydrate_provider_health_evidence(metrics, store, now=now)


def _bounded_endpoint(raw: str) -> str:
    text = (raw or "").strip()
    if len(text) > 128:
        return text[:128]
    return text
