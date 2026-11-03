"""Control-plane application ports."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
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
class EvidenceReadContext(Protocol):
    """Read-only control-plane view bound to one data root."""

    @property
    def data_root(self) -> Path:
        """Absolute data root selected for this resolve."""
        ...

    def get_manifest_by_run_id(self, run_id: object) -> object | None:
        """Load a manifest by run id from the bound root, or ``None``.

        Args:
            run_id: Identifier of the run whose manifest is requested.
        """
        ...

    def get_workflow_manifest_by_run_id(self, run_id: object) -> object | None:
        """Load a workflow manifest by run id from the bound root, or ``None``.

        Args:
            run_id: Identifier of the run whose workflow manifest is requested.
        """
        ...

    def verify_replay_objects(self, manifest: object) -> Mapping[str, bool]:
        """Re-validate saved config, lock and Bronze bytes for ``manifest``.

        Args:
            manifest: Saved manifest containing the replay object references.
        """
        ...


@runtime_checkable
class EvidenceReadContextOpenerProtocol(Protocol):
    """Open read-only stores beneath a trusted data-root alias."""

    def open(
        self,
        data_root: Path,
        *,
        trusted_alias_base: Path,
    ) -> EvidenceReadContext:
        """Open read-only ports after validating path containment.

        Args:
            data_root: Data root selected for the read-only operation.
            trusted_alias_base: Trusted base used to validate alias containment.
        """
        ...


@runtime_checkable
class ControlPlaneArtifactLifecycleStoreProtocol(Protocol):
    """Plan/apply artifact lifecycle for a selected run."""

    def plan(
        self,
        policy: ControlPlaneArtifactLifecyclePolicy,
        *,
        dry_run: bool,
    ) -> ControlPlaneArtifactLifecyclePlan:
        """Plan artifact lifecycle actions for the selected run."""
        ...

    def apply(
        self,
        plan: ControlPlaneArtifactLifecyclePlan,
    ) -> ControlPlaneArtifactLifecycleApplyResult:
        """Apply a previously built artifact lifecycle plan."""
        ...


class ForensicRunDiffServiceProtocol(Protocol):
    """Compare retained runs through the control-plane forensic service."""

    def compare(
        self,
        left_identifier: str,
        right_identifier: str,
    ) -> ForensicRunDiffResult:
        """Compare two retained runs through forensic diff."""
        ...


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
    ) -> HistoricalReplayClosureReportRecord:
        """Build a historical-replay closure report."""
        ...


class HistoricalReplayCorpusServiceProtocol(Protocol):
    """Inspect and certify the retained historical replay corpus."""

    def build_certifiability_inventory(
        self,
    ) -> HistoricalReplayCertifiabilityInventory:
        """Build certifiability inventory for the retained corpus."""
        ...

    def certify_retained_corpus(
        self,
        *,
        specs: tuple[HistoricalReplayBulkCertificationSpec, ...],
    ) -> HistoricalReplayBulkCertificationResult:
        """Certify retained historical-replay corpus records."""
        ...


class HistoricalReplayUniverseServiceProtocol(Protocol):
    """Build closure evidence for the full historical replay universe."""

    def build_universe_closure_report(
        self,
        *,
        external_records: tuple[HistoricalReplayUniverseExternalRecord, ...] = (),
    ) -> HistoricalReplayUniverseClosureReportRecord:
        """Build closure evidence for the full historical-replay universe."""
        ...


class LineageInspectionServiceProtocol(Protocol):
    """Inspect persisted lineage from operator-facing interfaces."""

    def show_fragment(
        self,
        fragment_id: str,
        *,
        semantic: bool = False,
    ) -> LineageFragmentInspectionResult:
        """Show one persisted lineage fragment."""
        ...

    def trace(self, dataset_ref: str) -> LineageTraceResult:
        """Trace lineage for a dataset reference."""
        ...

    def explain_run(self, identifier: str) -> LineageRunExplanationResult:
        """Explain persisted lineage for one run identifier."""
        ...


class RunManifestInspectionServiceProtocol(Protocol):
    """Inspect, compare, and verify persisted run manifests."""

    def show(self, identifier: str) -> RunManifestInspectionResult:
        """Show a persisted run manifest."""
        ...

    def diff(
        self,
        left_identifier: str,
        right_identifier: str,
    ) -> RunManifestDiffResult:
        """Diff two persisted run manifests."""
        ...

    def verify(
        self,
        left_identifier: str,
        right_identifier: str,
    ) -> RunManifestVerifyResult:
        """Verify two persisted run manifests against each other."""
        ...


class WorkflowInspectionServiceProtocol(Protocol):
    """Inspect persisted workflow execution state."""

    def inspect_latest(self, workflow_name: str) -> WorkflowInspectionResult | None:
        """Inspect the latest execution of a named workflow."""
        ...

    def inspect_run_id(
        self,
        workflow_run_id: str,
    ) -> WorkflowInspectionResult | None:
        """Inspect a workflow execution by run id."""
        ...
