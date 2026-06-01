"""Lightweight assembly helpers for health-listener dependencies."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from bioetl.composition.runtime_builders.config_access import get_settings
from bioetl.domain.ports import (
    CheckpointPort,
    HealthCheckResult,
    HealthMonitorPort,
    HealthStatePort,
    MetricsPort,
    RunLedgerPort,
    RunManifestPort,
)
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.control_plane.file_run_ledger_store import (
    FileRunLedgerStore,
)
from bioetl.infrastructure.control_plane.file_run_manifest_store import (
    FileRunManifestStore,
)
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics

__all__ = [
    "HealthServerDependencies",
    "create_health_server_dependencies",
]


@dataclass(frozen=True, slots=True)
class HealthServerDependencies:
    """Dependencies required by the HTTP health server."""

    health_monitor: HealthMonitorPort
    metrics: MetricsPort
    checkpoint_port: CheckpointPort
    run_manifest_port: RunManifestPort
    run_ledger_port: RunLedgerPort


@dataclass(frozen=True, slots=True)
class _ReadOnlyHealthMonitor:
    """Minimal provider-health monitor for read-only dashboard helper backends."""

    metrics: MetricsPort

    def update_from_health_check_result(
        self,
        result: HealthCheckResult,
        logger: object | None = None,
    ) -> HealthStatus:
        return result.status

    def record_success(self, provider: str) -> HealthStatus:
        return HealthStatus.HEALTHY

    def record_error(self, provider: str) -> HealthStatus:
        return HealthStatus.DEGRADED

    def get_all_states(self) -> Mapping[str, HealthStatePort]:
        return {}


@dataclass(frozen=True, slots=True)
class _RunManifestPorts:
    manifest_port: RunManifestPort
    ledger_port: RunLedgerPort


def _create_control_plane_ports(metrics: MetricsPort) -> _RunManifestPorts:
    """Create file-backed read ports without importing full pipeline runtime."""
    settings = get_settings()
    output_root = Path(settings.data_dir) / "output" / "control"
    return _RunManifestPorts(
        manifest_port=FileRunManifestStore(
            base_path=output_root / "run_manifest",
            metrics=metrics,
        ),
        ledger_port=FileRunLedgerStore(
            base_path=output_root / "run_ledger",
            metrics=metrics,
        ),
    )


def create_health_server_dependencies(
    *,
    metrics: MetricsPort | None = None,
    checkpoint_port_factory: Callable[[str], CheckpointPort],
) -> HealthServerDependencies:
    """Build listener dependencies without provider/pipeline factory imports."""
    resolved_metrics = metrics or PrometheusMetrics()
    control_plane_ports = _create_control_plane_ports(resolved_metrics)
    return HealthServerDependencies(
        health_monitor=_ReadOnlyHealthMonitor(metrics=resolved_metrics),
        metrics=resolved_metrics,
        checkpoint_port=checkpoint_port_factory(""),
        run_manifest_port=control_plane_ports.manifest_port,
        run_ledger_port=control_plane_ports.ledger_port,
    )
