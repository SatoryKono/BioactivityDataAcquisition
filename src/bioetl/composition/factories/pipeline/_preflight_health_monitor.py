"""Preflight provider-health monitor wiring for pipeline runner assembly."""

from __future__ import annotations

from bioetl.composition.runtime_builders import control_plane_root
from bioetl.composition.runtime_builders.config_access import get_settings
from bioetl.domain.ports import HealthMonitorPort, MetricsPort
from bioetl.infrastructure.adapters.http.health_monitor import ProviderHealthMonitor
from bioetl.infrastructure.control_plane.file_provider_health_evidence import (
    FileProviderHealthEvidenceStore,
)
from bioetl.infrastructure.control_plane.provider_health_evidence import (
    PersistingProviderHealthMonitor,
    rehydrate_provider_health_evidence,
)


def _provider_health_evidence_store() -> FileProviderHealthEvidenceStore | None:
    """Build the compact CURRENT evidence store, or None when paths are unavailable."""
    try:
        settings = get_settings()
        return FileProviderHealthEvidenceStore(
            base_path=control_plane_root(settings, "provider_health")
        )
    except (OSError, RuntimeError, TypeError, ValueError):
        return None


def build_preflight_health_monitor(metrics: MetricsPort) -> HealthMonitorPort:
    """Wire ProviderHealthMonitor with compact persisted CURRENT evidence."""
    inner = ProviderHealthMonitor(metrics=metrics)
    store = _provider_health_evidence_store()
    if store is None:
        return inner
    return PersistingProviderHealthMonitor(inner=inner, store=store)


def rehydrate_provider_health_gauges(metrics: MetricsPort) -> int:
    """Publish CURRENT provider-health gauges from persisted evidence."""
    store = _provider_health_evidence_store()
    if store is None:
        return 0
    return rehydrate_provider_health_evidence(metrics, store)
