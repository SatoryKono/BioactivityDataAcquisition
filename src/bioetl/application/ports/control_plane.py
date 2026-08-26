"""Control-plane application ports."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.forensic_diff_service import (
        ForensicRunDiffResult,
    )
    from bioetl.application.services.control_plane.manifest.inspection_models import (
        RunManifestDiffResult,
        RunManifestInspectionResult,
        RunManifestVerifyResult,
    )
    from bioetl.application.services.control_plane.replay.historical_closure_models import (
        HistoricalReplayClaimScopeMode,
        HistoricalReplayClosureReportRecord,
        HistoricalReplayResidualDispositionRecord,
    )
    from bioetl.application.services.control_plane.replay.historical_corpus_models import (
        HistoricalReplayBulkCertificationResult,
        HistoricalReplayBulkCertificationSpec,
        HistoricalReplayCertifiabilityInventory,
    )
    from bioetl.application.services.control_plane.replay.historical_identity_models import (
        HistoricalReplayUniverseExternalRecord,
    )
    from bioetl.application.services.control_plane.replay.historical_universe_service import (
        HistoricalReplayUniverseClosureReportRecord,
    )
    from bioetl.application.services.control_plane.workflow.inspection_service import (
        WorkflowInspectionResult,
    )
    from bioetl.application.services.lineage.lineage_inspection_results import (
        LineageFragmentInspectionResult,
        LineageRunExplanationResult,
        LineageTraceResult,
    )
    from bioetl.domain.control_plane import (
        ControlPlaneArtifactLifecycleApplyResult,
        ControlPlaneArtifactLifecyclePlan,
        ControlPlaneArtifactLifecyclePolicy,
    )


@runtime_checkable
class ControlPlaneArtifactLifecycleStoreProtocol(Protocol):
    """Plan/apply artifact lifecycle for a selected run."""

    def plan(
        self,
        policy: ControlPlaneArtifactLifecyclePolicy,
        *,
        dry_run: bool,
    ) -> ControlPlaneArtifactLifecyclePlan: ...

    def apply(
        self,
        plan: ControlPlaneArtifactLifecyclePlan,
    ) -> ControlPlaneArtifactLifecycleApplyResult: ...


class ForensicRunDiffServiceProtocol(Protocol):
    """Compare retained runs through the control-plane forensic service."""

    def compare(
        self,
        left_identifier: str,
        right_identifier: str,
    ) -> ForensicRunDiffResult: ...


class HistoricalReplayClosureServiceProtocol(Protocol):
    """Build retained-corpus historical replay closure reports."""

    def build_closure_report(
        self,
        *,
        residual_dispositions: tuple[
            HistoricalReplayResidualDispositionRecord, ...
        ] = (),
        claim_scope_mode: HistoricalReplayClaimScopeMode = (
            "all_retained_historical_runs"
        ),
    ) -> HistoricalReplayClosureReportRecord: ...


class HistoricalReplayCorpusServiceProtocol(Protocol):
    """Inspect and certify the retained historical replay corpus."""

    def build_certifiability_inventory(
        self,
    ) -> HistoricalReplayCertifiabilityInventory: ...

    def certify_retained_corpus(
        self,
        *,
        specs: tuple[HistoricalReplayBulkCertificationSpec, ...],
    ) -> HistoricalReplayBulkCertificationResult: ...


class HistoricalReplayUniverseServiceProtocol(Protocol):
    """Build closure evidence for the full historical replay universe."""

    def build_universe_closure_report(
        self,
        *,
        external_records: tuple[HistoricalReplayUniverseExternalRecord, ...] = (),
    ) -> HistoricalReplayUniverseClosureReportRecord: ...


class LineageInspectionServiceProtocol(Protocol):
    """Inspect persisted lineage from operator-facing interfaces."""

    def show_fragment(
        self,
        fragment_id: str,
        *,
        semantic: bool = False,
    ) -> LineageFragmentInspectionResult: ...

    def trace(self, dataset_ref: str) -> LineageTraceResult: ...

    def explain_run(self, identifier: str) -> LineageRunExplanationResult: ...


class RunManifestInspectionServiceProtocol(Protocol):
    """Inspect, compare, and verify persisted run manifests."""

    def show(self, identifier: str) -> RunManifestInspectionResult: ...

    def diff(
        self,
        left_identifier: str,
        right_identifier: str,
    ) -> RunManifestDiffResult: ...

    def verify(
        self,
        left_identifier: str,
        right_identifier: str,
    ) -> RunManifestVerifyResult: ...


class WorkflowInspectionServiceProtocol(Protocol):
    """Inspect persisted workflow execution state."""

    def inspect_latest(self, workflow_name: str) -> WorkflowInspectionResult | None: ...

    def inspect_run_id(
        self,
        workflow_run_id: str,
    ) -> WorkflowInspectionResult | None: ...
