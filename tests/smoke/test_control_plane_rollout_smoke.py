"""Smoke tests for control-plane rollout artifacts and metrics."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock
from tests.helpers.deterministic_ids import deterministic_run_uuid_from_callsite

import pytest

import bioetl.infrastructure.control_plane.file_run_ledger_store as run_ledger_store_module
from bioetl.application.services.control_plane.manifest.inspection_service import (
    RunManifestInspectionService,
)
from bioetl.application.services.control_plane.ledger.service import RunLedgerService
from bioetl.domain.control_plane import RunCodeProvenance, RunManifest
from bioetl.domain.ports.observability.metrics import MetricsPort
from bioetl.domain.types import RunID, RunType
from bioetl.infrastructure.control_plane.file_run_ledger_store import FileRunLedgerStore
from bioetl.infrastructure.control_plane.file_run_manifest_store import (
    FileRunManifestStore,
)


def _make_manifest(run_id: RunID) -> RunManifest:
    return RunManifest(
        manifest_id="manifest-smoke",
        execution_fingerprint="fingerprint-smoke",
        schema_version="1.0",
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={"limit": 25},
        runtime_config={"run_type": "incremental", "limit": 25},
        resolved_config={"provider": "chembl", "entity_type": "activity"},
        code_provenance=RunCodeProvenance(
            pipeline_version="1.0.0",
            git_commit="abc1234",
            config_hash="d" * 64,
            contract_ref="chembl.activity",
            contract_version="1.2.0",
            dq_policy_ref="chembl_activity.gold",
            rule_bundle_version="2026.03",
            dq_contract_compatibility_hash="compat-hash-1",
            effective_config_artifact_id="eca-123",
        ),
    )


@pytest.mark.smoke
def test_control_plane_rollout_smoke_emits_artifacts_and_aggregate_metrics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # This smoke test verifies control-plane artifacts and metrics, not durable
    # flush semantics. Avoid Windows/cloud-synced filesystem fsync stalls.
    monkeypatch.setattr(run_ledger_store_module.os, "fsync", lambda _fd: None)
    metrics = MagicMock(spec=MetricsPort)
    run_id = deterministic_run_uuid_from_callsite("test_control_plane_rollout_smoke")
    manifest_store = FileRunManifestStore(
        base_path=tmp_path / "output" / "control" / "run_manifest",
        metrics=metrics,
    )
    ledger_store = FileRunLedgerStore(
        base_path=tmp_path / "output" / "control" / "run_ledger",
        metrics=metrics,
    )
    manifest = _make_manifest(run_id)
    entry_counter = {"value": 0}

    def _entry_id_factory() -> str:
        entry_counter["value"] += 1
        return f"entry-{entry_counter['value']}"

    manifest_store.save(manifest)
    ledger_service = RunLedgerService(
        ledger_port=ledger_store,
        manifest_id=manifest.manifest_id,
        run_id=run_id,
        _entry_id_factory=_entry_id_factory,
        _occurred_at_factory=lambda: datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )
    ledger_service.record_manifest_created(manifest)
    ledger_service.record_run_started()
    ledger_service.record_stage_completed(
        stage="execute_pipeline",
        metrics_snapshot={"records_bronze": 5},
        details={"result": "ok"},
    )
    ledger_service.record_artifact_published(
        layer="silver",
        artifact_path="data/output/silver/chembl/activity",
        artifact_content_hash="a" * 64,
        dataset_ref="silver:chembl.activity@1",
        lineage_fragment_id="silver:fragment-1",
        details={"source_batch_id": "batch-123", "dataset_hash": "hash-123"},
    )
    ledger_service.record_run_finished(metrics_snapshot={"records_silver": 5})

    inspection = RunManifestInspectionService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
    ).show(manifest.manifest_id)

    assert (
        tmp_path
        / "output"
        / "control"
        / "run_manifest"
        / f"{manifest.manifest_id}.json"
    ).exists()
    assert (
        tmp_path / "output" / "control" / "run_ledger" / f"{manifest.manifest_id}.jsonl"
    ).exists()
    assert inspection.diagnostics["latest_status"] == "success"
    assert inspection.diagnostics["latest_event_type"] == "run_finished"

    counter_metric_names = [
        call.args[0] for call in metrics.increment_counter.call_args_list
    ]
    histogram_metric_names = [
        call.args[0] for call in metrics.observe_histogram.call_args_list
    ]
    assert "bioetl_control_plane_manifest_writes_total" in counter_metric_names
    assert "bioetl_control_plane_ledger_appends_total" in counter_metric_names
    assert "bioetl_control_plane_reads_total" in counter_metric_names
    assert "bioetl_control_plane_read_duration_seconds" in histogram_metric_names
