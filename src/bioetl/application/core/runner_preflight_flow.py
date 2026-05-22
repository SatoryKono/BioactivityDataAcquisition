"""Preflight execution helpers for :mod:`bioetl.application.core.runner`."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Protocol

from bioetl.application.core._runner_observability import (
    emit_preflight_health_results,
)
from bioetl.domain.control_plane.run_ledger import ORDINARY_RUN_LEDGER_STAGE_NAMES

if TYPE_CHECKING:
    from bioetl.application.core.pipeline_service_protocols import (
        PipelineServicesProtocol,
    )
    from bioetl.application.core.preflight.service import PreflightService
    from bioetl.application.observability.observer import PipelineObserver

_PREFLIGHT_STAGE_NAME = ORDINARY_RUN_LEDGER_STAGE_NAMES[0]


class _PreflightExecutionHostProtocol(Protocol):
    """Runner attributes required by preflight validation."""

    _services: PipelineServicesProtocol
    _preflight_service: PreflightService
    _observer: PipelineObserver


async def validate_infrastructure(host: _PreflightExecutionHostProtocol) -> None:
    """Validate infrastructure health before pipeline execution."""
    start_time = time.perf_counter()
    try:
        report = await host._preflight_service.validate_infrastructure(
            host._services,
            raise_on_unhealthy=False,
        )
    except TypeError as exc:
        if "raise_on_unhealthy" not in str(exc):
            raise
        report = await host._preflight_service.validate_infrastructure(host._services)
    if report is None:
        return
    duration = time.perf_counter() - start_time
    emit_preflight_health_results(
        host,
        report,
        runner_stage=_PREFLIGHT_STAGE_NAME,
    )
    host._observer.emit_health_check_summary(
        validated=report.is_healthy,
        duration_seconds=duration,
        overall_status=report.overall_status.value,
        components_checked=len(report.results),
        runner_stage=_PREFLIGHT_STAGE_NAME,
    )
    host._preflight_service.assert_infrastructure_healthy(report)


__all__ = ["validate_infrastructure"]
