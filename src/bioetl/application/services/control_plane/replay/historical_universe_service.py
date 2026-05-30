"""Full-universe historical replay inventory and closure workflows."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from bioetl.application.runtime_clock import RuntimeClockService
from bioetl.application.services.control_plane.replay._historical_record_payload import (
    build_historical_run_identity_payload,
)
from bioetl.application.services.control_plane.replay.historical_corpus_service import (
    HistoricalReplayCertifiabilityInventory,
    HistoricalReplayCorpusService,
)
from bioetl.application.services.control_plane.replay.historical_identity_models import (
    HistoricalReplayRunIdentity,
)
from bioetl.application.services.control_plane.replay.historical_universe_policy import (
    build_authoritative_truth_surface,
    build_durable_coverage_claim,
    build_governed_full_corpus_gate,
    build_universal_claim,
    build_universe_report_id,
)

__all__ = [
    "HistoricalReplayUniverseClosureReport",
    "HistoricalReplayUniverseExternalRecord",
    "HistoricalReplayUniverseInventory",
    "HistoricalReplayUniverseRecord",
    "HistoricalReplayUniverseService",
]

_CLOSED_CERTIFICATION_STATUSES = frozenset({"already_replayable", "already_certified"})


@dataclass(frozen=True, slots=True)
class HistoricalReplayUniverseExternalRecord(HistoricalReplayRunIdentity):
    """One authoritative non-local historical run record."""

    certification_status: str
    replay_occurrence_kind: str
    blocking_reasons: tuple[str, ...] = ()
    evidence_residency: str = "archived"
    durable_evidence_coverage: bool = False
    source_pack_ref: str | None = None

    def to_dict(self) -> dict[str, object]:
        return build_historical_run_identity_payload(
            manifest_id=self.manifest_id,
            run_id=self.run_id,
            pipeline_name=self.pipeline_name,
            provider=self.provider,
            entity=self.entity,
            execution_context=self.execution_context,
            certification_status=self.certification_status,
            replay_occurrence_kind=self.replay_occurrence_kind,
            blocking_reasons=self.blocking_reasons,
            evidence_residency=self.evidence_residency,
            durable_evidence_coverage=self.durable_evidence_coverage,
            source_pack_ref=self.source_pack_ref,
        )


@dataclass(frozen=True, slots=True)
class HistoricalReplayUniverseRecord:
    """One merged historical-run record in the full replay universe."""

    manifest_id: str
    run_id: str
    pipeline_name: str
    provider: str
    entity: str
    execution_context: str
    certification_status: str
    replay_occurrence_kind: str
    blocking_reasons: tuple[str, ...]
    universe_origin: str
    evidence_residency: str
    durable_evidence_coverage: bool
    source_pack_ref: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "manifest_id": self.manifest_id,
            "run_id": self.run_id,
            "pipeline_name": self.pipeline_name,
            "provider": self.provider,
            "entity": self.entity,
            "execution_context": self.execution_context,
            "certification_status": self.certification_status,
            "replay_occurrence_kind": self.replay_occurrence_kind,
            "blocking_reasons": list(self.blocking_reasons),
            "universe_origin": self.universe_origin,
            "evidence_residency": self.evidence_residency,
            "durable_evidence_coverage": self.durable_evidence_coverage,
            "source_pack_ref": self.source_pack_ref,
        }


@dataclass(frozen=True, slots=True)
class HistoricalReplayUniverseInventorySnapshot:
    """Deterministic inventory for the full historical replay universe."""

    records: tuple[HistoricalReplayUniverseRecord, ...]

    @property
    def manifest_count(self) -> int:
        return len(self.records)

    @property
    def unresolved_count(self) -> int:
        return sum(
            1
            for record in self.records
            if record.certification_status not in _CLOSED_CERTIFICATION_STATUSES
        )

    @property
    def durable_coverage_gap_count(self) -> int:
        return sum(1 for record in self.records if not record.durable_evidence_coverage)

    @property
    def local_retained_count(self) -> int:
        return sum(
            1 for record in self.records if record.universe_origin == "local_retained"
        )

    @property
    def external_archived_count(self) -> int:
        return sum(
            1 for record in self.records if record.universe_origin != "local_retained"
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "manifest_count": self.manifest_count,
            "unresolved_count": self.unresolved_count,
            "durable_coverage_gap_count": self.durable_coverage_gap_count,
            "local_retained_count": self.local_retained_count,
            "external_archived_count": self.external_archived_count,
            "records": [record.to_dict() for record in self.records],
        }


@dataclass(frozen=True, slots=True)
class HistoricalReplayUniverseClosureReportRecord:
    """Persistable full-universe closure artifact."""

    generated_at: datetime
    report_id: str
    inventory: HistoricalReplayUniverseInventorySnapshot
    authoritative_truth_surface: dict[str, object]
    universal_claim: dict[str, object]
    durable_evidence_coverage_claim: dict[str, object]
    governed_full_corpus_gate: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "generated_at": self.generated_at.astimezone(UTC).isoformat(),
            "report_id": self.report_id,
            "inventory": self.inventory.to_dict(),
            "authoritative_truth_surface": self.authoritative_truth_surface,
            "universal_claim": self.universal_claim,
            "durable_evidence_coverage_claim": self.durable_evidence_coverage_claim,
            "governed_full_corpus_gate": self.governed_full_corpus_gate,
        }


@dataclass(slots=True)
class HistoricalReplayUniverseService:
    """Build full-universe replay inventories beyond the local retained corpus."""

    corpus_service: HistoricalReplayCorpusService
    now_factory: Callable[[], datetime] = RuntimeClockService().now

    def build_universe_inventory(
        self,
        *,
        external_records: tuple[HistoricalReplayUniverseExternalRecord, ...] = (),
    ) -> HistoricalReplayUniverseInventorySnapshot:
        local_inventory = self.corpus_service.build_certifiability_inventory()
        records = [
            *self._build_local_records(local_inventory),
            *self._build_external_records(external_records),
        ]
        records.sort(
            key=lambda item: (
                item.pipeline_name,
                item.provider,
                item.entity,
                item.run_id,
                item.manifest_id,
            )
        )
        return HistoricalReplayUniverseInventorySnapshot(records=tuple(records))

    def build_universe_closure_report(
        self,
        *,
        external_records: tuple[HistoricalReplayUniverseExternalRecord, ...] = (),
    ) -> HistoricalReplayUniverseClosureReportRecord:
        inventory = self.build_universe_inventory(external_records=external_records)
        authoritative_truth_surface = build_authoritative_truth_surface()
        universal_claim = build_universal_claim(inventory)
        durable_claim = build_durable_coverage_claim(inventory)
        governed_full_corpus_gate = build_governed_full_corpus_gate(
            authoritative_truth_surface=authoritative_truth_surface,
            universal_claim=universal_claim,
            durable_claim=durable_claim,
        )
        report_id = build_universe_report_id(
            inventory=inventory,
            authoritative_truth_surface=authoritative_truth_surface,
            universal_claim=universal_claim,
            durable_claim=durable_claim,
            governed_full_corpus_gate=governed_full_corpus_gate,
        )
        return HistoricalReplayUniverseClosureReportRecord(
            generated_at=self.now_factory(),
            report_id=report_id,
            inventory=inventory,
            authoritative_truth_surface=authoritative_truth_surface,
            universal_claim=universal_claim,
            durable_evidence_coverage_claim=durable_claim,
            governed_full_corpus_gate=governed_full_corpus_gate,
        )

    def _build_local_records(
        self,
        inventory: HistoricalReplayCertifiabilityInventory,
    ) -> list[HistoricalReplayUniverseRecord]:
        return [
            HistoricalReplayUniverseRecord(
                manifest_id=record.manifest_id,
                run_id=record.run_id,
                pipeline_name=record.pipeline_name,
                provider=record.provider,
                entity=record.entity,
                execution_context=record.execution_context,
                certification_status=record.certification_status,
                replay_occurrence_kind=record.replay_occurrence_kind,
                blocking_reasons=record.blocking_reasons,
                universe_origin="local_retained",
                evidence_residency="retained_local_control_plane",
                durable_evidence_coverage=(
                    record.certification_status in _CLOSED_CERTIFICATION_STATUSES
                ),
                source_pack_ref=None,
            )
            for record in inventory.records
        ]

    def _build_external_records(
        self,
        records: tuple[HistoricalReplayUniverseExternalRecord, ...],
    ) -> list[HistoricalReplayUniverseRecord]:
        return [
            HistoricalReplayUniverseRecord(
                manifest_id=record.manifest_id,
                run_id=record.run_id,
                pipeline_name=record.pipeline_name,
                provider=record.provider,
                entity=record.entity,
                execution_context=record.execution_context,
                certification_status=record.certification_status,
                replay_occurrence_kind=record.replay_occurrence_kind,
                blocking_reasons=record.blocking_reasons,
                universe_origin="external_archived",
                evidence_residency=record.evidence_residency,
                durable_evidence_coverage=record.durable_evidence_coverage,
                source_pack_ref=record.source_pack_ref,
            )
            for record in records
        ]


# Public aliases keep the exported control-plane surface stable while allowing
# the internal record/snapshot names to stay descriptive.
HistoricalReplayUniverseInventory = HistoricalReplayUniverseInventorySnapshot
HistoricalReplayUniverseClosureReport = HistoricalReplayUniverseClosureReportRecord
