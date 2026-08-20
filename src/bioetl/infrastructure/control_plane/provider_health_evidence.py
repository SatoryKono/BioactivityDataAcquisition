"""Persist and rehydrate canonical provider-health CURRENT evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bioetl.domain.ports import HealthCheckResult, HealthMonitorPort
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
    "rehydrate_provider_health_evidence",
]


@dataclass(slots=True)
class PersistingProviderHealthMonitor:
    """Delegate to ProviderHealthMonitor and persist compact evidence."""

    inner: HealthMonitorPort
    store: FileProviderHealthEvidenceStore

    def update_from_health_check_result(
        self,
        result: HealthCheckResult,
        logger: LoggerPort | None = None,
    ) -> HealthStatus:
        status = self.inner.update_from_health_check_result(result, logger)
        observed = result.checked_at or datetime.now(UTC)
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
    now: datetime | None = None,
) -> int:
    """Publish CURRENT gauges from persisted evidence without incrementing counters."""
    published = 0
    current = now or datetime.now(UTC)
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
        if record.is_fresh(now=current):
            restore_provider_health_status(
                metrics=metrics,
                provider=record.provider,
                status=record.status,
            )
        published += 1
    return published


def _bounded_endpoint(raw: str) -> str:
    text = (raw or "").strip()
    if len(text) > 128:
        return text[:128]
    return text
