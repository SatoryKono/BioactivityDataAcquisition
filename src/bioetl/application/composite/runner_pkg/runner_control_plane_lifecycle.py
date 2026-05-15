"""Lifecycle/start-event support for composite runner control-plane flows."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol

from bioetl.application.composite.runner_pkg.runner_stage_payloads import (
    build_dependency_stage_details,
    build_enrichment_stage_details,
)
from bioetl.domain.control_plane.run_ledger import COMPOSITE_RUN_LEDGER_STAGE_NAMES

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.run_ledger_service import (
        RunLedgerService,
    )
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.ports import MetricsPort


class CompositeRunnerControlPlaneHostProtocol(Protocol):
    _config: CompositeConfig
    _metrics: MetricsPort | None
    _run_ledger_service: RunLedgerService | None
    _manifest_id: str | None


SEED_STAGE_NAME = COMPOSITE_RUN_LEDGER_STAGE_NAMES[0]
DEPENDENCIES_STAGE_NAME = COMPOSITE_RUN_LEDGER_STAGE_NAMES[1]
ENRICHMENT_STAGE_NAME = COMPOSITE_RUN_LEDGER_STAGE_NAMES[2]
MERGE_STAGE_NAME = COMPOSITE_RUN_LEDGER_STAGE_NAMES[3]


def record_with_ledger_service(
    host: CompositeRunnerControlPlaneHostProtocol,
    recorder: Callable[[RunLedgerService], object],
) -> None:
    """Run one ledger write only when control-plane wiring is attached."""
    if host._run_ledger_service is None:
        return
    recorder(host._run_ledger_service)


def record_run_metrics_event(
    host: CompositeRunnerControlPlaneHostProtocol,
    *,
    metrics_snapshot: dict[str, int],
    recorder: Callable[[RunLedgerService, dict[str, int]], object],
) -> None:
    """Emit one run-level metrics-backed ledger event when attached."""
    record_with_ledger_service(
        host,
        lambda ledger_service: recorder(ledger_service, metrics_snapshot),
    )


def record_stage_started(
    host: CompositeRunnerControlPlaneHostProtocol,
    *,
    stage: str,
    details: dict[str, object] | None = None,
) -> None:
    """Append one composite ``stage_started`` entry when ledger is attached."""
    record_with_ledger_service(
        host,
        lambda ledger_service: ledger_service.record_stage_started(
            stage=stage,
            details=details,
        ),
    )


def record_stage_completed(
    host: CompositeRunnerControlPlaneHostProtocol,
    *,
    stage: str,
    metrics_snapshot: dict[str, int],
) -> None:
    """Append one composite ``stage_completed`` entry when ledger is attached."""
    record_with_ledger_service(
        host,
        lambda ledger_service: ledger_service.record_stage_completed(
            stage=stage,
            metrics_snapshot=metrics_snapshot,
        ),
    )


def record_run_started(host: CompositeRunnerControlPlaneHostProtocol) -> None:
    """Append ``run_started`` when control-plane ledger is attached."""
    record_with_ledger_service(
        host,
        lambda ledger_service: ledger_service.record_run_started(),
    )


def record_run_failed(
    host: CompositeRunnerControlPlaneHostProtocol,
    error: Exception,
) -> None:
    """Append ``run_failed`` when control-plane ledger is attached."""
    record_run_metrics_event(
        host,
        metrics_snapshot={},
        recorder=lambda ledger_service, metrics_snapshot: (
            ledger_service.record_run_exception(
                error=error,
                metrics_snapshot=metrics_snapshot,
            )
        ),
    )


def record_run_shutdown(host: CompositeRunnerControlPlaneHostProtocol) -> None:
    """Append ``run_shutdown`` when control-plane ledger is attached."""
    record_run_metrics_event(
        host,
        metrics_snapshot={},
        recorder=lambda ledger_service, metrics_snapshot: (
            ledger_service.record_run_shutdown(
                metrics_snapshot=metrics_snapshot,
            )
        ),
    )


def record_seed_stage_started(host: CompositeRunnerControlPlaneHostProtocol) -> None:
    """Append one ``stage_started`` entry for seed phase."""
    record_stage_started(host, stage=SEED_STAGE_NAME)


def record_dependencies_stage_started(
    host: CompositeRunnerControlPlaneHostProtocol,
    dependency_pipeline_names: list[str],
) -> None:
    """Append one ``stage_started`` entry for dependencies phase."""
    record_stage_started(
        host,
        stage=DEPENDENCIES_STAGE_NAME,
        details=build_dependency_stage_details(dependency_pipeline_names),
    )


def record_enrichment_stage_started(
    host: CompositeRunnerControlPlaneHostProtocol,
    enricher_names: list[str],
) -> None:
    """Append one ``stage_started`` entry for enrichment phase."""
    record_stage_started(
        host,
        stage=ENRICHMENT_STAGE_NAME,
        details=build_enrichment_stage_details(enricher_names),
    )


def record_merge_stage_started(host: CompositeRunnerControlPlaneHostProtocol) -> None:
    """Append one ``stage_started`` entry for merge phase."""
    record_stage_started(host, stage=MERGE_STAGE_NAME)


__all__ = [
    "CompositeRunnerControlPlaneHostProtocol",
    "DEPENDENCIES_STAGE_NAME",
    "ENRICHMENT_STAGE_NAME",
    "MERGE_STAGE_NAME",
    "SEED_STAGE_NAME",
    "record_dependencies_stage_started",
    "record_enrichment_stage_started",
    "record_merge_stage_started",
    "record_run_failed",
    "record_run_metrics_event",
    "record_run_shutdown",
    "record_run_started",
    "record_seed_stage_started",
    "record_stage_completed",
    "record_stage_started",
    "record_with_ledger_service",
]
