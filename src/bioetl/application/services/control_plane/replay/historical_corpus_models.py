"""Models for retained-corpus historical replay workflows."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.application.services.control_plane.replay._historical_record_payload import (
    HistoricalReplayRunIdentity,
    build_historical_certified_identity_payload_from_record,
)


@dataclass(frozen=True, slots=True)
class HistoricalReplaySnapshotCertification:
    """Immutable snapshot evidence used for historical replay certification."""

    provider: str
    entity: str
    pipeline_name: str
    snapshot_id: str
    content_hash: str
    immutable_uri: str
    bronze_batch_ref: str
    query: str | None = None
    query_fingerprint: str | None = None
    certification_artifact_ref: str | None = None
    certification_basis: str = "retained_bronze_artifact"
    upstream_run_id: str | None = None
    upstream_manifest_id: str | None = None


@dataclass(frozen=True, slots=True)
class HistoricalReplayCertifiabilityRecord(HistoricalReplayRunIdentity):
    """One deterministic certifiability record for a retained manifest."""

    family: str | None
    certification_scope: str | None
    certification_status: str
    replay_occurrence_kind: str
    broader_historical_exact_replay_policy: str
    broader_historical_exact_replay_boundary: str | None
    broader_historical_exact_replay_state: str
    blocking_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return build_historical_certified_identity_payload_from_record(
            self,
            family=self.family,
            certification_scope=self.certification_scope,
            broader_historical_exact_replay_policy=self.broader_historical_exact_replay_policy,
            broader_historical_exact_replay_boundary=self.broader_historical_exact_replay_boundary,
            broader_historical_exact_replay_state=self.broader_historical_exact_replay_state,
        )


@dataclass(frozen=True, slots=True)
class HistoricalReplayCertifiabilityInventory:
    """Corpus-wide retained-run certifiability inventory."""

    records: tuple[HistoricalReplayCertifiabilityRecord, ...]

    def count_status(self, *statuses: str) -> int:
        return sum(record.certification_status in statuses for record in self.records)

    @property
    def manifest_count(self) -> int:
        return len(self.records)

    @property
    def certified_count(self) -> int:
        return self.count_status("already_certified")

    @property
    def replayable_count(self) -> int:
        return self.count_status("already_replayable")

    @property
    def awaiting_source_certification_count(self) -> int:
        return self.count_status("awaiting_source_snapshot_certification")

    @property
    def awaiting_composite_lineage_count(self) -> int:
        return self.count_status("awaiting_certified_source_lineage")

    @property
    def unsupported_count(self) -> int:
        return self.count_status("outside_certified_historical_scope")

    @property
    def remaining_uncertified_count(self) -> int:
        return self.count_status(
            "awaiting_source_snapshot_certification",
            "awaiting_certified_source_lineage",
            "needs_operator_review",
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "manifest_count": self.manifest_count,
            "certified_count": self.certified_count,
            "replayable_count": self.replayable_count,
            "awaiting_source_certification_count": self.awaiting_source_certification_count,
            "awaiting_composite_lineage_count": self.awaiting_composite_lineage_count,
            "unsupported_count": self.unsupported_count,
            "remaining_uncertified_count": self.remaining_uncertified_count,
            "records": [record.to_dict() for record in self.records],
        }


@dataclass(frozen=True, slots=True)
class HistoricalReplayBulkCertificationSpec:
    manifest_id: str
    certifications: tuple[HistoricalReplaySnapshotCertification, ...]


@dataclass(frozen=True, slots=True)
class HistoricalReplayBulkCertificationRecord:
    """One applied or skipped bulk-certification outcome."""

    manifest_id: str
    run_id: str
    certification_scope: str | None
    status: str
    replay_occurrence_kind: str
    broader_historical_exact_replay_state: str

    def to_dict(self) -> dict[str, object]:
        return {
            "manifest_id": self.manifest_id,
            "run_id": self.run_id,
            "certification_scope": self.certification_scope,
            "status": self.status,
            "replay_occurrence_kind": self.replay_occurrence_kind,
            "broader_historical_exact_replay_state": self.broader_historical_exact_replay_state,
        }


@dataclass(frozen=True, slots=True)
class HistoricalReplayBulkCertificationResult:
    """Result of one deterministic retained-corpus certification pass."""

    inventory_before: HistoricalReplayCertifiabilityInventory
    inventory_after: HistoricalReplayCertifiabilityInventory
    records: tuple[HistoricalReplayBulkCertificationRecord, ...]

    @property
    def completed_count(self) -> int:
        return sum(1 for record in self.records if record.status == "certified")

    @property
    def skipped_count(self) -> int:
        return len(self.records) - self.completed_count

    def to_dict(self) -> dict[str, object]:
        return {
            "completed_count": self.completed_count,
            "skipped_count": self.skipped_count,
            "inventory_before": self.inventory_before.to_dict(),
            "inventory_after": self.inventory_after.to_dict(),
            "records": [record.to_dict() for record in self.records],
        }


CORPUS_MODEL_PUBLIC_NAMES: tuple[str, ...] = (
    "HistoricalReplayBulkCertificationRecord",
    "HistoricalReplayBulkCertificationResult",
    "HistoricalReplayBulkCertificationSpec",
    "HistoricalReplayCertifiabilityInventory",
    "HistoricalReplayCertifiabilityRecord",
    "HistoricalReplaySnapshotCertification",
)
__all__ = list(CORPUS_MODEL_PUBLIC_NAMES)
