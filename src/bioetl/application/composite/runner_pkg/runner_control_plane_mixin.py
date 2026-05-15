"""Thin control-plane mixins delegating composite runner events to support seams."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.application.composite.runner_pkg.runner_control_plane_support import (
    CompositeRunnerControlPlaneHostProtocol,
    record_dependencies_stage_completed,
    record_dependencies_stage_started,
    record_enrichment_stage_completed,
    record_enrichment_stage_started,
    record_merge_stage_completed,
    record_merge_stage_started,
    record_run_failed,
    record_run_finished,
    record_run_metrics_event,
    record_run_shutdown,
    record_run_started,
    record_seed_stage_completed,
    record_seed_stage_started,
    record_stage_completed,
    record_stage_started,
    record_with_ledger_service,
)

if TYPE_CHECKING:
    from bioetl.application.composite.runtime_models import CompositeExecutionContext
    from bioetl.application.services.control_plane.run_ledger_service import (
        RunLedgerService,
    )
    from bioetl.domain.composite.result import (
        DependencyResult,
        EnrichmentResult,
        MergeResult,
        SeedResult,
    )

__all__ = ["CompositeRunnerControlPlaneMixin"]


class _CompositeRunnerLedgerLifecycleMixin:
    """Ledger lifecycle helpers shared by composite runner control-plane flows."""

    _run_ledger_service: RunLedgerService | None
    _manifest_id: str | None

    @property
    def manifest_id(self: CompositeRunnerControlPlaneHostProtocol) -> str | None:
        """Return control-plane manifest identifier linked to this run."""
        return self._manifest_id

    def _record_with_ledger_service(
        self: CompositeRunnerControlPlaneHostProtocol,
        recorder: Callable[[RunLedgerService], object],
    ) -> None:
        """Run one ledger write only when control-plane wiring is attached."""
        record_with_ledger_service(self, recorder)

    def _record_run_metrics_event(
        self: CompositeRunnerControlPlaneHostProtocol,
        *,
        metrics_snapshot: dict[str, int],
        recorder: Callable[[RunLedgerService, dict[str, int]], object],
    ) -> None:
        """Emit one run-level metrics-backed ledger event when attached."""
        record_run_metrics_event(
            self,
            metrics_snapshot=metrics_snapshot,
            recorder=recorder,
        )

    def _record_stage_started(
        self: CompositeRunnerControlPlaneHostProtocol,
        *,
        stage: str,
        details: dict[str, object] | None = None,
    ) -> None:
        """Append one composite ``stage_started`` entry when ledger is attached."""
        record_stage_started(self, stage=stage, details=details)

    def _record_stage_completed(
        self: CompositeRunnerControlPlaneHostProtocol,
        *,
        stage: str,
        metrics_snapshot: dict[str, int],
    ) -> None:
        """Append one composite ``stage_completed`` entry when ledger is attached."""
        record_stage_completed(
            self,
            stage=stage,
            metrics_snapshot=metrics_snapshot,
        )

    def _record_run_started(self: CompositeRunnerControlPlaneHostProtocol) -> None:
        """Append ``run_started`` when control-plane ledger is attached."""
        record_run_started(self)

    def _record_run_failed(
        self: CompositeRunnerControlPlaneHostProtocol,
        error: Exception,
    ) -> None:
        """Append ``run_failed`` when control-plane ledger is attached."""
        record_run_failed(self, error)

    def _record_run_shutdown(self: CompositeRunnerControlPlaneHostProtocol) -> None:
        """Append ``run_shutdown`` when control-plane ledger is attached."""
        record_run_shutdown(self)

    def _record_seed_stage_started(self: CompositeRunnerControlPlaneHostProtocol) -> None:
        """Append one ``stage_started`` entry for seed phase."""
        record_seed_stage_started(self)

    def _record_dependencies_stage_started(
        self: CompositeRunnerControlPlaneHostProtocol,
        dependency_pipeline_names: list[str],
    ) -> None:
        """Append one ``stage_started`` entry for dependencies phase."""
        record_dependencies_stage_started(self, dependency_pipeline_names)

    def _record_enrichment_stage_started(
        self: CompositeRunnerControlPlaneHostProtocol,
        enricher_names: list[str],
    ) -> None:
        """Append one ``stage_started`` entry for enrichment phase."""
        record_enrichment_stage_started(self, enricher_names)

    def _record_merge_stage_started(self: CompositeRunnerControlPlaneHostProtocol) -> None:
        """Append one ``stage_started`` entry for merge phase."""
        record_merge_stage_started(self)


class _CompositeRunnerPhaseCompletionMixin:
    """Composite stage-completion helpers and metrics emission."""

    def _record_run_finished(
        self: CompositeRunnerControlPlaneHostProtocol,
        artifacts: CompositeExecutionContext,
    ) -> None:
        """Append ``run_finished`` when control-plane ledger is attached."""
        record_run_finished(self, artifacts)

    def _record_seed_stage_completed(
        self: CompositeRunnerControlPlaneHostProtocol,
        seed_result: SeedResult,
    ) -> None:
        """Append one ``stage_completed`` entry for seed phase."""
        record_seed_stage_completed(self, seed_result)

    def _record_dependencies_stage_completed(
        self: CompositeRunnerControlPlaneHostProtocol,
        dependency_results: dict[str, DependencyResult],
    ) -> None:
        """Append one ``stage_completed`` entry for dependencies phase."""
        record_dependencies_stage_completed(self, dependency_results)

    def _record_enrichment_stage_completed(
        self: CompositeRunnerControlPlaneHostProtocol,
        enrichment_results: dict[str, EnrichmentResult],
    ) -> None:
        """Append one ``stage_completed`` entry for enrichment phase."""
        record_enrichment_stage_completed(self, enrichment_results)

    def _record_merge_stage_completed(
        self: CompositeRunnerControlPlaneHostProtocol,
        merge_result: MergeResult,
    ) -> None:
        """Append one ``stage_completed`` entry for merge phase."""
        record_merge_stage_completed(self, merge_result)


class CompositeRunnerControlPlaneMixin(
    _CompositeRunnerPhaseCompletionMixin,
    _CompositeRunnerLedgerLifecycleMixin,
):
    """Mixin that emits composite lifecycle events into RunLedgerService."""
