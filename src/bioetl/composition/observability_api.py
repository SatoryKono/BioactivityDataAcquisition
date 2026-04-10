"""Canonical public observability composition API.

This module is the sanctioned public seam for observability-related runtime
helpers that need composition-owned dependency assembly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.composition.bootstrap.runtime.observability import start_metrics_server

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
    "start_metrics_server",
]


@dataclass(frozen=True, slots=True)
class ObservabilityDiagnosticsBundle:
    """Unified operator-facing observability diagnostics surface."""

    audit_service: AuditInspectionService
    health_service: HealthService
    checkpoint_service: CheckpointService
    audit_service: AuditInspectionService
    metrics_service: MetricsService
    workflow_service: ObservabilityWorkflowService
    quarantine_service: QuarantineService
    run_manifest_service: RunManifestInspectionService
    lineage_service: LineageInspectionService
    workflow_service: ObservabilityWorkflowService


def get_audit_service() -> AuditInspectionService:
    """Load the audit diagnostics service through composition on demand."""
    from bioetl.composition.services_api import get_audit_service as _impl

    return _impl()


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
    """Load the workflow-level observability diagnostics service on demand."""
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
        audit_service=get_audit_service(),
        health_service=get_health_service(),
        checkpoint_service=get_checkpoint_service(),
        audit_service=get_audit_service(),
        metrics_service=get_metrics_service(),
        workflow_service=get_observability_workflow_service(),
        quarantine_service=get_quarantine_service(),
        run_manifest_service=get_run_manifest_service(),
        lineage_service=get_lineage_service(),
        workflow_service=get_observability_workflow_service(),
    )
