"""Read-only application service for bounded control-plane validation evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import cast

from bioetl.application.observability.control_plane_evidence.checkpoint_validation import (
    build_checkpoint_checks,
)
from bioetl.application.observability.control_plane_evidence.checks import (
    EvidenceCheckResult,
    component_checks,
)
from bioetl.application.observability.control_plane_evidence.failure_reasons import (
    build_failure_reasons_payload,
)
from bioetl.application.observability.control_plane_evidence.lineage import (
    build_lineage_checks,
)
from bioetl.application.observability.control_plane_evidence.manifest_validation import (
    build_manifest_checks,
)
from bioetl.application.observability.control_plane_evidence.models import (
    _processing_status,
    unresolved_scope_check,
)
from bioetl.application.observability.control_plane_evidence.retention import (
    ArchiveVerifierProtocol,
    ControlPlaneLifecyclePlanner,
    build_retention_checks,
    serialize_resolution_issues,
    summarize_retention_artifacts,
)
from bioetl.application.observability.control_plane_evidence.service_support import (
    EvidenceScopeContext,
    ledger_entries,
    sanitized_manifest_payload_scope,
    service_payload,
)
from bioetl.domain.control_plane import (
    ControlPlaneArtifactLifecyclePlan,
    ControlPlaneArtifactLifecyclePolicy,
    RunLedgerEntry,
    RunManifest,
)
from bioetl.domain.ports import (
    LineageStorePort,
    RawRunManifestInspectionPort,
    RunLedgerPort,
)

DEFAULT_CONTROL_PLANE_RETENTION_DAYS = 90


@dataclass(slots=True)
class ControlPlaneEvidenceService:
    """Build bounded, run-scoped validation payloads from control-plane ports."""

    ledger_port: RunLedgerPort | None = None
    lineage_store: LineageStorePort | None = None
    lifecycle_planner: ControlPlaneLifecyclePlanner | None = None
    manifest_inspector: RawRunManifestInspectionPort | None = None
    retention_days: int = DEFAULT_CONTROL_PLANE_RETENTION_DAYS
    archive_verifier: ArchiveVerifierProtocol | None = None

    def trust_summary(
        self, *, scope: EvidenceScopeContext, now: datetime
    ) -> dict[str, object]:
        """Aggregate manifest, lineage and retention evidence for one exact scope."""
        # One immutable ledger view per response: no cross-request cache and no
        # repeated full ledger reads while assembling the same Trust verdict.
        snapshot = (
            ledger_entries(self.ledger_port, scope.manifest) if scope.manifest else ()
        )
        return self._trust_summary_from_snapshot(
            scope=scope, now=now, snapshot=snapshot
        )

    def successful_run_trust_summary(
        self, *, scope: EvidenceScopeContext, now: datetime
    ) -> dict[str, object] | None:
        """Validate a discovery candidate only after its terminal success is known.

        Non-success cannot satisfy latest-complete discovery, so reading its
        archives and lineage is unnecessary. Success still requires every Trust
        component; the same immutable ledger snapshot drives both decisions.
        """
        snapshot = (
            ledger_entries(self.ledger_port, scope.manifest) if scope.manifest else ()
        )
        if _processing_status(scope.manifest, snapshot) != "success":
            return None
        return self._trust_summary_from_snapshot(
            scope=scope, now=now, snapshot=snapshot
        )

    def _trust_summary_from_snapshot(
        self,
        *,
        scope: EvidenceScopeContext,
        now: datetime,
        snapshot: tuple[RunLedgerEntry, ...],
    ) -> dict[str, object]:
        components = (
            self.manifest_validation(scope=scope, ledger_snapshot=snapshot),
            self.lineage_validation(scope=scope, ledger_snapshot=snapshot),
            self.retention_compliance(scope=scope, now=now, ledger_snapshot=snapshot),
        )
        return service_payload(
            endpoint="trust-summary",
            scope=scope,
            checks=component_checks(components),
            ledger_entries=snapshot,
        )

    def checkpoint_validation(
        self,
        *,
        scope: EvidenceScopeContext,
        checkpoint: tuple[object, dict[str, object]] | None,
        evidence_source: str,
        aggregate_scope_unknown: bool,
    ) -> dict[str, object]:
        """Return explicit checkpoint parse/schema/checksum/anchor results."""
        if scope.manifest is None:
            return service_payload(
                endpoint="checkpoint-validation",
                scope=scope,
                checks=(unresolved_scope_check(scope.resolved_via),),
                additional_data={"evidence_source": evidence_source},
            )
        return service_payload(
            endpoint="checkpoint-validation",
            scope=scope,
            checks=build_checkpoint_checks(
                manifest=scope.manifest,
                checkpoint=checkpoint,
                aggregate_scope_unknown=aggregate_scope_unknown,
            ),
            additional_data={"evidence_source": evidence_source},
            ledger_entries=ledger_entries(self.ledger_port, scope.manifest),
        )

    def manifest_validation(
        self,
        *,
        scope: EvidenceScopeContext,
        ledger_snapshot: tuple[RunLedgerEntry, ...] | None = None,
    ) -> dict[str, object]:
        """Return manifest parsing, schema, version, and contract compatibility."""
        raw_inspection = None
        if scope.manifest is not None and self.manifest_inspector is not None:
            raw_inspection = self.manifest_inspector.inspect_raw_manifest(
                scope.manifest.manifest_id
            )
        checks = (
            (unresolved_scope_check(scope.resolved_via),)
            if scope.manifest is None
            else build_manifest_checks(
                scope.manifest,
                raw_inspection,
            )
        )
        return service_payload(
            endpoint="manifest-validation",
            scope=sanitized_manifest_payload_scope(scope, checks),
            checks=checks,
            ledger_entries=(
                (
                    ledger_snapshot
                    if ledger_snapshot is not None
                    else ledger_entries(self.ledger_port, scope.manifest)
                )
                if scope.manifest is not None
                else ()
            ),
        )

    def lineage_validation(
        self,
        *,
        scope: EvidenceScopeContext,
        ledger_snapshot: tuple[RunLedgerEntry, ...] | None = None,
    ) -> dict[str, object]:
        """Return lineage closure, identity, cycle, and persistence validation."""
        if scope.manifest is None:
            return service_payload(
                endpoint="lineage-validation",
                scope=scope,
                checks=(unresolved_scope_check(scope.resolved_via),),
            )
        if self.lineage_store is None:
            return service_payload(
                endpoint="lineage-validation",
                scope=scope,
                checks=(
                    EvidenceCheckResult(
                        "lineage_store",
                        "UNKNOWN",
                        "lineage_store_unavailable",
                        "The read-only lineage store is not configured.",
                    ),
                ),
            )
        fragments = tuple(
            self.lineage_store.list_by_manifest_id(scope.manifest.manifest_id)
        )
        if not fragments:
            fragments = tuple(self.lineage_store.list_by_run_id(scope.manifest.run_id))
        run_ledger_entries = (
            ledger_snapshot
            if ledger_snapshot is not None
            else ledger_entries(self.ledger_port, scope.manifest)
        )
        return service_payload(
            endpoint="lineage-validation",
            scope=scope,
            checks=build_lineage_checks(
                manifest=scope.manifest,
                fragments=fragments,
                ledger_entries=run_ledger_entries,
            ),
            additional_data={
                "fragment_count": len(fragments),
                "edge_count": sum(len(fragment.edges) for fragment in fragments),
                "node_count": len(
                    {node.node_id for fragment in fragments for node in fragment.nodes}
                ),
            },
            ledger_entries=run_ledger_entries,
        )

    def retention_compliance(
        self,
        *,
        scope: EvidenceScopeContext,
        now: datetime,
        ledger_snapshot: tuple[RunLedgerEntry, ...] | None = None,
    ) -> dict[str, object]:
        """Evaluate default retention and evidence-floor policy in dry-run mode."""
        if scope.manifest is None:
            return service_payload(
                endpoint="retention-compliance",
                scope=scope,
                checks=(unresolved_scope_check(scope.resolved_via),),
            )
        if self.lifecycle_planner is None:
            return service_payload(
                endpoint="retention-compliance",
                scope=scope,
                checks=(
                    EvidenceCheckResult(
                        "retention_policy",
                        "UNKNOWN",
                        "lifecycle_planner_unavailable",
                        "The read-only lifecycle planner is not configured.",
                    ),
                ),
                ledger_entries=(
                    ledger_snapshot
                    if ledger_snapshot is not None
                    else ledger_entries(self.ledger_port, scope.manifest)
                ),
            )
        plan = self._bounded_retention_plan(scope.manifest, now)
        checks, relevant_artifacts = build_retention_checks(
            manifest=scope.manifest,
            plan=plan,
            archive_verifier=self.archive_verifier,
        )
        return service_payload(
            endpoint="retention-compliance",
            scope=scope,
            checks=checks,
            additional_data={
                "retention_days": self.retention_days,
                "cutoff": plan.cutoff.isoformat(),
                "artifacts": summarize_retention_artifacts(relevant_artifacts),
                "retention_plan_scope": "manifest",
                "resolution_issues": serialize_resolution_issues(plan),
            },
            ledger_entries=(
                ledger_snapshot
                if ledger_snapshot is not None
                else ledger_entries(self.ledger_port, scope.manifest)
            ),
        )

    def _bounded_retention_plan(
        self,
        manifest: RunManifest,
        now: datetime,
    ) -> ControlPlaneArtifactLifecyclePlan:
        planner = self.lifecycle_planner
        assert planner is not None
        plan_for_manifest = getattr(planner, "plan_for_manifest", None)
        if callable(plan_for_manifest):
            return cast(
                ControlPlaneArtifactLifecyclePlan,
                plan_for_manifest(
                    ControlPlaneArtifactLifecyclePolicy(
                        retention_days=self.retention_days,
                        now=now,
                    ),
                    manifest=manifest,
                    dry_run=True,
                ),
            )
        return planner.plan(
            ControlPlaneArtifactLifecyclePolicy(
                retention_days=self.retention_days,
                now=now,
            ),
            dry_run=True,
        )

    def failure_reasons(self, *, scope: EvidenceScopeContext) -> dict[str, object]:
        """Return only fixed-category failure counts; omit raw errors/messages."""
        return build_failure_reasons_payload(scope=scope, ledger_port=self.ledger_port)


__all__ = [
    "DEFAULT_CONTROL_PLANE_RETENTION_DAYS",
    "ControlPlaneEvidenceService",
]
