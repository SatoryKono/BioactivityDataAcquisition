"""Bounded certification workflows for historical exact-replay evidence."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from bioetl.application.services.control_plane.replay._historical_certification_support import (
    HistoricalReplayCertificationResult,
    HistoricalReplayCertificationResultAssembler,
    HistoricalReplayCertificationValidator,
)
from bioetl.application.services.control_plane.replay._historical_snapshot_certification_modes import (
    HISTORICAL_COMPOSITE_REPLAY_ENVELOPE_CERTIFIED,
    HISTORICAL_SOURCE_SNAPSHOT_CERTIFIED,
)
from bioetl.application.services.control_plane.replay.historical_corpus_models import (
    HistoricalReplayBulkCertificationRecord as HistoricalReplayBulkCertificationRecord,
    HistoricalReplayBulkCertificationResult as HistoricalReplayBulkCertificationResult,
    HistoricalReplayBulkCertificationSpec as HistoricalReplayBulkCertificationSpec,
    HistoricalReplayCertifiabilityInventory as HistoricalReplayCertifiabilityInventory,
    HistoricalReplayCertifiabilityRecord as HistoricalReplayCertifiabilityRecord,
    HistoricalReplaySnapshotCertification,
)
from bioetl.domain.ports import RunLedgerPort, RunManifestPort
from bioetl.domain.types import RunID

__all__ = [
    "HistoricalReplayCertificationResult",
    "HistoricalReplayCertificationService",
    "HistoricalReplaySnapshotCertification",
]


@dataclass(slots=True)
class HistoricalReplayCertificationService:
    """Append certified historical replay evidence without mutating manifests."""

    manifest_port: RunManifestPort
    ledger_port: RunLedgerPort
    entry_id_factory: Callable[[], str]

    def certify_historical_source_run(
        self,
        *,
        manifest_id: str | None = None,
        run_id: RunID | None = None,
        certifications: tuple[HistoricalReplaySnapshotCertification, ...],
    ) -> HistoricalReplayCertificationResult:
        """Backfill certified immutable source snapshots for one historical run."""
        validator = self._validator()
        manifest = validator.load_manifest(manifest_id=manifest_id, run_id=run_id)
        validator.validate_source_context(manifest)
        validator.validate_certification_coverage(
            manifest=manifest,
            certifications=certifications,
        )
        ledger_service = validator.build_ledger_service(
            manifest=manifest,
            ledger_port=self.ledger_port,
            entry_id_factory=self.entry_id_factory,
        )
        for certification in certifications:
            normalized_query = validator.resolve_certification_query(
                manifest=manifest,
                certification=certification,
            )
            ledger_service.record_input_snapshot_published(
                provider=certification.provider,
                entity=certification.entity,
                pipeline_name=certification.pipeline_name,
                snapshot_id=certification.snapshot_id,
                content_hash=certification.content_hash,
                immutable_uri=certification.immutable_uri,
                bronze_batch_ref=certification.bronze_batch_ref,
                query_fingerprint=certification.query_fingerprint,
                details={
                    "query": normalized_query,
                    "materialization_mode": HISTORICAL_SOURCE_SNAPSHOT_CERTIFIED,
                    "certification_scope": "historical_source_replay",
                    "certification_basis": certification.certification_basis,
                    "certification_artifact_ref": (
                        certification.certification_artifact_ref
                    ),
                },
            )
        return self._result_builder().build(
            manifest=manifest,
            certification_scope="historical_source_replay",
        )

    def certify_historical_composite_run(
        self,
        *,
        manifest_id: str | None = None,
        run_id: RunID | None = None,
        certifications: tuple[HistoricalReplaySnapshotCertification, ...],
    ) -> HistoricalReplayCertificationResult:
        """Certify one historical composite replay parent from certified lineage."""
        validator = self._validator()
        manifest = validator.load_manifest(manifest_id=manifest_id, run_id=run_id)
        validator.validate_composite_context(manifest)
        validator.validate_certification_coverage(
            manifest=manifest,
            certifications=certifications,
        )
        validator.validate_upstream_certified_lineage(certifications)
        ledger_service = validator.build_ledger_service(
            manifest=manifest,
            ledger_port=self.ledger_port,
            entry_id_factory=self.entry_id_factory,
        )
        for certification in certifications:
            normalized_query = validator.resolve_certification_query(
                manifest=manifest,
                certification=certification,
            )
            ledger_service.record_input_snapshot_published(
                provider=certification.provider,
                entity=certification.entity,
                pipeline_name=certification.pipeline_name,
                snapshot_id=certification.snapshot_id,
                content_hash=certification.content_hash,
                immutable_uri=certification.immutable_uri,
                bronze_batch_ref=certification.bronze_batch_ref,
                query_fingerprint=certification.query_fingerprint,
                details={
                    "query": normalized_query,
                    "materialization_mode": (
                        HISTORICAL_COMPOSITE_REPLAY_ENVELOPE_CERTIFIED
                    ),
                    "certification_scope": "historical_composite_replay",
                    "certification_basis": "certified_source_lineage",
                    "certification_artifact_ref": (
                        certification.certification_artifact_ref
                    ),
                    "upstream_run_id": certification.upstream_run_id,
                    "upstream_manifest_id": certification.upstream_manifest_id,
                },
            )
        return self._result_builder().build(
            manifest=manifest,
            certification_scope="historical_composite_replay",
        )

    def _validator(self) -> HistoricalReplayCertificationValidator:
        return HistoricalReplayCertificationValidator(
            manifest_port=self.manifest_port,
            ledger_port=self.ledger_port,
        )

    def _result_builder(self) -> HistoricalReplayCertificationResultAssembler:
        return HistoricalReplayCertificationResultAssembler(
            ledger_port=self.ledger_port,
        )
