"""Control-plane application ports."""

from __future__ import annotations

from dataclasses import dataclass
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


# Stable read contracts shared by control-plane recording and inspection.
ARTIFACT_DETAIL_KEYS = (
    "metadata_path",
    "artifact_kind",
    "artifact_semantics",
    "record_count",
    "total_bytes",
    "content_hash",
    "hash_algorithm",
    "execution_fingerprint",
    "input_snapshot_count",
    "input_snapshot_ids",
    "input_snapshot_content_hashes",
    "pipeline_name",
    "provider",
    "entity",
    "run_id",
    "manifest_id",
)

ARTIFACT_TRACE_ORDERED_KEYS = (
    "event_type",
    "publication_status",
    "stage",
    "artifact_id",
    "dataset_ref",
    "lineage_fragment_id",
    "artifact_path",
    *ARTIFACT_DETAIL_KEYS,
)

REPLAY_TAXONOMY_FIELDS: tuple[str, ...] = (
    "replay_capability",
    "requested_exact_replay",
    "exact_replay_support_boundary",
    "replay_family_contract",
    "replay_support_state",
    "post_capture_replayable_parent_supported",
    "post_capture_replayable_parent_boundary",
    "historical_live_run_upgrade_policy",
    "historical_live_run_upgrade_boundary",
    "historical_live_run_upgrade_reason",
    "broader_historical_exact_replay_policy",
    "broader_historical_exact_replay_boundary",
    "broader_historical_exact_replay_reason",
    "broader_historical_exact_replay_state",
    "historical_live_run_upgrade_state",
    "replay_occurrence_kind",
    "source_posture",
    "input_snapshot_missing_source_refs",
    "replay_capability_reason",
    "replay_mode",
    "continuation_mode",
    "operator_replay_mode",
    "replay_resume_rebuild_verdict",
    "replay_next_action",
    "exact_replay_eligible",
    "exact_replay_blockers",
    "replay_readiness_verdict",
    "append_mode_semantic_sinks",
    "resume_contract",
    "resume_diagnostics",
    "lineage_closure_boundary",
)


@dataclass(frozen=True, slots=True)
class HistoricalReplayRunIdentityRecord:
    """Core run identity anchors shared by historical replay inventory records."""

    manifest_id: str
    run_id: str
    pipeline_name: str
    provider: str
    entity: str
    execution_context: str


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


class RunLedgerCorrelationFieldsProtocol(Protocol):
    """Shared correlation defaults required by ledger recording and diagnostics."""

    pipeline_name: str | None
    provider: str | None
    entity: str | None
    run_type: str | None
    resolved_config_hash: str | None
    effective_config_hash: str | None
    contract_ref: str | None
    contract_version: str | None
    dq_policy_ref: str | None
    rule_bundle_version: str | None
    dq_contract_compatibility_hash: str | None
    effective_config_artifact_id: str | None


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
