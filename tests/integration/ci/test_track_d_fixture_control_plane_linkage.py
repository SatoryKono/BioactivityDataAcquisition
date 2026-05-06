"""Track D integration checks for tracked Bronze fixtures and control-plane linkage."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from uuid import uuid4

import pytest

from bioetl.composition.bootstrap import bootstrap_pipeline_runner
from bioetl.composition.factories import _observability_wiring
from bioetl.domain.types import RunID
from bioetl.infrastructure.config import get_pipeline_config, get_settings
from tests.helpers.control_plane_replay import (
    PROJECT_ROOT,
    build_cached_fixture_run_context,
    build_tracked_fixture_exact_replay_matrix_payload,
    load_control_plane_bundle,
    load_control_plane_payloads,
    load_tracked_fixture_entry,
    materialize_cached_bronze_batch,
    patch_clean_code_revision,
    run_cached_fixture_pipeline,
)

pytestmark = [
    pytest.mark.relaxed_dq,
    pytest.mark.usefixtures("relaxed_dq_env"),
]

_PIPELINE_KEY = "chembl/activity"
_PIPELINE_NAME = "chembl_activity"


@pytest.mark.integration
@pytest.mark.no_api
@pytest.mark.asyncio
async def test_tracked_fixture_run_persists_linked_control_plane_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tracked fixture replay must produce linked manifest/effective-config artifacts."""
    fixture_entry = load_tracked_fixture_entry(pipeline_key=_PIPELINE_KEY)
    assert fixture_entry.get("fixture_kind") == "tracked_ci_sample"

    fixture_path_raw = fixture_entry.get("fixture_path")
    assert isinstance(fixture_path_raw, str) and fixture_path_raw
    tracked_fixture_path = PROJECT_ROOT / fixture_path_raw
    assert tracked_fixture_path.exists(), (
        f"Missing tracked fixture: {tracked_fixture_path}"
    )

    cached_root = tmp_path / "cached_bronze" / "chembl" / "activity"
    materialize_cached_bronze_batch(
        tracked_fixture_path=tracked_fixture_path,
        cache_root=cached_root,
        date="2026-03-25",
    )

    data_dir = tmp_path / "runtime_data"
    monkeypatch.setenv("BIOETL_DATA_DIR", str(data_dir))
    monkeypatch.setenv("BIOETL_TEST_MODE", "true")
    monkeypatch.setenv("BIOETL_PIPELINE__HEALTH_CHECK_MODE", "probe")
    patch_clean_code_revision(monkeypatch)
    get_settings.cache_clear()
    get_pipeline_config.cache_clear()

    run_id_first = await run_cached_fixture_pipeline(
        pipeline_name=_PIPELINE_NAME,
        cached_bronze_path=cached_root,
        date="2026-03-25",
    )
    run_id_second = await run_cached_fixture_pipeline(
        pipeline_name=_PIPELINE_NAME,
        cached_bronze_path=cached_root,
        date="2026-03-25",
    )

    manifest_first, effective_first = load_control_plane_payloads(
        data_dir=data_dir,
        run_id=run_id_first,
    )
    manifest_second, effective_second = load_control_plane_payloads(
        data_dir=data_dir,
        run_id=run_id_second,
    )

    code_provenance_first = manifest_first["code_provenance"]
    code_provenance_second = manifest_second["code_provenance"]
    assert manifest_first["run_id"] != manifest_second["run_id"]
    assert manifest_first["manifest_id"] != manifest_second["manifest_id"]
    assert manifest_first["replay_capability"] == "exact_replay_supported"
    assert manifest_second["replay_capability"] == "exact_replay_supported"
    assert (
        manifest_first["execution_fingerprint"]
        == manifest_second["execution_fingerprint"]
    )
    assert manifest_first["launch_context"]["exact_replay"] is True
    assert manifest_second["launch_context"]["exact_replay"] is True
    assert manifest_first["runtime_config"]["exact_replay"] is True
    assert manifest_second["runtime_config"]["exact_replay"] is True
    source_refs_first = manifest_first.get("source_refs")
    source_refs_second = manifest_second.get("source_refs")
    assert isinstance(source_refs_first, list) and source_refs_first
    assert isinstance(source_refs_second, list) and source_refs_second
    snapshots_first = source_refs_first[0].get("input_snapshots")
    snapshots_second = source_refs_second[0].get("input_snapshots")
    assert isinstance(snapshots_first, list) and snapshots_first
    assert isinstance(snapshots_second, list) and snapshots_second
    assert snapshots_first == snapshots_second
    assert isinstance(snapshots_first[0].get("snapshot_id"), str)
    assert isinstance(snapshots_first[0].get("content_hash"), str)
    assert isinstance(snapshots_first[0].get("immutable_uri"), str)
    assert snapshots_first[0]["snapshot_id"] == (
        f"sha256:{snapshots_first[0]['content_hash']}"
    )
    assert str(snapshots_first[0]["immutable_uri"]).startswith("bronze://")
    assert code_provenance_first["contract_ref"] == "chembl.activity"
    assert code_provenance_second["contract_ref"] == "chembl.activity"
    assert isinstance(code_provenance_first.get("contract_version"), str)
    assert isinstance(code_provenance_second.get("contract_version"), str)
    assert code_provenance_first["config_hash"] == code_provenance_second["config_hash"]
    assert (
        code_provenance_first["dq_contract_compatibility_hash"]
        == code_provenance_second["dq_contract_compatibility_hash"]
    )
    assert (
        code_provenance_first["effective_config_artifact_id"]
        == code_provenance_second["effective_config_artifact_id"]
    )
    semantic_first = effective_first["semantic_artifact"]
    semantic_second = effective_second["semantic_artifact"]
    assert effective_first["artifact_id"] == effective_second["artifact_id"]
    assert (
        semantic_first["effective_config_hash"]
        == semantic_second["effective_config_hash"]
    )
    assert (
        semantic_first["dq_contract_compatibility_hash"]
        == semantic_second["dq_contract_compatibility_hash"]
    )
    evidence_dir = tmp_path / "reports" / "reproducibility"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = evidence_dir / "tracked_fixture_exact_replay_matrix.json"
    evidence_path.write_text(
        json.dumps(
            build_tracked_fixture_exact_replay_matrix_payload(
                pipeline_name=_PIPELINE_NAME,
                manifest_payload=manifest_first,
                effective_payload=effective_first,
                occurrences=[
                    {
                        "run_id": str(manifest_first["run_id"]),
                        "manifest_id": str(manifest_first["manifest_id"]),
                    },
                    {
                        "run_id": str(manifest_second["run_id"]),
                        "manifest_id": str(manifest_second["manifest_id"]),
                    },
                ],
            ),
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    evidence_payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert evidence_payload["semantic_identity"]["snapshot_ids"] == [
        snapshots_first[0]["snapshot_id"]
    ]
    assert len(evidence_payload["occurrences"]) == 2

    get_settings.cache_clear()
    get_pipeline_config.cache_clear()


@pytest.mark.integration
@pytest.mark.no_api
@pytest.mark.asyncio
async def test_tracked_fixture_run_keeps_control_plane_stores_consistent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tracked fixture replay must keep manifest/effective-config/ledger aligned."""
    fixture_entry = load_tracked_fixture_entry(pipeline_key=_PIPELINE_KEY)
    fixture_path_raw = fixture_entry.get("fixture_path")
    assert isinstance(fixture_path_raw, str) and fixture_path_raw

    tracked_fixture_path = PROJECT_ROOT / fixture_path_raw
    cached_root = tmp_path / "cached_bronze" / "chembl" / "activity"
    materialize_cached_bronze_batch(
        tracked_fixture_path=tracked_fixture_path,
        cache_root=cached_root,
        date="2026-03-25",
    )

    data_dir = tmp_path / "runtime_data"
    monkeypatch.setenv("BIOETL_DATA_DIR", str(data_dir))
    monkeypatch.setenv("BIOETL_TEST_MODE", "true")
    monkeypatch.setenv("BIOETL_PIPELINE__HEALTH_CHECK_MODE", "probe")
    patch_clean_code_revision(monkeypatch)
    get_settings.cache_clear()
    get_pipeline_config.cache_clear()

    run_id = await run_cached_fixture_pipeline(
        pipeline_name=_PIPELINE_NAME,
        cached_bronze_path=cached_root,
        date="2026-03-25",
    )
    bundle = load_control_plane_bundle(data_dir=data_dir, run_id=run_id)

    manifest_payload = bundle["manifest_payload"]
    assert isinstance(manifest_payload, dict)
    effective_payload = bundle["effective_payload"]
    assert isinstance(effective_payload, dict)
    effective_occurrence = bundle["effective_occurrence"]
    assert isinstance(effective_occurrence, dict)
    ledger_entries = bundle["ledger_entries"]
    assert isinstance(ledger_entries, list) and ledger_entries
    lineage_fragments = bundle["lineage_fragments"]
    assert isinstance(lineage_fragments, list)

    code_provenance = manifest_payload.get("code_provenance")
    assert isinstance(code_provenance, dict)
    manifest_id = str(manifest_payload["manifest_id"])
    effective_artifact_id = str(code_provenance["effective_config_artifact_id"])

    assert effective_payload["artifact_id"] == effective_artifact_id
    assert effective_occurrence["artifact_id"] == effective_artifact_id
    assert effective_occurrence["run_id"] == str(run_id)
    assert any(entry["event_type"] == "run_finished" for entry in ledger_entries)
    assert all(entry["manifest_id"] == manifest_id for entry in ledger_entries)
    assert all(entry["run_id"] == str(run_id) for entry in ledger_entries)
    if lineage_fragments:
        assert all(
            fragment["manifest_id"] == manifest_id for fragment in lineage_fragments
        )
        assert all(fragment["run_id"] == str(run_id) for fragment in lineage_fragments)

    get_settings.cache_clear()
    get_pipeline_config.cache_clear()


@pytest.mark.integration
@pytest.mark.no_api
@pytest.mark.asyncio
async def test_tracked_fixture_strict_replay_uses_explicit_data_dir_for_control_plane_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Strict replay must persist control-plane roots under the explicit data_dir only."""
    fixture_entry = load_tracked_fixture_entry(pipeline_key=_PIPELINE_KEY)
    fixture_path_raw = fixture_entry.get("fixture_path")
    assert isinstance(fixture_path_raw, str) and fixture_path_raw

    tracked_fixture_path = PROJECT_ROOT / fixture_path_raw
    cached_root = tmp_path / "cached_bronze" / "chembl" / "activity"
    materialize_cached_bronze_batch(
        tracked_fixture_path=tracked_fixture_path,
        cache_root=cached_root,
        date="2026-03-25",
    )

    data_dir = tmp_path / "runtime_data"
    monkeypatch.setenv("BIOETL_DATA_DIR", str(data_dir))
    monkeypatch.setenv("BIOETL_TEST_MODE", "true")
    monkeypatch.setenv("BIOETL_PIPELINE__HEALTH_CHECK_MODE", "probe")
    monkeypatch.setenv(
        "BIOETL_PIPELINE__CONTROL_PLANE__REQUIRED_PERSISTENCE_PROFILE",
        "replay_ready",
    )
    patch_clean_code_revision(monkeypatch)
    get_settings.cache_clear()
    get_pipeline_config.cache_clear()

    run_id = await run_cached_fixture_pipeline(
        pipeline_name=_PIPELINE_NAME,
        cached_bronze_path=cached_root,
        date="2026-03-25",
    )
    bundle = load_control_plane_bundle(data_dir=data_dir, run_id=run_id)

    manifest_payload = bundle["manifest_payload"]
    assert isinstance(manifest_payload, dict)
    effective_payload = bundle["effective_payload"]
    assert isinstance(effective_payload, dict)
    effective_occurrence = bundle["effective_occurrence"]
    assert isinstance(effective_occurrence, dict)

    settings_snapshot = effective_payload["semantic_artifact"]["runtime_overrides"][
        "runtime_adjustments"
    ]["settings_snapshot"]
    assert settings_snapshot["settings"]["data_dir"] == str(data_dir)
    assert settings_snapshot["settings"]["data_root_mode"] == "explicit"
    assert effective_occurrence["run_id"] == str(run_id)
    assert all(
        str(artifact["path"]).startswith(str(data_dir / "output"))
        for artifact in manifest_payload["planned_artifacts"]
    )
    assert (
        data_dir
        / "output"
        / "control"
        / "run_manifest"
        / "_by_run_id"
        / f"{run_id}.txt"
    ).exists()
    assert (
        data_dir
        / "output"
        / "control"
        / "effective_config"
        / "_occurrences"
        / f"{run_id}.json"
    ).exists()

    get_settings.cache_clear()
    get_pipeline_config.cache_clear()


@pytest.mark.integration
@pytest.mark.no_api
@pytest.mark.asyncio
async def test_tracked_fixture_exact_replay_avoids_live_data_source_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exact replay must stay offline and avoid live data source construction."""
    fixture_entry = load_tracked_fixture_entry(pipeline_key=_PIPELINE_KEY)
    fixture_path_raw = fixture_entry.get("fixture_path")
    assert isinstance(fixture_path_raw, str) and fixture_path_raw

    tracked_fixture_path = PROJECT_ROOT / fixture_path_raw
    cached_root = tmp_path / "cached_bronze" / "chembl" / "activity"
    materialize_cached_bronze_batch(
        tracked_fixture_path=tracked_fixture_path,
        cache_root=cached_root,
        date="2026-03-25",
    )

    data_dir = tmp_path / "runtime_data"
    monkeypatch.setenv("BIOETL_DATA_DIR", str(data_dir))
    monkeypatch.setenv("BIOETL_TEST_MODE", "true")
    monkeypatch.setenv("BIOETL_PIPELINE__HEALTH_CHECK_MODE", "probe")
    patch_clean_code_revision(monkeypatch)

    def _raise_live_data_source(*args: object, **kwargs: object) -> object:
        raise AssertionError(
            "exact replay attempted live data source construction instead of offline cached Bronze replay"
        )

    monkeypatch.setattr(
        _observability_wiring,
        "_create_data_source",
        _raise_live_data_source,
    )
    get_settings.cache_clear()
    get_pipeline_config.cache_clear()

    run_id = await run_cached_fixture_pipeline(
        pipeline_name=_PIPELINE_NAME,
        cached_bronze_path=cached_root,
        date="2026-03-25",
    )
    manifest_payload, _effective_payload = load_control_plane_payloads(
        data_dir=data_dir,
        run_id=run_id,
    )
    snapshots = manifest_payload["source_refs"][0]["input_snapshots"]

    assert manifest_payload["launch_context"]["exact_replay"] is True
    assert manifest_payload["runtime_config"]["exact_replay"] is True
    assert len(snapshots) == 1
    assert snapshots[0]["immutable_uri"] == (
        "bronze://2026-03-25/batch_2026-03-25_tracked_fixture.jsonl.zst"
    )

    get_settings.cache_clear()
    get_pipeline_config.cache_clear()


@pytest.mark.integration
@pytest.mark.no_api
@pytest.mark.asyncio
async def test_exact_replay_without_materialized_cached_bronze_batches_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exact replay must fail closed and avoid publishing a manifest without snapshots."""
    await asyncio.sleep(0)
    cached_root = tmp_path / "cached_bronze" / "chembl" / "activity"
    (cached_root / "2026-03-25").mkdir(parents=True, exist_ok=True)

    data_dir = tmp_path / "runtime_data"
    monkeypatch.setenv("BIOETL_DATA_DIR", str(data_dir))
    monkeypatch.setenv("BIOETL_TEST_MODE", "true")
    monkeypatch.setenv("BIOETL_PIPELINE__HEALTH_CHECK_MODE", "probe")
    patch_clean_code_revision(monkeypatch)
    get_settings.cache_clear()
    get_pipeline_config.cache_clear()

    run_id = RunID(uuid4())
    context = build_cached_fixture_run_context(
        pipeline_name=_PIPELINE_NAME,
        cached_bronze_path=cached_root,
        date="2026-03-25",
        run_id=run_id,
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "Cached Bronze execution requires at least one persisted batch file "
            "for snapshot provenance"
        ),
    ):
        bootstrap_pipeline_runner(context)

    manifest_index = (
        data_dir
        / "output"
        / "control"
        / "run_manifest"
        / "_by_run_id"
        / f"{run_id}.txt"
    )
    assert not manifest_index.exists()

    get_settings.cache_clear()
    get_pipeline_config.cache_clear()
