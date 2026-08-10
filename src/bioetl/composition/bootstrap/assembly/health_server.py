"""Lightweight assembly helpers for health-listener dependencies."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from bioetl.application.observability.control_plane_integrity_metrics import (
    ControlPlaneIntegrityMetricsService,
)
from bioetl.application.observability.control_plane_evidence import (
    ControlPlaneEvidenceService,
)
from bioetl.composition.runtime_builders.config_access import get_settings
from bioetl.domain.ports import (
    CheckpointPort,
    HealthCheckResult,
    HealthMetricsExpositionPort,
    HealthMonitorPort,
    HealthStatePort,
    LineageStorePort,
    MetricsPort,
    RawRunManifestInspectionPort,
    RunLedgerPort,
    RunManifestPort,
    WorkflowManifestPort,
)
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.control_plane.file_artifact_lifecycle_store import (
    FileControlPlaneArtifactLifecycleStore,
)
from bioetl.infrastructure.control_plane.file_lineage_store import FileLineageStore
from bioetl.infrastructure.control_plane.file_run_ledger_store import (
    FileRunLedgerStore,
)
from bioetl.infrastructure.control_plane.file_run_manifest_store import (
    FileRunManifestStore,
)
from bioetl.infrastructure.control_plane.file_workflow_manifest_store import (
    FileWorkflowManifestStore,
)
from bioetl.infrastructure.observability.health_metrics_exposition import (
    HealthMetricsExpositionAdapter,
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
    workflow_manifest_port: WorkflowManifestPort
    metrics_exposition: HealthMetricsExpositionPort
    control_plane_evidence_service: ControlPlaneEvidenceService | None = None
    control_plane_integrity_refresher: ControlPlaneIntegrityMetricsService | None = None
    data_root: Path = Path()


@dataclass(frozen=True, slots=True)
class _ReadOnlyHealthMonitor:
    """Minimal provider-health monitor for read-only dashboard helper backends."""

    metrics: MetricsPort

    def update_from_health_check_result(
        self,
        result: HealthCheckResult,
        logger: object | None = None,
    ) -> HealthStatus:
        _ = logger  # protocol-compatible optional logger for real monitors
        return result.status

    def record_success(self, provider: str) -> HealthStatus:
        _ = provider  # protocol-compatible provider identity
        return HealthStatus.HEALTHY

    def record_error(self, provider: str) -> HealthStatus:
        _ = provider  # protocol-compatible provider identity
        return HealthStatus.DEGRADED

    def get_all_states(self) -> Mapping[str, HealthStatePort]:
        return {}


@dataclass(frozen=True, slots=True)
class _RunManifestPorts:
    manifest_port: RunManifestPort
    ledger_port: RunLedgerPort
    workflow_manifest_port: WorkflowManifestPort
    lineage_port: LineageStorePort


def _create_control_plane_ports(
    metrics: MetricsPort,
    *,
    data_root: Path | None = None,
) -> _RunManifestPorts:
    """Create file-backed read ports without importing full pipeline runtime."""
    settings = get_settings()
    resolved_data_root = data_root if data_root is not None else Path(settings.data_dir)
    output_root = resolved_data_root / "output" / "control"
    return _RunManifestPorts(
        manifest_port=FileRunManifestStore(
            base_path=output_root / "run_manifest",
            metrics=metrics,
        ),
        ledger_port=FileRunLedgerStore(
            base_path=output_root / "run_ledger",
            metrics=metrics,
        ),
        workflow_manifest_port=FileWorkflowManifestStore(
            base_path=output_root / "workflow_manifest",
            metrics=metrics,
        ),
        lineage_port=FileLineageStore(
            base_path=output_root / "lineage",
            metrics=metrics,
        ),
    )


def create_health_server_dependencies(
    *,
    metrics: MetricsPort | None = None,
    checkpoint_port_factory: Callable[[str], CheckpointPort],
    data_root: Path | None = None,
) -> HealthServerDependencies:
    """Build listener dependencies without provider/pipeline factory imports."""
    resolved_metrics = metrics or PrometheusMetrics()
    settings = get_settings()
    resolved_data_root = (
        data_root if data_root is not None else Path(settings.data_dir)
    ).resolve()
    control_plane_ports = _create_control_plane_ports(
        resolved_metrics,
        data_root=resolved_data_root,
    )
    return HealthServerDependencies(
        health_monitor=_ReadOnlyHealthMonitor(metrics=resolved_metrics),
        metrics=resolved_metrics,
        checkpoint_port=checkpoint_port_factory(""),
        run_manifest_port=control_plane_ports.manifest_port,
        run_ledger_port=control_plane_ports.ledger_port,
        workflow_manifest_port=control_plane_ports.workflow_manifest_port,
        control_plane_evidence_service=ControlPlaneEvidenceService(
            ledger_port=control_plane_ports.ledger_port,
            lineage_store=control_plane_ports.lineage_port,
            manifest_inspector=(
                control_plane_ports.manifest_port
                if isinstance(
                    control_plane_ports.manifest_port,
                    RawRunManifestInspectionPort,
                )
                else None
            ),
            lifecycle_planner=FileControlPlaneArtifactLifecycleStore(
                base_path=resolved_data_root / "output" / "control",
                metrics=resolved_metrics,
            ),
        ),
        control_plane_integrity_refresher=ControlPlaneIntegrityMetricsService(
            manifest_port=control_plane_ports.manifest_port,
            ledger_port=control_plane_ports.ledger_port,
            metrics=resolved_metrics,
        ),
        metrics_exposition=HealthMetricsExpositionAdapter(),
        data_root=resolved_data_root,
    )
