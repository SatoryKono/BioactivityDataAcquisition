"""Control-plane helpers for composite runner lifecycle events."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol

from bioetl.domain.composite.result import (
    DependencyResult,
    EnrichmentResult,
    EnrichmentStatus,
    MergeResult,
    SeedResult,
)
from bioetl.domain.control_plane.run_ledger import (
    COMPOSITE_RUN_LEDGER_STAGE_NAMES,
)

if TYPE_CHECKING:
    from bioetl.application.composite.runner_pkg.runner_models import (
        CompositeExecutionContext,
    )
    from bioetl.application.services.run_ledger_service import RunLedgerService

__all__ = ["CompositeRunnerControlPlaneMixin"]


class _CompositeRunnerControlPlaneHostProtocol(Protocol):
    _run_ledger_service: RunLedgerService | None
    _manifest_id: str | None

    def _record_with_ledger_service(
        self,
        recorder: Callable[[RunLedgerService], None],
    ) -> None: ...

    def _record_stage_started(
        self,
        *,
        stage: str,
        details: dict[str, object] | None = None,
    ) -> None: ...

    def _record_stage_completed(
        self,
        *,
        stage: str,
        metrics_snapshot: dict[str, int],
    ) -> None: ...


def _count_dependency_status(
    results: dict[str, DependencyResult],
    *,
    is_success: bool,
) -> int:
    """Count dependencies matching one success predicate."""
    return sum(1 for result in results.values() if result.is_success is is_success)


def _count_enrichment_status(
    results: dict[str, EnrichmentResult],
    *,
    status: EnrichmentStatus,
) -> int:
    """Count enrichers matching one terminal status."""
    return sum(1 for result in results.values() if result.status == status)


def _seed_stage_metrics(seed_result: SeedResult) -> dict[str, int]:
    """Build stable seed-stage metrics for run-ledger payloads."""
    return {
        "records_extracted": int(seed_result.records_extracted),
        "records_silver": int(seed_result.records_silver),
        "keys_generated": int(seed_result.keys_generated),
    }


def _dependency_stage_metrics(
    dependency_results: dict[str, DependencyResult],
) -> dict[str, int]:
    """Build dependency-stage metrics for run-ledger payloads."""
    return {
        "dependencies_total": len(dependency_results),
        "dependencies_succeeded": _count_dependency_status(
            dependency_results,
            is_success=True,
        ),
        "dependencies_failed": _count_dependency_status(
            dependency_results,
            is_success=False,
        ),
    }


def _enrichment_stage_metrics(
    enrichment_results: dict[str, EnrichmentResult],
) -> dict[str, int]:
    """Build enrichment-stage metrics for run-ledger payloads."""
    return {
        "enrichers_total": len(enrichment_results),
        "enrichers_succeeded": _count_enrichment_status(
            enrichment_results,
            status=EnrichmentStatus.SUCCESS,
        ),
        "enrichers_failed": _count_enrichment_status(
            enrichment_results,
            status=EnrichmentStatus.FAILED,
        ),
        "enrichers_skipped": _count_enrichment_status(
            enrichment_results,
            status=EnrichmentStatus.SKIPPED,
        ),
    }


def _merge_stage_metrics(merge_result: MergeResult) -> dict[str, int]:
    """Build merge-stage metrics for run-ledger payloads."""
    return {
        "records_merged": int(merge_result.records_merged),
        "records_from_seed": int(merge_result.records_from_seed),
        "records_enriched": int(merge_result.records_enriched),
        "records_fully_enriched": int(merge_result.records_fully_enriched),
    }


def _run_completion_metrics(
    artifacts: CompositeExecutionContext,
) -> dict[str, int]:
    """Build final aggregate metrics for run completion entries."""
    metrics = _seed_stage_metrics(artifacts.seed_result)
    metrics.update(_dependency_stage_metrics(artifacts.dependency_results))
    metrics.update(_enrichment_stage_metrics(artifacts.enrichment_results))
    if artifacts.merge_result is not None:
        metrics.update(_merge_stage_metrics(artifacts.merge_result))
    return metrics


_SEED_STAGE_NAME = COMPOSITE_RUN_LEDGER_STAGE_NAMES[0]
_DEPENDENCIES_STAGE_NAME = COMPOSITE_RUN_LEDGER_STAGE_NAMES[1]
_ENRICHMENT_STAGE_NAME = COMPOSITE_RUN_LEDGER_STAGE_NAMES[2]
_MERGE_STAGE_NAME = COMPOSITE_RUN_LEDGER_STAGE_NAMES[3]


class CompositeRunnerControlPlaneMixin:
    """Mixin that emits composite lifecycle events into RunLedgerService."""

    _run_ledger_service: RunLedgerService | None
    _manifest_id: str | None

    @property
    def manifest_id(self: _CompositeRunnerControlPlaneHostProtocol) -> str | None:
        """Return control-plane manifest identifier linked to this run."""
        return self._manifest_id

    def _record_with_ledger_service(
        self: _CompositeRunnerControlPlaneHostProtocol,
        recorder: Callable[[RunLedgerService], None],
    ) -> None:
        """Run one ledger write only when control-plane wiring is attached."""
        if self._run_ledger_service is None:
            return
        recorder(self._run_ledger_service)

    def _record_stage_started(
        self: _CompositeRunnerControlPlaneHostProtocol,
        *,
        stage: str,
        details: dict[str, object] | None = None,
    ) -> None:
        """Append one composite ``stage_started`` entry when ledger is attached."""
        self._record_with_ledger_service(
            lambda ledger_service: ledger_service.record_stage_started(
                stage=stage,
                details=details,
            )
        )

    def _record_stage_completed(
        self: _CompositeRunnerControlPlaneHostProtocol,
        *,
        stage: str,
        metrics_snapshot: dict[str, int],
    ) -> None:
        """Append one composite ``stage_completed`` entry when ledger is attached."""
        self._record_with_ledger_service(
            lambda ledger_service: ledger_service.record_stage_completed(
                stage=stage,
                metrics_snapshot=metrics_snapshot,
            )
        )

    def _record_run_started(self: _CompositeRunnerControlPlaneHostProtocol) -> None:
        """Append ``run_started`` when control-plane ledger is attached."""
        self._record_with_ledger_service(
            lambda ledger_service: ledger_service.record_run_started()
        )

    def _record_run_failed(
        self: _CompositeRunnerControlPlaneHostProtocol,
        error: Exception,
    ) -> None:
        """Append ``run_failed`` when control-plane ledger is attached."""
        self._record_with_ledger_service(
            lambda ledger_service: ledger_service.record_run_failed(
                message=str(error),
                error_type=type(error).__name__,
                metrics_snapshot={},
            )
        )

    def _record_seed_stage_started(
        self: _CompositeRunnerControlPlaneHostProtocol,
    ) -> None:
        """Append one ``stage_started`` entry for seed phase."""
        self._record_stage_started(stage=_SEED_STAGE_NAME)

    def _record_dependencies_stage_started(
        self: _CompositeRunnerControlPlaneHostProtocol,
        dependency_pipeline_names: list[str],
    ) -> None:
        """Append one ``stage_started`` entry for dependencies phase."""
        self._record_stage_started(
            stage=_DEPENDENCIES_STAGE_NAME,
            details={
                "dependencies": list(dependency_pipeline_names),
                "count": len(dependency_pipeline_names),
            },
        )

    def _record_enrichment_stage_started(
        self: _CompositeRunnerControlPlaneHostProtocol,
        enricher_names: list[str],
    ) -> None:
        """Append one ``stage_started`` entry for enrichment phase."""
        self._record_stage_started(
            stage=_ENRICHMENT_STAGE_NAME,
            details={
                "enrichers": list(enricher_names),
                "count": len(enricher_names),
            },
        )

    def _record_merge_stage_started(
        self: _CompositeRunnerControlPlaneHostProtocol,
    ) -> None:
        """Append one ``stage_started`` entry for merge phase."""
        self._record_stage_started(stage=_MERGE_STAGE_NAME)

    def _record_run_finished(
        self: _CompositeRunnerControlPlaneHostProtocol,
        artifacts: CompositeExecutionContext,
    ) -> None:
        """Append ``run_finished`` when control-plane ledger is attached."""
        self._record_with_ledger_service(
            lambda ledger_service: ledger_service.record_run_finished(
                metrics_snapshot=_run_completion_metrics(artifacts),
            )
        )

    def _record_seed_stage_completed(
        self: _CompositeRunnerControlPlaneHostProtocol,
        seed_result: SeedResult,
    ) -> None:
        """Append one ``stage_completed`` entry for seed phase."""
        self._record_stage_completed(
            stage=_SEED_STAGE_NAME,
            metrics_snapshot=_seed_stage_metrics(seed_result),
        )

    def _record_dependencies_stage_completed(
        self: _CompositeRunnerControlPlaneHostProtocol,
        dependency_results: dict[str, DependencyResult],
    ) -> None:
        """Append one ``stage_completed`` entry for dependencies phase."""
        self._record_stage_completed(
            stage=_DEPENDENCIES_STAGE_NAME,
            metrics_snapshot=_dependency_stage_metrics(dependency_results),
        )

    def _record_enrichment_stage_completed(
        self: _CompositeRunnerControlPlaneHostProtocol,
        enrichment_results: dict[str, EnrichmentResult],
    ) -> None:
        """Append one ``stage_completed`` entry for enrichment phase."""
        self._record_stage_completed(
            stage=_ENRICHMENT_STAGE_NAME,
            metrics_snapshot=_enrichment_stage_metrics(enrichment_results),
        )

    def _record_merge_stage_completed(
        self: _CompositeRunnerControlPlaneHostProtocol,
        merge_result: MergeResult,
    ) -> None:
        """Append one ``stage_completed`` entry for merge phase."""
        self._record_stage_completed(
            stage=_MERGE_STAGE_NAME,
            metrics_snapshot=_merge_stage_metrics(merge_result),
        )
