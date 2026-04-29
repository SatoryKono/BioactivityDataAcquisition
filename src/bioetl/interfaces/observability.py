"""Observability interface compatibility facade for BioETL.

This module remains import-safe for interface-layer consumers, but the
canonical public observability API now lives in
``bioetl.composition.observability_api``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.observability_api import ObservabilityDiagnosticsBundle
from bioetl.domain.exceptions import MetricsServerError
from bioetl.domain.ports import LoggerPort

if TYPE_CHECKING:
    from bioetl.application.services.audit_inspection_service import (
        AuditInspectionService,
    )
    from bioetl.application.services.checkpoint_service import CheckpointService
    from bioetl.application.services.control_plane.run_manifest_inspection_service import (
        RunManifestInspectionService,
    )
    from bioetl.application.services.health_service import HealthService
    from bioetl.application.services.lineage.lineage_inspection_service import (
        LineageInspectionService,
    )
    from bioetl.application.services.metrics_service import MetricsService
    from bioetl.application.services.observability_workflow_service import (
        ObservabilityWorkflowService,
        RunForensicDossierResult,
    )
    from bioetl.application.services.quarantine_service import QuarantineService
    from bioetl.composition.observability_api import MetricsOperatorProfile

__all__ = [
    "MetricsServerError",
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


def start_metrics_server(
    port: int = 8000,
    addr: str = "0.0.0.0",
    *,
    fail_fast: bool = False,
    retry_count: int = 3,
    retry_delay: float = 1.0,
    logger: LoggerPort | None = None,
) -> bool:
    """Start the metrics server through the canonical composition API."""
    from bioetl.composition.observability_api import start_metrics_server as _impl

    return _impl(
        port=port,
        addr=addr,
        fail_fast=fail_fast,
        retry_count=retry_count,
        retry_delay=retry_delay,
        logger=logger,
    )


def push_metrics_to_gateway(
    run_label: str = "bioetl",
    *,
    pipeline_name: str | None = None,
    run_type: str | None = None,
    logger: LoggerPort | None = None,
) -> bool:
    """Push metrics through the canonical composition API."""
    from bioetl.composition.observability_api import push_metrics_to_gateway as _impl

    return _impl(
        run_label=run_label,
        pipeline_name=pipeline_name,
        run_type=run_type,
        logger=logger,
    )


def delete_metrics_from_gateway(
    run_label: str = "bioetl",
    *,
    pipeline_name: str | None = None,
    run_type: str | None = None,
    logger: LoggerPort | None = None,
) -> bool:
    """Delete metrics through the canonical composition API."""
    from bioetl.composition.observability_api import (
        delete_metrics_from_gateway as _impl,
    )

    return _impl(
        run_label=run_label,
        pipeline_name=pipeline_name,
        run_type=run_type,
        logger=logger,
    )


def get_checkpoint_service() -> CheckpointService:
    """Load the checkpoint diagnostics service through the canonical composition API."""
    from bioetl.composition.observability_api import get_checkpoint_service as _impl

    return _impl()


def get_audit_service() -> AuditInspectionService:
    """Load the audit diagnostics service through the canonical composition API."""
    from bioetl.composition.observability_api import get_audit_service as _impl

    return _impl()


def get_metrics_service() -> MetricsService:
    """Load the metrics diagnostics service through the canonical composition API."""
    from bioetl.composition.observability_api import get_metrics_service as _impl

    return _impl()


def get_metrics_operator_profile() -> MetricsOperatorProfile:
    """Load the operator-facing metrics/admin diagnostics profile."""
    from bioetl.composition.observability_api import (
        get_metrics_operator_profile as _impl,
    )

    return _impl()


def get_observability_workflow_service() -> ObservabilityWorkflowService:
    """Load the observability workflow service through the canonical composition API."""
    from bioetl.composition.observability_api import (
        get_observability_workflow_service as _impl,
    )

    return _impl()


async def inspect_run_dossier(
    run_id: str,
    *,
    audit_limit: int = 100,
) -> RunForensicDossierResult:
    """Inspect one run through the canonical composition dossier seam."""
    from bioetl.composition.observability_api import inspect_run_dossier as _impl

    return await _impl(run_id, audit_limit=audit_limit)


def get_health_service() -> HealthService:
    """Load the health diagnostics service through the canonical composition API."""
    from bioetl.composition.observability_api import get_health_service as _impl

    return _impl()


def get_quarantine_service() -> QuarantineService:
    """Load the quarantine diagnostics service through the canonical composition API."""
    from bioetl.composition.observability_api import get_quarantine_service as _impl

    return _impl()


def get_run_manifest_service() -> RunManifestInspectionService:
    """Load the run-manifest diagnostics service through the canonical composition API."""
    from bioetl.composition.observability_api import get_run_manifest_service as _impl

    return _impl()


def get_lineage_service() -> LineageInspectionService:
    """Load the lineage diagnostics service through the canonical composition API."""
    from bioetl.composition.observability_api import get_lineage_service as _impl

    return _impl()


def get_observability_diagnostics_bundle() -> ObservabilityDiagnosticsBundle:
    """Return the unified diagnostics bundle through the composition API."""
    from bioetl.composition.observability_api import (
        get_observability_diagnostics_bundle as _impl,
    )

    return _impl()
