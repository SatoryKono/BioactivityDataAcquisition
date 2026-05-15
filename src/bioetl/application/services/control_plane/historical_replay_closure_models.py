"""Models for historical replay closure reporting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

RESIDUAL_BLOCKED_STATUSES = frozenset(
    {
        "awaiting_source_snapshot_certification",
        "awaiting_certified_source_lineage",
        "needs_operator_review",
        "outside_certified_historical_scope",
    }
)
RESOLUTION_DISPOSITIONS = frozenset(
    {
        "reconstruct_immutable_evidence",
        "expand_retention_and_publish_evidence",
        "certify_upstream_source_lineage",
        "irrecoverable_missing_immutable_evidence",
        "outside_universal_claim_scope",
        "manual_review_required",
    }
)
HistoricalReplayClaimScopeMode = Literal[
    "all_retained_historical_runs",
    "retained_certifiable_historical_runs",
]


@dataclass(frozen=True, slots=True)
class HistoricalReplayResidualDispositionRecord:
    """Explicit disposition for one residual historical replay blocker."""

    manifest_id: str
    disposition: str
    rationale: str
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.disposition not in RESOLUTION_DISPOSITIONS:
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
class HistoricalReplayClosureReportRecord:
    """Persistable closure report for retained historical replay state."""

    generated_at: datetime
    report_id: str
    inventory: object
    residual_dispositions: tuple[HistoricalReplayResidualDispositionRecord, ...]
    suggested_resolution_queue: tuple[dict[str, object], ...]
    closure_verdict: str
    closure_reason: str
    claim_scope_mode: HistoricalReplayClaimScopeMode
    global_universal_historical_replay_claim: dict[str, object]
    retained_corpus_claim: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        inventory = self.inventory
        inventory_dict = inventory.to_dict() if hasattr(inventory, "to_dict") else {}
        return {
            "generated_at": self.generated_at.astimezone(UTC).isoformat(),
            "report_id": self.report_id,
            "inventory": inventory_dict,
            "residual_dispositions": [
                disposition.to_dict() for disposition in self.residual_dispositions
            ],
            "suggested_resolution_queue": list(self.suggested_resolution_queue),
            "closure_verdict": self.closure_verdict,
            "closure_reason": self.closure_reason,
            "claim_scope_mode": self.claim_scope_mode,
            "global_universal_historical_replay_claim": (
                self.global_universal_historical_replay_claim
            ),
            "retained_corpus_claim": self.retained_corpus_claim,
        }


__all__ = [
    "HistoricalReplayClaimScopeMode",
    "HistoricalReplayClosureReportRecord",
    "HistoricalReplayResidualDispositionRecord",
    "RESIDUAL_BLOCKED_STATUSES",
]
