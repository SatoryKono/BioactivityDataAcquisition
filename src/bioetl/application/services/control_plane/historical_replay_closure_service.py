"""Closure reporting and claim gating for historical replay."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from bioetl.application.runtime_clock import RuntimeClockService
from bioetl.application.services.control_plane.historical_replay_closure_models import (
    RESIDUAL_BLOCKED_STATUSES,
    HistoricalReplayClaimScopeMode,
    HistoricalReplayClosureReportRecord,
    HistoricalReplayResidualDispositionRecord,
)
from bioetl.application.services.control_plane.historical_replay_closure_policy import (
    build_closure_report_id,
    build_global_claim_gate,
    build_retained_corpus_claim,
    build_suggested_resolution,
    resolve_closure_verdict,
    validate_residual_dispositions,
)
from bioetl.application.services.control_plane.historical_replay_corpus_service import (
    HistoricalReplayCorpusService,
)

__all__ = [
    "HistoricalReplayClosureReport",
    "HistoricalReplayClosureService",
    "HistoricalReplayResidualDisposition",
]


@dataclass(slots=True)
class HistoricalReplayClosureService:
    """Build closure artifacts and claim-gate verdicts for retained corpora."""

    corpus_service: HistoricalReplayCorpusService
    now_factory: Callable[[], datetime] = RuntimeClockService().now

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
        """Build one deterministic retained-corpus closure report."""
        inventory = self.corpus_service.build_certifiability_inventory()
        blocked_records = tuple(
            record
            for record in inventory.records
            if record.certification_status in RESIDUAL_BLOCKED_STATUSES
        )
        disposition_map = validate_residual_dispositions(
            blocked_records=blocked_records,
            residual_dispositions=residual_dispositions,
        )
        unresolved_records = tuple(
            record
            for record in blocked_records
            if record.manifest_id not in disposition_map
        )
        suggested_resolution_queue = tuple(
            build_suggested_resolution(record) for record in blocked_records
        )
        closure_verdict, closure_reason = resolve_closure_verdict(
            inventory=inventory,
            unresolved_records=unresolved_records,
            disposition_map=disposition_map,
            claim_scope_mode=claim_scope_mode,
        )
        global_claim = build_global_claim_gate(
            inventory=inventory,
            unresolved_records=unresolved_records,
            disposition_map=disposition_map,
            claim_scope_mode=claim_scope_mode,
        )
        retained_corpus_claim = build_retained_corpus_claim(
            inventory=inventory,
            unresolved_records=unresolved_records,
        )
        generated_at = self.now_factory()
        report_id = build_closure_report_id(
            inventory=inventory,
            residual_dispositions=residual_dispositions,
            closure_verdict=closure_verdict,
            closure_reason=closure_reason,
            claim_scope_mode=claim_scope_mode,
            global_claim=global_claim,
            retained_corpus_claim=retained_corpus_claim,
        )
        return HistoricalReplayClosureReportRecord(
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
            claim_scope_mode=claim_scope_mode,
            global_universal_historical_replay_claim=global_claim,
            retained_corpus_claim=retained_corpus_claim,
        )


HistoricalReplayClosureReport = HistoricalReplayClosureReportRecord
HistoricalReplayResidualDisposition = HistoricalReplayResidualDispositionRecord


HistoricalReplayClosureReport = HistoricalReplayClosureReportRecord
