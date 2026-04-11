"""Canonical public observability composition API.

This module is the sanctioned public seam for observability-related runtime
helpers that need composition-owned dependency assembly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import uuid4

from bioetl.domain.exceptions import MetricsServerError
from bioetl.domain.ports import LoggerPort

if TYPE_CHECKING:
    from bioetl.application.services.audit_inspection_service import (
        AuditInspectionService,
    )
    from bioetl.application.services.checkpoint_service import CheckpointService
    from bioetl.application.services.health_service import HealthService
    from bioetl.application.services.lineage_inspection_service import (
        LineageInspectionService,
    )
    from bioetl.application.services.metrics_service import MetricsService
    from bioetl.application.services.observability_workflow_service import (
        ObservabilityWorkflowService,
    )
    from bioetl.application.services.quarantine_service import QuarantineService
    from bioetl.application.services.run_manifest_inspection_service import (
        RunManifestInspectionService,
    )

__all__ = [
    "ObservabilityDiagnosticsBundle",
    "get_audit_service",
    "get_checkpoint_service",
    "get_health_service",
    "get_lineage_service",
    "get_metrics_service",
    "get_observability_diagnostics_bundle",
    "get_observability_workflow_service",
    "get_quarantine_service",
    "get_run_manifest_service",
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
    logger: LoggerPort | None = None,
) -> bool:
    """Push metrics through the canonical composition-owned observability seam."""
    from bioetl.composition.bootstrap.runtime.observability import bootstrap_logger_port
    from bioetl.infrastructure.config import get_settings

    settings = get_settings()
    gateway = getattr(settings, "pushgateway_url", None) or "localhost:9091"
    grouping_key: dict[str, str] = {}
    if pipeline_name:
        grouping_key["pipeline"] = pipeline_name
    if run_type:
        grouping_key["run_type"] = run_type
    metrics_service = get_metrics_service()
    metrics_service.logger = logger or bootstrap_logger_port(
        pipeline=pipeline_name or "metrics_publication",
        run_id=uuid4(),
        log_level="INFO",
    )
    result = metrics_service.push_to_gateway(
        gateway=gateway,
        run_label=run_label,
        grouping_key=grouping_key,
    )
    return bool(result.success)


def get_audit_service() -> AuditInspectionService:
    """Load the audit diagnostics service through composition on demand."""
    from bioetl.composition.services_api import get_audit_service as _impl

    return _impl()


def get_checkpoint_service() -> CheckpointService:
    """Load the checkpoint diagnostics service through composition on demand."""
    from bioetl.composition.services_api import get_checkpoint_service as _impl

    return _impl()


def get_metrics_service() -> MetricsService:
    """Load the metrics diagnostics service through composition on demand."""
    from bioetl.composition.services_api import get_metrics_service as _impl

    return _impl()


def get_observability_workflow_service() -> ObservabilityWorkflowService:
    """Load the canonical observability workflow service on demand."""
    from bioetl.composition.services_api import (
        get_observability_workflow_service as _impl,
    )

    return _impl()


def get_health_service() -> HealthService:
    """Load the health diagnostics service through composition on demand."""
    from bioetl.composition.services_api import get_health_service as _impl

    return _impl()


def get_quarantine_service() -> QuarantineService:
    """Load the quarantine diagnostics service through composition on demand."""
    from bioetl.composition.services_api import get_quarantine_service as _impl

    return _impl()


def get_run_manifest_service() -> RunManifestInspectionService:
    """Load the run-manifest diagnostics service through composition on demand."""
    from bioetl.composition.services_api import get_run_manifest_service as _impl

    return _impl()


def get_lineage_service() -> LineageInspectionService:
    """Load the lineage diagnostics service through composition on demand."""
    from bioetl.composition.services_api import get_lineage_service as _impl

    return _impl()


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
