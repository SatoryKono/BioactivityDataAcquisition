# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Focused tests for bounded latest RunManifest scope indexing."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

import bioetl.infrastructure.control_plane.file_run_manifest_store as store_module
from bioetl.domain.control_plane import RunCodeProvenance, RunManifest
from bioetl.domain.exceptions import StorageError
from bioetl.domain.types import RunID, RunType
from bioetl.infrastructure.control_plane import (
    FileRunManifestStore,
    RunManifestStoreCorruptionError,
)
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite

pytestmark = pytest.mark.unit


def _manifest(
    manifest_id: str,
    *,
    pipeline_name: str = "chembl_activity",
    run_type: RunType = RunType.INCREMENTAL,
    created_at: datetime = datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
) -> RunManifest:
    return RunManifest(
        manifest_id=manifest_id,
        execution_fingerprint=f"fingerprint-{manifest_id}",
        schema_version="1.0",
        created_at=created_at,
        run_id=RunID(deterministic_uuid_from_callsite(manifest_id)),
        run_type=run_type,
        pipeline_name=pipeline_name,
        provider=pipeline_name.split("_", maxsplit=1)[0],
        entity=pipeline_name.split("_", maxsplit=1)[-1],
        launch_context={},
        runtime_config={},
        resolved_config={},
        code_provenance=RunCodeProvenance(),
    )


def test_latest_scope_index_returns_deterministic_latest_candidate(tmp_path) -> None:
    store = FileRunManifestStore(base_path=tmp_path / "run_manifest")
    incremental = _manifest("manifest-incremental")
    backfill = _manifest(
        "manifest-backfill",
        run_type=RunType.BACKFILL,
        created_at=datetime(2026, 1, 2, 12, 0, tzinfo=UTC),
    )
    other_pipeline = _manifest(
        "manifest-pubchem",
        pipeline_name="pubchem_compound",
        created_at=datetime(2026, 1, 3, 12, 0, tzinfo=UTC),
    )

    for manifest in (backfill, other_pipeline, incremental):
        store.save(manifest)

    assert store.get_latest_for_scope("chembl_activity") == backfill
    assert (
        store.get_latest_for_scope(
            "chembl_activity",
            (RunType.INCREMENTAL,),
        )
        == incremental
    )
    assert store.get_latest_for_scope("missing_pipeline") is None


def test_latest_scope_happy_path_does_not_scan_manifest_catalog(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = FileRunManifestStore(base_path=tmp_path / "run_manifest")
    expected = _manifest("manifest-indexed")
    store.save(expected)

    monkeypatch.setattr(
        store,
        "list_all",
        lambda: (_ for _ in ()).throw(
            AssertionError("indexed latest lookup must not scan all manifests")
        ),
    )

    assert store.get_latest_for_scope("chembl_activity") == expected


def test_missing_legacy_scope_index_fails_closed_without_catalog_scan(
    tmp_path,
) -> None:
    store = FileRunManifestStore(base_path=tmp_path / "run_manifest")
    manifest = _manifest("manifest-legacy")
    store.save(manifest)
    store._latest_scope_index_path(
        manifest.pipeline_name,
        manifest.run_type,
    ).unlink()
    (store.base_path / "_latest_by_scope" / "_catalog.json").unlink()

    assert store.get_latest_for_scope("chembl_activity") is None


def test_complete_catalog_rejects_missing_scope_pointer(tmp_path) -> None:
    store = FileRunManifestStore(base_path=tmp_path / "run_manifest")
    manifest = _manifest("manifest-missing-pointer")
    store.save(manifest)
    store._latest_scope_index_path(
        manifest.pipeline_name,
        manifest.run_type,
    ).unlink()

    with pytest.raises(RunManifestStoreCorruptionError, match="has no pointer"):
        store.get_latest_for_scope("chembl_activity")


def test_latest_scope_index_rejects_wrong_scope_manifest(tmp_path) -> None:
    store = FileRunManifestStore(base_path=tmp_path / "run_manifest")
    chembl = _manifest("manifest-chembl")
    pubchem = _manifest("manifest-pubchem", pipeline_name="pubchem_compound")
    store.save(chembl)
    store.save(pubchem)
    index_path = store._latest_scope_index_path(
        chembl.pipeline_name,
        chembl.run_type,
    )
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    payload["manifest_id"] = pubchem.manifest_id
    index_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RunManifestStoreCorruptionError, match="not 'chembl_activity"):
        store.get_latest_for_scope("chembl_activity")


def test_latest_scope_index_rejects_malformed_and_missing_targets(tmp_path) -> None:
    store = FileRunManifestStore(base_path=tmp_path / "run_manifest")
    manifest = _manifest("manifest-corrupt")
    store.save(manifest)
    index_path = store._latest_scope_index_path(
        manifest.pipeline_name,
        manifest.run_type,
    )
    index_path.write_text("{not-json", encoding="utf-8")

    with pytest.raises(RunManifestStoreCorruptionError, match="cannot load"):
        store.get_latest_for_scope("chembl_activity", (RunType.INCREMENTAL,))

    index_path.write_text(
        json.dumps(
            {
                "manifest_id": "missing-manifest",
                "pipeline_name": "chembl_activity",
                "run_type": "incremental",
                "schema_version": 1,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(RunManifestStoreCorruptionError, match="missing manifest"):
        store.get_latest_for_scope("chembl_activity", (RunType.INCREMENTAL,))


def test_older_save_does_not_replace_newer_scope_index(tmp_path) -> None:
    store = FileRunManifestStore(base_path=tmp_path / "run_manifest")
    newer = _manifest(
        "manifest-newer",
        created_at=datetime(2026, 1, 2, 12, 0, tzinfo=UTC),
    )
    older = _manifest("manifest-older")

    store.save(newer)
    store.save(older)

    assert store.get_latest_for_scope("chembl_activity") == newer
    assert store.get_by_run_id(older.run_id) == older


def test_scope_index_write_failure_restores_manifest_and_run_index(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    metrics = MagicMock()
    store = FileRunManifestStore(
        base_path=tmp_path / "run_manifest",
        metrics=metrics,
    )
    manifest = _manifest("manifest-rollback")

    monkeypatch.setattr(
        store_module,
        "write_latest_scope_index",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            OSError("scope index write failed")
        ),
    )

    with pytest.raises(StorageError, match="Run manifest save failed"):
        store.save(manifest)

    assert not (store.base_path / f"{manifest.manifest_id}.json").exists()
    assert not (store.base_path / "_by_run_id" / f"{manifest.run_id}.txt").exists()
    assert not store._latest_scope_index_path(
        manifest.pipeline_name,
        manifest.run_type,
    ).exists()
    metrics.increment_counter.assert_called_once_with(
        "bioetl_control_plane_manifest_writes_total",
        1,
        {
            "pipeline": "chembl_activity",
            "run_type": "incremental",
            "status": "failed",
        },
    )


def test_latest_scope_read_emits_existing_control_plane_metrics(tmp_path) -> None:
    metrics = MagicMock()
    store = FileRunManifestStore(
        base_path=tmp_path / "run_manifest",
        metrics=metrics,
    )
    store.save(_manifest("manifest-metrics"))
    metrics.reset_mock()

    assert store.get_latest_for_scope("chembl_activity") is not None

    metrics.increment_counter.assert_called_once_with(
        "bioetl_control_plane_reads_total",
        1,
        {
            "store": "manifest",
            "operation": "get_latest_for_scope",
            "status": "success",
        },
    )
    metrics.observe_histogram.assert_called_once()


def test_legacy_index_rebuild_plan_is_deterministic_and_read_only(tmp_path) -> None:
    store = FileRunManifestStore(base_path=tmp_path / "run_manifest")
    older = _manifest("manifest-older")
    newer = _manifest(
        "manifest-newer",
        created_at=datetime(2026, 1, 2, 12, 0, tzinfo=UTC),
    )
    store.save(older)
    store.save(newer)
    index_path = store._latest_scope_index_path(
        newer.pipeline_name,
        newer.run_type,
    )
    index_path.unlink()
    (store.base_path / "_latest_by_scope" / "_catalog.json").unlink()

    report = store.plan_latest_scope_index_rebuild()

    assert report == {
        "approval_required_before_apply": True,
        "catalog": {
            "action": "create",
            "complete": True,
            "corruption": None,
            "index_path": "_latest_by_scope/_catalog.json",
            "scopes": [
                {
                    "pipeline_name": "chembl_activity",
                    "run_type": "incremental",
                }
            ],
        },
        "contract": "run_manifest_latest_scope_index_rebuild_v1",
        "entries": [
            {
                "action": "create",
                "corruption": None,
                "current_manifest_id": None,
                "desired_manifest_id": "manifest-newer",
                "index_path": "_latest_by_scope/chembl_activity/incremental.json",
                "pipeline_name": "chembl_activity",
                "run_type": "incremental",
            }
        ],
        "manifest_count": 2,
        "mode": "dry_run",
        "scope_count": 1,
        "writes_performed": 0,
    }
    assert not index_path.exists()
