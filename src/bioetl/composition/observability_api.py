"""Canonical public observability composition API.

This module is the sanctioned public seam for observability-related runtime
helpers that need composition-owned dependency assembly.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from urllib.parse import urlunsplit

from bioetl.composition import _services
from bioetl.composition.runtime_builders import config_access as _config_access
from bioetl.domain.exceptions import MetricsServerError
from bioetl.domain.ports import LoggerPort

_PUSHGATEWAY_FALLBACK = "localhost:9091"

if TYPE_CHECKING:
    from bioetl.application.services.export_lineage.audit_inspection_service import (
        AuditInspectionService,
    )
    from bioetl.application.services.checkpoint.checkpoint_service import (
        CheckpointService,
    )
    from bioetl.application.services.control_plane.manifest.inspection_service import (
        RunManifestInspectionService,
    )
    from bioetl.application.services.ops.health_service import HealthService
    from bioetl.application.services.lineage.lineage_inspection_service import (
        LineageInspectionService,
    )
    from bioetl.application.services.ops.metrics_service import MetricsService
    from bioetl.application.services.workflow.observability_workflow_service import (
        ObservabilityWorkflowService,
        RunForensicDossierResult,
    )
    from bioetl.application.services.quality.quarantine_service import QuarantineService

__all__ = [
    "MetricsOperatorProfile",
    "ObservabilityDiagnosticsBundle",
    "delete_metrics_from_gateway",
    "get_audit_service",
    "get_checkpoint_service",
    "get_health_service",
    "get_lineage_service",
    "get_metrics_operator_profile",
    "get_metrics_service",
    "get_observability_diagnostics_bundle",
    "get_observability_workflow_service",
    "get_quarantine_service",
    "get_run_manifest_service",
    "inspect_run_dossier",
    "push_metrics_to_gateway",
    "start_metrics_server",
]


@dataclass(frozen=True, slots=True)
class ObservabilityDiagnosticsBundle:
    """Unified operator-facing observability diagnostics surface."""

    health_service: HealthService
    checkpoint_service: CheckpointService
    audit_service: AuditInspectionService
    metrics_service: MetricsService
    quarantine_service: QuarantineService
    run_manifest_service: RunManifestInspectionService
    lineage_service: LineageInspectionService
    workflow_service: ObservabilityWorkflowService


@dataclass(frozen=True, slots=True)
class MetricsOperatorProfile:
    """Operator-facing summary of metrics/admin observability behavior."""

    metrics_enabled: bool
    metrics_server_enabled: bool
    metrics_server_running: bool
    metrics_port: int
    metrics_addr: str
    metrics_started_at: datetime | None
    metrics_endpoint: str | None
    metrics_server_mode: str
    pushgateway_mode: str
    pushgateway_gateway: str
    tracing_enabled: bool
    audit_enabled: bool

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe diagnostics payload."""
        return {
            "metrics_enabled": self.metrics_enabled,
            "metrics_server_enabled": self.metrics_server_enabled,
            "metrics_server_running": self.metrics_server_running,
            "metrics_port": self.metrics_port,
            "metrics_addr": self.metrics_addr,
            "metrics_started_at": (
                self.metrics_started_at.isoformat()
                if self.metrics_started_at is not None
                else None
            ),
            "metrics_endpoint": self.metrics_endpoint,
            "metrics_server_mode": self.metrics_server_mode,
            "pushgateway_mode": self.pushgateway_mode,
            "pushgateway_gateway": self.pushgateway_gateway,
            "tracing_enabled": self.tracing_enabled,
            "audit_enabled": self.audit_enabled,
        }


def start_metrics_server(
    port: int = 8000,
    addr: str = "0.0.0.0",
    *,
    fail_fast: bool = False,
    retry_count: int = 3,
    retry_delay: float = 1.0,
    logger: LoggerPort | None = None,
) -> bool:
    """Start the metrics server through the canonical metrics service seam."""
    metrics_service = get_metrics_service()
    if logger is not None:
        metrics_service.logger = logger
    result = metrics_service.start(
        port=port,
        addr=addr,
        fail_fast=fail_fast,
        retry_count=retry_count,
        retry_delay=retry_delay,
    )
    if fail_fast and not result.success and result.error is not None:
        raise MetricsServerError(port=port, reason=result.error)
    return bool(result.success)


def push_metrics_to_gateway(
    run_label: str = "bioetl",
    *,
    pipeline_name: str | None = None,
    run_type: str | None = None,
    grouping_key_extra: Mapping[str, str] | None = None,
    metric_names: tuple[str, ...] | None = None,
    logger: LoggerPort | None = None,
) -> bool:
    """Push metrics through the canonical composition-owned observability seam."""

    settings = _config_access.get_settings()
    gateway = getattr(settings, "pushgateway_url", None) or _PUSHGATEWAY_FALLBACK
    grouping_key: dict[str, str] = {}
    if pipeline_name:
        grouping_key["pipeline"] = pipeline_name
    if run_type:
        grouping_key["run_type"] = run_type
    if grouping_key_extra:
        grouping_key.update(grouping_key_extra)
    metrics_service = get_metrics_service()
    if logger is not None:
        metrics_service.logger = logger
    result = metrics_service.push_to_gateway(
        gateway=gateway,
        run_label=run_label,
        grouping_key=grouping_key,
        metric_names=metric_names,
    )
    return bool(result.success)


def delete_metrics_from_gateway(
    run_label: str = "bioetl",
    *,
    pipeline_name: str | None = None,
    run_type: str | None = None,
    logger: LoggerPort | None = None,
) -> bool:
    """Delete metrics through the canonical composition-owned observability seam."""

    settings = _config_access.get_settings()
    gateway = getattr(settings, "pushgateway_url", None) or _PUSHGATEWAY_FALLBACK
    grouping_key: dict[str, str] = {}
    if pipeline_name:
        grouping_key["pipeline"] = pipeline_name
    if run_type:
        grouping_key["run_type"] = run_type
    metrics_service = get_metrics_service()
    if logger is not None:
        metrics_service.logger = logger
    result = metrics_service.delete_from_gateway(
        gateway=gateway,
        run_label=run_label,
        grouping_key=grouping_key,
    )
    return bool(result.success)


def get_audit_service() -> AuditInspectionService:
    """Load the audit diagnostics service through composition on demand."""

    return _services.get_audit_service()


def get_checkpoint_service() -> CheckpointService:
    """Load the checkpoint diagnostics service through composition on demand."""

    return _services.get_checkpoint_service()


def get_metrics_service() -> MetricsService:
    """Load the metrics diagnostics service through composition on demand."""

    return _services.get_metrics_service()


def get_metrics_operator_profile() -> MetricsOperatorProfile:
    """Return the canonical operator-facing metrics/admin profile."""

    settings = _config_access.get_settings()
    metrics_service = get_metrics_service()
    status = metrics_service.get_status()
    live_metrics_port = (
        status.port
        if status.running and status.port is not None
        else settings.metrics_port
    )
    metrics_enabled = bool(settings.observability.metrics_enabled)
    metrics_server_enabled = bool(settings.observability.metrics_server_enabled)
    metrics_endpoint = None
    if metrics_enabled and metrics_server_enabled:
        metrics_endpoint = urlunsplit(
            (
                "http",
                f"{settings.metrics_addr}:{live_metrics_port}",
                "/metrics",
                "",
                "",
            )
        )
    metrics_server_mode = (
        "auto_managed_during_pipeline_runs"
        if metrics_enabled and metrics_server_enabled
        else "disabled"
    )
    pushgateway_mode = (
        "best_effort_on_run_completion" if metrics_enabled else "disabled"
    )
    pushgateway_gateway = (
        getattr(settings, "pushgateway_url", None) or _PUSHGATEWAY_FALLBACK
    )
    return MetricsOperatorProfile(
        metrics_enabled=metrics_enabled,
        metrics_server_enabled=metrics_server_enabled,
        metrics_server_running=status.running,
        metrics_port=live_metrics_port,
        metrics_addr=settings.metrics_addr,
        metrics_started_at=status.started_at,
        metrics_endpoint=metrics_endpoint,
        metrics_server_mode=metrics_server_mode,
        pushgateway_mode=pushgateway_mode,
        pushgateway_gateway=pushgateway_gateway,
        tracing_enabled=bool(settings.observability.tracing_enabled),
        audit_enabled=bool(settings.observability.audit_enabled),
    )


def get_observability_workflow_service() -> ObservabilityWorkflowService:
    """Load the canonical observability workflow service on demand."""

    return _services.get_observability_workflow_service()


async def inspect_run_dossier(
    run_id: str,
    *,
    audit_limit: int = 100,
) -> RunForensicDossierResult:
    """Inspect one run through the canonical observability workflow seam."""
    workflow_service = get_observability_workflow_service()
    return await workflow_service.inspect_run_dossier(
        run_id,
        audit_limit=audit_limit,
    )


def get_health_service() -> HealthService:
    """Load the health diagnostics service through composition on demand."""

    return _services.get_health_service()


def get_quarantine_service() -> QuarantineService:
    """Load the quarantine diagnostics service through composition on demand."""

    return _services.get_quarantine_service()


def get_run_manifest_service() -> RunManifestInspectionService:
    """Load the run-manifest diagnostics service through composition on demand."""

    return _services.get_run_manifest_service()


def get_lineage_service() -> LineageInspectionService:
    """Load the lineage diagnostics service through composition on demand."""

    return _services.get_lineage_service()


def get_observability_diagnostics_bundle() -> ObservabilityDiagnosticsBundle:
    """Return the canonical unified observability diagnostics bundle."""

    return ObservabilityDiagnosticsBundle(
        health_service=get_health_service(),
        checkpoint_service=get_checkpoint_service(),
        audit_service=get_audit_service(),
        metrics_service=get_metrics_service(),
        quarantine_service=get_quarantine_service(),
        run_manifest_service=get_run_manifest_service(),
        lineage_service=get_lineage_service(),
        workflow_service=get_observability_workflow_service(),
    )
