"""Observability interface for BioETL.

Re-exports observability components for external consumers.

Note:
    MetricsServerError is defined in domain.exceptions (value object,
    can be imported by all layers). start_metrics_server is exposed via
    the composition facade so interfaces do not wire directly to bootstrap
    runtime internals or infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.domain.exceptions import MetricsServerError
from bioetl.domain.ports import LoggerPort

if TYPE_CHECKING:
    from bioetl.application.services.health_service import HealthService
    from bioetl.application.services.lineage_inspection_service import (
        LineageInspectionService,
    )
    from bioetl.application.services.metrics_service import MetricsService
    from bioetl.application.services.quarantine_service import QuarantineService
    from bioetl.application.services.run_manifest_inspection_service import (
        RunManifestInspectionService,
    )

__all__ = [
    "MetricsServerError",
    "ObservabilityDiagnosticsBundle",
    "get_health_service",
    "get_lineage_service",
    "get_metrics_service",
    "get_observability_diagnostics_bundle",
    "get_quarantine_service",
    "get_run_manifest_service",
    "start_metrics_server",
]


@dataclass(frozen=True, slots=True)
class ObservabilityDiagnosticsBundle:
    """Unified operator-facing diagnostics surface.

    This bundles the existing operator diagnostics services into one
    discoverable interface seam without introducing new business logic.
    """

    health_service: HealthService
    metrics_service: MetricsService
    quarantine_service: QuarantineService
    run_manifest_service: RunManifestInspectionService
    lineage_service: LineageInspectionService


def start_metrics_server(
    port: int = 8000,
    addr: str = "0.0.0.0",
    *,
    fail_fast: bool = False,
    retry_count: int = 3,
    retry_delay: float = 1.0,
    logger: LoggerPort | None = None,
) -> bool:
    """Start the metrics server through composition on demand."""
    from bioetl.composition.observability_api import start_metrics_server as _impl

    return _impl(
        port=port,
        addr=addr,
        fail_fast=fail_fast,
        retry_count=retry_count,
        retry_delay=retry_delay,
        logger=logger,
    )


def get_metrics_service() -> MetricsService:
    """Load the metrics diagnostics service through composition on demand."""
    from bioetl.composition.services_api import get_metrics_service as _impl

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
    """Return one unified operator-facing diagnostics bundle.

    This keeps operator discovery in a single interface module while
    continuing to delegate actual service creation to composition.
    """

    return ObservabilityDiagnosticsBundle(
        health_service=get_health_service(),
        metrics_service=get_metrics_service(),
        quarantine_service=get_quarantine_service(),
        run_manifest_service=get_run_manifest_service(),
        lineage_service=get_lineage_service(),
    )
