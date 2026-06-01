"""Unit tests for retained-corpus historical replay workflows."""

from __future__ import annotations

import pytest

from dataclasses import replace
from datetime import UTC, datetime

from bioetl.application.services.control_plane.replay.historical_corpus_service import (
    HistoricalReplayBulkCertificationSpec,
    HistoricalReplayCorpusService,
)
from bioetl.application.services.control_plane.replay.historical_certification_service import (
    HistoricalReplayCertificationService,
    HistoricalReplaySnapshotCertification,
)
from bioetl.domain.control_plane import RunManifest, RunSourceRef
from bioetl.domain.types import RunID
from tests.helpers.control_plane import InMemoryRunLedgerStore, InMemoryRunManifestStore
from tests.helpers.deterministic_ids import deterministic_uuid_value
from tests.unit.application.services.run_manifest_test_support import (
    make_run_manifest as _build_manifest,
)


pytestmark = pytest.mark.unit

def _make_source_manifest() -> RunManifest:
    return _build_manifest(
        manifest_id="historical-source-manifest",
        execution_fingerprint="historical-source-fingerprint",
        run_id=RunID(deterministic_uuid_value("historical.corpus.source")),
        created_at=datetime(2026, 1, 2, 9, 0, tzinfo=UTC),
    )


def _make_composite_manifest() -> RunManifest:
    manifest = _build_manifest(
        manifest_id="historical-composite-manifest",
        execution_fingerprint="historical-composite-fingerprint",
        run_id=RunID(deterministic_uuid_value("historical.corpus.composite")),
        created_at=datetime(2026, 1, 2, 9, 30, tzinfo=UTC),
    )
    return replace(
        manifest,
        pipeline_name="composite_activity",
        provider="composite",
        entity="activity",
        launch_context={
            **manifest.launch_context,
            "execution_context": "composite",
        },
        runtime_config={
            **manifest.runtime_config,
            "execution_context": "composite",
        },
        resolved_config={
            **manifest.resolved_config,
            "execution_context": "composite",
        },
        source_refs=(
            RunSourceRef(
                provider="chembl",
                entity="activity",
                pipeline_name="chembl_activity",
                query=None,
            ),
        ),
        code_provenance=replace(
            manifest.code_provenance,
            contract_ref="composite.activity",
            contract_version="1.0.0",
            pipeline_version="1.0.0",
        ),
    )


def test_inventory_distinguishes_pending_and_certified_historical_records() -> None:
    source_manifest = _make_source_manifest()
    composite_manifest = _make_composite_manifest()
    manifest_store = InMemoryRunManifestStore()
    manifest_store.save(source_manifest)
    manifest_store.save(composite_manifest)
    ledger_store = InMemoryRunLedgerStore()
    service = HistoricalReplayCorpusService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
        certification_service=HistoricalReplayCertificationService(
            manifest_port=manifest_store,
            ledger_port=ledger_store,
        ),
    )

    inventory = service.build_certifiability_inventory()

    by_manifest_id = {record.manifest_id: record for record in inventory.records}
    assert inventory.manifest_count == 2
    assert inventory.awaiting_source_certification_count == 1
    assert inventory.awaiting_composite_lineage_count == 1
    assert by_manifest_id[source_manifest.manifest_id].certification_status == (
        "awaiting_source_snapshot_certification"
    )
    assert by_manifest_id[composite_manifest.manifest_id].certification_status == (
        "awaiting_certified_source_lineage"
    )


def test_bulk_certification_orders_source_before_composite_and_closes_inventory() -> (
    None
):
    source_manifest = _make_source_manifest()
    composite_manifest = _make_composite_manifest()
    manifest_store = InMemoryRunManifestStore()
    manifest_store.save(source_manifest)
    manifest_store.save(composite_manifest)
    ledger_store = InMemoryRunLedgerStore()
    service = HistoricalReplayCorpusService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
        certification_service=HistoricalReplayCertificationService(
            manifest_port=manifest_store,
            ledger_port=ledger_store,
        ),
    )

    result = service.certify_retained_corpus(
        specs=(
            HistoricalReplayBulkCertificationSpec(
                manifest_id=composite_manifest.manifest_id,
                certifications=(
                    HistoricalReplaySnapshotCertification(
                        provider="chembl",
                        entity="activity",
                        pipeline_name="chembl_activity",
                        snapshot_id="snapshot-certified-composite-1",
                        content_hash="sha256:composite-certified-1",
                        immutable_uri="file:///historical/composite/snapshot-1.jsonl",
                        bronze_batch_ref=(
                            "bronze://historical/composite/batch-1.jsonl"
                        ),
                        certification_artifact_ref=(
                            "control://historical/composite-certification-1.json"
                        ),
                        upstream_run_id=str(source_manifest.run_id),
                        upstream_manifest_id=source_manifest.manifest_id,
                    ),
                ),
            ),
            HistoricalReplayBulkCertificationSpec(
                manifest_id=source_manifest.manifest_id,
                certifications=(
                    HistoricalReplaySnapshotCertification(
                        provider=source_manifest.provider,
                        entity=source_manifest.entity,
                        pipeline_name=source_manifest.pipeline_name,
                        snapshot_id="snapshot-certified-source-1",
                        content_hash="sha256:source-certified-1",
                        immutable_uri="file:///historical/source/snapshot-1.jsonl",
                        bronze_batch_ref="bronze://historical/source/batch-1.jsonl",
                        certification_artifact_ref=(
                            "control://historical/source-certification-1.json"
                        ),
                    ),
                ),
            ),
        )
    )

    assert result.completed_count == 2
    assert result.skipped_count == 0
    assert tuple(record.manifest_id for record in result.records) == (
        source_manifest.manifest_id,
        composite_manifest.manifest_id,
    )
    assert (
        result.inventory_after.certified_count + result.inventory_after.replayable_count
        == 2
    )
    assert result.inventory_after.remaining_uncertified_count == 0
