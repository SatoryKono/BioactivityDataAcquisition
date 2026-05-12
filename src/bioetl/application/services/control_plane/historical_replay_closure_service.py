"""Closure reporting and global claim gating for historical replay."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json

from bioetl.application.services.control_plane.historical_replay_corpus_service import (
    HistoricalReplayCertifiabilityInventory,
    HistoricalReplayCertifiabilityRecord,
    HistoricalReplayCorpusService,
)

__all__ = [
    "HistoricalReplayClosureReport",
    "HistoricalReplayClosureService",
    "HistoricalReplayResidualDisposition",
]

_FULLY_CLOSED_STATUSES = frozenset({"already_certified", "already_replayable"})
_RESIDUAL_BLOCKED_STATUSES = frozenset(
    {
        "awaiting_source_snapshot_certification",
        "awaiting_certified_source_lineage",
        "needs_operator_review",
        "outside_certified_historical_scope",
    }
)
_RESOLUTION_DISPOSITIONS = frozenset(
    {
        "reconstruct_immutable_evidence",
        "expand_retention_and_publish_evidence",
        "certify_upstream_source_lineage",
        "irrecoverable_missing_immutable_evidence",
        "outside_universal_claim_scope",
        "manual_review_required",
    }
)


@dataclass(frozen=True, slots=True)
class HistoricalReplayResidualDisposition:
    """Explicit disposition for one residual historical replay blocker."""

    manifest_id: str
    disposition: str
    rationale: str
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.disposition not in _RESOLUTION_DISPOSITIONS:
            raise ValueError(
                "Unsupported historical replay residual disposition: "
                f"{self.disposition!r}"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "manifest_id": self.manifest_id,
            "disposition": self.disposition,
            "rationale": self.rationale,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class HistoricalReplayClosureReport:
    """Persistable closure report for retained historical replay state."""

    generated_at: datetime
    report_id: str
    inventory: HistoricalReplayCertifiabilityInventory
    residual_dispositions: tuple[HistoricalReplayResidualDisposition, ...]
    suggested_resolution_queue: tuple[dict[str, object], ...]
    closure_verdict: str
    closure_reason: str
    global_universal_historical_replay_claim: dict[str, object]
    retained_corpus_claim: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "generated_at": self.generated_at.astimezone(UTC).isoformat(),
            "report_id": self.report_id,
            "inventory": self.inventory.to_dict(),
            "residual_dispositions": [
                disposition.to_dict() for disposition in self.residual_dispositions
            ],
            "suggested_resolution_queue": list(self.suggested_resolution_queue),
            "closure_verdict": self.closure_verdict,
            "closure_reason": self.closure_reason,
            "global_universal_historical_replay_claim": (
                self.global_universal_historical_replay_claim
            ),
            "retained_corpus_claim": self.retained_corpus_claim,
        }


@dataclass(slots=True)
class HistoricalReplayClosureService:
    """Build closure artifacts and claim-gate verdicts for retained corpora."""

    corpus_service: HistoricalReplayCorpusService

    def build_closure_report(
        self,
        *,
        residual_dispositions: tuple[HistoricalReplayResidualDisposition, ...] = (),
    ) -> HistoricalReplayClosureReport:
        """Build one deterministic retained-corpus closure report."""
        inventory = self.corpus_service.build_certifiability_inventory()
        blocked_records = tuple(
            record
            for record in inventory.records
            if record.certification_status in _RESIDUAL_BLOCKED_STATUSES
        )
        disposition_map = self._validate_residual_dispositions(
            blocked_records=blocked_records,
            residual_dispositions=residual_dispositions,
        )
        unresolved_records = tuple(
            record
            for record in blocked_records
            if record.manifest_id not in disposition_map
        )
        suggested_resolution_queue = tuple(
            self._build_suggested_resolution(record) for record in blocked_records
        )
        closure_verdict, closure_reason = self._resolve_closure_verdict(
            inventory=inventory,
            unresolved_records=unresolved_records,
            disposition_map=disposition_map,
        )
        global_claim = self._build_global_claim_gate(
            inventory=inventory,
            unresolved_records=unresolved_records,
            disposition_map=disposition_map,
        )
        retained_corpus_claim = self._build_retained_corpus_claim(
            inventory=inventory,
            unresolved_records=unresolved_records,
        )
        generated_at = datetime.now(tz=UTC)
        report_id = self._build_report_id(
            inventory=inventory,
            residual_dispositions=residual_dispositions,
            closure_verdict=closure_verdict,
            closure_reason=closure_reason,
            global_claim=global_claim,
            retained_corpus_claim=retained_corpus_claim,
        )
        return HistoricalReplayClosureReport(
            generated_at=generated_at,
            report_id=report_id,
            inventory=inventory,
            residual_dispositions=tuple(
                sorted(
                    residual_dispositions,
                    key=lambda item: (item.manifest_id, item.disposition),
                )
            ),
            suggested_resolution_queue=suggested_resolution_queue,
            closure_verdict=closure_verdict,
            closure_reason=closure_reason,
            global_universal_historical_replay_claim=global_claim,
            retained_corpus_claim=retained_corpus_claim,
        )

    def _validate_residual_dispositions(
        self,
        *,
        blocked_records: tuple[HistoricalReplayCertifiabilityRecord, ...],
        residual_dispositions: tuple[HistoricalReplayResidualDisposition, ...],
    ) -> dict[str, HistoricalReplayResidualDisposition]:
        blocked_ids = {record.manifest_id for record in blocked_records}
        disposition_map: dict[str, HistoricalReplayResidualDisposition] = {}
        for disposition in residual_dispositions:
            if disposition.manifest_id not in blocked_ids:
                raise ValueError(
                    "Historical replay residual disposition references a manifest "
                    f"that is not currently blocked: {disposition.manifest_id!r}"
                )
            if disposition.manifest_id in disposition_map:
                raise ValueError(
                    "Duplicate historical replay residual disposition for manifest "
                    f"{disposition.manifest_id!r}"
                )
            disposition_map[disposition.manifest_id] = disposition
        return disposition_map

    def _resolve_closure_verdict(
        self,
        *,
        inventory: HistoricalReplayCertifiabilityInventory,
        unresolved_records: tuple[HistoricalReplayCertifiabilityRecord, ...],
        disposition_map: dict[str, HistoricalReplayResidualDisposition],
    ) -> tuple[str, str]:
        if (
            inventory.certified_count + inventory.replayable_count
            == inventory.manifest_count
            and inventory.unsupported_count == 0
        ):
            return (
                "fully_closed",
                "all_retained_historical_runs_are_already_replayable_or_certified",
            )
        if unresolved_records:
            return (
                "residual_disposition_required",
                "blocked_historical_runs_require_explicit_resolution_disposition",
            )
        if any(
            disposition.disposition == "irrecoverable_missing_immutable_evidence"
            for disposition in disposition_map.values()
        ):
            return (
                "residual_irrecoverable_subset_present",
                "some_historical_runs_remain_irrecoverable_without_trustworthy_immutable_evidence",
            )
        if inventory.unsupported_count:
            return (
                "outside_supported_scope_present",
                "some_retained_runs_remain_outside_the_current_supported_historical_replay_scope",
            )
        return (
            "residual_resolution_program_in_progress",
            "all_remaining_blocked_runs_have_explicit_resolution_tracks_but_not_yet_closed",
        )

    def _build_global_claim_gate(
        self,
        *,
        inventory: HistoricalReplayCertifiabilityInventory,
        unresolved_records: tuple[HistoricalReplayCertifiabilityRecord, ...],
        disposition_map: dict[str, HistoricalReplayResidualDisposition],
    ) -> dict[str, object]:
        claimed = (
            inventory.manifest_count > 0
            and inventory.certified_count + inventory.replayable_count
            == inventory.manifest_count
            and inventory.unsupported_count == 0
            and not unresolved_records
            and not any(
                disposition.disposition == "irrecoverable_missing_immutable_evidence"
                for disposition in disposition_map.values()
            )
        )
        if claimed:
            reason = (
                "all_retained_historical_runs_have_exact_replay_evidence_or_certified_parent_state"
            )
        elif unresolved_records:
            reason = (
                "residual_historical_runs_lack_explicit_resolution_disposition"
            )
        elif any(
            disposition.disposition == "irrecoverable_missing_immutable_evidence"
            for disposition in disposition_map.values()
        ):
            reason = "irrecoverable_legacy_runs_block_universal_historical_claim"
        elif inventory.unsupported_count:
            reason = "some_retained_runs_remain_outside_supported_historical_scope"
        else:
            reason = "historical_replay_closure_program_not_yet_completed"
        return {
            "claimed": claimed,
            "verdict": "claim_supported" if claimed else "claim_blocked",
            "reason": reason,
            "scope": "all_retained_historical_runs",
            "blocked_manifest_ids": [
                record.manifest_id for record in unresolved_records
            ],
        }

    def _build_retained_corpus_claim(
        self,
        *,
        inventory: HistoricalReplayCertifiabilityInventory,
        unresolved_records: tuple[HistoricalReplayCertifiabilityRecord, ...],
    ) -> dict[str, object]:
        claimed = (
            inventory.remaining_uncertified_count == 0
            and inventory.unsupported_count == 0
            and not unresolved_records
        )
        return {
            "claimed": claimed,
            "verdict": "claim_supported" if claimed else "claim_blocked",
            "reason": (
                "retained_corpus_has_no_remaining_uncertified_or_out_of_scope_runs"
                if claimed
                else "retained_corpus_still_contains_blocked_or_out_of_scope_runs"
            ),
            "scope": "retained_control_plane_corpus",
        }

    def _build_suggested_resolution(
        self, record: HistoricalReplayCertifiabilityRecord
    ) -> dict[str, object]:
        suggested = self._suggested_disposition(record)
        return {
            "manifest_id": record.manifest_id,
            "run_id": record.run_id,
            "certification_status": record.certification_status,
            "suggested_disposition": suggested,
            "blocking_reasons": list(record.blocking_reasons),
        }

    @staticmethod
    def _suggested_disposition(
        record: HistoricalReplayCertifiabilityRecord,
    ) -> str:
        if record.certification_status == "awaiting_source_snapshot_certification":
            return "reconstruct_immutable_evidence"
        if record.certification_status == "awaiting_certified_source_lineage":
            return "certify_upstream_source_lineage"
        if record.certification_status == "outside_certified_historical_scope":
            return "outside_universal_claim_scope"
        return "manual_review_required"

    def _build_report_id(
        self,
        *,
        inventory: HistoricalReplayCertifiabilityInventory,
        residual_dispositions: tuple[HistoricalReplayResidualDisposition, ...],
        closure_verdict: str,
        closure_reason: str,
        global_claim: dict[str, object],
        retained_corpus_claim: dict[str, object],
    ) -> str:
        payload = {
            "inventory": inventory.to_dict(),
            "residual_dispositions": [
                disposition.to_dict()
                for disposition in sorted(
                    residual_dispositions,
                    key=lambda item: (item.manifest_id, item.disposition),
                )
            ],
            "closure_verdict": closure_verdict,
            "closure_reason": closure_reason,
            "global_universal_historical_replay_claim": global_claim,
            "retained_corpus_claim": retained_corpus_claim,
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return f"historical-replay-closure-{digest[:16]}"
