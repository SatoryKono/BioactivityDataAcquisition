"""Unit tests for file-backed run-manifest storage."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

import bioetl.infrastructure.control_plane.file_run_manifest_store as manifest_store_module
from bioetl.domain.control_plane import (
    RunArtifactRef,
    RunCodeProvenance,
    RunInputSnapshotRef,
    RunManifest,
    RunSourceRef,
)
from bioetl.domain.exceptions import StorageError
from bioetl.domain.types import RunID, RunType
from bioetl.infrastructure.control_plane import (
    FileRunManifestStore,
    RunManifestStoreCorruptionError,
)
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite


pytestmark = pytest.mark.unit


def test_file_store_round_trips_manifest_by_id_and_run_id(tmp_path) -> None:
    store = FileRunManifestStore(base_path=tmp_path / "run_manifest")
    run_id = RunID(deterministic_uuid_from_callsite("replay-sensitive"))
    manifest = RunManifest(
        manifest_id="manifest-1",
        execution_fingerprint="fingerprint-1",
        schema_version="1.0",
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={"limit": 100},
        runtime_config={"run_type": "incremental"},
        resolved_config={"provider": "chembl", "entity_type": "activity"},
        code_provenance=RunCodeProvenance(
            pipeline_version="1.0.0",
            git_commit="abc1234",
            config_hash="deadbeef",
        ),
        source_refs=(
            RunSourceRef(
                provider="chembl",
                entity="activity",
                pipeline_name="chembl_activity",
                input_snapshots=(
                    RunInputSnapshotRef(
                        snapshot_id="snapshot-1",
                        content_hash="hash-1",
                        immutable_uri="s3://bioetl-snapshots/chembl/activity/1.jsonl",
                        storage_provider="s3",
                        object_bucket="bioetl-snapshots",
                        object_key="chembl/activity/1.jsonl",
                        object_version_id="version-1",
                        etag='"etag-1"',
                    ),
                ),
            ),
        ),
        planned_artifacts=(
            RunArtifactRef(layer="bronze", path="data/output/bronze/chembl/activity"),
        ),
    )

    store.save(manifest)

    assert store.get("manifest-1") == manifest
    assert store.get_by_run_id(run_id) == manifest


def test_file_store_emits_manifest_write_metric(tmp_path) -> None:
    metrics = MagicMock()
    store = FileRunManifestStore(
        base_path=tmp_path / "run_manifest",
        metrics=metrics,
    )
    manifest = RunManifest(
        manifest_id="manifest-2",
        execution_fingerprint="fingerprint-2",
        schema_version="1.0",
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={},
        runtime_config={},
        resolved_config={},
        code_provenance=RunCodeProvenance(),
    )

    store.save(manifest)

    metrics.increment_counter.assert_called_once_with(
        "bioetl_control_plane_manifest_writes_total",
        1,
        {
            "pipeline": "chembl_activity",
            "run_type": "incremental",
            "status": "success",
        },
    )
    metrics.observe_histogram.assert_called_once()
    args, kwargs = metrics.observe_histogram.call_args
    assert args[0] == "bioetl_control_plane_manifest_write_duration_seconds"
    assert isinstance(args[1], float)
    assert args[2] == {
        "pipeline": "chembl_activity",
        "run_type": "incremental",
        "status": "success",
    }
    assert kwargs == {}


def test_file_store_emits_manifest_read_metric_on_get_success(tmp_path) -> None:
    metrics = MagicMock()
    store = FileRunManifestStore(
        base_path=tmp_path / "run_manifest",
        metrics=metrics,
    )
    run_id = RunID(deterministic_uuid_from_callsite("replay-sensitive"))
    manifest = RunManifest(
        manifest_id="manifest-3",
        execution_fingerprint="fingerprint-3",
        schema_version="1.0",
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={},
        runtime_config={},
        resolved_config={},
        code_provenance=RunCodeProvenance(),
    )

    store.save(manifest)
    metrics.reset_mock()

    assert store.get("manifest-3") == manifest

    metrics.increment_counter.assert_called_once_with(
        "bioetl_control_plane_reads_total",
        1,
        {
            "store": "manifest",
            "operation": "get",
            "status": "success",
        },
    )
    metrics.observe_histogram.assert_called_once()
    args, kwargs = metrics.observe_histogram.call_args
    assert args[0] == "bioetl_control_plane_read_duration_seconds"
    assert isinstance(args[1], float)
    assert args[2] == {
        "store": "manifest",
        "operation": "get",
        "status": "success",
    }
    assert kwargs == {}


def test_file_store_emits_manifest_read_metric_on_get_failure(tmp_path) -> None:
    metrics = MagicMock()
    store = FileRunManifestStore(
        base_path=tmp_path / "run_manifest",
        metrics=metrics,
    )
    manifest_path = store.base_path / "broken.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text("{not-json", encoding="utf-8")

    try:
        store.get("broken")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected malformed manifest payload to raise ValueError")

    metrics.increment_counter.assert_called_once_with(
        "bioetl_control_plane_reads_total",
        1,
        {
            "store": "manifest",
            "operation": "get",
            "status": "failed",
        },
    )
    metrics.observe_histogram.assert_called_once()


def test_file_store_lists_all_manifests_in_deterministic_order(tmp_path) -> None:
    store = FileRunManifestStore(base_path=tmp_path / "run_manifest")
    older = RunManifest(
        manifest_id="manifest-b",
        execution_fingerprint="fingerprint-b",
        schema_version="1.0",
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={},
        runtime_config={},
        resolved_config={},
        code_provenance=RunCodeProvenance(),
    )
    newer = RunManifest(
        manifest_id="manifest-a",
        execution_fingerprint="fingerprint-a",
        schema_version="1.0",
        created_at=datetime(2026, 1, 2, 12, 0, tzinfo=UTC),
        run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={},
        runtime_config={},
        resolved_config={},
        code_provenance=RunCodeProvenance(),
    )

    store.save(newer)
    store.save(older)

    assert tuple(manifest.manifest_id for manifest in store.list_all()) == (
        "manifest-b",
        "manifest-a",
    )


def test_file_store_rolls_back_manifest_when_run_index_write_fails(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    metrics = MagicMock()
    store = FileRunManifestStore(
        base_path=tmp_path / "run_manifest",
        metrics=metrics,
    )
    manifest = RunManifest(
        manifest_id="manifest-rollback",
        execution_fingerprint="fingerprint-rollback",
        schema_version="1.0",
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={},
        runtime_config={},
        resolved_config={},
        code_provenance=RunCodeProvenance(),
    )
    original_atomic_write_text = manifest_store_module.atomic_write_text
    call_count = {"value": 0}

    def _fail_on_index_write(path, text, encoding="utf-8") -> None:
        call_count["value"] += 1
        if call_count["value"] == 1:
            original_atomic_write_text(path, text, encoding=encoding)
            return
        raise OSError("run index write failed")

    monkeypatch.setattr(
        "bioetl.infrastructure.control_plane.file_run_manifest_store.atomic_write_text",
        _fail_on_index_write,
    )

    with pytest.raises(StorageError) as exc_info:
        store.save(manifest)

    assert "Run manifest save failed" in str(exc_info.value)
    assert store.get(manifest.manifest_id) is None
    assert store.get_by_run_id(manifest.run_id) is None
    assert not (store.base_path / f"{manifest.manifest_id}.json").exists()
    metrics.increment_counter.assert_any_call(
        "bioetl_control_plane_manifest_writes_total",
        1,
        {
            "pipeline": "chembl_activity",
            "run_type": "incremental",
            "status": "failed",
        },
    )
    write_duration_calls = [
        call
        for call in metrics.observe_histogram.call_args_list
        if call.args[0] == "bioetl_control_plane_manifest_write_duration_seconds"
    ]
    assert len(write_duration_calls) == 1
    args, kwargs = write_duration_calls[0]
    assert isinstance(args[1], float)
    assert args[2] == {
        "pipeline": "chembl_activity",
        "run_type": "incremental",
        "status": "failed",
    }
    assert kwargs == {}


def test_file_store_reports_orphan_manifest_without_run_index(tmp_path) -> None:
    store = FileRunManifestStore(base_path=tmp_path / "run_manifest")
    run_id = RunID(deterministic_uuid_from_callsite("replay-sensitive"))
    manifest = RunManifest(
        manifest_id="manifest-orphan",
        execution_fingerprint="fingerprint-orphan",
        schema_version="1.0",
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={},
        runtime_config={},
        resolved_config={},
        code_provenance=RunCodeProvenance(),
    )
    store.base_path.mkdir(parents=True, exist_ok=True)
    (store.base_path / f"{manifest.manifest_id}.json").write_text(
        json.dumps(manifest.to_dict(), sort_keys=True),
        encoding="utf-8",
    )

    with pytest.raises(RunManifestStoreCorruptionError, match="index corruption"):
        store.get(manifest.manifest_id)
    assert store.get_by_run_id(run_id) is None


def test_file_store_reports_mismatched_run_index(tmp_path) -> None:
    metrics = MagicMock()
    store = FileRunManifestStore(base_path=tmp_path / "run_manifest", metrics=metrics)
    run_id = RunID(deterministic_uuid_from_callsite("replay-sensitive"))
    manifest = RunManifest(
        manifest_id="manifest-indexed",
        execution_fingerprint="fingerprint-indexed",
        schema_version="1.0",
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={},
        runtime_config={},
        resolved_config={},
        code_provenance=RunCodeProvenance(),
    )
    store.save(manifest)
    metrics.reset_mock()
    run_index_path = store.base_path / "_by_run_id" / f"{run_id}.txt"
    run_index_path.write_text("manifest-other", encoding="utf-8")

    with pytest.raises(RunManifestStoreCorruptionError, match="manifest-other"):
        store.get(manifest.manifest_id)
    metrics.increment_counter.assert_called_once_with(
        "bioetl_control_plane_reads_total",
        1,
        {
            "store": "manifest",
            "operation": "get",
            "status": "failed",
        },
    )
    metrics.observe_histogram.assert_called_once()
    metrics.reset_mock()

    with pytest.raises(RunManifestStoreCorruptionError, match="missing manifest"):
        store.get_by_run_id(run_id)
    metrics.increment_counter.assert_called_once_with(
        "bioetl_control_plane_reads_total",
        1,
        {
            "store": "manifest",
            "operation": "get_by_run_id",
            "status": "failed",
        },
    )
    metrics.observe_histogram.assert_called_once()


def test_file_store_fails_closed_on_run_id_manifest_collision(tmp_path) -> None:
    store = FileRunManifestStore(base_path=tmp_path / "run_manifest")
    run_id = RunID(deterministic_uuid_from_callsite("replay-sensitive"))
    original = RunManifest(
        manifest_id="manifest-original",
        execution_fingerprint="fingerprint-original",
        schema_version="1.0",
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={},
        runtime_config={},
        resolved_config={},
        code_provenance=RunCodeProvenance(),
    )
    conflicting = RunManifest(
        manifest_id="manifest-conflicting",
        execution_fingerprint="fingerprint-conflicting",
        schema_version="1.0",
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={},
        runtime_config={},
        resolved_config={},
        code_provenance=RunCodeProvenance(),
    )

    store.save(original)

    with pytest.raises(StorageError) as exc_info:
        store.save(conflicting)

    assert "Run manifest save failed" in str(exc_info.value)
    assert "already mapped to a different manifest_id" in str(exc_info.value)
    assert store.get(original.manifest_id) == original
    assert store.get_by_run_id(run_id) == original
    assert store.get(conflicting.manifest_id) is None
    assert not (store.base_path / f"{conflicting.manifest_id}.json").exists()
    run_index_path = store.base_path / "_by_run_id" / f"{run_id}.txt"
    assert run_index_path.read_text(encoding="utf-8").strip() == original.manifest_id


def test_file_store_allows_idempotent_retry_for_same_run_id_mapping(tmp_path) -> None:
    store = FileRunManifestStore(base_path=tmp_path / "run_manifest")
    manifest = RunManifest(
        manifest_id="manifest-retry",
        execution_fingerprint="fingerprint-retry",
        schema_version="1.0",
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={},
        runtime_config={},
        resolved_config={},
        code_provenance=RunCodeProvenance(),
    )

    store.save(manifest)
    store.save(manifest)

    assert store.get(manifest.manifest_id) == manifest
    assert store.get_by_run_id(manifest.run_id) == manifest


def test_file_store_assert_saved_checks_materialized_paths(tmp_path) -> None:
    store = FileRunManifestStore(base_path=tmp_path / "run_manifest")
    manifest = RunManifest(
        manifest_id="manifest-fast-post-save",
        execution_fingerprint="fingerprint-fast-post-save",
        schema_version="1.0",
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        run_id=RunID(deterministic_uuid_from_callsite("replay-sensitive")),
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={},
        runtime_config={},
        resolved_config={},
        code_provenance=RunCodeProvenance(),
    )

    store.save(manifest)

    store.assert_saved(manifest)

    (store.base_path / "_by_run_id" / f"{manifest.run_id}.txt").unlink()
    with pytest.raises(RuntimeError, match="run_id index is not materialized"):
        store.assert_saved(manifest)
