"""Corpus-wide historical replay inventory and bulk certification workflows."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module

from bioetl.application.services.control_plane.replay import historical_corpus_models
from bioetl.application.services.control_plane.replay.historical_certification_service import (
    HistoricalReplayCertificationResult,
    HistoricalReplayCertificationService,
)
from bioetl.application.services.control_plane.replay.historical_corpus_models import (
    HistoricalReplayBulkCertificationRecord as HistoricalReplayBulkCertificationRecord,
)
from bioetl.application.services.control_plane.replay.historical_corpus_models import (
    HistoricalReplayBulkCertificationResult as HistoricalReplayBulkCertificationResult,
)
from bioetl.application.services.control_plane.replay.historical_corpus_models import (
    HistoricalReplayBulkCertificationSpec as HistoricalReplayBulkCertificationSpec,
)
from bioetl.application.services.control_plane.replay.historical_corpus_models import (
    HistoricalReplayCertifiabilityInventory as HistoricalReplayCertifiabilityInventory,
)
from bioetl.application.services.control_plane.replay.historical_corpus_models import (
    HistoricalReplayCertifiabilityRecord as HistoricalReplayCertifiabilityRecord,
)
from bioetl.application.services.control_plane.replay.historical_corpus_policy import (
    bulk_spec_order_key,
    certification_scope_for_context,
    classify_certification_status,
    resolve_execution_context,
)
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.control_plane.reproducibility_profiles import (
    resolve_reproducibility_family_profile,
)
from bioetl.domain.ports import RunLedgerPort, RunManifestPort


def _build_diagnostics_summary(*args: object, **kwargs: object) -> object:
    """Lazy leaf import to avoid static diagnostics-package fan-in (ARCH-REF-04)."""
    return import_module(
        "bioetl.application.services.control_plane.manifest.diagnostics"
    ).build_diagnostics_summary(*args, **kwargs)


build_diagnostics_summary = _build_diagnostics_summary  # type: ignore[assignment]

__all__ = [*historical_corpus_models.__all__, "HistoricalReplayCorpusService"]


@dataclass(slots=True)
class HistoricalReplayCorpusService:
    """Operate on retained manifests as a bounded historical replay corpus."""

    manifest_port: RunManifestPort
    ledger_port: RunLedgerPort
    certification_service: HistoricalReplayCertificationService

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
                certification_service=self.certification_service,
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
        execution_context = resolve_execution_context(manifest)
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
        execution_context = resolve_execution_context(manifest)
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
        certification_scope = certification_scope_for_context(execution_context)
        certification_status, blocking_reasons = classify_certification_status(
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
        return bulk_spec_order_key(manifest)
