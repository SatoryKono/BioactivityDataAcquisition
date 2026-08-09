"""Read-only application service for bounded control-plane validation evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from bioetl.application.services.control_plane.evidence.checkpoint_validation import (
    build_checkpoint_checks,
)
from bioetl.application.services.control_plane.evidence.manifest_validation import (
    build_manifest_checks,
)
from bioetl.application.services.control_plane.evidence.failure_reasons import (
    FAILURE_REASON_CATEGORIES,
    build_failure_reason_rows,
)
from bioetl.application.services.control_plane.evidence.lineage import (
    build_lineage_checks,
)
from bioetl.application.services.control_plane.evidence.models import (
    EvidenceCheck,
    evidence_payload,
    unresolved_scope_check,
)
from bioetl.application.services.control_plane.evidence.retention import (
    ControlPlaneLifecyclePlanner,
    build_retention_checks,
    summarize_retention_artifacts,
)
from bioetl.domain.control_plane import (
    ControlPlaneArtifactLifecyclePolicy,
    RunLedgerEntry,
    RunManifest,
)
from bioetl.domain.ports import LineageStorePort, RunLedgerPort

DEFAULT_CONTROL_PLANE_RETENTION_DAYS = 90


@dataclass(frozen=True, slots=True)
class EvidenceScope:
    """Resolved selector context passed from the HTTP interface."""

    requested_pipeline: str
    selected_run_id: str | None
    selected_run_types: tuple[str, ...]
    resolved_via: str
    manifest: RunManifest | None


@dataclass(slots=True)
class ControlPlaneEvidenceService:
    """Build bounded, run-scoped validation payloads from control-plane ports."""

    ledger_port: RunLedgerPort | None = None
    lineage_store: LineageStorePort | None = None
    lifecycle_planner: ControlPlaneLifecyclePlanner | None = None
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
        return self._payload(
            endpoint="checkpoint-validation",
            scope=scope,
            checks=build_checkpoint_checks(
                manifest=scope.manifest,
                checkpoint=checkpoint,
                aggregate_scope_unknown=aggregate_scope_unknown,
            ),
            extra={"evidence_source": evidence_source},
        )

    def manifest_validation(self, *, scope: EvidenceScope) -> dict[str, object]:
        """Return manifest parsing, schema, version, and contract compatibility."""
        checks = (
            (unresolved_scope_check(scope.resolved_via),)
            if scope.manifest is None
            else build_manifest_checks(scope.manifest)
        )
        return self._payload(
            endpoint="manifest-validation",
            scope=scope,
            checks=checks,
        )

    def lineage_validation(self, *, scope: EvidenceScope) -> dict[str, object]:
        """Return lineage closure, identity, cycle, and persistence validation."""
        if scope.manifest is None:
            return self._payload(
                endpoint="lineage-validation",
                scope=scope,
                checks=(unresolved_scope_check(scope.resolved_via),),
            )
        if self.lineage_store is None:
            return self._payload(
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
            fragments = tuple(
                self.lineage_store.list_by_run_id(scope.manifest.run_id)
            )
        ledger_entries = self._ledger_entries(scope.manifest)
        return self._payload(
            endpoint="lineage-validation",
            scope=scope,
            checks=build_lineage_checks(
                manifest=scope.manifest,
                fragments=fragments,
                ledger_entries=ledger_entries,
            ),
            extra={
                "fragment_count": len(fragments),
                "edge_count": sum(len(fragment.edges) for fragment in fragments),
                "node_count": len(
                    {
                        node.node_id
                        for fragment in fragments
                        for node in fragment.nodes
                    }
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
            return self._payload(
                endpoint="retention-compliance",
                scope=scope,
                checks=(unresolved_scope_check(scope.resolved_via),),
            )
        if self.lifecycle_planner is None:
            return self._payload(
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
        return self._payload(
            endpoint="retention-compliance",
            scope=scope,
            checks=checks,
            extra={
                "retention_days": self.retention_days,
                "cutoff": plan.cutoff.isoformat(),
                "artifacts": summarize_retention_artifacts(relevant_artifacts),
            },
        )

    def failure_reasons(self, *, scope: EvidenceScope) -> dict[str, object]:
        """Return only fixed-category failure counts; omit raw errors/messages."""
        if scope.manifest is None:
            payload = self._payload(
                endpoint="failure-reasons",
                scope=scope,
                checks=(unresolved_scope_check(scope.resolved_via),),
                extra={
                    "categories": list(FAILURE_REASON_CATEGORIES),
                    "total_failure_count": 0,
                },
            )
            payload["rows"] = [
                {"category": category, "count": 0}
                for category in FAILURE_REASON_CATEGORIES
            ]
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
            rows = [
                {"category": category, "count": 0}
                for category in FAILURE_REASON_CATEGORIES
            ]
            total = 0
        else:
            rows, total = build_failure_reason_rows(
                self._ledger_entries(scope.manifest)
            )
            checks = (
                EvidenceCheck(
                    "classification",
                    "OK",
                    "failure_reasons_bounded",
                    "Failed ledger events were projected to the fixed category set.",
                ),
            )
        payload = self._payload(
            endpoint="failure-reasons",
            scope=scope,
            checks=checks,
            extra={
                "categories": list(FAILURE_REASON_CATEGORIES),
                "total_failure_count": total,
            },
        )
        payload["rows"] = rows
        return payload

    def source_error(
        self,
        *,
        endpoint: str,
        scope: EvidenceScope,
        reason: str,
        check: str,
    ) -> dict[str, object]:
        """Return a stable source-read failure without leaking raw exception text."""
        return self._payload(
            endpoint=endpoint,
            scope=scope,
            checks=(
                EvidenceCheck(
                    check,
                    "ERROR",
                    reason,
                    "Persisted control-plane evidence could not be read or parsed.",
                ),
            ),
        )

    def _ledger_entries(
        self,
        manifest: RunManifest,
    ) -> tuple[RunLedgerEntry, ...]:
        if self.ledger_port is None:
            return ()
        return tuple(self.ledger_port.list_entries(manifest.manifest_id))

    @staticmethod
    def _payload(
        *,
        endpoint: str,
        scope: EvidenceScope,
        checks: tuple[EvidenceCheck, ...],
        extra: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return evidence_payload(
            endpoint=endpoint,
            checks=checks,
            requested_pipeline=scope.requested_pipeline,
            selected_run_id=scope.selected_run_id,
            selected_run_types=scope.selected_run_types,
            resolved_via=scope.resolved_via,
            manifest=scope.manifest,
            extra=extra,
        )


__all__ = [
    "DEFAULT_CONTROL_PLANE_RETENTION_DAYS",
    "ControlPlaneEvidenceService",
    "EvidenceScope",
]
