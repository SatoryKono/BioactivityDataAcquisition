"""Unit tests for control-plane metric emitters."""

from __future__ import annotations

from datetime import datetime, UTC
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

from bioetl.domain.control_plane.run_ledger import RunLedgerEntry
from bioetl.domain.control_plane.run_manifest import RunCodeProvenance, RunManifest
from bioetl.domain.ports.observability.metrics import MetricsPort
from bioetl.domain.types import RunID, RunType
from bioetl.infrastructure.control_plane.file_run_ledger_store import FileRunLedgerStore
from bioetl.infrastructure.control_plane.file_run_manifest_store import (
    FileRunManifestStore,
)


def _make_manifest(pipeline: str = "chembl_activity") -> RunManifest:
    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return RunManifest(
        manifest_id="manifest-obs",
        execution_fingerprint="fingerprint",
        schema_version="1",
        created_at=now,
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        pipeline_name=pipeline,
        provider="chembl",
        entity="activity",
        launch_context={},
        runtime_config={},
        resolved_config={},
        code_provenance=RunCodeProvenance(),
    )


def _make_ledger_entry(manifest: RunManifest) -> RunLedgerEntry:
    return RunLedgerEntry(
        entry_id="entry-obs",
        manifest_id=manifest.manifest_id,
        run_id=manifest.run_id,
        event_type="manifest_created",
        occurred_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        status="success",
        details={"_diagnostic": {"pipeline": manifest.pipeline_name}},
    )


def test_manifest_and_ledger_emit_control_plane_counters(tmp_path: Path) -> None:
    metrics = MagicMock(spec=MetricsPort)
    manifest_store = FileRunManifestStore(
        base_path=tmp_path / "manifests", metrics=metrics
    )
    ledger_store = FileRunLedgerStore(base_path=tmp_path / "ledger", metrics=metrics)

    manifest = _make_manifest()
    manifest_store.save(manifest)
    manifest_histogram_call = metrics.observe_histogram.call_args
    assert manifest_histogram_call is not None
    assert manifest_histogram_call.args[0] == (
        "bioetl_control_plane_manifest_write_duration_seconds"
    )
    assert manifest_histogram_call.args[2] == {
        "pipeline": manifest.pipeline_name,
        "run_type": manifest.run_type.value,
        "status": "success",
    }
    metrics.observe_histogram.reset_mock()

    ledger_entry = _make_ledger_entry(manifest)
    ledger_store.append(ledger_entry)

    assert metrics.increment_counter.call_count == 2
    manifest_call, ledger_call = metrics.increment_counter.call_args_list

    manifest_labels = manifest_call.args[2]
    assert manifest_call.args[0] == "bioetl_control_plane_manifest_writes_total"
    assert manifest_labels == {
        "pipeline": manifest.pipeline_name,
        "run_type": manifest.run_type.value,
        "status": "success",
    }

    ledger_labels = ledger_call.args[2]
    assert ledger_call.args[0] == "bioetl_control_plane_ledger_appends_total"
    assert ledger_labels == {
        "pipeline": manifest.pipeline_name,
        "event_type": "manifest_created",
        "status": "success",
    }
    ledger_histogram_call = metrics.observe_histogram.call_args
    assert ledger_histogram_call is not None
    assert ledger_histogram_call.args[0] == (
        "bioetl_control_plane_ledger_append_duration_seconds"
    )
    assert ledger_histogram_call.args[2] == {
        "pipeline": manifest.pipeline_name,
        "event_type": "manifest_created",
        "status": "success",
    }

    allowed_keys = {"pipeline", "run_type", "event_type", "status"}
    for call in metrics.increment_counter.call_args_list:
        label_keys = set(call.args[2].keys())
        assert label_keys.issubset(allowed_keys)


def test_control_plane_metrics_never_emit_forbidden_labels_or_values(
    tmp_path: Path,
) -> None:
    metrics = MagicMock(spec=MetricsPort)
    manifest_store = FileRunManifestStore(
        base_path=tmp_path / "manifests",
        metrics=metrics,
    )
    ledger_store = FileRunLedgerStore(
        base_path=tmp_path / "ledger",
        metrics=metrics,
    )

    manifest = _make_manifest()
    manifest_store.save(manifest)
    artifact_path = str(tmp_path / "output" / "silver" / "chembl" / "activity")
    entry = RunLedgerEntry(
        entry_id="entry-guard",
        manifest_id=manifest.manifest_id,
        run_id=manifest.run_id,
        event_type="artifact_published",
        occurred_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        status="published",
        dataset_ref="silver:chembl.activity@hash-123",
        lineage_fragment_id="silver:fragment-1",
        details={
            "_diagnostic": {"pipeline": manifest.pipeline_name},
            "artifact_path": artifact_path,
            "source_batch_id": "batch-123",
            "dataset_hash": "hash-123",
        },
    )
    ledger_store.append(entry)

    assert manifest_store.get(manifest.manifest_id) == manifest
    assert manifest_store.get_by_run_id(manifest.run_id) == manifest

    manifest_entries = ledger_store.list_entries(manifest.manifest_id)
    run_entries = ledger_store.list_entries_by_run_id(manifest.run_id)
    assert len(manifest_entries) == 1
    assert len(run_entries) == 1
    for loaded_entry in (manifest_entries[0], run_entries[0]):
        assert loaded_entry.entry_id == entry.entry_id
        assert loaded_entry.manifest_id == entry.manifest_id
        assert loaded_entry.run_id == entry.run_id
        assert loaded_entry.event_type == entry.event_type
        assert loaded_entry.status == entry.status

    forbidden_keys = {
        "run_id",
        "manifest_id",
        "artifact_path",
        "path",
        "dataset_hash",
        "source_batch_id",
    }
    forbidden_values = {
        str(manifest.run_id),
        manifest.manifest_id,
        artifact_path,
        "hash-123",
        "batch-123",
        "silver:chembl.activity@hash-123",
    }
    allowed_keys_by_metric = {
        "bioetl_control_plane_manifest_writes_total": {
            "pipeline",
            "run_type",
            "status",
        },
        "bioetl_control_plane_manifest_write_duration_seconds": {
            "pipeline",
            "run_type",
            "status",
        },
        "bioetl_control_plane_ledger_appends_total": {
            "pipeline",
            "event_type",
            "status",
        },
        "bioetl_control_plane_ledger_append_duration_seconds": {
            "pipeline",
            "event_type",
            "status",
        },
        "bioetl_control_plane_reads_total": {"store", "operation", "status"},
        "bioetl_control_plane_read_duration_seconds": {
            "store",
            "operation",
            "status",
        },
    }

    def _assert_labels(metric_name: str, labels: dict[str, object]) -> None:
        assert set(labels).issubset(allowed_keys_by_metric[metric_name])
        assert forbidden_keys.isdisjoint(labels)
        for value in labels.values():
            rendered = str(value)
            assert rendered not in forbidden_values
            assert not rendered.startswith(str(tmp_path))

    for call in metrics.increment_counter.call_args_list:
        metric_name = call.args[0]
        labels = call.args[2]
        assert metric_name in allowed_keys_by_metric
        _assert_labels(metric_name, labels)

    for call in metrics.observe_histogram.call_args_list:
        metric_name = call.args[0]
        labels = call.args[2]
        assert metric_name in allowed_keys_by_metric
        _assert_labels(metric_name, labels)
