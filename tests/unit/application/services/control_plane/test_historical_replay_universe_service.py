"""Unit tests for full-universe historical replay closure workflows."""

from __future__ import annotations

import pytest

from datetime import UTC, datetime

from bioetl.application.services.control_plane.replay.historical_corpus_service import (
    HistoricalReplayCorpusService,
)
from bioetl.application.services.control_plane.replay.historical_certification_service import (
    HistoricalReplayCertificationService,
)
from bioetl.application.services.control_plane.replay.historical_universe_service import (
    HistoricalReplayUniverseExternalRecord,
    HistoricalReplayUniverseService,
)
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.types import RunID
from tests.helpers.control_plane import InMemoryRunLedgerStore, InMemoryRunManifestStore
from tests.helpers.deterministic_ids import deterministic_uuid_value
from tests.unit.application.services.run_manifest_test_support import (
    make_run_manifest as _build_manifest,
)


pytestmark = pytest.mark.unit

def _make_manifest() -> RunManifest:
    return _build_manifest(
        manifest_id="universe-source-manifest",
        execution_fingerprint="universe-source-fingerprint",
        run_id=RunID(deterministic_uuid_value("historical.universe.source")),
        created_at=datetime(2026, 1, 4, 9, 0, tzinfo=UTC),
    )


def test_universe_report_blocks_claim_when_external_archived_record_is_unresolved() -> (
    None
):
    manifest_store = InMemoryRunManifestStore()
    manifest_store.save(_make_manifest())
    ledger_store = InMemoryRunLedgerStore()
    service = HistoricalReplayUniverseService(
        corpus_service=HistoricalReplayCorpusService(
            manifest_port=manifest_store,
            ledger_port=ledger_store,
            certification_service=HistoricalReplayCertificationService(
                manifest_port=manifest_store,
                ledger_port=ledger_store,
            ),
        )
    )

    report = service.build_universe_closure_report(
        external_records=(
            HistoricalReplayUniverseExternalRecord(
                manifest_id="archived-manifest-1",
                run_id="archived-run-1",
                pipeline_name="chembl_activity",
                provider="chembl",
                entity="activity",
                execution_context="isolated",
                certification_status="awaiting_source_snapshot_certification",
                replay_occurrence_kind="ordinary_live_capture",
                blocking_reasons=("archive_snapshot_missing",),
                evidence_residency="archive_tier",
                durable_evidence_coverage=False,
                source_pack_ref="archive-pack-1",
            ),
        )
    )

    assert report.inventory.external_archived_count == 1
    assert report.inventory.durable_coverage_gap_count == 2
    assert report.authoritative_truth_surface["authoritative"] is True
    assert report.authoritative_truth_surface["scope"] == "all_known_historical_runs"
    assert report.universal_claim["claimed"] is False
    assert report.universal_claim["scope"] == "all_known_historical_runs"
    assert "archived-manifest-1" in report.universal_claim["blocked_manifest_ids"]
    assert report.durable_evidence_coverage_claim["claimed"] is False
    assert report.governed_full_corpus_gate["satisfied"] is False
    assert report.governed_full_corpus_gate["verdict"] == "gate_blocked"


def test_universe_report_supports_claim_when_local_and_external_records_are_closed() -> (
    None
):
    manifest_store = InMemoryRunManifestStore()
    ledger_store = InMemoryRunLedgerStore()
    service = HistoricalReplayUniverseService(
        corpus_service=HistoricalReplayCorpusService(
            manifest_port=manifest_store,
            ledger_port=ledger_store,
            certification_service=HistoricalReplayCertificationService(
                manifest_port=manifest_store,
                ledger_port=ledger_store,
            ),
        )
    )

    report = service.build_universe_closure_report(
        external_records=(
            HistoricalReplayUniverseExternalRecord(
                manifest_id="archived-manifest-2",
                run_id="archived-run-2",
                pipeline_name="chembl_activity",
                provider="chembl",
                entity="activity",
                execution_context="isolated",
                certification_status="already_certified",
                replay_occurrence_kind="historical_source_replay_certified_parent",
                blocking_reasons=(),
                evidence_residency="authoritative_archive",
                durable_evidence_coverage=True,
                source_pack_ref="archive-pack-2",
            ),
        )
    )

    assert report.inventory.local_retained_count == 0
    assert report.inventory.external_archived_count == 1
    assert report.authoritative_truth_surface["claim_kind"] == (
        "literal_any_run_exact_replay"
    )
    assert report.universal_claim["claimed"] is True
    assert report.universal_claim["scope"] == "all_known_historical_runs"
    assert report.durable_evidence_coverage_claim["claimed"] is True
    assert report.governed_full_corpus_gate["satisfied"] is True
