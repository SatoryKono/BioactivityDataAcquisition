"""Read-only application service for bounded control-plane validation evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from bioetl.application.services.control_plane.evidence.checkpoint_validation import (
    build_checkpoint_checks,
)
from bioetl.application.services.control_plane.evidence.failure_reasons import (
    FAILURE_REASON_CATEGORIES,
    build_failure_reason_rows,
    build_unknown_failure_reason_rows,
)
from bioetl.application.services.control_plane.evidence.lineage import (
    build_lineage_checks,
)
from bioetl.application.services.control_plane.evidence.manifest_validation import (
    build_manifest_checks,
)
from bioetl.application.services.control_plane.evidence.models import (
    EvidenceCheck,
    unresolved_scope_check,
)
from bioetl.application.services.control_plane.evidence.retention import (
    ControlPlaneLifecyclePlanner,
    build_retention_checks,
    summarize_retention_artifacts,
)
from bioetl.application.services.control_plane.evidence.service_support import (
    EvidenceScope,
    ledger_entries,
    sanitized_manifest_payload_scope,
    service_payload,
)
from bioetl.domain.control_plane import ControlPlaneArtifactLifecyclePolicy
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

    def checkpoint_validation(
        self,
        *,
        scope: EvidenceScope,
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
        )

    def manifest_validation(self, *, scope: EvidenceScope) -> dict[str, object]:
        """Return manifest parsing, schema, version, and contract compatibility."""
        checks = (
            (unresolved_scope_check(scope.resolved_via),)
            if scope.manifest is None
            else build_manifest_checks(
                scope.manifest,
                self.manifest_inspector.inspect_raw_manifest(scope.manifest.manifest_id)
                if self.manifest_inspector is not None
                else None,
            )
        )
        return service_payload(
            endpoint="manifest-validation",
            scope=sanitized_manifest_payload_scope(scope, checks),
            checks=checks,
        )

    def lineage_validation(self, *, scope: EvidenceScope) -> dict[str, object]:
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
                    EvidenceCheck(
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
        run_ledger_entries = ledger_entries(self.ledger_port, scope.manifest)
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
        )

    def retention_compliance(
        self,
        *,
        scope: EvidenceScope,
        now: datetime,
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
                    EvidenceCheck(
                        "retention_policy",
                        "UNKNOWN",
                        "lifecycle_planner_unavailable",
                        "The read-only lifecycle planner is not configured.",
                    ),
                ),
            )
        plan = self.lifecycle_planner.plan(
            ControlPlaneArtifactLifecyclePolicy(
                retention_days=self.retention_days,
                now=now,
            ),
            dry_run=True,
        )
        checks, relevant_artifacts = build_retention_checks(
            manifest=scope.manifest,
            plan=plan,
        )
        return service_payload(
            endpoint="retention-compliance",
            scope=scope,
            checks=checks,
            additional_data={
                "retention_days": self.retention_days,
                "cutoff": plan.cutoff.isoformat(),
                "artifacts": summarize_retention_artifacts(relevant_artifacts),
            },
        )

    def failure_reasons(self, *, scope: EvidenceScope) -> dict[str, object]:
        """Return only fixed-category failure counts; omit raw errors/messages."""
        if scope.manifest is None:
            scope_check = unresolved_scope_check(scope.resolved_via)
            payload = service_payload(
                endpoint="failure-reasons",
                scope=scope,
                checks=(scope_check,),
                additional_data={
                    "categories": list(FAILURE_REASON_CATEGORIES),
                    "total_failure_count": None,
                },
            )
            payload["rows"] = build_unknown_failure_reason_rows(scope_check.reason)
            return payload
        if self.ledger_port is None:
            checks = (
                EvidenceCheck(
                    "ledger",
                    "UNKNOWN",
                    "run_ledger_unavailable",
                    "The run ledger is not configured for failure aggregation.",
                ),
            )
            rows = build_unknown_failure_reason_rows("run_ledger_unavailable")
            total = None
        else:
            rows, total = build_failure_reason_rows(
                ledger_entries(self.ledger_port, scope.manifest)
            )
            checks = (
                EvidenceCheck(
                    "classification",
                    "OK",
                    "failure_reasons_bounded",
                    "Failed ledger events were projected to the fixed category set.",
                ),
            )
        payload = service_payload(
            endpoint="failure-reasons",
            scope=scope,
            checks=checks,
            additional_data={
                "categories": list(FAILURE_REASON_CATEGORIES),
                "total_failure_count": total,
            },
        )
        payload["rows"] = rows
        return payload


__all__ = [
    "DEFAULT_CONTROL_PLANE_RETENTION_DAYS",
    "ControlPlaneEvidenceService",
    "EvidenceScope",
]
