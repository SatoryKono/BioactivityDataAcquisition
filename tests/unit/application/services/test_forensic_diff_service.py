"""Tests for unified forensic run diff service."""

from __future__ import annotations

from uuid import uuid4

from bioetl.application.services.control_plane.forensic_diff_service import (
    ForensicRunDiffService,
)
from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.types import RunID, RunType
from tests.helpers.control_plane import InMemoryRunLedgerStore, InMemoryRunManifestStore
from tests.unit.application.services.run_manifest_test_support import (
    FIXED_TIME,
    VALID_CONFIG_HASH,
    make_run_manifest,
)


def test_forensic_diff_reports_semantic_and_artifact_evidence() -> None:
    manifest_store = InMemoryRunManifestStore()
    ledger_store = InMemoryRunLedgerStore()
    left_run_id = RunID(uuid4())
    right_run_id = RunID(uuid4())
    left = make_run_manifest(
        manifest_id="manifest-left",
        run_id=left_run_id,
        config_hash=VALID_CONFIG_HASH,
    )
    right = make_run_manifest(
        manifest_id="manifest-right",
        run_id=right_run_id,
        run_type=RunType.REBUILD,
        config_hash="b" * 64,
    )
    manifest_store.save(left)
    manifest_store.save(right)
    ledger_store.append(
        RunLedgerEntry(
            entry_id="artifact-left",
            manifest_id="manifest-left",
            run_id=left_run_id,
            event_type="artifact_published",
            occurred_at=FIXED_TIME,
            stage="silver",
            dataset_ref="silver:chembl.activity@1",
            lineage_fragment_id="silver:fragment-1",
            details={
                "artifact_path": "data/output/silver/chembl/activity",
                "metadata_path": "data/output/silver/chembl/activity/_metadata.yaml",
            },
        )
    )
    service = ForensicRunDiffService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
    )

    result = service.compare("manifest-left", "manifest-right")
    payload = result.to_dict()

    assert payload["classification"] == "semantic_drift"
    assert payload["semantic_equivalent"] is False
    assert payload["forensic_diff"]["verdict"] == "semantic_drift"
    assert payload["left_diagnostics"]["published_artifact_count"] == 1
    assert payload["right_diagnostics"]["published_artifact_count"] == 0
    assert payload["artifact_completeness"]["left"]["complete"] is True
    assert payload["artifact_completeness"]["right"]["complete"] is False
    assert payload["missing_evidence"]["right"] == [
        "run_ledger_entries_missing",
        "published_artifacts_missing",
        "produced_artifact_trace_incomplete",
    ]


def test_forensic_diff_classifies_occurrence_only_drift() -> None:
    manifest_store = InMemoryRunManifestStore()
    left_run_id = RunID(uuid4())
    right_run_id = RunID(uuid4())
    manifest_store.save(
        make_run_manifest(
            manifest_id="manifest-left",
            run_id=left_run_id,
            execution_fingerprint="fingerprint-same",
        )
    )
    manifest_store.save(
        make_run_manifest(
            manifest_id="manifest-right",
            run_id=right_run_id,
            execution_fingerprint="fingerprint-same",
        )
    )
    service = ForensicRunDiffService(manifest_port=manifest_store)

    payload = service.compare("manifest-left", "manifest-right").to_dict()

    assert payload["occurrence_only"] is True
    assert payload["classification"] == "occurrence_only"


def test_forensic_diff_classifies_exact_match() -> None:
    manifest_store = InMemoryRunManifestStore()
    run_id = RunID(uuid4())
    manifest_store.save(
        make_run_manifest(
            manifest_id="manifest-left",
            run_id=run_id,
            execution_fingerprint="fingerprint-same",
        )
    )
    service = ForensicRunDiffService(manifest_port=manifest_store)

    payload = service.compare("manifest-left", "manifest-left").to_dict()

    assert payload["classification"] == "identical"
    assert payload["semantic_equivalent"] is True
    assert payload["occurrence_only"] is False


def test_forensic_diff_classifies_missing_optional_evidence() -> None:
    manifest_store = InMemoryRunManifestStore()
    left_run_id = RunID(uuid4())
    right_run_id = RunID(uuid4())
    manifest_store.save(
        make_run_manifest(
            manifest_id="manifest-left",
            run_id=left_run_id,
            execution_fingerprint="fingerprint-same",
        )
    )
    manifest_store.save(
        make_run_manifest(
            manifest_id="manifest-right",
            run_id=right_run_id,
            execution_fingerprint="fingerprint-same",
        )
    )
    service = ForensicRunDiffService(manifest_port=manifest_store)

    payload = service.compare("manifest-left", "manifest-right").to_dict()

    assert payload["missing_evidence"]["left"] == [
        "run_ledger_entries_missing",
        "published_artifacts_missing",
        "produced_artifact_trace_incomplete",
    ]
    assert payload["missing_evidence"]["right"] == [
        "run_ledger_entries_missing",
        "published_artifacts_missing",
        "produced_artifact_trace_incomplete",
    ]


def test_forensic_diff_reports_missing_sidecars_and_incomplete_trace() -> None:
    manifest_store = InMemoryRunManifestStore()
    ledger_store = InMemoryRunLedgerStore()
    run_id = RunID(uuid4())
    manifest_store.save(make_run_manifest(manifest_id="manifest-left", run_id=run_id))
    ledger_store.append(
        RunLedgerEntry(
            entry_id="artifact-left",
            manifest_id="manifest-left",
            run_id=run_id,
            event_type="artifact_published",
            occurred_at=FIXED_TIME,
            stage="silver",
            dataset_ref="silver:chembl.activity@1",
            lineage_fragment_id="silver:fragment-1",
            details={"artifact_path": "data/output/silver/chembl/activity"},
        )
    )
    service = ForensicRunDiffService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
    )

    payload = service.compare("manifest-left", "manifest-left").to_dict()

    assert payload["artifact_completeness"]["left"]["complete"] is False
    assert (
        payload["artifact_completeness"]["left"]["metadata_sidecar_missing_count"] == 1
    )
    assert payload["missing_evidence"]["left"] == ["metadata_sidecars_missing"]


def test_forensic_diff_reports_checkpoint_mismatch() -> None:
    manifest_store = InMemoryRunManifestStore()
    manifest_store.save(
        make_run_manifest(
            manifest_id="manifest-left",
            run_id=RunID(uuid4()),
            execution_fingerprint="fingerprint-left",
            config_hash=VALID_CONFIG_HASH,
        )
    )
    manifest_store.save(
        make_run_manifest(
            manifest_id="manifest-right",
            run_id=RunID(uuid4()),
            execution_fingerprint="fingerprint-right",
            config_hash="c" * 64,
        )
    )
    service = ForensicRunDiffService(manifest_port=manifest_store)

    payload = service.compare("manifest-left", "manifest-right").to_dict()

    assert payload["checkpoint_compatibility"]["available"] is True
    assert payload["checkpoint_compatibility"]["compatible"] is False
    assert (
        "execution_fingerprint"
        in payload["checkpoint_compatibility"]["mismatched_fields"]
    )
