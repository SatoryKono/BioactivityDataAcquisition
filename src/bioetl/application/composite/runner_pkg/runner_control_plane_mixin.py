"""Control-plane helpers for composite runner lifecycle events."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol

from bioetl.application.composite.runner_pkg.runner_stage_payloads import (
    build_composite_run_completion_metrics,
    build_dependency_stage_details,
    build_dependency_stage_metrics,
    build_enrichment_stage_details,
    build_enrichment_stage_metrics,
    build_merge_stage_metrics,
    build_seed_stage_metrics,
)
from bioetl.application.observability.pipeline_metrics import PipelineMetricsRecorder
from bioetl.domain.composite.result import (
    DependencyResult,
    EnrichmentResult,
    MergeResult,
    SeedResult,
)
from bioetl.domain.control_plane.run_ledger import (
    COMPOSITE_RUN_LEDGER_STAGE_NAMES,
)

if TYPE_CHECKING:
    from bioetl.application.composite.runtime_models import (
        CompositeExecutionContext,
    )
    from bioetl.application.services.control_plane.run_ledger_service import (
        RunLedgerService,
    )
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.ports import MetricsPort

__all__ = ["CompositeRunnerControlPlaneMixin"]


class _CompositeRunnerControlPlaneHostProtocol(Protocol):
    _config: CompositeConfig
    _metrics: MetricsPort | None
    _run_ledger_service: RunLedgerService | None
    _manifest_id: str | None

    def _record_with_ledger_service(
        self,
        recorder: Callable[[RunLedgerService], object],
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

    def _record_run_metrics_event(
        self,
        *,
        metrics_snapshot: dict[str, int],
        recorder: Callable[[RunLedgerService, dict[str, int]], object],
    ) -> None: ...


_SEED_STAGE_NAME = COMPOSITE_RUN_LEDGER_STAGE_NAMES[0]
_DEPENDENCIES_STAGE_NAME = COMPOSITE_RUN_LEDGER_STAGE_NAMES[1]
_ENRICHMENT_STAGE_NAME = COMPOSITE_RUN_LEDGER_STAGE_NAMES[2]
_MERGE_STAGE_NAME = COMPOSITE_RUN_LEDGER_STAGE_NAMES[3]


def _build_pipeline_metrics(
    host: _CompositeRunnerControlPlaneHostProtocol,
) -> PipelineMetricsRecorder:
    """Build a pipeline-scoped metrics facade for composite phase counters."""
    return PipelineMetricsRecorder(host._metrics, f"composite:{host._config.name}")


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
        recorder: Callable[[RunLedgerService], object],
    ) -> None:
        """Run one ledger write only when control-plane wiring is attached."""
        if self._run_ledger_service is None:
            return
        recorder(self._run_ledger_service)

    def _record_run_metrics_event(
        self: _CompositeRunnerControlPlaneHostProtocol,
        *,
        metrics_snapshot: dict[str, int],
        recorder: Callable[[RunLedgerService, dict[str, int]], object],
    ) -> None:
        """Append one run-level ledger entry with an explicit metrics snapshot."""
        self._record_with_ledger_service(
            lambda ledger_service: recorder(ledger_service, metrics_snapshot)
        )

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
        self._record_run_metrics_event(
            metrics_snapshot={},
            recorder=lambda ledger_service, metrics_snapshot: (
                ledger_service.record_run_exception(
                    error=error,
                    metrics_snapshot=metrics_snapshot,
                )
            ),
        )

    def _record_run_shutdown(
        self: _CompositeRunnerControlPlaneHostProtocol,
    ) -> None:
        """Append ``run_shutdown`` when control-plane ledger is attached."""
        self._record_run_metrics_event(
            metrics_snapshot={},
            recorder=lambda ledger_service, metrics_snapshot: (
                ledger_service.record_run_shutdown(
                    metrics_snapshot=metrics_snapshot,
                )
            ),
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
            details=build_dependency_stage_details(dependency_pipeline_names),
        )

    def _record_enrichment_stage_started(
        self: _CompositeRunnerControlPlaneHostProtocol,
        enricher_names: list[str],
    ) -> None:
        """Append one ``stage_started`` entry for enrichment phase."""
        self._record_stage_started(
            stage=_ENRICHMENT_STAGE_NAME,
            details=build_enrichment_stage_details(enricher_names),
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
        self._record_run_metrics_event(
            metrics_snapshot=build_composite_run_completion_metrics(artifacts),
            recorder=lambda ledger_service, metrics_snapshot: (
                ledger_service.record_run_finished(
                    metrics_snapshot=metrics_snapshot,
                )
            ),
        )

    def _record_seed_stage_completed(
        self: _CompositeRunnerControlPlaneHostProtocol,
        seed_result: SeedResult,
    ) -> None:
        """Append one ``stage_completed`` entry for seed phase."""
        pipeline_metrics = _build_pipeline_metrics(self)
        pipeline_metrics.record_composite_phase_records(
            phase="seed",
            outcome="extracted",
            count=int(seed_result.records_extracted),
        )
        pipeline_metrics.record_composite_phase_records(
            phase="seed",
            outcome="silver",
            count=int(seed_result.records_silver),
        )
        pipeline_metrics.record_composite_phase_loss(
            phase="seed",
            loss_kind="unwritten",
            count=max(
                int(seed_result.records_extracted) - int(seed_result.records_silver),
                0,
            ),
        )
        if seed_result.resumed:
            pipeline_metrics.record_composite_phase_retries(
                phase="seed",
                retry_kind="resume",
            )
        self._record_stage_completed(
            stage=_SEED_STAGE_NAME,
            metrics_snapshot=build_seed_stage_metrics(seed_result),
        )

    def _record_dependencies_stage_completed(
        self: _CompositeRunnerControlPlaneHostProtocol,
        dependency_results: dict[str, DependencyResult],
    ) -> None:
        """Append one ``stage_completed`` entry for dependencies phase."""
        pipeline_metrics = _build_pipeline_metrics(self)
        records_extracted = sum(
            int(result.records_extracted) for result in dependency_results.values()
        )
        records_silver = sum(
            int(result.records_silver) for result in dependency_results.values()
        )
        failed = sum(
            1 for result in dependency_results.values() if result.status.value == "failed"
        )
        timed_out = sum(
            1 for result in dependency_results.values() if result.status.value == "timeout"
        )
        resumed = sum(1 for result in dependency_results.values() if result.resumed)
        pipeline_metrics.record_composite_phase_records(
            phase="dependencies",
            outcome="extracted",
            count=records_extracted,
        )
        pipeline_metrics.record_composite_phase_records(
            phase="dependencies",
            outcome="silver",
            count=records_silver,
        )
        pipeline_metrics.record_composite_phase_loss(
            phase="dependencies",
            loss_kind="unwritten",
            count=max(records_extracted - records_silver, 0),
        )
        pipeline_metrics.record_composite_phase_errors(
            phase="dependencies",
            error_kind="failed",
            count=failed,
        )
        pipeline_metrics.record_composite_phase_errors(
            phase="dependencies",
            error_kind="timeout",
            count=timed_out,
        )
        pipeline_metrics.record_composite_phase_retries(
            phase="dependencies",
            retry_kind="resume",
            count=resumed,
        )
        self._record_stage_completed(
            stage=_DEPENDENCIES_STAGE_NAME,
            metrics_snapshot=build_dependency_stage_metrics(dependency_results),
        )

    def _record_enrichment_stage_completed(
        self: _CompositeRunnerControlPlaneHostProtocol,
        enrichment_results: dict[str, EnrichmentResult],
    ) -> None:
        """Append one ``stage_completed`` entry for enrichment phase."""
        pipeline_metrics = _build_pipeline_metrics(self)
        records_input = sum(
            int(result.records_input) for result in enrichment_results.values()
        )
        records_enriched = sum(
            int(result.records_enriched) for result in enrichment_results.values()
        )
        records_not_found = sum(
            int(result.records_not_found) for result in enrichment_results.values()
        )
        records_errored = sum(
            int(result.records_errored) for result in enrichment_results.values()
        )
        failed = sum(
            1 for result in enrichment_results.values() if result.status.value == "failed"
        )
        timed_out = sum(
            1 for result in enrichment_results.values() if result.status.value == "timeout"
        )
        pipeline_metrics.record_composite_phase_records(
            phase="enrichment",
            outcome="input",
            count=records_input,
        )
        pipeline_metrics.record_composite_phase_records(
            phase="enrichment",
            outcome="enriched",
            count=records_enriched,
        )
        pipeline_metrics.record_composite_phase_loss(
            phase="enrichment",
            loss_kind="not_found",
            count=records_not_found,
        )
        pipeline_metrics.record_composite_phase_errors(
            phase="enrichment",
            error_kind="record_error",
            count=records_errored,
        )
        pipeline_metrics.record_composite_phase_errors(
            phase="enrichment",
            error_kind="failed",
            count=failed,
        )
        pipeline_metrics.record_composite_phase_errors(
            phase="enrichment",
            error_kind="timeout",
            count=timed_out,
        )
        self._record_stage_completed(
            stage=_ENRICHMENT_STAGE_NAME,
            metrics_snapshot=build_enrichment_stage_metrics(enrichment_results),
        )

    def _record_merge_stage_completed(
        self: _CompositeRunnerControlPlaneHostProtocol,
        merge_result: MergeResult,
    ) -> None:
        """Append one ``stage_completed`` entry for merge phase."""
        pipeline_metrics = _build_pipeline_metrics(self)
        pipeline_metrics.record_composite_phase_records(
            phase="merge",
            outcome="merged",
            count=int(merge_result.records_merged),
        )
        pipeline_metrics.record_composite_phase_records(
            phase="merge",
            outcome="enriched",
            count=int(merge_result.records_enriched),
        )
        pipeline_metrics.record_composite_phase_records(
            phase="merge",
            outcome="fully_enriched",
            count=int(merge_result.records_fully_enriched),
        )
        pipeline_metrics.record_composite_phase_loss(
            phase="merge",
            loss_kind="partially_enriched",
            count=max(
                int(merge_result.records_merged)
                - int(merge_result.records_fully_enriched),
                0,
            ),
        )
        pipeline_metrics.record_composite_phase_loss(
            phase="merge",
            loss_kind="quarantined",
            count=len(merge_result.quarantine_payloads),
        )
        self._record_stage_completed(
            stage=_MERGE_STAGE_NAME,
            metrics_snapshot=build_merge_stage_metrics(merge_result),
        )
