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
)


def build_preflight_health_monitor(metrics: MetricsPort) -> HealthMonitorPort:
    """Wire ProviderHealthMonitor with compact persisted CURRENT evidence."""
    inner = ProviderHealthMonitor(metrics=metrics)
    try:
        settings = get_settings()
        store = FileProviderHealthEvidenceStore(
            base_path=control_plane_root(settings, "provider_health")
        )
    except (OSError, RuntimeError, TypeError, ValueError):
        return inner
    return PersistingProviderHealthMonitor(inner=inner, store=store)
