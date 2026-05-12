"""Corpus-wide historical replay inventory and bulk certification workflows."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.application.services.control_plane.historical_replay_certification_service import (
    HistoricalReplayCertificationResult,
    HistoricalReplayCertificationService,
    HistoricalReplaySnapshotCertification,
)
from bioetl.application.services.control_plane.run_manifest_diagnostics import (
    build_diagnostics_summary,
)
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.control_plane.reproducibility_profiles import (
    resolve_reproducibility_family_profile,
)
from bioetl.domain.ports import RunLedgerPort, RunManifestPort

__all__ = [
    "HistoricalReplayBulkCertificationRecord",
    "HistoricalReplayBulkCertificationResult",
    "HistoricalReplayBulkCertificationSpec",
    "HistoricalReplayCertifiabilityInventory",
    "HistoricalReplayCertifiabilityRecord",
    "HistoricalReplayCorpusService",
]

_CERTIFIED_REPLAY_KINDS = frozenset(
    {
        "historical_source_replay_certified_parent",
        "historical_composite_replay_certified_parent",
    }
)
_ALREADY_REPLAYABLE_STATES = frozenset(
    {
        "exact_replay_child_run",
        "within_launch_time_snapshot_boundary",
        "within_post_capture_parent_boundary",
    }
)
_ALREADY_CERTIFIED_STATES = frozenset(
    {
        "historical_source_replay_certified",
        "historical_composite_replay_certified",
    }
)
_SUPPORTED_BROADER_POLICY = "certified_historical_exact_replay_tranche_supported"


@dataclass(frozen=True, slots=True)
class HistoricalReplayCertifiabilityRecord:
    """One deterministic certifiability record for a retained manifest."""

    manifest_id: str
    run_id: str
    pipeline_name: str
    provider: str
    entity: str
    execution_context: str
    family: str | None
    certification_scope: str | None
    certification_status: str
    replay_occurrence_kind: str
    broader_historical_exact_replay_policy: str
    broader_historical_exact_replay_boundary: str | None
    broader_historical_exact_replay_state: str
    blocking_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return one JSON-safe inventory row."""
        return {
            "manifest_id": self.manifest_id,
            "run_id": self.run_id,
            "pipeline_name": self.pipeline_name,
            "provider": self.provider,
            "entity": self.entity,
            "execution_context": self.execution_context,
            "family": self.family,
            "certification_scope": self.certification_scope,
            "certification_status": self.certification_status,
            "replay_occurrence_kind": self.replay_occurrence_kind,
            "broader_historical_exact_replay_policy": (
                self.broader_historical_exact_replay_policy
            ),
            "broader_historical_exact_replay_boundary": (
                self.broader_historical_exact_replay_boundary
            ),
            "broader_historical_exact_replay_state": (
                self.broader_historical_exact_replay_state
            ),
            "blocking_reasons": list(self.blocking_reasons),
        }


@dataclass(frozen=True, slots=True)
class HistoricalReplayCertifiabilityInventory:
    """Corpus-wide retained-run certifiability inventory."""

    records: tuple[HistoricalReplayCertifiabilityRecord, ...]

    @property
    def manifest_count(self) -> int:
        return len(self.records)

    @property
    def certified_count(self) -> int:
        return sum(
            1
            for record in self.records
            if record.certification_status == "already_certified"
        )

    @property
    def replayable_count(self) -> int:
        return sum(
            1
            for record in self.records
            if record.certification_status == "already_replayable"
        )

    @property
    def awaiting_source_certification_count(self) -> int:
        return sum(
            1
            for record in self.records
            if record.certification_status == "awaiting_source_snapshot_certification"
        )

    @property
    def awaiting_composite_lineage_count(self) -> int:
        return sum(
            1
            for record in self.records
            if record.certification_status == "awaiting_certified_source_lineage"
        )

    @property
    def unsupported_count(self) -> int:
        return sum(
            1
            for record in self.records
            if record.certification_status == "outside_certified_historical_scope"
        )

    @property
    def remaining_uncertified_count(self) -> int:
        return sum(
            1
            for record in self.records
            if record.certification_status
            in {
                "awaiting_source_snapshot_certification",
                "awaiting_certified_source_lineage",
                "needs_operator_review",
            }
        )

    def to_dict(self) -> dict[str, object]:
        """Return one JSON-safe inventory payload."""
        return {
            "manifest_count": self.manifest_count,
            "certified_count": self.certified_count,
            "replayable_count": self.replayable_count,
            "awaiting_source_certification_count": (
                self.awaiting_source_certification_count
            ),
            "awaiting_composite_lineage_count": (
                self.awaiting_composite_lineage_count
            ),
            "unsupported_count": self.unsupported_count,
            "remaining_uncertified_count": self.remaining_uncertified_count,
            "records": [record.to_dict() for record in self.records],
        }


@dataclass(frozen=True, slots=True)
class HistoricalReplayBulkCertificationSpec:
    """One deterministic bulk-certification unit."""

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
        """Return one JSON-safe bulk-certification outcome row."""
        return {
            "manifest_id": self.manifest_id,
            "run_id": self.run_id,
            "certification_scope": self.certification_scope,
            "status": self.status,
            "replay_occurrence_kind": self.replay_occurrence_kind,
            "broader_historical_exact_replay_state": (
                self.broader_historical_exact_replay_state
            ),
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
        """Return one JSON-safe bulk-certification payload."""
        return {
            "completed_count": self.completed_count,
            "skipped_count": self.skipped_count,
            "inventory_before": self.inventory_before.to_dict(),
            "inventory_after": self.inventory_after.to_dict(),
            "records": [record.to_dict() for record in self.records],
        }


@dataclass(slots=True)
class HistoricalReplayCorpusService:
    """Operate on retained manifests as a bounded historical replay corpus."""

    manifest_port: RunManifestPort
    ledger_port: RunLedgerPort

    def build_certifiability_inventory(self) -> HistoricalReplayCertifiabilityInventory:
        """Inventory retained manifests against the certified replay tranche."""
        records = tuple(
            self._build_record(manifest) for manifest in self._iter_manifests()
        )
        return HistoricalReplayCertifiabilityInventory(records=records)

    def certify_retained_corpus(
        self,
        *,
        specs: tuple[HistoricalReplayBulkCertificationSpec, ...],
    ) -> HistoricalReplayBulkCertificationResult:
        """Apply deterministic bulk certification across retained manifests."""
        inventory_before = self.build_certifiability_inventory()
        status_by_manifest_id = {
            record.manifest_id: record for record in inventory_before.records
        }
        manifest_by_id = {
            manifest.manifest_id: manifest for manifest in self._iter_manifests()
        }
        certification_service = HistoricalReplayCertificationService(
            manifest_port=self.manifest_port,
            ledger_port=self.ledger_port,
        )
        ordered_specs = tuple(
            sorted(
                specs,
                key=lambda spec: self._bulk_spec_order_key(
                    manifest_by_id[spec.manifest_id]
                ),
            )
        )
        records: list[HistoricalReplayBulkCertificationRecord] = []
        for spec in ordered_specs:
            manifest = manifest_by_id.get(spec.manifest_id)
            if manifest is None:
                raise ValueError(
                    f"Historical replay bulk certification could not find manifest "
                    f"{spec.manifest_id!r}"
                )
            inventory_record = status_by_manifest_id.get(spec.manifest_id)
            if inventory_record is None:
                raise ValueError(
                    f"Historical replay inventory is missing manifest "
                    f"{spec.manifest_id!r}"
                )
            if inventory_record.certification_status == "already_certified":
                records.append(
                    self._build_skipped_record(
                        inventory_record=inventory_record,
                        status="skipped_already_certified",
                    )
                )
                continue
            if inventory_record.certification_status == "already_replayable":
                records.append(
                    self._build_skipped_record(
                        inventory_record=inventory_record,
                        status="skipped_already_replayable",
                    )
                )
                continue
            if inventory_record.certification_status == (
                "outside_certified_historical_scope"
            ):
                raise ValueError(
                    "Historical replay bulk certification is outside the published "
                    f"certified tranche for manifest {spec.manifest_id!r}"
                )
            result = self._apply_one_certification(
                certification_service=certification_service,
                manifest=manifest,
                spec=spec,
            )
            records.append(
                HistoricalReplayBulkCertificationRecord(
                    manifest_id=result.manifest_id,
                    run_id=result.run_id,
                    certification_scope=result.certification_scope,
                    status="certified",
                    replay_occurrence_kind=result.replay_occurrence_kind,
                    broader_historical_exact_replay_state=(
                        result.broader_historical_exact_replay_state
                    ),
                )
            )
        return HistoricalReplayBulkCertificationResult(
            inventory_before=inventory_before,
            inventory_after=self.build_certifiability_inventory(),
            records=tuple(records),
        )

    def _apply_one_certification(
        self,
        *,
        certification_service: HistoricalReplayCertificationService,
        manifest: RunManifest,
        spec: HistoricalReplayBulkCertificationSpec,
    ) -> HistoricalReplayCertificationResult:
        execution_context = self._execution_context(manifest)
        if execution_context == "composite":
            return certification_service.certify_historical_composite_run(
                manifest_id=manifest.manifest_id,
                certifications=spec.certifications,
            )
        return certification_service.certify_historical_source_run(
            manifest_id=manifest.manifest_id,
            certifications=spec.certifications,
        )

    def _build_record(
        self, manifest: RunManifest
    ) -> HistoricalReplayCertifiabilityRecord:
        execution_context = self._execution_context(manifest)
        diagnostics = build_diagnostics_summary(
            manifest,
            tuple(self.ledger_port.list_entries(manifest.manifest_id)),
        )
        profile = resolve_reproducibility_family_profile(
            provider=manifest.provider,
            entity=manifest.entity,
            contract_ref=manifest.code_provenance.contract_ref
            or f"{manifest.provider}.{manifest.entity}",
            execution_context=execution_context,
        )
        replay_occurrence_kind = str(
            diagnostics.get("replay_occurrence_kind") or "unknown"
        )
        broader_state = str(
            diagnostics.get("broader_historical_exact_replay_state") or "unknown"
        )
        certification_scope = self._certification_scope_for_context(execution_context)
        certification_status, blocking_reasons = self._classify_certification_status(
            broader_policy=profile.broader_historical_exact_replay_policy,
            replay_occurrence_kind=replay_occurrence_kind,
            broader_state=broader_state,
        )
        return HistoricalReplayCertifiabilityRecord(
            manifest_id=manifest.manifest_id,
            run_id=str(manifest.run_id),
            pipeline_name=manifest.pipeline_name,
            provider=manifest.provider,
            entity=manifest.entity,
            execution_context=execution_context,
            family=profile.family,
            certification_scope=certification_scope,
            certification_status=certification_status,
            replay_occurrence_kind=replay_occurrence_kind,
            broader_historical_exact_replay_policy=(
                profile.broader_historical_exact_replay_policy
            ),
            broader_historical_exact_replay_boundary=(
                profile.broader_historical_exact_replay_boundary
            ),
            broader_historical_exact_replay_state=broader_state,
            blocking_reasons=blocking_reasons,
        )

    def _classify_certification_status(
        self,
        *,
        broader_policy: str,
        replay_occurrence_kind: str,
        broader_state: str,
    ) -> tuple[str, tuple[str, ...]]:
        if broader_policy != _SUPPORTED_BROADER_POLICY:
            return (
                "outside_certified_historical_scope",
                ("broader_historical_exact_replay_not_supported",),
            )
        if replay_occurrence_kind in _CERTIFIED_REPLAY_KINDS or (
            broader_state in _ALREADY_CERTIFIED_STATES
        ):
            return ("already_certified", ())
        if broader_state in _ALREADY_REPLAYABLE_STATES:
            return ("already_replayable", ())
        if broader_state == "awaiting_historical_snapshot_certification":
            return (
                "awaiting_source_snapshot_certification",
                ("retained_snapshot_certification_required",),
            )
        if broader_state == "awaiting_certified_source_lineage":
            return (
                "awaiting_certified_source_lineage",
                ("certified_source_lineage_required",),
            )
        return (
            "needs_operator_review",
            ("replay_certifiability_state_requires_review",),
        )

    def _build_skipped_record(
        self,
        *,
        inventory_record: HistoricalReplayCertifiabilityRecord,
        status: str,
    ) -> HistoricalReplayBulkCertificationRecord:
        return HistoricalReplayBulkCertificationRecord(
            manifest_id=inventory_record.manifest_id,
            run_id=inventory_record.run_id,
            certification_scope=inventory_record.certification_scope,
            status=status,
            replay_occurrence_kind=inventory_record.replay_occurrence_kind,
            broader_historical_exact_replay_state=(
                inventory_record.broader_historical_exact_replay_state
            ),
        )

    def _iter_manifests(self) -> tuple[RunManifest, ...]:
        return tuple(self.manifest_port.list_all())

    def _bulk_spec_order_key(self, manifest: RunManifest) -> tuple[int, object, str]:
        execution_context = self._execution_context(manifest)
        source_first = 0 if execution_context != "composite" else 1
        return (source_first, manifest.created_at, manifest.manifest_id)

    @staticmethod
    def _execution_context(manifest: RunManifest) -> str:
        context = str(manifest.launch_context.get("execution_context") or "").strip()
        if context:
            return context
        if manifest.provider == "composite":
            return "composite"
        return "source"

    @staticmethod
    def _certification_scope_for_context(execution_context: str) -> str | None:
        if execution_context == "composite":
            return "historical_composite_replay"
        if execution_context:
            return "historical_source_replay"
        return None
